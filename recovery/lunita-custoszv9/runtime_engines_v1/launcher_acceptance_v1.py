from __future__ import annotations

import hashlib
import pathlib
import tempfile
import unittest
from unittest import mock

import lunita_beta_v1_8 as launcher


class LunitaBetaV18Tests(unittest.TestCase):
    def test_runtime_environment_is_overlay_scoped(self):
        env = launcher.runtime_environment({})
        self.assertIn("/opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages",
                      env["PYTHONPATH"])
        self.assertEqual("/opt/lunita/engines/runtime_engines_v1/model-cache/fastembed",
                         env["LUNITA_FASTEMBED_CACHE"])
        self.assertEqual("/var/lib/lunita/vectors", env["LUNITA_VECTOR_DB_PATH"])
        self.assertEqual("1", env["HF_HUB_DISABLE_TELEMETRY"])

    def test_v17_legacy_launcher_digest_is_explicitly_pinned(self):
        self.assertEqual(64, len(launcher.LEGACY_SHA256))
        self.assertEqual("46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2",
                         launcher.LEGACY_SHA256)

    def test_status_reports_candidate_not_certification(self):
        status = launcher.engine_status()
        self.assertEqual("RUNTIME_CANDIDATE", status["status"])
        self.assertEqual("NOT_GRANTED", status["canonical_certification"])
        self.assertEqual(15, status["engine_registry"]["engine_count"])
        self.assertEqual(14, len(status["command_agents"]))

    def test_legacy_hash_verifier_detects_modified_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate = pathlib.Path(temporary) / "lunita_beta_v1_7.py"
            candidate.write_text("legacy fixture\n", encoding="utf-8")
            expected = hashlib.sha256(candidate.read_bytes()).hexdigest()
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", candidate), \
                 mock.patch.object(launcher, "LEGACY_SHA256", expected):
                self.assertEqual(expected, launcher.sha256_file(candidate))
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", candidate), \
                 mock.patch.object(launcher, "LEGACY_SHA256", "0" * 64):
                self.assertNotEqual(launcher.LEGACY_SHA256, launcher.sha256_file(candidate))


if __name__ == "__main__":
    unittest.main(verbosity=2)
