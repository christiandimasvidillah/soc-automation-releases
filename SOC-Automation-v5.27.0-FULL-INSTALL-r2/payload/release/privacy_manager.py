from __future__ import annotations

import copy
import ipaddress
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from config import settings
from data_sanitizer import generate_hash, log_audit_mapping, save_json_comparison
from local_ai_detector import (
    LocalAIDetectorError,
    OllamaSensitiveDetector,
)

logger = logging.getLogger(__name__)

# High-confidence paths. Matching uses canonical suffixes, so wrappers such as
# hits.hits._source and fields do not bypass discovery.
SENSITIVE_PATH_RULES: dict[str, tuple[str, str]] = {
    "data.findings.database.name": ("DATABASE_NAME", "DATABASE"),
    "data.findings.database.id": ("DATABASE_ID", "DATABASE_ID"),
    "data.findings.inventory.name": ("ASSET_NAME", "ASSET"),
    "data.findings.inventory.id": ("ASSET_ID", "ASSET_ID"),
    "data.findings.inventory.asset_unique_id": ("ASSET_ID", "ASSET_ID"),
    "data.findings.name": ("DATA_OBJECT", "DATA_OBJECT"),
    "data.findings.id": ("FINDING_ID", "FINDING"),
    "data.source": ("DATA_OBJECT", "DATA_OBJECT"),
    "data.asset_name": ("ASSET_NAME", "ASSET"),
    "data.asset_hostname": ("ASSET_NAME", "ASSET"),
    "data.cluster_name": ("ASSET_NAME", "ASSET"),
    "data.asset_vendor_id": ("ASSET_ID", "ASSET_ID"),
    "data.asset_unique_id": ("ASSET_ID", "ASSET_ID"),
    "data.account_name": ("CLOUD_ACCOUNT", "CLOUD_ACCOUNT"),
    "data.account_id": ("CLOUD_ACCOUNT_ID", "CLOUD_ACCOUNT_ID"),
    "data.cloud_provider_id": ("CLOUD_ACCOUNT", "CLOUD_ACCOUNT"),
    "data.alert_id": ("VENDOR_ALERT_ID", "VENDOR_ALERT"),
    "data.alert_ui_link": ("VENDOR_URL", "URL"),
    "data.rule_id": ("VENDOR_RULE_ID", "RULE"),
    "data.asset_tags.owner": ("INTERNAL_OWNER", "TEAM"),
    "data.asset_tags.app": ("INTERNAL_APP", "APP"),
    "data.asset_tags.product": ("INTERNAL_PRODUCT", "PRODUCT"),
    "data.asset_tags.system": ("INTERNAL_SYSTEM", "SYSTEM"),
    "data.asset_tags.name": ("ASSET_NAME", "ASSET"),
    "data.asset_tags.budgetid": ("INTERNAL_BUDGET", "BUDGET"),
    "data.asset_tags.projectid": ("CLOUD_ACCOUNT", "CLOUD_ACCOUNT"),
    "data.asset_tags.goog-fleet-project": ("CLOUD_ACCOUNT_ID", "CLOUD_ACCOUNT_ID"),
    "data.asset_tags.mesh_id": ("INTERNAL_SYSTEM", "SYSTEM"),
    "data.asset_tags.cluster-uid": ("INTERNAL_SYSTEM", "SYSTEM"),
    "data.asset_tags.instance-template": ("ASSET_ID", "ASSET_ID"),
    "data.asset_tags.created-by": ("ASSET_ID", "ASSET_ID"),
    "data.asset_tags.goog-k8s-cluster-name": ("ASSET_NAME", "ASSET"),
    "data.asset_tags.gke-cluster": ("ASSET_NAME", "ASSET"),
    "data.asset_tags.cluster-name": ("ASSET_NAME", "ASSET"),
    "data.asset_vpcs": ("NETWORK_ID", "NETWORK"),
    "data.business_units.name": ("INTERNAL_OWNER", "TEAM"),
    "data.findings.fimevents.id": ("FINDING_ID", "FINDING"),
    "kibana.alert.rule.rule_id": ("RULE_UUID", "RULE"),
    "kibana.alert.rule.parameters.rule_id": ("RULE_UUID", "RULE"),
    "kibana.alert.ancestors.rule": ("RULE_UUID", "RULE"),
    "kibana.alert.rule.exceptions_list.id": ("EXCEPTION_ID", "EXCEPTION"),
    "kibana.alert.rule.exceptions_list.list_id": ("EXCEPTION_LIST_ID", "EXCEPTION_LIST"),
    "_index": ("ELASTIC_INDEX", "INDEX"),
    "_id": ("ALERT_ID", "ALERT"),
    "host.name": ("HOSTNAME", "HOST"),
    "host.hostname": ("HOSTNAME", "HOST"),
    "host.id": ("HOST_ID", "HOST_ID"),
    "host.domain": ("DOMAIN", "DOMAIN"),
    "agent.id": ("AGENT_ID", "AGENT"),
    "elastic.agent.id": ("AGENT_ID", "AGENT"),
    "endpoint.id": ("ENDPOINT_ID", "ENDPOINT"),
    "event.id": ("EVENT_ID", "EVENT"),
    "process.entity_id": ("PROCESS_ID", "PROCESS"),
    "process.parent.entity_id": ("PROCESS_ID", "PROCESS"),
    "process.ext.ancestry": ("PROCESS_ANCESTRY", "PROCESS"),
    "kibana.alert.uuid": ("ALERT_ID", "ALERT"),
    "kibana.alert.rule.execution.uuid": ("EXECUTION_ID", "EXECUTION"),
    "kibana.alert.rule.uuid": ("RULE_UUID", "RULE"),
    "kibana.alert.original_event.id": ("EVENT_ID", "EVENT"),
    "kibana.alert.ancestors.id": ("ANCESTOR_ID", "ANCESTOR"),
    "kibana.alert.ancestors.index": ("ELASTIC_INDEX", "INDEX"),
    "kibana.alert.new_terms": ("NEW_TERM_ID", "TERM"),
    "signal.ancestors.id": ("ANCESTOR_ID", "ANCESTOR"),
    "signal.ancestors.index": ("ELASTIC_INDEX", "INDEX"),
    "signal.original_event.id": ("EVENT_ID", "EVENT"),
    "kibana.alert.rule.created_by": ("INTERNAL_USER", "USER"),
    "kibana.alert.rule.updated_by": ("INTERNAL_USER", "USER"),
    "kibana.alert.workflow_assignee_ids": ("INTERNAL_USER", "USER"),
    "kibana.alert.rule.actions.id": ("CONNECTOR_ID", "CONNECTOR"),
    "kibana.alert.rule.actions.uuid": ("ACTION_UUID", "ACTION"),
    "kibana.alert.rule.parameters.data_view_id": ("DATA_VIEW_ID", "DATA_VIEW"),
    "kibana.alert.rule.parameters.filters.meta.index": ("DATA_VIEW_ID", "DATA_VIEW"),
    "kibana.alert.rule.parameters.filters.meta.params.index": ("DATA_VIEW_ID", "DATA_VIEW"),
    "kibana.alert.url": ("INTERNAL_URL", "URL"),
    "kibana.alert.rule.meta.kibana_siem_app_url": ("INTERNAL_URL", "URL"),
    "kibana.alert.rule.parameters.meta.kibana_siem_app_url": ("INTERNAL_URL", "URL"),
    "alarm_id": ("SOCRADAR_ALARM_ID", "ALARM"),
    "notification_id": ("SOCRADAR_NOTIFICATION_ID", "NOTIFICATION"),
}

