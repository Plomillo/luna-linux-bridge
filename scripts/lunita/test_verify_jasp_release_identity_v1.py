import unittest

import verify_jasp_release_identity_v1 as identity


class JaspReleaseIdentityTests(unittest.TestCase):
    def test_self_test_passes_all_positive_and_negative_contracts(self):
        result = identity.self_test()
        self.assertEqual("PASS", result["status"])
        self.assertTrue(all(result["checks"].values()))

    def test_git_blob_identity_uses_git_object_header(self):
        self.assertEqual(
            "9daeafb9864cf43055ae93beb0afd6c7d144bfa4",
            identity.git_blob_sha1(b"test\n"),
        )

    def test_public_version_normalizes_only_fourth_zero(self):
        self.assertEqual("0.98.8", identity.normalize_project_version("0.98.8.0"))
        self.assertEqual("0.98.8", identity.normalize_project_version("0.98.8"))

    def test_rejects_nonzero_fourth_component(self):
        with self.assertRaises(identity.IdentityError):
            identity.normalize_project_version("0.98.8.1")


if __name__ == "__main__":
    unittest.main()
