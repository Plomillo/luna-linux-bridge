import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import cajita_luna_governed_preflight as ctl


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def make_root(base: Path) -> Path:
    root = base / "Cajita de Luna"
    root.mkdir()
    for domain in ctl.EXPECTED_DOMAINS:
        (root / domain).mkdir(parents=True)
    edge = root / ctl.EDGE_ARCHIVE_REL
    edge.parent.mkdir(parents=True, exist_ok=True)
    edge.write_bytes(b"edge-test-payload-not-real-profile")
    digest = hashlib.sha256(edge.read_bytes()).hexdigest()
    edge.with_suffix(".sha256").write_text(f"{digest}  {edge.name}\n", encoding="utf-8")
    edge.with_suffix(".audit.jsonl").write_text('{"status":"fixture-only"}\n', encoding="utf-8")
    write_json(root / "RUNTIME_CANDIDATE_V1" / "registry.json", {"artifacts": []})
    return root


class GovernedPreflightTests(unittest.TestCase):
    def test_tree_scan_counts_hidden_files_and_sidecars(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".hidden").write_bytes(b"1234")
            (root / "visible").write_bytes(b"abc")
            (root / ".candidate").mkdir()
            (root / ".candidate" / "receipt.json").write_bytes(b"xy")
            scan = ctl.scan_tree(root)
            self.assertEqual(scan["total_bytes"], 9)
            self.assertEqual(scan["regular_file_count"], 3)

    def test_edge_integrity_uses_streaming_hash_and_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp))
            evidence = ctl.edge_evidence(root)
            self.assertEqual(evidence["status"], "PASS")
            self.assertEqual(evidence["sha256_observed"], hashlib.sha256((root / ctl.EDGE_ARCHIVE_REL).read_bytes()).hexdigest())
            (root / ctl.EDGE_ARCHIVE_REL).write_bytes(b"changed")
            self.assertEqual(ctl.edge_evidence(root)["status"], "BLOCKED")

    def test_registry_audit_reports_missing_and_size_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "present.json").write_text("abc", encoding="utf-8")
            write_json(root / "RUNTIME_CANDIDATE_V1" / "registry.json", {
                "artifacts": [
                    {"path": "present.json", "size": 77},
                    {"path": "missing.safetensors", "size": 25},
                ]
            })
            result = ctl.registry_comparison(root)
            self.assertEqual(result["artifact_count"], 2)
            self.assertEqual(result["declared_original_bytes"], 102)
            self.assertEqual(result["missing_count"], 1)
            self.assertEqual(result["size_mismatch_count"], 1)
            self.assertEqual(result["status"], "RECONCILIATION_REQUIRED")

    def test_reduction_math_is_exact_and_uses_decimal_cap(self):
        self.assertEqual(1_656_649_690 - 470_000_000, 1_186_649_690)
        projected = ctl.calculate_projected_final(1_000, 600, 50, 100)
        self.assertEqual(projected, 550)
        self.assertTrue(ctl.calculate_projected_final(1_000, 600, 50, 100) <= 470_000_000)

    def test_preflight_never_self_certifies_and_never_transforms_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp))
            payload = root / "2. Orquestación" / "untouched.txt"
            payload.write_bytes(b"frozen-payload")
            before = hashlib.sha256(payload.read_bytes()).hexdigest()
            report = ctl.check_preflight(root)
            after = hashlib.sha256(payload.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertFalse(report["invariants"]["payload_transformations_performed"])
            self.assertEqual(report["gates"]["G23"], "NOT_RUN_FOR_CAJITA")
            self.assertEqual(report["gates"]["G24"], "NOT_ISSUED_FOR_CAJITA")
            self.assertEqual(report["certification_status"], "NOT_GRANTED")
            self.assertEqual(report["release_status"], "BLOCKED")
            self.assertIn("OPTIMIZATION_PLAN_MISSING", report["blockers"])

    def test_missing_frozen_and_reconciliation_manifests_are_blockers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp))
            registry = ctl.registry_comparison(root)
            self.assertIn("FROZEN_V9_OUTPUTS_MANIFEST_MISSING", ctl.validate_frozen_manifest(root))
            self.assertIn("REGISTRY_RECONCILIATION_MANIFEST_MISSING", ctl.validate_reconciliation(root, registry))

    def test_subject_digest_is_deterministic_and_excludes_generated_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".cajita-optimization-candidates" / "evidence").mkdir(parents=True)
            (root / "model.bin").write_bytes(b"model")
            first, count, size = ctl.candidate_tree_digest(root)
            (root / ".cajita-optimization-candidates" / "evidence" / "G23.json").write_text("one", encoding="utf-8")
            second, count2, size2 = ctl.candidate_tree_digest(root)
            self.assertNotEqual(first, second)
            self.assertEqual(count, 1)
            self.assertEqual(size, 5)
            self.assertEqual(count2, 2)
            self.assertEqual(size2, 8)
            third, count3, size3 = ctl.candidate_tree_digest(
                root, {".cajita-optimization-candidates/evidence/G23.json"}
            )
            self.assertEqual(first, third)
            self.assertEqual(count3, 1)
            self.assertEqual(size3, 5)
            (root / "model.bin").write_bytes(b"other")
            fourth, _, _ = ctl.candidate_tree_digest(
                root, {".cajita-optimization-candidates/evidence/G23.json"}
            )
            self.assertNotEqual(first, fourth)

    def test_persisted_report_and_hash_sidecar_are_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "artifact.bin").write_bytes(b"x" * 37)
            report = {"inventory": {"total_bytes": 37}, "release_status": "BLOCKED"}
            path = ctl.persist_report(root, report)
            sidecar = path.with_suffix(".json.sha256")
            self.assertTrue(path.is_file())
            self.assertTrue(sidecar.is_file())
            stated = sidecar.read_text(encoding="utf-8").split()[0]
            self.assertEqual(stated, hashlib.sha256(path.read_bytes()).hexdigest())
            actual = ctl.scan_tree(root)["total_bytes"]
            self.assertEqual(actual, report["inventory"]["bytes_after_this_evidence_record"])
            self.assertGreater(actual, 37)

    def test_safe_relative_rejects_parent_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                ctl.safe_relative(root, "../outside.bin")


    def test_missing_22_domain_routing_report_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp))
            errors = ctl.validate_domain_routing(
                root,
                {"schema": "CAJITA_OPTIMIZATION_PLAN_V9/1.0"},
                {},
            )
            self.assertIn("DOMAIN_ROUTING_MANIFEST_MISSING", errors)

    def test_domain_routing_requires_exact_twenty_two_domains(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp))
            report_path = root / ctl.DOMAIN_TOOL_REPORT_REL
            write_json(report_path, {
                "schema": "CAJITA_DOMAIN_TOOL_VALIDATION_V9/1.0",
                "repository": "Plomillo/luna-linux-bridge",
                "repository_commit": "a" * 40,
                "status": "PASS",
                "domains": [],
            })
            errors = ctl.validate_domain_routing(
                root,
                {
                    "schema": "CAJITA_OPTIMIZATION_PLAN_V9/1.0",
                    "domain_routing": {
                        "schema": "CAJITA_V9_DOMAIN_ROUTING/1.0",
                        "repository": "Plomillo/luna-linux-bridge",
                        "repository_commit": "a" * 40,
                        "validation_report_path": ctl.DOMAIN_TOOL_REPORT_REL,
                        "validation_report_sha256": ctl.sha256_file(report_path),
                        "domains": [],
                    },
                },
                {},
            )
            self.assertIn("DOMAIN_ROUTING_MATRIX_MUST_COVER_D01_D22_EXACTLY", errors)
            self.assertIn("DOMAIN_TOOL_VALIDATION_MUST_COVER_D01_D22_EXACTLY", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
