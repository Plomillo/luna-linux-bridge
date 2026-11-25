"""Capabilities that have a schema and an oracle id. Unknown ids cannot run."""
from __future__ import annotations

import ipaddress
from collections.abc import Callable

from pydantic import BaseModel


class Capability(BaseModel):
    capability_id: str
    version: str
    input_schema: dict
    output_schema: dict
    oracle_id: str
    status: str


def cidr_bounds(cidr: str) -> dict:
    address, prefix_s = cidr.split("/")
    ip = 0
    for part in address.split("."):
        ip = (ip << 8) | int(part)
    prefix = int(prefix_s)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    network = ip & mask
    broadcast = network | (0xFFFFFFFF ^ mask)

    def dotted(value: int) -> str:
        return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))

    return {"network": dotted(network), "broadcast": dotted(broadcast)}


def cidr_oracle(cidr: str, observed: dict) -> dict:
    network = ipaddress.ip_interface(cidr).network
    ok = observed["network"] == str(network.network_address) and observed["broadcast"] == str(network.broadcast_address)
    return {"ok": ok, "method": "ipaddress, not the integer mask"}


REGISTRY: dict[str, Capability] = {
    "cidr_bounds": Capability(
        capability_id="cidr_bounds",
        version="1",
        input_schema={"type": "object", "required": ["cidr"], "properties": {"cidr": {"type": "string"}}},
        output_schema={"type": "object", "required": ["network", "broadcast"]},
        oracle_id="ipaddress",
        status="TESTED",
    )
}

ORACLES: dict[str, Callable[..., dict]] = {
    "ipaddress": lambda arguments, observed: cidr_oracle(arguments["cidr"], observed),
}

EXECUTORS: dict[str, Callable[..., dict]] = {"cidr_bounds": cidr_bounds}


def run(capability_id: str, arguments: dict) -> dict:
    if capability_id not in REGISTRY or capability_id not in EXECUTORS:
        raise KeyError(capability_id)
    return EXECUTORS[capability_id](**arguments)