WELL_KNOWN_ACCOUNTS = {
    "system", "nt authority", "local service", "network service",
    "s-1-5-18", "s-1-5-19", "s-1-5-20",
}
PRESERVE_PATH_SUFFIXES = (
    "process.name", "process.executable", "process.command_line", "process.args",
    "process.parent.name", "registry.path", "registry.key", "registry.value",
    "registry.data.strings", "file.name", "file.path", "dll.name",
    "code_signature.subject_name", "code_signature.trusted", "code_signature.status",
    "kibana.alert.rule.name", "kibana.alert.rule.description", "kibana.alert.rule.note",
    "kibana.alert.rule.query", "kibana.alert.severity", "kibana.alert.risk_score",
    "@timestamp", "event.created", "event.ingested",
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![0-9A-Fa-f:])")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
USER_PROFILE_RE = re.compile(r"(?i)([A-Z]:\\Users\\)([^\\/]+)(\\)")
# UNC harus berbentuk \\server\share. Regex sengaja menangkap server dan
# share agar escape sequence EQL/registry tidak dianggap UNC path.
UNC_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_\\])\\\\"
    r"([A-Za-z0-9][A-Za-z0-9.-]{1,62})\\"
    r"([^\\\s]+)"
)
UNC_RESERVED_NAMES = {
    "registry", "machine", "system", "system32", "syswow64", "windows",
    "services", "service", "networkprovider", "providerpath", "controlset001",
    "controlset002", "currentcontrolset", "program files", "program files (x86)",
}
INTERNAL_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
PSEUDONYM_RE = re.compile(
    r"^(?:INDEX|ALERT|HOST|HOST_ID|AGENT|EVENT|PROCESS|ANCESTOR|USER|URL|"
    r"EMAIL|IP|MAC|HASH|UUID|RULE|EXECUTION|TERM|ID|SECRET|CONNECTOR|"
    r"ACTION|DATA_VIEW|ALARM|NOTIFICATION|DOMAIN|ENDPOINT|DATABASE|DATABASE_ID|"
    r"DATA_OBJECT|FINDING|ASSET|ASSET_ID|CLOUD_ACCOUNT|CLOUD_ACCOUNT_ID|TEAM|"
    r"APP|PRODUCT|SYSTEM|BUDGET|VENDOR_ALERT|EXCEPTION|EXCEPTION_LIST|NETWORK)_[0-9a-f]{8,64}$",
    re.IGNORECASE,
)

