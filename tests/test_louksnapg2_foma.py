from __future__ import annotations
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"cajita-luna-runtime"/"LOUKSNAPG2_RUNTIME"))
from louksnapg2_foma import FomaEngine,FomaRuntimeError
class FomaRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        source=self.root/"4. Traductor Inteligente/Traducción de lenguas antiguas/foma-master/foma-master/foma"
        source.mkdir(parents=True); (source/"Makefile").write_text("all:\n\t@true\n",encoding="utf-8")
        self.resources=self.root/"LOUKSNAPG2_RUNTIME/foma_transducers"; self.resources.mkdir(parents=True)
        self.manifest=self.resources/"manifest.json"; self.fst=self.resources/"latin-en.fst"
        self.fst.write_bytes(b"pinned-foma-binary"); self.engine=FomaEngine(self.root,self.manifest)
    def tearDown(self): self.temp.cleanup()
    def write_manifest(self,rows):
        self.manifest.write_text(json.dumps({"schema":"LOUKSNAPG2_FOMA_TRANSLATION_RESOURCES/1.0","transducers":rows}),encoding="utf-8")
    def test_missing_transducer_fails_closed(self):
        self.write_manifest({})
        with self.assertRaisesRegex(FomaRuntimeError,"FOMA_TRANSLATION_RESOURCES_NOT_PROVISIONED"):
            self.engine.translate("Alea iacta est",src_lang="lat",tgt_lang="eng")
    def test_pinned_transducer_uses_flookup_no_model_fallback(self):
        self.write_manifest({"lat->eng":{"path":"latin-en.fst","bytes":self.fst.stat().st_size,
            "sha256":hashlib.sha256(self.fst.read_bytes()).hexdigest()}})
        with mock.patch.object(self.engine,"_binaries",return_value=(Path("/tmp/foma"),Path("/tmp/flookup"))), \
             mock.patch("louksnapg2_foma._run",return_value={"stdout_tail":"The die is cast.\n","exit_code":0}):
            r=self.engine.translate("Alea iacta est",src_lang="lat",tgt_lang="eng")
        self.assertEqual(r["output_text"],"The die is cast.")
        self.assertEqual(r["adapter_id"],"LOUKSNAPG2_FOMA_ANCIENT_TRANSLATION_ADAPTER/1.0")
        self.assertEqual(r["translation_strategy"],"FOMA_FINITE_STATE_TRANSDUCER_LOOKUP")
        self.assertFalse(r["general_translation_fallback_selected"])
    def test_hash_mismatch_rejected(self):
        self.write_manifest({"lat->eng":{"path":"latin-en.fst","bytes":1,"sha256":"0"*64}})
        with self.assertRaisesRegex(FomaRuntimeError,"FOMA_TRANSDUCER_IDENTITY_MISMATCH"):
            self.engine.translate("Alea iacta est",src_lang="lat",tgt_lang="eng")
    def test_path_traversal_rejected(self):
        escape=self.root/"LOUKSNAPG2_RUNTIME"/"escape.fst"
        escape.parent.mkdir(parents=True,exist_ok=True); escape.write_bytes(b"outside-resource-root")
        self.write_manifest({"lat->eng":{"path":"../escape.fst","bytes":escape.stat().st_size,
            "sha256":hashlib.sha256(escape.read_bytes()).hexdigest()}})
        with self.assertRaisesRegex(FomaRuntimeError,"FOMA_TRANSDUCER_PATH_UNSAFE"):
            self.engine.translate("Alea iacta est",src_lang="lat",tgt_lang="eng")
    def test_unregistered_language_rejected(self):
        self.write_manifest({})
        with self.assertRaisesRegex(FomaRuntimeError,"FOMA_SOURCE_LANGUAGE_NOT_REGISTERED"):
            self.engine.translate("bonjour",src_lang="fra",tgt_lang="eng")
if __name__=="__main__": unittest.main()
