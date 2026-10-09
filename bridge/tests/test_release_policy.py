"""Release-policy regression tests for fail-closed packaging and provisioning."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROVISIONER = (ROOT / "scripts/provision-mtls-local.sh").read_text()
WORKFLOW = (ROOT / ".github/workflows/louksna-debian-package.yml").read_text()


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
        self.assertLess(PROVISIONER.index("VALIDATED=1"), PROVISIONER.index(publish_owner))

    def test_lintian_is_not_silenced_and_errors_block_release(self):
        self.assertNotIn("lintian --no-tag-display-limit \"$DEB\" | tee lintian.txt || true", WORKFLOW)
        self.assertIn('grep -q \'^E:\' lintian.txt', WORKFLOW)
        self.assertIn('"HOLD_LINTIAN"', WORKFLOW)
        self.assertIn("lintian.exit", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
