from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from config import settings


logger = logging.getLogger(__name__)
AI_ANALYSIS_FAILED = "AI_ANALYSIS_FAILED"


@dataclass
class ModelState:
    """Status runtime sebuah model pada project/API key saat ini."""

    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    last_success_at: float = 0.0


# Cache dibagi oleh seluruh AI worker agar setiap worker tidak melakukan
# models.list dan tidak menguji model rate-limited secara berulang-ulang.
_MODEL_LOCK = threading.RLock()
_MODEL_LIST: list[str] = []
_MODEL_LIST_EXPIRES_AT = 0.0
_MODEL_STATES: dict[str, ModelState] = {}
_PREFERRED_MODEL: str | None = None


def _model_name(model: Any) -> str:
    name = str(getattr(model, "name", "") or "").strip()
    return name.removeprefix("models/")


def _supports_generate_content(model: Any) -> bool:
    """Memilih hanya model yang mendukung operasi generateContent."""
    actions = getattr(model, "supported_actions", None)
    if actions is None:
        # Kompatibilitas jika versi SDK tidak mengembalikan metadata actions.
        return True

    normalized_actions = {
        str(action).replace("_", "").casefold()
        for action in actions
    }
    return "generatecontent" in normalized_actions


def _discover_models(client: Any, *, force_refresh: bool = False) -> list[str]:
    """
    Mengambil model akun yang mendukung generateContent, lalu melakukan
    intersect dengan allowlist SOC dalam urutan yang ditentukan di .env.
    """
    global _MODEL_LIST, _MODEL_LIST_EXPIRES_AT

    now = time.monotonic()
    with _MODEL_LOCK:
        if (
            not force_refresh
            and _MODEL_LIST
            and now < _MODEL_LIST_EXPIRES_AT
        ):
            return list(_MODEL_LIST)

    available_generate_models: set[str] = set()
    discovered_all: list[str] = []

    for model in client.models.list():
        name = _model_name(model)
        if not name:
            continue
        discovered_all.append(name)
        if _supports_generate_content(model):
            available_generate_models.add(name)

    # Urutan allowlist adalah urutan rotasi. Hanya model yang benar-benar
    # tersedia bagi API key/project saat ini yang dipertahankan.
    allowed_order = [
        name.removeprefix("models/").strip()
        for name in settings.gemini.allowed_models
        if name.strip()
    ]
    selected = [
        name for name in allowed_order
        if name in available_generate_models
    ]

    if not selected:
        logger.error(
            "Tidak ada model pada GEMINI_ALLOWED_MODELS yang tersedia dan "
            "mendukung generateContent. Available generateContent count=%d.",
            len(available_generate_models),
        )
        raise RuntimeError(
            "Tidak ada model SOC allowlist yang tersedia untuk generateContent."
        )

    unavailable_allowed = [
        name for name in allowed_order
        if name not in available_generate_models
    ]

    with _MODEL_LOCK:
        _MODEL_LIST = selected
        _MODEL_LIST_EXPIRES_AT = (
            time.monotonic() + settings.gemini.model_cache_seconds
        )
        for model_name in selected:
            _MODEL_STATES.setdefault(model_name, ModelState())

    logger.info(
        "Rotasi Gemini aktif (%d model): %s",
        len(selected),
        " -> ".join(selected),
    )
    if unavailable_allowed:
        logger.warning(
            "Model allowlist yang tidak tersedia/tidak mendukung "
            "generateContent dilewati: %s",
            ", ".join(unavailable_allowed),
        )

    return list(selected)


def dapatkan_model_dinamis(client: Any) -> list[str]:
    """Daftar model rotasi SOC yang tersedia untuk API key/project."""
    try:
        return _discover_models(client)
    except Exception:
        logger.exception("Gagal mengambil daftar model Gemini dinamis.")
        return []


def _is_rate_limit_error(error: Exception) -> bool:
    message = str(error).casefold()
    indicators = (
        "429",
        "resource_exhausted",
        "resource exhausted",
        "quota",
        "rate limit",
        "too many requests",
    )
    return any(indicator in message for indicator in indicators)


def _is_unavailable_model_error(error: Exception) -> bool:
    message = str(error).casefold()
    indicators = (
        "404",
        "not found",
        "not supported",
        "unsupported",
        "permission denied",
        "403",
    )
    return any(indicator in message for indicator in indicators)


def _ordered_usable_models(models: list[str]) -> list[str]:
    """Preferred model dahulu, lalu model yang tidak sedang cooldown."""
    now = time.monotonic()
    with _MODEL_LOCK:
        preferred = _PREFERRED_MODEL
        usable = [
            model
            for model in models
            if _MODEL_STATES.setdefault(model, ModelState()).cooldown_until
            <= now
        ]

    if preferred in usable:
        usable.remove(preferred)
        usable.insert(0, preferred)
    return usable


