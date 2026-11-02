from __future__ import annotations

import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from google import genai

from config import ConfigurationError, settings
from health_manager import HealthManager, HealthManagerError
from jira_client import JiraClient
from siem_client import SiemClient
from telegram_notifier import close_default_notifier
from ticket_lock import TicketLockStore
from role_gate import ActiveSlotGate
from worker_identity import WorkerIdentity
from ticket_processor import TicketProcessor
from worker_manager import AutomationManager


FILE_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(threadName)-12s | "
    "%(name)-20s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class CleanConsoleFormatter(logging.Formatter):
    """Formatter terminal ringkas, berwarna, dan mudah dipindai."""

    RESET = "\033[0m"
    DIM = "\033[2m"
    COLORS = {
        logging.DEBUG: "\033[36m",     # cyan
        logging.INFO: "\033[32m",      # green
        logging.WARNING: "\033[33m",   # yellow
        logging.ERROR: "\033[31m",     # red
        logging.CRITICAL: "\033[1;31m", # bold red
    }
    ICONS = {
        logging.DEBUG: "🔎",
        logging.INFO: "✅",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "🚨",
    }

    def __init__(self, *, use_color: bool) -> None:
        super().__init__()
        self.use_color = use_color

    @staticmethod
    def _component(record: logging.LogRecord) -> str:
        if record.threadName.startswith("ai-worker"):
            return record.threadName.replace("ai-worker_", "AI-")
        names = {
            "__main__": "SYSTEM",
            "worker_manager": "POLLER",
            "ticket_processor": "TICKET",
            "jira_client": "JIRA",
            "siem_client": "SIEM",
            "gemini_manager": "GEMINI",
            "telegram_notifier": "TELEGRAM",
            "data_sanitizer": "SANITIZER",
        }
        return names.get(record.name, record.name.rsplit(".", 1)[-1].upper())

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%H:%M:%S")
        icon = self.ICONS.get(record.levelno, "•")
        component = self._component(record)
        message = record.getMessage()
        line = f"{timestamp}  {icon}  {component:<10}  {message}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        if not self.use_color:
            return line

        color = self.COLORS.get(record.levelno, "")
        return f"{self.DIM}{timestamp}{self.RESET}  {color}{icon}  {component:<10}{self.RESET}  {message}"


def configure_logging() -> None:
    """Log ringkas ke terminal dan log detail ke rotating file."""
    level = getattr(logging, settings.logging.level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        CleanConsoleFormatter(use_color=sys.stdout.isatty())
    )

    handlers: list[logging.Handler] = [console_handler]

    if settings.logging.log_to_file:
        log_path = Path(settings.logging.log_file).expanduser()
        if log_path.parent != Path("."):
            log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.logging.max_bytes,
            backupCount=settings.logging.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT)
        )
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def get_version() -> str:
    version_file = Path(__file__).with_name("VERSION")
    try:
        return version_file.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def get_shared_dir() -> Path:
    configured = os.getenv("SOC_SHARED_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    resolved = Path(__file__).resolve()
    if resolved.parent.parent.name == "releases":
        return resolved.parents[2] / "shared"
    return resolved.parent / "shared"


def build_automation_manager(health_manager: HealthManager | None = None, role_gate: ActiveSlotGate | None = None) -> AutomationManager:
    """Membuat dependency aplikasi dan merangkainya ke manager."""
    jira_client = JiraClient(settings.jira)
    siem_client = SiemClient(settings.siem)
    ticket_lock_store = TicketLockStore(
        get_shared_dir() / "ticket_locks.sqlite3",
        owner_id=f"worker-{os.getpid()}",
    )

    try:
        ai_client = genai.Client(
            api_key=settings.gemini.api_key,
        )

        ticket_processor = TicketProcessor(
            jira_client=jira_client,
            siem_client=siem_client,
            ai_client=ai_client,
            app_settings=settings,
            ticket_lock_store=ticket_lock_store,
        )

        return AutomationManager(
            jira_client=jira_client,
            ticket_processor=ticket_processor,
            max_workers=settings.gemini.max_workers,
            polling_interval_seconds=(
                settings.automation.polling_interval_seconds
            ),
            recent_ticket_lookback_minutes=(
                settings.automation.recent_ticket_lookback_minutes
            ),
            shutdown_wait_for_workers=(
                settings.automation.shutdown_wait_for_workers
            ),
            max_search_results=(
                settings.automation.max_search_results
            ),
            health_manager=health_manager,
            ticket_lock_store=ticket_lock_store,
            role_gate=role_gate,
        )
    except Exception:
        jira_client.close()
        siem_client.close()
        raise


def main() -> int:
    """Entry point SOC Automation dengan PID, health, dan graceful signal."""
    manager: AutomationManager | None = None
    health: HealthManager | None = None
    exit_code = 1

    try:
        configure_logging()
        logger = logging.getLogger(__name__)

        identity = WorkerIdentity.from_environment()
        health = HealthManager(get_shared_dir(), get_version(), identity)
        health.register()
        role_gate = ActiveSlotGate(get_shared_dir(), identity.slot)
        health.mark_role(role_gate.role(), active_slot=role_gate.active_slot())
        manager = build_automation_manager(health, role_gate)

        def handle_shutdown(signum: int, _frame: object) -> None:
            signal_name = signal.Signals(signum).name
            logger.info(
                "Signal %s diterima; meminta graceful shutdown.",
                signal_name,
            )
            if health is not None:
                health.request_shutdown(signal_name=signal_name)
            if manager is not None:
                manager.request_stop()

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

        logger.info("=" * 68)
        logger.info("SOC AUTOMATION AKTIF | Version %s | PID %d", get_version(), os.getpid())
        logger.info(
            "Workflow : %s  →  %s  →  %s",
            settings.jira.open_status,
            settings.jira.l1_analysis_status,
            settings.jira.waiting_confirmation_status,
        )
        logger.info(
            "Runtime  : %d AI worker | cek setiap %d detik | lookback %d menit",
            settings.gemini.max_workers,
            settings.automation.polling_interval_seconds,
            settings.automation.recent_ticket_lookback_minutes,
        )
        logger.info(
            "Health   : %s",
            health.health_file,
        )
        logger.info("=" * 68)

        health.mark_running()
        manager.run()
        exit_code = 0
        return exit_code

    except HealthManagerError as exc:
        logging.getLogger(__name__).critical("Startup ditolak: %s", exc)
        exit_code = 3
        return exit_code
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Interrupt diterima; menghentikan polling.")
        if health is not None:
            health.request_shutdown(signal_name="KeyboardInterrupt")
        if manager is not None:
            manager.request_stop()
        exit_code = 0
        return exit_code
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR, format=FILE_LOG_FORMAT)
        logging.getLogger(__name__).critical("Konfigurasi aplikasi tidak valid: %s", exc)
        exit_code = 2
        return exit_code
    except Exception:
        logging.getLogger(__name__).exception("SOC Automation berhenti karena fatal error.")
        exit_code = 1
        return exit_code
    finally:
        if manager is not None:
            try:
                manager.shutdown()
            except Exception:
                logging.getLogger(__name__).exception("Error ketika shutdown manager.")
                exit_code = 1
        try:
            close_default_notifier()
        except Exception:
            logging.getLogger(__name__).exception("Error ketika menutup Telegram notifier.")
        if health is not None:
            try:
                health.shutdown(exit_code=exit_code)
            except Exception:
                logging.getLogger(__name__).exception("Error ketika menulis final health state.")


if __name__ == "__main__":
    raise SystemExit(main())
