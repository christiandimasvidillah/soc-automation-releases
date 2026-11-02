from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Iterable

import requests
from requests import Response
from requests.auth import HTTPBasicAuth

from config import JiraSettings, settings


logger = logging.getLogger(__name__)


class JiraClientError(RuntimeError):
    """Kesalahan umum ketika berkomunikasi dengan Jira."""


class JiraAuthenticationError(JiraClientError):
    """Kredensial Jira ditolak atau tidak memiliki izin."""


class JiraNotFoundError(JiraClientError):
    """Issue atau resource Jira tidak ditemukan."""


class JiraClient:
    """Client terpusat untuk operasi Jira yang dipakai automation."""

    def __init__(self, jira_settings: JiraSettings | None = None) -> None:
        self.settings = jira_settings or settings.jira
        self.account_id = self.settings.account_id

        # Satu Session per thread agar aman ketika poller dan AI workers
        # mengakses Jira secara bersamaan.
        self._thread_local = threading.local()
        self._sessions: list[requests.Session] = []
        self._sessions_lock = threading.Lock()
        self._field_map: dict[str, str] | None = None
        self._field_map_lock = threading.Lock()

    def _get_session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.auth = HTTPBasicAuth(
                self.settings.email,
                self.settings.api_token,
            )
            session.headers.update(self.settings.headers)
            self._thread_local.session = session

            with self._sessions_lock:
                self._sessions.append(session)

        return session

    def close(self) -> None:
        """Menutup seluruh connection pool yang dibuat oleh tiap thread."""
        with self._sessions_lock:
            sessions = list(self._sessions)
            self._sessions.clear()

        for session in sessions:
            session.close()

    def __enter__(self) -> JiraClient:
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
        """Menjalankan HTTP request dengan timeout dan error konsisten."""
        kwargs.setdefault("timeout", self.settings.request_timeout)

        try:
            response = self._get_session().request(method, url, **kwargs)
        except requests.Timeout as exc:
            raise JiraClientError(
                f"Request Jira timeout setelah "
                f"{self.settings.request_timeout} detik: {method} {url}"
            ) from exc
        except requests.RequestException as exc:
            raise JiraClientError(
                f"Gagal terhubung ke Jira: {method} {url}: {exc}"
            ) from exc

        if response.status_code in expected_statuses:
            return response

        message = self._extract_error_message(response)

        if response.status_code in {401, 403}:
            raise JiraAuthenticationError(
                f"Jira menolak request ({response.status_code}): {message}"
            )

        if response.status_code == 404:
            raise JiraNotFoundError(f"Resource Jira tidak ditemukan: {message}")

        raise JiraClientError(
            f"Request Jira gagal ({response.status_code}) "
            f"untuk {method} {url}: {message}"
        )

    @staticmethod
    def _extract_error_message(response: Response) -> str:
        """Mengambil pesan error Jira tanpa membocorkan credential request."""
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or "Respons Jira tidak memiliki detail."

        messages: list[str] = []

        error_messages = payload.get("errorMessages", [])
        if isinstance(error_messages, list):
            messages.extend(str(item) for item in error_messages)

        errors = payload.get("errors", {})
        if isinstance(errors, dict):
            messages.extend(
                f"{field}: {detail}" for field, detail in errors.items()
            )

        if payload.get("message"):
            messages.append(str(payload["message"]))

        return "; ".join(messages) or str(payload)

    @staticmethod
    def parse_jira_datetime(value: str) -> datetime:
        """Mengubah timestamp ISO Jira menjadi datetime timezone-aware."""
        normalized = value.strip()

        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise JiraClientError(
                f"Format timestamp Jira tidak dikenali: {value}"
            ) from exc

        if parsed.tzinfo is None:
            raise JiraClientError(
                f"Timestamp Jira tidak memiliki timezone: {value}"
            )

        return parsed

    def search_tickets(
        self,
        *,
        jql: str | None = None,
        fields: list[str] | None = None,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """Mencari tiket Jira dan menangani pagination otomatis."""
        if max_results < 1:
            raise ValueError("max_results minimal bernilai 1.")

        # Alert URL/ID dapat berada pada custom field Jira yang berbeda.
        # Default ke *all agar extractor menerima seluruh field issue.
        selected_fields = fields if fields is not None else ["*all"]

        issues: list[dict[str, Any]] = []
        next_page_token: str | None = None

        while True:
            payload: dict[str, Any] = {
                "jql": jql or self.settings.polling_jql,
                "fields": selected_fields,
                "maxResults": min(max_results, 100),
            }

            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = self._request(
                "POST",
                self.settings.search_api_url,
                expected_statuses={200},
                json=payload,
            )
            data = response.json()
            page_issues = data.get("issues", [])

            if not isinstance(page_issues, list):
                raise JiraClientError(
                    "Respons pencarian Jira tidak berisi list 'issues'."
                )

            issues.extend(page_issues)

            if len(issues) >= max_results:
                return issues[:max_results]

            next_page_token = data.get("nextPageToken")
            if not next_page_token or data.get("isLast") is True:
                return issues

    def search_new_tickets(
        self,
        *,
        created_after: datetime | None = None,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Mengambil tiket kandidat lalu memfilter berdasarkan waktu pembuatan.

        Deduplikasi utama tetap harus dilakukan worker manager melalui
        koleksi in-flight/processed agar tiket tidak diproses dua kali.
        """
        issues = self.search_tickets(max_results=max_results)

        if created_after is None:
            return issues

        if created_after.tzinfo is None:
            raise ValueError("created_after harus timezone-aware.")

        new_issues: list[dict[str, Any]] = []

        for issue in issues:
            created_value = issue.get("fields", {}).get("created")
            if not created_value:
                logger.warning(
                    "Tiket %s tidak memiliki field created.",
                    issue.get("key", "UNKNOWN"),
                )
                continue

            if self.parse_jira_datetime(created_value) > created_after:
                new_issues.append(issue)

        new_issues.sort(
            key=lambda issue: self.parse_jira_datetime(
                issue["fields"]["created"]
            )
        )
        return new_issues

    def get_field_map(self, *, force_refresh: bool = False) -> dict[str, str]:
        """Memetakan nama field Jira (casefold) ke ID internal customfield_* ."""
        with self._field_map_lock:
            if self._field_map is not None and not force_refresh:
                return dict(self._field_map)

        response = self._request(
            "GET",
            f"{self.settings.base_url}/rest/api/3/field",
            expected_statuses={200},
        )
        payload = response.json()
        if not isinstance(payload, list):
            raise JiraClientError("Respons metadata field Jira bukan list.")

        mapping: dict[str, str] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            field_id = str(item.get("id") or "").strip()
            field_name = str(item.get("name") or "").strip()
            if field_id and field_name:
                mapping[field_name.casefold()] = field_id

        with self._field_map_lock:
            self._field_map = mapping
        return dict(mapping)

    def get_field_id_by_names(self, *names: str) -> str | None:
        mapping = self.get_field_map()
        for name in names:
            field_id = mapping.get(name.strip().casefold())
            if field_id:
                return field_id
        return None

    def get_issue_for_analysis(self, ticket_key: str) -> dict[str, Any]:
        """Ambil issue terbaru beserta seluruh field dan metadata nama field."""
        issue = self.get_issue(ticket_key, fields=["*all"])
        fields = issue.get("fields", {})
        field_map = self.get_field_map()
        id_to_name = {field_id: name for name, field_id in field_map.items()}

        named_fields: dict[str, Any] = {}
        for field_id, value in fields.items():
            display_name = id_to_name.get(field_id, field_id)
            named_fields[display_name] = value

        issue["named_fields"] = named_fields
        return issue

    def get_issue(
        self,
        ticket_key: str,
        *,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Mengambil detail terbaru sebuah tiket Jira."""
        params: dict[str, str] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._request(
            "GET",
            f"{self.settings.issue_api_url}/{ticket_key}",
            expected_statuses={200},
            params=params,
        )
        return response.json()

    def get_current_status(self, ticket_key: str) -> str:
        """Mengambil nama status Jira terbaru."""
        issue = self.get_issue(ticket_key, fields=["status"])
        return issue.get("fields", {}).get("status", {}).get("name", "Unknown")

    def assign_to_me(self, ticket_key: str) -> bool:
        """Assign tiket ke account yang dikonfigurasi pada JIRA_ACCOUNT_ID."""
        self._request(
            "PUT",
            f"{self.settings.issue_api_url}/{ticket_key}/assignee",
            expected_statuses={204},
            json={"accountId": self.account_id},
        )
        logger.info("Tiket %s berhasil di-assign ke account automation.", ticket_key)
        return True

    def get_transitions(self, ticket_key: str) -> list[dict[str, Any]]:
        """Mengambil seluruh transisi yang tersedia dari status saat ini."""
        response = self._request(
            "GET",
            f"{self.settings.issue_api_url}/{ticket_key}/transitions",
            expected_statuses={200},
        )
        transitions = response.json().get("transitions", [])

        if not isinstance(transitions, list):
            raise JiraClientError(
                f"Respons transition untuk {ticket_key} bukan sebuah list."
            )

        return transitions

    def transition(
        self,
        ticket_key: str,
        target_status_name: str,
    ) -> bool:
        """
        Mencari transition ID secara dinamis lalu menjalankan transisinya.

        Mengembalikan True jika status sudah sesuai atau transisi berhasil,
        dan False jika workflow saat ini tidak menyediakan status tujuan.
        """
        current_status = self.get_current_status(ticket_key)
        if current_status.casefold() == target_status_name.casefold():
            logger.info(
                "Tiket %s sudah berada pada status %s.",
                ticket_key,
                target_status_name,
            )
            return True

        transitions = self.get_transitions(ticket_key)
        target_transition_id: str | None = None

        for transition in transitions:
            destination = transition.get("to", {}).get("name", "")
            if destination.casefold() == target_status_name.casefold():
                target_transition_id = str(transition["id"])
                break

        if target_transition_id is None:
            available = [
                item.get("to", {}).get("name", "Unknown")
                for item in transitions
            ]
            logger.warning(
                "Transisi %s -> %s tidak tersedia. Pilihan: %s",
                ticket_key,
                target_status_name,
                available,
            )
            return False

        self._request(
            "POST",
            f"{self.settings.issue_api_url}/{ticket_key}/transitions",
            expected_statuses={204},
            json={"transition": {"id": target_transition_id}},
        )
        logger.info(
            "Status tiket %s berhasil diubah menjadi %s.",
            ticket_key,
            target_status_name,
        )
        return True

    def update_field(
        self,
        ticket_key: str,
        field_id: str,
        value: Any,
    ) -> bool:
        """Memperbarui satu field Jira."""
        self._request(
            "PUT",
            f"{self.settings.issue_api_url}/{ticket_key}",
            expected_statuses={204},
            json={"fields": {field_id: value}},
        )
        logger.info("Field %s pada %s berhasil diperbarui.", field_id, ticket_key)
        return True

    def update_analysis_result(
        self,
        ticket_key: str,
        analysis_result: str,
    ) -> bool:
        """Mengisi custom field hasil analisis AI."""
        if not analysis_result.strip():
            raise ValueError("analysis_result tidak boleh kosong.")

        return self.update_field(
            ticket_key,
            self.settings.analysis_field_id,
            analysis_result.strip(),
        )

    def get_notification_data(self, ticket_key: str) -> dict[str, str]:
        """Mengambil data Jira terbaru yang diperlukan notifikasi Telegram."""
        issue = self.get_issue(
            ticket_key,
            fields=[
                "summary",
                "status",
                "assignee",
                "priority",
                "created",
                "issuetype",
            ],
        )
        fields = issue.get("fields", {})
        assignee = fields.get("assignee") or {}

        return {
            "ticket_key": ticket_key,
            "ticket_summary": fields.get("summary") or "",
            "status": fields.get("status", {}).get("name", "Unknown"),
            "assignee": assignee.get("displayName", "Unassigned"),
            "priority": fields.get("priority", {}).get("name", "Unknown"),
            "created_date": (fields.get("created") or "")[:10],
            "issue_type": fields.get("issuetype", {}).get("name", "Unknown"),
        }
