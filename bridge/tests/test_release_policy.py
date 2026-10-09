"""Release-policy regression tests for fail-closed packaging and provisioning."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROVISIONER = (ROOT / "scripts/provision-mtls-local.sh").read_text()
WORKFLOW = (ROOT / ".github/workflows/louksna-debian-package.yml").read_text()
SERVICE = (ROOT / "bridge/deploy/louksna-mtls-readonly.service.in").read_text()
CONTROL = (ROOT / "debian/control").read_text()
REPORT = (ROOT / "docs/ROOT_CAUSE_REMEDIATION_0.4.0-3.md").read_text()
MTLS_DOC = (ROOT / "bridge/MTLS_READONLY_GATEWAY.md").read_text()


class ReleasePolicyTests(unittest.TestCase):
    def test_provisioner_never_recursively_deletes_partial_state(self):
        self.assertNotIn("rm -rf", PROVISIONER)
        self.assertIn('rmdir "$TLS"', PROVISIONER)
        self.assertIn('rmdir "$CLIENT"', PROVISIONER)
        self.assertIn('trap cleanup EXIT', PROVISIONER)

    def test_signal_handlers_exit_through_exit_cleanup(self):
        self.assertIn("trap 'exit 129' HUP", PROVISIONER)
        self.assertIn("trap 'exit 130' INT", PROVISIONER)
        self.assertIn("trap 'exit 143' TERM", PROVISIONER)

    def test_client_directory_is_root_private_until_validation(self):
        private_creation = 'install -d -o root -g root -m 0700 "$CLIENT"'
        publish_owner = 'chown "$OWNER_UID:$OWNER_GID" "$CLIENT"'
        self.assertIn(private_creation, PROVISIONER)
        self.assertIn(publish_owner, PROVISIONER)
        self.assertLess(PROVISIONER.index(publish_owner), PROVISIONER.rindex("VALIDATED=1"))

    def test_lintian_is_not_silenced_and_errors_block_release(self):
        self.assertNotIn('lintian --no-tag-display-limit "$DEB" | tee lintian.txt || true', WORKFLOW)
        self.assertIn("grep -q '^E:' lintian.txt", WORKFLOW)
        self.assertIn('"HOLD_LINTIAN"', WORKFLOW)
        self.assertIn("lintian.exit", WORKFLOW)
        self.assertIn("--tag-display-limit 0", WORKFLOW)
        self.assertIn("Install and exercise provisioner on ephemeral runner", WORKFLOW)
        self.assertIn("SERVICE_ACTIVE=false; SERVICE_ENABLED=false", WORKFLOW)
        self.assertIn("test ! -e /etc/louksna", WORKFLOW)

    def test_runtime_identity_matches_root_owned_key_policy_and_is_explicit(self):
        self.assertIn("User=root", SERVICE)
        self.assertIn("Group=root", SERVICE)
        self.assertIn("owner=os.getuid() if field==\"server_key\"", (ROOT / "bridge/mtls_gateway.py").read_text())
        self.assertIn("ProtectSystem=strict", SERVICE)
        self.assertIn("NoNewPrivileges=yes", SERVICE)
        self.assertIn("CapabilityBoundingSet=", SERVICE)
        self.assertIn("AmbientCapabilities=", SERVICE)
        self.assertIn("ProtectProc=invisible", SERVICE)
        self.assertIn("ProcSubset=pid", SERVICE)
        self.assertIn("RestrictNamespaces=yes", SERVICE)
        self.assertIn("SystemCallArchitectures=native", SERVICE)
        self.assertIn("MemoryDenyWriteExecute=yes", SERVICE)
        self.assertIn("RestrictAddressFamilies=AF_UNIX AF_INET", SERVICE)
        self.assertIn("StateDirectory=louksna/remote-bridge", SERVICE)
        self.assertIn("StateDirectoryMode=0700", SERVICE)
        self.assertIn("ReadWritePaths=@OWNER_PRIVATE_STATE@", SERVICE)
        self.assertIn("server_key (absolute root-owned private mode-0600 file", MTLS_DOC)

    def test_release_stays_blocked_without_authoritative_legal_and_contact_metadata(self):
        self.assertIn("maintainers@louksna.invalid", CONTROL)
        self.assertIn("debian/copyright", REPORT)
        self.assertIn("titular autorizado", REPORT)
        self.assertIn("G23", REPORT)
        self.assertIn("G24", REPORT)
        self.assertIn("PACKAGE_COMPONENT_INVENTORY.md", REPORT)
        self.assertIn("debian/copyright", (ROOT / "docs/PACKAGE_COMPONENT_INVENTORY.md").read_text())


if __name__ == "__main__":
    unittest.main()
