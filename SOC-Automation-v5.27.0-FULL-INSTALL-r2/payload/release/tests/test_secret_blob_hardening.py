from __future__ import annotations
import json
from privacy_manager import PrivacyManager
payload={"data":{"asset_tags":{
 "system":"SYSTEM_aaaaaaaaaaaa",
 "configure-sh":"#!/bin/bash\nACCESS_TOKEN=real-token-value\nBEGIN RSA PRIVATE KEY",
 "user-data":"#cloud-config\nKUBE_PROXY_TOKEN: real-proxy-token",
 "ssh-keys":"ubuntu:ssh-rsa AAAAB3NzaSensitiveKey",
 "kube-env":"TPM_BOOTSTRAP_KEY: VERY_SECRET_PRIVATE_KEY\nCA_CERT: CERTDATA",
 "kubeconfig":"users: token: real-kube-token",
 "kubelet-config":"serverTLSBootstrap: true",
 "cluster-uid":"0123456789abcdef",
 "goog-fleet-project":"183026177251"
},"asset_vpcs":["projects/private-project/global/networks/prod-vpc"],
"business_units":[{"name":"Internal Security Team"}],
"findings":{"FimEvents":[{"id":"private-fim-id","name":"/root/.ssh/authorized_keys","EventType":"File Changed"}]}}}
result=PrivacyManager().prepare_payload(ticket_key='TEST-RC4',raw_json=json.dumps(payload))
text=result.sanitized_json; out=json.loads(text)
for key in ('configure-sh','user-data','ssh-keys','kube-env','kubeconfig','kubelet-config'):
 assert out['data']['asset_tags'][key]=='[REDACTED_SENSITIVE_BLOB]', key
for secret in ('real-token-value','PRIVATE KEY','real-proxy-token','AAAAB3NzaSensitiveKey','VERY_SECRET_PRIVATE_KEY','real-kube-token','private-project','Internal Security Team','private-fim-id'):
 assert secret not in text, secret
assert '/root/.ssh/authorized_keys' in text
assert result.safe_for_ai, result.residual_categories
assert result.residual_count == 0, result.residual_categories
print('Secret blob and idempotency hardening tests: OK')