POTENTIAL_SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|authorization|password|secret)\s*[:=]\s*([^\s,;]+)"
)


MAX_PROPAGATION_SEEDS = 256
MAX_PROPAGATED_OCCURRENCES = 4096


@dataclass(frozen=True)
class Finding:
    category: str
    path: str
    original: str
    replacement: str
    confidence: str
    start_offset: int | None = None
    end_offset: int | None = None



LOCAL_AI_CATEGORY_MAPPING = {
    "EMAIL": ("EMAIL", "EMAIL"),
    "IP_ADDRESS": ("IP_ADDRESS", "IP"),
    "USER_IDENTITY": ("USER_IDENTITY", "USER"),
    "HOST_IDENTIFIER": ("HOSTNAME", "HOST"),
    "ASSET_IDENTIFIER": ("ASSET_NAME", "ASSET"),
    "CLOUD_IDENTIFIER": ("CLOUD_ACCOUNT", "CLOUD_ACCOUNT"),
    "INTERNAL_URL": ("INTERNAL_URL", "URL"),
    "POTENTIAL_SECRET": ("POTENTIAL_SECRET", "SECRET"),
    "UNKNOWN_SENSITIVE": ("UNKNOWN_SENSITIVE", "SECRET"),
}


def _resolve_local_ai_path(payload: Any, path: str):
    """Resolve dot paths while supporting dictionary keys containing dots."""
    parts = path.split(".")
    current = payload
    position = 0

    while position < len(parts):
        if isinstance(current, list):
            part = parts[position]
            if not part.isdigit():
                raise LocalAIDetectorError(
                    "LOCAL_AI_ARRAY_INDEX_INVALID"
                )
            index = int(part)
            if index < 0 or index >= len(current):
                raise LocalAIDetectorError(
                    "LOCAL_AI_ARRAY_INDEX_OUT_OF_RANGE"
                )
            current = current[index]
            position += 1
            continue

        if isinstance(current, dict):
            matched = False
            for end in range(len(parts), position, -1):
                candidate = ".".join(parts[position:end])
                if candidate in current:
                    current = current[candidate]
                    position = end
                    matched = True
                    break
            if not matched:
                raise LocalAIDetectorError(
                    "LOCAL_AI_PATH_NOT_FOUND"
                )
            continue

        raise LocalAIDetectorError(
            "LOCAL_AI_PATH_PARENT_NOT_CONTAINER"
        )

    return current


