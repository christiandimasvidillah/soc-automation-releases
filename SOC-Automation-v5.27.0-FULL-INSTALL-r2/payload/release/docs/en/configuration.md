# Configuration

The shared .env contains Jira, SIEM, Gemini, Local AI, Telegram, polling, worker, timeout, and policy settings. Secrets are never displayed. Feature flags are stored atomically with locking, revisions, hashes, backups, permissions, and audit. Configured ON differs from Effective ON; blockers, not-applicable states, and provider unavailability are shown separately. Gemini depends on SIEM retrieval and privacy sanitization.
