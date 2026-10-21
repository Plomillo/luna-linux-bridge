import json,pathlib,unittest
MISSION=pathlib.Path(__file__).with_name("INTELDOC_GLOBAL_30MB_MISSION.json")
class GlobalMissionContract(unittest.TestCase):
 def test_exact_global_cap(self):
  d=json.loads(MISSION.read_text(encoding="utf-8"))
  self.assertEqual(d["global_limit"]["hard_cap_bytes"],30000000)
  self.assertTrue(d["global_limit"]["global_not_per_component"])
  self.assertTrue(d["global_limit"]["fail_closed"])
 def test_all_pinned_artifacts_are_in_scope(self):
  d=json.loads(MISSION.read_text(encoding="utf-8"))
  ids={x["id"] for x in d["inventory"]["pinned_originals"]}
  self.assertEqual(ids,{"granite_docling_q4_gguf","granite_docling_mmproj_f16","docling_slim_wheel","calibre_binary_reference","calibre_source_reference"})
 def test_smoke_deferred_by_user(self):
  d=json.loads(MISSION.read_text(encoding="utf-8"))
  self.assertIn("DEFERRED_BY_USER",d["execution"]["smoke_test"])
 def test_no_certification_or_promotion_authority(self):
  d=json.loads(MISSION.read_text(encoding="utf-8"))
  self.assertFalse(d["execution"]["canonical_promotion_authorized"])
  self.assertFalse(d["execution"]["certification_authorized"])
if __name__=="__main__": unittest.main()
