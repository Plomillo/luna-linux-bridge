#!/usr/bin/env bash
set -Eeuo pipefail

BASE_REF="audit/r4-part4-part9-second-order-20261001"
MAIN_REF="main"
OFFICIAL_IMAGE="progressofficial/marklogic-db:latest-12"
EVIDENCE_DIR="evidence/knowledge-operator-marklogic12"
MISSION_DIR="mission-control/knowledge-operator-marklogic12-10m"

fail() {
  echo "MISSION_STATE=HOLD"
  echo "BLOCKER=$1"
  exit "${2:-1}"
}

echo "MISSION=KNOWLEDGE_OPERATOR_MARKLOGIC12_THREE_POINT"
echo "HARD_CEILING_SECONDS=600"
echo "AUTHORITY=Louksna.md"
echo "ASSURANCE=PUAC2.md"
echo "DOCTRINE=EXTEND_DO_NOT_REPLACE"
echo "FAILURE_POSTURE=FAIL_CLOSED"

git fetch origin "$BASE_REF" "$MAIN_REF"

# ---------------------------------------------------------------------------
# POINT 1 — compatible additive skeleton; existing Shared Reasoner/Qwen reused.
# ---------------------------------------------------------------------------
test -f Louksna.md || fail "LOUKSNA_MISSING"
test -f PUAC2.md || fail "PUAC2_MISSING"
test -f bridge/reasoning/MODEL_MANIFEST.json || fail "REASONING_MANIFEST_MISSING"
test -f bridge/reasoning/interface.py || fail "REASONING_INTERFACE_MISSING"
test -f bridge/reasoning/bridge_adapter.py || fail "REASONING_ADAPTER_MISSING"
test -f mission-control/r4-part4-dedup-policy/DETERMINISTIC_POLICY_20260929.md || fail "DEDUP_POLICY_MISSING"

BASE_REASONING_TREE="$(git rev-parse "origin/$BASE_REF:bridge/reasoning")"
CURRENT_REASONING_TREE="$(git rev-parse "HEAD:bridge/reasoning")"
test "$BASE_REASONING_TREE" = "$CURRENT_REASONING_TREE" || fail "PREEXISTING_REASONING_DRIFT"

python3 - <<'PY'
import json
m=json.load(open("bridge/reasoning/MODEL_MANIFEST.json",encoding="utf-8"))
assert m["interface"]=="REASONING_INTERFACE/1.0"
assert m["replaceable"] is True
assert m["model"]["provider_id"]=="QWEN35_4B_S"
for k in ("canonical_authority","execution_authority","gate_authority","root_authority","self_certification"):
    assert m[k] is False
print("SHARED_REASONER_EXISTING_CONTRACT=PASS")
PY

mkdir -p bridge/knowledge bridge/cooperation "$EVIDENCE_DIR"

if [ ! -e bridge/knowledge/KNOWLEDGE_MANIFEST.json ]; then
cat > bridge/knowledge/KNOWLEDGE_MANIFEST.json <<'EOF'
{
  "schema": "LOUKSNA_KNOWLEDGE_PROVIDER_MANIFEST/1.0",
  "status": "SKELETON_MATERIALIZED_PROVIDER_PENDING",
  "authority": "Louksna.md",
  "role": "KNOWLEDGE_OPERATOR",
  "interface": "KNOWLEDGE_INTERFACE/1.0",
  "compatible_consumer_interface": "REASONING_INTERFACE/1.0",
  "provider": {
    "provider_id": "MARKLOGIC_12",
    "provider_class": "SWAPPABLE_KNOWLEDGE_PROVIDER",
    "replaceable": true,
    "material_binding": null
  },
  "canonical_authority": false,
  "execution_authority": false,
  "gate_authority": false,
  "root_authority": false,
  "self_certification": false,
  "new_engine_identity_created": false,
  "existing_capability_bindings": {
    "E05": "PROVIDES_BACKEND_FOR_VECTOR_SEARCH",
    "E06": "PROVIDES_BACKEND_FOR_KNOWLEDGE_GRAPH",
    "E07": "PROVIDES_BACKEND_FOR_RDF",
    "E14": "INTEGRATES_WITH_PROVENANCE"
  },
  "activation": false
}
EOF
fi

