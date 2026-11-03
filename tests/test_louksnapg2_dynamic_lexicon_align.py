from __future__ import annotations
import io, tarfile, tempfile, unittest
from pathlib import Path
from louksnapg2_dynamic_lexicon_align import build_candidates, parse_archive


class DynamicLexiconAlignmentTests(unittest.TestCase):
    def test_requires_exact_translation_syntax_and_shared_author(self):
        greek = [
            {"original":"λόγος","original_key":"λόγος","translated":"word","translated_key":"word","syntax_type":"nouns","authors":["Plato"],"count":12,"loglikelihood":8.0,"entry_form":"λόγος","pos":"noun","source_member":"g.xml"},
            {"original":"λέγω","original_key":"λέγω","translated":"word","translated_key":"word","syntax_type":"verbs","authors":["Plato"],"count":12,"loglikelihood":8.0,"entry_form":"λέγω","pos":"verb","source_member":"g2.xml"},
        ]
        latin = [
            {"original":"verbum","original_key":"verbum","translated":"word","translated_key":"word","syntax_type":"nouns","authors":["Plato"],"count":10,"loglikelihood":7.0,"entry_form":"verbum","pos":"noun","source_member":"l.xml"},
            {"original":"dictum","original_key":"dictum","translated":"word","translated_key":"word","syntax_type":"nouns","authors":["Cicero"],"count":8,"loglikelihood":6.0,"entry_form":"dictum","pos":"noun","source_member":"l2.xml"},
        ]
        result = build_candidates(greek, latin)
        self.assertEqual(result["candidate_count"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["greek"], ["λόγος"])
        self.assertEqual(candidate["latin"], ["verbum"])
        self.assertEqual(candidate["shared_authors"], ["Plato"])
        self.assertEqual(candidate["epistemic_status"], "HYPOTHESIS_ONLY_REQUIRES_HELD_OUT_PHILOLOGICAL_VALIDATION")

    def test_tar_parser_preserves_collocation_provenance(self):
        xml = b"""<lexicalentry><form>logos</form><count>12</count><poscontainer>
        <pos>noun</pos><syntaxcontainer><type>Nouns</type><collocation>
        <original>logos</original><trans>word</trans><count>7</count><loglikelihood>8.4</loglikelihood>
        <authorcontainer><author><name>Plato</name></author></authorcontainer>
        </collocation></syntaxcontainer></poscontainer></lexicalentry>"""
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"greek.tar.gz"
            with tarfile.open(path,"w:gz") as archive:
                info=tarfile.TarInfo("entries/one.xml"); info.size=len(xml); archive.addfile(info,io.BytesIO(xml))
            rows=parse_archive(path,"grc")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["original"],"logos")
        self.assertEqual(rows[0]["translated"],"word")
        self.assertEqual(rows[0]["authors"],["Plato"])
        self.assertEqual(rows[0]["count"],7)

    def test_rejects_archive_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"greek.tar.gz"
            with tarfile.open(path,"w:gz") as archive:
                info=tarfile.TarInfo("../escape.xml"); info.size=5; archive.addfile(info,io.BytesIO(b"<x/> "))
            with self.assertRaisesRegex(RuntimeError,"UNSAFE_MEMBER"):
                parse_archive(path,"grc")


if __name__=="__main__":
    unittest.main(verbosity=2)
