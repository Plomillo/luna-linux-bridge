#!/usr/bin/env python3
"""Validate Louksna1 axiom-table provenance and execute it as an RDF graph with packaged Jena.

This is a structural/provenance execution gate only; it is not a proof of semantic truth.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

HEADING = "# LUNACORE V15 --- B15-B134 AXIOM MATERIALIZATION REGISTRY"
END_HEADING = "## Integrity Checks"
LEGACY = re.compile(r"^[ \t]*id:[ \t]*(AX\d+)\b", re.MULTILINE)
AXID = re.compile(r"AX\d{5}")
TRACE = re.compile(r"TRACE-V11-(B\d{3})::(AX\d{5})")
RDF_TYPE = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
LABEL = "<http://www.w3.org/2000/01/rdf-schema#label>"
DERIVED = "<http://www.w3.org/ns/prov#wasDerivedFrom>"
INTEGER = "<http://www.w3.org/2001/XMLSchema#integer>"
P = lambda name: f"<urn:louksna:{name}>"

def sha(data): return hashlib.sha256(data).hexdigest()
def lit(value): return json.dumps(value, ensure_ascii=False)
def line_uri(n): return f"<urn:louksna:source-line:{n}>"
def add(rows, s, p, o): rows.append(f"{s} {p} {o} .")
def is_row(line):
    return len(line) >= 59 and bool(AXID.fullmatch(line[2:9].strip())) and line[9:20].isspace()

def parse_legacy(text):
    return [{"id":m.group(1),"numeric":int(m.group(1)[2:]),"line":text.count("\n",0,m.start())+1}
            for m in LEGACY.finditer(text)]

def parse_materialized(text):
    if text.count(HEADING) != 1:
        raise ValueError("MATERIALIZATION_HEADING_COUNT_MISMATCH")
    lines=text.splitlines()
    start=next(i for i,v in enumerate(lines) if v.strip()==HEADING)
    ends=[i for i in range(start+1,len(lines)) if lines[i].strip()==END_HEADING]
    if not ends: raise ValueError("MATERIALIZATION_END_MARKER_MISSING")
    stop=ends[0]
    rows=[]
    for i in range(start+1,stop):
        line=lines[i]
        if not is_row(line): continue
        aid=line[2:9].strip()
        cls=line[20:38].strip()
        first=line[38:59].strip()
        trace=line[59:].strip()
        match=TRACE.fullmatch(trace)
        if not match or match.group(2)!=aid:
            raise ValueError(f"AXIOM_ROW_TRACE_MISMATCH:{i+1}:{aid}:{trace[:80]}")
        if not cls or not first: raise ValueError(f"AXIOM_ROW_FIELDS_EMPTY:{i+1}:{aid}")
        parts=[first]
        j=i+1
        while j<stop:
            cont=lines[j]
            if is_row(cont): break
            if not cont.strip(): break
            if len(cont)>=59 and not cont[:38].strip() and cont[38:59].strip() and not cont[59:].strip():
                parts.append(cont[38:59].strip()); j+=1
            else: break
        rows.append({"id":aid,"numeric":int(aid[2:]),"class":cls,"text":" ".join(parts),
                     "trace":trace,"block":match.group(1),"line":i+1})
    return rows

def expected_block(n):
    if 2415<=n<=5774: return 15+(n-2415)//84
    if 5775<=n<=12414: return 55+(n-5775)//83
    raise ValueError(f"AXIOM_OUTSIDE_MATERIALIZED_RANGE:{n}")

def validate_materialized(rows):
    expected=list(range(2415,12415)); numbers=[r["numeric"] for r in rows]
    if len(rows)!=10000: raise ValueError(f"AXIOM_RECORD_COUNT:{len(rows)}!=10000")
    if len(set(numbers))!=len(numbers): raise ValueError("AXIOM_DUPLICATE_NUMERIC_IDS")
    if sorted(numbers)!=expected: raise ValueError("AXIOM_RANGE_NOT_CONTIGUOUS")
    counts=collections.Counter(); classes=collections.Counter(); text_hashes=collections.Counter()
    for row in rows:
        if not row["text"].strip(): raise ValueError(f"AXIOM_TEXT_EMPTY:{row['id']}")
        if row["block"]!=f"B{expected_block(row['numeric']):03d}":
            raise ValueError(f"AXIOM_BLOCK_ALLOCATION_MISMATCH:{row['id']}:{row['block']}")
        counts[row["block"]]+=1; classes[row["class"]]+=1
        text_hashes[sha(row["text"].encode())]+=1
    target={f"B{i:03d}":(84 if i<=54 else 83) for i in range(15,135)}
    actual={k:counts[k] for k in target}
    if actual!=target: raise ValueError("AXIOM_BLOCK_COUNTS_MISMATCH")
    return {"record_count":len(rows),"unique_ids":True,"first_id":rows[0]["id"],"last_id":rows[-1]["id"],
            "range":"AX2415-AX12414","contiguous":True,"trace_alignment":"PASS","block_allocation":"PASS",
            "block_count":len(counts),"block_counts":actual,"class_counts":dict(sorted(classes.items())),
            "exact_duplicate_text_extra_occurrences":sum(v-1 for v in text_hashes.values() if v>1),
            "semantic_validity":"NOT_ESTABLISHED_BY_STRUCTURAL_AUDIT"}

def legacy_census(rows):
    nums=[r["numeric"] for r in rows]; lex=[r["id"] for r in rows]; freq=collections.Counter(nums)
    gaps=[n for n in range(1,2415) if n not in set(nums)]
    result={"definition_records":len(rows),"distinct_numeric_ids":len(set(nums)),
            "distinct_lexical_ids":len(set(lex)),"repeated_definition_records":len(rows)-len(set(nums)),
            "numeric_gaps_1_2414":len(gaps),"gap_ids_first_32":[f"AX{n:04d}" for n in gaps[:32]],
            "ids_with_repeated_records":sum(v>1 for v in freq.values()),
            "historical_657_gap_claim":"DISCLOSED_NONBLOCKING_HISTORICAL_DEBT"}
    return result

def build_graph(axioms, legacy, out):
    triples=[]
    for r in axioms:
        s=f"<urn:louksna:axiom:{r['id']}>"; src=line_uri(r["line"])
        for p,o in [(RDF_TYPE,"<urn:louksna:Axiom>"),(LABEL,lit(r["id"])),(P("axiomClass"),lit(r["class"])),
                    (P("axiomText"),lit(r["text"])),(P("traceId"),lit(r["trace"])),
                    (P("blockId"),lit(r["block"])),(P("sourceLine"),f'"{r["line"]}"^^{INTEGER}'),(DERIVED,src)]:
            add(triples,s,p,o)
        add(triples,src,RDF_TYPE,"<urn:louksna:SourceRow>")
        add(triples,src,LABEL,lit(f"LOUKSNAMEJORADA.md#L{r['line']}"))
    for r in legacy:
        occurrence=f"<urn:louksna:legacy-definition-occurrence:L{r['line']}>"
        axid=f"<urn:louksna:legacy-axiom-id:{r['id']}>"; src=line_uri(r["line"])
        add(triples,occurrence,RDF_TYPE,"<urn:louksna:LegacyDefinitionOccurrence>")
        add(triples,occurrence,P("axiomIdentifier"),axid)
        add(triples,occurrence,P("legacyNumericId"),f'"{r["numeric"]}"^^{INTEGER}')
        add(triples,occurrence,P("sourceLine"),f'"{r["line"]}"^^{INTEGER}')
        add(triples,occurrence,DERIVED,src)
        add(triples,axid,RDF_TYPE,"<urn:louksna:LegacyAxiomIdentifier>")
        add(triples,axid,LABEL,lit(r["id"]))
    out.parent.mkdir(parents=True,exist_ok=True)
    data=("\n".join(triples)+"\n").encode("utf-8"); out.write_bytes(data)
    return len(triples),sha(data),len(data)

def jena_query(jena_root, graph, query_text, query_path):
    query_path.write_text(query_text+"\n",encoding="utf-8")
    cmd=["sh",str(jena_root/"bin"/"arq"),f"--data={graph}",f"--query={query_path}","--results=JSON"]
    result=subprocess.run(cmd,cwd=jena_root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300,check=False)
    if result.returncode: raise RuntimeError("JENA_ARQ_FAILED:"+result.stderr[-2500:])
    start=result.stdout.find("{")
    if start<0: raise RuntimeError("JENA_ARQ_JSON_RESULT_MISSING:"+result.stdout[-1000:])
    payload=json.loads(result.stdout[start:]); bindings=payload.get("results",{}).get("bindings",[])
    if len(bindings)!=1 or "count" not in bindings[0]: raise RuntimeError("JENA_ARQ_COUNT_RESULT_INVALID")
    return int(bindings[0]["count"]["value"])

def execute_jena_graph(jena, graph, output):
    jena = Path(jena).resolve()
    for path in (jena, jena / "bin" / "riot", jena / "bin" / "arq"):
        if path.is_symlink() or not (path.is_dir() if path == jena else path.is_file()):
            raise RuntimeError("PACKAGED_JENA_MISSING_OR_SYMLINK:" + str(path))
        if not path.resolve().is_relative_to(jena):
            raise RuntimeError("PACKAGED_JENA_PATH_ESCAPE:" + str(path))
    riot = subprocess.run(
        ["sh", str(jena / "bin" / "riot"), "--syntax=NT", str(graph)],
        cwd=jena, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, timeout=300, check=False,
    )
    if riot.returncode:
        raise RuntimeError("JENA_RIOT_PARSE_FAILED:" + riot.stderr[-2500:])
    counts = {}
    queries = {
        "materialized_axioms": (
            "SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s <urn:louksna:traceId> ?o . }", 10000
        ),
        "legacy_definition_occurrences": (
            "SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s a <urn:louksna:LegacyDefinitionOccurrence> . }", 1927
        ),
        "legacy_distinct_numeric_ids": (
            "SELECT (COUNT(DISTINCT ?n) AS ?count) WHERE { ?s <urn:louksna:legacyNumericId> ?n . }", 1708
        ),
    }
    for name, (query, expected) in queries.items():
        actual = jena_query(jena, graph, query, output / (name + ".rq"))
        if actual != expected:
            raise ValueError(f"JENA_QUERY_COUNT_MISMATCH:{name}:{actual}!={expected}")
        counts[name] = {"count": actual, "expected": expected, "status": "PASS"}
    return {"riot_parse": "PASS", "sparql_counts": counts}


def audit(args):
    source=Path(args.source).read_bytes(); companion=Path(args.companion).read_bytes()
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    source_sha=sha(source); companion_sha=sha(companion)
    expected_factory_sha=os.environ.get("LOUKSNA_FACTORY_HEAD_SHA","").strip()
    factory_run_id=os.environ.get("LOUKSNA_FACTORY_RUN_ID","").strip()
    manifest_source_sha=manifest.get("source_commit")
    if not isinstance(manifest_source_sha,str) or not re.fullmatch(r"[0-9a-f]{40}",manifest_source_sha):
        raise ValueError("RELEASE_MANIFEST_SOURCE_COMMIT_INVALID")
    if expected_factory_sha and manifest_source_sha != expected_factory_sha:
        raise ValueError("FACTORY_SOURCE_COMMIT_MISMATCH_WITH_RELEASE_MANIFEST")
    # Always bind the structural graph audit to evidence for the manifest's exact
    # candidate. An empty workflow_run environment must not bypass this gate.
    evidence_root=Path("docs/cajita-luna")
    g23=json.loads((evidence_root/"LOUKSNA1_G23_EVIDENCE.json").read_text(encoding="utf-8"))
    g24=json.loads((evidence_root/"LOUKSNA1_G24_EVIDENCE.json").read_text(encoding="utf-8"))
    task=json.loads((evidence_root/"LOUKSNA1_TASK_ADAPTER_EVIDENCE.json").read_text(encoding="utf-8"))
    if g23.get("status")!="PASS" or g23.get("source_commit")!=manifest_source_sha:
        raise ValueError("G23_EVIDENCE_NOT_PASS_OR_SOURCE_MISMATCH")
    if g24.get("status")!="PASS_FOR_DECLARED_SYNTHETIC_FUNCTIONAL_E2E_SCOPE" or g24.get("source_commit")!=manifest_source_sha:
        raise ValueError("G24_EVIDENCE_NOT_PASS_OR_SOURCE_MISMATCH")
    if task.get("status")!="PASS_SYNTHETIC_END_TO_END_EXECUTION_ONLY" or task.get("source_commit")!=manifest_source_sha:
        raise ValueError("TASK_ADAPTER_EVIDENCE_NOT_PASS_OR_SOURCE_MISMATCH")
    bound_factory_evidence={"factory_run_id":factory_run_id,"source_commit":manifest_source_sha,
                            "G23":g23["status"],"G24":g24["status"],"task_adapter_evidence":task["status"]}
    if source_sha!=manifest["protected_architecture"]["sha256"]: raise ValueError("PROTECTED_SOURCE_SHA256_MISMATCH")
    if not companion.startswith(source): raise ValueError("LOUKSNA1_PREFIX_NOT_BYTE_EXACT")
    if companion_sha!=manifest["louksna1"]["sha256"]: raise ValueError("LOUKSNA1_SHA256_MISMATCH")
    text=source.decode("utf-8"); legacy=parse_legacy(text); axiom_rows=parse_materialized(text)
    legacy_result=legacy_census(legacy)
    expected_legacy={"definition_records":1927,"distinct_numeric_ids":1708,
                     "repeated_definition_records":219,"numeric_gaps_1_2414":706}
    for key,value in expected_legacy.items():
        if legacy_result[key]!=value:
            raise ValueError(f"LEGACY_SOURCE_CENSUS_MISMATCH:{key}:{legacy_result[key]}!={value}")
    axiom_result=validate_materialized(axiom_rows)
    output=Path(args.output).resolve(); graph=output/"louksna1-axiom-provenance.nt"
    triple_count,graph_sha,graph_bytes=build_graph(axiom_rows,legacy,graph)
    root=Path(args.runtime).resolve()
    sys.path.insert(0,str(root))
    from cajita_externalized_packaging import materialize_registered_asset
    with tempfile.TemporaryDirectory(prefix="louksna1-jena-verified-") as temp_name:
        extraction_root=Path(temp_name)/"jena-runtime"
        jena_reconstruction=materialize_registered_asset(root,"APACHE_JENA_6_2_0",extraction_root)
        jena=extraction_root/"apache-jena-6.2.0"
        jena_results=execute_jena_graph(jena,graph,output)

    return {
      "schema":"LOUKSNA1_INTEGRAL_CERTIFICATION_ASSESSMENT/1.0",
      "assessment":"PASS_STRUCTURAL_AXIOM_GRAPH_EXECUTION","decision":"HOLD","global_certification":"NOT_GRANTED",
      "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
      "source_commit":manifest.get("source_commit"),"factory_evidence_binding":bound_factory_evidence,
      "source":{"path":Path(args.source).name,"sha256":source_sha,"bytes":len(source),
                "companion_sha256":companion_sha,"companion_bytes":len(companion),"protected_prefix_byte_exact":True},
      "legacy_definition_census":legacy_result,"materialized_axiom_census":axiom_result,
      "rdf_graph":{"path":graph.name,"bytes":graph_bytes,"sha256":graph_sha,"triples":triple_count,
                   "format":"N-Triples","scope":"CONTENT_CLASS_BLOCK_TRACE_SOURCE_LINE_PROVENANCE"},
      "jena":{"container_reconstruction":jena_reconstruction,**jena_results},
      "semantic_gates":{"axiom_proposition_validity":"NOT_ESTABLISHED",
        "semantic_consistency":"NOT_ESTABLISHED","model_quality_equivalence":"NOT_ESTABLISHED",
        "all_21_target_task_adapters":"NOT_ESTABLISHED","full_integrated_runtime_behaviour":"NOT_ESTABLISHED"},
      "blockers":["The natural-language axiom propositions and their logical consistency have not been independently validated.",
        "21 canonical target manifests still report consumer_adapter=NOT_REGISTERED_FOR_ALL_TASKS.",
        "Synthetic adapter execution does not establish quality equivalence to reference baselines.",
        "Required native/hardware and end-to-end rollback evidence is not complete."],
      "historical_debt":{"declared_gaps":657,"measured_legacy_numeric_gaps":legacy_result["numeric_gaps_1_2414"],
        "status":"DISCLOSED_NONBLOCKING_HISTORICAL_DEBT","source_mutation":False},
      "certification_scope":"STRUCTURAL_AXIOM_PROVENANCE_GRAPH_ONLY","authority":"ASSESSMENT_ONLY_NOT_A_CERTIFICATE"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--companion",required=True)
    p.add_argument("--manifest",required=True);p.add_argument("--runtime",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    try:
        out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
        report=audit(a);path=out/"LOUKSNA1_INTEGRAL_CERTIFICATION_ASSESSMENT.json"
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":report["assessment"],"global_certification":report["global_certification"],
            "materialized_axioms":report["materialized_axiom_census"]["record_count"],
            "legacy_definitions":report["legacy_definition_census"]["definition_records"],
            "rdf_triples":report["rdf_graph"]["triples"],"report":str(path)},ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"FAIL_CLOSED","global_certification":"NOT_GRANTED",
            "reason":type(exc).__name__+":"+str(exc)[:1500]},ensure_ascii=False))
        return 2
if __name__=="__main__": raise SystemExit(main())
