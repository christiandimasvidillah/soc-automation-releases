from __future__ import annotations

import csv
import hashlib
import hmac
import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from config import settings


logger = logging.getLogger(__name__)
_AUDIT_LOCK = threading.Lock()
_SAFE_TICKET_KEY = re.compile(r"[^A-Za-z0-9._-]+")

_IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_UUID_PATTERN = re.compile(
    r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-"
    r"[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}\b"
)
_LONG_HEX_PATTERN = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,128}(?![0-9A-Fa-f])")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_USER_PROFILE_PATTERN = re.compile(
    r"(?i)([A-Z]:\\Users\\)([^\\/]+)(\\)"
)

# Field-field berikut adalah identifier/infrastruktur sensitif dan tidak
# diperlukan secara literal oleh AI untuk menentukan true/false positive.
_SENSITIVE_EXACT_PATHS = {
    "_id",
    "_index",
    "agent.id",
    "elastic.agent.id",
    "host.id",
    "host.name",
    "process.entity_id",
    "event.id",
    "kibana.alert.uuid",
    "kibana.alert.rule.execution.uuid",
    "kibana.alert.rule.uuid",
    "kibana.alert.ancestors.id",
    "kibana.alert.ancestors.index",
    "kibana.alert.original_event.id",
    "signal.ancestors.id",
    "signal.ancestors.index",
    "signal.original_event.id",
    "signal.rule.id",
}

# Key berakhiran berikut biasanya berupa identifier unik.
_SENSITIVE_KEY_SUFFIXES = (
    ".entity_id",
    ".agent_id",
    ".execution.uuid",
)

# Nilai akun Windows umum dipertahankan karena konteks privilege penting.
_WELL_KNOWN_ACCOUNTS = {
    "system",
    "local service",
    "network service",
    "nt authority",
    "s-1-5-18",
    "s-1-5-19",
    "s-1-5-20",
}


