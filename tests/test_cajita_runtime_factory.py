from __future__ import annotations
import tempfile, unittest, zipfile
from pathlib import Path
from cajita_runtime_factory import safe_rel, extract, tree_hash, tree_rows
from reproduce_macrodown import BINARY_SUFFIXES, add_stream

class FactorySafetyTests(unittest.TestCase):
 def test_parent_traversal_is_denied(self):
  with self.assertRaisesRegex(RuntimeError,"TRAVERSAL"): safe_rel("../outside")
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

if __name__=="__main__": unittest.main()
