# Gambaran Sistem

## Tujuan

SOC Automation mempercepat intake dan triage tiket Jira, menghubungkan alert SIEM, membersihkan data sensitif, menjalankan analisis AI yang dikontrol, memperbarui Jira, mengirim Telegram, serta menjalankan Auto-FP yang dibatasi policy.

## Komponen utama

- Jira sebagai sumber tiket dan workflow.
- Elastic/Kibana sebagai sumber alert SIEM.
- Python deterministic sanitizer sebagai pengendali privacy.
- Local AI sebagai penemu lokasi data sensitif, bukan sanitizer.
- Gemini sebagai analis atas JSON yang sudah aman.
- SQLite sebagai lease, retry, cooldown, completion, dan idempotency store.
- SocMaster dan worker blue/green sebagai runtime berdaya pulih.
- TUI sebagai control plane utama.
- Status Viewer dan Documentation Viewer sebagai read-only visibility plane.

## Hasil akhir per tiket

- False Positive eksplisit dan aman: Jira False Incident → Done, lalu SIEM ditutup.
- Bukan False Positive/hasil ambigu: tiket tetap Waiting untuk analis.
- AI/SIEM OFF: intake selesai, tiket Waiting, Telegram terkirim, tanpa raw SIEM atau AI call.
