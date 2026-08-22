# SOC Automation Releases

Official stable installer and incremental-update distribution for the **SOC Automation Platform** cybersecurity portfolio project.

> **Designed, built, and maintained by Dimas Vidillah Christian**

## Current Release Status

| Component | Current version | Status |
|---|---:|---|
| Runtime | v5.27.0 | Stable |
| Manager/TUI | v1.27.11 | Recommended cumulative update |
| Full Installer | v5.27.0-r2 | Portable release candidate / publish after final artifact checksum |
| Documentation | Indonesia + English | Maintained with each release |

## Download

- **Latest Full Installer:** https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest
- **Manager/TUI v1.27.11:** https://github.com/christiandimasvidillah/soc-automation-releases/releases/tag/manager-v1.27.11
- **Documentation:** https://christiandimasvidillah.github.io/soc-automation-docs/

## Which Package Should I Use?

### New installation

Use the latest `FULL-INSTALL` package. The portable revision supports both the default installation root and a custom root.

### Existing v5.27.0 installation

Use the cumulative Manager/TUI v1.27.11 update through:

```text
TUI
→ Update Manager
→ Apply Manager/TUI update from path
```

v1.27.11 supports direct upgrades from v1.27.8, v1.27.9, and v1.27.10. Installing intermediate versions is not required.

### Future runtime upgrades

Starting with the next stable runtime release, publish both:

- a Full Installer for new installations;
- an incremental update for supported existing versions.

## What the Full Installer Contains

- Runtime release files
- Manager/TUI control plane
- Root-aware `soc-tui` launcher
- Versioned release layout and atomic `current` symlink
- Python virtual-environment bootstrap
- Bilingual documentation payload
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

- explicit active-file allowlisting;
- fixture-aware secret scanning;
- backup and obsolete-source exclusion;
- production-state exclusion;
- generated installer compilation;
- installed Manager/TUI compilation;
- custom-root installation simulation;
- extracted installer compilation;
- internal `SHA256SUMS` verification;
- manifest integrity;
- ZIP integrity;
- default-root fresh installation;
- custom-root fresh installation;
- automatic root detection;
- interactive TUI startup.

## Release Assets

A stable Full Installer release should contain:

```text
SOC-Automation-vX.Y.Z-FULL-INSTALL[-rN].zip
SOC-Automation-vX.Y.Z-FULL-INSTALL[-rN].zip.sha256
SHA256SUMS
release.json
FRESH_INSTALL_ACCEPTANCE_*.md
FRESH_INSTALL_ACCEPTANCE_*.json
```

A Manager/TUI release should contain:

```text
SOC-Automation-Manager-TUI-vA.B.C-*.zip
SOC-Automation-Manager-TUI-vA.B.C-*.zip.sha256
V*_TEST_REPORT.json
```

## Release Policy

- Never replace a published asset with different content under the same name.
- Never reuse a published checksum after rebuilding or renaming an artifact.
- Keep historical releases available.
- Mark only the newest validated Full Installer as **Latest**.
- Do not mark Manager/TUI-only updates as the main Latest release.
- Publish Indonesian and English documentation with every update.
- Publish incremental patches only for explicitly supported source versions.

## Superseded Internal Builds

- Manager/TUI v1.27.9: generated-installer newline defect.
- Manager/TUI v1.27.10: non-interactive launcher validation inherited the primary installation environment.
- Manager/TUI v1.27.11: recommended cumulative update.

## Public Portfolio Boundary

This repository is intentionally limited to sanitized release distribution and public-safe metadata. Development workspaces, production configuration, internal endpoints, operational allowlists, raw evidence, databases, logs, and backups remain outside this repository.

## Documentation

Complete operational documentation:

https://christiandimasvidillah.github.io/soc-automation-docs/
