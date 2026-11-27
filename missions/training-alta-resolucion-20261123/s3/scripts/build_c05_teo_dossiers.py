#!/usr/bin/env python3
"""Compile 50 source-bound TEO dossiers without inventing biblical source inputs."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/"PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
OUT=ROOT/"missions/training-alta-resolucion-20261123/s3/reports/C05_TEO_DOSSIERS.jsonl"
SUMMARY=ROOT/"missions/training-alta-resolucion-20261123/s3/reports/C05_TEO_DOSSIERS_SUMMARY.json"
EXPECTED=[f"MGL5-TEO-{i:04d}" for i in range(1,51)]
PATTERN=re.compile(r"(?m)^\[(MGL5-TEO-\d{4})\]")

def main() -> int:
    raw=SOURCE.read_bytes()
    text=raw.decode("utf-8")
    matches=list(PATTERN.finditer(text))
    ids=[m.group(1) for m in matches]
    if ids!=EXPECTED:
        raise SystemExit(f"TEO source population mismatch: {len(ids)} records; expected 50 unique ordered IDs")
    lines=raw.splitlines(keepends=True)
    source_sha=hashlib.sha256(raw).hexdigest()
    blob=hashlib.sha1(f"blob {len(raw)}\0".encode("ascii")+raw).hexdigest()
    rows=[]
    for index,match in enumerate(matches):
        end_offset=matches[index+1].start() if index+1<len(matches) else len(text)
        excerpt=text[match.start():end_offset].rstrip("\n")
        start=text.count("\n",0,match.start())+1
        end=start+excerpt.count("\n")
        exact=b"".join(lines[start-1:end])
        if exact.decode("utf-8").rstrip("\n")!=excerpt:
            raise SystemExit(f"line-range mismatch for {match.group(1)}")
        header=excerpt.splitlines()[0]
        operation=re.search(r"OPERACIÓN:\s*(.*?)\s*\|\s*CRITERIO:",header)
        criterion=re.search(r"CRITERIO:\s*(.*)$",header)
        control=re.search(r"(?m)^CONTROL:\s*(.*)$",excerpt)
        if not operation or not criterion or not control:
            raise SystemExit(f"incomplete source contract for {match.group(1)}")
        missing=["primary_text_and_edition","book_chapter_verse_or_passage","pericope_boundaries","immediate_context","historical_cultural_sources","language_and_lexical_sources"]
        rows.append({
            "case_id":match.group(1),
            "title":header.split("] ",1)[1].split(" | ",1)[0],
            "source":{"file":SOURCE.name,"line_start":start,"line_end":end,"sha256":source_sha,"git_blob":blob,"excerpt_sha256":hashlib.sha256(exact).hexdigest(),"exact_excerpt":excerpt},
            "operation":operation.group(1).strip(),
            "acceptance_criterion":criterion.group(1).strip(),
            "source_control":control.group(1).strip(),
            "hermeneutic_pipeline":["TEXT","OBSERVATION","LINGUISTIC_ANALYSIS","CONTEXT","HISTORICAL_CULTURAL_ANALYSIS","INFERENCE","INTERPRETATION","DOCTRINAL_SYNTHESIS","VALIDATION"],
            "anti_error_controls":["EISEGESIS","PROOF_TEXTING","ANACHRONISM","LEXICAL_FALLACY","SEMANTIC_OVERLOADING","CONTEXTUAL_DISPLACEMENT","CIRCULARITY"],
            "required_source_inputs":{key:None for key in missing},
            "missing_essential_inputs":missing,
            "oracle_requirement":"TEXT_SOURCE + PRIMARY_SOURCES + INDEPENDENT_AUDIT_OF_INFERENCES",
            "human_review_required":True,
            "execution_status":"BLOCKED",
            "validation_status":"NOT_RUN",
            "certification_status":"NOT_CERTIFIED",
            "block_reason":"The training source defines the method and criterion but does not supply the primary passage, edition, pericope and context needed to perform this case without inventing evidence."
        })
    if OUT.exists() or SUMMARY.exists():
        raise SystemExit("refusing overwrite of existing TEO dossier artifacts")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text("".join(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n" for row in rows),encoding="utf-8")
    summary={"source_sha256":source_sha,"source_blob":blob,"dossiers":len(rows),"unique_ids":len({r["case_id"] for r in rows}),"execution_status_counts":{"BLOCKED":len(rows)},"validation_status_counts":{"NOT_RUN":len(rows)},"human_review_required":len(rows),"status":"SOURCE_BOUND_DOSSIERS_COMPILED_NOT_EXECUTED_NOT_VALIDATED"}
    SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
