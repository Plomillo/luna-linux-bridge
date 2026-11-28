import importlib


def test_zip_central_directory_compares_local_headers_and_detects_mismatch_without_extracting():
    executor = importlib.import_module("metagente_luna_s3.zip_central_exec").zip_central_compare
    oracle = importlib.import_module("metagente_luna_s3.zip_central_oracle").zip_central_compare_oracle
    fixture = [{"name": "safe.txt", "data_hex": "616263"}]

    valid_args = {"entries": fixture, "tamper_central_name": False}
    valid = executor(fixture, False)
    assert valid["mismatch_detected"] is False
    assert valid["local_names"] == valid["central_names"] == ["safe.txt"]
    assert valid["extraction_performed"] is False
    assert oracle(valid_args, valid)["ok"] is True

    negative_args = {"entries": fixture, "tamper_central_name": True}
    negative = executor(fixture, True)
    assert negative["mismatch_detected"] is True
    assert negative["discrepancies"][0]["field"] == "filename"
    assert negative["extraction_performed"] is False
    assert negative["outside_destination_write"] is False
    assert oracle(negative_args, negative)["ok"] is True


def test_zip_central_directory_negative_and_boundary_controls_are_independently_adjudicated():
    controls = importlib.import_module("metagente_luna_s4.controls")
    independent = importlib.import_module("metagente_luna_s4.independent_validator")
    rows = next(row for row in controls.run_controls() if row["case_id"] == "MGL5-INF-0069")
    assert set(rows["controls"]) == {"negative", "boundary"}
    for kind in ("negative", "boundary"):
        control = rows["controls"][kind]
        expect = controls.CONTROLS["MGL5-INF-0069"][kind]["expect"]
        assert control["accepted"] is True
        assert independent._independent_control_accepts(expect, control["observed"], control["execution_status"]) is True
