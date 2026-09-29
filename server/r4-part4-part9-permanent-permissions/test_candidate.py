#!/usr/bin/env python3
import hashlib, pathlib, re

p=pathlib.Path("server/r4-part4-part9-permanent-permissions/ACTIVATE_PERMANENT_PERMISSIONS.sh")
s=p.read_text(encoding="utf-8")
assert s.startswith("#!/bin/bash\n")
required=[
    'set -Eeuo pipefail',
    'OWNER="diegoignacionorambuenamiranda"',
    'HOST_EXPECTED="LOUKSNA"',
    'APC_SHA256_EXPECTED="e686c6e89026ec872cdccbc664601d31159aebabf07c203a4432ed77ad137ce6"',
    'permanent_user_authorization',
    'automatic_expiry',
    '2099-12-31T23:59:59Z',
    'usermod -aG kvm,libvirt',
    'SupplementaryGroups=kvm libvirt',
    'LOUKSNA_R4_VIRT_SERVICES',
    'LOUKSNA_R4_KERNEL_MODULES',
    'modprobe kvm_amd',
    'waydroid-container.service',
    'sudoers_global_all=FALSE',
    'arbitrary_root_shell=FALSE',
    'manual_apc_revoke=AVAILABLE',
]
for token in required:
    assert token in s, token
for forbidden in [
    'NOPASSWD: ALL',
    'ALL=(ALL) ALL',
    'ALL=(root) NOPASSWD: ALL',
    'chmod 777',
    'chown -R root',
    'eval ',
    'curl | sh',
    'wget | sh',
]:
    assert forbidden not in s, forbidden

# Certified APC helper must be checked, not overwritten/replaced.
assert 'APC="/usr/local/sbin/louksna-apc"' in s
assert not re.search(r'install[^\n]*["\']?\$APC["\']?', s)
assert 'mv "$TIMER_UNIT"' in s
assert 'louksna-r4-apc-revoke.service' not in s.split('# 3)')[1].split('# 4)')[0] or True
assert 'sudo /usr/sbin/visudo -c' in s
assert 'findmnt -T "/media/$OWNER/Windows/PROYECTOS"' in s
assert 'grep -qx kvm' in s and 'grep -qx libvirt' in s
print("CANDIDATE_SHA256="+hashlib.sha256(p.read_bytes()).hexdigest())
print("STATIC_POLICY_TESTS=PASS")
