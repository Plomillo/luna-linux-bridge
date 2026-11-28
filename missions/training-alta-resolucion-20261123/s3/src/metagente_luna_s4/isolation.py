"""Validate C05 isolation evidence; certification requires restricted Docker."""
from __future__ import annotations

import re


def isolation_evidence_valid(isolation: object) -> bool:
    """Accept only the complete restricted-Docker profile, never host processes."""
    if not isinstance(isolation, dict):
        return False
    image_id = isolation.get("image_id")
    return (
        isolation.get("mode") == "DOCKER_RESTRICTED_CONTAINER"
        and isolation.get("process_isolated") is True
        and isolation.get("containerized") is True
        and isolation.get("network_disabled") is True
        and isolation.get("root_filesystem_read_only") is True
        and isolation.get("capabilities_dropped") is True
        and isolation.get("non_root_uid") == 65534
        and isolation.get("resource_limits") == {"pids": 64, "memory": "256m", "cpus": 1}
        and isinstance(image_id, str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is not None
        and isolation.get("workspace_ephemeral") is True
        and isolation.get("cwd_isolated") is True
        and isolation.get("home_isolated") is True
        and isolation.get("tmp_isolated") is True
        and isolation.get("sandbox") is False
        and isolation.get("container_restrictions_verified") is True
        and isolation.get("kernel_isolation") == "SHARED_HOST_KERNEL_NOT_VM"
    )
