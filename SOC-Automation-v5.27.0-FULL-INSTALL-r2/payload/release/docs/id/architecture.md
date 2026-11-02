# Arsitektur dan Alur Kerja

## Runtime blue/green

SocMaster memonitor heartbeat, PID, restart budget, backoff, startup readiness, graceful shutdown, dan active slot. Hanya worker aktif yang boleh intake. Worker standby mempertahankan readiness tetapi tidak memproses tiket.

## Pipeline penuh

```text
Jira JQL
  → validasi project/status/assignee
  → persistent lease + processing state
  → Open → L1 Analysis → Waiting
  → resolve Alert ID
  → fetch alert SIEM
  → Local AI sensitive-path discovery
  → deterministic Python sanitization
  → residual scan + privacy gate
  → sharing allowlist / Gemini
  → output privacy gate
  → Jira analysis field
  → decision gate
      ├─ FALSE POSITIVE eksplisit → False Incident → Done → SIEM close
      └─ lainnya/ambigu → tetap Waiting
  → Telegram
  → audit event + completion/failure state
```

## Snapshot konfigurasi

Setiap tiket memakai profile, revision, hash, dan effective feature snapshot saat tiket mulai diproses. Perubahan feature di tengah proses tidak mencampur keputusan dua konfigurasi.

## Cutover

Target standby diverifikasi, active slot diganti atomik, source menunggu drain, target menjalani stabilization, dan automatic failback dilakukan jika target tidak sehat.
