from __future__ import annotations

import logging
import os
from pathlib import Path
import uuid
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from jira_client import JiraClient, JiraClientError
from health_manager import HealthManager
from ticket_lock import TicketLockStore
from role_gate import ActiveSlotGate
from ticket_processor import TicketProcessingResult, TicketProcessor
from runtime_events import emit_ticket_event
from intake_circuit_breaker import IntakeCircuitBreaker
from operational_alerts import OperationalAlertManager
from feature_control import FeatureControl
from telegram_notifier import kirim_notifikasi_telegram


logger = logging.getLogger(__name__)


class AutomationManager:
    """
    Menjalankan polling Jira dan worker analisis secara independen.

    Alur intake tetap berjalan pada polling thread:
    1. Temukan tiket kandidat.
    2. Claim tiket agar tidak diduplikasi.
    3. Assign tiket ke akun automation.
    4. Transisikan tiket ke L1 Analysis.
    5. Submit pekerjaan berat ke ThreadPoolExecutor.

    Karena assign dan transisi awal tidak dilakukan oleh AI worker, tiket baru
    tetap dapat masuk ke L1 Analysis meskipun seluruh AI worker sedang sibuk.
    """

    def __init__(
        self,
        *,
        jira_client: JiraClient,
        ticket_processor: TicketProcessor,
        max_workers: int,
        polling_interval_seconds: int,
        recent_ticket_lookback_minutes: int = 5,
        shutdown_wait_for_workers: bool = True,
        max_search_results: int = 100,
        health_manager: HealthManager | None = None,
        ticket_lock_store: TicketLockStore | None = None,
        role_gate: ActiveSlotGate | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers minimal bernilai 1.")
        if polling_interval_seconds < 1:
            raise ValueError(
                "polling_interval_seconds minimal bernilai 1."
            )
        if recent_ticket_lookback_minutes < 1:
            raise ValueError(
                "recent_ticket_lookback_minutes minimal bernilai 1."
            )
        if max_search_results < 1:
            raise ValueError("max_search_results minimal bernilai 1.")

        self.jira = jira_client
        self.ticket_processor = ticket_processor
        self.max_workers = max_workers
        self.polling_interval_seconds = polling_interval_seconds
        self.recent_ticket_lookback_minutes = recent_ticket_lookback_minutes
        self.shutdown_wait_for_workers = shutdown_wait_for_workers
        self.max_search_results = max_search_results
        self.health = health_manager
        self.ticket_locks = ticket_lock_store
        self.role_gate = role_gate
        self.instance_id = f"{os.getpid()}-{uuid.uuid4().hex[:12]}"
        self.intake_breaker = IntakeCircuitBreaker(threshold=3, cooldown_seconds=300)
        root = Path(os.getenv("SOC_AUTOMATION_ROOT", str(Path.home() / "SOC-Automation")))
        self.operational_alerts = OperationalAlertManager(root, send_func=kirim_notifikasi_telegram, dedupe_seconds=3600)
        self._circuit_alerted = False
        self.feature_control = FeatureControl(root)

        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ai-worker",
        )
        self.stop_event = threading.Event()

        # in_flight mencakup tiket yang sedang intake, menunggu worker,
        # maupun sedang diproses oleh worker.
        self._in_flight: set[str] = set()
        self._completed_this_run: set[str] = set()
        self._in_flight_lock = threading.Lock()

        # Future dipantau agar exception yang tidak terduga tetap terlihat.
        self._futures: set[Future[TicketProcessingResult]] = set()
        self._futures_lock = threading.Lock()

        self._started = False
        self._shutdown = False
        self._poll_cycle = 0

    def run(self) -> None:
        """Menjalankan polling sampai stop event atau KeyboardInterrupt."""
        if self._shutdown:
            raise RuntimeError(
                "AutomationManager yang sudah shutdown tidak dapat dijalankan."
            )
        if self._started:
            raise RuntimeError("AutomationManager sudah berjalan.")

        self._started = True
        if self.health is not None:
            self.health.mark_running()

        logger.info(
            "SOC Automation aktif: workers=%s, polling=%ss, lookback=%sm.",
            self.max_workers,
            self.polling_interval_seconds,
            self.recent_ticket_lookback_minutes,
        )

        try:
            while not self.stop_event.is_set():
                if self.role_gate is not None and not self.role_gate.is_active():
                    if self.health is not None:
                        self.health.mark_role(
                            "standby",
                            active_slot=self.role_gate.active_slot(),
                        )
                    self.stop_event.wait(min(self.polling_interval_seconds, 5))
                    continue
                if self.role_gate is not None and self.health is not None:
                    self.health.mark_role(
                        "active",
                        active_slot=self.role_gate.active_slot(),
                    )
                cycle_started = time.monotonic()
                if self.ticket_locks is not None:
                    self.ticket_locks.cleanup_expired()
                    self.ticket_locks.renew_owned()
                if self.health is not None:
                    self.health.mark_poll_started(
                        poll_cycle=self._poll_cycle + 1,
                        in_flight=self.in_flight_count,
                        pending_workers=self.pending_future_count,
                    )

                try:
                    if self.intake_breaker.is_open():
                        circuit = self.intake_breaker.snapshot()
                        logger.error("Ticket intake circuit breaker OPEN; polling intake ditunda sampai %s.", circuit.get("open_until"))
                        if self.health is not None:
                            self.health.mark_intake_health(status="circuit_open", circuit=circuit, error_code="INTAKE_CIRCUIT_OPEN")
                    else:
                        self.poll_once()
                        prior_open = self._circuit_alerted
                        self.intake_breaker.success()
                        if prior_open:
                            self.operational_alerts.notify("INTAKE_RECOVERED","ticket_intake",severity="INFO",fingerprint="intake-recovered",details={"worker":os.getenv("SOC_WORKER_SLOT","unknown"),"recovery":True})
                            self._circuit_alerted = False
                        if self.health is not None:
                            self.health.mark_intake_health(status="success", circuit=self.intake_breaker.snapshot())
                except JiraClientError:
                    logger.exception("Polling Jira gagal.")
                    if self.health is not None:
                        self.health.mark_poll_finished(
                            submitted=0,
                            in_flight=self.in_flight_count,
                            pending_workers=self.pending_future_count,
                            poll_status="jira_error",
                        )
                except Exception as exc:
                    logger.exception("Unexpected error pada polling/intake loop.")
                    circuit = self.intake_breaker.failure(exc)
                    if circuit["state"] == "open" and not self._circuit_alerted:
                        self.operational_alerts.notify("INTAKE_CIRCUIT_OPEN","ticket_intake",fingerprint=circuit.get("failure_fingerprint"),details={"worker":os.getenv("SOC_WORKER_SLOT","unknown"),"occurrences":circuit.get("consecutive_failures",0),"circuit_state":"open","open_until":circuit.get("open_until")})
                        self._circuit_alerted = True
                    if self.health is not None:
                        self.health.mark_poll_finished(submitted=0,in_flight=self.in_flight_count,pending_workers=self.pending_future_count,poll_status="intake_failed")
                        self.health.mark_intake_health(status="circuit_open" if circuit["state"]=="open" else "failed",circuit=circuit,error_code="UNHANDLED_INTAKE_EXCEPTION")

                elapsed = time.monotonic() - cycle_started
                remaining = max(
                    0.0,
                    self.polling_interval_seconds - elapsed,
                )
                self.stop_event.wait(remaining)
        finally:
            self._started = False

    def poll_once(self) -> int:
        """
        Memeriksa semua tiket hasil JQL dan menampilkan status setiap tiket.

        Tidak ada filter waktu pembuatan. Tiket lama tetap terlihat. Tiket Open
        ditransisikan ke L1 Analysis, tiket L1 Analysis dilanjutkan/recovery,
        sedangkan tiket Waiting hanya diperiksa assignee dan diinformasikan.
        """
        feature_snapshot = self.feature_control.snapshot()
        if not feature_snapshot["effective"]["jira_polling"]["effective"]:
            logger.info("Jira polling dilewati; feature jira_polling OFF (profile=%s).", feature_snapshot["profile"])
            return 0
        self._poll_cycle += 1
        poll_started = time.monotonic()

        logger.info(
            "[CHECK #%04d] Memeriksa seluruh tiket hasil JQL... "
            "(in-flight=%d, worker/pending=%d)",
            self._poll_cycle,
            self.in_flight_count,
            self.pending_future_count,
        )
        logger.info("[CHECK #%04d] JQL: %s", self._poll_cycle, self.jira.settings.polling_jql)

        issues = self.jira.search_tickets(
            max_results=self.max_search_results,
        )

        if not issues:
            elapsed = time.monotonic() - poll_started
            logger.info(
                "[CHECK #%04d] Selesai %.2fs — JQL tidak mengembalikan tiket. "
                "Cek berikutnya dalam %d detik.",
                self._poll_cycle,
                elapsed,
                self.polling_interval_seconds,
            )
            if self.health is not None:
                self.health.mark_poll_finished(
                    submitted=0,
                    in_flight=self.in_flight_count,
                    pending_workers=self.pending_future_count,
                )
            return 0

        status_counts: dict[str, int] = {}
        submitted = 0
        reassigned = 0
        unchanged = 0

        logger.info(
            "[CHECK #%04d] JQL mengembalikan %d tiket. Memeriksa satu per satu:",
            self._poll_cycle,
            len(issues),
        )

        for position, issue in enumerate(issues, start=1):
            if self.stop_event.is_set():
                break

            fields = issue.get("fields", {})
            status = fields.get("status", {}).get("name", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

            try:
                action = self._intake_ticket(
                    issue,
                    position=position,
                    total=len(issues),
                )
                if action == "submitted":
                    submitted += 1
                elif action == "reassigned":
                    reassigned += 1
                else:
                    unchanged += 1
            except JiraClientError:
                ticket_key = str(issue.get("key") or "UNKNOWN")
                logger.exception("[%d/%d] Operasi Jira gagal untuk %s.", position, len(issues), ticket_key)
            except Exception:
                ticket_key = str(issue.get("key") or "UNKNOWN")
                logger.exception("[%d/%d] Error ketika memproses %s.", position, len(issues), ticket_key)

        elapsed = time.monotonic() - poll_started
        status_summary = " | ".join(
            f"{name}: {count}"
            for name, count in sorted(status_counts.items())
        )
        logger.info("[CHECK #%04d] Ringkasan status — %s", self._poll_cycle, status_summary)
        logger.info(
            "[CHECK #%04d] Selesai %.2fs — total=%d, analisis disubmit=%d, "
            "re-assign saja=%d, tidak berubah=%d, in-flight=%d. "
            "Cek berikutnya dalam %d detik.",
            self._poll_cycle,
            elapsed,
            len(issues),
            submitted,
            reassigned,
            unchanged,
            self.in_flight_count,
            self.polling_interval_seconds,
        )
        if self.health is not None:
            self.health.mark_poll_finished(
                submitted=submitted,
                in_flight=self.in_flight_count,
                pending_workers=self.pending_future_count,
            )
        return submitted

    def _intake_ticket(
        self,
        issue: dict[str, Any],
        *,
        position: int,
        total: int,
    ) -> str:
        """
        Normalisasi status tiket ke Waiting, lalu submit analisis AI.

        Open    -> L1 Analysis -> Waiting -> AI
        L1      -> Waiting -> AI
        Waiting -> AI
        """
        ticket_key, fields = self._extract_issue(issue)
        summary = str(fields.get("summary") or "Tanpa summary").strip()
        status = fields.get("status", {}).get("name", "Unknown")
        assignee = fields.get("assignee")
        assignee_id = assignee.get("accountId") if isinstance(assignee, dict) else None
        assignee_name = (
            assignee.get("displayName", "Unknown")
            if isinstance(assignee, dict)
            else "Unassigned"
        )

        logger.info(
            "[%d/%d] %s | Status: %s | Assignee: %s | %s",
            position,
            total,
            ticket_key,
            status,
            assignee_name,
            summary,
        )

        reassigned = False
        if assignee_id != self.jira.account_id:
            logger.info(
                "[%s] Re-assign diperlukan: %s -> account automation.",
                ticket_key,
                assignee_name,
            )
            self.jira.assign_to_me(ticket_key)
            reassigned = True
        else:
            logger.info("[%s] Assignee sudah sesuai.", ticket_key)

        normalized = status.casefold()
        open_status = self.jira.settings.open_status.casefold()
        l1_status = self.jira.settings.l1_analysis_status.casefold()
        waiting_status = self.jira.settings.waiting_confirmation_status.casefold()

        if normalized not in {open_status, l1_status, waiting_status}:
            logger.warning(
                "[%s] Status %s termasuk hasil JQL tetapi tidak termasuk "
                "workflow Open/L1/Waiting; hanya assignee yang diperiksa.",
                ticket_key,
                status,
            )
            return "reassigned" if reassigned else "unchanged"

        with self._in_flight_lock:
            if ticket_key in self._completed_this_run:
                logger.info(
                    "[%s] Sudah selesai dianalisis pada sesi ini; "
                    "tidak disubmit ulang.",
                    ticket_key,
                )
                return "reassigned" if reassigned else "unchanged"

        if not self._claim_ticket(ticket_key):
            logger.info(
                "[%s] Sedang berada dalam antrean/analisis AI; "
                "tidak disubmit ulang.",
                ticket_key,
            )
            return "reassigned" if reassigned else "unchanged"

        submitted = False
        try:
            if normalized == open_status:
                logger.info(
                    "[%s] Tahap 1/2: %s -> %s.",
                    ticket_key,
                    status,
                    self.jira.settings.l1_analysis_status,
                )
                if not self.jira.transition(
                    ticket_key,
                    self.jira.settings.l1_analysis_status,
                ):
                    logger.warning(
                        "[%s] Transisi ke L1 Analysis tidak tersedia; proses dihentikan.",
                        ticket_key,
                    )
                    return "reassigned" if reassigned else "unchanged"
                emit_ticket_event(ticket_key,"JIRA_STATUS_TRANSITION","PASS",jira_status=self.jira.settings.l1_analysis_status)
                time.sleep(1.0)

                logger.info(
                    "[%s] Tahap 2/2: %s -> %s.",
                    ticket_key,
                    self.jira.settings.l1_analysis_status,
                    self.jira.settings.waiting_confirmation_status,
                )
                if not self.jira.transition(
                    ticket_key,
                    self.jira.settings.waiting_confirmation_status,
                ):
                    logger.warning(
                        "[%s] Transisi ke Waiting Confirmation tidak tersedia; "
                        "AI tidak dijalankan.",
                        ticket_key,
                    )
                    return "reassigned" if reassigned else "unchanged"
                emit_ticket_event(ticket_key,"JIRA_STATUS_TRANSITION","PASS",jira_status=self.jira.settings.waiting_confirmation_status)

            elif normalized == l1_status:
                logger.info(
                    "[%s] Transisi awal: %s -> %s.",
                    ticket_key,
                    status,
                    self.jira.settings.waiting_confirmation_status,
                )
                if not self.jira.transition(
                    ticket_key,
                    self.jira.settings.waiting_confirmation_status,
                ):
                    logger.warning(
                        "[%s] Transisi ke Waiting Confirmation tidak tersedia; "
                        "AI tidak dijalankan.",
                        ticket_key,
                    )
                    return "reassigned" if reassigned else "unchanged"
                emit_ticket_event(ticket_key,"JIRA_STATUS_TRANSITION","PASS",jira_status=self.jira.settings.waiting_confirmation_status)

            else:
                logger.info(
                    "[%s] Sudah berada di %s; langsung masuk proses AI.",
                    ticket_key,
                    self.jira.settings.waiting_confirmation_status,
                )

            if normalized == waiting_status:
                emit_ticket_event(ticket_key,"JIRA_STATUS_OBSERVED","PASS",jira_status=self.jira.settings.waiting_confirmation_status)
            feature_snapshot = self.feature_control.snapshot()
            if not feature_snapshot["effective"]["siem_retrieval"]["effective"]:
                result = self.ticket_processor.process_intake_only(issue, feature_snapshot=feature_snapshot)
                with self._in_flight_lock:
                    self._completed_this_run.add(ticket_key)
                if self.ticket_locks is not None:
                    self.ticket_locks.mark_completed(ticket_key)
                logger.info("[%s] Intake-only selesai; SIEM dan AI tidak dipanggil.", ticket_key)
                return "submitted"
            future = self.executor.submit(
                self.ticket_processor.process_analysis,
                issue,
            )
            submitted = True
            self._track_future(ticket_key, future)
            logger.info(
                "[%s] Berhasil disubmit ke antrean AI. Pending=%d.",
                ticket_key,
                self.pending_future_count,
            )
            return "submitted"
        finally:
            if not submitted:
                self._release_ticket(ticket_key)

    @staticmethod
    def _extract_issue(
        issue: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if not isinstance(issue, dict):
            raise ValueError("issue harus berupa dictionary.")

        ticket_key = str(issue.get("key") or "").strip()
        if not ticket_key:
            raise ValueError("Issue tidak memiliki ticket key.")

        fields = issue.get("fields")
        if not isinstance(fields, dict):
            raise ValueError(
                f"Issue {ticket_key} tidak memiliki fields yang valid."
            )

        return ticket_key, fields

    def _claim_ticket(self, ticket_key: str) -> bool:
        with self._in_flight_lock:
            if ticket_key in self._in_flight:
                return False

            if self.ticket_locks is not None:
                allowed, reason = (
                    self.ticket_locks.processing_allowed(
                        ticket_key
                    )
                )

                if not allowed:
                    logger.info(
                        "[%s] Pemrosesan dilewati; state=%s.",
                        ticket_key,
                        reason,
                    )
                    return False

                if not self.ticket_locks.acquire(
                    ticket_key
                ):
                    return False

                try:
                    state = (
                        self.ticket_locks.mark_processing(
                            ticket_key
                        )
                    )

                    logger.info(
                        "[%s] Persistent processing state; "
                        "attempt=%s, state=%s.",
                        ticket_key,
                        state.get("attempts"),
                        state.get("state"),
                    )

                except Exception:
                    self.ticket_locks.release(
                        ticket_key
                    )
                    raise

            self._in_flight.add(ticket_key)
            return True

    def _release_ticket(self, ticket_key: str) -> None:
        with self._in_flight_lock:
            self._in_flight.discard(ticket_key)
        if self.ticket_locks is not None:
            self.ticket_locks.release(ticket_key)

    def _track_future(
        self,
        ticket_key: str,
        future: Future[TicketProcessingResult],
    ) -> None:
        with self._futures_lock:
            self._futures.add(future)

        future.add_done_callback(
            lambda completed: self._on_future_done(
                ticket_key,
                completed,
            )
        )

    def _on_future_done(
        self,
        ticket_key,
        future,
    ):
        successful = False

        try:
            if future.cancelled():
                logger.warning(
                    "Worker untuk %s dibatalkan.",
                    ticket_key,
                )

                if self.ticket_locks is not None:
                    state = self.ticket_locks.mark_failure(
                        ticket_key,
                        "WORKER_CANCELLED",
                    )

                    logger.warning(
                        "[%s] Persistent failure state; "
                        "attempt=%s, state=%s.",
                        ticket_key,
                        state.get("attempts"),
                        state.get("state"),
                    )

                return

            result = future.result()

            successful_outcomes = {
                "false_positive_closed",
                "waiting_non_false_positive",
                "intake_only_waiting",
            }

            successful = (
                result.outcome
                in successful_outcomes
            )

            if successful:
                with self._in_flight_lock:
                    self._completed_this_run.add(
                        ticket_key
                    )

                if self.ticket_locks is not None:
                    state = (
                        self.ticket_locks.mark_completed(
                            ticket_key
                        )
                    )

                    logger.info(
                        "[%s] Persistent completion state; "
                        "attempt=%s, state=%s.",
                        ticket_key,
                        state.get("attempts"),
                        state.get("state"),
                    )

            elif self.ticket_locks is not None:
                failure_code = str(
                    result.outcome
                    or "PROCESSING_FAILED"
                ).strip().upper()[:128]

                state = self.ticket_locks.mark_failure(
                    ticket_key,
                    failure_code,
                )

                logger.warning(
                    "[%s] Persistent failure state; "
                    "attempt=%s, state=%s, code=%s.",
                    ticket_key,
                    state.get("attempts"),
                    state.get("state"),
                    state.get("failure_code"),
                )

            logger.info(
                "Worker selesai: ticket=%s, outcome=%s.",
                result.ticket_key,
                result.outcome,
            )

        except Exception:
            logger.exception(
                "Worker untuk %s berakhir dengan exception.",
                ticket_key,
            )

            if self.ticket_locks is not None:
                try:
                    self.ticket_locks.mark_failure(
                        ticket_key,
                        "WORKER_EXCEPTION",
                    )
                except Exception:
                    logger.exception(
                        "[%s] Gagal menyimpan persistent "
                        "failure state.",
                        ticket_key,
                    )

        finally:
            if self.health is not None:
                self.health.mark_worker_finished(
                    successful=successful
                )

            self._release_ticket(ticket_key)

            with self._futures_lock:
                self._futures.discard(future)

    @property
    def in_flight_count(self) -> int:
        with self._in_flight_lock:
            return len(self._in_flight)

    @property
    def pending_future_count(self) -> int:
        with self._futures_lock:
            return len(self._futures)

    def request_stop(self) -> None:
        """Meminta polling loop berhenti tanpa langsung mematikan worker."""
        self.stop_event.set()
        if self.health is not None:
            self.health.request_shutdown()

    def shutdown(self) -> None:
        """Menghentikan polling, executor, serta menutup client HTTP."""
        if self._shutdown:
            return

        self._shutdown = True
        self.stop_event.set()

        logger.info(
            "Shutdown dimulai: pending=%s, wait_for_workers=%s.",
            self.pending_future_count,
            self.shutdown_wait_for_workers,
        )

        self.executor.shutdown(
            wait=self.shutdown_wait_for_workers,
            cancel_futures=not self.shutdown_wait_for_workers,
        )

        # Pastikan koneksi ditutup setelah worker selesai atau dibatalkan.
        try:
            self.jira.close()
        finally:
            self.ticket_processor.siem.close()

        if self.ticket_locks is not None:
            self.ticket_locks.release_all()
            self.ticket_locks.close()

        logger.info("SOC Automation berhenti.")
