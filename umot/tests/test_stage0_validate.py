import base64, hashlib, tempfile, unittest, zipfile
from pathlib import Path
from stage0_validate import EXPECTED_SHA256, EXPECTED_BYTES, WHEEL_NAME, WHEEL_TAG, parse_version, safe_wheel_members, verify_record

class Stage0UnitTests(unittest.TestCase):
    def test_protected_identity_constants(self):
        self.assertEqual(len(EXPECTED_SHA256), 64)
        self.assertGreater(EXPECTED_BYTES, 0)
        self.assertTrue(WHEEL_NAME.endswith("manylinux_2_34_x86_64.whl"))
        self.assertEqual(WHEEL_TAG, "py3-none-manylinux_2_34_x86_64")
    def test_version_parser(self):
        self.assertEqual(parse_version("glibc 2.41"), (2, 41))
        self.assertEqual(parse_version("2.34"), (2, 34))
        self.assertIsNone(parse_version("unknown"))
    def test_rejects_path_traversal(self):
        ok, reason = safe_wheel_members(["umot/__init__.py", "../escape.py"])
        self.assertFalse(ok)
        self.assertIn("UNSAFE_WHEEL_MEMBER", reason)
    def test_accepts_safe_members(self):
        ok, reason = safe_wheel_members(["umot/__init__.py", "umot-1.0.dist-info/METADATA"])
        self.assertTrue(ok)
        self.assertIsNone(reason)
    def test_record_detects_tampering(self):
        payload = b"trusted"
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode().rstrip("=")
        record = f"package.py,sha256={digest},{len(payload)}\npackage-1.dist-info/RECORD,,\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.whl"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("package.py", b"tampered")
                archive.writestr("package-1.dist-info/RECORD", record)
            with zipfile.ZipFile(path) as archive:
                status, errors = verify_record(archive, "package-1.dist-info/RECORD")
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("RECORD_HASH_MISMATCH" in item for item in errors))

if __name__ == "__main__":
    unittest.main()
