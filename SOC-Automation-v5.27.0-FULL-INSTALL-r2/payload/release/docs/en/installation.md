# Full Automation Installation

Prepare WSL/Linux, a non-root service user, Python venv/pip, tmux, systemd user services, network access to configured providers, Local AI when enabled, and sufficient persistent disk. Create releases/current/manager/shared/.venv structure; keep persistent state under shared. Install requirements in the virtual environment, create shared/.env with 0600 permission, install optional user services, run configuration/health/privacy/readiness preflights, then Start All through the TUI in safe SHADOW modes. Accept only one active worker, healthy SQLite, passing privacy tests, and localhost-only viewers.

<!-- custom-root-launcher-v1.27.9 -->
## Custom root and root-aware launcher

Starting with Manager/TUI v1.27.9, installations created with `python3 install.py --root <path>` persist the effective root in `.installation-root`. The `manager/soc-tui` launcher resolves the root from `--root`, `SOC_AUTOMATION_ROOT`, installation metadata, or its own location.

<!-- cumulative-installer-generation-v1.27.10 -->
## Manager/TUI v1.27.10 - Custom-root installation

Cumulative patch v1.27.10 can be installed directly from v1.27.8 or v1.27.9. The installer uses `chr(10)` for root metadata and validates generated `install.py` before distribution.

<!-- cumulative-installer-generation-v1.27.11 -->
## Manager/TUI v1.27.10 - Custom-root installation

Cumulative patch v1.27.10 can be installed directly from v1.27.8 or v1.27.9. The installer uses `chr(10)` for root metadata and validates generated `install.py` before distribution.
