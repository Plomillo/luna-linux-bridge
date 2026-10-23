#!/usr/bin/env python3
"""Independent structural validation of the temporary BTX SQLite candidate.

This validator does not trust the builder's pass/fail flag. It checks the database
using a separate read-only process. It does NOT certify verse-by-verse equivalence
against the PDF; that remains a separate content-validation gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

EXPECTED_BOOKS = [
 ("Génesis",50),("Éxodo",40),("Levítico",27),("Números",36),("Deuteronomio",34),
 ("Josué",24),("Jueces",21),("Rut",4),("1 Samuel",31),("2 Samuel",24),
 ("1 Reyes",22),("2 Reyes",25),("1 Crónicas",29),("2 Crónicas",36),("Esdras",10),
 ("Nehemías",13),("Ester",10),("Job",42),("Salmos",150),("Proverbios",31),
 ("Eclesiastés",12),("Cantares",8),("Isaías",66),("Jeremías",52),("Lamentaciones",5),
 ("Ezequiel",48),("Daniel",12),("Oseas",14),("Joel",3),("Amós",9),("Abdías",1),
 ("Jonás",4),("Miqueas",7),("Nahúm",3),("Habacuc",3),("Sofonías",3),("Hageo",2),
 ("Zacarías",14),("Malaquías",4),("Mateo",28),("Marcos",16),("Lucas",24),("Juan",21),
 ("Hechos",28),("Romanos",16),("1 Corintios",16),("2 Corintios",13),("Gálatas",6),
 ("Efesios",6),("Filipenses",4),("Colosenses",4),("1 Tesalonicenses",5),
 ("2 Tesalonicenses",3),("1 Timoteo",6),("2 Timoteo",4),("Tito",3),("Filemón",1),
 ("Hebreos",13),("Santiago",5),("1 Pedro",5),("2 Pedro",3),("1 Juan",5),("2 Juan",1),
 ("3 Juan",1),("Judas",1),("Apocalipsis",22)
]
REFERENCE_CASES = [
 ("Génesis",1,1),("Salmos",1,1),("Salmos",119,1),("Salmos",150,1),
 ("Mateo",1,1),("Juan",3,16),("Romanos",8,28),("Apocalipsis",22,21),
 ("Abdías",1,1),("Filemón",1,1),("2 Juan",1,1),("3 Juan",1,1),("Judas",1,1),
]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def as_value(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw

def source_hashes(source_audit: Path) -> tuple[str | None,str | None]:
    data=json.loads(source_audit.read_text(encoding="utf-8"))
    archive=data.get("source_archive",{})
    archive_hash=archive.get("sha256")
    pdf_hash=None
    for item in archive.get("pdf_audits",[]):
        if item.get("sha256"):
            pdf_hash=item["sha256"]
            break
    return archive_hash,pdf_hash

def validate(database: Path, source_audit: Path | None) -> dict[str,Any]:
    report: dict[str,Any]={
        "schema":"BTX_SQLITE_INDEPENDENT_VALIDATION/1.0",
        "database_path":database.name,
        "certification":"NOT_GRANTED",
        "source_removal_allowed":False,
        "source_pdf_removed":False,
        "verse_text_emitted":False,
        "source_equivalence":"NOT_INDEPENDENTLY_VALIDATED",
        "checks":{},
        "failures":[],
    }
    report["database_file_bytes"]=database.stat().st_size
    report["database_sha256"]=sha256(database)
    con=sqlite3.connect(f"file:{database.resolve()}?mode=ro",uri=True)
    con.row_factory=sqlite3.Row
    integrity=con.execute("PRAGMA integrity_check").fetchone()[0]
    report["checks"]["sqlite_integrity_check"]={"status":"PASS" if integrity=="ok" else "FAIL","value":integrity}
    if integrity!="ok":
        report["failures"].append("SQLITE_INTEGRITY_CHECK_FAILED")

    fk_issues=con.execute("PRAGMA foreign_key_check").fetchall()
    report["checks"]["foreign_key_check"]={"status":"PASS" if not fk_issues else "FAIL","issue_count":len(fk_issues)}
    if fk_issues:
        report["failures"].append("FOREIGN_KEY_VIOLATIONS")

    tables={r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    required={"metadata","books","chapters","verses","source_reference_gaps"}
    report["checks"]["required_tables"]={"status":"PASS" if required.issubset(tables) else "FAIL","present":sorted(required&t ables) if False else sorted(required & tables),"missing":sorted(required-tables)}
    if not required.issubset(tables):
        report["failures"].append("REQUIRED_TABLE_MISSING")
    if "verses_fts" in tables:
        report["failures"].append("CORE_DATABASE_UNEXPECTEDLY_BUNDLES_FTS5")
    report["checks"]["core_database_compact_policy"]={"status":"PASS" if "verses_fts" not in tables else "FAIL","fts5_table_bundled":"verses_fts" in tables}

    metadata={r["key"]:as_value(r["value"]) for r in con.execute("SELECT key,value FROM metadata")}
    report["source_archive_sha256"]=metadata.get("source_archive_sha256")
    report["source_pdf_sha256"]=metadata.get("source_pdf_sha256")
    report["parser_version"]=metadata.get("parser_version")
    report["metadata_content_scope"]=metadata.get("content_scope")
    if source_audit and source_audit.is_file():
        expected_archive,expected_pdf=source_hashes(source_audit)
        pass_hashes=metadata.get("source_archive_sha256")==expected_archive and metadata.get("source_pdf_sha256")==expected_pdf
        report["checks"]["source_provenance_binding"]={
            "status":"PASS" if pass_hashes else "FAIL",
            "source_archive_sha256_matches":metadata.get("source_archive_sha256")==expected_archive,
            "source_pdf_sha256_matches":metadata.get("source_pdf_sha256")==expected_pdf,
        }
        if not pass_hashes:
            report["failures"].append("SOURCE_HASH_BINDING_MISMATCH")

    books=con.execute("SELECT book_id,book_order,name,abbreviation FROM books ORDER BY book_order").fetchall()
    expected_names=[item[0] for item in EXPECTED_BOOKS]
    actual_names=[row["name"] for row in books]
    book_pass=len(books)==66 and actual_names==expected_names and [r["book_order"] for r in books]==list(range(1,67))
    report["book_count"]=len(books)
    report["checks"]["canonical_book_catalog"]={"status":"PASS" if book_pass else "FAIL","expected_count":66,"actual_count":len(books),"ordered_names_exact":actual_names==expected_names}
    if not book_pass:
        report["failures"].append("BOOK_CATALOG_MISMATCH")

    chapters=con.execute("SELECT book_id,chapter_number FROM chapters ORDER BY book_id,chapter_number").fetchall()
    expected_chapters=sum(count for _,count in EXPECTED_BOOKS)
    chapter_map: dict[int,list[int]]={}
    for row in chapters:
        chapter_map.setdefault(int(row["book_id"]),[]).append(int(row["chapter_number"]))
    chapter_sequence_pass=(len(chapters)==expected_chapters)
    for i,(_,count) in enumerate(EXPECTED_BOOKS,start=1):
        if chapter_map.get(i)!=list(range(1,count+1)):
            chapter_sequence_pass=False
    report["chapter_count"]=len(chapters)
    report["checks"]["canonical_chapter_sequence"]={"status":"PASS" if chapter_sequence_pass else "FAIL","expected_count":expected_chapters,"actual_count":len(chapters),"all_chapter_sequences_exact":chapter_sequence_pass}
    if not chapter_sequence_pass:
        report["failures"].append("CHAPTER_SEQUENCE_MISMATCH")

    verse_count=con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    empty_count=con.execute("SELECT COUNT(*) FROM verses WHERE text IS NULL OR length(trim(text))=0").fetchone()[0]
    duplicate_ids=con.execute("SELECT COUNT(*) FROM (SELECT verse_id FROM verses GROUP BY verse_id HAVING COUNT(*)>1)").fetchone()[0]
    duplicate_refs=con.execute("SELECT COUNT(*) FROM (SELECT book_id,chapter_number,verse_number,verse_suffix FROM verses GROUP BY book_id,chapter_number,verse_number,verse_suffix HAVING COUNT(*)>1)").fetchone()[0]
    report["verse_row_count"]=verse_count
    report["checks"]["verse_rows"]={"status":"PASS" if verse_count>0 and empty_count==0 and duplicate_ids==0 and duplicate_refs==0 else "FAIL","empty_text_rows":empty_count,"duplicate_ids":duplicate_ids,"duplicate_references":duplicate_refs}
    if verse_count<=0 or empty_count or duplicate_ids or duplicate_refs:
        report["failures"].append("VERSE_ROW_VALIDATION_FAILED")

    indices={r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    expected_indices={"idx_verses_reference","idx_verses_id"}
    report["checks"]["reference_indexes"]={"status":"PASS" if expected_indices.issubset(indices) else "FAIL","indices_present":sorted(expected_indices & indices)}
    if not expected_indices.issubset(indices):
        report["failures"].append("REFERENCE_INDEX_MISSING")

    gap_rows=con.execute("SELECT g.book_id,g.chapter_number,g.verse_number,g.status FROM source_reference_gaps g ORDER BY g.book_id,g.chapter_number,g.verse_number").fetchall()
    overlap=0
    for gap in gap_rows:
        exists=con.execute("SELECT 1 FROM verses WHERE book_id=? AND chapter_number=? AND verse_number=? AND verse_suffix=''",(gap["book_id"],gap["chapter_number"],gap["verse_number"])).fetchone()
        if exists:
            overlap+=1
    gap_count=int(metadata.get("source_unmarked_reference_count",0) or 0)
    gap_pass=len(gap_rows)==gap_count and overlap==0 and all(g["status"]=="NO_EXPLICIT_VERSE_MARKER_FOUND_IN_SOURCE_RANGE" for g in gap_rows)
    report["source_unmarked_reference_count"]=len(gap_rows)
    report["checks"]["source_reference_gaps"]={"status":"PASS" if gap_pass else "FAIL","metadata_count":gap_count,"table_count":len(gap_rows),"overlap_with_verse_rows":overlap,"policy":"NO_TEXT_SYNTHESIZED"}
    if not gap_pass:
        report["failures"].append("SOURCE_REFERENCE_GAP_TABLE_MISMATCH")

    query_results=[]
    for book,ch,verse in REFERENCE_CASES:
        row=con.execute("SELECT v.verse_id FROM verses v JOIN books b ON b.book_id=v.book_id WHERE b.name=? AND v.chapter_number=? AND v.verse_number=? AND v.verse_suffix='' AND length(trim(v.text))>0 LIMIT 1",(book,ch,verse)).fetchone()
        query_results.append({"book":book,"chapter":ch,"verse":verse,"found":bool(row)})
    passed=sum(x["found"] for x in query_results)
    report["checks"]["reference_queries"]={"status":"PASS" if passed==len(REFERENCE_CASES) else "FAIL","cases":len(REFERENCE_CASES),"passed":passed,"results":query_results}
    if passed!=len(REFERENCE_CASES):
        report["failures"].append("REFERENCE_QUERY_TEST_FAILURE")

    # Independent transient FTS5 probe; no FTS index is added to the delivered core DB.
    ftstest={"passed":False,"bundled_in_core_database":False,"mode":"TRANSIENT_IN_MEMORY_PROTOTYPE","text_emitted":False}
    try:
        rows=con.execute("SELECT verse_id,text FROM verses WHERE length(trim(text))>0 ORDER BY book_id,chapter_number,verse_number,verse_suffix").fetchall()
        if rows:
            tokens=re.findall(r"[^\W_]{4,}",rows[0]["text"],flags=re.UNICODE)
            if tokens:
                tmp=sqlite3.connect(":memory:")
                tmp.execute("CREATE VIRTUAL TABLE probe_fts USING fts5(verse_id UNINDEXED,text,tokenize='unicode61 remove_diacritics 2')")
                tmp.executemany("INSERT INTO probe_fts(verse_id,text) VALUES(?,?)",[(r["verse_id"],r["text"]) for r in rows])
                match=tmp.execute("SELECT verse_id FROM probe_fts WHERE probe_fts MATCH ? LIMIT 1",(tokens[0],)).fetchone()
                ftstest.update({"passed":bool(match),"indexed_rows":len(rows),"query_token_length":len(tokens[0])})
                tmp.close()
    except sqlite3.OperationalError as exc:
        ftstest.update({"reason":type(exc).__name__})
    report["checks"]["optional_full_text_search_probe"]=ftstest
    if not ftstest["passed"]:
        report["failures"].append("OPTIONAL_FULL_TEXT_SEARCH_PROBE_FAILED")

    report["content_equivalence_against_original_pdf"]="NOT independently verified"
    report["editorial_notes_and_cross_references"]="NOT included/certified by this body-text candidate"
    report["candidate_structural_independent_validation"]="PASS" if not report["failures"] else "FAIL"
    report["certification"]="NOT_GRANTED"
    report["source_removal_allowed"]=False
    con.close()
    return report

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--database",type=Path,required=True)
    p.add_argument("--source-audit",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    try:
        report=validate(a.database,a.source_audit)
    except Exception as exc:
        report={"schema":"BTX_SQLITE_INDEPENDENT_VALIDATION/1.0","candidate_structural_independent_validation":"ABORTED_FAIL_CLOSED","certification":"NOT_GRANTED","source_removal_allowed":False,"error":type(exc).__name__,"source_equivalence":"NOT_INDEPENDENTLY_VALIDATED"}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="checks"},ensure_ascii=False,indent=2))
    return 0 if report.get("candidate_structural_independent_validation")=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