def _convert_local_ai_findings(
    payload: dict[str, Any],
    detected: list[Any],
):
    converted: list[Finding] = []

    for item in detected:
        mapping = LOCAL_AI_CATEGORY_MAPPING.get(
            item.category
        )

        if mapping is None:
            raise LocalAIDetectorError(
                "LOCAL_AI_CATEGORY_MAPPING_MISSING"
            )

        original = _resolve_local_ai_path(
            payload,
            item.path,
        )

        if not isinstance(
            original,
            (str, int, float),
        ) or isinstance(original, bool):
            raise LocalAIDetectorError(
                "LOCAL_AI_PATH_NOT_SCALAR"
            )

        original_text = str(original).strip()

        if not original_text:
            continue

        category, prefix = mapping

        if category == "IP_ADDRESS":
            if not isinstance(original, str):
                logger.warning(
                    "Local AI IP finding ignored for non-string path %s.",
                    item.path,
                )
                continue
            try:
                ipaddress.ip_address(original_text)
            except ValueError:
                logger.warning(
                    "Local AI IP finding ignored for invalid value at path %s.",
                    item.path,
                )
                continue

        replacement = _replacement(
            category,
            prefix,
            original_text,
        )

        converted.append(
            Finding(
                category=category,
                path=item.path,
                original=original_text,
                replacement=replacement,
                confidence="high",
            )
        )

    return converted


def _merge_findings(
    deterministic: list[Finding],
    local_ai: list[Finding],
):
    merged: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()

    for finding in deterministic + local_ai:
        key = (
            finding.category,
            finding.path,
            finding.original,
        )

        if key in seen:
            continue

        seen.add(key)
        merged.append(finding)

    return merged


def _discover_verified_occurrences(
    payload: Any,
    structural_findings: list[Finding],
) -> list[Finding]:
    """Temukan salinan terverifikasi dari nilai sensitif struktural."""
    scalar_strings: list[tuple[str, str]] = []

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                child = str(key) if not path else path + "." + str(key)
                walk(value, child)
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                child = str(index) if not path else path + "." + str(index)
                walk(value, child)
            return
        if isinstance(node, str):
            scalar_strings.append((path, node))

    walk(payload)
    propagated: list[Finding] = []
    seen: set[tuple[str, int, int, str]] = set()

    for finding in structural_findings[:MAX_PROPAGATION_SEEDS]:
        if _rule_for_path(finding.path) is None or not finding.original:
            continue
        pattern = re.compile(
            r"(?<![A-Za-z0-9._-])"
            + re.escape(finding.original)
            + r"(?![A-Za-z0-9._-])",
            re.IGNORECASE,
        )
        for path, scalar in scalar_strings:
            normalized = re.sub(r"\.\d+(?=\.|$)", "[]", path)
            if normalized == finding.path:
                continue
            # A scalar on another structural-sensitive path must be replaced
            # as one complete value. Propagating a shorter seed into it first
            # would mutate the source string and prevent exact path replacement.
            if _rule_for_path(normalized) is not None:
                continue
            for match in pattern.finditer(scalar):
                location = (path, match.start(), match.end(), finding.replacement)
                if location in seen:
                    continue
                seen.add(location)
                if len(propagated) >= MAX_PROPAGATED_OCCURRENCES:
                    return propagated
                propagated.append(Finding(
                    category=finding.category,
                    path=path,
                    original=match.group(0),
                    replacement=finding.replacement,
                    confidence=finding.confidence,
                    start_offset=match.start(),
                    end_offset=match.end(),
                ))
    return propagated


@dataclass(frozen=True)
class PrivacyResult:
    sanitized_json: str
    findings_count: int
    replacements_count: int
    residual_count: int
    safe_for_ai: bool
    categories: tuple[str, ...]
    residual_categories: tuple[str, ...]


def _canonical(path: str) -> str:
    value = path.casefold().replace("[]", "").strip(".")
    for wrapper in ("hits.hits.", "_source.", "fields."):
        value = value.replace(wrapper, "")
    return value


def _rule_for_path(path: str) -> tuple[str, str] | None:
    canonical = _canonical(path)
    # Preserve analytical fields before generic suffix matching.
    if any(canonical.endswith(item) for item in PRESERVE_PATH_SUFFIXES):
        return None
    # Longest rule first prevents agent.id from overriding elastic.agent.id.
    for suffix in sorted(SENSITIVE_PATH_RULES, key=len, reverse=True):
        if canonical == suffix or canonical.endswith("." + suffix):
            return SENSITIVE_PATH_RULES[suffix]
    if canonical.endswith((".entity_id", ".agent_id", ".execution.uuid")):
        return "IDENTIFIER", "ID"
    if canonical.endswith((".thumbprint_sha256", ".imphash", ".hash.sha256")):
        return "CRYPTOGRAPHIC_IDENTIFIER", "HASH"
    if canonical in {"user.name", "user.id", "user.domain", "user.email"}:
        return "USER_IDENTITY", "USER"
    return None


