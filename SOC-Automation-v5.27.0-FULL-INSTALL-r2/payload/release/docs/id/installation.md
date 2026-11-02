# Instalasi Automation dari Awal

## 1. Prasyarat host

- WSL/Linux 64-bit dengan user non-root khusus operasi.
- Python sesuai `requirements.txt`, `venv`, `pip`, `tmux`, `systemd --user`, `curl`, `unzip`, `sha256sum`.
- Akses jaringan ke Jira, SIEM, Gemini (jika aktif), Telegram (jika aktif), VirusTotal (jika aktif).
- Ollama/Local AI tersedia pada endpoint lokal bila Local AI digunakan.
- Ruang disk untuk releases, backups, audit, SQLite, dan logs.

## 2. Struktur direktori

```text
~/SOC-Automation/
├── current → releases/vX.Y.Z
├── releases/
├── manager/
├── shared/
│   ├── .env
│   ├── audit_logs/
│   ├── logs/
│   ├── control/
│   ├── workers/
│   └── ticket_locks.sqlite3
└── .venv/
```

`current` harus berupa symlink release aktif. Data persistent berada di `shared`, bukan di release directory.

## 3. Virtual environment

```bash
python3 -m venv ~/SOC-Automation/.venv
~/SOC-Automation/.venv/bin/pip install -r ~/SOC-Automation/current/requirements.txt
```

## 4. Shared configuration

Buat `shared/.env` dari template internal. Set permission minimum `0600`. Jangan menaruh credential di source release atau dokumentasi.

## 5. Service dan tmux

Pasang user service untuk Manual False-Incident dan Background Auto-FP jika digunakan. Viewer dapat dijalankan oleh user service atau tmux sesuai TUI.

## 6. Preflight sebelum start pertama

Jalankan Configuration Preflight, Runtime Health, Privacy Regression, Local AI Diagnostic, dan Maintenance Readiness. Semua blocker harus diperbaiki sebelum Full Automation.

## 7. Start pertama

Gunakan TUI → Runtime Control → Start All. Pilih mode aman lebih dahulu, misalnya Manual False-Incident `SHADOW` dan Background Auto-FP `SHADOW`. Verifikasi master PID, active worker PID, service active, Jira connectivity, dan provider status.

## 8. Acceptance criteria

- Hanya satu active worker.
- SQLite integrity `ok`.
- Jira dan SIEM preflight lulus.
- Privacy regression lulus.
- Viewer hanya listen pada localhost.
- Tidak ada secret pada log/status endpoint.

<!-- custom-root-launcher-v1.27.9 -->
## Custom root dan launcher root-aware

Mulai Manager/TUI v1.27.9, instalasi dengan `python3 install.py --root <path>` menyimpan root aktual pada `.installation-root`. Launcher `manager/soc-tui` menentukan root dari `--root`, `SOC_AUTOMATION_ROOT`, metadata instalasi, atau lokasi launcher.

<!-- cumulative-installer-generation-v1.27.10 -->
## Manager/TUI v1.27.10 - Instalasi custom root

Patch cumulative v1.27.10 dapat dipasang langsung dari v1.27.8 atau v1.27.9. Installer menggunakan `chr(10)` untuk metadata root dan memvalidasi generated `install.py` sebelum distribusi.

<!-- cumulative-installer-generation-v1.27.11 -->
## Manager/TUI v1.27.10 - Instalasi custom root

Patch cumulative v1.27.10 dapat dipasang langsung dari v1.27.8 atau v1.27.9. Installer menggunakan `chr(10)` untuk metadata root dan memvalidasi generated `install.py` sebelum distribusi.
