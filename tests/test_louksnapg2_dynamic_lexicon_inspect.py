from __future__ import annotations
import io, tarfile, tempfile, unittest
from pathlib import Path
from louksnapg2_dynamic_lexicon_inspect import inspect_archive

def make_tar(path: Path, name: str, data: bytes):
    with tarfile.open(path,"w:gz") as archive:
        info=tarfile.TarInfo(name); info.size=len(data); archive.addfile(info,io.BytesIO(data))

class DynamicLexiconInspectorTests(unittest.TestCase):
    def test_xml_inventory(self):
        xml=b"<root><entry id='x'><form>logos</form><sense><gloss>word</gloss></sense></entry></root>"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"x.tar.gz"; make_tar(path,"entries/x.xml",xml); result=inspect_archive(path,"grc")
        self.assertEqual(result["xml_members"],1)
        self.assertEqual(result["candidate_lexical_tags"]["entry"],1)
        self.assertEqual(result["candidate_lexical_tags"]["sense"],1)
        self.assertEqual(result["candidate_lexical_tags"]["gloss"],1)
    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"x.tar.gz"; make_tar(path,"../escape.xml",b"<root/>")
            with self.assertRaisesRegex(RuntimeError,"UNSAFE_MEMBER"): inspect_archive(path,"lat")
    def test_rejects_entity_declarations(self):
        xml=b"<!DOCTYPE root [<!ENTITY x 'expanded'>]><root><entry>&x;</entry></root>"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"x.tar.gz"; make_tar(path,"x.xml",xml)
            with self.assertRaises(Exception): inspect_archive(path,"grc")

if __name__=="__main__": unittest.main(verbosity=2)
