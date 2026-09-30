"""Virtual remote 120B brain: adversarial tests, NO real provider requests."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import virtual_brain as brain

CONFIG=json.loads((ROOT/"VIRTUAL_BRAIN.json").read_text())


class MockReply:
    status=200
    def __init__(self, response):
        self.content=json.dumps(response).encode("utf-8")
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self, n):return self.content[:n]


class VirtualBrainTests(unittest.TestCase):
    def setUp(self):
        self.calls=0
        self.captured=[]
        def transport(req,*,timeout,context):
            self.calls+=1
            self.captured.append({"url":req.full_url,"auth":req.get_header("Authorization"),
                                  "payload":json.loads(req.data),"timeout":timeout})
            return MockReply({"model":"openai/gpt-oss-120b",
                              "choices":[{"message":{"content":"Respuesta de prueba"}}]})
        self.mock=transport
        self.instance=brain.VirtualBrain(CONFIG,transport=transport,
                                         environ={"GROQ_API_KEY":"fixture-g",
                                                  "HF_TOKEN":"fixture-h"})

    def test_virtual_mode_no_download_or_default_egress(self):
        state=self.instance.availability()
        self.assertTrue(state["virtual"])
        self.assertFalse(state["local_model_weights"])
        self.assertEqual(state["default_outbound_execution"],"DENIED")
        self.assertEqual(self.calls,0)

    def test_owner_consent_required(self):
        with self.assertRaisesRegex(PermissionError,"OWNER_CONSENT"):
            self.instance.infer(provider="groq",prompt="test")
        self.assertEqual(self.calls,0)

    def test_hf_usage_cost_gate_required(self):
        with self.assertRaisesRegex(PermissionError,"CHARGES"):
            self.instance.infer(provider="huggingface",prompt="test",
                                owner_consents_to_egress=True)
        self.assertEqual(self.calls,0)

    def test_groq_response_is_only_advisory(self):
        result=self.instance.infer(provider="groq",prompt="test",
                                    owner_consents_to_egress=True)
        self.assertEqual(self.calls,1)
        self.assertEqual(result["text"],"Respuesta de prueba")
        self.assertFalse(result["authorized_host_execution"])
        self.assertFalse(result["certified"])
        self.assertEqual(result["g23"],"NOT_EXECUTED")
        self.assertEqual(self.captured[0]["url"],brain.ENDPOINTS["groq"][0])
        self.assertEqual(self.captured[0]["payload"]["model"],"openai/gpt-oss-120b")
        self.assertEqual(self.captured[0]["timeout"],20)

    def test_hf_can_use_same_virtual_model_explicitly(self):
        result=self.instance.infer(provider="huggingface",prompt="test",
                                    owner_consents_to_egress=True,
                                    acknowledges_usage_billing=True)
        self.assertEqual(result["provider"],"huggingface")
        self.assertEqual(self.captured[0]["url"],brain.ENDPOINTS["huggingface"][0])
        self.assertEqual(self.calls,1)

    def test_missing_credentials_prevent_request(self):
        instance=brain.VirtualBrain(CONFIG,transport=self.mock,environ={})
        with self.assertRaisesRegex(PermissionError,"CREDENTIAL"):
            instance.infer(provider="groq",prompt="test",owner_consents_to_egress=True)
        self.assertEqual(self.calls,0)

    def test_invalid_provider_cannot_redirect_egress(self):
        with self.assertRaisesRegex(ValueError,"NOT_REGISTERED"):
            self.instance.infer(provider="http://localhost/admin",prompt="test",
                                owner_consents_to_egress=True)
        self.assertEqual(self.calls,0)

    def test_model_endpoint_configuration_change_requires_review(self):
        alter=json.loads(json.dumps(CONFIG))
        alter["providers"]["groq"]["endpoint"]="http://127.0.0.1/root"
        with self.assertRaisesRegex(ValueError,"UNAPPROVED"):
            brain.VirtualBrain(alter)
        alter=json.loads(json.dumps(CONFIG))
        alter["providers"]["groq"]["model"]="other-model"
        with self.assertRaisesRegex(ValueError,"UNAPPROVED"):
            brain.VirtualBrain(alter)

    def test_invalid_prompt_and_output_quota_rejected(self):
        for prompt in ("", "A"*17000):
            with self.subTest(size=len(prompt)):
                with self.assertRaisesRegex(ValueError,"PROMPT"):
                    self.instance.infer(provider="groq",prompt=prompt,
                                        owner_consents_to_egress=True)
        for size in (0,1025,True):
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError,"OUTPUT"):
                    self.instance.infer(provider="groq",prompt="test",
                                        max_tokens=size,owner_consents_to_egress=True)
        self.assertEqual(self.calls,0)

    def test_provider_429_yields_hold_without_fallback(self):
        def fail(req,**kwargs):
            self.calls+=1
            raise urllib.error.HTTPError(req.full_url,429,"Too Many Requests",{},None)
        self.instance.transport=fail
        with self.assertRaisesRegex(RuntimeError,"QUOTA_HOLD"):
            self.instance.infer(provider="groq",prompt="test",
                                owner_consents_to_egress=True)
        self.assertEqual(self.calls,1)

    def test_malformed_external_reply_denied(self):
        self.instance.transport=lambda *a,**k:MockReply({"choices":[]})
        with self.assertRaisesRegex(RuntimeError,"REPLY_UNVERIFIED"):
            self.instance.infer(provider="groq",prompt="test",
                                owner_consents_to_egress=True)

    def test_status_never_contains_credentials(self):
        report=json.dumps(self.instance.availability())
        self.assertNotIn("fixture-g",report)
        self.assertNotIn("fixture-h",report)

    def test_default_config_cannot_enable_ungated_remote_calls(self):
        changed=json.loads(json.dumps(CONFIG))
        changed["remote_inference_default"]=True
        with self.assertRaisesRegex(ValueError,"AUTHORITY_DRIFT"):
            brain.VirtualBrain(changed)

    def test_transport_receives_exactly_one_explicit_request(self):
        self.instance.infer(provider="groq",prompt="owner-authorized sample",
                            owner_consents_to_egress=True)
        self.assertEqual(self.calls,1)
        self.assertEqual(self.captured[0]["payload"]["messages"],
                         [{"role":"user","content":"owner-authorized sample"}])


if __name__=="__main__":
    unittest.main()
