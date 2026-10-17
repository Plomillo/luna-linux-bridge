"""Measured resource gates: unknown measurements are HOLD, not PASS."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import os,shutil
from pathlib import Path
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
def probe_host_resources(path:str|Path=".")->ResourceSnapshot:
 """Measure available RAM, free disk and CPU without third-party runtime dependencies."""
 available_ram=None;source="UNKNOWN"
 if os.name=="posix":
  try:
   pages=os.sysconf("SC_AVPHYS_PAGES");page_size=os.sysconf("SC_PAGE_SIZE")
   if pages>=0 and page_size>0:available_ram=int(pages)*int(page_size);source="os.sysconf:SC_AVPHYS_PAGES"
  except (OSError,ValueError,KeyError):pass
 if available_ram is None and os.name=="nt":
  try:
   import ctypes
   class MemoryStatus(ctypes.Structure):
    _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),
      ("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),
      ("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),
      ("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),
      ("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
   status=MemoryStatus();status.dwLength=ctypes.sizeof(MemoryStatus)
   if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
    available_ram=int(status.ullAvailPhys);source="Windows:GlobalMemoryStatusEx"
  except (AttributeError,OSError,TypeError):pass
 if available_ram is None:
  try:
   for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
    if line.startswith("MemAvailable:"):
     available_ram=int(line.split()[1])*1024;source="/proc/meminfo:MemAvailable";break
  except (OSError,ValueError,IndexError):pass
 try:disk_free=int(shutil.disk_usage(path).free)
 except (OSError,ValueError):disk_free=None
 cpu=os.cpu_count()
 confidence="MEASURED" if available_ram is not None and disk_free is not None and cpu is not None else "UNKNOWN"
 return ResourceSnapshot(available_ram,disk_free,cpu,datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),source,confidence)
def evaluate_budget(budget:ResourceBudget,snapshot:ResourceSnapshot)->dict[str,Any]:
 invalid=[]
 for name,value in (("ram_required_bytes",budget.ram_required_bytes),("ram_reserved_bytes",budget.ram_reserved_bytes),("disk_required_bytes",budget.disk_required_bytes),("max_concurrency",budget.max_concurrency)):
  if isinstance(value,bool) or not isinstance(value,int) or value<0:invalid.append("BUDGET_FIELD_INVALID:"+name)
 if invalid:return {"status":"FAIL","reasons":invalid,"snapshot":snapshot.to_dict()}
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
