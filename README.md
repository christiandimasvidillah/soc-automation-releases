# SOC Automation Releases

Official stable installer and incremental-update distribution for the **SOC Automation Platform** cybersecurity portfolio project.

> **Designed, built, and maintained by Dimas Vidillah Christian**

## Current Release Status

| Component | Current version | Status |
|---|---:|---|
| Runtime | v5.33.1 | Stable (*Gemini · Antigravity Upgrade*) |
| Manager/TUI | v1.32.1 | Stable cumulative update (*Gemini · Antigravity*) |
| Full Installer | v5.33.1 | Portable verified release (`SOC-Automation-v5.33.1-FULL-INSTALL.zip`) |
| Documentation | Indonesia + English | Synchronized for v5.33.1 / TUI v1.32.1 |

## Download

- **Latest Release (v5.33.1):** https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest
- **Tag v5.33.1:** https://github.com/christiandimasvidillah/soc-automation-releases/releases/tag/v5.33.1
- **Documentation:** https://christiandimasvidillah.github.io/soc-automation-docs/

## v5.33.1 | TUI v1.32.1 Highlights (*Gemini · Antigravity Patch*)

- **Reasoning-Aware Live Gemini Readiness Probe (`gemini_key_manager.py`)**: Allocates `max_output_tokens=1024` with a `60s` timeout and minimal `thinking_config` (`LOW` / `MINIMAL`) for reasoning-class models (`gemini-4-*`, `gemini-3.1-pro-preview`, `gemini-pro-latest`) during `socctl.py gemini probe --generate`, preventing hidden thinking tokens from exhausting the output budget so healthy reasoning models accurately report `READY` instead of `EMPTY_RESPONSE` (never retrying `429`/`503`/`404`/`401` states).
- **Safe Hidden-Input `GEMINI_API_KEY` Rotation (`socctl.py gemini set-key`)**: Hidden `getpass`/`--stdin` input, strict format validation & optional fail-closed live `--verify`, atomic `0600` `shared/.env` persistence (`fcntl.flock` + `fsync` + `os.replace`), immediate `resolve_live_gemini_api_key()` hot-reload, and 12-hex SHA-256 fingerprint-only audit logs (`secrets_disclosed: false`).
- **Manager/TUI v1.32.1 (`Gemini · Antigravity`)**: Aligns **Gemini API & Model Center** (`[F] Feature Control Center` and `[6] Diagnostics`) and `[P] Playbook Engine Center` with full custom-root portability and all 7 Safe Full Installer gates.

## Verified Checksums (v5.33.1)

```text
025a385a6390f5eccb55bb782cc9b9ee47f313dc0990a327a59556fbe4e44c86  SOC-Automation-v5.33.1-FULL-INSTALL.zip
32947d18191d4ac28f7171540ef26bde7c7fe389f92740da860e44e29153a4c5  soc-automation-patch-v5.33.1.zip
c0378f0c265f6ca977d9e13ad861fbd80f7b4bce17a3065c8ae2234d8393179f  soc-automation-manager-tui-v1.32.1.zip
```

## Which Package Should I Use?

### New installation

Use `SOC-Automation-v5.33.1-FULL-INSTALL.zip`. Supports both the default installation root (`~/SOC-Automation`) and any custom `--root` directory.

### Existing v5.31.6+ installation

Apply `soc-automation-patch-v5.33.1.zip` via TUI Update Manager / `deploy_manager.py`, and apply `soc-automation-manager-tui-v1.32.1.zip` via:

```text
TUI
→ Update Manager
→ Apply Manager/TUI update from path
```

## What the Full Installer Contains

- Runtime release files (`v5.33.1`)
- Manager/TUI control plane (`v1.32.1 · Gemini · Antigravity`)
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
