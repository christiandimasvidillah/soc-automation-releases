# Architecture and Workflow

SocMaster supervises blue/green workers, heartbeat, PID, restart budget, readiness, and graceful shutdown. Only the active slot performs intake. Each ticket uses a configuration snapshot. Full flow: Jira → lease → status normalization → Alert ID → SIEM → Local AI path discovery → deterministic sanitization → privacy gate → allowlist/Gemini → output privacy → Jira decision → Telegram → audit. Cutover is atomic, drain-aware, stabilized, and failback-capable.
