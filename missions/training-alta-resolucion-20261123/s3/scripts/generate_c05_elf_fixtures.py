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
        route_source, route_binary = root / "fixture-route.c", root / "fixture-route.elf"
        boundary_route_binary = root / "fixture-route-boundary.elf"
        route_source.write_bytes(SOURCE)
        subprocess.run(["gcc", "-O0", "-fno-pie", "-no-pie", "-Wl,--build-id=none", "-Wl,-rpath,/c05/rpath:/c05/runpath", "-o", str(route_binary), str(route_source)], check=True, timeout=15)
        subprocess.run(["gcc", "-O0", "-fno-pie", "-no-pie", "-Wl,--build-id=none", "-Wl,-rpath,/c05/rpath:/c05/direct", "-o", str(boundary_route_binary), str(route_source)], check=True, timeout=15)
        variants = {
            "FX-MGL5-INF-0054-0095.elf": normal.read_bytes(),
            "FX-MGL5-INF-0095-boundary.elf": alternate.read_bytes(),
            "FX-MGL5-INF-0057-stripped.elf": stripped.read_bytes(),
            "FX-MGL5-INF-0057-boundary-stripped.elf": alternate_stripped.read_bytes(),
            "FX-MGL5-INF-0059-rpath-runpath.elf": add_both_search_tags(route_binary.read_bytes(), "/c05/runpath"),
            "FX-MGL5-INF-0059-boundary-rpath-runpath.elf": add_both_search_tags(boundary_route_binary.read_bytes(), "/c05/direct"),
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


def add_both_search_tags(payload: bytes, rpath_value: str) -> bytes:
    """Repurpose the inert DT_DEBUG slot as DT_RPATH alongside DT_RUNPATH."""
    import struct

    raw = bytearray(payload)
    shoff = struct.unpack_from("<Q", raw, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", raw, 58)
    headers = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff + i * shentsize) for i in range(shnum)]
    names_header = headers[shstrndx]
    names = raw[names_header[4]:names_header[4] + names_header[5]]
    def section_name(offset: int) -> str:
        end = names.find(0, offset)
        return names[offset:end if end >= 0 else len(names)].decode()
    sections = {section_name(row[0]): row for row in headers}
    dynamic, dynstr = sections[".dynamic"], sections[".dynstr"]
    strings = raw[dynstr[4]:dynstr[4] + dynstr[5]]
    target = rpath_value.encode() + b"\0"
    string_offset = strings.find(target)
    if string_offset < 0:
        raise RuntimeError(f"dynamic string table lacks RPATH value: {rpath_value}")
    entry_size = dynamic[9] or 16
    for offset in range(dynamic[4], dynamic[4] + dynamic[5], entry_size):
        tag, _value = struct.unpack_from("<qQ", raw, offset)
        if tag == 21:  # DT_DEBUG is loader-populated and inert in this static fixture.
            struct.pack_into("<qQ", raw, offset, 15, string_offset)
            return bytes(raw)
    raise RuntimeError("fixture has no DT_DEBUG slot to use for DT_RPATH")


if __name__ == "__main__":
    main()
