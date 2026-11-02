# Incident Runbooks

For Jira outage, allow the circuit breaker to protect intake and fix connectivity before recovery. For SIEM outage, use JIRA_INTAKE_ONLY if intake must continue. For Local AI or Gemini outage, select a safe profile instead of forcing the provider. For stuck tickets, use observability, lease/cooldown/failure review, then validated reprocess. For viewer failure, verify service/tmux, bind, port, logs, restart, and hard refresh.
