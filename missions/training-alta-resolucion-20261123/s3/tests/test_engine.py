import pytest
from hypothesis import given
from hypothesis import strategies as st

from metagente_luna_s3.discover import discover
from metagente_luna_s3.interpret import interpret, literals
from metagente_luna_s3.ir import Argument, Provenance
from metagente_luna_s3.planner import CycleError, Step, order
from metagente_luna_s3.registry import cidr_oracle, run


def test_grammar_keeps_the_cidr_intact():
    found = literals("Calcular red y broadcast de 192.0.2.130/26.")
    assert found["cidr"] == ["192.0.2.130/26"]


def test_interpretation_is_ready_only_when_the_intent_is_present():
    ready = interpret("Calcular red y broadcast de 192.0.2.130/26.")
    assert ready.status == "READY"
    assert ready.arguments[0].provenance is Provenance.SOURCE_INSTRUCTION
    bare = interpret("192.0.2.130/26")
    assert bare.status == "AMBIGUOUS"


def test_required_unknown_argument_is_rejected():
    with pytest.raises(ValueError):
        Argument(name="address", value="10.0.0.1", provenance=Provenance.UNKNOWN)


def test_cycle_is_rejected():
    steps = [Step(step_id="a", capability_id="x", depends_on=["b"]), Step(step_id="b", capability_id="y", depends_on=["a"])]
    with pytest.raises(CycleError):
        order(steps)


def test_keyword_does_not_invent_a_fixture():
    result = discover("MGL5-INF-0054", "Extraer secciones de un ELF de laboratorio.", ["README.md", "missions/training/fixtures/MGL5-INF-0009/a.json"])
    assert result["result"] == "FIXTURE_NOT_IN_TREE"
    assert result["keyword_is_evidence"] is False
    assert result["elf_paths"] == []


def test_cidr_executor_and_oracle_agree():
    observed = run("cidr_bounds", {"cidr": "192.0.2.130/26"})
    assert observed == {"network": "192.0.2.128", "broadcast": "192.0.2.191"}
    assert cidr_oracle("192.0.2.130/26", observed)["ok"] is True


def test_unknown_capability_cannot_run():
    with pytest.raises(KeyError):
        run("not-registered", {})


@given(st.lists(st.integers(min_value=0, max_value=20), min_size=1, max_size=6, unique=True))
def test_ordering_is_stable(nodes):
    steps = [Step(step_id=str(node), capability_id="x", depends_on=[str(other) for other in nodes if other < node]) for node in nodes]
    assert order(steps) == [str(node) for node in sorted(nodes)]
