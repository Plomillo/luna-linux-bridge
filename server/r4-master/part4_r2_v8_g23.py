#!/usr/bin/env python3
"""Independent digest-bound G23 checks for V8 cleanup and migration authorization."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib

REPO = pathlib.Path("server/r4-master")
EXPECTED_MANIFEST = "99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"
SOURCE_RUN = 36682665542
EXPECTED_RECORDS = 498092
EXPECTED_BYTES = 200490852057
TEMP_REQUIRED = EXPECTED_BYTES + 1000000000
GEOMETRY = {
    "p3_start": 567296, "p3_original_size": 853844280,
    "p3_shrunk_size": 446629888, "p3_new_end": 447197183,
    "temp_start": 447199232, "temp_end": 854409528,
    "p3_final_size": 853842233, "p3_final_end": 854409528
}

def h(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def write_result(out: pathlib.Path, stage: str, checks: dict, additional: dict) -> None:
    ok = all(checks.values())
    result = {
        "schema": "LOUKSNA_R4_PART4_R2_V8_G23/1.0",
        "stage": stage,
        "status": "PASS" if ok else "HOLD",
        "checks": checks,
        "g24_allowed": ok,
        "repair_allowed": False,
        "validated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        **additional,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not ok:
        raise SystemExit(23)

def pre(probe: pathlib.Path, failure: pathlib.Path, out: pathlib.Path) -> None:
    pp = probe / "CLEANUP_PLAN_V8.json"
    p, v, x, ps, ta, fail = map(load, (
        pp, probe / "SOURCE_VERIFY.json", probe / "SOURCE_XATTR.json",
        probe / "SOURCE_POSIX.json", probe / "TEMP_ROOT_AUDIT.json", failure
    ))
    migrate = REPO / "part4_r2_storage_resume_after_v7_capacity_fail_closed_v8.sh"
    cleanup = REPO / "part4_r2_temp_cleanup_v8.sh"
    sx, sc = migrate.read_text(), cleanup.read_text()
    checks = {
        "source_failure_provenance": (
            fail.get("source_run") == SOURCE_RUN
            and fail.get("status") == "FAIL_CLOSED_HOLD"
            and fail.get("bug_class") == "V7_TEMP_FREE_CAPACITY_PRECHECK_WITH_PARTIAL_COPY"
        ),
        "source_run": p.get("source_failure_run") == SOURCE_RUN,
        "plan_status": p.get("status") == "PASS",
        "stage": p.get("stage") == "P3_SHRUNK_TEMP_EXT4_PARTIAL_V6_V7_CAPACITY_HOLD",
        "manifest": p.get("manifest_sha256") == EXPECTED_MANIFEST,
        "source_tree": (
            v.get("status") == "PASS" and v.get("mismatch_count") == 0
            and v.get("seen_records") == EXPECTED_RECORDS
            and v.get("regular_file_bytes") == EXPECTED_BYTES
            and v.get("manifest_sha256") == EXPECTED_MANIFEST
            and p.get("source_verify_sha256") == h(probe / "SOURCE_VERIFY.json")
        ),
        "source_xattr": (
            x.get("status") == "PASS" and x.get("unexpected_count") == 0
            and x.get("records_scanned") == EXPECTED_RECORDS
            and p.get("source_xattr_sha256") == h(probe / "SOURCE_XATTR.json")
        ),
        "posix_source": (
            ps.get("status") == "PASS" and ps.get("records") == EXPECTED_RECORDS
            and ps.get("directory_nlink_normalized") is True
            and p.get("source_posix_sha256") == h(probe / "SOURCE_POSIX.json")
            and p.get("source_posix_fingerprint") == ps.get("fingerprint_sha256")
        ),
        "temporary_identity": (
            p.get("temporary", {}).get("fstype") == "ext4"
            and p.get("temporary", {}).get("label") == "LOUKSNA_TMP"
            and bool(p.get("temporary", {}).get("uuid"))
            and p.get("temporary", {}).get("size_sectors") == 407210297
        ),
        "geometry": all(p.get("geometry", {}).get(k) == v for k,v in GEOMETRY.items()),
        "temp_root_safe": (
            ta.get("status") == "PASS"
            and ta.get("top_level_names") in ([],["lost+found"],["PROYECTOS"],["PROYECTOS","lost+found"])
            and ta.get("partial_is_real_directory") is True
            and ta.get("partial_present") is p.get("partial_present")
            and p.get("temp_root_audit_sha256") == h(probe / "TEMP_ROOT_AUDIT.json")
        ),
        "script_digests": (
            p.get("cleanup_script_sha256") == h(cleanup)
            and p.get("migration_script_sha256") == h(migrate)
        ),
        "cleanup_scoped": (
            "rm -rf --one-file-system -- " in sc
            and '"$TMPM/PROYECTOS"' in sc
            and "NESTED_MOUNT_PRESENT" in sc
            and "P3_UUID_DRIFT" in sc
            and "mkfs.ext4" not in sc
            and "parted -s" not in sc
        ),
        "safe_migration": (
            sx.count("-aHA --no-xattrs --delete --numeric-ids") == 2
            and "-aHAX --delete --numeric-ids" not in sx
            and "POSIX_TEMP_PREREFORMAT.json" in sx
            and sx.index("POSIX_TEMP_PREREFORMAT.json") < sx.index("sudo -n mkfs.ext4")
            and sx.count("resize_partition_sfdisk(){") == 1
            and "TEMP_NOT_CLEAN" in sx
        ),
        "cleanup_scope": p.get("cleanup_scope") == "TEMP_EXT4_PROYECTOS_PARTIAL_ONLY" and p.get("p3_mutation_authorized") is False,
        "required_capacity": p.get("required_after_cleanup_bytes") == TEMP_REQUIRED and p.get("required_after_cleanup_inodes") == 600000,
        "rollback": p.get("rollback") == "P3_SHRUNK_NTFS_IS_SOURCE_OF_TRUTH",
    }
    write_result(out, "PRECLEAN", checks, {
        "plan_sha256": h(pp), "source_verify_sha256": h(probe / "SOURCE_VERIFY.json"),
        "source_posix_sha256": h(probe / "SOURCE_POSIX.json"),
        "xattr_inventory_sha256": h(probe / "SOURCE_XATTR.json"),
        "cleanup_script_sha256": h(cleanup), "migration_script_sha256": h(migrate),
        "failure_evidence_sha256": h(failure)
    })

def post(probe: pathlib.Path, clean: pathlib.Path, g24clean: pathlib.Path, out: pathlib.Path) -> None:
    pp = probe / "CLEANUP_PLAN_V8.json"
    rp, mp = clean / "CLEANUP_RESULT_V8.json", clean / "MIGRATION_PLAN_V8.json"
    p, r, m, cert = map(load, (pp,rp,mp,g24clean))
    migrator = REPO / "part4_r2_storage_resume_after_v7_capacity_fail_closed_v8.sh"
    post_capacity = r.get("after", {})
    checks = {
        "cleanup_certificate_bound": (
            cert.get("status") == "PASS"
            and cert.get("scope") == "TEMP_EXT4_PROYECTOS_PARTIAL_ONLY"
            and cert.get("plan_sha256") == h(pp)
            and cert.get("p3_mutation_authorized") is False
        ),
        "cleanup_status_and_scope": r.get("status") == "PASS" and r.get("scope") == "TEMP_EXT4_PROYECTOS_PARTIAL_ONLY",
        "cleanup_plan_bound": r.get("source_plan_sha256") == h(pp),
        "partition_unchanged": (
            r.get("pre_sfdisk_sha256") == h(clean / "PARTITION_TABLE_PRECLEAN.sfdisk")
            and r.get("post_sfdisk_sha256") == h(clean / "PARTITION_TABLE_POSTCLEAN.sfdisk")
            and (clean / "PARTITION_TABLE_PRECLEAN.sfdisk").read_bytes() == (clean / "PARTITION_TABLE_POSTCLEAN.sfdisk").read_bytes()
            and h(clean / "PARTITION_TABLE_PRECLEAN.sfdisk") == p.get("partition_checkpoint_sha256")
        ),
        "p3_preserved": r.get("p3_preserved_ntfs") is True and r.get("p3_reformatted") is False and r.get("p3_old_uuid") == "F2848A148489DC0B",
        "temp_identity": (
            r.get("temp_device") == p.get("temporary", {}).get("device")
            and r.get("temp_uuid") == p.get("temporary", {}).get("uuid")
            and r.get("temporary_unmounted") is True
        ),
        "no_foreign_files": post_capacity.get("top_level") == ["lost+found"],
        "free_bytes": post_capacity.get("available_bytes", -1) >= TEMP_REQUIRED,
        "free_inodes": post_capacity.get("available_inodes", -1) >= 600000,
        "same_total": r.get("before", {}).get("total_bytes") == post_capacity.get("total_bytes"),
        "migration_plan": (
            m.get("status") == "PASS"
            and m.get("stage") == "P3_SHRUNK_TEMP_EXT4_CLEANED_V8_PRECOPY"
            and m.get("source_failure_run") == SOURCE_RUN
            and m.get("script_sha256") == h(migrator)
            and m.get("cleanup_report_sha256") == h(rp)
            and m.get("cleanup_plan_sha256") == h(pp)
        ),
        "migration_source_bound": (
            m.get("source_posix_fingerprint") == p.get("source_posix_fingerprint")
            and m.get("source_verify_sha256") == p.get("source_verify_sha256")
            and m.get("manifest_sha256") == EXPECTED_MANIFEST
        ),
        "migration_geometry": all(m.get("geometry", {}).get(k) == v for k,v in GEOMETRY.items()),
        "migration_mount_state": m.get("preexisting_mounts",{}).get("temp") == "",
        "rollback": m.get("rollback_contract",{}).get("before_p3_reformat") == "SHRUNK_NTFS_P3_REMAINS_SOURCE_OF_TRUTH",
        "migrator_digest": p.get("migration_script_sha256") == h(migrator),
    }
    write_result(out, "POSTCLEAN_MIGRATION_AUTHORIZATION", checks, {
        "migration_plan_sha256": h(mp), "cleanup_report_sha256": h(rp),
        "cleanup_g24_sha256": h(g24clean), "migration_script_sha256": h(migrator),
        "source_verify_sha256": p["source_verify_sha256"],
        "source_posix_sha256": p["source_posix_sha256"]
    })

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="stage",required=True)
    x=sub.add_parser("pre")
    x.add_argument("--probe",type=pathlib.Path,required=True)
    x.add_argument("--failure",type=pathlib.Path,required=True)
    x.add_argument("--out",type=pathlib.Path,required=True)
    y=sub.add_parser("post")
    y.add_argument("--probe",type=pathlib.Path,required=True)
    y.add_argument("--cleanup",type=pathlib.Path,required=True)
    y.add_argument("--cleanup-cert",type=pathlib.Path,required=True)
    y.add_argument("--out",type=pathlib.Path,required=True)
    a=parser.parse_args()
    if a.stage=="pre": pre(a.probe,a.failure,a.out)
    else: post(a.probe,a.cleanup,a.cleanup_cert,a.out)
if __name__=="__main__":
    main()
