# SOC Automation Platform

[![Latest Release](https://img.shields.io/github/v/release/christiandimasvidillah/soc-automation-releases?label=latest&color=2ea44f)](https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest)
[![Documentation](https://img.shields.io/badge/documentation-online-0969da)](https://christiandimasvidillah.github.io/soc-automation-docs/)
[![Release Channel](https://img.shields.io/badge/channel-stable-2ea44f)](https://github.com/christiandimasvidillah/soc-automation-releases/releases)
[![Languages](https://img.shields.io/badge/docs-Indonesia%20%7C%20English-8250df)](https://christiandimasvidillah.github.io/soc-automation-docs/)

A privacy-first cybersecurity automation portfolio project for Security Operations Center workflows.

> **Designed, built, and maintained by Dimas Vidillah Christian**

---

## Latest Stable Release

**SOC Automation v5.27.0** — `LATEST`

| Component | Version |
|---|---:|
| Runtime | v5.27.0 |
| Manager/TUI | v1.27.8 |
| Channel | Stable |
| Package type | Full Installation |
| Documentation | Indonesia and English |

### Download

[v5.27.0](https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest)

The latest release page provides:

- Full Installation ZIP package
- SHA-256 checksum
- Combined checksum metadata
- Release metadata
- Installation instructions
- Security-validation summary

---

## Project Overview

SOC Automation is a Python-based Security Operations Center automation platform designed to simplify repetitive alert-handling workflows while maintaining privacy, auditability, operational control, and fail-closed behavior.

The platform combines:

- Jira ticket orchestration
- SIEM alert retrieval and lifecycle handling
- Deterministic privacy sanitization
- Local AI sensitive-data detection
- Gemini-assisted security analysis behind a privacy gate
- VirusTotal enrichment
- Approved-sharing allowlists
- Background Auto-FP with guardrails
- Manual False-Incident reconciliation
- Telegram notifications
- Terminal and web operational dashboards
- Transactional updates and rollback
- Secure Full Installer generation
- Bilingual operational documentation

---

## Problems Addressed

The project was designed to address several recurring SOC operational challenges:

- Repetitive alert-triage workflows
- Manual switching between ticketing and SIEM platforms
- Inconsistent False Positive handling
- Risk of sending sensitive evidence to external AI providers
- Limited visibility into automation workers and ticket queues
- Duplicate ticket processing
- Unsafe or non-reproducible software distribution
- Complex upgrade, rollback, and recovery procedures
- Incomplete operational documentation

---

## Architecture Overview

```text
Jira Ticket Intake
        |
        v
Assignment, Locking, and Workflow Control
        |
        v
Feature and AI Control Center
        |
        +---- Jira Intake Only
        |       |
        |       +---- Waiting for User Confirmation
        |       +---- Telegram Notification
        |
        +---- Full Analysis Pipeline
                |
                v
            SIEM Evidence
                |
                v
      Deterministic Sanitization
                |
                v
      Local AI Sensitive Detection
                |
                v
             Privacy Gate
                |
                v
          Gemini Analysis
                |
                v
        Policy and Risk Decision
                |
        +-------+--------+
        |       |        |
        v       v        v
      Jira     SIEM   Telegram
```

---

## Privacy-First AI Pipeline

The automation separates privacy functions into distinct layers:

1. Raw SIEM evidence is retrieved only when the effective feature profile permits it.
2. Deterministic Python sanitization removes or pseudonymizes sensitive values.
3. Local AI is used to detect residual sensitive information.
4. A privacy gate blocks unsafe payloads.
5. Gemini receives only evidence that passes the privacy controls.
6. Audit records document each processing stage without exposing secrets.

When AI processing is disabled, the automation can remain operational in Jira Intake Only mode without retrieving raw SIEM JSON or calling an AI provider.

---

## Main Capabilities

### Ticket Automation

- Jira polling
- Account assignment
- Workflow normalization
- Persistent ticket locking
- Retry and recovery handling
- Idempotent processing
- Ticket history and observability

### SIEM Integration

- Alert evidence retrieval
- Alert identity validation
- Scoped correlation
- False Positive alert closure
- Fail-closed error handling

### AI and Privacy

- Deterministic sanitization
- Local AI residual-sensitive-data detection
- Gemini analysis
- Configurable AI feature states
- Per-ticket feature snapshots
- Privacy-gate enforcement

### Automatic Response

- Background Auto-FP
- Shadow, Approval, Limited, and Global modes
- Candidate identity binding
- Rate limiting
- Circuit breakers
- Manual False-Incident reconciliation
- Jira and SIEM state verification

### Operations

- Curses-based TUI
- Status Web Viewer
- Bilingual Documentation Viewer
- Start All and Graceful Stop All
- Blue/green runtime control
- Backup verification
- Transactional deployment
- Rollback
- Diagnostics and maintenance

---

## Safe Full Installer

Every published Full Installer must pass:

- Explicit active-file allowlisting
- Secret-pattern scanning
- Synthetic security-fixture validation
- Backup and obsolete-source exclusion
- Production-state exclusion
- Python compilation
- Internal SHA-256 verification
- Manifest integrity validation
- ZIP integrity validation

The v5.27.0 Full Installer passed all required controls with zero secret findings.

### v5.27.0 Full Installer SHA-256

```text
8c07e00097fd0758c95a9cc59ed249a874dc74055026302663dcc2915359cb71
```

Always verify the checksum before installation.

---

## Installation

Download the latest stable release:

https://github.com/christiandimasvidillah/soc-automation-releases/releases/latest

Verify the downloaded package:

```bash
sha256sum -c \
  SOC-Automation-v5.27.0-FULL-INSTALL.zip.sha256
```

Extract the package:

```bash
unzip \
  SOC-Automation-v5.27.0-FULL-INSTALL.zip
```

Enter the extracted directory:

```bash
cd SOC-Automation-v5.27.0-FULL-INSTALL
```

Install using the default root:

```bash
python3 install.py
```

The default installation root is:

```text
~/SOC-Automation
```

To use a custom installation root:

```bash
python3 install.py \
  --root /path/to/SOC-Automation
```

After installation:

1. Create the local production configuration from `config/env.example`.
2. Store credentials only in the local environment.
3. Run configuration preflight.
4. Run privacy and Local AI diagnostics.
5. Start with controlled or shadow modes.
6. Validate Jira, SIEM, Telegram, and AI integrations.
7. Review the complete documentation before enabling automatic actions.

---

## Documentation

The complete bilingual documentation is available at:

https://christiandimasvidillah.github.io/soc-automation-docs/

### Languages

- Bahasa Indonesia — primary and default
- English — secondary

The documentation covers:

- Architecture
- Complete installation
- Configuration
- TUI reference
- Jira and SIEM integration
- Privacy and AI processing
- Auto-FP and reconciliation
- Daily operations
- Security and hardening
- Testing and acceptance
- Update, backup, and rollback
- Troubleshooting
- Version history

---

## Skills Demonstrated

- Python
- Linux and WSL
- Cybersecurity automation
- Security Operations workflows
- Jira REST API integration
- SIEM integration
- Privacy engineering
- Local AI integration
- Gemini integration
- Threat-intelligence enrichment
- SQLite
- Curses TUI development
- Background services
- Blue/green runtime operations
- Transactional deployment
- Rollback engineering
- Secure software distribution
- GitHub Pages
- GitHub Releases
- Bilingual technical documentation

---

## Security Notice

This public repository is intended only for sanitized release distribution.

The repository must never contain:

- Production `.env` files
- API keys or access tokens
- Jira or SIEM credentials
- Telegram, Gemini, or VirusTotal credentials
- Private keys
- Raw SIEM evidence
- Production ticket data
- Production databases
- Operational audit logs
- Internal allowlists
- Production backups

If sensitive information is discovered, stop distribution and follow the security-reporting process.

---

## Release Policy

A release is published only when:

- Runtime validation passes
- Manager/TUI validation passes
- Documentation is updated in Indonesian and English
- Version history is updated
- Secret scanning passes
- Package integrity passes
- Installation instructions are available
- Rollback or recovery guidance is documented

---

## Ownership

**Designed, built, and maintained by Dimas Vidillah Christian**

Cybersecurity automation portfolio project focused on:

- Security Operations
- Incident-triage automation
- Privacy-preserving AI
- Operational observability
- Controlled automated response
- Secure release engineering
