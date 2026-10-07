"""Contract tests for strictly read-only existing privilege-bridge inspection."""
import json
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import apc_inventory as inventory


def manifest():
    return {"schema":"LOUKSNA_PRIVILEGE_BRIDGE_SYNC/1.0",
            "version":"1.2.1","host":"LOUKSNA","status":"PASS_STRICT",
            "runuser":{"sha256":"a"*64},
            "bridge":{"version":"1.2.1",
                      "g23_path":"/fixed/g23.json","g23_sha256":"b"*64,
                      "g24_path":"/fixed/g24.json","g24_sha256":"c"*64}}


class FakeAPC:
    def is_symlink(self):return False
    def is_file(self):return True
    def stat(self):return SimpleNamespace(st_uid=0,st_mode=stat.S_IFREG|0o755)


class ProbeTests(unittest.TestCase):
    def test_exact_root_readonly_hash_argv_only(self):
        wanted=Path("/fixed/g23.json")
        seen=[]
        def invoke(args, **kw):
            seen.append(args)
            return subprocess.CompletedProcess(args,0,stdout=("b"*64+"  /fixed/g23.json\n").encode(),stderr=b"")
        self.assertEqual(inventory.privileged_readonly_sha(wanted,invoke),"b"*64)
        self.assertEqual(seen,[["sudo","-n","/usr/bin/sha256sum",str(wanted)]])

    def test_unbound_hash_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"UNBOUND"):
            inventory.parse_hash_output(("b"*64+"  /other/path\n").encode(),Path("/fixed/g23.json"))

    def test_ambiguous_output_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"AMBIGUOUS"):
            inventory.parse_hash_output(b"123\n456\n",Path("/fixed/g23.json"))

    def fake_invoke(self,args,**kw):
        if args == ["sudo","-n","true"]:
            return subprocess.CompletedProcess(args,0,stdout=b"",stderr=b"")
        if args[:3]==["sudo","-n","/usr/bin/sha256sum"]:
            if args[-1]=="/fixed/g23.json":
                return subprocess.CompletedProcess(args,0,stdout=("b"*64+"  /fixed/g23.json\n").encode(),stderr=b"")
            if args[-1]=="/fixed/g24.json":
                return subprocess.CompletedProcess(args,0,stdout=("c"*64+"  /fixed/g24.json\n").encode(),stderr=b"")
        raise AssertionError("Unexpected root command: "+repr(args))

    def run_collect(self,actual=None,invoke=None):
        values=actual or manifest()
        def fake_sha(path,*args,**kwargs):
            return "a"*64 if str(path)=="/fake/runuser" else "d"*64
        with mock.patch.object(inventory.os,"uname",return_value=SimpleNamespace(nodename="LOUKSNA")), \
             mock.patch.object(inventory.os,"geteuid",return_value=1000), \
             mock.patch.object(inventory,"sha",side_effect=fake_sha):
            return inventory.collect(values,host="LOUKSNA",invoke=invoke or self.fake_invoke,
                                     apc=FakeAPC(),runuser=Path("/fake/runuser"))

    def test_valid_historical_proofs_do_not_create_new_gate(self):
        result=self.run_collect()
        self.assertIn("NOT_LRB_CERTIFIED",result["status"])
        self.assertFalse(result["root_mutation_authorized"])
        self.assertEqual(result["g24_current_lrb"],"NOT_EXECUTED")
        self.assertEqual(result["sudo_policy_full_sha256"],"NOT_LIVE_VERIFIED")

    def test_disallowed_hash_command_holds(self):
        def deny(args,**kwargs):
            if args==["sudo","-n","true"]:
                return subprocess.CompletedProcess(args,0,stdout=b"",stderr=b"")
            return subprocess.CompletedProcess(args,1,stdout=b"",stderr=b"denied")
        with self.assertRaisesRegex(RuntimeError,"SUDO_FIXED_SHA256_NOT_ALLOWED"):
            self.run_collect(invoke=deny)

    def test_historical_g24_mismatch_holds(self):
        bad=manifest()
        bad["bridge"]["g24_sha256"]="f"*64
        with self.assertRaisesRegex(RuntimeError,"CERTIFICATE_HASH_CHANGED"):
            self.run_collect(actual=bad)

    def test_bad_historical_schema_holds(self):
        bad=manifest()
        bad["bridge"]["version"]="100"
        with self.assertRaisesRegex(RuntimeError,"HISTORIC_PRIVILEGE_RECORD_INVALID"):
            self.run_collect(actual=bad)

    def test_root_owned_apc_required(self):
        fake=FakeAPC()
        fake.stat=lambda:SimpleNamespace(st_uid=1000,st_mode=stat.S_IFREG|0o755)
        with mock.patch.object(inventory.os,"uname",return_value=SimpleNamespace(nodename="LOUKSNA")), \
             mock.patch.object(inventory.os,"geteuid",return_value=1000), \
             mock.patch.object(inventory,"sha",return_value="a"*64):
            with self.assertRaisesRegex(RuntimeError,"APC_OWNERSHIP_OR_MODE_UNSAFE"):
                inventory.collect(manifest(),apc=fake,runuser=Path("/fake/runuser"),invoke=self.fake_invoke)


if __name__=="__main__":
    unittest.main()
