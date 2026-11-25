"""Literal grammar. It does not call a remote model."""
from __future__ import annotations

from pathlib import Path

from lark import Lark, Token, Tree

from metagente_luna_s3.ir import Argument, Interpretation, Provenance

_PARSER = Lark(Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8"), parser="earley")


def literals(instruction: str) -> dict[str, list[str]]:
    found = {"cidr": [], "ipv4": [], "bracket": [], "quoted": [], "number": []}
    for node in _PARSER.parse(instruction).children:
        if isinstance(node, Tree) and node.data in found:
            found[node.data].append(str(node.children[0]))
        elif isinstance(node, Token) and node.type in found:
            found[node.type].append(str(node))
    return found


def interpret(instruction: str) -> Interpretation:
    found = literals(instruction)
    text = " ".join(instruction.split())
    if found["cidr"] and ("red" in text or "broadcast" in text):
        return Interpretation(
            source_instruction=text,
            intent="cidr_bounds",
            intent_method="LARK_LITERALS_PLUS_INTENT_WORD",
            arguments=[Argument(name="cidr", value=found["cidr"][0], provenance=Provenance.SOURCE_INSTRUCTION)],
            status="READY",
        )
    if found["cidr"]:
        return Interpretation(
            source_instruction=text,
            intent="UNRESOLVED",
            intent_method="LARK_LITERALS_PLUS_INTENT_WORD",
            arguments=[Argument(name="cidr", value=found["cidr"][0], provenance=Provenance.SOURCE_INSTRUCTION, required=False)],
            ambiguities=["a CIDR is present but the operation does not say network or broadcast"],
            status="AMBIGUOUS",
        )
    return Interpretation(
        source_instruction=text,
        intent="UNRESOLVED",
        intent_method="LARK_LITERALS_PLUS_INTENT_WORD",
        missing=["no registered intent"],
        status="UNRESOLVED",
    )