if [ ! -e bridge/knowledge/interface.py ]; then
cat > bridge/knowledge/interface.py <<'PY'
#!/usr/bin/env python3
import hashlib
import json

REQUEST_SCHEMA = "LOUKSNA_KNOWLEDGE_REQUEST/1.0"
RESULT_SCHEMA = "LOUKSNA_KNOWLEDGE_RESULT/1.0"
FALSE_AUTHORITY = {
    "canonical": False,
    "execution": False,
    "root": False,
    "gate": False,
    "certification": False,
}

def canonical_digest(obj):
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def validate_result(obj):
    if not isinstance(obj,dict) or obj.get("schema") != RESULT_SCHEMA:
        raise ValueError("RESULT_SCHEMA_INVALID")
    if obj.get("authority") != FALSE_AUTHORITY:
        raise ValueError("AUTHORITY_DRIFT")
    if obj.get("execution_allowed") is not False:
        raise ValueError("EXECUTION_AUTHORITY_DRIFT")
    return obj
PY
fi

if [ ! -e bridge/knowledge/marklogic_provider.py ]; then
cat > bridge/knowledge/marklogic_provider.py <<'PY'
#!/usr/bin/env python3

def bind_material(image_ref, repo_digest, image_id, main_commit):
    if not image_ref.startswith("progressofficial/marklogic-db:"):
        raise ValueError("UNAPPROVED_PROVIDER")
    if "@sha256:" not in repo_digest:
        raise ValueError("UNPINNED_DIGEST")
    return {
        "provider_id": "MARKLOGIC_12",
        "provider_class": "SWAPPABLE_KNOWLEDGE_PROVIDER",
        "image_ref": image_ref,
        "repo_digest": repo_digest,
        "image_id": image_id,
        "acquisition_root_ref": "main",
        "main_commit": main_commit,
        "canonical_authority": False,
        "execution_authority": False,
        "certification_authority": False,
        "activation": False,
    }
PY
fi

if [ ! -e bridge/cooperation/contract.py ]; then
cat > bridge/cooperation/contract.py <<'PY'
#!/usr/bin/env python3

COOPERATION_SCHEMA = "LOUKSNA_KNOWLEDGE_REASONING_COOPERATION/1.0"

def bind(reasoning_request, knowledge_binding):
    if reasoning_request.get("schema") != "LOUKSNA_REASONING_REQUEST/1.0":
        raise ValueError("REASONING_REQUEST_SCHEMA_INVALID")
    if knowledge_binding.get("interface") != "KNOWLEDGE_INTERFACE/1.0":
        raise ValueError("KNOWLEDGE_INTERFACE_INVALID")
    out=dict(reasoning_request)
    context=dict(out.get("context") or {})
    if "knowledge_binding" in context:
        raise ValueError("DUPLICATE_KNOWLEDGE_BINDING")
    context["knowledge_binding"]=dict(knowledge_binding)
    out["context"]=context
    return out
PY
fi

if [ ! -e bridge/cooperation/coordinator.py ]; then
cat > bridge/cooperation/coordinator.py <<'PY'
#!/usr/bin/env python3

def plan(operation_id):
    if not operation_id:
        raise ValueError("OPERATION_ID_REQUIRED")
    return {
        "operation_id": operation_id,
        "knowledge_interface": "KNOWLEDGE_INTERFACE/1.0",
        "reasoning_interface": "REASONING_INTERFACE/1.0",
        "provider_to_provider_hard_binding": False,
        "execution_allowed": False,
    }
PY
fi

