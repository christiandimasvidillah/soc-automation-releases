# Troubleshooting

## Start All PARTIAL_OR_FAILED
Periksa `shared/logs/soc_master.out`, PID path, active slot, import/dependency, service state, dan startup timeout.

## Feature ON tetapi effective OFF
Lihat reason dependency. Jangan mengubah file manual; aktifkan dependency atau pilih profile yang valid.

## Privacy blocked
Periksa residual category/path, jalankan privacy regression dan stored audit retest. Jangan bypass.

## Gemini credential missing
Perbaiki `.env` melalui prosedur secret management, restart worker bila diperlukan, lalu cek status CONFIGURED.

## Service Health kosong
Periksa endpoint JSON, content type, frontend cache, viewer version, dan browser hard refresh.

## Candidate expired/hash mismatch/UUID mismatch
Candidate tidak boleh dieksekusi. Bangun ulang evidence dan candidate baru.

<!-- custom-root-launcher-v1.27.9 -->
## Launcher mencari `.venv` pada root yang salah

Gunakan launcher v1.27.9 atau lebih baru. Periksa `.installation-root`, lalu jalankan `manager/soc-tui --root <root>` bila override eksplisit diperlukan.

<!-- cumulative-installer-generation-v1.27.10 -->
## Generated install.py syntax error

Masalah newline bertingkat pada v1.27.9 diselesaikan oleh v1.27.10. Build sekarang fail-closed pada compile, extraction, checksum, custom-root simulation, dan launcher gate.

<!-- cumulative-installer-generation-v1.27.11 -->
## Generated install.py syntax error

Masalah newline bertingkat pada v1.27.9 diselesaikan oleh v1.27.10. Build sekarang fail-closed pada compile, extraction, checksum, custom-root simulation, dan launcher gate.
