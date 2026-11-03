from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import louksnapg2_anti_hallucination_probe as probe


class AntiHallucinationProbeContractTests(unittest.TestCase):
    def test_symbolic_dimensions_are_bounded_to_one(self):
        self.assertEqual(probe._fixed_shape([1, "sequence", None]), (1, 1, 1))

    def test_static_dimensions_are_preserved(self):
        self.assertEqual(probe._fixed_shape([1, 128]), (1, 128))

    def test_excessive_static_dimensions_fail_closed(self):
        with self.assertRaisesRegex(probe.ProbeError, "OUT_OF_RANGE"):
            probe._fixed_shape([1, 4096])

    def test_total_input_tensor_elements_are_bounded(self):
        with self.assertRaisesRegex(probe.ProbeError, "ELEMENT_LIMIT"):
            probe._fixed_shape([1024, 2048])

    def test_vector_is_padded_and_reshaped(self):
        import numpy as np
        value = probe._fit_vector([4, 7], (1, 4), np.int64, np)
        self.assertEqual(value.tolist(), [[4, 7, 0, 0]])

    def test_vector_is_truncated_to_declared_static_shape(self):
        import numpy as np
        value = probe._fit_vector([1, 2, 3, 4], (1, 2), np.int32, np)
        self.assertEqual(value.tolist(), [[1, 2]])

    def test_probe_constants_match_current_source_registry(self):
        self.assertEqual(probe.MODEL_BYTES, 110_516_001)
        self.assertEqual(len(probe.MODEL_SHA256), 64)
        self.assertEqual(len(probe.TOKENIZER_SHA256), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
