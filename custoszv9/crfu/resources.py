"""Measured resource gates: unknown or invalid measurements are HOLD, not PASS."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
import shutil
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResourceSnapshot:
    ram_available_bytes: int | None
    disk_available_bytes: int | None
    cpu_count: int | None
    measured_at_utc: str
    source: str
    confidence: str = "MEASURED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResourceBudget:
    ram_required_bytes: int
    ram_reserved_bytes: int
    disk_required_bytes: int
    max_concurrency: int


def _nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def probe_host_resources(path: str | Path = ".") -> ResourceSnapshot:
    """Measure available RAM, free disk and CPU without third-party runtime dependencies."""
    available_ram = None
    source = "UNKNOWN"
    if os.name == "posix":
        try:
            pages = os.sysconf("SC_AVPHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if pages >= 0 and page_size > 0:
                available_ram = int(pages) * int(page_size)
                source = "os.sysconf:SC_AVPHYS_PAGES"
        except (OSError, ValueError, KeyError):
            pass
    if available_ram is None and os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                available_ram = int(status.ullAvailPhys)
                source = "Windows:GlobalMemoryStatusEx"
        except (AttributeError, OSError, TypeError):
            pass
    if available_ram is None:
        try:
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    available_ram = int(line.split()[1]) * 1024
                    source = "/proc/meminfo:MemAvailable"
                    break
        except (OSError, ValueError, IndexError):
            pass
    try:
        disk_free = int(shutil.disk_usage(path).free)
    except (OSError, ValueError):
        disk_free = None
    cpu = os.cpu_count()
    confidence = (
        "MEASURED"
        if available_ram is not None and disk_free is not None and cpu is not None
        else "UNKNOWN"
    )
    return ResourceSnapshot(
        available_ram,
        disk_free,
        cpu,
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        source,
        confidence,
    )


def evaluate_budget(budget: ResourceBudget, snapshot: ResourceSnapshot) -> dict[str, Any]:
    """Apply strict Agda-aligned limits; equality is rejected and invalid evidence holds."""
    invalid = []
    for name, value in (
        ("ram_required_bytes", budget.ram_required_bytes),
        ("ram_reserved_bytes", budget.ram_reserved_bytes),
        ("disk_required_bytes", budget.disk_required_bytes),
        ("max_concurrency", budget.max_concurrency),
    ):
        if not _nonnegative_int(value):
            invalid.append("BUDGET_FIELD_INVALID:" + name)
    if invalid:
        return {"status": "FAIL", "reasons": invalid, "snapshot": snapshot.to_dict()}

    missing = []
    values = (
        ("ram_available_bytes", snapshot.ram_available_bytes),
        ("disk_available_bytes", snapshot.disk_available_bytes),
        ("cpu_count", snapshot.cpu_count),
    )
    for name, value in values:
        if value is None:
            missing.append(name.upper() + "_UNKNOWN")
        elif not _nonnegative_int(value):
            missing.append("RESOURCE_MEASUREMENT_INVALID:" + name)
    if snapshot.confidence != "MEASURED":
        missing.append("RESOURCE_MEASUREMENT_NOT_TRUSTED")
    if missing:
        return {"status": "HOLD", "reasons": missing, "snapshot": snapshot.to_dict()}

    assert snapshot.ram_available_bytes is not None
    assert snapshot.disk_available_bytes is not None
    assert snapshot.cpu_count is not None
    usable = max(0, snapshot.ram_available_bytes - budget.ram_reserved_bytes)
    fail = []
    # Strict semantics: required + reserved must be strictly below available RAM.
    # This also rejects a reservation >= available RAM when required RAM is zero.
    if budget.ram_required_bytes + budget.ram_reserved_bytes >= snapshot.ram_available_bytes:
        fail.append("RAM_BUDGET_EXCEEDED")
    # Strict semantics: required disk must be strictly below available disk.
    if budget.disk_required_bytes >= snapshot.disk_available_bytes:
        fail.append("DISK_BUDGET_EXCEEDED")
    if budget.max_concurrency < 1 or budget.max_concurrency > max(1, snapshot.cpu_count):
        fail.append("CONCURRENCY_BUDGET_INVALID")
    return {
        "status": "FAIL" if fail else "PASS",
        "reasons": fail,
        "ram_usable_bytes": usable,
        "disk_available_bytes": snapshot.disk_available_bytes,
        "cpu_count": snapshot.cpu_count,
        "measured_at_utc": snapshot.measured_at_utc,
        "source": snapshot.source,
    }
