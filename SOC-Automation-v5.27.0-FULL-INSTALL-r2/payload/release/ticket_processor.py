from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from dataclasses import dataclass
from html import escape
from typing import Any, Callable, Literal

from config import Settings, settings
from privacy_manager import PrivacyManager
from gemini_manager import dapatkan_analisis_ai
from jira_client import JiraClient, JiraClientError
from prompt_builder import PromptBuilderError, build_analysis_prompt, validate_analysis_result
from output_privacy import sanitize_ai_output
from siem_client import SiemClient, SiemClientError
from telegram_notifier import kirim_notifikasi_telegram, send_ai_analysis_notification
from runtime_events import emit_ticket_event
from sharing_allowlist import evaluate_alert
from feature_control import FeatureControl


logger = logging.getLogger(__name__)

def _automation_root() -> Path:
    """Resolve installation root without depending on PrivacyManager internals."""
    return Path(
        os.getenv(
            "SOC_AUTOMATION_ROOT",
            str(Path.home() / "SOC-Automation"),
        )
    ).expanduser().resolve()

TicketOutcome = Literal[
    "false_positive_closed",
    "false_positive_transition_failed",
    "waiting_non_false_positive",
    "missing_alert_id",
    "siem_data_unavailable",
    "ai_failed",
    "processing_failed",
    "sanitization_failed",
    "intake_only_waiting",
]


@dataclass(frozen=True)
class TicketProcessingResult:
    ticket_key: str
    outcome: TicketOutcome
    analysis_result: str | None = None
    alert_id: str | None = None
    detail: str | None = None


