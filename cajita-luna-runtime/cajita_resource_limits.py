#!/usr/bin/env python3
"""Fail-closed cgroup-v2 RAM and one-core policies for Cajita.

The kernel enforces the aggregate memory ceiling through the enclosing Docker
cgroup. RLIMIT_AS is intentionally not used: it caps virtual address space and
can reject mmap-backed safetensors files even when resident RAM is below budget.
A caller must run inside a cgroup already configured with the exact requested
memory ceiling; this module verifies, but never pretends to create, that cgroup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

CANDIDATE_MEMORY_BYTES = 1 * 1024**3
CANDIDATE_CPU_COUNT = 1
REPAIR_MEMORY_BYTES = 3 * 1024**3
REPAIR_CPU_COUNT = 1
CGROUP_ROOT = Path("/sys/fs/cgroup")


class ResourcePolicyError(RuntimeError):
    """Raised when an execution environment does not satisfy its resource contract."""


def _read_cgroup_text(name: str) -> str:
    path = CGROUP_ROOT / name
    try:
        return path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise ResourcePolicyError("CGROUP_V2_CONTROL_UNAVAILABLE:" + name) from exc


def _read_cgroup_int(name: str, *, allow_zero: bool = False) -> int:
    raw = _read_cgroup_text(name)
    if raw == "max":
        raise ResourcePolicyError("CGROUP_V2_LIMIT_UNBOUNDED:" + name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ResourcePolicyError("CGROUP_V2_LIMIT_INVALID:" + name) from exc
    if value < 0 or (value == 0 and not allow_zero):
        raise ResourcePolicyError("CGROUP_V2_LIMIT_NONPOSITIVE:" + name)
    return value


def _optional_swap_limit() -> int | None:
    """Read the swap cap when exposed; zero is valid and means swap is disabled."""
    path = CGROUP_ROOT / "memory.swap.max"
    if not path.is_file():
        return None
    raw = _read_cgroup_text("memory.swap.max")
    if raw == "max":
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ResourcePolicyError("CGROUP_V2_LIMIT_INVALID:memory.swap.max") from exc
    if value < 0:
        raise ResourcePolicyError("CGROUP_V2_LIMIT_INVALID:memory.swap.max")
    return value


def verify_cgroup_budget(memory_bytes: int, cpu_count: int = 1) -> dict:
    """Verify an exact RAM cap and a CPU quota no greater than one core."""
    if isinstance(memory_bytes, bool) or not isinstance(memory_bytes, int) or memory_bytes <= 0:
        raise ResourcePolicyError("RESOURCE_MEMORY_LIMIT_INVALID")
    if isinstance(cpu_count, bool) or cpu_count != 1:
        raise ResourcePolicyError("CPU_BUDGET_MUST_EQUAL_ONE")
    if not sys.platform.startswith("linux"):
        raise ResourcePolicyError("CGROUP_V2_RESOURCE_POLICY_REQUIRES_LINUX")
    if not (CGROUP_ROOT / "cgroup.controllers").is_file():
        raise ResourcePolicyError("CGROUP_V2_NOT_AVAILABLE")

    observed_memory = _read_cgroup_int("memory.max")
    if observed_memory != memory_bytes:
        raise ResourcePolicyError(
            "CGROUP_MEMORY_BUDGET_MISMATCH:observed="
            + str(observed_memory) + ":expected=" + str(memory_bytes)
        )

    cpu_fields = _read_cgroup_text("cpu.max").split()
    if len(cpu_fields) != 2:
        raise ResourcePolicyError("CGROUP_CPU_MAX_FIELDS_INVALID")
    try:
        quota, period = (int(value) for value in cpu_fields)
    except ValueError as exc:
        raise ResourcePolicyError("CGROUP_CPU_MAX_UNAVAILABLE_OR_INVALID") from exc
    if quota <= 0 or period <= 0 or quota > period:
        raise ResourcePolicyError(
            "CGROUP_CPU_BUDGET_EXCEEDS_ONE_CORE:quota=" + str(quota) + ":period=" + str(period)
        )

    swap_limit = _optional_swap_limit()
    return {
        "memory_limit_bytes": observed_memory,
        "memory_limit_gib": observed_memory / 1024**3,
        "memory_limit_mechanism": "DOCKER_CGROUP_V2_MEMORY_MAX",
        "memory_swap_limit_bytes": swap_limit,
        "memory_swap_policy": (
            "SWAP_DISABLED" if swap_limit == 0 else
            "SWAP_LIMITED" if swap_limit is not None else
            "SWAP_CONTROL_NOT_EXPOSED_OR_UNBOUNDED"
        ),
        "cpu_count": 1,
        "cpu_quota": quota,
        "cpu_period": period,
        "cpu_limit_cores": quota / period,
        "cpu_limit_mechanism": "DOCKER_CGROUP_V2_CPU_MAX",
        "aggregate_cgroup_memory_limit": "ENFORCED_BY_KERNEL",
    }


def apply_cpu_affinity(cpu_count: int = 1) -> list[int]:
    if isinstance(cpu_count, bool) or cpu_count != 1:
        raise ResourcePolicyError("CPU_BUDGET_MUST_EQUAL_ONE")
    if not hasattr(os, "sched_getaffinity") or not hasattr(os, "sched_setaffinity"):
        raise ResourcePolicyError("RESOURCE_CPU_AFFINITY_UNAVAILABLE")
    allowed = sorted(os.sched_getaffinity(0))
    if not allowed:
        raise ResourcePolicyError("RESOURCE_CPU_AFFINITY_EMPTY")
    selected = allowed[0]
    os.sched_setaffinity(0, {selected})
    observed = sorted(os.sched_getaffinity(0))
    if observed != [selected]:
        raise ResourcePolicyError("RESOURCE_CPU_AFFINITY_POSTCHECK_FAILED")
    return observed


def apply_process_limits(memory_bytes: int, cpu_count: int = 1) -> dict:
    """Verify actual aggregate cgroup limits and pin this process to one CPU."""
    cgroup = verify_cgroup_budget(memory_bytes, cpu_count)
    affinity = apply_cpu_affinity(cpu_count)
    return {
        "status": "PASS_CGROUP_AND_CPU_AFFINITY_VERIFIED",
        "platform": sys.platform,
        **cgroup,
        "cpu_affinity": affinity,
        "process_virtual_address_limit": "NOT_USED",
    }


def child_preexec_fn(
    memory_bytes: int = CANDIDATE_MEMORY_BYTES,
    cpu_count: int = CANDIDATE_CPU_COUNT,
) -> Callable[[], None]:
    """Return a pre-exec hook that refuses candidate startup outside its 1-GiB cgroup."""
    if not sys.platform.startswith("linux"):
        raise ResourcePolicyError("CANDIDATE_RESOURCE_LIMITS_REQUIRE_LINUX")
    if cpu_count != 1:
        raise ResourcePolicyError("CPU_BUDGET_MUST_EQUAL_ONE")

    def _apply() -> None:
        apply_process_limits(memory_bytes, cpu_count)

    return _apply


def candidate_policy() -> dict:
    return {
        "memory_limit_bytes": CANDIDATE_MEMORY_BYTES,
        "memory_limit_gib": 1,
        "memory_limit_mechanism": "DOCKER_CGROUP_V2_MEMORY_MAX",
        "cpu_count": CANDIDATE_CPU_COUNT,
        "cpu_limit_mechanism": "DOCKER_CGROUP_V2_CPU_MAX",
        "thread_environment": {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
        },
        "aggregate_cgroup_memory_limit": "REQUIRED_AND_VERIFIED",
        "process_virtual_address_limit": "NOT_USED",
    }


def repair_policy() -> dict:
    return {
        "memory_limit_bytes": REPAIR_MEMORY_BYTES,
        "memory_limit_gib": 3,
        "memory_limit_mechanism": "DOCKER_CGROUP_V2_MEMORY_MAX",
        "cpu_count": REPAIR_CPU_COUNT,
        "cpu_limit_mechanism": "DOCKER_CGROUP_V2_CPU_MAX_AND_SCHED_SETAFFINITY",
        "thread_environment": candidate_policy()["thread_environment"],
        "aggregate_cgroup_memory_limit": "REQUIRED_AND_VERIFIED",
        "process_virtual_address_limit": "NOT_USED",
    }
