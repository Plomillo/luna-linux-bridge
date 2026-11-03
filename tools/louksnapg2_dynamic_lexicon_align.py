#!/usr/bin/env python3
"""Extract research-only Greek/Latin correspondence hypotheses from Perseus sense records.

The source is a noisy, automatically induced lexicon. A shared English sense and
part of speech create a candidate correspondence, never a certified translation.
No candidate is written into Foma resources or promoted into the runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tarfile
import unicodedata
from collections import defaultdict
from pathlib import Path, PurePosixPath

from defusedxml import ElementTree as DET

SOURCE_REPOSITORY = "PerseusDL/dynamic-lexicon"
SOURCE_COMMIT = "945b03db7ff358217a18540a7d7efef9d7339b66"
SOURCE_LICENSE = "CC BY-SA (version unspecified by upstream README)"
ARCHIVE_SHA256 = {
    "grc": "e9b4f2ff9ab62c5b4b838b74fab78dff3b28fa8381889931f1885792683dd3b8",
    "lat": "f7d0b0ce41c5b7ec75c4d83e5018371b4a366b27f2f8f169abfdbe8af21e42ac",
}
ARCHIVE_LIMIT_BYTES = 5_000_000
MEMBER_LIMIT = 20_000
XML_TOTAL_LIMIT_BYTES = 1_000_000_000
XML_MEMBER_LIMIT_BYTES = 2_000_000
MAX_SENSE_RECORDS = 500_000
MAX_OUTPUT_CANDIDATES = 20_000
MAX_GROUP_PRODUCT = 2_500


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def local_name(tag: object) -> str:
    return str(tag).rsplit("}", 1)[-1].split(":")[-1].casefold()


def children_named(node, name: str):
    return [child for child in list(node) if local_name(child.tag) == name]


def descendants_named(node, name: str):
    return [child for child in node.iter() if child is not node and local_name(child.tag) == name]


def first_child_text(node, name: str) -> str:
    rows = children_named(node, name)
    return clean_text(rows[0].text) if rows else ""


def parse_number(value: object, *, integer: bool = False):
    raw = clean_text(value)
    try:
        number = float(raw)
        if not math.isfinite(number):
            return 0 if integer else 0.0
        return int(number) if integer else number
    except (TypeError, ValueError, OverflowError):
        return 0 if integer else 0.0


def parse_archive(path: Path, language: str) -> list[dict]:
    path = Path(path)
    if language not in {"grc", "lat"}:
        raise RuntimeError("DYNAMIC_LEXICON_LANGUAGE_UNSUPPORTED:" + str(language))
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("DYNAMIC_LEXICON_ARCHIVE_MISSING_OR_UNSAFE:" + language)
    if path.stat().st_size > ARCHIVE_LIMIT_BYTES:
        raise RuntimeError("DYNAMIC_LEXICON_ARCHIVE_SIZE_LIMIT:" + language)

    records: list[dict] = []
    member_count = 0
    total_xml_bytes = 0
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive:
            member_count += 1
            if member_count > MEMBER_LIMIT:
                raise RuntimeError("DYNAMIC_LEXICON_MEMBER_LIMIT:" + language)
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise RuntimeError("DYNAMIC_LEXICON_UNSAFE_MEMBER:" + member.name[:200])
            if member.isdir():
                continue
            if not member.isfile():
                raise RuntimeError("DYNAMIC_LEXICON_UNSAFE_MEMBER_TYPE:" + member.name[:200])
            if not name.name.casefold().endswith(".xml") or member.size < 1:
                continue
            if member.size > XML_MEMBER_LIMIT_BYTES:
                raise RuntimeError("DYNAMIC_LEXICON_XML_MEMBER_LIMIT:" + member.name[:200])
            total_xml_bytes += int(member.size)
            if total_xml_bytes > XML_TOTAL_LIMIT_BYTES:
                raise RuntimeError("DYNAMIC_LEXICON_XML_TOTAL_LIMIT:" + language)
            handle = archive.extractfile(member)
            if handle is None:
                raise RuntimeError("DYNAMIC_LEXICON_MEMBER_READ_FAILED:" + member.name[:200])
            try:
                payload = handle.read(XML_MEMBER_LIMIT_BYTES + 1)
            finally:
                handle.close()
            if len(payload) != member.size or len(payload) > XML_MEMBER_LIMIT_BYTES:
                raise RuntimeError("DYNAMIC_LEXICON_XML_MEMBER_SIZE_MISMATCH:" + member.name[:200])

            root = DET.fromstring(payload)
            root_nodes = [root] if local_name(root.tag) == "lexicalentry" else descendants_named(root, "lexicalentry")
            for entry in root_nodes:
                form = first_child_text(entry, "form")
                entry_key = normalize_key(form)
                if not form or not entry_key:
                    continue
                entry_count = parse_number(first_child_text(entry, "count"), integer=True)
                entry_per10k = parse_number(first_child_text(entry, "per10k"))
                for poscontainer in children_named(entry, "poscontainer"):
                    pos = first_child_text(poscontainer, "pos").casefold() or "unknown"
                    for sense_container in descendants_named(poscontainer, "sensecontainer"):
                        sense_text = first_child_text(sense_container, "sense")
                        sense_key = normalize_key(sense_text)
                        if not sense_text or not sense_key:
                            continue
                        records.append({
                            "language": language,
                            "source_member": member.name,
                            "entry_form": form,
                            "entry_key": entry_key,
                            "entry_count": entry_count,
                            "entry_per10k": entry_per10k,
                            "pos": pos,
                            "sense": sense_text,
                            "sense_key": sense_key,
                            "count": parse_number(first_child_text(sense_container, "count"), integer=True),
                            "probability": parse_number(first_child_text(sense_container, "prob")),
                            "loglikelihood": parse_number(first_child_text(sense_container, "loglikelihood")),
                        })
                        if len(records) > MAX_SENSE_RECORDS:
                            raise RuntimeError("DYNAMIC_LEXICON_SENSE_RECORD_LIMIT:" + language)
    return records


def build_candidates(greek_records: list[dict], latin_records: list[dict]) -> dict:
    greek_index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    latin_index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in greek_records:
        greek_index[(row["sense_key"], row["pos"])].append(row)
    for row in latin_records:
        latin_index[(row["sense_key"], row["pos"])].append(row)

    pair_evidence: dict[tuple[str, str, str], dict] = {}
    shared_groups = 0
    skipped_ambiguous_groups = 0
    matched_sense_keys = set()
    for key in sorted(set(greek_index).intersection(latin_index)):
        g_rows, l_rows = greek_index[key], latin_index[key]
        if not g_rows or not l_rows:
            continue
        shared_groups += 1
        matched_sense_keys.add(key[0])
        if len(g_rows) * len(l_rows) > MAX_GROUP_PRODUCT:
            skipped_ambiguous_groups += 1
            continue
        for greek in g_rows:
            for latin in l_rows:
                pair = (greek["entry_key"], latin["entry_key"], key[1])
                row = pair_evidence.setdefault(pair, {
                    "greek_forms": set(),
                    "latin_forms": set(),
                    "greek_source_members": set(),
                    "latin_source_members": set(),
                    "evidence": {},
                    "support_score": 0.0,
                })
                evidence = row["evidence"].setdefault(key[0], {
                    "english_sense_key": key[0],
                    "greek_senses": [],
                    "latin_senses": [],
                })
                greek_evidence = {
                    "entry_form": greek["entry_form"],
                    "sense": greek["sense"],
                    "pos": greek["pos"],
                    "entry_count": greek["entry_count"],
                    "sense_count": greek["count"],
                    "probability": greek["probability"],
                    "loglikelihood": greek["loglikelihood"],
                    "source_member": greek["source_member"],
                }
                latin_evidence = {
                    "entry_form": latin["entry_form"],
                    "sense": latin["sense"],
                    "pos": latin["pos"],
                    "entry_count": latin["entry_count"],
                    "sense_count": latin["count"],
                    "probability": latin["probability"],
                    "loglikelihood": latin["loglikelihood"],
                    "source_member": latin["source_member"],
                }
                if greek_evidence not in evidence["greek_senses"]:
                    evidence["greek_senses"].append(greek_evidence)
                if latin_evidence not in evidence["latin_senses"]:
                    evidence["latin_senses"].append(latin_evidence)
                row["greek_forms"].add(greek["entry_form"])
                row["latin_forms"].add(latin["entry_form"])
                row["greek_source_members"].add(greek["source_member"])
                row["latin_source_members"].add(latin["source_member"])
                row["support_score"] += min(
                    math.log1p(max(greek["count"], 0)),
                    math.log1p(max(latin["count"], 0)),
                )

    candidates = []
    for (greek_key, latin_key, pos), row in pair_evidence.items():
        evidence_rows = []
        for value in sorted(row["evidence"].values(), key=lambda x: x["english_sense_key"]):
            value["greek_senses"].sort(key=lambda x: (x["entry_form"].casefold(), x["source_member"]))
            value["latin_senses"].sort(key=lambda x: (x["entry_form"].casefold(), x["source_member"]))
            evidence_rows.append(value)
        candidates.append({
            "candidate_id": hashlib.sha256((greek_key + "\0" + latin_key + "\0" + pos).encode("utf-8")).hexdigest()[:20],
            "greek_lemmas": sorted(row["greek_forms"], key=str.casefold),
            "latin_lemmas": sorted(row["latin_forms"], key=str.casefold),
            "part_of_speech": pos,
            "independent_shared_sense_count": len(evidence_rows),
            "support_score": round(row["support_score"], 6),
            "greek_source_members": sorted(row["greek_source_members"]),
            "latin_source_members": sorted(row["latin_source_members"]),
            "evidence": evidence_rows,
            "epistemic_status": "HYPOTHESIS_ONLY_REQUIRES_HELD_OUT_PHILOLOGICAL_VALIDATION",
        })
    candidates.sort(key=lambda x: (
        -x["independent_shared_sense_count"],
        -x["support_score"],
        x["candidate_id"],
    ))
    return {
        "candidate_count": len(candidates),
        "candidate_output_truncated": len(candidates) > MAX_OUTPUT_CANDIDATES,
        "candidates": candidates[:MAX_OUTPUT_CANDIDATES],
        "alignment_diagnostics": {
            "shared_english_sense_and_pos_groups": shared_groups,
            "matched_english_sense_keys": len(matched_sense_keys),
            "candidate_pairs_with_shared_senses": len(candidates),
            "groups_skipped_for_many_to_many_ambiguity": skipped_ambiguous_groups,
            "maximum_group_cartesian_product": MAX_GROUP_PRODUCT,
            "pairing_rule": "EXACT_NORMALIZED_ENGLISH_SENSE + EXACT_PART_OF_SPEECH",
            "translation_equivalence_asserted": False,
            "automatic_runtime_promotion": False,
        },
    }


def extraction_status(greek_records: list[dict], latin_records: list[dict], candidate_count: int) -> str:
    if not greek_records or not latin_records:
        return "FAIL_NO_SOURCE_SENSE_RECORDS"
    if candidate_count <= 0:
        return "FAIL_NO_SHARED_SENSE_CANDIDATES"
    return "PASS_CANDIDATE_EXTRACTION_ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--greek", type=Path, required=True)
    parser.add_argument("--latin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    greek_sha = sha256_file(args.greek)
    latin_sha = sha256_file(args.latin)
    if greek_sha != ARCHIVE_SHA256["grc"]:
        raise RuntimeError("DYNAMIC_LEXICON_SOURCE_HASH_MISMATCH:grc")
    if latin_sha != ARCHIVE_SHA256["lat"]:
        raise RuntimeError("DYNAMIC_LEXICON_SOURCE_HASH_MISMATCH:lat")
    greek = parse_archive(args.greek, "grc")
    latin = parse_archive(args.latin, "lat")
    alignment = build_candidates(greek, latin)
    status = extraction_status(greek, latin, alignment["candidate_count"])
    report = {
        "schema": "LOUKSNAPG2_DYNAMIC_LEXICON_ALIGNMENT_CANDIDATES/2.0",
        "status": status,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "license": SOURCE_LICENSE,
            "attribution": "Perseus Digital Library Dynamic Lexicon",
            "greek_archive_sha256": greek_sha,
            "latin_archive_sha256": latin_sha,
        },
        "source_coverage": {
            "greek_sense_records": len(greek),
            "latin_sense_records": len(latin),
            "greek_source_members_with_senses": len({x["source_member"] for x in greek}),
            "latin_source_members_with_senses": len({x["source_member"] for x in latin}),
        },
        "alignment": {
            key: value for key, value in alignment.items() if key != "candidates"
        },
        "candidate_policy": {
            "shared_english_sense_is_hypothesis_not_translation_proof": True,
            "source_forms_and_part_of_speech_preserved": True,
            "sense_ambiguity_and_source_provenance_preserved": True,
            "automatic_runtime_promotion": "NOT_AUTHORIZED",
            "held_out_philological_validation": "REQUIRED",
            "certification": "NOT_GRANTED",
        },
    }
    report["alignment_candidates"] = alignment["candidates"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "source_coverage": report["source_coverage"],
        "alignment": report["alignment"],
        "top_candidates": alignment["candidates"][:8],
        "output": str(args.output),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if status == "PASS_CANDIDATE_EXTRACTION_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