class TicketProcessor:
    """
    Menganalisis tiket yang sudah dipastikan berada di Waiting Confirmation.

    False Positive: Waiting -> False Incident -> Done, lalu tutup alert SIEM.
    Selain False Positive: tetap Waiting dan kirim notifikasi Telegram.
    """

    AI_FAILURE_SENTINEL = "AI_ANALYSIS_FAILED"

    def __init__(
        self,
        *,
        jira_client: JiraClient,
        siem_client: SiemClient,
        ai_client: Any,
        app_settings: Settings | None = None,
        ai_analyzer: Callable[[Any, str], str] = dapatkan_analisis_ai,
        error_notifier: Callable[[str], Any] = kirim_notifikasi_telegram,
        analysis_notifier: Callable[..., Any] = send_ai_analysis_notification,
        transition_sync_delay_seconds: float = 1.0,
        ticket_lock_store=None,
    ) -> None:
        self.jira = jira_client
        self.siem = siem_client
        self.ai_client = ai_client
        self.settings = app_settings or settings
        self.ai_analyzer = ai_analyzer
        self.error_notifier = error_notifier
        self.analysis_notifier = analysis_notifier
        self.transition_sync_delay_seconds = max(0.0, transition_sync_delay_seconds)
        self.ticket_locks = ticket_lock_store
        self.feature_control = FeatureControl(_automation_root())

    def process_analysis(self, issue: dict[str, Any]) -> TicketProcessingResult:
        ticket_key, summary, fields = self._extract_issue_context(issue)
        alert_id: str | None = None
        logger.info("[%s] AI analysis dimulai.", ticket_key)
        feature_snapshot = self.feature_control.snapshot()
        effective = feature_snapshot["effective"]
        logger.info("[%s] Feature profile=%s revision=%s.", ticket_key, feature_snapshot["profile"], feature_snapshot["revision"])
        if not effective["siem_retrieval"]["effective"]:
            return self.process_intake_only(issue, feature_snapshot=feature_snapshot)
        emit_ticket_event(ticket_key,"TICKET_DETECTED","PASS")
        emit_ticket_event(ticket_key,"ALERT_ID_WAIT","RUNNING")

        try:
            alert_id, fresh_issue, source_name = self._wait_for_alert_id(
                ticket_key
            )
            fresh_fields = fresh_issue.get("fields", {})
            named_fields = fresh_issue.get("named_fields", {})
            summary = str(fresh_fields.get("summary") or summary).strip()

            if not alert_id:
                reference_fields = self.siem.find_alert_reference_fields(
                    named_fields
                )
                field_names = (
                    ", ".join(reference_fields)
                    if reference_fields
                    else "tidak ada"
                )
                detail = (
                    "Alert ID belum ditemukan setelah "
                    f"{self.settings.automation.alert_field_max_attempts} "
                    "percobaan. Field yang tampak memuat referensi Elastic: "
                    f"{field_names}."
                )
                return self._handle_failure(
                    ticket_key,
                    "missing_alert_id",
                    detail,
                )

            emit_ticket_event(ticket_key,"ALERT_ID_RESOLVED","PASS")
            emit_ticket_event(ticket_key,"SIEM_ALERT_FETCH","RUNNING")
            logger.info(
                "[%s] Alert ID siap digunakan dari %s.",
                ticket_key,
                source_name,
            )

            logger.info(
                "[%s] Mengambil alert SIEM; "
                "alert_ref=%s, alert_id_length=%d.",
                ticket_key,
                self.siem.safe_alert_reference(alert_id),
                len(alert_id),
            )
            alert_text = self.siem.get_alert(
                alert_id,
                max_attempts=2,
                retry_delay_seconds=2.0,
            )
            if not alert_text:
                return self._handle_failure(
                    ticket_key, "siem_data_unavailable",
                    "Alert SIEM tidak ditemukan setelah seluruh percobaan.",
                    alert_id,
                )

            logger.info("[%s] Discovery dan sanitasi privacy dimulai.", ticket_key)
            privacy_manager = PrivacyManager(enable_local_ai=effective["local_ai_detection"]["effective"])
            privacy_result = privacy_manager.prepare_payload(
                ticket_key=ticket_key,
                raw_json=alert_text,
            )
            if not privacy_result.safe_for_ai:
                categories = ", ".join(privacy_result.residual_categories)
                return self._handle_failure(
                    ticket_key,
                    "sanitization_failed",
                    "Privacy gate memblokir payload; residual sensitive data: "
                    f"{privacy_result.residual_count}. Kategori: {categories}.",
                    alert_id,
                )
            emit_ticket_event(ticket_key,"LOCAL_AI_DETECTION","PASS",findings_count=privacy_result.findings_count)
            emit_ticket_event(ticket_key,"DETERMINISTIC_SANITIZATION","PASS",replacements_count=privacy_result.replacements_count)
            emit_ticket_event(ticket_key,"PRIVACY_GATE","PASS" if privacy_result.safe_for_ai else "BLOCKED",residual_count=privacy_result.residual_count)
            safe_payload = privacy_result.sanitized_json
            logger.info(
                "[%s] Privacy gate PASSED; payload aman dikirim ke Gemini.",
                ticket_key,
            )

            allowlist = evaluate_alert(_automation_root(), alert_text, summary) if effective["sharing_allowlist"]["effective"] else {"matched": False, "reason": "disabled_by_feature_policy"}
            if allowlist.get("matched"):
                emit_ticket_event(ticket_key,"SHARING_ALLOWLIST_MATCH","PASS",decision="APPROVED_SHARING_ALLOWLIST")
                raw_result = "FALSE POSITIVE: The structured file-sharing targets belong to an approved internal/vendor collaboration allowlist entry. All targets are approved and the operation is AddedToSecureLink. Reason code: APPROVED_SHARING_ALLOWLIST."
            else:
                emit_ticket_event(ticket_key,"SHARING_ALLOWLIST_MATCH","SKIPPED",decision=allowlist.get("reason"))
                if not effective["gemini_analysis"]["effective"]:
                    raw_result = "MANUAL REVIEW REQUIRED: Gemini analysis is disabled by the active feature profile. SIEM evidence passed the configured privacy controls and the ticket remains available for analyst review."
                    emit_ticket_event(ticket_key,"GEMINI_ANALYSIS","SKIPPED",decision="DISABLED_BY_FEATURE_POLICY")
                else:
                    prompt = build_analysis_prompt(ticket_key=ticket_key,summary=summary,safe_payload=safe_payload)
                    raw_result = self.ai_analyzer(self.ai_client, prompt)
            if raw_result == self.AI_FAILURE_SENTINEL:
                return self._handle_failure(
                    ticket_key, "ai_failed",
                    "Seluruh model AI gagal atau terkena limit; tiket tetap Waiting untuk review manual.",
                    alert_id,
                )

            analysis_result = validate_analysis_result(raw_result)
            privacy_output = sanitize_ai_output(analysis_result)
            analysis_result = privacy_output.text
            if privacy_output.withheld:
                logger.warning("[%s] AI output ditahan oleh output privacy gate.", ticket_key)
            elif privacy_output.replacements:
                logger.info("[%s] AI output diminimalkan; replacements=%d.", ticket_key, privacy_output.replacements)
            self.jira.update_analysis_result(ticket_key, analysis_result)
            logger.info("[%s] Analysis Result berhasil disimpan ke Jira.", ticket_key)

            fp_allowed, decision_reason, ambiguity_flags = self._classify_fp_decision(
                analysis_result
            )
            logger.info(
                "[%s] AI decision audit: auto_close_allowed=%s reason=%s flags=%s parser_version=3.",
                ticket_key,
                fp_allowed,
                decision_reason,
                list(ambiguity_flags),
            )
            if fp_allowed:
                logger.info("[%s] Kesimpulan AI: FALSE POSITIVE.", ticket_key)
                outcome = self._complete_false_positive(ticket_key, alert_id)
            else:
                logger.info(
                    "[%s] Kesimpulan AI bukan False Positive; status tetap %s.",
                    ticket_key,
                    self.settings.jira.waiting_confirmation_status,
                )
                emit_ticket_event(ticket_key,"JIRA_STATUS_OBSERVED","PASS",jira_status=self.settings.jira.waiting_confirmation_status)
                outcome = "waiting_non_false_positive"

            self._wait_for_jira_sync()
            self._send_analysis_notification(ticket_key, issue, analysis_result)
            emit_ticket_event(ticket_key,"TELEGRAM_NOTIFICATION","PASS")
            emit_ticket_event(ticket_key,"PROCESSING_COMPLETE","COMPLETED",outcome=outcome)
            return TicketProcessingResult(
                ticket_key=ticket_key,
                outcome=outcome,
                analysis_result=analysis_result,
                alert_id=alert_id,
            )

        except (JiraClientError, SiemClientError, PromptBuilderError, ValueError) as exc:
            logger.exception("[%s] Processing gagal.", ticket_key)
            return self._handle_failure(
                ticket_key,
                "processing_failed",
                f"{type(exc).__name__}: {exc}",
                alert_id,
            )
        except Exception as exc:
            logger.exception("[%s] Unexpected processing error.", ticket_key)
            return self._handle_failure(
                ticket_key,
                "processing_failed",
                f"{type(exc).__name__}: {exc}",
                alert_id,
            )

    def process_intake_only(self, issue: dict[str, Any], feature_snapshot: dict[str, Any] | None = None) -> TicketProcessingResult:
        ticket_key, summary, _fields = self._extract_issue_context(issue)
        snapshot = feature_snapshot or self.feature_control.snapshot()
        emit_ticket_event(ticket_key, "FEATURE_CONFIG_SNAPSHOT", "PASS", decision=snapshot.get("profile"))
        emit_ticket_event(ticket_key, "SIEM_ALERT_FETCH", "SKIPPED", decision="DISABLED_BY_FEATURE_POLICY")
        emit_ticket_event(ticket_key, "LOCAL_AI_DETECTION", "SKIPPED", decision="DISABLED_BY_FEATURE_POLICY")
        emit_ticket_event(ticket_key, "GEMINI_ANALYSIS", "SKIPPED", decision="DISABLED_BY_FEATURE_POLICY")
        result = "MANUAL REVIEW REQUIRED: AI and SIEM analysis are disabled by the active automation profile. No raw SIEM JSON was retrieved and no AI provider was called."
        if snapshot["effective"]["telegram_notification"]["effective"]:
            self._send_intake_notification(ticket_key, issue, result)
            emit_ticket_event(ticket_key, "TELEGRAM_NOTIFICATION", "PASS")
        emit_ticket_event(ticket_key, "PROCESSING_COMPLETE", "COMPLETED", outcome="intake_only_waiting")
        return TicketProcessingResult(ticket_key=ticket_key, outcome="intake_only_waiting", analysis_result=result, detail=f"profile={snapshot.get('profile')} revision={snapshot.get('revision')}")

    def _send_intake_notification(self, ticket_key: str, fallback_issue: dict[str, Any], detail: str) -> None:
        try:
            data = self.jira.get_notification_data(ticket_key)
        except JiraClientError:
            fields = fallback_issue.get("fields", {})
            assignee = fields.get("assignee") or {}
            data = {"ticket_key": ticket_key, "ticket_summary": fields.get("summary") or "", "status": fields.get("status", {}).get("name", "Waiting for User Confirmation"), "assignee": assignee.get("displayName", "Unassigned"), "priority": fields.get("priority", {}).get("name", "Unknown"), "created_date": (fields.get("created") or "")[:10], "issue_type": fields.get("issuetype", {}).get("name", "Unknown")}
        try:
            from telegram_notifier import send_intake_only_notification
            send_intake_only_notification(**data, detail=detail)
        except Exception:
            logger.exception("[%s] Gagal mengirim notifikasi intake-only.", ticket_key)

    def _wait_for_alert_id(
        self,
        ticket_key: str,
    ) -> tuple[str | None, dict[str, Any], str]:
        """
        Membaca ulang custom field Jira sampai Alert ID tersedia.

        Retry hanya menahan AI worker terkait; poller utama tetap berjalan.
        """
        max_attempts = self.settings.automation.alert_field_max_attempts
        retry_seconds = self.settings.automation.alert_field_retry_seconds
        latest_issue: dict[str, Any] = {}

        for attempt in range(1, max_attempts + 1):
            logger.info(
                "[%s] Membaca Alert ID dari Jira, percobaan %d/%d.",
                ticket_key,
                attempt,
                max_attempts,
            )

            latest_issue = self.jira.get_issue_for_analysis(ticket_key)
            fields = latest_issue.get("fields", {})
            named_fields = latest_issue.get("named_fields", {})

            configured_alert_id = fields.get(
                self.settings.jira.alert_id_field_id
            )
            configured_alert_link = fields.get(
                self.settings.jira.alert_link_field_id
            )

            # Alert_ID custom field adalah sumber otoritatif. Jika terisi,
            # gunakan nilainya langsung tanpa syarat panjang atau hexadecimal.
            alert_id = self.siem.extract_configured_alert_id(
                configured_alert_id
            )
            if alert_id:
                logger.info(
                    "[%s] Alert ID diambil langsung dari %s pada "
                    "percobaan %d/%d (panjang=%d).",
                    ticket_key,
                    self.settings.jira.alert_id_field_id,
                    attempt,
                    max_attempts,
                    len(alert_id),
                )
                return (
                    alert_id,
                    latest_issue,
                    self.settings.jira.alert_id_field_id,
                )

            # Fallback hanya dipakai apabila custom field Alert_ID kosong.
            extraction_sources = (
                (
                    self.settings.jira.alert_link_field_id,
                    configured_alert_link,
                ),
                ("metadata nama field Jira", named_fields),
                ("fallback seluruh field Jira", fields),
            )

            for source_name, source_value in extraction_sources:
                alert_id = self.siem.extract_alert_id(source_value)
                if alert_id:
                    logger.info(
                        "[%s] Alert ID ditemukan dari %s pada "
                        "percobaan %d/%d.",
                        ticket_key,
                        source_name,
                        attempt,
                        max_attempts,
                    )
                    return alert_id, latest_issue, source_name

            # Informasikan keberadaan field tanpa mencetak nilai sensitif.
            logger.warning(
                "[%s] Custom field Alert_ID kosong dan fallback belum menghasilkan Alert ID "
                "pada percobaan %d/%d (%s: %s | %s: %s).",
                ticket_key,
                attempt,
                max_attempts,
                self.settings.jira.alert_id_field_id,
                self.siem.describe_alert_field(configured_alert_id),
                self.settings.jira.alert_link_field_id,
                self.siem.describe_alert_field(configured_alert_link),
            )

            if attempt < max_attempts:
                logger.info(
                    "[%s] Menunggu %.1f detik sebelum membaca ulang Jira.",
                    ticket_key,
                    retry_seconds,
                )
                time.sleep(retry_seconds)

        return None, latest_issue, "tidak ditemukan"

    @staticmethod
    def _extract_issue_context(issue: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        if not isinstance(issue, dict):
            raise ValueError("issue harus berupa dictionary.")
        ticket_key = str(issue.get("key") or "").strip()
        fields = issue.get("fields")
        if not ticket_key or not isinstance(fields, dict):
            raise ValueError("Issue Jira tidak memiliki key/fields yang valid.")
        summary = str(fields.get("summary") or "SIEM Alert").strip()
        return ticket_key, summary, fields

    @staticmethod
    def _classify_fp_decision(result: str) -> tuple[bool, str, tuple[str, ...]]:
        """Return a safe decision, reason code, and non-sensitive ambiguity flags."""
        normalized = " ".join(result.casefold().split())
        if not normalized.startswith("false positive:"):
            reason = (
                "manual_review_prefix"
                if normalized.startswith("manual review required:")
                else "missing_false_positive_prefix"
            )
            return False, reason, ()

        ambiguity_patterns = (
            ("manual_validation", r"\bmanual (?:validation|review)\b"),
            ("review_required", r"\brequires? (?:manual )?(?:validation|review|investigation)\b"),
            ("further_review", r"\b(?:further|additional) (?:validation|review|investigation)\b"),
            ("insufficient_evidence", r"\binsufficient (?:evidence|data|information)\b"),
            ("missing_evidence", r"\b(?:missing|absent|absence of|without) (?:specific )?(?:evidence|data|information)\b"),
            ("unable_to_confirm", r"\b(?:cannot|can't|unable to|could not) (?:be )?(?:confirm|determine|verify|classify)\w*\b"),
            ("uncertain_language", r"\b(?:may|might|possibly|potentially|unclear|ambiguous|unknown|inconclusive)\b"),
            ("conditional_false_positive", r"\bwhether\b.*\bfalse positive\b"),
            ("missing_object_evidence", r"\bno (?:specific )?(?:file|object|activity) evidence\b"),
        )
        flags = tuple(
            code for code, pattern in ambiguity_patterns
            if re.search(pattern, normalized)
        )
        if flags:
            return False, "ambiguity_detected", flags
        return True, "explicit_false_positive", ()

    @staticmethod
    def _is_false_positive(result: str) -> bool:
        """Compatibility wrapper around the auditable fail-closed decision gate."""
        allowed, _, _ = TicketProcessor._classify_fp_decision(result)
        return allowed

    def _complete_false_positive(self, ticket_key: str, alert_id: str) -> TicketOutcome:
        moved_false = self.jira.transition(
            ticket_key,
            self.settings.jira.false_incident_status,
        )
        if not moved_false:
            detail = (
                f"Transisi ke {self.settings.jira.false_incident_status} tidak tersedia; "
                "tiket tidak dilanjutkan ke Done."
            )
            logger.warning("[%s] %s", ticket_key, detail)
            self._notify_error("FALSE POSITIVE TRANSITION FAILED", ticket_key, detail)
            return "false_positive_transition_failed"

        logger.info(
            "[%s] Berhasil ditransisikan ke %s.",
            ticket_key,
            self.settings.jira.false_incident_status,
        )
        emit_ticket_event(ticket_key,"JIRA_STATUS_TRANSITION","PASS",jira_status=self.settings.jira.false_incident_status)
        self._wait_for_jira_sync()

        moved_done = self.jira.transition(ticket_key, self.settings.jira.done_status)
        if not moved_done:
            detail = f"Transisi ke {self.settings.jira.done_status} tidak tersedia."
            logger.warning("[%s] %s", ticket_key, detail)
            self._notify_error("DONE TRANSITION FAILED", ticket_key, detail)
            return "false_positive_transition_failed"

        logger.info("[%s] Berhasil ditransisikan ke %s.", ticket_key, self.settings.jira.done_status)
        emit_ticket_event(ticket_key,"JIRA_STATUS_TRANSITION","PASS",jira_status=self.settings.jira.done_status)

        try:
            self.siem.close_alert(alert_id, closing_reason="False Positive")
            logger.info("[%s] Alert Elastic SIEM berhasil ditutup.", ticket_key)
        except SiemClientError as exc:
            logger.exception("[%s] Gagal menutup alert SIEM.", ticket_key)
            self._notify_error("SIEM CLOSE FAILED", ticket_key, str(exc))

        return "false_positive_closed"

    def _handle_failure(
        self,
        ticket_key: str,
        outcome: TicketOutcome,
        detail: str,
        alert_id: str | None = None,
    ) -> TicketProcessingResult:
        logger.warning("[%s] %s", ticket_key, detail)
        self._notify_error(outcome.replace("_", " ").upper(), ticket_key, detail)
        return TicketProcessingResult(
            ticket_key=ticket_key,
            outcome=outcome,
            alert_id=alert_id,
            detail=detail,
        )

    def _notify_error(self, title: str, ticket_key: str, detail: str) -> None:
        failure_code = str(
            title or "PROCESSING FAILED"
        ).strip().upper()[:128]
        if self.ticket_locks is not None:
            try:
                should_send = (
                    self.ticket_locks.claim_failure_notification(
                        ticket_key,
                        failure_code,
                        cooldown_seconds=1800.0,
                    )
                )
            except Exception:
                logger.exception(
                    "[%s] Gagal memeriksa deduplikasi "
                    "notifikasi; notifikasi ditahan.",
                    ticket_key,
                )
                return
            if not should_send:
                logger.info(
                    "[%s] Notifikasi error duplikat "
                    "dilewati; code=%s.",
                    ticket_key,
                    failure_code,
                )
                return
        ticket_url = f"{self.settings.jira.browse_url}/{ticket_key}"
        message = (
            f"⚠️ <b>[SOC Automation - {escape(title)}]</b>\n"
            f"<b>Tiket:</b> <a href='{ticket_url}'>{escape(ticket_key)}</a>\n"
            f"<b>Detail:</b> {escape(detail)}"
        )
        try:
            self.error_notifier(message)
        except Exception:
            logger.exception("[%s] Gagal mengirim notifikasi error.", ticket_key)

    def _send_analysis_notification(
        self,
        ticket_key: str,
        fallback_issue: dict[str, Any],
        analysis_result: str,
    ) -> None:
        try:
            data = self.jira.get_notification_data(ticket_key)
        except JiraClientError:
            fields = fallback_issue.get("fields", {})
            assignee = fields.get("assignee") or {}
            data = {
                "ticket_key": ticket_key,
                "ticket_summary": fields.get("summary") or "",
                "status": fields.get("status", {}).get("name", "Updated"),
                "assignee": assignee.get("displayName", "Unassigned"),
                "priority": fields.get("priority", {}).get("name", "Unknown"),
                "created_date": (fields.get("created") or "")[:10],
                "issue_type": fields.get("issuetype", {}).get("name", "Unknown"),
            }
        try:
            self.analysis_notifier(**data, analysis_result=analysis_result)
        except Exception:
            logger.exception("[%s] Gagal mengirim notifikasi hasil AI.", ticket_key)

    def _wait_for_jira_sync(self) -> None:
        if self.transition_sync_delay_seconds > 0:
            time.sleep(self.transition_sync_delay_seconds)
