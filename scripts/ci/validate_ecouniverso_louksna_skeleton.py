#!/usr/bin/env python3
import hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = ROOT / "architecture/ecouniverso-louksna/ECOUNIVERSO_LOUKSNA_HARDENED_SKELETON.md"
OUT = ROOT / "evidence/ecouniverso-louksna"
BASE_REF = "origin/staging/luna-r4-master-part1-part9-20260929"

def require(text, tokens, family):
    missing=[x for x in tokens if x not in text]
    if missing:
        raise SystemExit(f"{family}_FAIL_MISSING=" + ",".join(missing))
    return {"family":family,"status":"PASS","tokens":tokens}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if not SPEC.is_file():
        raise SystemExit("SPEC_MISSING")
    text=SPEC.read_text(encoding="utf-8")

    checks=[]
    checks.append(require(text,[
        "AUDITABILITY_REQUIRED = TRUE",
        "MISSING_AUDIT_RECORD = FAIL_CLOSED",
        "CERTIFICATION_WITHOUT_AUDIT_EVIDENCE = FORBIDDEN"
    ],"AUDITABILITY"))

    checks.append(require(text,[
        "TRACEABILITY_REQUIRED = TRUE",
        "TRACE_ID_REQUIRED = TRUE",
        "MISSING_TRACE = FAIL_CLOSED",
        "TRACEABILITY_LOSS = REJECT"
    ],"TRACEABILITY"))

    checks.append(require(text,[
        "GOVERNANCE_ROOT = Louksna.md",
        "EXTEND_DO_NOT_REPLACE = TRUE",
        "APPEND_ONLY = TRUE",
        "FAIL_CLOSED = TRUE",
        "NO_SILENT_AUTHORITY_TRANSFER = TRUE",
        "AUTO_CERTIFICATION = FORBIDDEN",
        "CERTIFICATION_PROPAGATION = FORBIDDEN"
    ],"GOVERNANCE"))

    checks.append(require(text,[
        "PROVENANCE_REQUIRED = TRUE",
        "NEW_MATERIAL_PROVENANCE = MANDATORY",
        "UNRESOLVED_PROVENANCE = FAIL_CLOSED",
        "PROVENANCE_DELETION = FORBIDDEN",
        "PROVENANCE_FABRICATION = FORBIDDEN"
    ],"PROVENANCE"))

    checks.append(require(text,[
        "CANONICAL_AUTHORITY = Louksna.md",
        "ASSURANCE_STANDARD = PUAC2.md",
        "CURRENT_ORDER_MODE = QUINTO_ORDEN_MODE",
        "ORDER_CHANGE != IDENTITY_CHANGE",
        "ORDER_CHANGE != FAMILY_REPLACEMENT",
        "ORDER_CHANGE != AUTHORITY_TRANSFER",
        "VALIDATOR = G23",
        "CERTIFIER = G24",
        "STATUS_FINAL_DE_ESTA_ESPECIFICACION = CANDIDATE_NOT_CERTIFIED"
    ],"AUTHORITY_AND_ORDER"))

    family_literals=[
        "TEORIA_DE_TIPOS_DEPENDIENTES_DE_ORDEN_SUPERIOR","HOTT_UNIVALENCIA",
        "ANTIPARALISIS","ORDEN","GOBERNANZA","GENERAL","PARTICULAR",
        "MULTIDISCIPLINARIEDAD","INTERDISCIPLINARIEDAD","TRANSDISCIPLINARIEDAD",
        "ELASTICIDAD","PODA","CUANTIZACION","ENDURECIMIENTO",
        "CATOLICIDAD_REFORMADA_SISTEMATICA","NETKAIZEN","AUDITABILIDAD","TRAZABILIDAD",
        "INSTITUCION","CONSTITUCION","DIRECTRICES","MATRIX","DIRECTIVA",
        "HERMENEUTICA","EXEGESIS","TRADUCTOR","CHECKPOINT","TRANSPARENCIA",
        "ANTI_DUPLICACION","TAXONOMIA","SEMANTICA","OPTIMIZACION","METAFISICA",
        "INGENIERIA_Y_SOFTWARE","LOGICA_FORMAL","INTEGRIDAD"
    ]
    checks.append(require(text,family_literals,"FAMILY_PRESENCE"))

    diff=subprocess.check_output(
        ["git","diff","--name-status",BASE_REF+"...HEAD"],cwd=ROOT,text=True
    ).splitlines()
    deleted=[line for line in diff if line.startswith("D\t")]
    if deleted:
        raise SystemExit("DELETION_DETECTED="+"|".join(deleted))

    protected=[
        "Louksna.md",
        "PUAC2.md",
        "bridge/reasoning",
        "server/r4-master",
        "server/r4-48h"
    ]
    touched=[]
    for line in diff:
        parts=line.split("\t",1)
        if len(parts)!=2: continue
        p=parts[1]
        if p in ("Louksna.md","PUAC2.md") or p.startswith("bridge/reasoning/") or p.startswith("server/r4-master/") or p.startswith("server/r4-48h/"):
            touched.append(line)
    if touched:
        raise SystemExit("PROTECTED_EXISTING_SCOPE_MUTATED="+"|".join(touched))

    OUT.mkdir(parents=True,exist_ok=True)
    result={
        "schema":"LOUKSNA_ECOUNIVERSO_SKELETON_VALIDATION/1.0",
        "status":"PASS",
        "certification_claimed":False,
        "authority":"Louksna.md",
        "assurance_standard":"PUAC2.md",
        "spec_path":SPEC.relative_to(ROOT).as_posix(),
        "spec_sha256":sha(SPEC),
        "base_ref":"staging/luna-r4-master-part1-part9-20260929",
        "checks":checks,
        "deletions":[],
        "protected_existing_scope_mutation":[],
        "non_regression_scope":"STRUCTURAL_ADDITIVE_PREFLIGHT",
        "g23_status":"NOT_CLAIMED",
        "g24_status":"NOT_CLAIMED"
    }
    (OUT/"VALIDATION.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("AUDITABILITY=PASS")
    print("TRACEABILITY=PASS")
    print("GOVERNANCE=PASS")
    print("PROVENANCE=PASS")
    print("STRUCTURAL_ADDITIVE_PREFLIGHT=PASS")
    print("CERTIFICATION_CLAIMED=FALSE")

if __name__=="__main__":
    main()
