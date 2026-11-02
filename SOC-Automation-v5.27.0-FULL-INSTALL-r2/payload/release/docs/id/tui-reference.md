# Referensi Lengkap TUI

## Dashboard

Menampilkan release, versi TUI, active slot, SocMaster, worker blue/green, PID, heartbeat, SQLite, service, feature profile/revision, Local AI model/mode/reachability, serta Gemini model/mode/credential state. Dashboard read-only.

**Gunakan ketika:** memulai shift, sebelum maintenance, setelah update, atau saat incident operasi.

**Recovery:** status `UNKNOWN`, `DEGRADED`, atau `UNAVAILABLE` harus ditelusuri melalui Runtime Health dan Log Viewer sebelum auto-action diaktifkan.

## Runtime Control

Pilihan: Restart Active Worker, Stop Automation, Cut Over to Standby, Deployment Status, Start All, Graceful Stop All.

Restart/stop dikirim ke SocMaster. Cutover melakukan readiness, atomic active-slot switch, drain, stabilization, dan failback. Start All memulai runtime dan service policy lalu memulihkan mode. Stop All menonaktifkan mode, menghentikan service, menghentikan runtime, lalu memverifikasi seluruh PID inactive.

## Update Manager

Pilihan: Inspect Package, Verify SHA-256, Dry-run Release Patch, Apply Transactional Release, Apply Manager/TUI Update, Deployment Status.

Inspect memvalidasi ZIP/manifest/path/hash/minimum version. Dry-run membuat validasi tanpa switch. Apply membangun staging release, memasang shared links, menjalankan checks, mengganti `current` atomik, dan menulis release metadata.

## Audit Viewer

Menampilkan daftar audit, summary, full JSON, ticket audit, maintenance, feature control, Auto-FP, update, dan rollback audit. Viewer membatasi path, ukuran, control sequence, key sensitif, dan truncation.

## Log Viewer

Membaca SocMaster output, worker logs, viewer logs, Auto-FP service, dan Manual False-Incident service. Log bukan sumber keputusan tiket final; gunakan audit untuk outcome.

## Diagnostics

System/Runtime Health, Configuration Preflight, Maintenance Readiness, Privacy Regression, Local AI, sanitizer diagnostic, Ticket Observability/Stuck Report, Backup Verification, Release Qualification, VT/SMB diagnostics.

## Viewer Services

Status Viewer: Start, Stop, Status, URL pada `127.0.0.1:8765`. Documentation Viewer: Start, Stop, Status, URL, Build/Refresh pada `127.0.0.1:8766`. Semua write method ditolak.

## Release and Rollback

Release Status, Inventory, Rollback Previous, Rollback to Version. Rollback mengganti code release dan shared link secara atomik, tetapi tidak membalik tindakan eksternal Jira/SIEM.

## Maintenance

Cleanup Dry-run/Apply, Compile Python, Retention Policy, Backup Verification, Live-state Reconciliation, Ticket Reprocess/Dismiss/Restore, Sharing Allowlist, VT/SMB tools, Auto-FP configuration, Manual False-Incident configuration.

## Feature Control Center

Feature & AI Dashboard, Apply Operating Profile, Configure Individual Feature, Show Effective Configuration. Perubahan atomic, revisioned, hashed, audited, dan berlaku untuk pekerjaan baru.
