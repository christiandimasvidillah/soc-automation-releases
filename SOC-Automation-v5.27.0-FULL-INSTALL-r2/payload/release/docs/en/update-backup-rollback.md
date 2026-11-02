# Update, Backup, and Rollback

The safe workflow is preflight, readiness, verified backup, inspect, checksum, dry-run, required stop, transactional staging, syntax/import/tests, atomic current switch, start, and post-update verification. Backups are read without extraction and unsafe members are rejected. Rollback validates a previous release and shared links, then switches atomically. Every release documents minimum version, schema/migration, compatibility, restart, known issues, and rollback target.

<!-- cumulative-installer-generation-v1.27.10 -->
## Manager/TUI v1.27.10 upgrade path

Direct upgrades are supported from v1.27.8 and v1.27.9. Installing v1.27.9 first is not required.

<!-- cumulative-installer-generation-v1.27.11 -->
## Manager/TUI v1.27.10 upgrade path

Direct upgrades are supported from v1.27.8 and v1.27.9. Installing v1.27.9 first is not required.