def _scalar_values(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            yield value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield str(value)
    elif isinstance(value, list):
        for item in value:
            yield from _scalar_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _scalar_values(item)


def _replacement(category: str, prefix: str, value: str) -> str:
    masked = f"{prefix}_{generate_hash(value.casefold())}"
    log_audit_mapping(category, value, masked)
    return masked


def _walk(node: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            yield child, value
            yield from _walk(value, child)
    elif isinstance(node, list):
        list_path = path + "[]"
        for value in node:
            yield list_path, value
            yield from _walk(value, list_path)


_REDACT_PATH_SUFFIXES = (
    "data.findings.sensitivedbentries.sample",
    "data.findings.sensitivefiles.sensitivedata.sample",
    "data.asset_tags.configure-sh",
    "data.asset_tags.user-data",
    "data.asset_tags.ssh-keys",
    "data.asset_tags.kube-env",
    "data.asset_tags.kubeconfig",
    "data.asset_tags.kubelet-config",
    "data.asset_tags.kube-labels",
    "data.asset_tags.kube_labels",
    "gcp.audit.request.spec.request",
    "gcp.audit.response.spec.request",
    "request.spec.request",
    "response.spec.request",
)

_HIGH_RISK_BLOB_KEYS = {
    "password", "passwd", "pwd",
    "api_key", "api-key", "apikey",
    "authorization", "bearer_token", "bearer-token",
    "secret", "client_secret", "client-secret",
    "access_token", "access-token",
    "refresh_token", "refresh-token",
    "configure-sh", "configure_sh", "userdata", "user-data", "ssh-keys",
    "ssh_keys", "kube-env", "kube_env", "kubeconfig", "kubelet-config", "kube-labels", "kube_labels", 
    "kubelet_config", "private_key", "private-key", "client_secret",
    "client-secret", "access_token", "access-token", "refresh_token",
    "refresh-token", "bootstrap_key", "bootstrap-key", "certificate_request",
    "certificate-request", "csr", "public_key", "public-key", "certificate",
    "attestation", "attestation_data", "attestation-data", "attestation_signature",
    "attestation-signature", "vm_identity", "vm-identity", "credential-id",
    "client-certificate-data", "client-key-data", "certificate-authority-data",
}


def _redact_high_risk_samples(node: Any, path: str = "") -> tuple[Any, int]:
    count = 0
    if isinstance(node, dict):
        result: dict[str, Any] = {}
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            canonical = _canonical(child)
            leaf = str(key).strip().casefold()
            if any(canonical == item or canonical.endswith("." + item) for item in _REDACT_PATH_SUFFIXES):
                marker = (
                    "[REDACTED_SENSITIVE_SAMPLE]"
                    if canonical.endswith(".sample")
                    else "[REDACTED_SENSITIVE_BLOB]"
                )
                result[key] = marker
                count += 1
            elif leaf in _HIGH_RISK_BLOB_KEYS:
                result[key] = "[REDACTED_SENSITIVE_BLOB]"
                count += 1
            elif isinstance(value, str) and (
                (leaf == "request" and canonical.endswith(".spec.request") and len(value) >= 128)
                or ("credential-id" in canonical and ("SHA" in value.upper() or len(value) >= 32))
                or re.search(r"-----BEGIN (?:CERTIFICATE|CERTIFICATE REQUEST|ATTESTATION DATA|ATTESTATION SIGNATURE|VM IDENTITY|PUBLIC KEY|PRIVATE KEY)", value, re.I)
            ):
                result[key] = "[REDACTED_CERTIFICATE_OR_ATTESTATION_BLOB]"
                count += 1
            else:
                result[key], child_count = _redact_high_risk_samples(value, child)
                count += child_count
        return result, count
    if isinstance(node, list):
        result_list = []
        for value in node:
            sanitized, child_count = _redact_high_risk_samples(value, path)
            result_list.append(sanitized)
            count += child_count
        return result_list, count
    return node, 0


class SensitiveDataDetector:
    def discover(self, payload: Any) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[tuple[str, str, str]] = set()

        def add(category: str, path: str, value: str, prefix: str, confidence: str) -> None:
            normalized = value.strip()
            if (
                not normalized
                or normalized.casefold() in WELL_KNOWN_ACCOUNTS
                or PSEUDONYM_RE.fullmatch(normalized)
            ):
                return
            key = (category, path, normalized)
            if key in seen:
                return
            seen.add(key)
            findings.append(Finding(
                category, path, normalized,
                _replacement(category, prefix, normalized), confidence,
            ))

        # Pass 1: structural high-confidence discovery.
        for path, value in _walk(payload):
            rule = _rule_for_path(path)
            if rule:
                category, prefix = rule
                for scalar in _scalar_values(value):
                    add(category, path, scalar, prefix, "high")

        # Pass 2: value patterns from every free-text scalar.
        for path, value in _walk(payload):
            if not isinstance(value, str):
                continue
            for match in EMAIL_RE.finditer(value):
                add("EMAIL", path, match.group(0), "EMAIL", "high")
            for match in IPV4_RE.finditer(value):
                try:
                    ipaddress.ip_address(match.group(0))
                except ValueError:
                    continue
                add("IP_ADDRESS", path, match.group(0), "IP", "high")
            for match in IPV6_RE.finditer(value):
                candidate = match.group(0)
                try:
                    ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                add("IP_ADDRESS", path, candidate, "IP", "high")
            for match in MAC_RE.finditer(value):
                add("MAC_ADDRESS", path, match.group(0), "MAC", "high")
            for match in USER_PROFILE_RE.finditer(value):
                add("WINDOWS_PROFILE", path, match.group(2), "USER", "high")
            for match in UNC_RE.finditer(value):
                server = match.group(1)
                share = match.group(2)
                server_lower = server.casefold()
                # Hindari false positive dari escaped EQL/registry/Windows path,
                # misalnya \\REGISTRY\MACHINE atau \\Services\*.
                if (
                    server_lower in UNC_RESERVED_NAMES
                    or share in {"*", "?*"}
                    or server.startswith(("%", "?"))
                ):
                    continue
                # Host internal yang pendek dan murni alfabet sulit dibedakan
                # dari kata biasa. Terima jika bentuknya jelas sebagai host,
                # atau jika path field memang menunjukkan network/UNC.
                canonical_path = _canonical(path)
                host_shaped = (
                    "." in server
                    or "-" in server
                    or any(char.isdigit() for char in server)
                    or any(token in canonical_path for token in (
                        "unc", "network", "share", "server", "source", "destination"
                    ))
                )
                if host_shaped:
                    add("UNC_HOST", path, server, "HOST", "high")
            for match in POTENTIAL_SECRET_RE.finditer(value):
                add("POTENTIAL_SECRET", path, match.group(1), "SECRET", "high")
            for match in INTERNAL_URL_RE.finditer(value):
                url = match.group(0)
                if any(marker in url.casefold() for marker in (
                    "elastic-cloud.com", ".local", ".internal", "atlassian.net",
                    "platform.socradar.com", "image.socradar.com"
                )):
                    add("INTERNAL_URL", path, url, "URL", "high")

        return findings


class SensitiveDataSanitizer:
    def apply(self, payload: Any, findings: list[Finding]) -> tuple[Any, int]:
        result = copy.deepcopy(payload)
        findings_by_path: dict[str, list[Finding]] = {}

        for finding in findings:
            findings_by_path.setdefault(
                finding.path,
                [],
            ).append(finding)

        count = 0

        def transform(node: Any, path: str = "") -> Any:
            nonlocal count

            if isinstance(node, dict):
                return {
                    key: transform(
                        value,
                        str(key)
                        if not path
                        else path + "." + str(key),
                    )
                    for key, value in node.items()
                }

            if isinstance(node, list):
                return [
                    transform(
                        value,
                        path + "." + str(index)
                        if path
                        else str(index),
                    )
                    for index, value in enumerate(node)
                ]

            deterministic_path = re.sub(
                r"\.\d+(?=\.|$)",
                "[]",
                path,
            )
            path_findings = list(
                findings_by_path.get(path, [])
            )
            if deterministic_path != path:
                path_findings.extend(
                    findings_by_path.get(
                        deterministic_path,
                        [],
                    )
                )

            if isinstance(node, str):
                updated = node

                offset_findings = [
                    finding
                    for finding in path_findings
                    if finding.start_offset is not None
                    and finding.end_offset is not None
                ]
                for finding in sorted(
                    offset_findings,
                    key=lambda item: item.start_offset,
                    reverse=True,
                ):
                    start = finding.start_offset
                    end = finding.end_offset
                    if (
                        start is None
                        or end is None
                        or start < 0
                        or end < start
                        or end > len(updated)
                        or updated[start:end] != finding.original
                    ):
                        continue
                    updated = updated[:start] + finding.replacement + updated[end:]
                    count += 1

                for finding in sorted(
                    (
                        item
                        for item in path_findings
                        if item.start_offset is None
                        and item.end_offset is None
                    ),
                    key=lambda item: len(item.original),
                    reverse=True,
                ):
                    occurrences = updated.count(
                        finding.original
                    )

                    if occurrences:
                        updated = updated.replace(
                            finding.original,
                            finding.replacement,
                        )
                        count += occurrences

                return updated

            if isinstance(node, (int, float)) and not isinstance(node, bool):
                scalar = str(node)

                for finding in path_findings:
                    if scalar == finding.original:
                        count += 1
                        return finding.replacement

            return node

        return transform(result), count


def _enforce_sensitive_paths(node: Any, path: str = ""):
    """
    Memastikan scalar pada path sensitif selalu dipseudonimkan.

    Pass ini melengkapi replacement global dan menangani struktur
    dictionary/list seperti hits.hits[]._source.
    """
    replacements = 0

    if isinstance(node, dict):
        result = {}

        for key, value in node.items():
            child_path = (
                str(key)
                if not path
                else path + "." + str(key)
            )

            rule = _rule_for_path(child_path)

            if (
                rule is not None
                and isinstance(value, (str, int, float))
                and not isinstance(value, bool)
            ):
                category, prefix = rule
                scalar = str(value).strip()

                if (
                    scalar
                    and scalar.casefold() not in WELL_KNOWN_ACCOUNTS
                    and not PSEUDONYM_RE.fullmatch(scalar)
                    and not scalar.startswith("[REDACTED_")
                ):
                    result[key] = _replacement(
                        category,
                        prefix,
                        scalar,
                    )
                    replacements += 1
                    continue

            transformed, count = _enforce_sensitive_paths(
                value,
                child_path,
            )

            result[key] = transformed
            replacements += count

        return result, replacements

    if isinstance(node, list):
        result = []
        list_path = path + "[]"
        list_rule = _rule_for_path(list_path)

        for value in node:
            if (
                list_rule is not None
                and isinstance(value, (str, int, float))
                and not isinstance(value, bool)
            ):
                category, prefix = list_rule
                scalar = str(value).strip()
                if (
                    scalar
                    and scalar.casefold() not in WELL_KNOWN_ACCOUNTS
                    and not PSEUDONYM_RE.fullmatch(scalar)
                    and not scalar.startswith("[REDACTED_")
                ):
                    result.append(_replacement(category, prefix, scalar))
                    replacements += 1
                    continue

            transformed, count = _enforce_sensitive_paths(
                value,
                list_path,
            )
            result.append(transformed)
            replacements += count

        return result, replacements

    return node, 0



class SanitizationValidator:
    def validate(self, sanitized_json: str, findings: list[Finding]) -> list[Finding]:
        residuals: list[Finding] = []
        # Residual ditentukan melalui structured rediscovery.
        # Global substring matching sengaja tidak digunakan karena
        # nilai pendek dapat cocok pada lokasi lain dan menyebabkan
        # false positive.

        # Re-run discovery to catch sensitive values introduced or missed by pass 1.
        payload = json.loads(sanitized_json)
        rediscovered = SensitiveDataDetector().discover(payload)
        known_replacements = {f.replacement for f in findings}
        residual_keys = {(f.category, f.path, f.original) for f in residuals}
        for finding in rediscovered:
            if (
                finding.original in known_replacements
                or PSEUDONYM_RE.fullmatch(finding.original)
            ):
                continue
            key = (finding.category, finding.path, finding.original)
            if key not in residual_keys:
                residuals.append(finding)
                residual_keys.add(key)
        return residuals


class PrivacyManager:
    """Local discovery -> sanitization -> residual validation, fail closed."""
    def __init__(self, enable_local_ai: bool = True) -> None:
        self.detector = SensitiveDataDetector()
        self.local_ai_detector = (
            OllamaSensitiveDetector(settings.local_ai)
            if enable_local_ai
            else type("DisabledLocalAI", (), {"detect": lambda self, payload: []})()
        )
        self.sanitizer = SensitiveDataSanitizer()
        self.validator = SanitizationValidator()

    def prepare_payload(
        self,
        *,
        ticket_key: str,
        raw_json: str,
    ) -> PrivacyResult:
        raw_payload = json.loads(raw_json)

        if not isinstance(raw_payload, dict):
            raise ValueError(
                "Raw SIEM JSON harus berupa JSON object."
            )

        local_ai_findings: list[Finding] = []
        local_ai_error: str | None = None

        logger.info(
            "[%s] Local AI sensitive-data discovery dimulai.",
            ticket_key,
        )

        try:
            detected = self.local_ai_detector.detect(
                raw_payload
            )

            local_ai_findings = (
                _convert_local_ai_findings(
                    raw_payload,
                    detected,
                )
            )

            logger.info(
                "[%s] Local AI findings valid=%d.",
                ticket_key,
                len(local_ai_findings),
            )

        except LocalAIDetectorError as exc:
            local_ai_error = str(exc)[:128]

            logger.error(
                "[%s] Local AI discovery gagal: %s.",
                ticket_key,
                local_ai_error,
            )

        payload, irreversible_redactions = (
            _redact_high_risk_samples(
                raw_payload
            )
        )

        logger.info(
            "[%s] Deterministic privacy discovery dimulai; "
            "sample_redactions=%d.",
            ticket_key,
            irreversible_redactions,
        )

        deterministic_findings = (
            self.detector.discover(payload)
        )

        findings = _merge_findings(
            deterministic_findings,
            local_ai_findings,
        )
        findings.extend(
            _discover_verified_occurrences(
                payload,
                deterministic_findings,
            )
        )

        counts = Counter(
            finding.category
            for finding in findings
        )

        logger.info(
            "[%s] Combined sensitive findings=%d; "
            "deterministic=%d; local_ai=%d; kategori=%s.",
            ticket_key,
            len(findings),
            len(deterministic_findings),
            len(local_ai_findings),
            ", ".join(
                f"{key}:{value}"
                for key, value in sorted(counts.items())
            )
            or "tidak ada",
        )

        sanitized, replacements = self.sanitizer.apply(
            payload,
            findings,
        )

        sanitized, enforced_replacements = (
            _enforce_sensitive_paths(
                sanitized
            )
        )

        replacements += enforced_replacements

        sanitized_json = json.dumps(
            sanitized,
            ensure_ascii=False,
            indent=2,
        )

        residuals = self.validator.validate(
            sanitized_json,
            findings,
        )

        residual_categories = {
            finding.category
            for finding in residuals
        }

        if local_ai_error is not None:
            residual_categories.add(
                "LOCAL_AI_DETECTION_FAILED"
            )

        residual_categories_tuple = tuple(
            sorted(residual_categories)
        )

        safe = (
            not residuals
            and local_ai_error is None
        )

        logger.info(
            "[%s] Sanitasi locations=%d; residual=%d; "
            "local_ai_error=%s; safe_for_ai=%s.",
            ticket_key,
            replacements,
            len(residuals),
            bool(local_ai_error),
            safe,
        )

        if not safe:
            logger.error(
                "[%s] Privacy gate BLOCKED. "
                "Residual categories: %s.",
                ticket_key,
                ", ".join(
                    residual_categories_tuple
                ),
            )

        save_json_comparison(
            ticket_key,
            raw_json,
            sanitized_json,
        )

        return PrivacyResult(
            sanitized_json=sanitized_json,
            findings_count=len(findings),
            replacements_count=(
                replacements
                + irreversible_redactions
            ),
            residual_count=(
                len(residuals)
                + (1 if local_ai_error else 0)
            ),
            safe_for_ai=safe,
            categories=tuple(sorted(counts)),
            residual_categories=(
                residual_categories_tuple
            ),
        )