python3 -m py_compile bridge/knowledge/*.py bridge/cooperation/*.py
git diff --exit-code "origin/$BASE_REF" -- bridge/reasoning
test -z "$(git diff --diff-filter=D --name-only "origin/$BASE_REF")" || fail "DELETION_DETECTED"
if grep -RniE 'marklogic|qwen' bridge/cooperation; then
  fail "PROVIDER_HARD_BINDING_DETECTED"
fi

python3 - <<'PY'
import json
m=json.load(open("bridge/knowledge/KNOWLEDGE_MANIFEST.json",encoding="utf-8"))
assert m["role"]=="KNOWLEDGE_OPERATOR"
assert m["interface"]=="KNOWLEDGE_INTERFACE/1.0"
assert m["compatible_consumer_interface"]=="REASONING_INTERFACE/1.0"
assert m["provider"]["provider_class"]=="SWAPPABLE_KNOWLEDGE_PROVIDER"
assert m["provider"]["replaceable"] is True
assert m["new_engine_identity_created"] is False
assert m["activation"] is False
for k in ("canonical_authority","execution_authority","gate_authority","root_authority","self_certification"):
    assert m[k] is False
print("POINT1_COMPATIBLE_SKELETON=PASS")
PY

python3 - <<'PY'
import json, hashlib
from pathlib import Path
paths=[
 "bridge/knowledge/KNOWLEDGE_MANIFEST.json",
 "bridge/knowledge/interface.py",
 "bridge/knowledge/marklogic_provider.py",
 "bridge/cooperation/contract.py",
 "bridge/cooperation/coordinator.py",
]
obj={
 "schema":"LOUKSNA_KNOWLEDGE_OPERATOR_PHASE1/1.0",
 "status":"PASS",
 "authority":"Louksna.md",
 "assurance":"PUAC2.md",
 "existing_shared_reasoner_reused":True,
 "qwen_redownload":False,
 "existing_reasoning_mutation":False,
 "duplicate_engine_identity":False,
 "files":{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
}
Path("evidence/knowledge-operator-marklogic12/PHASE1.json").write_text(
 json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add bridge/knowledge bridge/cooperation "$EVIDENCE_DIR/PHASE1.json"
if ! git diff --cached --quiet; then
  git commit -m "feat(knowledge): materialize compatible Knowledge Operator skeleton"
  git push origin "HEAD:$GITHUB_REF_NAME"
fi

# ---------------------------------------------------------------------------
# POINT 2 — acquire MarkLogic 12 using main as read-only recovery root.
# ---------------------------------------------------------------------------
MAIN_ROOT="$RUNNER_TEMP/main-root"
git worktree add --detach "$MAIN_ROOT" origin/main
python3 "$MAIN_ROOT/recovery/recovery.py" selftest
python3 "$MAIN_ROOT/recovery/recovery.py" checkpoint --root "$RUNNER_TEMP/main-checkpoint"
test -z "$(git -C "$MAIN_ROOT" status --porcelain)" || fail "MAIN_MUTATION_PRE_DOWNLOAD"

docker manifest inspect "$OFFICIAL_IMAGE" >/dev/null || fail "OFFICIAL_MARKLOGIC12_IMAGE_NOT_RESOLVABLE"
timeout 240s docker pull "$OFFICIAL_IMAGE" || fail "MARKLOGIC12_DOWNLOAD_FAILED_OR_TIMED_OUT"

REPO_DIGEST="$(docker image inspect "$OFFICIAL_IMAGE" --format '{{index .RepoDigests 0}}')"
IMAGE_ID="$(docker image inspect "$OFFICIAL_IMAGE" --format '{{.Id}}')"
case "$REPO_DIGEST" in
  *@sha256:*) ;;
  *) fail "MARKLOGIC12_DIGEST_NOT_PINNED" ;;
esac
MAIN_COMMIT="$(git rev-parse origin/main)"

export OFFICIAL_IMAGE REPO_DIGEST IMAGE_ID MAIN_COMMIT
python3 - <<'PY'
import json, os
from pathlib import Path
p=Path("bridge/knowledge/KNOWLEDGE_MANIFEST.json")
m=json.loads(p.read_text(encoding="utf-8"))
m["status"]="PROVIDER_MATERIAL_ACQUIRED_NOT_ACTIVE"
m["provider"]["material_binding"]={
 "source":"OFFICIAL_PROGRESS_MARKLOGIC_DOCKER_IMAGE",
 "source_repository":"progressofficial/marklogic-db",
 "image_ref":os.environ["OFFICIAL_IMAGE"],
 "repo_digest":os.environ["REPO_DIGEST"],
 "image_id":os.environ["IMAGE_ID"],
 "acquisition_root_ref":"main",
 "main_commit":os.environ["MAIN_COMMIT"],
 "downloaded":True,
 "license_activation_performed":False,
 "server_configuration_performed":False
}
m["activation"]=False
p.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
Path("evidence/knowledge-operator-marklogic12/PHASE2.json").write_text(
 json.dumps({
  "schema":"LOUKSNA_MARKLOGIC12_ACQUISITION/1.0",
  "status":"PASS",
  "authority":"Louksna.md",
  "assurance":"PUAC2.md",
  "acquisition_root_ref":"main",
  "main_commit":os.environ["MAIN_COMMIT"],
  "official_image":os.environ["OFFICIAL_IMAGE"],
  "repo_digest":os.environ["REPO_DIGEST"],
  "image_id":os.environ["IMAGE_ID"],
  "main_mutation":False,
  "qwen_redownload":False,
  "activation":False
 },indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY

test -z "$(git -C "$MAIN_ROOT" status --porcelain)" || fail "MAIN_MUTATION_POST_DOWNLOAD"
git diff --exit-code "origin/$BASE_REF" -- bridge/reasoning
git add bridge/knowledge/KNOWLEDGE_MANIFEST.json "$EVIDENCE_DIR/PHASE2.json"
if ! git diff --cached --quiet; then
  git commit -m "build(knowledge): bind official MarkLogic12 digest via main recovery root"
  git push origin "HEAD:$GITHUB_REF_NAME"
fi

echo "POINT2_MARKLOGIC12_MAIN_ACQUISITION=PASS"

# ---------------------------------------------------------------------------
# POINT 3 — freeze, validate in detached no-write view, certify bounded scope.
# ---------------------------------------------------------------------------
CANDIDATE_SHA="$(git rev-parse HEAD)"
G23_ROOT="$RUNNER_TEMP/g23-readonly"
git worktree add --detach "$G23_ROOT" "$CANDIDATE_SHA"

(
  cd "$G23_ROOT"
  git diff --exit-code "origin/$BASE_REF" -- bridge/reasoning
  test -z "$(git diff --diff-filter=D --name-only "origin/$BASE_REF")"
  python3 -m py_compile bridge/knowledge/*.py bridge/cooperation/*.py
  python3 - <<'PY'
import json
m=json.load(open("bridge/knowledge/KNOWLEDGE_MANIFEST.json",encoding="utf-8"))
assert m["status"]=="PROVIDER_MATERIAL_ACQUIRED_NOT_ACTIVE"
assert m["activation"] is False
assert m["provider"]["replaceable"] is True
assert m["new_engine_identity_created"] is False
b=m["provider"]["material_binding"]
assert b["acquisition_root_ref"]=="main"
assert b["downloaded"] is True
assert b["license_activation_performed"] is False
assert "@sha256:" in b["repo_digest"]
for k in ("canonical_authority","execution_authority","gate_authority","root_authority","self_certification"):
    assert m[k] is False
print("G23_BOUNDED_VALIDATION=PASS")
PY
)

python3 - <<PY
import json
from pathlib import Path
obj={
 "schema":"LOUKSNA_KNOWLEDGE_MARKLOGIC12_G23_G24/1.0",
 "candidate_sha":"$CANDIDATE_SHA",
 "g23":{
   "status":"PASS",
   "method":"DETACHED_WORKTREE_READ_ONLY_VALIDATION_PROCESS",
   "external_actor_independence":False,
   "candidate_mutation":False
 },
 "g24":{
   "status":"PASS",
   "certified_scope":"KNOWLEDGE_OPERATOR_SKELETON+MARKLOGIC12_ACQUISITION_BINDING+SHARED_REASONER_COOPERATION",
   "same_frozen_candidate_sha":True,
   "certification_propagation":False
 },
 "active":False,
 "runtime_marklogic_query_certified":False,
 "authority":"Louksna.md",
 "assurance":"PUAC2.md"
}
Path("evidence/knowledge-operator-marklogic12/FINAL_SCOPE_CERTIFICATION.json").write_text(
 json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY

git add "$EVIDENCE_DIR/FINAL_SCOPE_CERTIFICATION.json"
git commit -m "cert(knowledge): record bounded frozen-scope validation"
git push origin "HEAD:$GITHUB_REF_NAME"

echo "POINT3_FROZEN_SCOPE_CERTIFICATION=PASS"
echo "ACTIVE=FALSE"
echo "CERTIFICATION_PROPAGATION=FALSE"
echo "MISSION_STATE=COMPLETE"
