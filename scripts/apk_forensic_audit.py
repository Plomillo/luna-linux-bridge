#!/usr/bin/env python3
"""Read-only static inventory for one Android APK. Never installs or executes the APK."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

def safe_call(obj, method: str):
    try:
        value = getattr(obj, method)()
        if isinstance(value, (tuple, set)):
            return list(value)
        return value
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{str(exc)[:160]}"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    apk_path = args.apk.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not apk_path.is_file() or apk_path.stat().st_size == 0:
        raise SystemExit(f"APK_MISSING_OR_EMPTY={apk_path}")

    digest = hashlib.sha256()
    with apk_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    inventory: dict = {
        "file": apk_path.name,
        "size_bytes": apk_path.stat().st_size,
        "sha256": digest.hexdigest(),
    }

    with zipfile.ZipFile(apk_path) as archive:
        infos = archive.infolist()
        bad_entry = archive.testzip()
        names = [item.filename for item in infos]
        duplicates = sorted(name for name, count in collections.Counter(names).items() if count > 1)
        dex_files = sorted(
            name for name in names if re.fullmatch(r"classes(?:[2-9][0-9]*)?\.dex|classes\.dex", name)
        )
        native = [item for item in infos if item.filename.startswith("lib/") and item.filename.endswith(".so")]
        abi_counts = collections.Counter(item.filename.split("/")[1] for item in native if len(item.filename.split("/")) > 2)
        assets = [item for item in infos if item.filename.startswith("assets/")]
        model_suffixes = (".gguf", ".onnx", ".tflite", ".safetensors", ".pt", ".pth", ".pb", ".model")
        model_payloads = [
            {"path": item.filename, "size_bytes": item.file_size}
            for item in infos
            if item.filename.lower().endswith(model_suffixes)
        ]
        inventory.update({
            "zip_integrity": "PASS" if bad_entry is None else f"FAIL:{bad_entry}",
            "zip_entry_count": len(infos),
            "duplicate_entry_names": duplicates,
            "android_manifest_present": "AndroidManifest.xml" in names,
            "resources_arsc_present": "resources.arsc" in names,
            "dex_files": [{"path": item.filename, "size_bytes": item.file_size} for item in infos if item.filename in dex_files],
            "native_library_count": len(native),
            "native_libraries_by_abi": dict(sorted(abi_counts.items())),
            "native_libraries": [{"path": item.filename, "size_bytes": item.file_size} for item in native],
            "asset_total_bytes": sum(item.file_size for item in assets),
            "largest_entries": [
                {"path": item.filename, "size_bytes": item.file_size}
                for item in sorted(infos, key=lambda value: value.file_size, reverse=True)[:30]
            ],
            "embedded_model_payloads": model_payloads,
            "encrypted_zip_entries": [item.filename for item in infos if item.flag_bits & 0x1],
        })
        if bad_entry is not None:
            raise SystemExit(f"ZIP_INTEGRITY_FAILURE={bad_entry}")

    # Androguard parses the manifest and DEX tables without executing application code.
    from androguard.core.apk import APK
    from androguard.core.dex import DEX

    apk = APK(str(apk_path))
    root = apk.get_android_manifest_xml()
    root_attrs = {}
    app_attrs = {}
    components = {}
    manifest_permissions = []
    manifest_features = []
    if root is not None:
        root_attrs = {key.rsplit("}", 1)[-1]: value for key, value in root.attrib.items()}
        application = root.find("application")
        if application is not None:
            app_attrs = {key.rsplit("}", 1)[-1]: value for key, value in application.attrib.items()}
        for permission_tag in ("uses-permission", "uses-permission-sdk-23", "uses-permission-sdk-m"):
            for element in root.findall(permission_tag):
                value = element.attrib.get(ANDROID_NS + "name")
                if value:
                    manifest_permissions.append(value)
        for element in root.findall("uses-feature"):
            manifest_features.append({
                "name": element.attrib.get(ANDROID_NS + "name"),
                "required": element.attrib.get(ANDROID_NS + "required", "true"),
                "glEsVersion": element.attrib.get(ANDROID_NS + "glEsVersion"),
            })
        for kind in ("activity", "activity-alias", "service", "receiver", "provider"):
            rows = []
            for element in root.findall(".//application/" + kind):
                attrs = {key.rsplit("}", 1)[-1]: value for key, value in element.attrib.items()}
                actions = [
                    child.attrib.get(ANDROID_NS + "name")
                    for child in element.findall("./intent-filter/action")
                    if child.attrib.get(ANDROID_NS + "name")
                ]
                categories = [
                    child.attrib.get(ANDROID_NS + "name")
                    for child in element.findall("./intent-filter/category")
                    if child.attrib.get(ANDROID_NS + "name")
                ]
                rows.append({"attributes": attrs, "actions": actions, "categories": categories})
            components[kind] = rows

    metadata_methods = (
        "get_package", "get_app_name", "get_androidversion_name", "get_androidversion_code",
        "get_min_sdk_version", "get_target_sdk_version", "get_effective_target_sdk_version",
        "get_max_sdk_version", "get_main_activity", "get_permissions", "get_activities",
        "get_services", "get_receivers", "get_providers", "get_libraries", "get_features",
    )
    metadata = {method: safe_call(apk, method) for method in metadata_methods}

    dex_names = list(apk.get_dex_names())
    dex_blobs = list(apk.get_all_dex())
    class_count = 0
    namespace_counts = collections.Counter()
    interesting_classes = set()
    matched_indicators = collections.Counter()
    url_hosts = set()

    indicator_patterns = {
        "boot_completed": re.compile(r"BOOT_COMPLETED|LOCKED_BOOT_COMPLETED", re.I),
        "foreground_service": re.compile(r"startForeground|FOREGROUND_SERVICE", re.I),
        "scheduled_work": re.compile(r"WorkManager|JobScheduler|AlarmManager|androidx\.work", re.I),
        "push_messaging": re.compile(r"FirebaseMessagingService|firebase.?messaging", re.I),
        "accessibility": re.compile(r"AccessibilityService|BIND_ACCESSIBILITY_SERVICE", re.I),
        "vpn": re.compile(r"VpnService|BIND_VPN_SERVICE", re.I),
        "device_admin": re.compile(r"DeviceAdminReceiver|BIND_DEVICE_ADMIN", re.I),
        "dynamic_code_loading": re.compile(r"DexClassLoader|InMemoryDexClassLoader|PathClassLoader|loadDex", re.I),
        "process_execution": re.compile(r"Runtime;->exec|ProcessBuilder", re.I),
        "microphone_capture": re.compile(r"MediaRecorder|AudioRecord", re.I),
        "sms_telephony": re.compile(r"SmsManager|TelephonyManager|READ_SMS|SEND_SMS", re.I),
        "screen_capture": re.compile(r"MediaProjection|createScreenCaptureIntent", re.I),
        "wake_lock": re.compile(r"WakeLock|WAKE_LOCK", re.I),
        "overlay": re.compile(r"SYSTEM_ALERT_WINDOW|TYPE_APPLICATION_OVERLAY", re.I),
        "package_installation": re.compile(r"REQUEST_INSTALL_PACKAGES|PackageInstaller", re.I),
        "cleartext_network": re.compile(r"http://", re.I),
        "webview_javascript": re.compile(r"setJavaScriptEnabled|addJavascriptInterface", re.I),
    }

    for index, raw_dex in enumerate(dex_blobs):
        dex = DEX(raw_dex)
        for clazz in dex.get_classes():
            class_count += 1
            class_name = clazz.get_name()
            parts = class_name.strip("L;").split("/")
            if parts:
                namespace_counts["/".join(parts[: min(3, len(parts) - 1 or 1)])] += 1
            if any(token in class_name.lower() for token in (
                "service", "worker", "job", "alarm", "receiver", "boot", "firebase",
                "push", "foreground", "notification", "sync", "accessibility",
                "vpn", "inputmethod", "wake", "deviceadmin",
            )):
                interesting_classes.add(class_name)
        for value in dex.get_strings():
            string_value = str(value)
            for key, pattern in indicator_patterns.items():
                if pattern.search(string_value):
                    matched_indicators[key] += 1
            for candidate in re.findall(r"https?://[^\s\"'<>\\]+", string_value, flags=re.I):
                try:
                    host = urlsplit(candidate).hostname
                    if host:
                        url_hosts.add(host.lower())
                except Exception:
                    pass

    package_path = str(metadata.get("get_package", ""))
    class_names = set(namespace_counts)
    frameworks = {}
    framework_signals = {
        "Flutter": any("flutter" in name.lower() for name in inventory["largest_entries"] if "path" in name)
                    or any("io/flutter" in name for name in class_names)
                    or any(item["path"].startswith("assets/flutter_assets/") for item in inventory["largest_entries"]),
        "React Native": any("com/facebook/react" in name for name in class_names),
        "Unity": any("com/unity3d" in name for name in class_names)
                 or any(item["path"].endswith("/libunity.so") for item in inventory["native_libraries"]),
        "Cordova": any("org/apache/cordova" in name for name in class_names),
        "Capacitor": any("com/getcapacitor" in name for name in class_names),
        "Godot": any("godot" in item["path"].lower() for item in inventory["native_libraries"]),
        "Xamarin/Mono": any("monodroid" in item["path"].lower() or "mono/" in item["path"].lower()
                            for item in inventory["native_libraries"]),
        "Jetpack Compose": any("androidx/compose" in name for name in class_names),
        "Firebase": any("com/google/firebase" in name for name in class_names),
    }
    frameworks = [name for name, present in framework_signals.items() if present]

    split_name = root_attrs.get("split")
    if split_name:
        apk_kind = "SPLIT_APK"
    elif inventory["android_manifest_present"]:
        apk_kind = "BASE_OR_STANDALONE_APK (no split attribute in manifest)"
    else:
        apk_kind = "NOT_CONFIRMED_AS_ANDROID_APK"

    report = {
        "file": inventory,
        "apk_kind": apk_kind,
        "manifest": {
            "root_attributes": root_attrs,
            "application_attributes": app_attrs,
            "components": components,
            "uses_permissions": sorted(set(manifest_permissions)),
            "uses_features": manifest_features,
        },
        "package_metadata": metadata,
        "dex": {
            "dex_count": len(dex_names),
            "dex_names": dex_names,
            "class_count": class_count,
            "top_namespaces": namespace_counts.most_common(50),
            "background_and_service_related_classes": sorted(interesting_classes)[:250],
            "string_indicator_counts": dict(sorted(matched_indicators.items())),
            "network_url_hosts_from_dex_strings": sorted(url_hosts)[:200],
        },
        "framework_fingerprints": frameworks,
        "analysis_scope": "STATIC_ONLY; APK NOT INSTALLED OR EXECUTED",
        "limitations": [
            "String and class-name matches indicate code presence/capability, not confirmed runtime behavior.",
            "Static inspection cannot prove an APK is malware-free.",
            "Dynamically downloaded, encrypted, or server-provided code may not be represented in this artifact.",
        ],
    }

    json_path = out_dir / "apk-forensic-report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    summary_lines = [
        "APK FORENSIC AUDIT — STATIC",
        f"File: {inventory['file']}",
        f"Size: {inventory['size_bytes']} bytes",
        f"SHA-256: {inventory['sha256']}",
        f"ZIP integrity: {inventory['zip_integrity']}",
        f"APK classification: {apk_kind}",
        f"Package: {metadata.get('get_package')}",
        f"Application label: {metadata.get('get_app_name')}",
        f"Version: {metadata.get('get_androidversion_name')} (code {metadata.get('get_androidversion_code')})",
        f"Min SDK: {metadata.get('get_min_sdk_version')}; target SDK: {metadata.get('get_target_sdk_version')}",
        f"Main activity: {metadata.get('get_main_activity')}",
        f"DEX files: {len(dex_names)}; classes: {class_count}",
        f"Native libraries: {len(inventory['native_libraries'])}; ABIs: {inventory['native_libraries_by_abi']}",
        f"Embedded model-like files: {len(model_payloads)}",
        f"Framework fingerprints: {frameworks}",
        f"Permissions: {len(set(manifest_permissions))}",
        f"Components: " + ", ".join(f"{kind}={len(rows)}" for kind, rows in components.items()),
        f"DEX indicator counts: {dict(sorted(matched_indicators.items()))}",
        f"Hosts referenced in DEX strings: {sorted(url_hosts)[:80]}",
        "",
        "This is static analysis only. The APK was not installed or executed.",
        "See apk-forensic-report.json and the attached manifest/signature/aapt outputs for details.",
    ]
    summary_path = out_dir / "apk-forensic-summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print("\n".join(summary_lines))
    print(f"JSON_REPORT={json_path}")
    print(f"SUMMARY_REPORT={summary_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
