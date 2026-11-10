import hashlib
import json
import pathlib
import tempfile
import unittest

import certify_candidate_squashfs_v1 as cert


class SquashFSFunctionalCertificateTests(unittest.TestCase):
    def prepare(self, base: pathlib.Path):
        image_dir = base / "image"
        target_dir = base / "target"
        independent_dir = base / "independent"
        s32_dir = base / "s32"
        stable_dir = base / "stable"
        for folder in (image_dir, target_dir, independent_dir, s32_dir, stable_dir):
            folder.mkdir(parents=True)

        image = image_dir / "LUNITA.squashfs"
        image.write_bytes(b"verified squashfs candidate bytes")
        image_sha = cert.sha256_file(image)
        checksum = image_dir / "LUNITA.squashfs.sha256"
        checksum.write_text(f"{image_sha}  {image.name}\n", encoding="ascii")

        manifest = base / "LUNITA_V1_8_CANDIDATE_FREEZE.json"
        manifest.write_text(json.dumps({
            "schema": "LUNITA_CANDIDATE_FREEZE/1.0",
            "candidate_id": cert.CANDIDATE_ID,
            "version": cert.VERSION,
            "freeze_status": "FROZEN_CANDIDATE_NOT_CERTIFIED",
            "preserved_baseline": {
                "frozen_g06_mutated": False,
                "canonical_g08_bindings_mutated": False,
                "legacy_v1_7_launcher_replaced": False,
            },
        }), encoding="utf-8")
        manifest_sha = cert.sha256_file(manifest)

        target = target_dir / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json"
        target.write_text(json.dumps({
            "schema": cert.TARGET_SCHEMA,
            "status": cert.PASS_TARGET,
            "candidate_id": cert.CANDIDATE_ID,
            "certification": "NOT_GRANTED",
            "canonical_g06_certification": "NOT_GRANTED",
            "canonical_g08_binding_mutation": False,
        }), encoding="utf-8")
        target_sha = cert.sha256_file(target)

        independent = independent_dir / "BETA_INDEPENDENT_VALIDATION.json"
        required = {
            "candidate_manifest_identity_sha256",
            "runtime_report_and_launcher_identity",
            "target_v1_8_runtime_acceptance_e01_e15_int8",
            "candidate_rootfs_inventory_and_dependency_manifest",
            "jasp_packaged_fixture_nonregression",
        }
        checks = {name: {"status": "PASS", "returncode": 0} for name in required}
        checks["candidate_manifest_identity_sha256"]["sha256"] = manifest_sha
        checks["target_v1_8_runtime_acceptance_e01_e15_int8"].update({
            "receipt_path": str(target), "receipt_sha256": target_sha,
        })
        independent.write_text(json.dumps({
            "schema": cert.INDEPENDENT_SCHEMA,
            "status": "PASS_INDEPENDENT_VALIDATION",
            "candidate_id": cert.CANDIDATE_ID,
            "certification_profile": "V1_8_DIRECT",
            "candidate_manifest_sha256": manifest_sha,
            "runtime_report_path": str(target),
            "runtime_report_sha256": target_sha,
            "checks": checks,
            "frozen_g06_mutated": False,
            "canonical_g08_bindings_mutated": False,
        }), encoding="utf-8")
        independent_sha = cert.sha256_file(independent)

        package_path = image_dir / "LUNITA_SQUASHFS_PACKAGE_RECEIPT.json"
        package_path.write_text(json.dumps({
            "schema": cert.PACKAGE_SCHEMA,
            "status": cert.PASS_PACKAGE,
            "candidate_id": cert.CANDIDATE_ID,
            "version": cert.VERSION,
            "image_name": image.name,
            "image_sha256": image_sha,
            "image_bytes": image.stat().st_size,
            "source_rootfs_manifest_sha256": hashlib.sha256(b"rootfs-manifest").hexdigest(),
            "roundtrip_manifest_match": True,
            "source_rootfs_unchanged": True,
            "target_runtime_receipt_path": str(target),
            "target_runtime_receipt_sha256": target_sha,
            "target_runtime_status": cert.PASS_TARGET,
            "certification": "NOT_GRANTED",
            "g23": "NOT_GRANTED",
            "g24": "NOT_GRANTED",
            "s32": "NOT_ISSUED",
            "mksquashfs": "PASS",
            "unsquashfs_superblock": "PASS",
            "unsquashfs_roundtrip": "PASS",
        }), encoding="utf-8")

        s32 = s32_dir / f"S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT_{independent_sha[:16]}.json"
        s32.write_text(json.dumps({
            "schema": cert.S32_SCHEMA,
            "status": cert.PASS_S32,
            "candidate_id": cert.CANDIDATE_ID,
            "runtime_report_path": str(target),
            "runtime_report_sha256": target_sha,
            "independent_report_path": str(independent),
            "independent_report_sha256": independent_sha,
            "evidence": {
                "independent_validation": "PASS",
                "independent_report_path": str(independent),
                "independent_report_sha256": independent_sha,
                "target_runtime_receipt_path": str(target),
                "target_runtime_receipt_sha256": target_sha,
                "candidate_manifest_sha256": manifest_sha,
            },
            "canonical_g06_certification": "NOT_GRANTED",
            "frozen_g06_mutated": False,
            "canonical_g08_bindings_mutated": False,
            "g23_status": "NOT_GRANTED",
            "g24_status": "NOT_GRANTED",
        }), encoding="utf-8")
        s32_sha = cert.sha256_file(s32)

        stable = stable_dir / "release_test.json"
        stable.write_text(json.dumps({
            "schema": cert.STABLE_SCHEMA,
            "status": cert.PASS_STABLE,
            "candidate_id": cert.CANDIDATE_ID,
            "version": cert.VERSION,
            "certification": "GRANTED_FOR_VERSIONED_CANDIDATE",
            "independent_report_sha256": independent_sha,
            "runtime_report_sha256": target_sha,
            "s32_receipt": {"path": str(s32), "sha256": s32_sha},
            "frozen_g06_mutated": False,
            "canonical_g08_bindings_mutated": False,
        }), encoding="utf-8")

        return {
            "image": image,
            "checksum": checksum,
            "package": package_path,
            "target_dir": target_dir,
            "independent": independent,
            "manifest": manifest,
            "s32_dir": s32_dir,
            "stable_dir": stable_dir,
            "target_sha": target_sha,
            "independent_sha": independent_sha,
        }

    def test_certificate_binds_exact_image_and_all_required_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepare(pathlib.Path(tmp))
            result = cert.build_certificate(
                paths["image"], paths["checksum"], paths["package"], paths["target_dir"],
                paths["independent"], paths["manifest"], paths["s32_dir"], paths["stable_dir"],
            )
        self.assertEqual("CERTIFIED_FUNCTIONAL_CANDIDATE", result["status"])
        self.assertEqual(cert.sha256_file(paths["image"]), result["artifact"]["sha256"])
        self.assertEqual(paths["target_sha"], result["target_runtime_receipt"]["sha256"])
        self.assertEqual(paths["independent_sha"], result["independent_validation"]["sha256"])
        self.assertEqual("NOT_GRANTED", result["g23"])
        self.assertEqual("NOT_GRANTED", result["g24"])
        self.assertFalse(result["automatic_canonical_promotion"])

    def test_missing_s32_receipt_blocks_functional_certificate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepare(pathlib.Path(tmp))
            for item in paths["s32_dir"].glob("*.json"):
                item.unlink()
            with self.assertRaises(cert.CertificationError):
                cert.build_certificate(
                    paths["image"], paths["checksum"], paths["package"], paths["target_dir"],
                    paths["independent"], paths["manifest"], paths["s32_dir"], paths["stable_dir"],
                )

    def test_image_tampering_after_package_receipt_blocks_certificate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepare(pathlib.Path(tmp))
            paths["image"].write_bytes(b"tampered after package receipt")
            with self.assertRaises(cert.CertificationError):
                cert.build_certificate(
                    paths["image"], paths["checksum"], paths["package"], paths["target_dir"],
                    paths["independent"], paths["manifest"], paths["s32_dir"], paths["stable_dir"],
                )


if __name__ == "__main__":
    unittest.main()
