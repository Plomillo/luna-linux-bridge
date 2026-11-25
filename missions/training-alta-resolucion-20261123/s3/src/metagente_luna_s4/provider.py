"""Remote interpretation is a separate adapter. This one does not invent it."""
from __future__ import annotations

from typing import Protocol


class Interpreter(Protocol):
    def interpret(self, instruction: str) -> dict: ...


class UnavailableProvider:
    status = "UNAVAILABLE"

    def interpret(self, instruction: str) -> dict:
        return {"status": self.status, "interpretation": None, "instruction_received": bool(instruction)}
