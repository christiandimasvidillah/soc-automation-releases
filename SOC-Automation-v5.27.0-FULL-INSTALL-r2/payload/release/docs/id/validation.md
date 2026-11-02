# Pengujian dan Acceptance

## Minimum test set

- Python compile/import.
- JavaScript syntax.
- ZIP integrity dan SHA-256.
- Release Manager dry-run.
- TUI menu/docs parity.
- Bahasa Indonesia/English parity.
- Internal route/link check.
- Secret scan.
- Privacy regression.
- Jira no-action dan SIEM no-action test.
- Intake-only test.
- Feature dependency test.
- Viewer read-only/loopback test.
- Backup unsafe-member test.

Release gagal jika implementasi berubah tetapi dokumentasi, release notes, migration, rollback, atau version history belum diperbarui.

<!-- custom-root-launcher-v1.27.9 -->
## Acceptance custom root

Validasi wajib: default root, custom root, metadata root, environment override, explicit `--root`, launcher execution, dan pesan error yang menunjukkan effective root.

<!-- cumulative-installer-generation-v1.27.10 -->
## Gate installer v1.27.10

Wajib PASS: generated compile, custom-root simulation, launcher execution, extracted compile, internal checksum, ZIP integrity, secret scan, dan production-state exclusion.

<!-- cumulative-installer-generation-v1.27.11 -->
## Gate installer v1.27.10

Wajib PASS: generated compile, custom-root simulation, launcher execution, extracted compile, internal checksum, ZIP integrity, secret scan, dan production-state exclusion.
