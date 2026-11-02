from __future__ import annotations

import html
import logging
import threading
from typing import Any

import requests

from config import TelegramSettings, settings


logger = logging.getLogger(__name__)


class TelegramNotifierError(RuntimeError):
    """Notifikasi Telegram gagal dikirim."""


class TelegramNotifier:
    """Notifier Telegram yang aman digunakan oleh beberapa worker thread."""

    def __init__(
        self,
        telegram_settings: TelegramSettings | None = None,
    ) -> None:
        self.settings = telegram_settings or settings.telegram
        self._thread_local = threading.local()
        self._sessions: list[requests.Session] = []
        self._sessions_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.settings.enabled

    def _get_session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._thread_local.session = session
            with self._sessions_lock:
                self._sessions.append(session)
        return session

    def close(self) -> None:
        with self._sessions_lock:
            sessions = list(self._sessions)
            self._sessions.clear()
        for session in sessions:
            session.close()

    def send_message(self, message: str) -> bool:
        """Mengirim HTML message yang sudah dibangun oleh notifier."""
        if not self.enabled:
            logger.debug("Notifikasi Telegram dinonaktifkan.")
            return False

        if not message.strip():
            raise ValueError("Pesan Telegram tidak boleh kosong.")

        url = (
            "https://api.telegram.org/bot"
            f"{self.settings.bot_token}/sendMessage"
        )
        payload = {
            "chat_id": self.settings.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = self._get_session().post(
                url,
                json=payload,
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = ""
            if exc.response is not None:
                detail = f" | Detail: {exc.response.text[:500]}"
            raise TelegramNotifierError(
                f"Gagal mengirim notifikasi Telegram: {exc}{detail}"
            ) from exc

        return True

    def send_error_notification(
        self,
        *,
        title: str,
        ticket_key: str,
        detail: str,
    ) -> bool:
        """Mengirim notifikasi error/manual action dengan format HTML."""
        ticket_url = f"{self.settings.jira_browse_url}/{ticket_key}"
        message = (
            f"⚠️ <b>[SOC Automation - {html.escape(title)}]</b>\n"
            f"<b>Tiket:</b> "
            f"<a href=\"{html.escape(ticket_url, quote=True)}\">"
            f"{html.escape(ticket_key)}</a>\n"
            f"<b>Detail:</b> {html.escape(detail)}"
        )
        return self.send_message(message)

    def send_intake_only_notification(self, *, ticket_key: str, ticket_summary: str, status: str, assignee: str, priority: str, created_date: str, issue_type: str, detail: str) -> bool:
        ticket_url = f"{self.settings.jira_browse_url}/{ticket_key}"
        ticket_label = f"{ticket_key} - {ticket_summary}"
        message = f"""⚠️ <b>[CSOC Automation] Ticket Intake Completed — AI Analysis Disabled</b>
━━━━━━━━━━━━━━━━━━━━
📋 <b>TICKET DETAILS</b>
━━━━━━━━━━━━━━━━━━━━
🔗 Ticket: <a href="{html.escape(ticket_url, quote=True)}">{html.escape(ticket_label)}</a>
📊 Status: {html.escape(status)}
👤 Assignee: {html.escape(assignee)}
🏷️ Priority: {html.escape(priority)}
📅 Created: {html.escape(created_date)}
📂 Type: {html.escape(issue_type)}
━━━━━━━━━━━━━━━━━━━━
⚙️ <b>PIPELINE RESULT</b>
━━━━━━━━━━━━━━━━━━━━
{html.escape(detail)}"""
        return self.send_message(message)

    def send_ai_analysis_notification(
        self,
        *,
        ticket_key: str,
        ticket_summary: str,
        status: str,
        assignee: str,
        priority: str,
        created_date: str,
        issue_type: str,
        analysis_result: str,
    ) -> bool:
        """Mengirim hasil analisis AI mengikuti format file awal."""
        ticket_url = f"{self.settings.jira_browse_url}/{ticket_key}"
        ticket_label = f"{ticket_key} - {ticket_summary}"

        message = f"""⚠️ <b>[CSOC Automation] AI Analysis Completed</b>

━━━━━━━━━━━━━━━━━━━━
📋 <b>TICKET DETAILS</b>
━━━━━━━━━━━━━━━━━━━━
🔗 Ticket: <a href="{html.escape(ticket_url, quote=True)}">{html.escape(ticket_label)}</a>
📊 Status: {html.escape(status)}
👤 Assignee: {html.escape(assignee)}
🏷️ Priority: {html.escape(priority)}
📅 Created: {html.escape(created_date)}
📂 Type: {html.escape(issue_type)}

━━━━━━━━━━━━━━━━━━━━
🧠 <b>ANALYSIS RESULT</b>
━━━━━━━━━━━━━━━━━━━━
{html.escape(analysis_result)}"""

        sent = self.send_message(message)
        if sent:
            logger.info(
                "Notifikasi Telegram terkirim untuk tiket %s.",
                ticket_key,
            )
        return sent


_default_notifier: TelegramNotifier | None = None
_default_notifier_lock = threading.Lock()


def get_default_notifier() -> TelegramNotifier:
    global _default_notifier
    if _default_notifier is None:
        with _default_notifier_lock:
            if _default_notifier is None:
                _default_notifier = TelegramNotifier()
    return _default_notifier


def kirim_notifikasi_telegram(pesan: str) -> bool:
    """Compatibility wrapper untuk pesan umum dari implementasi lama."""
    # Fungsi lama menerima string HTML utuh. Gunakan langsung agar tag yang
    # dibuat ticket_processor tetap dirender, sedangkan data dinamis sudah
    # di-escape sebelum wrapper dipanggil.
    try:
        return get_default_notifier().send_message(pesan)
    except TelegramNotifierError:
        logger.exception("Gagal mengirim notifikasi Telegram umum.")
        return False


def send_ai_analysis_notification(
    ticket_key: str,
    ticket_summary: str,
    status: str,
    assignee: str,
    priority: str,
    created_date: str,
    issue_type: str,
    analysis_result: str,
) -> bool:
    """Compatibility wrapper mengikuti signature file awal."""
    try:
        return get_default_notifier().send_ai_analysis_notification(
            ticket_key=ticket_key,
            ticket_summary=ticket_summary,
            status=status,
            assignee=assignee,
            priority=priority,
            created_date=created_date,
            issue_type=issue_type,
            analysis_result=analysis_result,
        )
    except TelegramNotifierError:
        logger.exception(
            "Gagal mengirim hasil analisis Telegram untuk %s.",
            ticket_key,
        )
        return False


def send_intake_only_notification(ticket_key: str, ticket_summary: str, status: str, assignee: str, priority: str, created_date: str, issue_type: str, detail: str) -> bool:
    try:
        return get_default_notifier().send_intake_only_notification(ticket_key=ticket_key,ticket_summary=ticket_summary,status=status,assignee=assignee,priority=priority,created_date=created_date,issue_type=issue_type,detail=detail)
    except TelegramNotifierError:
        logger.exception("Gagal mengirim notifikasi intake-only untuk %s.", ticket_key)
        return False

def close_default_notifier() -> None:
    global _default_notifier
    with _default_notifier_lock:
        notifier = _default_notifier
        _default_notifier = None
    if notifier is not None:
        notifier.close()
