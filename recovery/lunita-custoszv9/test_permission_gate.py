import importlib.util
import json
import pathlib
import tempfile
import unittest

HERE=pathlib.Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("permission_gate", HERE/"permission_gate.py")
GATE=importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(GATE)

def candidate(root, cid=GATE.CID):
    c=root/cid; c.mkdir()
    data={
      "state.json":{"schema":GATE.SCHEMAS["state.json"],"candidate_id":cid,"phase":"WAITING_FOR_RUNTIME_REBUILD_INPUTS"},
      "BUILD_PLAN.json":{"schema":GATE.SCHEMAS["BUILD_PLAN.json"],"candidate_id":cid,"never_do":["REWRITE_FROZEN_G08_BINDINGS","PROMOTE_WITHOUT_INDEPENDENT_VALIDATION"]},
      "BASE_REBUILD_RECEIPT.json":{"schema":GATE.SCHEMAS["BASE_REBUILD_RECEIPT.json"],"candidate_id":cid,"certification":"NOT_GRANTED"},
    }
    for name,obj in data.items():
        (c/name).write_text(json.dumps(obj),encoding="utf-8")
    return c

class GateTests(unittest.TestCase):
    def test_correct_identity(self):
        with tempfile.TemporaryDirectory() as td:
            c=candidate(pathlib.Path(td))
            self.assertEqual(GATE.inspect(c,"root")["candidate_id"],GATE.CID)

    def test_identity_mismatch_is_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            c=candidate(pathlib.Path(td),"G06_WRONG")
            with self.assertRaisesRegex(GATE.GateError,"IDENTITY_MISMATCH"):
                GATE.inspect(c,"root")

    def test_missing_plan_is_not_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            c=candidate(pathlib.Path(td)); (c/"BUILD_PLAN.json").unlink()
            with self.assertRaisesRegex(GATE.GateError,"FILE_MISSING:BUILD_PLAN.json"):
                GATE.inspect(c,"root")

    def test_invalid_json_is_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            c=candidate(pathlib.Path(td)); (c/"BUILD_PLAN.json").write_text("{broken")
            with self.assertRaisesRegex(GATE.GateError,"INVALID_JSON_OR_IO:BUILD_PLAN.json"):
                GATE.inspect(c,"root")

    def test_audit_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            c=candidate(pathlib.Path(td))
            before={n:GATE.digest(c/n) for n in GATE.SCHEMAS}
            GATE.inspect(c,"root")
            self.assertEqual(before,{n:GATE.digest(c/n) for n in GATE.SCHEMAS})

if __name__=="__main__": unittest.main(verbosity=2)
