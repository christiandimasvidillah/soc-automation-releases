# Keamanan dan Hardening

- Viewer bind hanya 127.0.0.1 dan menolak metode tulis.
- Gunakan Content-Security-Policy, X-Frame-Options, no-store, dan nosniff.
- Secret disimpan di shared `.env` berpermission terbatas.
- Audit dan database persistent berada di shared.
- Package update memvalidasi path, hash, identity, dan minimum version.
- Jangan masukkan output command yang mengandung secret ke tiket/chat.
- Gunakan least privilege untuk Jira, SIEM, Telegram, Gemini, dan VT credential.
- Review retention policy dan backup secara berkala.
