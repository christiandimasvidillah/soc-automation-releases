from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APPLICATION_ROOT = Path.home() / "SOC-Automation"
ENV_PATH = APPLICATION_ROOT / "shared" / ".env"
load_dotenv(
    dotenv_path=ENV_PATH,
    override=False,
)


class ConfigurationError(RuntimeError):
    """Konfigurasi wajib tidak tersedia atau memiliki nilai tidak valid."""


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigurationError(
            f"Environment variable '{name}' belum dikonfigurasi."
        )
    return value.strip()


def get_optional_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def get_int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"Environment variable '{name}' harus berupa integer."
        ) from exc

    if value < minimum:
        raise ConfigurationError(
            f"Environment variable '{name}' minimal bernilai {minimum}."
        )
    return value


def get_csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    values = tuple(item.strip() for item in raw_value.split(",") if item.strip())
    if not values:
        raise ConfigurationError(
            f"Environment variable '{name}' harus berisi minimal satu nilai."
        )
    return values


def get_float_env(name: str, default: float, *, minimum: float = 0.0) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"Environment variable '{name}' harus berupa angka."
        ) from exc
    if value < minimum:
        raise ConfigurationError(
            f"Environment variable '{name}' minimal bernilai {minimum}."
        )
    return value


def get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    normalized = raw_value.strip().casefold()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False

    raise ConfigurationError(
        f"Environment variable '{name}' harus berupa "
        "true/false, 1/0, yes/no, atau on/off."
    )


@dataclass(frozen=True)
class JiraSettings:
    domain: str
    email: str
    api_token: str
    account_id: str
    project_key: str
    issue_type: str
    analysis_field_id: str
    alert_id_field_id: str
    alert_link_field_id: str
    open_status: str
    l1_analysis_status: str
    waiting_confirmation_status: str
    false_incident_status: str
    done_status: str
    request_timeout: int

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}.atlassian.net"

    @property
    def issue_api_url(self) -> str:
        return f"{self.base_url}/rest/api/2/issue"

    @property
    def search_api_url(self) -> str:
        return f"{self.base_url}/rest/api/3/search/jql"

    @property
    def browse_url(self) -> str:
        return f"{self.base_url}/browse"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @property
    def polling_jql(self) -> str:
        # Sama dengan filter JQL pada Jira: seluruh tiket aktif pada
        # statusCategory 2 dan 4, bukan hanya tiket berstatus Open.
        return (
            f'project = "{self.project_key}" '
            f'AND issuetype = "{self.issue_type}" '
            'AND statusCategory in (2, 4) '
            'ORDER BY "Time to done" ASC'
        )


@dataclass(frozen=True)
class SiemSettings:
    base_url: str
    api_key: str
    request_timeout: int
    verify_ssl: bool

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
            "kbn-xsrf": "true",
        }

    @property
    def alert_search_url(self) -> str:
        return (
            f"{self.base_url.rstrip('/')}"
            "/api/detection_engine/signals/search"
        )

    @property
    def alert_status_url(self) -> str:
        # Dipertahankan agar SiemClient tetap kompatibel, walaupun workflow
        # saat ini tidak melakukan auto-close alert.
        return (
            f"{self.base_url.rstrip('/')}"
            "/api/detection_engine/signals/status"
        )


@dataclass(frozen=True)
class LocalAISettings:
    provider: str
    endpoint: str
    model: str
    request_timeout: int
    min_confidence: float
    max_chunk_bytes: int
    max_findings: int
    store_prompts: bool


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    max_workers: int
    allowed_models: tuple[str, ...]
    max_cycles: int
    request_delay_seconds: float
    cycle_delay_seconds: float
    model_cache_seconds: float
    rate_limit_cooldown_seconds: float
    error_cooldown_seconds: float
    fallback_models: tuple[str, ...]


@dataclass(frozen=True)
class SanitizerSettings:
    hash_secret_key: str
    hash_length: int
    audit_dir: str


