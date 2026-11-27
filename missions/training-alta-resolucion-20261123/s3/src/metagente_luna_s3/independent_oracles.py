"""Independent reference oracles kept separate from capability producers.

These functions intentionally use independent standard-library references and
must not import or call producer implementations.
"""
from __future__ import annotations

import ipaddress


def cidr_bounds_oracle(arguments: dict, observed: dict) -> dict:
    try:
        network = ipaddress.ip_interface(arguments["cidr"]).network
    except ValueError:
        expected = {"accepted": False, "rejected": True}
        return {
            "ok": observed.get("accepted") is False and observed.get("rejected") is True,
            "method": "independent ipaddress input-validation oracle",
            "expected": expected,
        }
    expected = {
        "accepted": True,
        "network": str(network.network_address),
        "broadcast": str(network.broadcast_address),
    }
    return {
        "ok": all(observed.get(key) == value for key, value in expected.items()),
        "method": "ipaddress.ip_interface reference implementation",
        "expected": expected,
    }
