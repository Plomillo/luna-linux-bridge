from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "cajita-luna-runtime"
sys.path.insert(0, str(RUNTIME))

import cajita_remote_execution as remote


def _signature(key: bytes, payload: dict) -> str:
    return hmac.new(key, remote.canonical_json(payload), hashlib.sha256).hexdigest()


class RemoteProtocolFixture(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def _reply(self, status, data):
        raw = remote.canonical_json(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path != "/v1/identity":
            self._reply(404, {"status": "FAIL_CLOSED"})
            return
        state = self.server.state
        identity = state["identity"]
        if state.get("identity_tamper"):
            identity = dict(identity)
            identity["source_revision"] = "0" * 40
        envelope = {
            "schema": remote.SIGNED_IDENTITY_SCHEMA,
            "key_id": state["key_id"],
            "identity": identity,
            "issued_at_utc": remote.utc_now(),
        }
        envelope["signature"] = _signature(state["key"], envelope)
        self._reply(200, envelope)

    def do_POST(self):
        state = self.server.state
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request = json.loads(raw.decode("utf-8"))
        state["post_count"] += 1
        valid_sig = hmac.compare_digest(
            self.headers.get("X-Louksnapg-Request-Signature", ""),
            hmac.new(state["key"], raw, hashlib.sha256).hexdigest(),
        )
        if not valid_sig or remote.canonical_json(request) != raw:
            self._reply(401, {"status": "FAIL_CLOSED"})
            return
        response = {
            "schema": remote.RESPONSE_SCHEMA,
            "request_id": request["request_id"],
            "request_sha256": remote.sha256_bytes(remote.canonical_json(request)),
            "identity_sha256": request["identity_sha256"],
            "domain_id": request["domain_id"],
            "model_id": request["model_id"],
            "source_revision": request["source_revision"],
            "status": "PASS_REMOTE_EXECUTION",
            "output_text": "The result is four.",
            "generated_token_count": 5,
            "issued_at_utc": remote.utc_now(),
        }
        response["signature"] = _signature(state["key"], response)
        if state.get("response_tamper"):
            response["output_text"] = "tampered after signature"
        self._reply(200, response)


class RemoteExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        policy = json.loads((RUNTIME / "CAJITA_REMOTE_MODEL_POLICY.json").read_text(encoding="utf-8"))
        (self.root / "CAJITA_REMOTE_MODEL_POLICY.json").write_text(
            json.dumps(policy, ensure_ascii=False), encoding="utf-8"
        )
        self.policy = policy
        self.spec = policy["domains"]["D01_CEREBRO"]
        self.key = bytes.fromhex("ab" * 32)
        self.old_env = {
            name: os.environ.get(name)
            for name in (self.spec["url_env"], self.spec["key_env"])
        }
        os.environ[self.spec["key_env"]] = self.key.hex()
        rows = []
        for row in self.spec["weight_files"]:
            sha = row.get("sha256") or hashlib.sha256(("fixture:" + row["path"]).encode()).hexdigest()
            rows.append({"path": row["path"], "bytes": row["bytes"], "sha256": sha})
        rows.sort(key=lambda row: row["path"].encode("utf-8"))
        self.identity = {
            "schema": remote.IDENTITY_SCHEMA,
            "domain_id": "D01_CEREBRO",
            "model_id": self.spec["model_id"],
            "source_repo": self.spec["source_repo"],
            "source_revision": self.spec["source_revision"],
            "source_config_sha256": self.spec["source_config_sha256"],
            "source_index_sha256": self.spec["source_index_sha256"],
            "weight_files": rows,
            "weight_inventory_sha256": remote.sha256_bytes(remote.canonical_json(rows)),
            "model_loaded": True,
            "gateway_version": "fixture-only",
            "created_at_utc": remote.utc_now(),
        }
        self.server = HTTPServer(("127.0.0.1", 0), RemoteProtocolFixture)
        self.server.state = {
            "key": self.key, "key_id": self.spec["key_id"], "identity": self.identity,
            "post_count": 0, "identity_tamper": False, "response_tamper": False,
        }
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        os.environ[self.spec["url_env"]] = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        for name, value in self.old_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp.cleanup()

    def task(self):
        return {
            "task_id": "remote-unit-test",
            "domain_id": "D01_CEREBRO",
            "operation": "generate_text",
            "input": {"prompt": "What is two plus two?"},
            "input_files": [],
            "limits": {"max_new_tokens": 8, "timeout_seconds": 20},
        }

    def test_policy_pins_immutable_source_revisions_and_does_not_bind_ancient_to_general(self):
        policy = remote.load_policy(self.root)
        self.assertEqual(len(policy["domains"]), 4)
        for domain in policy["domains"].values():
            self.assertRegex(domain["source_revision"], r"^[0-9a-f]{40}$")
            self.assertEqual(domain["model_id"], domain["source_repo"])
        ancient = policy["unsupported_domains"]["D04_TRADUCCION_LENGUAS_ANTIGUAS"]
        self.assertFalse(ancient["allow_general_translation_fallback"])
        self.assertEqual(ancient["status"], "BLOCKED_NO_SOURCE_BOUND_TRANSLATION_RESOURCE")

    def test_verified_remote_task_returns_provenance_but_not_quality_certification(self):
        result = remote.execute_remote_task(self.task(), self.root)
        self.assertEqual(result["status"], "PASS_REMOTE_EXECUTION")
        self.assertTrue(result["execution_authorized"])
        self.assertEqual(result["output_text"], "The result is four.")
        self.assertEqual(result["remote_evidence"]["model_id"], self.spec["model_id"])
        self.assertEqual(result["remote_evidence"]["source_revision"], self.spec["source_revision"])
        self.assertEqual(result["quality_equivalence"], "NOT_ESTABLISHED")
        self.assertEqual(result["certification"], "NOT_GRANTED")
        self.assertEqual(self.server.state["post_count"], 1)

    def test_signed_but_wrong_source_revision_is_rejected_before_execution(self):
        self.server.state["identity_tamper"] = True
        result = remote.execute_remote_task(self.task(), self.root)
        self.assertEqual(result["status"], "FAIL_REMOTE_EXECUTION")
        self.assertFalse(result["execution_authorized"])
        self.assertIn("REMOTE_SOURCE_IDENTITY_MISMATCH:source_revision", result["reason"])
        self.assertEqual(self.server.state["post_count"], 0)

    def test_response_modified_after_signing_is_rejected(self):
        self.server.state["response_tamper"] = True
        result = remote.execute_remote_task(self.task(), self.root)
        self.assertEqual(result["status"], "FAIL_REMOTE_EXECUTION")
        self.assertIn("REMOTE_SIGNATURE_VERIFICATION_FAILED", result["reason"])

    def test_missing_endpoint_fails_closed_without_local_fallback(self):
        os.environ.pop(self.spec["url_env"], None)
        result = remote.execute_remote_task(self.task(), self.root)
        self.assertEqual(result["status"], "FAIL_REMOTE_EXECUTION")
        self.assertFalse(result["execution_authorized"])
        self.assertIn("REMOTE_ENDPOINT_NOT_CONFIGURED", result["reason"])
        self.assertEqual(self.server.state["post_count"], 0)

    def test_http_non_loopback_endpoint_is_rejected(self):
        os.environ[self.spec["url_env"]] = "http://192.0.2.1:8765"
        result = remote.execute_remote_task(self.task(), self.root)
        self.assertEqual(result["status"], "FAIL_REMOTE_EXECUTION")
        self.assertIn("REMOTE_ENDPOINT_REQUIRES_HTTPS", result["reason"])
        self.assertEqual(self.server.state["post_count"], 0)

    def test_wrong_key_cannot_validate_remote_identity(self):
        os.environ[self.spec["key_env"]] = "cd" * 32
        result = remote.execute_remote_task(self.task(), self.root)
        self.assertEqual(result["status"], "FAIL_REMOTE_EXECUTION")
        self.assertIn("REMOTE_SIGNATURE_VERIFICATION_FAILED", result["reason"])
        self.assertEqual(self.server.state["post_count"], 0)


if __name__ == "__main__":
    unittest.main()
