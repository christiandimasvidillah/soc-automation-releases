# Diagnostik dan Troubleshooting

- Start All partial: periksa shared/logs/soc_master.out, PID file, dependency import, startup preflight, timeout.
- Circuit open: periksa fingerprint, consecutive failures, open_until; pulihkan Jira/intake dan tunggu cooldown/success.
- Privacy blocked: jalankan regression/retest; jangan bypass gate.
- Viewer gagal: cek loopback bind, port, JSON content type, cache-busted asset, PID detection.
- Ghost ticket: reconciliation hanya bila in-flight nol; hanya state lokal diubah ketika Jira sudah terminal.
