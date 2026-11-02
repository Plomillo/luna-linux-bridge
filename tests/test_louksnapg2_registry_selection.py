from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from louksnapg2_custoszv9_repair_worker import select_repair_registry_path


class RepairRegistrySelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name: str) -> Path:
        path = self.root / name
        path.write_text(name, encoding="utf-8")
        return path

    def test_prefers_v3_over_v2_and_v1(self):
        self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V1.json")
        self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V2.json")
        v3 = self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V3.json")
        self.assertEqual(select_repair_registry_path(self.root), v3)

    def test_falls_back_to_v2_when_v3_is_absent(self):
        self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V1.json")
        v2 = self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V2.json")
        self.assertEqual(select_repair_registry_path(self.root), v2)

    def test_falls_back_to_v1_when_v2_and_v3_are_absent(self):
        v1 = self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V1.json")
        self.assertEqual(select_repair_registry_path(self.root), v1)

    def test_rejects_symlinked_v3_instead_of_silently_falling_back(self):
        v2 = self.write("LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V2.json")
        target = self.root / "v3-target.json"
        target.write_text("untrusted", encoding="utf-8")
        link = self.root / "LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V3.json"
        link.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, "REPAIR_REGISTRY_SYMLINK_REJECTED"):
            select_repair_registry_path(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
