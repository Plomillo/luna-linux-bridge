#!/usr/bin/env python3
"""Optional virtual 120B brain: external inference behind one swappable interface.

OFF by default. An explicit owner-authorized outbound request and a provider
credential are mandatory. This is advisory text inference, NEVER an executor,
privilege broker, gate issuer or evidence authenticator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request

SCHEMA = "LRB_VIRTUAL_BRAIN/0.1"
MAX_PROMPT_BYTES = 16_384
MAX_REPLY_BYTES = 524_288
MAX_OUTPUT_TOKENS = 1024
DEFAULT_CONFIG = Path(__file__).with_name("VIRTUAL_BRAIN.json")
MODEL_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,127}$")
ENDPOINTS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "huggingface": ("https://router.huggingface.co/v1/chat/completions", "HF_TOKEN"),
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {
        "schema", "status", "authority", "remote_inference_default",
        "no_weight_download", "fallback_policy", "providers"
    }:
        raise ValueError("BRAIN_CONFIG_FIELDS_DENIED")
    if (config["schema"] != SCHEMA or config["authority"] != "Louksna.md"
            or config["status"] != "CANDIDATE_UNCERTIFIED"
            or config["remote_inference_default"] is not False
            or config["no_weight_download"] is not True
            or config["fallback_policy"] != "NO_SILENT_PROVIDER_SWITCH"):
        raise ValueError("BRAIN_CONFIG_AUTHORITY_DRIFT")
    if not isinstance(config["providers"], dict) or set(config["providers"]) != set(ENDPOINTS):
        raise ValueError("BRAIN_PROVIDERS_UNREVIEWED")
    for name, (endpoint, variable) in ENDPOINTS.items():
        row = config["providers"][name]
        if (not isinstance(row, dict) or set(row) != {
            "endpoint", "credential_env", "model", "cost_gate"
        } or row["endpoint"] != endpoint or row["credential_env"] != variable
            or not isinstance(row["model"], str)
            or not MODEL_IDENTIFIER.fullmatch(row["model"])
            or row["cost_gate"] not in ("FREE_PLAN_RATE_LIMITED",
                                      "OWNER_ACKNOWLEDGES_USAGE_BILLING")):
            raise ValueError("UNAPPROVED_PROVIDER_CONFIGURATION")
    if (config["providers"]["groq"]["cost_gate"] != "FREE_PLAN_RATE_LIMITED" or
        config["providers"]["huggingface"]["cost_gate"] !=
            "OWNER_ACKNOWLEDGES_USAGE_BILLING"):
        raise ValueError("COST_GATE_CANNOT_BE_SILENTLY_DOWNGRADED")


def read_config(path=DEFAULT_CONFIG):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("BRAIN_CONFIG_UNSAFE")
    result = json.loads(path.read_text(encoding="utf-8"))
    validate_config(result)
    return result


class VirtualBrain:
    """Provider-independent Chat Completions interface; no model weights here."""

    def __init__(self, config=None, transport=None, environ=None):
        self.config = config if config is not None else read_config()
        validate_config(self.config)
        self.transport = transport or urllib.request.urlopen
        self.environ = os.environ if environ is None else environ

    def availability(self):
        return {
            "schema": SCHEMA, "virtual": True, "local_model_weights": False,
            "inference_mode": "REMOTE_API_ONLY",
            "default_outbound_execution": "DENIED",
            "providers": {
                name: {
                    "model": self.config["providers"][name]["model"],
                    "credential_present": bool(self.environ.get(token)),
                    "verified_live_inference": False,
                    "capacity_or_free_tier_guaranteed": False,
                    "usage_billing_possible": name == "huggingface"
                } for name, (_, token) in ENDPOINTS.items()
            },
            "certified": False
        }

    def infer(self, *, provider, prompt, owner_consents_to_egress=False,
              acknowledges_usage_billing=False, max_tokens=256):
        if provider not in ENDPOINTS or type(provider) is not str:
            raise ValueError("PROVIDER_NOT_REGISTERED")
        if owner_consents_to_egress is not True:
            raise PermissionError("OUTBOUND_MODEL_TRANSFER_REQUIRES_OWNER_CONSENT")
        if (provider == "huggingface" and acknowledges_usage_billing is not True):
            raise PermissionError("POSSIBLE_USAGE_CHARGES_NOT_ACKNOWLEDGED")
        if (type(prompt) is not str or not prompt.strip() or
            len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES):
            raise ValueError("PROMPT_UNBOUNDED_OR_EMPTY")
        if type(max_tokens) is not int or not (1 <= max_tokens <= MAX_OUTPUT_TOKENS):
            raise ValueError("OUTPUT_BUDGET_INVALID")
        endpoint, envvar = ENDPOINTS[provider]
        credential = self.environ.get(envvar)
        if not credential or any(c in credential for c in "\r\n") or len(credential) > 4096:
            raise PermissionError("PROVIDER_CREDENTIAL_UNAVAILABLE")
        payload = {
            "model": self.config["providers"][provider]["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False
        }
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        request = urllib.request.Request(
            endpoint, data=encoded, method="POST",
            headers={"Authorization": "Bearer " + credential,
                     "Content-Type": "application/json",
                     "User-Agent": "Louksna-VirtualBrain/0.1"})
        try:
            with self.transport(request, timeout=20, context=ssl.create_default_context()) as reply:
                if getattr(reply, "status", 200) != 200:
                    raise RuntimeError("REMOTE_PROVIDER_NON_SUCCESS")
                raw = reply.read(MAX_REPLY_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise RuntimeError("REMOTE_PROVIDER_QUOTA_HOLD") from None
            if exc.code in (401, 403):
                raise RuntimeError("REMOTE_PROVIDER_CREDENTIAL_DENIED") from None
            raise RuntimeError("REMOTE_PROVIDER_HTTP_FAILURE") from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("REMOTE_PROVIDER_NETWORK_HOLD") from None
        if len(raw) > MAX_REPLY_BYTES:
            raise RuntimeError("REMOTE_PROVIDER_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(raw)
            response = result["choices"][0]["message"]["content"]
            if not isinstance(response, str) or not response.strip():
                raise ValueError
        except (ValueError, KeyError, TypeError, IndexError):
            raise RuntimeError("REMOTE_PROVIDER_REPLY_UNVERIFIED") from None
        return {
            "schema": SCHEMA, "provider": provider,
            "model_claimed_by_provider": result.get("model"),
            "model_requested": payload["model"],
            "text": response,
            "prompt_sha256": sha256(prompt.encode("utf-8")),
            "response_sha256": sha256(response.encode("utf-8")),
            "execution": "REMOTE_INFERENCE_RESPONSE_RECEIVED",
            "source_provenance": "SELF_REPORTED_EXTERNAL_PROVIDER",
            "authorized_host_execution": False,
            "independently_verified": False,
            "g23": "NOT_EXECUTED", "g24": "NOT_EXECUTED",
            "certified": False
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    req = sub.add_parser("infer")
    req.add_argument("--provider", choices=tuple(ENDPOINTS), required=True)
    req.add_argument("--allow-outbound-model-data", action="store_true")
    req.add_argument("--acknowledge-possible-usage-charges", action="store_true")
    req.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args(argv)
    try:
        brain = VirtualBrain()
        if args.cmd == "status":
            print(json.dumps(brain.availability(), indent=2, sort_keys=True))
        else:
            # Never infer/send repo contents or the desktop automatically.
            if not args.allow_outbound_model_data:
                raise PermissionError("OUTBOUND_MODEL_TRANSFER_REQUIRES_OWNER_CONSENT")
            prompt = sys.stdin.read(MAX_PROMPT_BYTES + 1)
            result = brain.infer(
                provider=args.provider, prompt=prompt,
                owner_consents_to_egress=True,
                acknowledges_usage_billing=args.acknowledge_possible_usage_charges,
                max_tokens=args.max_tokens)
            print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except Exception as exc:
        # Never expose credential, prompt or external exception content.
        print(json.dumps({"status": "HOLD", "error": str(exc)[:90],
                          "certified": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
