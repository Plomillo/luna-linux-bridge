import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "puac2_mtls_gate", Path(__file__).parents[1] / "scripts" / "puac2_mtls_gate.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def minimal_manifest():
    return {
        "schema": "PUAC2_MTLS_CERTIFICATION/1.0",
        "candidate_commit": "a" * 40,
        "submitter_id": "submitter",
        "evidence": {},
        "tests": {"status": "HOLD", "passed": 0, "failed": 0},
        "g23": {},
        "g24": {},
    }


def test_empty_manifest_fails_closed():
    code, reasons = gate.validate(minimal_manifest(), "", "")
    assert code == 3
    assert "G23_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED" in reasons
    assert "G24_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED" in reasons
    assert "TESTS_NOT_PROVEN_PASS" in reasons


def test_wrong_schema_is_rejected():
    manifest = minimal_manifest()
    manifest["schema"] = "anything"
    code, reasons = gate.validate(manifest, "", "")
    assert code == 3
    assert "SCHEMA_INVALID" in reasons


def test_malformed_hashes_are_rejected():
    manifest = minimal_manifest()
    manifest["evidence"] = {
        "input_sha256": "not-a-hash",
        "output_sha256": "0" * 64,
        "test_report_sha256": "0" * 64,
        "host_mtls_test_sha256": "0" * 64,
        "rollback_test_sha256": "0" * 64,
    }
    code, reasons = gate.validate(manifest, "", "")
    assert code == 3
    assert "HASH_INVALID:input_sha256" in reasons


def test_missing_g23_and_g24_never_certifies():
    manifest = minimal_manifest()
    manifest["tests"] = {"status": "PASS", "passed": 1, "failed": 0}
    code, reasons = gate.validate(manifest, "", "")
    assert code == 3
    assert "G23_NOT_PASS" in reasons
    assert "G24_NOT_CERTIFIED" in reasons


def test_pr_preflight_cannot_be_used_as_release_certification():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "puac2-e2e.yml").read_text()
    assert "workflow_dispatch:" not in workflow
    assert "runs-on: [self-hosted" not in workflow
    assert "Require evidence manifest on release runs" not in workflow
    assert "certification_status" in workflow
    assert "non-certifying" in workflow
    assert "puac2-autonomous.yml" in workflow


def test_privileged_chain_stays_excluded_from_pull_requests():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "puac2-autonomous.yml").read_text()
    assert "if: github.event_name != 'pull_request'" in workflow
    assert "runs-on: [self-hosted, linux, x64, luna-aux]" in workflow
    assert "  workflow_dispatch:" in workflow

def test_autonomous_workflow_writes_valid_json_newline():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "puac2-autonomous.yml").read_text()
    assert 'json.dumps(data,sort_keys=True,indent=2)+"\\n"' in workflow
    assert 'json.dumps(data,sort_keys=True,indent=2)+"\\\\n"' not in workflow


def test_autonomous_workflow_matches_host_hashes_by_basename():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "puac2-autonomous.yml").read_text()
    assert 'actual_hashes[Path(parts[1].lstrip("*")).name] = parts[0]' in workflow

