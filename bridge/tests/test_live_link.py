"""Negative/local-socket verification for the LOUKSNA 0.3 transport."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import lrb_core as core
import elastic_automation as elastic
import live_link as live

CONTRACT = json.loads((ROOT / "CONTRACT.v0.json").read_text())


def safe_observation():
    return {"memory_bytes": {"MemTotal": 1000, "MemAvailable": 900},
            "root_fs_bytes": {"available": 1024**3}, "load": [0.01,0.01,0.01],
            "host": "FIXTURE_NOT_LIVE"}


class LiveTransportTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.state = Path(self.t.name) / "state"
        self.transport = live.Transport(self.state, CONTRACT,
                                        observer=safe_observation, sleeper=lambda _: None)

    def tearDown(self):
        self.t.cleanup()

    def test_status_is_uncertified(self):
        r = self.transport.dispatch({"op":"status"})
        self.assertEqual(r["g24"], "NOT_EXECUTED")
        self.assertFalse(r["certified"])
        self.assertEqual(r["sudo_root_shell"], "NOT_EXPOSED")

    def test_observation_has_chained_receipt(self):
        r = self.transport.dispatch({"op":"observe"})
        self.assertEqual(r["observation"]["host"], "FIXTURE_NOT_LIVE")
        self.assertEqual(r["evidence_sha256"], self.transport.ledger.verify())
        self.assertFalse(r["certified"])

    def test_unknown_remote_execution_denied(self):
        for query in ({"op":"sudo"}, {"op":"reboot"},
                      {"op":"tick_readonly", "command":"bash"},
                      {"op":"status","force":True},
                      {"op":"watch","frames":100,"interval_sec":1}):
            with self.subTest(query=query):
                if query["op"]=="watch":
                    with self.assertRaisesRegex(RuntimeError, "WATCH_RESOURCE_BUDGET"):
                        list(self.transport.watch(query))
                else:
                    with self.assertRaisesRegex(RuntimeError, "UNREGISTERED_OPERATION"):
                        self.transport.dispatch(query)

    def test_missing_or_extra_watch_fields_denied(self):
        for query in ({"op":"watch","frames":1},
                      {"op":"watch","frames":1,"interval_sec":1,"sudo":"bash"}):
            with self.assertRaisesRegex(RuntimeError,"INVALID_WATCH"):
                list(self.transport.watch(query))

    def test_bound_watch_chain_and_backpressure(self):
        events = list(self.transport.watch({"op":"watch","frames":2,"interval_sec":1}))
        self.assertEqual(len(events),2)
        self.assertEqual([x["frame"] for x in events],[1,2])
        self.assertNotEqual(events[0]["evidence_hash"],events[1]["evidence_hash"])
        self.assertEqual(events[-1]["evidence_hash"],self.transport.ledger.verify())

    def test_watch_budget_invalid_zero(self):
        with self.assertRaisesRegex(RuntimeError, "WATCH_RESOURCE_BUDGET"):
            list(self.transport.watch({"op":"watch","frames":0,"interval_sec":0}))

    def test_report_validates_id(self):
        with self.assertRaisesRegex(RuntimeError, "MISSION_ID_INVALID"):
            self.transport.dispatch({"op":"report","mission_id":"../privileged"})

    def test_root_socket_symlink_denied(self):
        p = self.state / "BRIDGE.sock"
        p.symlink_to("/tmp/forbidden")
        with self.assertRaisesRegex(RuntimeError, "SOCKET_SYMLINK_DENIED"):
            live.guarded_socket_path(self.state)

    def test_socket_regular_file_not_removed(self):
        p = self.state / "BRIDGE.sock"
        p.write_text("do not delete")
        with self.assertRaisesRegex(RuntimeError, "FOREIGN_OR_INVALID_SOCKET"):
            live.guarded_socket_path(self.state)
        self.assertEqual(p.read_text(),"do not delete")

    def test_live_server_same_user_only_and_readonly(self):
        path = live.guarded_socket_path(self.state)
        server = live.Server(path,self.transport)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect(str(path))
                s.sendall(b'{"op":"status"}\n')
                with s.makefile("rb") as f:
                    response=json.loads(f.readline())
            self.assertEqual(response["local_transport"],"CONNECTED_SAME_UID")
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect(str(path))
                s.sendall(b'{"op":"sudo"}\n')
                with s.makefile("rb") as f:
                    response=json.loads(f.readline())
            self.assertEqual(response["status"],"HOLD")
            self.assertFalse(response["certified"])
        finally:
            server.shutdown()
            server.server_close()

    def test_reentry_live_socket_is_held(self):
        path = live.guarded_socket_path(self.state)
        server = live.Server(path,self.transport)
        try:
            with self.assertRaisesRegex(RuntimeError,"LIVE_SERVER_ALREADY_BOUND"):
                live.guarded_socket_path(self.state)
        finally:
            server.server_close()
            path.unlink()

    def test_diagnosis_binds_real_local_authenticated_channel(self):
        from datetime import datetime,timedelta,timezone
        request={"mission_id":"diagnose","user_objective":"Observe exact host only",
                 "model_proposal":"Observe host without root",
                 "model":{"declared_name":"TEST","declared_version":"1"},
                 "deadline_utc":(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat(),
                 "max_auto_steps":1,"steps":[{"kind":"OBSERVE_LOCAL"}]}
        self.transport.automation.admit(request)
        result=self.transport.dispatch({"op":"diagnose","mission_id":"diagnose"})
        self.assertEqual(result["status"],"READY_REGISTERED_READONLY_STEP")
        self.assertEqual(result["owner_goal_exact"],"Observe exact host only")
        self.assertFalse(result["privileged_execution_allowed"])
        self.assertEqual(len(result["review_passes"]),3)

    def test_model_drift_is_rejected_before_structural_review(self):
        from datetime import datetime,timedelta,timezone
        request={"mission_id":"model-001","user_objective":"Preserve owner exact wording",
                 "model_proposal":"Observe only",
                 "model":{"declared_name":"TEST","declared_version":"1"},
                 "deadline_utc":(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat(),
                 "max_auto_steps":1,"steps":[{"kind":"OBSERVE_LOCAL"}]}
        self.transport.automation.admit(request)
        with self.assertRaisesRegex(RuntimeError,"MODEL_OWNER_SCOPE_DRIFT"):
            self.transport.dispatch({"op":"review_model","mission_id":"model-001",
                  "envelope":{"user_objective":"LLM invented a different objective"},
                  "evidence_index":{"observations":{}}})

    def test_gate_preflight_does_not_grant_on_missing_checkpoint(self):
        from datetime import datetime,timedelta,timezone
        req={"mission_id":"safe-first","user_objective":"Only observation now",
             "model_proposal":"No privilege",
             "model":{"declared_name":"TEST","declared_version":"1"},
             "deadline_utc":(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat(),
             "max_auto_steps":1,"steps":[{"kind":"OBSERVE_LOCAL"}]}
        self.transport.automation.admit(req)
        with self.assertRaisesRegex(RuntimeError,"GATED_MISSION_CHECKPOINT_REQUIRED"):
            self.transport.dispatch({"op":"gate_preflight","mission_id":"safe-first",
                 "request_path":"/nonexistent","owner_signature":"/nonexistent",
                 "receipts":{},"strong":True})

    def test_weakened_external_gate_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"STRONG_EXTERNAL_GATES_REQUIRED"):
            self.transport.dispatch({"op":"gate_preflight","mission_id":"no-mission",
                 "request_path":"x","owner_signature":"x","receipts":{},"strong":False})

    def test_failed_gate_cannot_run_via_socket(self):
        from datetime import datetime, timedelta, timezone
        mission={"mission_id":"host-report","user_objective":"Only an approval-gated task",
                 "model_proposal":"Request G23 and G24, do not execute",
                 "model":{"declared_name":"FIXTURE","declared_version":"TEST"},
                 "max_auto_steps":1,
                 "deadline_utc":(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat(),
                 "steps":[{"kind":"GATED_OPERATION","requested_capability":"CAP_SUDO_BASH"}]}
        self.transport.automation.admit(mission)
        result=self.transport.dispatch({"op":"tick_readonly"})["result"]
        self.assertEqual(result["status"],"WAITING_FRESH_G23_G24")
        self.assertEqual(result["executed_steps"],0)
        self.assertFalse(result["certified"])


if __name__ == "__main__":
    unittest.main()