def _audit_dir() -> Path:
    path = Path(settings.sanitizer.audit_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_hash(value: str) -> str:
    """Membuat pseudonym HMAC konsisten dengan panjang configurable."""
    if not isinstance(value, str) or not value:
        raise ValueError("value untuk hashing harus berupa string non-kosong.")
    digest = hmac.new(
        settings.sanitizer.hash_secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[: settings.sanitizer.hash_length]


def log_audit_mapping(category: str, original_value: str, hashed_value: str) -> None:
    """Mencatat mapping pseudonym ke CSV harian secara thread-safe."""
    audit_file = _audit_dir() / f"hash_audit_{datetime.now():%Y-%m-%d}.csv"
    try:
        with _AUDIT_LOCK:
            file_exists = audit_file.exists()
            with audit_file.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                if not file_exists:
                    writer.writerow(
                        ["Timestamp", "Category", "Original_Value", "Hashed_Value"]
                    )
                writer.writerow(
                    [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        category,
                        original_value,
                        hashed_value,
                    ]
                )
    except OSError:
        logger.exception("Gagal menulis audit mapping ke %s.", audit_file)


def _pseudonym(category: str, value: Any, prefix: str) -> str:
    original = str(value)
    masked = f"{prefix}_{generate_hash(original.casefold())}"
    log_audit_mapping(category, original, masked)
    return masked


def _valid_ipv4(value: str) -> bool:
    try:
        return all(0 <= int(part) <= 255 for part in value.split("."))
    except ValueError:
        return False


def _sanitize_internal_url(match: re.Match[str]) -> str:
    original = match.group(0)
    # Lepaskan punctuation/HTML entity yang sering menempel pada URL.
    trailing = ""
    while original and original[-1] in ".,;)]":
        trailing = original[-1] + trailing
        original = original[:-1]

    try:
        parts = urlsplit(original)
    except ValueError:
        return match.group(0)

    hostname = (parts.hostname or "").casefold()
    is_internal_elastic = (
        hostname.endswith("elastic-cloud.com")
        or hostname.endswith("elastic-cloud.com&quot;")
    )
    if not is_internal_elastic:
        return match.group(0)

    safe_host = _pseudonym("Internal_Elastic_Host", hostname, "ELASTIC_HOST")
    if parts.port:
        safe_host = f"{safe_host}:{parts.port}"

    # Path/query dapat berisi Alert UUID dan nama index internal.
    safe_path = _LONG_HEX_PATTERN.sub(
        lambda m: _pseudonym("Alert_Identifier", m.group(0), "ALERT_ID"),
        parts.path,
    )
    safe_query = re.sub(
        r"(?i)(index=)([^&]+)",
        lambda m: m.group(1)
        + _pseudonym("Elastic_Index", m.group(2), "INDEX"),
        parts.query,
    )
    return urlunsplit(
        (parts.scheme, safe_host, safe_path, safe_query, parts.fragment)
    ) + trailing


def _sanitize_string(value: str, path: str) -> str:
    result = value

    result = _URL_PATTERN.sub(_sanitize_internal_url, result)

    def replace_ip(match: re.Match[str]) -> str:
        original = match.group(0)
        if not _valid_ipv4(original):
            return original
        return _pseudonym("IP_Address", original, "IP")

    result = _IPV4_PATTERN.sub(replace_ip, result)
    result = _EMAIL_PATTERN.sub(
        lambda m: _pseudonym("Email_Address", m.group(0), "EMAIL"),
        result,
    )
    result = _MAC_PATTERN.sub(
        lambda m: _pseudonym("MAC_Address", m.group(0), "MAC"),
        result,
    )
    result = _USER_PROFILE_PATTERN.sub(
        lambda m: m.group(1)
        + _pseudonym("Windows_Profile", m.group(2), "USER")
        + m.group(3),
        result,
    )

    # Hash/UUID hanya disamarkan untuk field ID/hash atau konteks URL/identifier.
    path_lower = path.casefold()
    if any(token in path_lower for token in ("uuid", "thumbprint", "hash", "_id")):
        result = _UUID_PATTERN.sub(
            lambda m: _pseudonym("UUID", m.group(0), "UUID"),
            result,
        )
        result = _LONG_HEX_PATTERN.sub(
            lambda m: _pseudonym("Cryptographic_Identifier", m.group(0), "HASH"),
            result,
        )

    return result


def _canonical_path(path: str) -> str:
    """Hapus wrapper respons Elastic agar rule path berlaku di _source/fields."""
    normalized = path.casefold().strip(".")
    wrappers = ("_source.", "fields.")
    changed = True
    while changed:
        changed = False
        for wrapper in wrappers:
            if normalized.startswith(wrapper):
                normalized = normalized[len(wrapper):]
                changed = True
    return normalized


def _matches_sensitive_path(path: str) -> bool:
    """Cocokkan full path maupun suffix pada object Elastic yang bersarang."""
    canonical = _canonical_path(path)
    if canonical in _SENSITIVE_EXACT_PATHS:
        return True
    return any(
        canonical.endswith("." + sensitive_path)
        for sensitive_path in _SENSITIVE_EXACT_PATHS
    )


def _sanitize_scalar_by_path(value: Any, path: str) -> Any:
    canonical_path = _canonical_path(path)
    text = str(value)
    if canonical_path.endswith((
        "data.findings.sensitivedbentries.sample",
        "data.findings.sensitivefiles.sensitivedata.sample",
    )):
        return "[REDACTED_SENSITIVE_SAMPLE]"
    if canonical_path.endswith((
        "data.asset_tags.configure-sh",
        "data.asset_tags.user-data",
        "data.asset_tags.ssh-keys",
        "data.asset_tags.kube-env",
        "data.asset_tags.kubeconfig",
        "data.asset_tags.kubelet-config",
        "data.asset_tags.kube-labels",
        "data.asset_tags.kube_labels",
    )):
        return "[REDACTED_SENSITIVE_BLOB]"

    if canonical_path in {"user.name", "user.id", "user.domain"}:
        if text.casefold() in _WELL_KNOWN_ACCOUNTS:
            return value
        return _pseudonym("User_Identity", text, "USER")

    suffix_sensitive = canonical_path.endswith(_SENSITIVE_KEY_SUFFIXES)
    if _matches_sensitive_path(canonical_path) or suffix_sensitive:
        prefix = "HOST" if canonical_path.endswith("host.name") else "ID"
        return _pseudonym("Sensitive_Identifier", text, prefix)

    if isinstance(value, str):
        return _sanitize_string(value, canonical_path)
    return value


def _sanitize_node(node: Any, path: str = "") -> Any:
    if isinstance(node, dict):
        return {
            key: _sanitize_node(
                value,
                f"{path}.{key}" if path else str(key),
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_sanitize_node(value, path) for value in node]
    return _sanitize_scalar_by_path(node, path)


def sanitize_siem_payload_with_hash(raw_json_string: str) -> str:
    """
    Sanitasi terstruktur payload SIEM sebelum dikirim ke AI.

    Struktur JSON, nama rule, severity, MITRE, process name, signed/trusted
    status, registry path/data, timestamp, dan konteks investigasi dipertahankan.
    Identitas host/user/agent, event IDs, UUID, hash identifiers, IP, email,
    MAC, internal Elastic URL/index, dan username pada profile path dipseudonymkan.
    """
    if not isinstance(raw_json_string, str) or not raw_json_string.strip():
        raise ValueError("raw_json_string harus berupa string JSON non-kosong.")
    try:
        parsed: Any = json.loads(raw_json_string)
    except json.JSONDecodeError as exc:
        raise ValueError("Payload SIEM bukan JSON yang valid.") from exc

    sanitized = _sanitize_node(parsed)
    return json.dumps(sanitized, ensure_ascii=False, indent=2)


def save_json_comparison(
    ticket_key: str,
    raw_json: str,
    sanitized_json: str,
) -> None:
    """Menyimpan JSON asli dan tersanitasi dengan write atomik."""
    safe_key = _SAFE_TICKET_KEY.sub("_", ticket_key.strip())
    if not safe_key:
        raise ValueError("ticket_key tidak valid untuk nama file audit.")
    try:
        raw_payload = json.loads(raw_json)
        sanitized_payload = json.loads(sanitized_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Raw atau sanitized payload bukan JSON valid.") from exc

    output_dir = _audit_dir()
    destinations = (
        (output_dir / f"{safe_key}_raw.json", raw_payload),
        (output_dir / f"{safe_key}_sanitized.json", sanitized_payload),
    )
    with _AUDIT_LOCK:
        for destination, payload in destinations:
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(destination)
    logger.info("Audit JSON tersimpan untuk tiket %s.", ticket_key)
