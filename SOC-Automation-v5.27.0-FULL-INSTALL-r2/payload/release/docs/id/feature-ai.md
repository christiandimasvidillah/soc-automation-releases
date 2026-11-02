# Feature dan AI Control Center

## Fitur individual

- `jira_polling`: pencarian dan intake tiket.
- `siem_retrieval`: pengambilan raw alert.
- `privacy_sanitization`: sanitasi deterministik dan privacy gate.
- `local_ai_detection`: discovery path sensitif.
- `gemini_analysis`: analisis AI cloud setelah gate.
- `virustotal_enrichment`: reputasi destination.
- `sharing_allowlist`: approved identity/domain policy.
- `telegram_notification`: notifikasi operator.
- `status_web_viewer`: status viewer.
- `documentation_viewer`: web documentation.

## Profile

### FULL_AUTOMATION
Seluruh pipeline dan policy aktif. Gunakan hanya jika readiness lulus.

### JIRA_INTAKE_ONLY
Jira polling, assignment, transition, dan Telegram aktif; SIEM, Local AI, Gemini, VT, dan sharing policy tidak dipanggil.

### PRIVACY_LOCAL_AI_ONLY
SIEM, sanitizer, privacy gate, dan Local AI aktif; Gemini/external enrichment OFF.

### AI_ANALYSIS_NO_AUTO_ACTION
Analisis berjalan, tindakan otomatis dibatasi; operator menjadi decision owner.

### MAINTENANCE_SAFE_MODE
Pipeline intake/AI/auto-action dinonaktifkan untuk maintenance.

### CUSTOM
Hasil toggle individual. Wajib periksa effective reason.

## AI status

Local AI menampilkan provider, model, endpoint, reachability, mode. Gemini menampilkan preferred model, allowed models, mode, credential configured, dan availability—tanpa API key.
