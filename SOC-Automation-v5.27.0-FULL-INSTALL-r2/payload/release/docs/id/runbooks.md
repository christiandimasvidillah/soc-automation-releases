# Runbook Gangguan

## Jira unavailable
Aktifkan circuit breaker behavior, jangan spam retry, periksa credential/network/rate limit, pulihkan, lalu verifikasi recovery alert.

## SIEM unavailable
Gunakan JIRA_INTAKE_ONLY bila intake tetap dibutuhkan. Jangan menghasilkan analisis tanpa evidence.

## Local AI unavailable
Jika policy memungkinkan, nonaktifkan Local AI dan gunakan deterministic sanitizer; jika tidak, pindah ke intake-only.

## Gemini unavailable
Nonaktifkan Gemini atau pilih privacy-local-only. Tiket tetap Waiting.

## Ticket stuck
Gunakan Observability/Stuck Report, periksa lease/cooldown/failure, retest privacy bila terkait, lalu reprocess setelah root cause selesai.

## Viewer gagal
Periksa service/tmux, bind, port, output log, restart viewer, dan hard refresh.
