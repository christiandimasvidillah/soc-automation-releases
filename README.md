# SOC Automation Releases

Official stable installer and incremental-update distribution for the **SOC Automation Platform** cybersecurity portfolio project.

> **Designed, built, and maintained by Dimas Vidillah Christian**

## Current Release Status

| Component | Current version | Status |
|---|---:|---|
| Runtime | v5.32.0 | Stable (*Gemini · Antigravity Upgrade*) |
| Manager/TUI | v1.31.0 | Stable cumulative update (*Gemini · Antigravity*) |
| Full Installer | v5.32.0 | Portable verified release (`SOC-Automation-v5.32.0-FULL-INSTALL.zip`) |
| Documentation | Indonesia + English | Synchronized for v5.32.0 / TUI v1.31.0 |

## Download

- **Latest Release (v5.32.0):** https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest
- **Tag v5.32.0:** https://github.com/christiandimasvidillah/soc-automation-releases/releases/tag/v5.32.0
- **Documentation:** https://christiandimasvidillah.github.io/soc-automation-docs/

## v5.32.0 | TUI v1.31.0 Highlights (*Gemini · Antigravity Upgrade*)

- **Automated Playbook Engine**: Deterministic *blockers-first* False Positive evaluation over privacy-sanitized payloads (`safe_payload`) with `confidence_score >= min_confidence` (default `0.90`), atomic `fcntl.flock` store, execution audit logs, and inactive `CANDIDATE` rule mining from `*_sanitized.json`.
- **`MANUAL REVIEW REQUIRED` Policy & Empty Analysis Auto-Close**: Skips writing to the Jira Analysis Result custom field on manual-review outcomes (delivering sanitized summaries via Telegram only), while enabling `FULL_AUTOMATION` automatic closure (`False Incident -> Done` + SIEM closure) even when Jira's Analysis Result field is empty.
- **Authoritative Gemini Credentials & Tiered Model Rotation**: Authoritative `shared/.env` loading (`override=True`), runtime `GEMINI_API_KEY` hot-reload, and tiered Pro / Gemini 4 reasoning primary -> Gemini 3.x Flash fallback rotation.
- **Manager/TUI v1.31.0 (`Gemini · Antigravity`)**: Adds `[P] Playbook Engine Center` and `socctl.py playbook` CLI subcommands.

## Verified Checksums (v5.32.0)

```text
efc223a41e232e40904bec7da22f266282150012df66d456297546585fb3042b  SOC-Automation-v5.32.0-FULL-INSTALL.zip
abd240438449ec6dd40a34fdcc5aaa1f78bc752340c85d9a4cb925430ec241f9  soc-automation-patch-v5.32.0.zip
32d149ee7effef24cd9f46db3ed4292ff256db92bf1310a039908d614cf3af7c  soc-automation-manager-tui-v1.31.0.zip
```

## Which Package Should I Use?

### New installation

Use `SOC-Automation-v5.32.0-FULL-INSTALL.zip`. Supports both the default installation root (`~/SOC-Automation`) and any custom `--root` directory.

### Existing v5.31.6 installation

Apply `soc-automation-patch-v5.32.0.zip` via TUI Update Manager / `deploy_manager.py`, and apply `soc-automation-manager-tui-v1.31.0.zip` via:

```text
TUI
→ Update Manager
→ Apply Manager/TUI update from path
```

## What the Full Installer Contains

- Runtime release files (`v5.32.0`)
- Manager/TUI control plane (`v1.31.0 · Gemini · Antigravity`)
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
