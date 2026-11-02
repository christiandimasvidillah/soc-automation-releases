# Konfigurasi

## `.env`

Kelompok konfigurasi mencakup Jira URL/account/token/workflow fields, SIEM endpoint/credential, Gemini key/model list, Local AI provider/model/endpoint, Telegram bot/chat, polling interval, worker count, timeout, dan policy feature. Nilai secret tidak boleh ditampilkan di dashboard; cukup `CONFIGURED` atau `MISSING`.

## Feature flags

File persistent: `shared/control/feature_flags.json`. Penulisan menggunakan file lock, atomic replace, permission terbatas, revision, config hash, backup, dan audit append-only.

## Configured vs effective

- **Configured ON:** operator meminta fitur aktif.
- **Effective ON:** seluruh dependency terpenuhi.
- **Blocked:** diminta ON tetapi dependency tidak tersedia.
- **Not applicable:** tidak relevan karena upstream OFF.
- **Unavailable:** konfigurasi aktif tetapi provider/service gagal.

## Dependency penting

Gemini memerlukan SIEM retrieval dan privacy sanitization. Local AI detection memerlukan payload SIEM dan privacy pipeline. VT/sharing policy menjadi tidak relevan bila SIEM retrieval OFF.

## Permission

`.env`, feature flags, ticket database, dan audit sensitif harus dapat dibaca hanya oleh user service yang berwenang.
