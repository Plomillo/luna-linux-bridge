"""Independent reference oracles kept separate from capability producers.

These functions intentionally use independent standard-library references and
must not import or call producer implementations.
"""
from __future__ import annotations

import ipaddress


def cidr_bounds_oracle(arguments: dict, observed: dict) -> dict:
    network = ipaddress.ip_interface(arguments["cidr"]).network
    expected = {
        "network": str(network.network_address),
        "broadcast": str(network.broadcast_address),
    }
    return {
        "ok": observed == expected,
        "method": "ipaddress.ip_interface reference implementation",
        "expected": expected,
    }
