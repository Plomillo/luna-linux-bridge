from __future__ import annotations

from metagente_luna_s3.apk_inventory_exec import apk_inventory
from metagente_luna_s3.apk_inventory_oracle import apk_inventory_oracle
from metagente_luna_s4.controls import accepts


APK = [
    {"name": "AndroidManifest.xml", "data_hex": "3c6d616e69666573742f3e"},
    {"name": "resources.arsc", "data_hex": "01020304"},
    {"name": "classes.dex", "data_hex": "6465780a30333500"},
]


def test_apk_inventory_lists_manifest_resources_and_dex_without_mutation():
    observed = apk_inventory(APK)
    assert observed["members"] == ["AndroidManifest.xml", "classes.dex", "resources.arsc"]
    assert observed["present"] == {"manifest": True, "resources": True, "dex": True}
    assert observed["missing"] == []
    assert observed["zip_integrity"] is True
    assert observed["archive_unchanged"] is True
    assert apk_inventory_oracle({"entries": APK}, observed)["ok"] is True


def test_apk_inventory_negative_missing_dex_and_boundary_empty_members():
    negative = apk_inventory([APK[0], APK[1]])
    assert negative["missing"] == ["classes.dex"]
    assert accepts("apk-dex-missing-reported", negative, "EXECUTED") is True
    assert apk_inventory_oracle({"entries": [APK[0], APK[1]]}, negative)["ok"] is True

    boundary_entries = [
        {"name": "AndroidManifest.xml", "data_hex": ""},
        {"name": "resources.arsc", "data_hex": ""},
        {"name": "classes.dex", "data_hex": ""},
    ]
    boundary = apk_inventory(boundary_entries)
    assert boundary["present"] == {"manifest": True, "resources": True, "dex": True}
    assert boundary["uncompressed_bytes"] == 0
    assert apk_inventory_oracle({"entries": boundary_entries}, boundary)["ok"] is True
    assert accepts("apk-empty-members-listed", boundary, "EXECUTED") is True

def test_apk_inventory_control_runs_are_adjudicated_by_both_validators():
    from metagente_luna_s4.controls import CONTROLS, run_controls
    from metagente_luna_s4.independent_validator import _independent_control_accepts

    case = next(row for row in run_controls() if row["case_id"] == "MGL5-INF-0065")
    assert set(case["controls"]) == {"negative", "boundary"}
    for kind in ("negative", "boundary"):
        control = case["controls"][kind]
        assert control["accepted"] is True
        assert _independent_control_accepts(
            CONTROLS[case["case_id"]][kind]["expect"], control["observed"], control["execution_status"]
        ) is True
