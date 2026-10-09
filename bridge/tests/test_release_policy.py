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

    def test_client_identity_paths_are_written_as_owner_not_root(self):
        owner_creation = 'runuser -u "$OWNER_USER" -- mkdir -m 0700 "$CLIENT"'
        owner_keygen = 'runuser -u "$OWNER_USER" -- openssl req -new'
        owner_publish = 'runuser -u "$OWNER_USER" -- cp "$TLS/client.pem" "$CLIENT/client.pem"'
        self.assertIn(owner_creation, PROVISIONER)
        self.assertIn(owner_keygen, PROVISIONER)
        self.assertIn(owner_publish, PROVISIONER)
        self.assertIn('chmod 0644 "$TLS/client.pem"', PROVISIONER)
        self.assertNotIn('chown "$OWNER_UID:$OWNER_GID" "$CLIENT"', PROVISIONER)
        self.assertLess(PROVISIONER.index('runuser -u "$OWNER_USER" -- chmod 0700 "$CLIENT"'),
                        PROVISIONER.rindex("VALIDATED=1"))

    def test_lintian_is_not_silenced_and_errors_block_release(self):
        self.assertNotIn('lintian --no-tag-display-limit "$DEB" | tee lintian.txt || true', WORKFLOW)
        self.assertIn("grep -q '^E:' lintian.txt", WORKFLOW)
        self.assertIn('"HOLD_LINTIAN"', WORKFLOW)
        self.assertIn("lintian.exit", WORKFLOW)
        self.assertIn("--tag-display-limit 0", WORKFLOW)
        self.assertIn("Install and exercise provisioner on ephemeral runner", WORKFLOW)
        self.assertIn("SERVICE_ACTIVE=false; SERVICE_ENABLED=false", WORKFLOW)
        self.assertIn("test ! -e /etc/louksna", WORKFLOW)
        self.assertIn("PROVISIONER_FAULT_INJECTION=PASS", WORKFLOW)
        self.assertIn('test "$failure_rc" -eq 71', WORKFLOW)

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

    def test_gui_assets_are_included_in_package_build(self):
        rules = (ROOT / "debian/rules").read_text()
        self.assertIn("bridge/*.py", rules)
        self.assertIn("usr/bin/louksna", rules)
        self.assertIn("usr/share/applications/louksna-linux-bridge.desktop", rules)
        self.assertIn("python3-tk", CONTROL)

    def test_release_stays_blocked_without_authoritative_legal_and_contact_metadata(self):
        legal_audit = (ROOT / "docs/LEGAL_METADATA_AUDIT_0.4.0-3.md").read_text()
        self.assertIn("maintainers@louksna.invalid", CONTROL)
        self.assertIn("copyright holder(s)", legal_audit)
        self.assertIn("license under which the project code may be redistributed", legal_audit)
        self.assertFalse((ROOT / "debian/copyright").exists())
        self.assertIn("debian/copyright", REPORT)
        self.assertIn("titular autorizado", REPORT)
        self.assertIn("G23", REPORT)
        self.assertIn("G24", REPORT)
        self.assertIn("PACKAGE_COMPONENT_INVENTORY.md", REPORT)
        self.assertIn("Enforce distribution clearance before artifact staging", WORKFLOW)
        self.assertIn("docs/DISTRIBUTION_CLEARANCE.json", WORKFLOW)
        self.assertIn('record.get("status") != "CLEARED"', WORKFLOW)
        self.assertLess(
            WORKFLOW.index("Enforce distribution clearance before artifact staging"),
            WORKFLOW.index("Stage Debian package for artifact upload"),
        )
        self.assertTrue((ROOT / "docs/DISTRIBUTION_CLEARANCE_GATE.md").is_file())
        self.assertIn("debian/copyright", (ROOT / "docs/PACKAGE_COMPONENT_INVENTORY.md").read_text())


if __name__ == "__main__":
    unittest.main()