def _mark_success(model_name: str) -> None:
    global _PREFERRED_MODEL
    with _MODEL_LOCK:
        state = _MODEL_STATES.setdefault(model_name, ModelState())
        state.cooldown_until = 0.0
        state.consecutive_failures = 0
        state.last_success_at = time.time()
        _PREFERRED_MODEL = model_name


def _mark_failure(model_name: str, *, rate_limited: bool) -> None:
    with _MODEL_LOCK:
        state = _MODEL_STATES.setdefault(model_name, ModelState())
        state.consecutive_failures += 1

        if rate_limited:
            # Exponential cooldown dibatasi multiplier 8 agar model tidak
            # langsung dihantam ulang oleh worker lain.
            multiplier = min(2 ** (state.consecutive_failures - 1), 8)
            state.cooldown_until = time.monotonic() + (
                settings.gemini.rate_limit_cooldown_seconds * multiplier
            )
        else:
            state.cooldown_until = time.monotonic() + (
                settings.gemini.error_cooldown_seconds
            )


def _wait_until_a_model_is_ready(models: list[str]) -> None:
    """Menunggu cooldown tercepat tanpa melampaui delay siklus."""
    now = time.monotonic()
    with _MODEL_LOCK:
        cooldowns = [
            _MODEL_STATES.setdefault(model, ModelState()).cooldown_until
            for model in models
        ]

    future_cooldowns = [value - now for value in cooldowns if value > now]
    if not future_cooldowns:
        return

    delay = min(
        min(future_cooldowns),
        settings.gemini.cycle_delay_seconds,
    )
    if delay > 0:
        logger.warning(
            "Semua model sedang cooldown; menunggu %.1f detik.",
            delay,
        )
        time.sleep(delay)


def dapatkan_analisis_ai(
    client: Any,
    prompt: str,
    max_siklus: int | None = None,
) -> str:
    """
    Menemukan semua model akun secara dinamis lalu memakai model yang sehat.

    Tidak ada allowlist model. Status rate limit diketahui melalui request
    generate_content yang nyata; model yang mengembalikan 429 diberi cooldown
    dan worker berikutnya akan melewatinya untuk sementara.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt AI tidak boleh kosong.")

    cycles = max_siklus or settings.gemini.max_cycles
    if cycles < 1:
        raise ValueError("max_siklus minimal bernilai 1.")

    try:
        models = _discover_models(client)
    except Exception:
        logger.exception("Model discovery Gemini gagal.")
        return AI_ANALYSIS_FAILED

    refreshed_after_model_error = False

    for cycle in range(1, cycles + 1):
        usable_models = _ordered_usable_models(models)
        if not usable_models:
            _wait_until_a_model_is_ready(models)
            usable_models = _ordered_usable_models(models)

        for model_name in usable_models:
            logger.info(
                "Menguji/menggunakan model %s untuk analisis, siklus %s/%s.",
                model_name,
                cycle,
                cycles,
            )

            if settings.gemini.request_delay_seconds > 0:
                time.sleep(settings.gemini.request_delay_seconds)

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                result = str(getattr(response, "text", "") or "").strip()
                if not result:
                    logger.warning(
                        "Model %s merespons tanpa text; mencoba model lain.",
                        model_name,
                    )
                    _mark_failure(model_name, rate_limited=False)
                    continue

                _mark_success(model_name)
                logger.info(
                    "Model %s tersedia dan berhasil; dijadikan preferred model.",
                    model_name,
                )
                return result

            except Exception as exc:
                rate_limited = _is_rate_limit_error(exc)
                _mark_failure(model_name, rate_limited=rate_limited)

                if rate_limited:
                    logger.warning(
                        "Model %s terkena limit; masuk cooldown dan "
                        "beralih ke model berikutnya.",
                        model_name,
                    )
                else:
                    logger.error(
                        "Model %s gagal: %s: %s",
                        model_name,
                        type(exc).__name__,
                        exc,
                    )

                    # Jika model sudah ditarik/permission berubah, refresh list
                    # sekali agar daftar mengikuti akun/project terbaru.
                    if (
                        _is_unavailable_model_error(exc)
                        and not refreshed_after_model_error
                    ):
                        try:
                            models = _discover_models(
                                client,
                                force_refresh=True,
                            )
                            refreshed_after_model_error = True
                        except Exception:
                            logger.exception(
                                "Refresh daftar model Gemini gagal."
                            )

        if cycle < cycles:
            _wait_until_a_model_is_ready(models)

    logger.error(
        "Tidak ada model Gemini yang berhasil setelah seluruh rotasi."
    )
    return AI_ANALYSIS_FAILED
