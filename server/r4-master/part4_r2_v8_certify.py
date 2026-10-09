#!/usr/bin/env python3
"""Issue a stage-specific V8 scope certificate from a successful independent G23."""
import argparse,base64,datetime as dt,hashlib,json,os,pathlib,urllib.parse,urllib.request

REPO="Plomillo/luna-linux-bridge"
BRANCH="refs/heads/staging/luna-r4-master-part1-part9-20260929"

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--stage",choices=("CLEANUP","MIGRATION"),required=True)
 ap.add_argument("--g23",type=pathlib.Path,required=True)
 ap.add_argument("--out",type=pathlib.Path,required=True)
 a=ap.parse_args()
 g=json.loads(a.g23.read_text(encoding="utf-8"))
 assert g["status"]=="PASS" and g["g24_allowed"] is True and all(g["checks"].values())
 if a.stage=="CLEANUP":
  assert g["stage"]=="PRECLEAN"
  p=g["plan_sha256"]; s=g["cleanup_script_sha256"]; extra=""
  scope="TEMP_EXT4_PROYECTOS_PARTIAL_ONLY"
 else:
  assert g["stage"]=="POSTCLEAN_MIGRATION_AUTHORIZATION"
  p=g["migration_plan_sha256"]; s=g["migration_script_sha256"]; extra=g["cleanup_report_sha256"]
  scope="P3_EXT4_ONLY_AFTER_TEMP_CONTENT_POSIX_VERIFIED"
 gh=hashlib.sha256(a.g23.read_bytes()).hexdigest()
 aud=f"louksna-r4-part4-r2-v8-{a.stage.lower()}:{p}:{s}:{extra}:{gh}"
 base=os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
 token=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
 req=urllib.request.Request(base+"&audience="+urllib.parse.quote(aud,safe=""),
   headers={"Authorization":"bearer "+token})
 with urllib.request.urlopen(req,timeout=30) as res: raw=json.load(res)["value"]
 parts=raw.split(".")
 assert len(parts)==3
 enc=parts[1]+"="*((4-len(parts[1])%4)%4)
 claims=json.loads(base64.urlsafe_b64decode(enc))
 audience=claims.get("aud")
 assert audience==aud or (isinstance(audience,list) and aud in audience)
 assert claims.get("iss")=="https://token.actions.githubusercontent.com"
 assert claims.get("repository")==REPO
 assert claims.get("ref")==BRANCH
 assert claims.get("sha")==os.environ["GITHUB_SHA"]
 assert claims.get("exp",0)>dt.datetime.now(dt.timezone.utc).timestamp()
 cert={"schema":"LOUKSNA_R4_PART4_R2_V8_G24/1.0","status":"PASS",
  "stage":a.stage,"scope":scope,"plan_sha256":p,"script_sha256":s,
  "g23_sha256":gh,"authority_authenticated":True,
  "authority_reference":"GITHUB_OIDC_JWT_SHA256:"+hashlib.sha256(raw.encode()).hexdigest(),
  "p3_mutation_authorized":False if a.stage=="CLEANUP" else "CONDITIONAL_AFTER_VERIFIED_TEMP",
  "p3_reformat_authorized_only_after_verified_temp_content_and_posix_equivalence":a.stage=="MIGRATION",
  "p2_p4_retirement_authorized":False,"raw_ntfs_wsl_xattr_transport_authorized":False,
  "canonical_mutation":False,"authority_transfer":False,
  "certified_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
 if a.stage=="MIGRATION": cert["cleanup_report_sha256"]=extra
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(cert,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({k:v for k,v in cert.items() if k!="authority_reference"},sort_keys=True))
if __name__=="__main__":
 main()
