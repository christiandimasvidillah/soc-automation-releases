# SOC Automation — Manual Operasional Lengkap

> **Bahasa utama:** Indonesia · **Versi dokumentasi:** 5.27.0 · **Baseline implementasi:** runtime 5.26.1 dan Manager/TUI 1.26.1.

Dokumentasi ini adalah sumber rujukan utama untuk keseluruhan SOC Automation: pemasangan awal, konfigurasi, TUI, Jira, SIEM, privacy, Local AI, Gemini, Telegram, Auto-FP, worker blue/green, viewer, audit, maintenance, update, rollback, troubleshooting, pengujian, dan riwayat versi.

## Jalur belajar

1. Baca **Gambaran Sistem** dan **Arsitektur**.
2. Ikuti **Instalasi Automation** untuk pemasangan awal.
3. Lengkapi **Konfigurasi** dan jalankan **Preflight & Readiness**.
4. Gunakan **Referensi TUI** untuk operasi normal.
5. Gunakan **Runbook** ketika terjadi gangguan.

## Batas keamanan

- Jangan memasukkan `.env`, token, API key, raw SIEM JSON, attachment tiket, atau private key ke dokumentasi/audit publik.
- Jangan melewati privacy gate atau decision gate.
- Web Viewer dan Documentation Viewer hanya boleh bind ke `127.0.0.1`.
- Operasi normal wajib melalui TUI; command hanya untuk recovery darurat.
