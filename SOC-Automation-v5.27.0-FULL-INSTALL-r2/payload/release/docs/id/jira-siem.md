# Jira dan SIEM

## Intake Jira

JQL mengembalikan tiket sesuai project/status. Assignee dinormalisasi ke automation account. Open melewati L1 Analysis lalu Waiting; L1 menuju Waiting; Waiting dapat langsung diproses.

## Alert identity

Custom Alert ID adalah sumber otoritatif. Fallback terkontrol: alert link, named fields, lalu seluruh fields. Identity digunakan untuk SIEM fetch, audit binding, dan close verification.

## Jira result

Analysis field menerima hasil yang sudah melewati output privacy. Decision gate menerima hanya prefix dan semantics yang diizinkan. Bahasa ambigu mencegah auto-close.

## SIEM close

Urutan wajib: Jira False Incident → Jira Done → verifikasi status → SIEM close dengan reason False Positive. Bila Jira gagal, SIEM tidak boleh ditutup.

## Partial state

Jika Jira selesai tetapi SIEM close gagal, tulis partial audit/recovery state dan retry terkontrol. Jangan mengulang Jira transition secara buta.
