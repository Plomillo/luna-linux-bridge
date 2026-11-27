"""Validate recorded isolation metadata for local-process and restricted-Docker runs."""
from __future__ import annotations

import re


def isolation_evidence_valid(isolation: object) -> bool:
    """Accept only fully evidenced process isolation or the pinned restricted Docker profile."""
    if not isinstance(isolation, dict):
        return False
    common = (
        isolation.get("process_isolated") is True
        and isolation.get("workspace_ephemeral") is True
        and isolation.get("cwd_isolated") is True
        and isolation.get("home_isolated") is True
        and isolation.get("tmp_isolated") is True
        and isolation.get("sandbox") is False
        and isolation.get("kernel_isolation") == "SHARED_HOST_KERNEL_NOT_VM"
    )
    if not common:
        return False
    mode = isolation.get("mode")
    if mode == "FRESH_PROCESS_TEMPORARY_WORKSPACE":
        return (
            isolation.get("containerized") is False
            and isolation.get("network_disabled") is False
            and isolation.get("root_filesystem_read_only") is False
            and isolation.get("capabilities_dropped") is False
            and isolation.get("container_restrictions_verified") is False
            and isolation.get("image_id") is None
        )
    if mode == "DOCKER_RESTRICTED_CONTAINER":
        return (
            isolation.get("containerized") is True
            and isolation.get("network_disabled") is True
            and isolation.get("root_filesystem_read_only") is True
            and isolation.get("capabilities_dropped") is True
            and isolation.get("non_root_uid") == 65534
            and isolation.get("container_restrictions_verified") is True
            and isinstance(isolation.get("image_id"), str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", isolation["image_id"]) is not None
            and isolation.get("resource_limits") == {"pids": 64, "memory": "256m", "cpus": 1}
        )
    return False
