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

        rootfs = base / "packaged-rootfs"
        (rootfs / "etc").mkdir(parents=True)
        (rootfs / "etc" / "os-release").write_text("NAME=Test\n", encoding="utf-8")
        rootfs_manifest = cert.canonical_rootfs_tree_manifest(rootfs)

        independent = independent_dir / "BETA_INDEPENDENT_VALIDATION.json"
        required = {
            "candidate_manifest_identity_sha256",
            "runtime_report_and_launcher_identity",
            "target_v1_8_runtime_acceptance_e01_e15_int8",
            "candidate_rootfs_inventory_and_dependency_manifest",
            "jasp_packaged_fixture_nonregression",
            "squashfs_rootfs_postvalidation_manifest_closure",
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
            "source_rootfs": str(rootfs),
            "source_rootfs_manifest_sha256": rootfs_manifest["entries_sha256"],
            "source_rootfs_entry_count": rootfs_manifest["entry_count"],
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
        package_sha = cert.sha256_file(package_path)
        packager_path = pathlib.Path(cert.__file__).resolve().parent / "package_candidate_squashfs_v1.py"
        closure_receipt = independent_dir / "rootfs_package_manifest_closure.json"
        closure_payload = {
            "schema": "LUNITA_POSTVALIDATION_ROOTFS_PACKAGE_MANIFEST_CLOSURE/1.0",
            "candidate_id": cert.CANDIDATE_ID,
            "status": "PASS",
            "rootfs_path": str(rootfs),
            "package_receipt_path": str(package_path),
            "package_receipt_sha256": package_sha,
            "packager_source_path": str(packager_path),
            "packager_source_sha256": cert.sha256_file(packager_path),
            "package_source_rootfs_manifest_sha256": rootfs_manifest["entries_sha256"],
            "observed_post_validation_rootfs_manifest_sha256": rootfs_manifest["entries_sha256"],
            "package_source_rootfs_entry_count": rootfs_manifest["entry_count"],
            "observed_post_validation_rootfs_entry_count": rootfs_manifest["entry_count"],
            "same_canonical_algorithm": True,
            "exact_manifest_equality": True,
        }
        closure_receipt.write_text(json.dumps(closure_payload), encoding="utf-8")
        closure_sha = cert.sha256_file(closure_receipt)
        checks["squashfs_rootfs_postvalidation_manifest_closure"] = {
            "status": "PASS", "returncode": 0,
            "rootfs_path": str(rootfs),
            "package_source_rootfs_manifest_sha256": rootfs_manifest["entries_sha256"],
            "observed_post_validation_rootfs_manifest_sha256": rootfs_manifest["entries_sha256"],
            "package_source_rootfs_entry_count": rootfs_manifest["entry_count"],
            "observed_post_validation_rootfs_entry_count": rootfs_manifest["entry_count"],
            "package_receipt_path": str(package_path),
            "package_receipt_sha256": package_sha,
            "packager_source_path": str(packager_path),
            "packager_source_sha256": cert.sha256_file(packager_path),
            "manifest_closure_receipt_path": str(closure_receipt),
            "manifest_closure_receipt_sha256": closure_sha,
            "same_canonical_algorithm": True,
            "exact_manifest_equality": True,
            "evidence": {
                str(closure_receipt): closure_sha,
                str(package_path): package_sha,
                str(packager_path): cert.sha256_file(packager_path),
            },
        }
        checksum_sha = cert.sha256_file(checksum)
        independent_data = json.loads(independent.read_text(encoding="utf-8"))
        independent_data["checks"]["squashfs_rootfs_postvalidation_manifest_closure"] = checks[
            "squashfs_rootfs_postvalidation_manifest_closure"
        ]
        image_binding = {
            "status": "PASS", "returncode": 0,
            "image_path": str(image), "image_sha256": image_sha, "image_bytes": image.stat().st_size,
            "checksum_path": str(checksum), "checksum_sha256": checksum_sha,
            "package_receipt_path": str(package_path), "package_receipt_sha256": package_sha,
            "candidate_manifest_path": str(manifest), "candidate_manifest_sha256": manifest_sha,
            "evidence": {str(image): image_sha, str(checksum): checksum_sha,
                         str(package_path): package_sha, str(manifest): manifest_sha},
        }
        independent_data["checks"]["squashfs_image_and_package_binding"] = image_binding
        independent_data.update({
            "squashfs_image_path": str(image), "squashfs_image_sha256": image_sha,
            "squashfs_image_bytes": image.stat().st_size,
            "squashfs_checksum_path": str(checksum), "squashfs_checksum_sha256": checksum_sha,
            "squashfs_package_receipt_path": str(package_path),
            "squashfs_package_receipt_sha256": package_sha,
        })
        independent.write_text(json.dumps(independent_data), encoding="utf-8")
        independent_sha = cert.sha256_file(independent)

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
                "squashfs_image_sha256": image_sha,
                "squashfs_image_bytes": image.stat().st_size,
                "squashfs_checksum_sha256": checksum_sha,
                "squashfs_package_receipt_sha256": package_sha,
            },
            "candidate_manifest_sha256": manifest_sha,
            "squashfs_image_sha256": image_sha,
            "squashfs_image_bytes": image.stat().st_size,
            "squashfs_checksum_sha256": checksum_sha,
            "squashfs_package_receipt_sha256": package_sha,
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
            "candidate_manifest_sha256": manifest_sha,
            "squashfs_image_sha256": image_sha,
            "squashfs_image_bytes": image.stat().st_size,
            "squashfs_checksum_sha256": checksum_sha,
            "squashfs_package_receipt_sha256": package_sha,
            "s32_receipt": {"path": str(s32), "sha256": s32_sha},
            "frozen_g06_mutated": False,
            "canonical_g08_bindings_mutated": False,
        }), encoding="utf-8")

        return {
            "image": image,
            "rootfs": rootfs,
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
            image_sha = cert.sha256_file(paths["image"])
            result = cert.build_certificate(
                paths["image"], paths["checksum"], paths["package"], paths["target_dir"],
                paths["independent"], paths["manifest"], paths["s32_dir"], paths["stable_dir"],
            )
            self.assertEqual("CERTIFIED_FUNCTIONAL_CANDIDATE", result["status"])
            self.assertEqual(image_sha, result["artifact"]["sha256"])
            self.assertEqual(paths["target_sha"], result["target_runtime_receipt"]["sha256"])
            self.assertEqual(paths["independent_sha"], result["independent_validation"]["sha256"])
            self.assertEqual("NOT_GRANTED", result["g23"])
            self.assertEqual("NOT_GRANTED", result["g24"])
            self.assertFalse(result["automatic_canonical_promotion"])

    def test_s32_receipt_with_other_image_or_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepare(pathlib.Path(tmp))
            receipt_path = next(paths["s32_dir"].glob("S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT_*.json"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["evidence"]["squashfs_image_sha256"] = "f" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(cert.CertificationError, "No S32 receipt is bound"):
                cert.build_certificate(
                    paths["image"], paths["checksum"], paths["package"], paths["target_dir"],
                    paths["independent"], paths["manifest"], paths["s32_dir"], paths["stable_dir"],
                )

    def test_stable_release_with_other_image_or_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepare(pathlib.Path(tmp))
            stable_path = next(paths["stable_dir"].glob("release_*.json"))
            stable = json.loads(stable_path.read_text(encoding="utf-8"))
            stable["candidate_manifest_sha256"] = "e" * 64
            stable_path.write_text(json.dumps(stable), encoding="utf-8")
            with self.assertRaisesRegex(cert.CertificationError, "No stable-release receipt is bound"):
                cert.build_certificate(
                    paths["image"], paths["checksum"], paths["package"], paths["target_dir"],
                    paths["independent"], paths["manifest"], paths["s32_dir"], paths["stable_dir"],
                )

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

    def test_postvalidation_rootfs_mutation_blocks_functional_certificate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepare(pathlib.Path(tmp))
            (paths["rootfs"] / "etc" / "os-release").write_text("NAME=Mutated\n", encoding="utf-8")
            with self.assertRaisesRegex(cert.CertificationError, "Live post-validation rootfs no longer equals packaged canonical manifest"):
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
