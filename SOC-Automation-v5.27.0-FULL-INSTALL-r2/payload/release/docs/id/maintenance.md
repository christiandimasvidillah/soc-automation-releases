# Update, Backup, Rollback, Maintenance

## Update aman
1. Configuration preflight dan maintenance readiness.
2. Pastikan in-flight nol dan deployment idle.
3. Verifikasi backup dan ruang disk.
4. Inspect ZIP, SHA-256, manifest, minimum version, files.
5. Dry-run.
6. Graceful Stop All bila perlu.
7. Transactional staging deploy, syntax/test gate, atomic current switch.
8. Start All dan post-update verification.

Backup verifier membaca gzip/tar tanpa extraction dan menolak absolute path, traversal, symlink, hardlink, serta device. Rollback memasang shared links, menjalankan checks, dan mengganti current secara atomik.
