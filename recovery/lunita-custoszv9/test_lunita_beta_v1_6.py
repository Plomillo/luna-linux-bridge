import ast
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "recovery/lunita-custoszv9/lunita_beta_v1_6.py"
PROVENANCE = ROOT / "recovery/lunita-custoszv9/BETA_PROVENANCE_v1_6.json"
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT, filename=str(SOURCE))


def function_source(name):
    node = next(
        (n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name),
        None,
    )
    if node is None:
        raise AssertionError(f"required function missing: {name}")
    return ast.get_source_segment(TEXT, node)


class LunitaBetaV16ContractTests(unittest.TestCase):
    def test_launcher_compiles_and_has_expected_identity(self):
        compile(TEXT, str(SOURCE), "exec")
        evidence = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["beta_revision"], "beta-v1.6")
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), evidence["beta_launcher_sha256"])
        self.assertFalse(evidence["exact_frozen_launcher_match"])
        self.assertEqual(
            evidence["source_sha256"],
            "dc7d673b16a578c5cc94999856ed4b70d0b039702155779660a1083e2da54066",
        )

    def test_flatpak_commit_pins_are_exact(self):
        self.assertIn(
            "'org.jamovi.jamovi':'4685c60d99398dc687837d58f370b31e01edc160c2e3bbd3d4b204a20b249fab'",
            TEXT,
        )
        self.assertIn(
            "'org.jaspstats.JASP':'83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e284de3df7'",
            TEXT,
        )

    def test_flatpak_uses_supported_commit_query_not_version_option(self):
        body = function_source("flatpak_check")
        self.assertIn("--show-commit", body)
        self.assertNotIn("--show-version", body)
        self.assertIn("Installation: system", body)
        self.assertIn("Origin: flathub", body)

    def test_flatpak_sandbox_probe_fails_closed(self):
        body = function_source("flatpak_check")
        self.assertIn("return 0 if q.returncode==0 else 3", body)
        self.assertIn("finally:shutil.rmtree(h,ignore_errors=True)", body)

    def test_brujula_gets_its_own_writable_home_and_xdg_dirs(self):
        body = function_source("brujula")
        self.assertIn("tempfile.mkdtemp(prefix='lunita-brujula-home-',dir='/tmp')", body)
        self.assertIn("'HOME':h", body)
        self.assertIn("'XDG_CACHE_HOME':h+'/cache'", body)
        self.assertIn("'XDG_CONFIG_HOME':h+'/config'", body)
        self.assertIn("'XDG_DATA_HOME':h+'/data'", body)
        self.assertIn("env=env", body)
        self.assertIn("finally:shutil.rmtree(h,ignore_errors=True)", body)

    def test_qwen_invocation_is_bounded_and_does_not_use_zero_token_probe(self):
        body = function_source("qwen")
        for token in ("'-t','1'", "'-c','256'", "'-b','64'", "'-ub','32'", "'--no-warmup'", "timeout=90"):
            self.assertIn(token, body)
        self.assertNotIn("'0' if mode=='load'", body)

    def test_r_selftest_enforces_461(self):
        body = function_source("rcheck")
        self.assertIn('getRversion())=="4.6.1"', body)

    def test_cli_routes_app_selftests_to_pinned_commits(self):
        self.assertIn("flatpak_check('org.jamovi.jamovi',FLATPAK_PINNED_COMMITS['org.jamovi.jamovi'],True)", TEXT)
        self.assertIn("flatpak_check('org.jaspstats.JASP',FLATPAK_PINNED_COMMITS['org.jaspstats.JASP'],True)", TEXT)

    def test_no_automatic_certification_claim_in_provenance(self):
        evidence = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["certification"], "NOT_GRANTED")
        self.assertFalse(evidence["mission_completion_claim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
