# Privacy dan AI Safety

## Trust boundary
1. Raw evidence adalah data tidak tepercaya.
2. Local AI hanya boleh mengembalikan category, dot-path, confidence, reason code; tidak boleh mengembalikan nilai asli.
3. Python menerapkan pseudonimisasi HMAC, structural redaction, controlled propagation, dan residual scan.
4. Payload hanya boleh menuju Gemini bila safe_for_ai=true dan residual_count=0.
5. Keluaran Gemini diperiksa lagi sebelum Jira/Telegram.

## Fail closed
Path tidak valid, residual sensitif, blob sertifikat/private key, prefix AI tidak valid, atau bahasa FALSE POSITIVE yang ambigu semuanya menghasilkan blocking/manual review.

## Data yang tidak boleh masuk paket
.env, token, credential, raw SIEM JSON, attachment tiket, database produksi, private key, dan certificate private key.
