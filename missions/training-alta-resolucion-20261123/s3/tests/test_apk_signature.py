import importlib


APK_ENTRIES = [
    {"name": "AndroidManifest.xml", "data_hex": "3c6d616e69666573742f3e"},
    {"name": "resources.arsc", "data_hex": "01020304"},
    {"name": "classes.dex", "data_hex": "6465780a30333500"},
]


def test_apk_signature_probe_distinguishes_valid_invalid_and_absent_fixture_signatures():
    executor = importlib.import_module("metagente_luna_s3.apk_signature_exec").apk_signature_verify
    oracle = importlib.import_module("metagente_luna_s3.apk_signature_oracle").apk_signature_oracle

    for mode, expected in (("valid", "VALID"), ("invalid", "INVALID"), ("absent", "ABSENT")):
        arguments = {"entries": APK_ENTRIES, "signature_mode": mode}
        observed = executor(APK_ENTRIES, mode)
        assert observed["status"] == expected
        assert observed["archive_unchanged"] is True
        assert oracle(arguments, observed)["ok"] is True


def test_apk_signature_probe_negative_invalid_and_boundary_absent_controls_are_adjudicated():
    controls = importlib.import_module("metagente_luna_s4.controls")
    independent = importlib.import_module("metagente_luna_s4.independent_validator")
    rows = next(row for row in controls.run_controls() if row["case_id"] == "MGL5-INF-0066")
    assert set(rows["controls"]) == {"negative", "boundary"}
    for kind in ("negative", "boundary"):
        control = rows["controls"][kind]
        expect = controls.CONTROLS["MGL5-INF-0066"][kind]["expect"]
        assert control["accepted"] is True
        assert independent._independent_control_accepts(expect, control["observed"], control["execution_status"]) is True
