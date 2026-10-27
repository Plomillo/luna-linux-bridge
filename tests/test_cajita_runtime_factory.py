from __future__ import annotations
import json, shutil, tempfile, unittest, zipfile
from pathlib import Path
from cajita_runtime_factory import safe_rel, extract, tree_hash, tree_rows, factory_materialize, sha_file, COMBINED_CAP, externalized_container_contract, validate_packaged_archive_member_set, build_native_engine_overlays, max_required_glibc_version
from reproduce_macrodown import BINARY_SUFFIXES, add_stream, DEFAULT_COMBINED_CAP_BYTES
from cajita_runtime import KNOWN_INFRASTRUCTURE_TEST_FIXTURES, classify_model_like_paths, COMBINED_DISTRIBUTION_CAP_BYTES

class FactorySafetyTests(unittest.TestCase):
 def test_glibc_symbol_version_parser_uses_numeric_maximum(self):
  self.assertEqual(max_required_glibc_version("foo GLIBC_2.9 GLIBC_2.35 GLIBC_2.36"),(2,36))
  self.assertGreater(max_required_glibc_version("GLIBC_2.35 GLIBC_2.38"),(2,36))
  self.assertIsNone(max_required_glibc_version("statically linked with no versioned GLIBC symbols"))

 def test_cajita_archive_and_combined_distribution_have_distinct_caps(self):
  from cajita_runtime_factory import RUNTIME_ARCHIVE_CAP
  from reproduce_macrodown import RUNTIME_ARCHIVE_CAP_BYTES
  self.assertEqual(RUNTIME_ARCHIVE_CAP, 470_000_000)
  self.assertEqual(RUNTIME_ARCHIVE_CAP_BYTES, 470_000_000)
  self.assertEqual(COMBINED_CAP, 479_000_000)
  self.assertEqual(DEFAULT_COMBINED_CAP_BYTES, 479_000_000)
  self.assertEqual(COMBINED_DISTRIBUTION_CAP_BYTES, 479_000_000)

 def test_archive_free_rerun_preserves_and_revalidates_materialized_modules_and_history(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); runtime=root/"runtime"; runtime.mkdir(); rollback=root/"rollback"; rollback.mkdir()
   module_key="engines/sample_engine"; module=runtime/module_key; module.mkdir(parents=True)
   payload=module/"engine.py"; payload.write_text("VALUE = 7\n",encoding="utf-8")
   rows=tree_rows(module,True)
   descriptor={
    "schema":"CAJITA_MATERIALIZED_MODULE/1.0","module_key":module_key,
    "identity_type":"PATH_SCOPED_NO_CANONICAL_ID_REASSIGNMENT","canonical_asset_id":"SAMPLE_ENGINE",
    "source_archives":[{"path":"engines/sample_engine.zip","bytes":123,"sha256":"a"*64}],
    "materialization":{"status":"PASS","file_count":len(rows),"bytes":sum(x["bytes"] for x in rows),"tree_sha256":tree_hash(module)},
    "consumer_adapter":"NOT_PROVEN_BY_EXTRACTION","functional_smoke":"REQUIRED","certification":"NOT_GRANTED"}
   descriptor_path=module/"CAJITA_MODULE.json"
   descriptor_path.write_text(json.dumps(descriptor,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
   descriptor_sha=sha_file(descriptor_path)
   historic_archive={"source_path":"engines/sample_engine.zip","source_sha256":"a"*64,"source_bytes":123,
    "expanded_path":module_key,"expanded_file_count_at_extract":1,"expanded_bytes_at_extract":len(payload.read_bytes()),
    "archive_removed_from_runtime":True,"rollback_path":"engines/sample_engine.zip","asset_id":"SAMPLE_ENGINE"}
   historic_readme={"path":"README.md","bytes":5,"sha256":"b"*64}
   registry={"schema":"CAJITA_MODULE_REGISTRY/1.0","materialized_module_count":1,"modules":[
    {"module_key":module_key,"canonical_asset_id":"SAMPLE_ENGINE","path":module_key,
     "manifest":module_key+"/CAJITA_MODULE.json","manifest_sha256":descriptor_sha,
     "tree_sha256":tree_hash(module),"bytes":sum(x["bytes"] for x in rows),"file_count":len(rows),
     "state":"MATERIALIZED_HASH_VERIFIED","consumer_adapter":"NOT_PROVEN_BY_EXTRACTION","execution":"NOT_GRANTED_WITHOUT_ADAPTER_AND_SMOKE","certification":"NOT_GRANTED"}],
    "certification":"NOT_GRANTED"}
   (runtime/"module_registry.json").write_text(json.dumps(registry,indent=2)+"\n",encoding="utf-8")
   (runtime/"MACRODOWN_MANIFEST.json").write_text(json.dumps({"files":[]})+"\n",encoding="utf-8")
   placement={"assets":[],"factory_reconciliation":{"schema":"CAJITA_LOUKSNA1_FACTORY/1.0","archive_count_materialized":1,
    "archive_bytes_removed":123,"archives":[historic_archive],"readmes_removed":[historic_readme],
    "module_count":1,"rollback_copies_retained_outside_runtime":True,"all_zip_7z_removed":True}}
   (runtime/"EXTERNALIZED_ASSET_PLACEMENT.json").write_text(json.dumps(placement,indent=2)+"\n",encoding="utf-8")
   routing={"state":{"status":"OLD","task_dispatch":"PLAN_ONLY","certification":"NOT_GRANTED"},
    "domain_order":[],"engine_registry":[],"route_profiles":[],"support_assets":[],
    "materialization":{"archive_count_removed":1,"module_count":1}}
   (runtime/"command_subdomain_routing.json").write_text(json.dumps(routing,indent=2)+"\n",encoding="utf-8")
   result=factory_materialize(runtime,rollback,10_000_000)
   registry_after=json.loads((runtime/"module_registry.json").read_text(encoding="utf-8"))
   placement_after=json.loads((runtime/"EXTERNALIZED_ASSET_PLACEMENT.json").read_text(encoding="utf-8"))
   routing_after=json.loads((runtime/"command_subdomain_routing.json").read_text(encoding="utf-8"))
   self.assertEqual(result["archive_count"],1)
   self.assertEqual(result["archive_count_this_run"],0)
   self.assertEqual(result["module_count"],1)
   self.assertEqual(registry_after["materialized_module_count"],1)
   self.assertEqual(len(registry_after["modules"]),1)
   self.assertEqual(placement_after["factory_reconciliation"]["archives"],[historic_archive])
   self.assertEqual(placement_after["factory_reconciliation"]["readmes_removed"],[historic_readme])
   self.assertEqual(routing_after["materialization"]["archive_count_removed"],1)
   self.assertEqual(routing_after["materialization"]["archive_count_this_run"],0)
   self.assertFalse(any(p.suffix.lower() in {".zip",".7z"} for p in runtime.rglob("*")))

 def test_native_engine_builds_are_pinned_hash_bound_and_reproducible(self):
  import stat
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory(prefix="native-engine-factory-test-") as temp:
   root=Path(temp); runtime=root/"runtime"; runtime.mkdir()
   foma_module=runtime/"4. Traductor Inteligente/Traducción de lenguas antiguas"
   foma_source=foma_module/"foma-master/foma-master/foma"
   foma_source.mkdir(parents=True)
   (foma_source/"Makefile").write_text("all:\n\t@true\ncheck:\n\t@true\n",encoding="utf-8")
   (foma_source/"tests").mkdir()
   foma_test_runner=foma_source/"tests"/"run.sh"
   foma_test_runner.write_text("#!/bin/sh\nexit 0\n",encoding="utf-8")
   foma_test_runner.chmod(0o644)
   foma_test_runner_sha=sha_file(foma_test_runner)
   trealla_module=runtime/"4. Traductor Inteligente/Hermenéutica H-G"
   trealla_source=trealla_module/"trealla-2.100.24/trealla-2.100.24"
   (trealla_source/"samples").mkdir(parents=True)
   (trealla_source/"Makefile").write_text("all: README.md\n\t@true\n",encoding="utf-8")
   (trealla_source/"samples/grammar.pl").write_text("sentence --> [fixture].\n",encoding="utf-8")
   routing={"targets":[
    {"id":"D04_TRADUCCION_LENGUAS_ANTIGUAS","path":"4. Traductor Inteligente/Traducción de lenguas antiguas"},
    {"id":"D04_HERMENEUTICA_HG","path":"4. Traductor Inteligente/Hermenéutica H-G"}]}
   (runtime/"command_subdomain_routing.json").write_text(json.dumps(routing),encoding="utf-8")
   observed_commands=[]
   def fake_run(command,cwd=None,stdout=None,stderr=None,text=None,timeout=None,check=None,env=None):
    observed_commands.append(list(command))
    cwd=Path(cwd) if cwd else runtime
    out=""
    if command[:2] in (["make","--version"],["cc","--version"]): out="tool version fixture\n"
    elif command and command[0]=="make" and cwd.name=="foma":
     if command==["make","check"]:
      runner_script=cwd/"tests"/"run.sh"
      if not runner_script.is_file() or not (runner_script.stat().st_mode&0o111):
       return SimpleNamespace(returncode=1,stdout="temporary Foma test runner is not executable\n",stderr="")
      out="foma regression fixture\n"
     else:
      for name in ("foma","flookup"):
       binary=cwd/name; binary.write_bytes(Path(shutil.which("true")).read_bytes()); binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
      out="foma build fixture\n"
    elif command and command[0]=="make" and cwd.name=="trealla-2.100.24":
     binary=cwd/"tpl"; binary.write_bytes(Path(shutil.which("true")).read_bytes()); binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
     out="trealla build fixture\n"
    elif command and command[0]=="ldd": out="statically linked\n"
    elif command and command[0]=="objdump": out="GLIBC_2.17 GLIBC_2.35\\n"
    else: out="ok\n"
    return SimpleNamespace(returncode=0,stdout=out,stderr="")
   receipt=build_native_engine_overlays(runtime,"a"*40,runner=fake_run)
   self.assertEqual(receipt["schema"],"CAJITA_NATIVE_ENGINE_BUILD_RECEIPTS/1.0")
   self.assertEqual(receipt["source_commit"],"a"*40)
   self.assertEqual(len(receipt["builds"]),2)
   self.assertIn(["make","-j1",'GIT_VERSION="2.100.24"',"NOFFI=1","NOSSL=1","NOTHREADS=1","ISOCLINE=1"],observed_commands)
   foma_build=next(row for row in receipt["builds"] if row["target_id"]=="D04_TRADUCCION_LENGUAS_ANTIGUAS")
   trealla_build=next(row for row in receipt["builds"] if row["target_id"]=="D04_HERMENEUTICA_HG")
   output_paths={row["name"]:runtime/row["path"] for row in foma_build["binary_artifacts"]}
   trealla_binary=runtime/trealla_build["binary_artifacts"][0]["path"]
   self.assertTrue(output_paths["foma"].is_file())
   self.assertTrue(output_paths["flookup"].is_file())
   self.assertTrue((runtime/trealla_binary).is_file())
   self.assertFalse((foma_source/"foma").exists())
   self.assertFalse((foma_source/"flookup").exists())
   self.assertFalse((trealla_source/"tpl").exists())
   self.assertFalse((trealla_source/"README.md").exists())
   self.assertTrue(foma_build["source_tree_preserved"])
   foma_row=next(row for row in foma_build["binary_artifacts"] if row["name"]=="foma")
   self.assertEqual(foma_row["linkage"]["max_required_glibc"],"2.35")
   self.assertEqual(trealla_build["binary_artifacts"][0]["linkage"]["glibc_compatibility"],"PASS")
   self.assertEqual(foma_build["source_tree_sha256_before_build"],foma_build["source_tree_sha256_after_build"])
   self.assertTrue(trealla_build["source_tree_preserved"])
   self.assertEqual(trealla_build["source_tree_sha256_before_build"],trealla_build["source_tree_sha256_after_build"])
   # The downloaded source archive omitted this executable bit. Only the temporary
   # build copy may be repaired; source bytes and mode remain untouched.
   self.assertEqual(sha_file(foma_test_runner),foma_test_runner_sha)
   self.assertFalse(foma_test_runner.stat().st_mode&0o111)
   repair=foma_build["temporary_test_mode_repairs"][0]
   self.assertEqual(repair["path"],"tests/run.sh")
   self.assertEqual(repair["sha256"],foma_test_runner_sha)
   self.assertEqual(repair["scope"],"TEMPORARY_BUILD_COPY_ONLY")
   self.assertFalse(repair["source_tree_mutated"])
   saved=json.loads((runtime/"NATIVE_ENGINE_BUILD_RECEIPTS.json").read_text(encoding="utf-8"))
   self.assertEqual(saved["model_weight_downloads"],0)
   self.assertFalse(saved["remote_commander_used"])
 def test_only_registered_externalized_containers_are_allowed_in_macrodown(self):
  runtime=Path(__file__).resolve().parents[1]/"cajita-luna-runtime"
  contract=externalized_container_contract(runtime)
  expected_ids={
   "APACHE_JENA_6_2_0","PLAYWRIGHT_1_63_0_SOURCE","ONNX_RUNTIME_1_29_0_CP311",
   "DAGGER_0_21_8_LINUX_AMD64","OPA_STATIC_LINUX_AMD64_CANDIDATE","RQLITE_10_2_7_LINUX_AMD64",
   "SQLITE_SOURCE_3_53_4","CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE","AVALONIA_12_1_1_NUGET",
   "TAURI_2_11_5_SOURCE_ZIP",
  }
  self.assertEqual(len(contract),10)
  self.assertEqual({row["id"] for row in contract.values()},expected_ids)
  self.assertEqual(validate_packaged_archive_member_set(list(contract),contract),list(contract))
  with self.assertRaisesRegex(RuntimeError,"EXTERNALIZED_ARCHIVE_MEMBER_SET_MISMATCH"):
   validate_packaged_archive_member_set(list(contract)+["unregistered/rogue.zip"],contract)

 def test_parent_traversal_is_denied(self):
  with self.assertRaisesRegex(RuntimeError,"TRAVERSAL"): safe_rel("../outside")
 def test_onnxruntime_dataset_models_are_infrastructure_fixtures_not_extra_weights(self):
  found=set(KNOWN_INFRASTRUCTURE_TEST_FIXTURES)|{"1. Cerebro/model.safetensors","6. Sistema Inteligente/Anti-Alucinaciones/model.onnx"}
  listed={"1. Cerebro/model.safetensors","6. Sistema Inteligente/Anti-Alucinaciones/model.onnx"}
  result=classify_model_like_paths(found,listed)
  self.assertEqual(result["recognized_infrastructure_fixtures"],sorted(KNOWN_INFRASTRUCTURE_TEST_FIXTURES))
  self.assertEqual(result["undeclared_model_like_files"],[])
  self.assertEqual(result["missing_infrastructure_fixtures"],[])
 def test_unknown_model_like_files_remain_fail_closed(self):
  result=classify_model_like_paths({"6. Sistema Inteligente/Anti-Alucinaciones/unregistered.onnx"},set())
  self.assertIn("6. Sistema Inteligente/Anti-Alucinaciones/unregistered.onnx",result["undeclared_model_like_files"])
  self.assertEqual(len(result["missing_infrastructure_fixtures"]),3)
 def test_absolute_path_is_denied(self):
  with self.assertRaisesRegex(RuntimeError,"ABSOLUTE"): safe_rel("/etc/passwd")
 def test_zip_extract_is_deterministic(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); arc=root/"engine.zip"
   with zipfile.ZipFile(arc,"w") as z:
    z.writestr("src/main.py","print('ok')\n"); z.writestr("src/config.json",'{"ok":true}\n')
   dest=root/"dest"; dest2=root/"rollback"; dest2.mkdir()
   extract(arc,dest,dest2); first=tree_hash(dest)
   extract(arc,dest,dest2); self.assertEqual(first,tree_hash(dest))
   self.assertEqual(len(tree_rows(dest)),2)
 def test_model_payloads_are_deflated_in_outer_container_without_byte_changes(self):
  for suffix in (".safetensors", ".onnx", ".bin", ".model"):
   self.assertNotIn(suffix, BINARY_SUFFIXES)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); payload=root/"model.safetensors"
   raw=(bytes(range(256))*2048)
   payload.write_bytes(raw)
   outer=root/"test.macrodown"
   with zipfile.ZipFile(outer,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    add_stream(z,payload.name,payload)
   with zipfile.ZipFile(outer) as z:
    info=z.getinfo(payload.name)
    self.assertEqual(info.compress_type,zipfile.ZIP_DEFLATED)
    self.assertEqual(z.read(payload.name),raw)
 def test_zip_slip_fails_before_writing_outside(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); arc=root/"bad.zip"
   with zipfile.ZipFile(arc,"w") as z: z.writestr("../outside.txt","bad")
   dest=root/"dest"; rollback=root/"rollback"; rollback.mkdir()
   with self.assertRaisesRegex(RuntimeError,"TRAVERSAL"): extract(arc,dest,rollback)
   self.assertFalse((root/"outside.txt").exists())


 def test_model_runtimes_resolve_packaged_root_by_materializer_file(self):
  root = Path(__file__).resolve().parents[1] / "cajita-luna-runtime"
  paths = (
   "1. Cerebro/cerebro_180mb_runtime.py",
   "3. Transcripción/lowrank_runtime.py",
   "4. Traductor Inteligente/Traducción general/lowrank_runtime.py",
   "6. Sistema Inteligente/Análisis Avanzado/lowrank_runtime_v2.py",
  )
  for rel in paths:
   with self.subTest(path=rel):
    source = (root / rel).read_text(encoding="utf-8")
    self.assertIn('(parent / "cajita_weight_materializer.py").is_file()', source)
    self.assertNotIn('p.name == "cajita-luna-runtime"', source)

if __name__=="__main__": unittest.main()
