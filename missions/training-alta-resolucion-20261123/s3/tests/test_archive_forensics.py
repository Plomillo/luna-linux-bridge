from __future__ import annotations

import importlib.util
from pathlib import Path

from metagente_luna_s3.registry import ORACLES, REGISTRY, run
from metagente_luna_s4.batch2 import CASES
from metagente_luna_s4.controls import run_controls

SCRIPT = Path(__file__).parents[1] / "scripts" / "build_c05_executable_plans.py"
SPEC = importlib.util.spec_from_file_location("build_c05_executable_plans", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
COMPILER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPILER)


EXPECTED = {
    "MGL5-INF-0070": "zip_path_safety",
    "MGL5-INF-0071": "zip_crc",
    "MGL5-INF-0072": "zip_duplicates",
    "MGL5-INF-0073": "tar_offsets",
    "MGL5-INF-0074": "tar_truncated",
    "MGL5-INF-0075": "gzip_crc",
    "MGL5-INF-0078": "sqlite_header",
    "MGL5-INF-0079": "sqlite_integrity",
    "MGL5-INF-0085": "wasm_header",
    "MGL5-INF-0080": "png_chunks",
    "MGL5-INF-0088": "unknown_format",
    "MGL5-INF-0089": "block_entropy",
    "MGL5-INF-0090": "binary_diff",
    "MGL5-INF-0097": "bounded_declared_size",
    "MGL5-INF-0099": "reproducible_structure",
    "MGL5-INF-0081": "jpeg_markers",
    "MGL5-INF-0091": "partial_recovery",
    "MGL5-INF-0092": "timestamp_provenance",
    "MGL5-INF-0093": "dependency_graph",
    "MGL5-INF-0094": "protocol_version_diff",
    "MGL5-INF-0096": "section_overlaps",
    "MGL5-INF-0098": "nested_zip_tar",
    "MGL5-INF-0100": "forensic_report",
    "MGL5-INF-0076": "seven_zip_list",
    "MGL5-INF-0077": "seven_zip_missing_volume",
    "MGL5-INF-0086": "wasm_sections",
    "MGL5-INF-0087": "wasm_type_indices",
    "MGL5-INF-0082": "pdf_objects",
    "MGL5-INF-0083": "pdf_xref",
    "MGL5-INF-0084": "pdf_encryption_boundary",
    "MGL5-INF-0056": "elf_symbol_tables",
    "MGL5-INF-0057": "elf_symbol_tables",
    "MGL5-INF-0095": "elf_symbol_tables",
    "MGL5-INF-0060": "elf_host_compatibility",
    "MGL5-INF-0054": "elf_section_layout",
    "MGL5-INF-0055": "elf_section_layout",
    "MGL5-INF-0058": "elf_dynamic_dependencies",
    "MGL5-INF-0059": "elf_rpath_runpath",
    "MGL5-INF-0061": "pe_inspect",
    "MGL5-INF-0062": "pe_inspect",
    "MGL5-INF-0063": "pe_inspect",
    "MGL5-INF-0064": "pe_inspect",
    "MGL5-INF-0067": "dex_header",
    "MGL5-INF-0068": "dex_tables",
    "MGL5-INF-0633": "acf_lag0",
    "MGL5-INF-0634": "trend_stationarity",
}


def test_archive_forensics_source_cases_have_three_stable_oracled_runs():
    selected = {row["case_id"]: row for row in COMPILER.CASE_SPECS if row["case_id"] in EXPECTED}
    assert set(selected) == set(EXPECTED)

    for case_id, capability in EXPECTED.items():
        spec = selected[case_id]
        observations = [run(capability, spec["arguments"]) for _ in range(3)]
        oracle = ORACLES[REGISTRY[capability].oracle_id]
        assert observations[0] == observations[1] == observations[2], case_id
        assert all(oracle(spec["arguments"], observed)["ok"] is True for observed in observations), case_id


def test_archive_forensics_cases_compile_with_source_and_two_controls():
    plans, _ = COMPILER.compile_plans()
    by_id = {plan["CASE_ID"]: plan for plan in plans}
    controls = {row["case_id"]: row for row in run_controls()}

    for case_id in EXPECTED:
        assert case_id in by_id
        assert case_id in by_id[case_id]["source_excerpt"]
        assert by_id[case_id]["source_metadata"]["excerpt_sha256"]
        assert set(controls[case_id]["controls"]) == {"negative", "boundary"}
        assert controls[case_id]["controls"]["negative"]["accepted"] is True
        assert controls[case_id]["controls"]["boundary"]["accepted"] is True
        assert controls[case_id]["controls"]["negative"]["run_kind"] == "NEGATIVE"
        assert controls[case_id]["controls"]["boundary"]["run_kind"] == "BOUNDARY"
        assert controls[case_id]["controls"]["negative"]["control_metadata"]["source"].endswith(f"{case_id}:negative")


