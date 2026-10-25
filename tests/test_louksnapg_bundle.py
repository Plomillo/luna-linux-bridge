import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "louksnapg_bundle.py"
SPEC = importlib.util.spec_from_file_location("louksnapg_bundle", MODULE_PATH)
bundle = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(bundle)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LouksnapgBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "LOUKSNAMEJORADA.md"
        self.cajita = self.root / "CajitadeLuna.md"
        self.doc = self.root / "Louksna1.md"
        self.runtime = self.root / "CAJITA_LUNA_RUNTIME_V10.macrodown"
        self.output = self.root / "LOUKSNAPG.md"

        self.source_bytes = b"# protected architecture\nIMMUTABLE=TRUE\n"
        self.cajita_bytes = b"# Cajita Runtime V10\nROUTE=READY\n"
        self.source.write_bytes(self.source_bytes)
        self.cajita.write_bytes(self.cajita_bytes)
        self.doc.write_bytes(
            self.source_bytes
            + b"\n---\n# Unification marker\n\n# Documento central del runtime Cajita de Luna (copia literal)\n\n"
            + self.cajita_bytes
        )
        self.runtime_rows = [
            ("cajita_runtime.py", b"def main():\n    return 0\n", "DEFLATED"),
            ("cajita_router.py", b"ROUTE_TABLE = 21\n", "DEFLATED"),
            ("model.bin", b"\x00\x01\x02runtime-bytes", "STORED"),
        ]
        files = [
            {"path": name, "size_bytes": len(data), "sha256": sha(data), "zip_method": method}
            for name, data, method in self.runtime_rows
        ]
        manifest = {
            "schema": "CAJITA_RUNTIME_MACRODOWN/1.0",
            "candidate_id": "CAJITA_TEST_CANDIDATE",
            "files": files,
        }
        with zipfile.ZipFile(self.runtime, "w", allowZip64=True) as zf:
            for name, data, method in self.runtime_rows:
                compression = zipfile.ZIP_STORED if method == "STORED" else zipfile.ZIP_DEFLATED
                zf.writestr(name, data, compress_type=compression)
            zf.writestr(
                "MACRODOWN_MANIFEST.json",
                json.dumps(manifest, sort_keys=True).encode(),
                compress_type=zipfile.ZIP_DEFLATED,
            )

    def tearDown(self):
        self.temp.cleanup()

    def build(self, cap=bundle.DEFAULT_MAX_BYTES):
        return bundle.build_bundle(
            self.doc,
            self.runtime,
            self.output,
            self.source,
            self.cajita,
            max_bytes=cap,
        )

    def test_builds_one_zip_container_with_document_and_runtime_members(self):
        report = self.build()
        self.assertEqual(report["integrity_status"], "PASS")
        self.assertLessEqual(report["bundle_bytes"], bundle.DEFAULT_MAX_BYTES)
        self.assertEqual(report["global_certification"], "NOT_GRANTED")
        self.assertTrue(zipfile.is_zipfile(self.output))
        with zipfile.ZipFile(self.output) as zf:
            names = set(zf.namelist())
            self.assertIn("Louksna1.md", names)
            self.assertIn("cajita_runtime.py", names)
            self.assertIn("cajita_router.py", names)
            self.assertIn("model.bin", names)
            self.assertIn("MACRODOWN_MANIFEST.json", names)
            self.assertIn("LOUKSNAPG_MANIFEST.json", names)
            self.assertNotIn("CAJITA_LUNA_RUNTIME_V10.macrodown", names)
            self.assertEqual(zf.read("Louksna1.md"), self.doc.read_bytes())

    def test_independent_reverification_detects_member_hash_change(self):
        self.build()
        tampered = self.root / "tampered.md"
        with zipfile.ZipFile(self.output) as zin, zipfile.ZipFile(tampered, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "cajita_router.py":
                    data += b"# tamper"
                zout.writestr(info.filename, data)
        with self.assertRaisesRegex(ValueError, "CRC_FAILURE|HASH_OR_SIZE_MISMATCH|MEMBER_SET"):
            bundle.verify_bundle(tampered)

    def test_hard_byte_cap_is_enforced_and_candidate_removed(self):
        with self.assertRaisesRegex(ValueError, "LOUKSNAPG_OVER_CAP"):
            self.build(cap=1)
        self.assertFalse(self.output.exists())

    def test_protected_prefix_cannot_drift(self):
        wrong = self.root / "wrong-source.md"
        wrong.write_bytes(b"# changed architecture\n")
        with self.assertRaisesRegex(ValueError, "PREFIX_NOT_BYTE_EXACT"):
            bundle.build_bundle(self.doc, self.runtime, self.output, wrong, self.cajita)
        self.assertFalse(self.output.exists())

    def test_runtime_member_hash_is_checked_before_release(self):
        broken = self.root / "broken.macrodown"
        with zipfile.ZipFile(self.runtime) as zin, zipfile.ZipFile(broken, "w") as zout:
            for info in zin.infolist():
                payload = zin.read(info.filename)
                if info.filename == "cajita_runtime.py":
                    payload += b"# altered without manifest update"
                zout.writestr(info.filename, payload)
        with self.assertRaisesRegex(ValueError, "CRC_FAILURE|HASH_OR_SIZE_MISMATCH"):
            bundle.build_bundle(self.doc, broken, self.output, self.source, self.cajita)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
