# Operasi Harian

## Startup shift

1. Buka Dashboard.
2. Periksa runtime/service/AI status.
3. Jalankan Runtime Health dan Configuration Preflight bila ada perubahan.
4. Periksa feature profile.
5. Start All jika runtime berhenti.
6. Pastikan hanya satu active worker.

## Shutdown maintenance

1. Tunggu in-flight selesai.
2. Graceful Stop All.
3. Verifikasi service inactive dan PID hilang.
4. Buat/verifikasi backup.
5. Jalankan maintenance.

## Perubahan mode

Gunakan TUI. Catat reason dan pastikan feature audit revision berubah. Jangan edit JSON secara manual kecuali recovery darurat.
