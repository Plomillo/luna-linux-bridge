"""Measured resource gates: unknown measurements are HOLD, not PASS."""
from dataclasses import dataclass,asdict
from typing import Any
@dataclass(frozen=True)
class ResourceSnapshot:
 ram_available_bytes:int|None
 disk_available_bytes:int|None
 cpu_count:int|None
 measured_at_utc:str
 source:str
 confidence:str="MEASURED"
 def to_dict(self)->dict[str,Any]:return asdict(self)
@dataclass(frozen=True)
class ResourceBudget:
 ram_required_bytes:int
 ram_reserved_bytes:int
 disk_required_bytes:int
 max_concurrency:int
def evaluate_budget(budget:ResourceBudget,snapshot:ResourceSnapshot)->dict[str,Any]:
 missing=[]
 if snapshot.ram_available_bytes is None:missing.append("RAM_AVAILABLE_UNKNOWN")
 if snapshot.disk_available_bytes is None:missing.append("DISK_AVAILABLE_UNKNOWN")
 if snapshot.cpu_count is None:missing.append("CPU_COUNT_UNKNOWN")
 if snapshot.confidence!="MEASURED":missing.append("RESOURCE_MEASUREMENT_NOT_TRUSTED")
 if missing:return {"status":"HOLD","reasons":missing,"snapshot":snapshot.to_dict()}
 usable=max(0,int(snapshot.ram_available_bytes)-budget.ram_reserved_bytes);fail=[]
 if budget.ram_required_bytes>usable:fail.append("RAM_BUDGET_EXCEEDED")
 if budget.disk_required_bytes>int(snapshot.disk_available_bytes):fail.append("DISK_BUDGET_EXCEEDED")
 if budget.max_concurrency<1 or budget.max_concurrency>max(1,int(snapshot.cpu_count)):fail.append("CONCURRENCY_BUDGET_INVALID")
 return {"status":"FAIL" if fail else "PASS","reasons":fail,"ram_usable_bytes":usable,"disk_available_bytes":snapshot.disk_available_bytes,"cpu_count":snapshot.cpu_count,"measured_at_utc":snapshot.measured_at_utc,"source":snapshot.source}
