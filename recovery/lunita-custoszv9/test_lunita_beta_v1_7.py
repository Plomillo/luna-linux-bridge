import ast
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "recovery/lunita-custoszv9/lunita_beta_v1_7.py"
PROVENANCE = ROOT / "recovery/lunita-custoszv9/BETA_PROVENANCE_v1_7.json"
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)


def function_source(name):
    node = next(
        (n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name),
        None,
    )
    if node is None:
        raise AssertionError(f"missing function: {name}")
    return ast.get_source_segment(TEXT, node)


class LunitaBetaV17ContractTests(unittest.TestCase):
    def test_launcher_compiles_and_hash_matches_provenance(self):
        compile(TEXT, str(SOURCE), "exec")
        evidence = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["beta_revision"], "beta-v1.7")
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), evidence["beta_launcher_sha256"])
        self.assertFalse(evidence["exact_frozen_launcher_match"])
        self.assertEqual(evidence["certification"], "NOT_GRANTED")

    def test_original_pre_g05_source_hash_is_preserved(self):
        evidence = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(
            evidence["source_sha256"],
            "dc7d673b16a578c5cc94999856ed4b70d0b039702155779660a1083e2da54066",
        )
        self.assertTrue(evidence["source_frozen_launcher_unchanged"])

    def test_jasp_commit_pin_matches_the_observed_candidate_deployment(self):
        expected = "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
        self.assertIn("'org.jaspstats.JASP':'" + expected + "'", TEXT)
        self.assertNotIn(
            "'org.jaspstats.JASP':'83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e284de3df7'",
            TEXT,
        )

    def test_jamovi_commit_pin_matches_the_observed_candidate_deployment(self):
        self.assertIn(
            "'org.jamovi.jamovi':'4685c60d99398dc687837d58f370b31e01edc160c2e3bbd3d4b204a20b249fab'",
            TEXT,
        )

    def test_flatpak_uses_supported_commit_query_and_system_flathub_checks(self):
        body = function_source("flatpak_check")
        self.assertIn("--show-commit", body)
        self.assertNotIn("--show-version", body)
        self.assertIn("Installation: system", body)
        self.assertIn("Origin: flathub", body)

    def test_flatpak_sandbox_smoke_fails_closed(self):
        body = function_source("flatpak_check")
        self.assertIn("return 0 if q.returncode==0 else 3", body)
        self.assertIn("finally:shutil.rmtree(h,ignore_errors=True)", body)

    def test_brujula_has_scoped_writable_temporary_home(self):
        body = function_source("brujula")
        self.assertIn("tempfile.mkdtemp(prefix='lunita-brujula-home-',dir='/tmp')", body)
        self.assertIn("'HOME':h", body)
        self.assertIn("'XDG_CACHE_HOME':h+'/cache'", body)
        self.assertIn("'XDG_CONFIG_HOME':h+'/config'", body)
        self.assertIn("'XDG_DATA_HOME':h+'/data'", body)
        self.assertIn("finally:shutil.rmtree(h,ignore_errors=True)", body)

    def test_qwen_invocation_is_bounded(self):
        body = function_source("qwen")
        for token in ("'-t','1'", "'-c','256'", "'-b','64'", "'-ub','32'", "'--no-warmup'", "timeout=90"):
            self.assertIn(token, body)
        self.assertNotIn("'0' if mode=='load'", body)

    def test_r_selftest_checks_exact_version(self):
        self.assertIn('getRversion())=="4.6.1"', function_source("rcheck"))

    def test_fault_injection_handles_missing_executable_without_side_effects(self):
        body = function_source("fault")
        self.assertIn("FileNotFoundError", body)
        self.assertIn("missing", body)

    def test_provenance_preserves_explicit_regression_blocker(self):
        evidence = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["post_patch_validation"]["runtime_gate"], "PASS_RUNTIME_TESTS")
        self.assertEqual(
            evidence["post_patch_validation"]["independent_gate"],
            "BLOCKED_REQUIRED_REGRESSION_AND_INVENTORY",
        )
        self.assertEqual(evidence["certification"], "NOT_GRANTED")
        self.assertFalse(evidence["mission_completion_claim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
