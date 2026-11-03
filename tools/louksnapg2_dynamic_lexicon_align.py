#!/usr/bin/env python3
"""Build provenance-rich Greek/Latin correspondence candidates from Dynamic Lexicon collocations.

This is a research extractor, not a certified dictionary. It requires exact shared
English collocation text, compatible syntax type and at least one shared author.
All ambiguity and source evidence are retained; no candidate is auto-promoted.
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
ARCHIVE_LIMIT_BYTES = 5_000_000
MEMBER_LIMIT = 20_000
XML_TOTAL_LIMIT_BYTES = 1_000_000_000
XML_MEMBER_LIMIT_BYTES = 2_000_000
MAX_OUTPUT_CANDIDATES = 20_000


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def names_under(node, path: str) -> list[str]:
    values = []
    for item in node.findall(path):
        value = clean_text(item.text)
        if value and value.casefold() != "null":
            values.append(value)
    return sorted(set(values), key=str.casefold)


def parse_archive(path: Path, language: str) -> list[dict]:
    path = Path(path)
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
            payload = handle.read(XML_MEMBER_LIMIT_BYTES + 1)
            handle.close()
            if len(payload) != member.size or len(payload) > XML_MEMBER_LIMIT_BYTES:
                raise RuntimeError("DYNAMIC_LEXICON_XML_MEMBER_SIZE_MISMATCH:" + member.name[:200])

            root = DET.fromstring(payload)
            form = clean_text(root.findtext("form"))
            entry_count = clean_text(root.findtext("count"))
            per10k = clean_text(root.findtext("per10k"))
            if not form:
                continue
            for poscontainer in root.findall("./poscontainer"):
                pos = clean_text(poscontainer.findtext("pos")).casefold()
                if not pos:
                    pos = "unknown"
                for syntaxcontainer in poscontainer.findall("./syntaxcontainer"):
                    syntax_type = clean_text(syntaxcontainer.findtext("type")).casefold()
                    if not syntax_type:
                        syntax_type = "unspecified"
                    for collocation in syntaxcontainer.findall("./collocation"):
                        original = clean_text(collocation.findtext("original"))
                        translated = clean_text(collocation.findtext("trans"))
                        translated_key = normalize_key(translated)
                        original_key = normalize_key(original)
                        if not original or not translated or not translated_key or not original_key:
                            continue
                        count_raw = clean_text(collocation.findtext("count"))
                        loglikelihood_raw = clean_text(collocation.findtext("loglikelihood"))
                        try:
                            count = int(float(count_raw))
                        except (ValueError, TypeError):
                            count = 0
                        try:
                            loglikelihood = float(loglikelihood_raw)
                        except (ValueError, TypeError):
                            loglikelihood = 0.0
                        authors = names_under(collocation, "./authorcontainer/author/name")
                        records.append({
                            "language": language,
                            "source_member": member.name,
                            "entry_form": form,
                            "entry_count": entry_count,
                            "entry_per10k": per10k,
                            "pos": pos,
                            "syntax_type": syntax_type,
                            "original": original,
                            "original_key": original_key,
                            "translated": translated,
                            "translated_key": translated_key,
                            "count": count,
                            "loglikelihood": loglikelihood,
                            "authors": authors,
                        })
    return records


def build_candidates(greek_records: list[dict], latin_records: list[dict]) -> dict:
    greek_index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    latin_index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in greek_records:
        greek_index[(row["translated_key"], row["syntax_type"])].append(row)
    for row in latin_records:
        latin_index[(row["translated_key"], row["syntax_type"])].append(row)

    pair_evidence: dict[tuple[str, str], dict] = {}
    shared_groups = 0
    skipped_no_author = 0
    skipped_oversized = 0
    for key in sorted(set(greek_index).intersection(latin_index)):
        g_rows, l_rows = greek_index[key], latin_index[key]
        if not g_rows or not l_rows:
            continue
        shared_groups += 1
        # Avoid a many-to-many flood from common glosses. Keep the group in the
        # diagnostics and deny expansion instead of arbitrarily dropping rows.
        if len(g_rows) * len(l_rows) > 2500:
            skipped_oversized += 1
            continue
        for greek in g_rows:
            g_authors = set(greek["authors"])
            if not g_authors:
                continue
            for latin in l_rows:
                shared_authors = sorted(g_authors.intersection(latin["authors"]), key=str.casefold)
                if not shared_authors:
                    skipped_no_author += 1
                    continue
                pair = (greek["original_key"], latin["original_key"])
                row = pair_evidence.setdefault(pair, {
                    "greek_forms": set(),
                    "latin_forms": set(),
                    "greek_pos": set(),
                    "latin_pos": set(),
                    "evidence": {},
                    "shared_authors": set(),
                    "support_score": 0.0,
                })
                evidence_key = key[0] + "\u241f" + key[1]
                evidence = row["evidence"].setdefault(evidence_key, {
                    "english_collocation": greek["translated"],
                    "syntax_type": greek["syntax_type"],
                    "greek": [],
                    "latin": [],
                    "shared_authors": set(),
                })
                def compact(record: dict) -> dict:
                    return {
                        "form": record["original"],
                        "entry_form": record["entry_form"],
                        "pos": record["pos"],
                        "count": record["count"],
                        "loglikelihood": record["loglikelihood"],
                        "source_member": record["source_member"],
                        "authors": record["authors"],
                    }
                grec = compact(greek)
                latc = compact(latin)
                if grec not in evidence["greek"]:
                    evidence["greek"].append(grec)
                if latc not in evidence["latin"]:
                    evidence["latin"].append(latc)
                evidence["shared_authors"].update(shared_authors)
                row["greek_forms"].add(greek["original"])
                row["latin_forms"].add(latin["original"])
                row["greek_pos"].add(greek["pos"])
                row["latin_pos"].add(latin["pos"])
                row["shared_authors"].update(shared_authors)
                row["support_score"] += min(math.log1p(greek["count"]), math.log1p(latin["count"])) + min(
                    max(greek["loglikelihood"], 0.0), max(latin["loglikelihood"], 0.0)
                ) / 100.0

    candidates = []
    for (greek_key, latin_key), row in pair_evidence.items():
        evidence_rows = []
        for value in sorted(row["evidence"].values(), key=lambda x: (x["syntax_type"], x["english_collocation"].casefold())):
            value["shared_authors"] = sorted(value["shared_authors"], key=str.casefold)
            value["greek"] = sorted(value["greek"], key=lambda x: (x["form"].casefold(), x["source_member"]))
            value["latin"] = sorted(value["latin"], key=lambda x: (x["form"].casefold(), x["source_member"]))
            evidence_rows.append(value)
        candidates.append({
            "candidate_id": hashlib.sha256((greek_key + "\0" + latin_key).encode("utf-8")).hexdigest()[:20],
            "greek": sorted(row["greek_forms"], key=str.casefold),
            "latin": sorted(row["latin_forms"], key=str.casefold),
            "greek_pos_observed": sorted(row["greek_pos"]),
            "latin_pos_observed": sorted(row["latin_pos"]),
            "shared_authors": sorted(row["shared_authors"], key=str.casefold),
            "independent_english_collocation_keys": len(evidence_rows),
            "support_score": round(row["support_score"], 6),
            "evidence": evidence_rows,
            "epistemic_status": "HYPOTHESIS_ONLY_REQUIRES_HELD_OUT_PHILOLOGICAL_VALIDATION",
        })
    candidates.sort(key=lambda x: (-x["independent_english_collocation_keys"], -x["support_score"], x["candidate_id"]))
    truncated = len(candidates) > MAX_OUTPUT_CANDIDATES
    return {
        "candidate_count": len(candidates),
        "candidate_output_truncated": truncated,
        "candidates": candidates[:MAX_OUTPUT_CANDIDATES],
        "alignment_diagnostics": {
            "shared_english_collocation_and_syntax_groups": shared_groups,
            "candidate_pairs_with_shared_author": len(candidates),
            "pairs_rejected_without_shared_author": skipped_no_author,
            "groups_skipped_for_many_to_many_ambiguity": skipped_oversized,
            "pairing_rule": "EXACT_NORMALIZED_ENGLISH_COLLOCATION + EXACT_SYNTAX_TYPE + AT_LEAST_ONE_SHARED_AUTHOR",
            "translation_equivalence_asserted": False,
            "automatic_runtime_promotion": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--greek", type=Path, required=True)
    parser.add_argument("--latin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    greek = parse_archive(args.greek, "grc")
    latin = parse_archive(args.latin, "lat")
    alignment = build_candidates(greek, latin)
    report = {
        "schema": "LOUKSNAPG2_DYNAMIC_LEXICON_ALIGNMENT_CANDIDATES/1.0",
        "status": "PASS_CANDIDATE_EXTRACTION_ONLY",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "license": SOURCE_LICENSE,
            "attribution": "Perseus Digital Library Dynamic Lexicon",
            "greek_archive_sha256": sha256_file(args.greek),
            "latin_archive_sha256": sha256_file(args.latin),
        },
        "source_coverage": {
            "greek_collocation_records": len(greek),
            "latin_collocation_records": len(latin),
            "greek_source_members_with_collocations": len({x["source_member"] for x in greek}),
            "latin_source_members_with_collocations": len({x["source_member"] for x in latin}),
        },
        "alignment": {
            key: value for key, value in alignment.items() if key != "candidates"
        },
        "candidate_policy": {
            "shared_english_gloss_without_author_is_insufficient": True,
            "source_forms_and_morphology_preserved": True,
            "ambiguity_preserved": True,
            "foma_runtime_promotion": "NOT_AUTHORIZED",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
