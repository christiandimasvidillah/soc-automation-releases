from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from typing import Any, Iterable

import requests
import urllib3
from requests import Response

from config import SiemSettings, settings


logger = logging.getLogger(__name__)

# Elastic alert IDs pada environment ini dapat berupa SHA-1 40-hex atau 64-hex.
ALERT_ID_PATTERN = re.compile(
    r"(?<![a-fA-F0-9])([a-fA-F0-9]{40}|[a-fA-F0-9]{64})(?![a-fA-F0-9])"
)
ALERT_REDIRECT_PATTERN = re.compile(
    r"/app/security/alerts/redirect/([^/?#\s\"']+)",
    re.IGNORECASE,
)


class SiemClientError(RuntimeError):
    """Kesalahan umum ketika berkomunikasi dengan Elastic/Kibana SIEM."""


class SiemAuthenticationError(SiemClientError):
    """API key Elastic ditolak atau tidak memiliki izin yang diperlukan."""


class SiemNotFoundError(SiemClientError):
    """Resource atau alert Elastic tidak ditemukan."""


class SiemResponseError(SiemClientError):
    """Respons SIEM valid secara HTTP tetapi memiliki struktur tidak sesuai."""


class SiemClient:
    """
    Client untuk pencarian dan perubahan status alert Elastic SIEM.

    Satu requests.Session dibuat untuk setiap thread agar client yang sama
    aman dipakai oleh beberapa AI worker secara bersamaan.
    """

    def __init__(self, siem_settings: SiemSettings | None = None) -> None:
        self.settings = siem_settings or settings.siem

        self._thread_local = threading.local()
        self._sessions: list[requests.Session] = []
        self._sessions_lock = threading.Lock()

        if not self.settings.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get_session(self) -> requests.Session:
        """Mengambil atau membuat HTTP session khusus thread saat ini."""
        session = getattr(self._thread_local, "session", None)

        if session is None:
            session = requests.Session()
            session.headers.update(self.settings.headers)
            self._thread_local.session = session

            with self._sessions_lock:
                self._sessions.append(session)

        return session

    def close(self) -> None:
        """Menutup seluruh session yang dibuat oleh poller dan worker."""
        with self._sessions_lock:
            sessions = list(self._sessions)
            self._sessions.clear()

        for session in sessions:
            session.close()

    def __enter__(self) -> SiemClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        url: str,
        *,
        expected_statuses: Iterable[int],
        **kwargs: Any,
    ) -> Response:
        """Menjalankan request SIEM dengan timeout dan error yang konsisten."""
        kwargs.setdefault("timeout", self.settings.request_timeout)
        kwargs.setdefault("verify", self.settings.verify_ssl)

        try:
            response = self._get_session().request(method, url, **kwargs)
        except requests.Timeout as exc:
            raise SiemClientError(
                "Request SIEM timeout setelah "
                f"{self.settings.request_timeout} detik: {method} {url}"
            ) from exc
        except requests.SSLError as exc:
            raise SiemClientError(
                "Verifikasi sertifikat SSL SIEM gagal. Periksa sertifikat "
                "atau konfigurasi SIEM_VERIFY_SSL."
            ) from exc
        except requests.RequestException as exc:
            raise SiemClientError(
                f"Gagal terhubung ke SIEM: {method} {url}: {exc}"
            ) from exc

        if response.status_code in expected_statuses:
            return response

        message = self._extract_error_message(response)

        if response.status_code in {401, 403}:
            raise SiemAuthenticationError(
                f"SIEM menolak request ({response.status_code}): {message}"
            )

        if response.status_code == 404:
            raise SiemNotFoundError(
                f"Resource SIEM tidak ditemukan: {message}"
            )

        raise SiemClientError(
            f"Request SIEM gagal ({response.status_code}) "
            f"untuk {method} {url}: {message}"
        )

    @staticmethod
    def _extract_error_message(response: Response) -> str:
        """Mengambil detail error tanpa menyertakan API key request."""
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or "Respons SIEM tidak memiliki detail."

        if isinstance(payload, dict):
            error = payload.get("error")

            if isinstance(error, dict):
                reason = error.get("reason")
                root_cause = error.get("root_cause")

                if reason:
                    return str(reason)

                if isinstance(root_cause, list) and root_cause:
                    first_error = root_cause[0]
                    if isinstance(first_error, dict) and first_error.get("reason"):
                        return str(first_error["reason"])

            if error:
                return str(error)

            if payload.get("message"):
                return str(payload["message"])

        return str(payload)

    @staticmethod
    def find_alert_reference_fields(source: Any) -> list[str]:
        """Mengembalikan nama field yang mengandung referensi Elastic/alert."""
        if not isinstance(source, dict):
            return []

        candidates: list[str] = []
        keywords = (
            "security/alerts",
            "alerts/redirect",
            "kibana",
            "elastic",
            "alert id",
            "signal id",
        )
        for field_name, value in source.items():
            try:
                text = json.dumps(value, ensure_ascii=False, default=str).casefold()
            except (TypeError, ValueError):
                text = str(value).casefold()
            if any(keyword in text for keyword in keywords):
                candidates.append(str(field_name))
        return candidates

    @staticmethod
    def _iter_scalar_texts(source: Any):
        """Flatten nilai Jira (string/dict/list/ADF/link object) menjadi teks."""
        if source is None:
            return
        if isinstance(source, str):
            yield source
            return
        if isinstance(source, (int, float, bool)):
            yield str(source)
            return
        if isinstance(source, dict):
            # Field URL Jira kadang menyimpan URL pada atribut url/href/value.
            preferred_keys = ("value", "url", "href", "text", "content")
            visited: set[str] = set()
            for key in preferred_keys:
                if key in source:
                    visited.add(key)
                    yield from SiemClient._iter_scalar_texts(source[key])
            for key, value in source.items():
                if key not in visited:
                    yield from SiemClient._iter_scalar_texts(value)
            return
        if isinstance(source, (list, tuple, set)):
            for value in source:
                yield from SiemClient._iter_scalar_texts(value)
            return
        yield str(source)

    @staticmethod
    def describe_alert_field(source: Any) -> str:
        """Deskripsi aman untuk log tanpa membocorkan Alert ID/URL lengkap."""
        if source is None:
            return "kosong"
        texts = [text.strip() for text in SiemClient._iter_scalar_texts(source) if text.strip()]
        if not texts:
            return f"terisi type={type(source).__name__}, tetapi tanpa teks"
        lengths = sorted({len(text) for text in texts})
        return (
            f"terisi type={type(source).__name__}, "
            f"teks={len(texts)}, panjang={lengths[:5]}"
        )

    @staticmethod
    def extract_configured_alert_id(source: Any) -> str | None:
        """Ambil nilai non-kosong dari custom field Alert_ID tanpa format limit."""
        if source is None:
            return None

        for raw_text in SiemClient._iter_scalar_texts(source):
            normalized = " ".join(str(raw_text).split()).strip()
            normalized = normalized.strip('"').strip("'")
            if not normalized:
                continue
            if any(ord(char) < 32 for char in normalized):
                continue
            return normalized

        return None

    @staticmethod
    def extract_alert_id(source: Any) -> str | None:
        """
        Mengekstrak Alert ID dari string ataupun struktur custom field Jira.

        Mendukung string polos, URL redirect, dict link, list, dan Atlassian
        Document Format. URL redirect diprioritaskan sebelum generic 64-hex.
        """
        if source is None:
            return None

        texts = list(SiemClient._iter_scalar_texts(source))

        # Prioritas 1: URL Elastic redirect pada scalar mana pun.
        for text in texts:
            redirect_match = ALERT_REDIRECT_PATTERN.search(text)
            if redirect_match:
                return redirect_match.group(1).lower()

        # Prioritas 2: nilai hex 40 atau 64 karakter pada scalar mana pun.
        for text in texts:
            normalized = text.strip().strip('"').strip("'")
            if re.fullmatch(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})", normalized):
                return normalized.lower()

            generic_match = ALERT_ID_PATTERN.search(text)
            if generic_match:
                return generic_match.group(1).lower()

        # Fallback terakhir: serialisasi struktur lengkap.
        try:
            searchable_text = json.dumps(
                source,
                ensure_ascii=False,
                default=str,
            )
        except (TypeError, ValueError):
            searchable_text = str(source)

        redirect_match = ALERT_REDIRECT_PATTERN.search(searchable_text)
        if redirect_match:
            return redirect_match.group(1).lower()

        generic_match = ALERT_ID_PATTERN.search(searchable_text)
        if generic_match:
            return generic_match.group(1).lower()

        return None

    @staticmethod
    def _get_total_hits(payload: dict[str, Any]) -> int:
        """Mendukung format hits.total object maupun integer."""
        total = payload.get("hits", {}).get("total", 0)

        if isinstance(total, dict):
            total = total.get("value", 0)

        try:
            return int(total)
        except (TypeError, ValueError):
            return 0

    def search_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Mencari alert berdasarkan _id dan mengembalikan payload lengkap."""
        normalized_id = self._validate_alert_id(alert_id)

        response = self._request(
            "POST",
            self.settings.alert_search_url,
            expected_statuses={200},
            json={"query": {"match": {"_id": normalized_id}}},
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SiemResponseError(
                "Respons pencarian SIEM bukan JSON yang valid."
            ) from exc

        if not isinstance(payload, dict):
            raise SiemResponseError(
                "Respons pencarian SIEM harus berupa JSON object."
            )

        if self._get_total_hits(payload) <= 0:
            return None

        hits = payload.get("hits", {}).get("hits", [])
        if not isinstance(hits, list) or not hits:
            raise SiemResponseError(
                "SIEM melaporkan total hits, tetapi daftar hits kosong."
            )

        return payload

    @staticmethod
    def safe_alert_reference(alert_id):
        normalized = str(alert_id or "").strip()

        if not normalized:
            return "ALERT_UNAVAILABLE"

        digest = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()[:12]

        return "ALERT_" + digest

    def get_alert(
        self,
        alert_id: str,
        *,
        max_attempts: int = 2,
        retry_delay_seconds: float = 2.0,
    ) -> str | None:
        """
        Mengambil alert dengan retry untuk mengatasi delay sinkronisasi SIEM.

        Mengembalikan JSON string jika ditemukan, atau None jika seluruh
        percobaan berhasil secara HTTP tetapi alert belum tersedia.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts minimal bernilai 1.")

        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds tidak boleh negatif.")

        normalized_id = self._validate_alert_id(alert_id)

        for attempt in range(1, max_attempts + 1):
            payload = self.search_alert(normalized_id)

            if payload is not None:
                logger.info(
                    "Alert SIEM ditemukan; "
                    "alert_ref=%s, alert_id_length=%d, "
                    "attempt=%s/%s.",
                    self.safe_alert_reference(normalized_id),
                    len(normalized_id),
                    attempt,
                    max_attempts,
                )
                return json.dumps(payload, indent=2, ensure_ascii=False)

            logger.warning(
                "Alert SIEM belum ditemukan; "
                "alert_ref=%s, alert_id_length=%d, "
                "attempt=%s/%s.",
                self.safe_alert_reference(normalized_id),
                len(normalized_id),
                attempt,
                max_attempts,
            )

            if attempt < max_attempts:
                time.sleep(retry_delay_seconds)

        return None

    def close_alert(
        self,
        alert_id: str,
        *,
        closing_reason: str = "False Positive",
    ) -> bool:
        """Menutup alert SIEM sesuai kontrak API yang dipakai skrip awal."""
        normalized_id = self._validate_alert_id(alert_id)

        self._request(
            "POST",
            self.settings.alert_status_url,
            expected_statuses={200},
            json={
                "signal_ids": [normalized_id],
                "status": "closed",
                "closing_reason": closing_reason,
            },
        )

        logger.info(
            "Alert SIEM berhasil ditutup; "
            "alert_ref=%s, alert_id_length=%d, reason=%s.",
            self.safe_alert_reference(normalized_id),
            len(normalized_id),
            closing_reason,
        )
        return True

    @staticmethod
    def _validate_alert_id(alert_id: str) -> str:
        """Validasi minimal untuk opaque Alert ID dari Jira."""
        if not isinstance(alert_id, str):
            raise ValueError("alert_id harus berupa string.")

        normalized_id = " ".join(alert_id.split()).strip()
        normalized_id = normalized_id.strip('"').strip("'")
        if not normalized_id:
            raise ValueError("alert_id tidak boleh kosong.")
        if len(normalized_id) > 1024:
            raise ValueError("alert_id terlalu panjang; maksimum 1024 karakter.")
        if any(ord(char) < 32 for char in normalized_id):
            raise ValueError("alert_id mengandung karakter kontrol yang tidak valid.")

        return normalized_id