@dataclass(frozen=True)
class TelegramSettings:
    enabled: bool
    bot_token: str
    chat_id: str
    request_timeout: int
    jira_browse_url: str


@dataclass(frozen=True)
class AutomationSettings:
    polling_interval_seconds: int
    recent_ticket_lookback_minutes: int
    shutdown_wait_for_workers: bool
    max_search_results: int
    alert_field_max_attempts: int
    alert_field_retry_seconds: float


@dataclass(frozen=True)
class LoggingSettings:
    level: str
    log_to_file: bool
    log_file: str
    max_bytes: int
    backup_count: int


@dataclass(frozen=True)
class Settings:
    jira: JiraSettings
    siem: SiemSettings
    local_ai: LocalAISettings
    gemini: GeminiSettings
    sanitizer: SanitizerSettings
    telegram: TelegramSettings
    automation: AutomationSettings
    logging: LoggingSettings


def load_settings() -> Settings:
    log_level = get_optional_env("LOG_LEVEL", "INFO").upper()
    valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level not in valid_log_levels:
        raise ConfigurationError(
            "LOG_LEVEL harus salah satu dari DEBUG, INFO, WARNING, "
            "ERROR, atau CRITICAL."
        )

    return Settings(
        jira=JiraSettings(
            domain=get_optional_env("JIRA_DOMAIN", "bankjasajakarta"),
            email=get_required_env("JIRA_EMAIL"),
            api_token=get_required_env("JIRA_API_TOKEN"),
            account_id=get_required_env("JIRA_ACCOUNT_ID"),
            project_key=get_optional_env("JIRA_PROJECT_KEY", "CSOC"),
            issue_type=get_optional_env("JIRA_ISSUE_TYPE", "SIEM Alert"),
            analysis_field_id=get_optional_env(
                "JIRA_ANALYSIS_FIELD_ID",
                "customfield_10798",
            ),
            alert_id_field_id=get_optional_env(
                "JIRA_ALERT_ID_FIELD_ID",
                "customfield_10771",
            ),
            alert_link_field_id=get_optional_env(
                "JIRA_ALERT_LINK_FIELD_ID",
                "customfield_10786",
            ),
            open_status=get_optional_env("JIRA_STATUS_OPEN", "Open"),
            l1_analysis_status=get_optional_env(
                "JIRA_STATUS_L1_ANALYSIS",
                "L1 Analysis",
            ),
            waiting_confirmation_status=get_optional_env(
                "JIRA_STATUS_WAITING_CONFIRMATION",
                "Waiting for User Confirmation",
            ),
            false_incident_status=get_optional_env(
                "JIRA_STATUS_FALSE_INCIDENT",
                "False Incident",
            ),
            done_status=get_optional_env("JIRA_STATUS_DONE", "Done"),
            request_timeout=get_int_env(
                "JIRA_REQUEST_TIMEOUT",
                30,
            ),
        ),
        siem=SiemSettings(
            base_url=get_optional_env(
                "SIEM_API_BASE_URL",
                (
                    "https://bjj-siem.kb.asia-southeast2."
                    "gcp.elastic-cloud.com"
                ),
            ),
            api_key=get_required_env("ELASTIC_API_KEY"),
            request_timeout=get_int_env(
                "SIEM_REQUEST_TIMEOUT",
                30,
            ),
            verify_ssl=get_bool_env(
                "SIEM_VERIFY_SSL",
                False,
            ),
        ),
        local_ai=LocalAISettings(
            provider=get_optional_env(
                "LOCAL_AI_PROVIDER",
                "ollama",
            ).strip().casefold(),
            endpoint=get_optional_env(
                "LOCAL_AI_ENDPOINT",
                "http://127.0.0.1:11434",
            ).rstrip("/"),
            model=get_required_env(
                "LOCAL_AI_MODEL",
            ),
            request_timeout=get_int_env(
                "LOCAL_AI_TIMEOUT_SECONDS",
                120,
            ),
            min_confidence=get_float_env(
                "LOCAL_AI_MIN_CONFIDENCE",
                0.85,
            ),
            max_chunk_bytes=get_int_env(
                "LOCAL_AI_MAX_CHUNK_BYTES",
                65536,
            ),
            max_findings=get_int_env(
                "LOCAL_AI_MAX_FINDINGS",
                500,
            ),
            store_prompts=get_bool_env(
                "LOCAL_AI_STORE_PROMPTS",
                False,
            ),
        ),
        gemini=GeminiSettings(
            api_key=get_required_env("GEMINI_API_KEY"),
            max_workers=get_int_env(
                "AI_MAX_WORKERS",
                3,
            ),
            allowed_models=get_csv_env(
                "GEMINI_ALLOWED_MODELS",
                (
                    "gemini-3.5-flash",
                    "gemini-3.1-flash-lite",
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-lite",
                    "gemini-2.5-pro",
                ),
            ),
            max_cycles=get_int_env("GEMINI_MAX_CYCLES", 2),
            request_delay_seconds=get_float_env(
                "GEMINI_REQUEST_DELAY_SECONDS",
                2.5,
            ),
            cycle_delay_seconds=get_float_env(
                "GEMINI_CYCLE_DELAY_SECONDS",
                60.0,
            ),
            model_cache_seconds=get_float_env(
                "GEMINI_MODEL_CACHE_SECONDS",
                900.0,
            ),
            rate_limit_cooldown_seconds=get_float_env(
                "GEMINI_RATE_LIMIT_COOLDOWN_SECONDS",
                60.0,
            ),
            error_cooldown_seconds=get_float_env(
                "GEMINI_ERROR_COOLDOWN_SECONDS",
                30.0,
            ),
            fallback_models=get_csv_env(
                "GEMINI_FALLBACK_MODELS",
                ("gemini-2.0-flash", "gemini-1.5-flash"),
            ),
        ),
        sanitizer=SanitizerSettings(
            hash_secret_key=get_required_env("HASH_SECRET_KEY"),
            hash_length=get_int_env("HASH_LENGTH", 12),
            audit_dir=get_optional_env("AUDIT_DIR", "audit_logs"),
        ),
        telegram=TelegramSettings(
            enabled=get_bool_env("TELEGRAM_ENABLED", True),
            bot_token=get_required_env("TELEGRAM_BOT_TOKEN"),
            chat_id=get_required_env("TELEGRAM_CHAT_ID"),
            request_timeout=get_int_env(
                "TELEGRAM_REQUEST_TIMEOUT",
                15,
            ),
            jira_browse_url=(
                f"https://{get_optional_env('JIRA_DOMAIN', 'bankjasajakarta')}"
                ".atlassian.net/browse"
            ),
        ),
        automation=AutomationSettings(
            polling_interval_seconds=get_int_env(
                "POLL_INTERVAL_SECONDS",
                30,
            ),
            recent_ticket_lookback_minutes=get_int_env(
                "RECENT_TICKET_LOOKBACK_MINUTES",
                5,
            ),
            shutdown_wait_for_workers=get_bool_env(
                "SHUTDOWN_WAIT_FOR_WORKERS",
                True,
            ),
            max_search_results=get_int_env(
                "MAX_SEARCH_RESULTS",
                100,
            ),
            alert_field_max_attempts=get_int_env(
                "JIRA_ALERT_FIELD_MAX_ATTEMPTS",
                5,
            ),
            alert_field_retry_seconds=get_float_env(
                "JIRA_ALERT_FIELD_RETRY_SECONDS",
                3.0,
            ),
        ),
        logging=LoggingSettings(
            level=log_level,
            log_to_file=get_bool_env("LOG_TO_FILE", True),
            log_file=get_optional_env(
                "LOG_FILE",
                "soc_automation.log",
            ),
            max_bytes=get_int_env(
                "LOG_MAX_BYTES",
                10 * 1024 * 1024,
            ),
            backup_count=get_int_env(
                "LOG_BACKUP_COUNT",
                5,
                minimum=0,
            ),
        ),
    )


settings = load_settings()
