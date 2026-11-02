# Privacy, Local AI, and Gemini

Local AI discovers sensitive categories and paths only. Python performs HMAC pseudonymization, structural redaction, controlled propagation, restricted-blob handling, and residual scanning. Gemini is called only when safe_for_ai is true and residual count is zero. AI output is checked again for secrets, identifiers, and decision format. Provider-off states are supported and are not automatically errors.
