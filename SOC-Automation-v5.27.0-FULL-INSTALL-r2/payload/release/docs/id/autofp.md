# Auto-FP dan Manual Reconciliation

## SMB evidence

Rule yang didukung adalah Rare SMB Connection to the Internet. Correlation harus terikat host, process entity, source, destination port, rule, dan time window. Scoped fan-out destination dianalisis sebagai satu cluster.

## No-observed-success

Eligible hanya jika tidak ada established, authentication, transfer, atau success evidence; VT cluster bersih; serta tidak ada high-risk host/user atau high/critical alert blocker.

## Controlled Auto-FP

Memerlukan kill switch, project scope, eligible policy, dan rate limit per jam/hari. Dry-run menghasilkan `WOULD_APPLY` tanpa mutasi.

## Background Auto-FP

Mode DISABLED, SHADOW, APPROVAL, LIMITED, GLOBAL. Candidate memiliki ticket/evidence binding, TTL, hash, alert UUID, dan idempotency key. Circuit breaker membatasi kegagalan berulang.

## Manual False-Incident

Scope: project CSOC, status False Incident, current user/assignee. Validasi analysis, raw audit, identity, status, lalu Jira Done dan SIEM close. Partial failure masuk recovery flow.
