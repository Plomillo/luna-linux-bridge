from metagente_luna_s3.evidence import verify_run, write_run
from metagente_luna_s4.d01_batch import assess_c05, run_all


def test_encoding_cases_meet_their_stated_criterion_on_three_runs():
    rows = run_all()
    assert len(rows) == 21
    assert {row["execution_status"] for row in rows} == {"CRITERION_MET"}
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0001"]["recovered"] == "Luna-2026"
    assert by_id["MGL5-INF-0007"] == {"little_endian_hex": "0x04030201", "big_endian_hex": "0x01020304"}
    assert by_id["MGL5-INF-0010"]["signed"] == -1
    assert by_id["MGL5-INF-0011"]["bits_hex"] == "0x3fc00000"
    assert by_id["MGL5-INF-0048"]["digest_hex"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    gate = assess_c05(rows)
    assert gate["gate"] == "NOT_PASSED"
    assert gate["not_run"] == 979
    assert gate["counter"] == "4/26"


def test_one_encoding_result_is_stored_and_checked(tmp_path):
    row = next(item for item in run_all() if item["case_id"] == "MGL5-INF-0007")
    folder = write_run(tmp_path, "MGL5-INF-0007", "run-d01-r1", {
        "observed.json": row["observed"],
        "oracle.json": {"method": row["oracle_method"]},
        "result.json": {"execution_status": row["execution_status"], "c05_gate": "NOT_PASSED"},
    })
    assert verify_run(folder, tmp_path) == "EVIDENCE_VALIDATED"
