"""Typed intermediate representation. A required argument cannot be UNKNOWN."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Provenance(str, Enum):
    SOURCE_INSTRUCTION = "SOURCE_INSTRUCTION"
    PREVIOUS_CONTEXT = "PREVIOUS_CONTEXT"
    FIXTURE = "FIXTURE"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    DETERMINISTIC_DERIVATION = "DETERMINISTIC_DERIVATION"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    USER_SPECIFIED = "USER_SPECIFIED"
    UNKNOWN = "UNKNOWN"


class Argument(BaseModel):
    name: str
    value: Any
    provenance: Provenance
    required: bool = True

    @model_validator(mode="after")
    def reject_unknown_required(self) -> Argument:
        if self.required and self.provenance is Provenance.UNKNOWN:
            raise ValueError("a required argument cannot have UNKNOWN provenance")
        return self


class Interpretation(BaseModel):
    source_instruction: str
    intent: str
    intent_method: str
    arguments: list[Argument] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    status: str
    model_provider: str = "UNAVAILABLE"
