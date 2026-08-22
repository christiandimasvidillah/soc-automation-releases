# Checklist Publikasi Release

## Sebelum build

- [ ] Runtime dan Manager/TUI version sudah final.
- [ ] Dokumentasi Indonesia diperbarui.
- [ ] Dokumentasi English diperbarui.
- [ ] Version history, installation, update, rollback, troubleshooting, validation, compatibility, dan known issues diperbarui.
- [ ] Production credentials dan persistent state tidak berada dalam source allowlist.

## Full Installer gates

- [ ] Active-source scan PASS.
- [ ] Installer package scan PASS.
- [ ] Secret findings = 0.
- [ ] Generated `install.py` compile PASS.
- [ ] Installed Manager/TUI compile PASS.
- [ ] Custom-root simulation PASS.
- [ ] Extracted `install.py` compile PASS.
- [ ] Internal `SHA256SUMS` PASS.
- [ ] Manifest integrity PASS.
- [ ] ZIP integrity PASS.
- [ ] Backup/obsolete-source scan kosong.
- [ ] Production-state scan kosong.

## Fresh-install acceptance

- [ ] Download artifact dari jalur distribusi yang akan dipublikasikan.
- [ ] Default-root installation PASS.
- [ ] Default-root autodetection PASS.
- [ ] Explicit `--root` PASS.
- [ ] Custom-root installation PASS.
- [ ] Custom-root autodetection PASS.
- [ ] Interactive TUI startup PASS.
- [ ] Acceptance report tidak mengandung credential atau data internal.

## Final artifact

- [ ] Nama artifact final ditentukan sebelum checksum dibuat.
- [ ] Checksum dibuat dari artifact final.
- [ ] `.zip.sha256` cocok.
- [ ] `SHA256SUMS` cocok.
- [ ] `release.json` memuat hash aktual dan timestamp final.
- [ ] Release description sesuai artifact.
- [ ] Historical release tidak ditimpa.

## GitHub settings

- [ ] Tag sesuai versi/revision.
- [ ] Full Installer stable terbaru ditandai Latest.
- [ ] Manager/TUI-only release tidak mengambil label Latest utama.
- [ ] Pre-release tidak dicentang untuk stable release.
- [ ] Semua asset berhasil diunduh anonim dan diverifikasi ulang.
