#!/usr/bin/env python3
"""Linux process limits for bounded Cajita candidate inference.

RLIMIT_AS is an enforceable per-process virtual-address-space ceiling. CPU
affinity pins the child and its inherited threads to one permitted logical CPU.
This module does not claim a cgroup-wide RSS cap: the caller records the exact
mechanism used and separately records observed RSS.
"""
from __future__ import annotations

import os
import resource
import sys
from typing import Callable

CANDIDATE_MEMORY_BYTES = 1 * 1024**3
CANDIDATE_CPU_COUNT = 1
REPAIR_MEMORY_BYTES = 3 * 1024**3
REPAIR_CPU_COUNT = 1


class ResourcePolicyError(RuntimeError):
    pass


def _effective_as_limit(requested_bytes: int) -> int:
    if isinstance(requested_bytes, bool) or not isinstance(requested_bytes, int) or requested_bytes <= 0:
        raise ResourcePolicyError("RESOURCE_MEMORY_LIMIT_INVALID")
    if not sys.platform.startswith("linux") or not hasattr(resource, "RLIMIT_AS"):
        raise ResourcePolicyError("RESOURCE_LIMITS_REQUIRE_LINUX_RLIMIT_AS")
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    values = [requested_bytes]
    if soft != resource.RLIM_INFINITY:
        values.append(int(soft))
    if hard != resource.RLIM_INFINITY:
        values.append(int(hard))
    effective = min(values)
    if effective <= 0:
        raise ResourcePolicyError("RESOURCE_ADDRESS_SPACE_LIMIT_UNAVAILABLE")
    return effective


def apply_process_limits(memory_bytes: int, cpu_count: int = 1) -> dict:
    """Apply hard per-process address-space and Linux CPU-affinity limits."""
    if isinstance(cpu_count, bool) or cpu_count != 1:
        raise ResourcePolicyError("CANDIDATE_CPU_BUDGET_MUST_EQUAL_ONE")
    if not hasattr(os, "sched_getaffinity") or not hasattr(os, "sched_setaffinity"):
        raise ResourcePolicyError("RESOURCE_CPU_AFFINITY_UNAVAILABLE")
    allowed = sorted(os.sched_getaffinity(0))
    if not allowed:
        raise ResourcePolicyError("RESOURCE_CPU_AFFINITY_EMPTY")
    selected = allowed[0]
    os.sched_setaffinity(0, {selected})
    effective = _effective_as_limit(memory_bytes)
    resource.setrlimit(resource.RLIMIT_AS, (effective, effective))
    observed_affinity = sorted(os.sched_getaffinity(0))
    if observed_affinity != [selected]:
        raise ResourcePolicyError("RESOURCE_CPU_AFFINITY_POSTCHECK_FAILED")
    actual_soft, actual_hard = resource.getrlimit(resource.RLIMIT_AS)
    if actual_soft != effective or actual_hard != effective:
        raise ResourcePolicyError("RESOURCE_ADDRESS_SPACE_POSTCHECK_FAILED")
    return {
        "status": "PASS_PROCESS_LIMITS_APPLIED",
        "platform": sys.platform,
        "memory_limit_bytes": effective,
        "memory_limit_mechanism": "RLIMIT_AS_SOFT_AND_HARD_PER_PROCESS",
        "cpu_count": 1,
        "cpu_affinity": observed_affinity,
        "cpu_limit_mechanism": "SCHED_SETAFFINITY_INHERITED_BY_CHILD_THREADS",
        "aggregate_cgroup_rss_limit": "NOT_CLAIMED",
    }


def child_preexec_fn(memory_bytes: int = CANDIDATE_MEMORY_BYTES, cpu_count: int = CANDIDATE_CPU_COUNT) -> Callable[[], None]:
    """Return a POSIX pre-exec hook; limits are active before model imports."""
    if not sys.platform.startswith("linux"):
        raise ResourcePolicyError("CANDIDATE_RESOURCE_LIMITS_REQUIRE_LINUX")
    if cpu_count != 1:
        raise ResourcePolicyError("CANDIDATE_CPU_BUDGET_MUST_EQUAL_ONE")

    def _apply() -> None:
        apply_process_limits(memory_bytes, cpu_count)

    return _apply


def candidate_policy() -> dict:
    return {
        "memory_limit_bytes": CANDIDATE_MEMORY_BYTES,
        "memory_limit_gib": 1,
        "memory_limit_mechanism": "RLIMIT_AS_SOFT_AND_HARD_PER_PROCESS",
        "cpu_count": CANDIDATE_CPU_COUNT,
        "cpu_limit_mechanism": "SCHED_SETAFFINITY",
        "thread_environment": {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
        },
        "aggregate_cgroup_rss_limit": "NOT_CLAIMED",
    }
