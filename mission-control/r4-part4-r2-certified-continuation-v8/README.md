# PART4-R2 V8: governed recovery after V7 free-capacity HOLD

Source: V7 run 36682665542, commit 6b0cb7e3804550618b761bfd47345b66733450a1.
Observed failure: HOLD:TEMP_BYTES_TOO_SMALL (exit 20), before V7 rsync and before P3 formatting.
Frozen PROYECTOS inventory: 498092 records, 200490852057 regular-file bytes, 0 mismatches.
Manifest SHA-256: 99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e.
V7 xattr inventory: five paths with reserved WSL NTFS xattrs; zero unknown xattrs.

## Boundary and sequence

1. Run read-only physical probe and full SHA-256 manifest + xattr + POSIX inventory; prove temp is precisely known ext4 with no foreign top-level entry or nested mount.
2. Independent G23 validates the exact cleanup script, live probe, source evidence, geometry and rollback.
3. G24 issues cleanup-only scope. It explicitly forbids any P3 mutation.
4. Cleanup verifies the same UUID, geometry, mount binding and root entries; removes only temporary ext4/PROYECTOS partial with --one-file-system; unmounts and measures *actual* full free bytes/inodes. STOP if 201490852057 free bytes or 600000 free inodes is not available.
5. Independent post-clean G23 validates source/plan/digests, before/after partition checkpoints and actual free capacity.
6. New G24 binds post-clean migration plan, cleanup artifact and script SHA. P3 formatting is conditional upon verified temporary content *and* normalized POSIX fingerprint.
7. Migrate source P3 NTFS to clean temp via rsync -aHA --no-xattrs --delete --numeric-ids; verify manifest + POSIX twice before touching P3. After verified temp, format and migrate P3; verify again, retire temp, expand P3 using restored and guarded resize_partition_sfdisk.
8. Existing downstream migration G23/G24, P2/P4 retirement G23/G24 and final merge/postboot chain remain ordered and gated; no authorization is inherited from older versions.

No PASS is claimed by this document. All operational and certification status must be read from this run's live GitHub jobs, step logs and digest-bearing artifacts.

## Failure handling

Any unexpected mount, P3 UUID/NTFS/geometry drift, foreign temporary data, unknown xattr, insufficient actual clean capacity, invalid scripts, mismatch in source/destination content or POSIX metadata, or stale certificate produces HOLD before subsequent authorized operations. If failure occurs after an irreversible boundary, preserve the latest independently verified temp/P3 copy and create a fresh forensic continuation rather than assuming the original NTFS remains available.
