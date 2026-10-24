from __future__ import annotations
import tempfile, unittest, zipfile
from pathlib import Path
from cajita_runtime_factory import safe_rel, extract, tree_hash, tree_rows
from reproduce_macrodown import BINARY_SUFFIXES, add_stream
from cajita_runtime import KNOWN_INFRASTRUCTURE_TEST_FIXTURES, classify_model_like_paths

class FactorySafetyTests(unittest.TestCase):
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
