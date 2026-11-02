# Known Issues dan Batasan

- Source TUI dalam `current` dapat berbeda dari manager launcher; gunakan header versi dan package metadata.
- Rollback code tidak membalik tindakan eksternal Jira/SIEM yang sudah selesai.
- Credential hanya ditampilkan sebagai CONFIGURED/MISSING.
- Feature changes berlaku untuk pekerjaan baru; tiket aktif memakai snapshot awal.
- Documentation full-text search hanya mengindeks konten yang dibangun pada release aktif.

<!-- custom-root-launcher-v1.27.9 -->
## Resolved in TUI v1.27.9

Launcher lama meng-hardcode `~/SOC-Automation` dan gagal pada custom installation root. Masalah ini telah diperbaiki dengan root-aware launcher.

<!-- cumulative-installer-generation-v1.27.10 -->
## v1.27.9 superseded

v1.27.9 adalah internal superseded build dan tidak boleh digunakan untuk menghasilkan Full Installer. Gunakan cumulative v1.27.10.

<!-- cumulative-installer-generation-v1.27.11 -->
## v1.27.9 superseded

v1.27.9 adalah internal superseded build dan tidak boleh digunakan untuk menghasilkan Full Installer. Gunakan cumulative v1.27.10.
