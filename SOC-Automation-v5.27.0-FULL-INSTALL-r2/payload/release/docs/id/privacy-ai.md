# Privacy, Local AI, dan Gemini

## Local AI

Local AI hanya menemukan kategori dan dot-path data sensitif. Local AI tidak melakukan sanitasi dan tidak boleh menerima perintah untuk mengembalikan nilai asli.

## Deterministic sanitizer

Python menerapkan HMAC pseudonymization, structural rules, recursive redaction, controlled propagation, certificate/private-key blocking, dan residual scan.

## Privacy gate

Gemini hanya dipanggil jika `safe_for_ai=true`, residual count nol, dan audit berhasil ditulis. Kegagalan mana pun menghasilkan manual review.

## Output privacy

Keluaran AI diperiksa untuk credential, token, private key, raw identifier, dan format keputusan. Hanya output aman yang boleh menuju Jira atau Telegram.

## Mode OFF

Gemini OFF tidak boleh dianggap error. Local AI OFF tetap mengizinkan deterministic sanitizer jika profile mengizinkan. SIEM OFF membuat privacy/AI not applicable.
