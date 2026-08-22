# SOC Automation {{RELEASE_VERSION}}

> **{{RELEASE_STATUS}}**

**Runtime:** {{RUNTIME_VERSION}}  
**Manager/TUI:** {{MANAGER_TUI_VERSION}}  
**Release type:** {{RELEASE_TYPE}}  
**Owned by:** Dimas Vidillah Christian  

## Summary

{{SUMMARY}}

## Choose a Package

### New installation

Download the Full Installer ZIP and checksum.

### Existing installation

Use the incremental runtime update or cumulative Manager/TUI update only when the source version is explicitly supported.

## Changes

{{CHANGELOG}}

## Security Validation

```text
Active source scan             : PASS
Installer package scan         : PASS
Secret findings                : 0
Generated installer compile    : PASS
Extracted installer compile    : PASS
Internal checksums             : PASS
ZIP integrity                  : PASS
Default-root installation      : PASS
Custom-root installation       : PASS
Automatic root detection       : PASS
```

## Verify

```bash
sha256sum -c {{CHECKSUM_FILE}}
```

## Install

```bash
unzip {{PACKAGE_FILE}}
cd {{EXTRACTED_DIRECTORY}}
python3 install.py
```

Custom root:

```bash
python3 install.py --root "$HOME/SOC-Automation-Custom-Test"
```

## Documentation

https://christiandimasvidillah.github.io/soc-automation-docs/

## Notes

- Run the curses TUI directly in an interactive terminal.
- Do not apply a Full Installer through Incremental Update Manager.
- Do not publish credentials, raw evidence, databases, logs, or backups.
