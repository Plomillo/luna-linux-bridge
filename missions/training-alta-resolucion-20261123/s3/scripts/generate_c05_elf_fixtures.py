"""Build deterministic ELF specimens for the read-only INF case probes."""
from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = b"int exported_value = 23; int fixture_marker(int x) { return x + exported_value; } int main(void) { return fixture_marker(1) == 24 ? 0 : 1; }\n"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="c05-elf-build-") as directory:
        root = Path(directory)
        source, alternate_source = root / "fixture.c", root / "fixture-alt.c"
        normal, stripped = root / "fixture.elf", root / "fixture-stripped.elf"
        alternate, alternate_stripped = root / "fixture-alt.elf", root / "fixture-alt-stripped.elf"
        source.write_bytes(SOURCE)
        alternate_source.write_bytes(SOURCE.replace(b"23", b"29"))
        subprocess.run(["gcc", "-O0", "-fno-pie", "-no-pie", "-Wl,--build-id=none", "-Wl,--export-dynamic", "-o", str(normal), str(source)], check=True, timeout=15)
        subprocess.run(["cp", str(normal), str(stripped)], check=True, timeout=5)
        subprocess.run(["strip", "--strip-all", str(stripped)], check=True, timeout=5)
        subprocess.run(["gcc", "-O0", "-fno-pie", "-no-pie", "-Wl,--build-id=none", "-Wl,--export-dynamic", "-o", str(alternate), str(alternate_source)], check=True, timeout=15)
        subprocess.run(["cp", str(alternate), str(alternate_stripped)], check=True, timeout=5)
        subprocess.run(["strip", "--strip-all", str(alternate_stripped)], check=True, timeout=5)
        variants = {
            "FX-MGL5-INF-0054-0095.elf": normal.read_bytes(),
            "FX-MGL5-INF-0095-boundary.elf": alternate.read_bytes(),
            "FX-MGL5-INF-0057-stripped.elf": stripped.read_bytes(),
            "FX-MGL5-INF-0057-boundary-stripped.elf": alternate_stripped.read_bytes(),
        }
    raw = bytearray(variants["FX-MGL5-INF-0054-0095.elf"])
    if raw[:6] != b"\x7fELF\x02\x01":
        raise RuntimeError("compiler did not emit ELF64 little-endian")
    raw[18:20] = (40).to_bytes(2, "little")
    variants["FX-MGL5-INF-0060-arm.elf"] = bytes(raw)
    for name, payload in variants.items():
        path = ROOT / "fixtures" / name
        path.write_bytes(payload)
        print(f"{name} sha256={hashlib.sha256(payload).hexdigest()} bytes={len(payload)}")


if __name__ == "__main__":
    main()
