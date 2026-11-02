from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from louksnapg2_docling_q4_repair import GLOBAL_RELEASE_MAX_BYTES


class DoclingGlobalDistributionCapTests(unittest.TestCase):
    def test_docling_reconstruction_uses_authorized_louksnapg2_cap(self):
        self.assertEqual(GLOBAL_RELEASE_MAX_BYTES, 490_000_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
