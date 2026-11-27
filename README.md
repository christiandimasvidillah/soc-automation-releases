# SOC Automation Releases

Official stable installer and incremental-update distribution for the **SOC Automation Platform** cybersecurity portfolio project.

> **Designed, built, and maintained by Dimas Vidillah Christian**

## Current Release Status

| Component | Current version | Status |
|---|---:|---|
| Runtime | v5.33.0 | Stable (*Gemini · Antigravity Upgrade*) |
| Manager/TUI | v1.32.0 | Stable cumulative update (*Gemini · Antigravity*) |
| Full Installer | v5.33.0 | Portable verified release (`SOC-Automation-v5.33.0-FULL-INSTALL.zip`) |
| Documentation | Indonesia + English | Synchronized for v5.33.0 / TUI v1.32.0 |

## Download

- **Latest Release (v5.33.0):** https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest
- **Tag v5.33.0:** https://github.com/christiandimasvidillah/soc-automation-releases/releases/tag/v5.33.0
- **Documentation:** https://christiandimasvidillah.github.io/soc-automation-docs/

## v5.33.0 | TUI v1.32.0 Highlights (*Gemini · Antigravity Upgrade*)

- **Safe Hidden-Input `GEMINI_API_KEY` Rotation (`gemini_key_manager.py`, `socctl.py gemini set-key`)**: Hidden `getpass`/`--stdin` input (rejecting raw CLI key arguments), strict URL-safe format validation & optional fail-closed live `--verify` prior to disk mutation, atomic `0600` `shared/.env` persistence (`fcntl.flock` + `fsync` + `os.replace`), immediate `resolve_live_gemini_api_key()` hot-reload, and 12-hex SHA-256 fingerprint-only rotation audit logs (`secrets_disclosed: false`).
- **Live Gemini Model & Quota Readiness Probe (`socctl.py gemini status` / `probe`)**: Zero-token `models.list()` candidate discovery plus optional minimal 4-token readiness classification (`READY`, `QUOTA_LIMITED`, `OVERLOADED`, `UNAVAILABLE`, `AUTH_INVALID`) hardened by automatic secret redaction (`redact_secrets()`).
- **Manager/TUI v1.32.0 (`Gemini · Antigravity`)**: Adds **Gemini API & Model Center** to `[F] Feature Control Center` and `[6] Diagnostics` (with masked secret input) plus non-secret `key_fingerprint` reporting in `ai_health.py` while retaining all v5.32.0 Automated Playbook Engine and `FULL_AUTOMATION` capabilities.

## Verified Checksums (v5.33.0)

```text
3872268f412871b4fd4eca2def048b2b938ad877bcd8709275f849834f46ce2d  SOC-Automation-v5.33.0-FULL-INSTALL.zip
b0ea81232690e3b976370112956b5fb5b078866567c53164745800587ae8e6c4  soc-automation-patch-v5.33.0.zip
92864059ecfddce2c0c81462c42388ffa8ed3b58b9fcfd798ea179b2a3f95663  soc-automation-manager-tui-v1.32.0.zip
```

## Which Package Should I Use?

### New installation

Use `SOC-Automation-v5.33.0-FULL-INSTALL.zip`. Supports both the default installation root (`~/SOC-Automation`) and any custom `--root` directory.

### Existing v5.31.6+ installation

Apply `soc-automation-patch-v5.33.0.zip` via TUI Update Manager / `deploy_manager.py`, and apply `soc-automation-manager-tui-v1.32.0.zip` via:

```text
TUI
→ Update Manager
→ Apply Manager/TUI update from path
```

## What the Full Installer Contains

- Runtime release files (`v5.33.0`)
- Manager/TUI control plane (`v1.32.0 · Gemini · Antigravity`)
- Root-aware `soc-tui` launcher
- Versioned release layout and atomic `current` symlink
- Python virtual-environment bootstrap
- Bilingual documentation payload (`docs/id/` & `docs/en/`)
- Status and Documentation viewers
- Tests and release-validation metadata

The package does **not** include production credentials, raw SIEM evidence, production databases, audit logs, private keys, or persistent production state.

## Portable Installation

Default root:

```bash
python3 install.py
~/SOC-Automation/manager/soc-tui
```

Custom root:

```bash
python3 install.py --root "$HOME/SOC-Automation-Custom-Test"
~/SOC-Automation-Custom-Test/manager/soc-tui
```

Launcher root resolution order:

1. Explicit `--root`
2. `SOC_AUTOMATION_ROOT`
3. `.installation-root`
4. Launcher location

The curses TUI must be launched directly from an interactive terminal. Pipes and output redirection may cause `cbreak()`/`nocbreak()` errors.

## Release Security Gates

Every published installer must pass:

- release qualification gate (`release_qualification_gate.py`);
- explicit active-file allowlisting;
- fixture-aware secret scanning (`0` findings);
- backup and obsolete-source exclusion;
- production-state exclusion;
- generated installer compilation;
- installed Manager/TUI compilation;
- custom-root installation simulation;
- extracted installer compilation;
- internal `SHA256SUMS` verification;
- manifest integrity;
- ZIP integrity.

## Release Policy

- Never commit binary `.zip` archives into the Git working tree; attach binaries as GitHub Release assets.
- Never replace a published asset with different content under the same name.
- Keep historical releases available.
- Mark only the newest validated Full Installer as **Latest**.
- Publish Indonesian and English documentation with every update.

## Public Portfolio Boundary

This repository is intentionally limited to sanitized release distribution and public-safe metadata. Development workspaces, production configuration, internal endpoints, operational allowlists, raw evidence, databases, logs, and backups remain outside this repository.

## Documentation

Complete operational documentation:

https://christiandimasvidillah.github.io/soc-automation-docs/
