"""V9 CRFU commands plus delegated legacy V8 CLI in the same interpreter."""
import argparse,json,sys
from pathlib import Path
from . import __version__,ARTIFACT_ID
from .crfu.evidence import verify_journal
from .crfu.selftest import run_selftest
def emit(obj):print(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2))
def crfu(argv:list[str])->int:
 p=argparse.ArgumentParser(prog="CUSTOSZV9.pyz crfu");sub=p.add_subparsers(dest="command",required=True)
 sub.add_parser("status");sub.add_parser("selftest")
 j=sub.add_parser("journal-verify");j.add_argument("path",type=Path)
 a=p.parse_args(argv)
 if a.command=="status":
  emit({"artifact_id":ARTIFACT_ID,"version":__version__,"capability":"CRFU","gates_G01_G24":"NOT_GRANTED","PUAC_C25_C32":"LOCAL_CONTROLS_NOT_CANONICALLY_ADMITTED","formal_assurance":"SOURCE_INCLUDED_NOT_TYPECHECKED","certification":"NOT_GRANTED","active_authorized":False,"canonical_promotion":"NOT_AUTHORIZED"});return 0
 if a.command=="selftest":
  out=run_selftest();emit(out);return 0 if out["status"]=="PASS" else 1
 if a.command=="journal-verify":
  out=verify_journal(a.path);emit(out);return 0 if out["status"]=="PASS" else 1
 return 2
def main()->int:
 args=sys.argv[1:]
 if args==["--version"]:print(f"{ARTIFACT_ID} {__version__}");return 0
 if args and args[0]=="crfu":return crfu(args[1:])
 # Existing V8 commands are dispatched to the preserved V8 CLI in this interpreter.
 from custoszv8.cli import main as v8_main
 result=v8_main()
 return int(result) if isinstance(result,int) else 0
