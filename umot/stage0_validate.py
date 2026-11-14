#!/usr/bin/env python3
"""Fail-closed Stage 0 verifier for the protected UMOT wheel on Debian 13."""
from __future__ import annotations
import argparse
import base64, csv, hashlib, io, json, os, platform, re, shutil, subprocess, sys, tempfile, zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath

WHEEL_NAME = "umot_compact-1.0.5.post11-m11-m12-imatrix-cpu128-py3-none-manylinux_2_34_x86_64.whl"
EXPECTED_SHA256 = "2950aa605d972672af925015ec4d061e5f5e526187aaa2507fba6b6e80246db6"
EXPECTED_BYTES = 205679247
MIN_GLIBC = (2, 34)
WHEEL_TAG = "py3-none-manylinux_2_34_x86_64"

def run(argv: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)

def parse_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return values

def parse_version(value: str) -> tuple[int, ...] | None:
    match = re.search(r"(\d+(?:\.\d+)+|\d+)", value)
    return tuple(int(part) for part in match.group(1).split(".")) if match else None

def file_sha256(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size

def wheel_filename_compliance(filename: str) -> dict:
    """Check PEP 427 filename shape without changing the protected artifact."""
    basename = Path(filename).name
    if not basename.endswith(".whl"):
        return {"status": "FAIL", "reason": "WHEEL_EXTENSION_MISSING", "field_count": None}
    fields = basename[:-4].split("-")
    valid = len(fields) in (5, 6)
    return {"status": "PASS" if valid else "FAIL", "field_count": len(fields),
            "fields": fields,
            "reason": None if valid else "WHEEL_FILENAME_MUST_HAVE_5_OR_6_HYPHEN_FIELDS"}


def safe_wheel_members(names: list[str]) -> tuple[bool, str | None]:
    for name in names:
        member = PurePosixPath(name)
        if member.is_absolute() or ".." in member.parts or "\\" in name:
            return False, f"UNSAFE_WHEEL_MEMBER:{name}"
    return True, None

def verify_record(archive: zipfile.ZipFile, record_name: str) -> tuple[str, list[str]]:
    errors, seen = [], set()
    try:
        rows = csv.reader(io.StringIO(archive.read(record_name).decode("utf-8")))
        signature_files = {record_name + ".jws", record_name + ".p7s"}
        actual = {n for n in archive.namelist()
                  if not n.endswith("/") and n not in signature_files}
        for row in rows:
            if len(row) != 3:
                errors.append("RECORD_ROW_MALFORMED")
                continue
            name, hash_spec, size_spec = row
            if name in seen:
                errors.append(f"RECORD_DUPLICATE:{name}")
                continue
            seen.add(name)
            if name not in actual:
                errors.append(f"RECORD_MISSING_MEMBER:{name}")
                continue
            payload = archive.read(name)
            if name == record_name:
                if hash_spec or size_spec:
                    errors.append("RECORD_SELF_ENTRY_MUST_HAVE_EMPTY_HASH_AND_SIZE")
                continue
            if not hash_spec.startswith("sha256="):
                errors.append(f"RECORD_HASH_ALGORITHM_OR_MISSING:{name}")
                continue
            expected = hash_spec.split("=", 1)[1]
            observed = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode().rstrip("=")
            if observed != expected:
                errors.append(f"RECORD_HASH_MISMATCH:{name}")
            if not size_spec or not size_spec.isdigit() or int(size_spec) != len(payload):
                errors.append(f"RECORD_SIZE_MISMATCH:{name}")
        if record_name not in seen:
            errors.append("RECORD_SELF_ENTRY_MISSING")
        errors.extend(f"RECORD_UNLISTED_MEMBER:{n}" for n in sorted(actual - seen))
    except Exception as exc:
        errors.append(f"RECORD_READ_ERROR:{type(exc).__name__}:{exc}")
    return ("PASS" if not errors else "FAIL"), errors

def inspect_wheel(path: Path) -> dict:
    result = {
        "wheel": WHEEL_NAME, "path": str(path), "identity": "HOLD",
        "archive_integrity": "HOLD", "record_integrity": "HOLD",
        "wheel_tag": "HOLD", "metadata": "HOLD", "requires_dist": [],
        "native_objects": [], "elf_objects": [], "top_level_modules": [],
        "member_count": 0, "errors": [],
    }
    if path.is_symlink() or not path.is_file():
        result["errors"].append("WHEEL_NOT_A_REGULAR_FILE")
        result["identity"] = "FAIL"
        return result
    with path.open("rb") as stream:
        prefix = stream.read(100)
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        result["errors"].append("GIT_LFS_POINTER_NOT_HYDRATED")
        result["identity"] = "FAIL"
        return result
    digest, size = file_sha256(path)
    result.update(actual_sha256=digest, actual_bytes=size,
                  expected_sha256=EXPECTED_SHA256, expected_bytes=EXPECTED_BYTES)
    result["identity"] = "PASS" if digest == EXPECTED_SHA256 and size == EXPECTED_BYTES else "FAIL"
    if result["identity"] == "FAIL":
        result["errors"].append("PROTECTED_WHEEL_IDENTITY_MISMATCH")
    result["filename_compliance"] = wheel_filename_compliance(path.name)
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                result["archive_integrity"] = "FAIL"
                result["errors"].append(f"ZIP_CRC_FAILURE:{bad_member}")
                return result
            result["archive_integrity"] = "PASS"
            names = archive.namelist()
            result["member_count"] = sum(not n.endswith("/") for n in names)
            result["member_preview"] = names[:100]
            result["payload_uncompressed_bytes"] = sum(
                info.file_size for info in archive.infolist()
                if not info.is_dir() and ".dist-info/" not in info.filename
            )
            result["python_source_files"] = [
                n for n in names if n.endswith(".py") and ".dist-info/" not in n
            ][:200]
            entry_points_file = f"{dist_info}/entry_points.txt"
            result["entry_points"] = (
                archive.read(entry_points_file).decode("utf-8", errors="replace")
                if entry_points_file in names else ""
            )
            safe, reason = safe_wheel_members(names)
            if not safe:
                result["archive_integrity"] = "FAIL"
                result["errors"].append(reason)
                return result
            dist_infos = sorted({n.split("/", 1)[0] for n in names if ".dist-info/" in n})
            if len(dist_infos) != 1:
                result["metadata"] = "FAIL"
                result["errors"].append("EXPECTED_EXACTLY_ONE_DIST_INFO_DIRECTORY")
                return result
            dist_info = dist_infos[0]
            wheel_meta, metadata_file, record_file = (
                f"{dist_info}/WHEEL", f"{dist_info}/METADATA", f"{dist_info}/RECORD")
            for required in (wheel_meta, metadata_file, record_file):
                if required not in names:
                    result["errors"].append(f"WHEEL_REQUIRED_FILE_MISSING:{required}")
            if result["errors"]:
                result["metadata"] = "FAIL"
                return result
            wheel_text = archive.read(wheel_meta).decode("utf-8", errors="replace")
            tags = [line.split(":", 1)[1].strip() for line in wheel_text.splitlines()
                    if line.startswith("Tag:")]
            result["declared_tags"] = tags
            result["wheel_tag"] = "PASS" if WHEEL_TAG in tags else "FAIL"
            if result["wheel_tag"] == "FAIL":
                result["errors"].append("EXPECTED_MANYLINUX_2_34_X86_64_TAG_NOT_FOUND")
            metadata = Parser().parsestr(
                archive.read(metadata_file).decode("utf-8", errors="replace"))
            result["distribution_name"] = metadata.get("Name")
            result["distribution_version"] = metadata.get("Version")
            result["requires_dist"] = metadata.get_all("Requires-Dist", [])
            result["metadata"] = "PASS" if result["distribution_name"] and result["distribution_version"] else "FAIL"
            if result["metadata"] == "FAIL":
                result["errors"].append("DISTRIBUTION_METADATA_INCOMPLETE")
            top_level_file = f"{dist_info}/top_level.txt"
            if top_level_file in names:
                modules = [line.strip() for line in archive.read(top_level_file).decode(
                    "utf-8", errors="replace").splitlines()
                    if line.strip() and line.strip().isidentifier()]
            else:
                modules = sorted({
                    n.split("/", 1)[0][:-3] if n.endswith(".py") else n.split("/", 1)[0]
                    for n in names if not n.endswith("/") and not n.startswith(dist_info + "/")
                    and not n.startswith("__") and ".data/" not in n
                })
                modules = [m for m in modules if m.isidentifier()]
            result["top_level_modules"] = modules
            record_status, record_errors = verify_record(archive, record_file)
            result["record_integrity"] = record_status
            result["errors"].extend(record_errors)
            result["native_objects"] = [
                n for n in names if not n.endswith("/") and (n.endswith(".so") or ".so." in n)]
            elf_objects = []
            for name in names:
                if name.endswith("/"):
                    continue
                with archive.open(name) as member:
                    if member.read(4) == b"\x7fELF":
                        elf_objects.append(name)
            result["elf_objects"] = elf_objects
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        result["archive_integrity"] = "FAIL"
        result["errors"].append(f"WHEEL_ARCHIVE_ERROR:{type(exc).__name__}:{exc}")
    return result

def check_environment() -> dict:
    os_release = parse_os_release()
    os_ok = (os_release.get("ID", "").lower() == "debian"
             and os_release.get("VERSION_ID", "").split(".", 1)[0] == "13"
             and os_release.get("VERSION_CODENAME", "").lower() == "trixie")
    result = {"distribution": os_release.get("PRETTY_NAME", "UNKNOWN"),
              "id": os_release.get("ID"), "version_id": os_release.get("VERSION_ID"),
              "codename": os_release.get("VERSION_CODENAME"), "architecture": platform.machine(),
              "debian_13_trixie": "PASS" if os_ok else "FAIL", "glibc": None,
              "glibc_requirement": ">=2.34", "glibc_compatibility": "HOLD"}
    libc = run(["getconf", "GNU_LIBC_VERSION"], timeout=20)
    if libc.returncode == 0:
        result["glibc"] = libc.stdout.strip()
        version = parse_version(libc.stdout)
        result["glibc_compatibility"] = "PASS" if version and version >= MIN_GLIBC else "FAIL"
    else:
        result["glibc_compatibility"] = "FAIL"
        result["glibc_error"] = libc.stdout.strip()[:1000]
    if result["architecture"] != "x86_64":
        result["debian_13_trixie"] = "FAIL"
    return result

def check_native_dependencies(wheel: Path, native_names: list[str]) -> dict:
    if not native_names:
        return {"status": "PASS", "objects": 0, "needed": [], "missing": []}
    readelf, ldconfig = shutil.which("readelf"), shutil.which("ldconfig")
    if not readelf or not ldconfig:
        return {"status": "HOLD", "reason": "BINUTILS_OR_LDCONFIG_UNAVAILABLE"}
    system = run([ldconfig, "-p"], timeout=30)
    if system.returncode != 0:
        return {"status": "HOLD", "reason": "LDCONFIG_CACHE_UNAVAILABLE"}
    system_paths = re.findall(r"\s=>\s+(/[^\s]+)", system.stdout)
    system_basenames = {Path(item).name for item in system_paths}
    needed, bundled_sonames = set(), set()
    with tempfile.TemporaryDirectory(prefix="umot-native-audit-") as tmp:
        root = Path(tmp)
        try:
            with zipfile.ZipFile(wheel) as archive:
                for name in native_names:
                    target = root.joinpath(*PurePosixPath(name).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
                    info = run([readelf, "-d", str(target)], timeout=30)
                    if info.returncode != 0:
                        return {"status": "FAIL", "reason": "READELF_FAILED", "object": name}
                    needed.update(re.findall(r"\(NEEDED\).*?\[(.*?)\]", info.stdout))
                    bundled_sonames.update(re.findall(r"\(SONAME\).*?\[(.*?)\]", info.stdout))
        except Exception as exc:
            return {"status": "FAIL", "reason": f"NATIVE_AUDIT_ERROR:{type(exc).__name__}:{exc}"}
    missing = sorted(n for n in needed if n not in system_basenames and n not in bundled_sonames)
    return {"status": "PASS" if not missing else "HOLD", "objects": len(native_names),
            "needed": sorted(needed), "bundled_sonames": sorted(bundled_sonames),
            "missing": missing,
            "reason": None if not missing else "SYSTEM_LIBRARY_REQUIREMENTS_NEED_REVIEW_OR_PROVISIONING"}

def offline_install_test(
    wheel: Path, distribution_name: str | None, distribution_version: str | None,
    top_level_modules: list[str], filename_report: dict,
    wheelhouse: Path, lockfile: Path,
) -> dict:
    if not distribution_name or not distribution_version:
        return {"status": "HOLD", "reason": "DISTRIBUTION_METADATA_UNAVAILABLE"}
    if not wheelhouse.is_dir() or not lockfile.is_file():
        return {"status": "HOLD", "reason": "LOCK_OR_WHEELHOUSE_MISSING"}
    normalized_name = re.sub(r"[-_.]+", "_", distribution_name).lower()
    normalized_version = distribution_version.replace("-", "_")
    alias_name = f"{normalized_name}-{normalized_version}-{WHEEL_TAG}.whl"
    with tempfile.TemporaryDirectory(prefix="umot-offline-install-") as tmp:
        root, venv = Path(tmp), Path(tmp) / "venv"
        install_wheel = wheel if filename_report.get("status") == "PASS" else root / alias_name
        if install_wheel != wheel:
            shutil.copyfile(wheel, install_wheel)
        source_hash, source_size = file_sha256(wheel)
        install_hash, install_size = file_sha256(install_wheel)
        if (source_hash, source_size) != (install_hash, install_size):
            return {"status": "FAIL", "reason": "TEMPORARY_CANONICAL_ALIAS_CONTENT_MISMATCH"}
        created = run([sys.executable, "-m", "venv", str(venv)], timeout=120)
        if created.returncode != 0:
            return {"status": "HOLD", "reason": "VENV_CREATION_FAILED", "output": created.stdout[-2000:]}
        python = venv / "bin" / "python"
        env = os.environ.copy()
        env.update(PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1")
        deps = subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index",
             "--find-links", str(wheelhouse), "--require-hashes", "-r", str(lockfile)],
            check=False, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=900, env=env)
        if deps.returncode != 0:
            return {"status": "FAIL", "reason": "OFFLINE_LOCKED_DEPENDENCY_INSTALL_FAILED",
                    "output": deps.stdout[-6000:]}
        package = subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index",
             "--find-links", str(wheelhouse), "--no-deps", "--no-compile", str(install_wheel)],
            check=False, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=600, env=env)
        if package.returncode != 0:
            return {"status": "FAIL", "reason": "OFFLINE_UMOT_WHEEL_INSTALL_FAILED",
                    "output": package.stdout[-5000:],
                    "install_alias_filename": install_wheel.name,
                    "source_filename_compliance": filename_report.get("status"),
                    "content_identical_alias": True, "source_sha256": source_hash}
        check = run([str(python), "-m", "pip", "check"], timeout=60)
        if check.returncode != 0:
            return {"status": "FAIL", "reason": "OFFLINE_DEPENDENCY_GRAPH_INCONSISTENT",
                    "output": check.stdout[-4000:]}
        metadata = run([
            str(python), "-c",
            "import importlib.metadata as m,sys; d=m.distribution(sys.argv[1]); "
            "print(d.metadata['Name'],d.version)",
            distribution_name], timeout=30)
        if metadata.returncode != 0:
            return {"status": "FAIL", "reason": "INSTALLED_DISTRIBUTION_NOT_DISCOVERABLE",
                    "output": metadata.stdout[-2000:]}
        module_probe = String = (
            "import importlib,inspect,json,pkgutil,sys; "
            "name=sys.argv[1]; m=importlib.import_module(name); failures=[]; "
            "mods=[x.name for x in pkgutil.walk_packages(getattr(m,'__path__',[]),m.__name__+'.')]; "
            "[(lambda n: (importlib.import_module(n)))(n) for n in mods]; "
            "print(json.dumps({'module':name,'file':getattr(m,'__file__',None),"
            "'submodules':mods,'public_names':sorted(n for n in dir(m) if not n.startswith('_'))},"
            "sort_keys=True))"
        )
        import_status, import_output = "HOLD", "TOP_LEVEL_MODULE_MANIFEST_UNAVAILABLE"
        if top_level_modules:
            imported = subprocess.run(
                [str(python), "-c", module_probe, top_level_modules[0]],
                check=False, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=180, env=env)
            import_output = imported.stdout[-6000:]
            if imported.returncode == 0:
                import_status = "PASS"
            elif "ModuleNotFoundError" in imported.stdout:
                import_status = "HOLD"
            else:
                import_status = "FAIL"
        return {
            "status": "PASS", "method": "pip --no-index --find-links --require-hashes",
            "distribution": metadata.stdout.strip(), "pip_check": "PASS",
            "locked_dependency_install": "PASS",
            "lockfile": str(lockfile), "wheelhouse_file_count": len(list(wheelhouse.glob("*.whl"))),
            "install_alias_filename": install_wheel.name,
            "source_filename_compliance": filename_report.get("status"),
            "content_identical_alias": True, "source_sha256": source_hash,
            "module_import_status": import_status, "module_import_output": import_output,
        }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("umot-stage0-report.json"))
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--lockfile", type=Path, default=Path("umot/requirements-offline.lock"))
    args = parser.parse_args()
    report = {"specification": "UMOT_STAGE_0_DEBIAN_13", "protected_wheel": WHEEL_NAME,
              "expected_bytes": EXPECTED_BYTES, "expected_sha256": EXPECTED_SHA256,
              "environment": check_environment()}
    wheel_result = inspect_wheel(args.wheel)
    report["wheel"] = wheel_result
    native = check_native_dependencies(args.wheel, wheel_result.get("elf_objects", [])) if wheel_result.get("archive_integrity") == "PASS" else {"status": "HOLD", "reason": "WHEEL_ARCHIVE_NOT_INSPECTABLE"}
    report["native_dependency_audit"] = native
    install = offline_install_test(args.wheel, wheel_result.get("distribution_name"), wheel_result.get("distribution_version"), wheel_result.get("top_level_modules", []), wheel_result.get("filename_compliance", {}), args.wheelhouse, args.lockfile) if wheel_result.get("archive_integrity") == "PASS" else {"status": "HOLD", "reason": "WHEEL_ARCHIVE_NOT_INSPECTABLE"}
    report["wheel_filename_compliance"] = wheel_result.get("filename_compliance", {"status": "HOLD"})
    report["offline_wheel_install"] = install
    requirements = wheel_result.get("requires_dist", [])
    lock_text = args.lockfile.read_text(encoding="utf-8") if args.lockfile.is_file() else ""
    locked_versions = all(token in lock_text for token in (
        "playwright==1.62.0", "pyee==13.0.1", "greenlet==3.5.6", "typing-extensions==4.16.0"))
    wheelhouse_files = sorted(args.wheelhouse.glob("*.whl")) if args.wheelhouse.is_dir() else []
    expected_wheel_hashes = {
        "playwright-1.62.0-py3-none-manylinux1_x86_64.whl": "ba33bae6a13b3d9d354c751cb618af357d20fe1d57767cbcce52079bbef17ad3",
        "pyee-13.0.1-py3-none-any.whl": "af2f8fede4171ef667dfded53f96e2ed0d6e6bd7ee3bb46437f77e3b57689228",
        "greenlet-3.5.6-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl": "f98e8215e172f567ce80eeaed9107fb4d32b6c44f26983d9b8334658136a205a",
        "typing_extensions-4.16.0-py3-none-any.whl": "481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8",
    }
    wheelhouse_hashes = {}
    for artifact in wheelhouse_files:
        digest, _ = file_sha256(artifact)
        wheelhouse_hashes[artifact.name] = digest
    wheelhouse_integrity = (
        "PASS" if wheelhouse_hashes == expected_wheel_hashes else "FAIL")
    report["dependency_inventory"] = {
        "requires_dist": requirements, "locked": locked_versions,
        "lockfile": str(args.lockfile), "wheelhouse_present": len(wheelhouse_files) == 4,
        "wheelhouse_integrity": wheelhouse_integrity,
        "wheelhouse_artifact_scope": "CI_MATERIALIZED_ARTIFACT_NOT_REPOSITORY_PERSISTENT_STORE",
        "status": "PASS" if locked_versions and wheelhouse_integrity == "PASS" else "HOLD",
        "wheelhouse_files": wheelhouse_hashes,
    }
    report["full_offline_dependency_install"] = (
        "PASS" if install.get("locked_dependency_install") == "PASS" and
        install.get("pip_check") == "PASS" else "FAIL")

    report["reproducible_rebuild"] = {"status": "HOLD", "reason": "SOURCE_REVISION_AND_PINNED_BUILD_RECIPE_NOT_YET_REGISTERED"}
    required = [report["environment"]["debian_13_trixie"], report["environment"]["glibc_compatibility"],
                wheel_result["identity"], wheel_result["archive_integrity"], wheel_result["record_integrity"],
                report["wheel_filename_compliance"]["status"],
                wheel_result["wheel_tag"], wheel_result["metadata"], native["status"], install["status"],
                install.get("module_import_status", "HOLD"),
                report["dependency_inventory"]["status"], report["reproducible_rebuild"]["status"]]
    overall = "FAIL" if "FAIL" in required else ("PASS" if all(x == "PASS" for x in required) else "HOLD")
    report["stage0_status"] = overall
    report["certification"] = "NOT_GRANTED" if overall != "PASS" else "ELIGIBLE_FOR_INDEPENDENT_REVIEW"
    report["network_required_for_this_test"] = False
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return {"PASS": 0, "HOLD": 2, "FAIL": 1}[overall]

if __name__ == "__main__":
    raise SystemExit(main())
