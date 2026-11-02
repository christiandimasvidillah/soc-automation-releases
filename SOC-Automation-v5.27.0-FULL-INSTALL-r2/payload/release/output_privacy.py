from __future__ import annotations
import re
from dataclasses import dataclass

FALLBACK = "AI analysis completed, but the generated output was withheld because it contained restricted technical data. Review the sanitized audit record locally."

HIGH_RISK = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(r"-----BEGIN (?:CERTIFICATE REQUEST|CERTIFICATE|ATTESTATION DATA|ATTESTATION SIGNATURE|VM IDENTITY|PUBLIC KEY)-----", re.I),
    re.compile(r"\b(?:client_secret|access_token|refresh_token|bootstrap_key|private_key)\b\s*[:=]", re.I),
    re.compile(r"\b[A-Za-z0-9+/]{256,}={0,2}\b"),
]
REPLACEMENTS = [
    (re.compile(r"\b(?:USER|ACCOUNT|IDENTITY)_[A-Za-z0-9_-]+\b", re.I), "an identity"),
    (re.compile(r"\bIP_[A-Za-z0-9_-]+\b", re.I), "the source address"),
    (re.compile(r"\b(?:PROJECT|CLOUD_ACCOUNT|CLOUD_ACCOUNT_ID)_[A-Za-z0-9_-]+\b", re.I), "the cloud project"),
    (re.compile(r"\bCLUSTER_[A-Za-z0-9_-]+\b", re.I), "the Kubernetes cluster"),
    (re.compile(r"\b(?:HOST|INSTANCE|ASSET|SYSTEM|AGENT|EVENT|ALERT|INDEX|URL|RESOURCE|TOKEN|CERT|RULE|EXECUTION|ANCESTOR|FINDING|DATA_OBJECT)_[A-Za-z0-9_-]+\b", re.I), "the affected resource"),
    (re.compile(r"\bX509SHA256=[A-Fa-f0-9]{32,}\b"), "the certificate credential"),
    (re.compile(r"\b[0-9a-fA-F]{40,128}\b"), "the technical identifier"),
    (re.compile(r"\bhttps?://\S+", re.I), "the referenced service"),
    (re.compile(r"\b[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "an identity"),
    (re.compile(r"(?<![A-Za-z0-9_])(?:\d{1,3}\.){3}\d{1,3}(?![A-Za-z0-9_])"), "the source address"),
]
RESIDUAL = re.compile(r"\b(?:USER|IP|HOST|PROJECT|CLUSTER|INSTANCE|AGENT|EVENT|ALERT|INDEX|URL|RESOURCE|TOKEN|CERT|SYSTEM|ASSET|CLOUD_ACCOUNT)_[A-Za-z0-9_-]+\b", re.I)

@dataclass(frozen=True)
class OutputPrivacyResult:
    text: str
    safe: bool
    withheld: bool
    replacements: int


def sanitize_ai_output(text: str) -> OutputPrivacyResult:
    value = " ".join(str(text or "").split())
    if any(pattern.search(value) for pattern in HIGH_RISK):
        return OutputPrivacyResult(FALLBACK, False, True, 0)
    count = 0
    for pattern, replacement in REPLACEMENTS:
        value, n = pattern.subn(replacement, value)
        count += n
    if RESIDUAL.search(value) or any(pattern.search(value) for pattern in HIGH_RISK):
        return OutputPrivacyResult(FALLBACK, False, True, count)
    return OutputPrivacyResult(value, True, False, count)