def test_archive_forensics_capabilities_reject_untyped_extra_arguments():
    for capability in EXPECTED.values():
        schema = REGISTRY[capability].input_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False



def _rehash_dex_fixture(payload: bytearray) -> bytes:
    import hashlib
    import struct
    import zlib

    payload[12:32] = hashlib.sha1(payload[32:]).digest()
    struct.pack_into("<I", payload, 8, zlib.adler32(payload[12:]) & 0xffffffff)
    return bytes(payload)


def test_dex_table_parser_reconstructs_strings_and_all_declared_table_shapes():
    from metagente_luna_s3.format_exec import dex_inspect
    from metagente_luna_s3.format_oracle import dex_tables_oracle
    from metagente_luna_s4.batch2 import _DEX_HEX

    arguments = {"payload_hex": _DEX_HEX}
    observed = dex_inspect(_DEX_HEX, "tables")
    assert observed["rejected"] is False
    assert observed["strings"] == ["LExample;", "V", "run"]
    assert observed["type_string_indices"] == [0]
    assert observed["proto_references"] == [{"shorty_idx": 1, "return_type_idx": 0, "parameters_off": 0, "parameter_type_indices": []}]
    assert observed["field_references"] == []
    assert observed["method_references"] == [{"class_idx": 0, "proto_idx": 0, "name_idx": 2}]
    assert observed["indices_valid"] is True
    assert dex_tables_oracle(arguments, observed)["ok"] is True


def test_dex_parser_rejects_data_section_overrun_even_with_recomputed_integrity():
    import struct

    from metagente_luna_s3.format_exec import dex_inspect
    from metagente_luna_s4.batch2 import _DEX_FIXTURE

    malformed = bytearray(_DEX_FIXTURE)
    struct.pack_into("<I", malformed, 104, len(malformed) + 1)
    payload = _rehash_dex_fixture(malformed).hex()
    observed = dex_inspect(payload, "tables")
    assert observed == {"rejected": True, "reason": "data_section_out_of_bounds"}


def test_dex_parser_rejects_string_data_pointer_into_header():
    import struct

    from metagente_luna_s3.format_exec import dex_inspect
    from metagente_luna_s4.batch2 import _DEX_FIXTURE

    malformed = bytearray(_DEX_FIXTURE)
    string_ids_off = struct.unpack_from("<I", malformed, 60)[0]
    struct.pack_into("<I", malformed, string_ids_off, 56)
    observed = dex_inspect(_rehash_dex_fixture(malformed).hex(), "tables")
    assert observed == {"rejected": True, "reason": "string_data_offset_out_of_bounds"}


def test_dex_parser_checks_uleb128_utf16_length_and_terminator():
    import struct

    from metagente_luna_s3.format_exec import dex_inspect
    from metagente_luna_s4.batch2 import _DEX_FIXTURE

    malformed = bytearray(_DEX_FIXTURE)
    data_off = struct.unpack_from("<I", malformed, 108)[0]
    malformed[data_off] = 8  # The string contains nine UTF-16 code units.
    observed = dex_inspect(_rehash_dex_fixture(malformed).hex(), "tables")
    assert observed == {"rejected": True, "reason": "string_data_encoding_or_length_invalid"}


def test_dex_parser_bounds_proto_parameter_type_list():
    import struct

    from metagente_luna_s3.format_exec import dex_inspect
    from metagente_luna_s4.batch2 import _DEX_FIXTURE

    malformed = bytearray(_DEX_FIXTURE)
    proto_ids_off = struct.unpack_from("<I", malformed, 76)[0]
    data_end = struct.unpack_from("<I", malformed, 104)[0] + struct.unpack_from("<I", malformed, 108)[0]
    struct.pack_into("<I", malformed, proto_ids_off + 8, data_end + 4)
    observed = dex_inspect(_rehash_dex_fixture(malformed).hex(), "tables")
    assert observed == {"rejected": True, "reason": "proto_parameters_offset_out_of_bounds"}



def test_dex_modified_utf8_handles_encoded_nul_and_surrogate_pair_and_rejects_four_byte_utf8():
    from metagente_luna_s3.format_exec import _dex_mutf8

    assert _dex_mutf8(bytes([0xc0, 0x80, 0x00]), 0, 3, 1) == chr(0)
    assert _dex_mutf8(bytes([0xed, 0xa0, 0xbd, 0xed, 0xba, 0x80, 0x00]), 0, 7, 2) == "\U0001f680"
    assert _dex_mutf8(bytes([0xf0, 0x9f, 0x9a, 0x80, 0x00]), 0, 5, 2) is None
