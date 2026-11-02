# Update, Backup, dan Rollback

## Update

Preflight → readiness → backup verification → package inspect → checksum → dry-run → stop jika diwajibkan → transactional staging → syntax/import/test gates → atomic current switch → start → post-update verification.

## Backup

Verifier membaca archive tanpa extraction, menghitung SHA-256, dan menolak absolute path, `..`, symlink, hardlink, device, atau member berbahaya.

## Rollback

Pilih previous atau target version. Release manager memasang shared links, menjalankan checks, dan mengganti current atomik. Restart komponen yang diminta manifest.

## Migration

Setiap release harus mendokumentasikan minimum version, schema change, compatibility, data migration, service restart, known issues, dan rollback target.

<!-- cumulative-installer-generation-v1.27.10 -->
## Jalur upgrade Manager/TUI v1.27.10

Didukung langsung: v1.27.8 ke v1.27.10 dan v1.27.9 ke v1.27.10. Instalasi v1.27.9 tidak diwajibkan.

<!-- cumulative-installer-generation-v1.27.11 -->
## Jalur upgrade Manager/TUI v1.27.10

Didukung langsung: v1.27.8 ke v1.27.10 dan v1.27.9 ke v1.27.10. Instalasi v1.27.9 tidak diwajibkan.
