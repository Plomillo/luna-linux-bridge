from __future__ import annotations
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from louksnapg2_dynamic_lexicon_align import (
    build_candidates,
    extraction_status,
    parse_archive,
)


class DynamicLexiconAlignmentTests(unittest.TestCase):
    def test_parses_current_perseus_sensecontainer_schema(self):
        xml = """<lexicalentry>
          <form>λόγος</form><count>12</count><per10k>0.055</per10k>
          <poscontainer><pos>noun</pos><senses>
            <sensecontainer><sense>word</sense><count>7</count><prob>0.8</prob><loglikelihood>8.4</loglikelihood></sensecontainer>
            <sensecontainer><sense>account</sense><count>3</count><prob>0.2</prob><loglikelihood>3.1</loglikelihood></sensecontainer>
          </senses></poscontainer>
        </lexicalentry>""".encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "greek.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                info = tarfile.TarInfo("entries/logos.xml")
                info.size = len(xml)
                archive.addfile(info, io.BytesIO(xml))
            rows = parse_archive(path, "grc")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["entry_form"], "λόγος")
        self.assertEqual(rows[0]["sense"], "word")
        self.assertEqual(rows[0]["pos"], "noun")
        self.assertEqual(rows[0]["count"], 7)
        self.assertEqual(rows[0]["probability"], 0.8)

    def test_candidates_require_exact_english_sense_and_pos(self):
        greek = [
            {"entry_form":"λόγος","entry_key":"λόγος","sense":"word","sense_key":"word","pos":"noun","count":12,"source_member":"g1.xml"},
            {"entry_form":"λέγω","entry_key":"λέγω","sense":"word","sense_key":"word","pos":"verb","count":9,"source_member":"g2.xml"},
        ]
        latin = [
            {"entry_form":"verbum","entry_key":"verbum","sense":"word","sense_key":"word","pos":"noun","count":10,"source_member":"l1.xml"},
            {"entry_form":"dictum","entry_key":"dictum","sense":"word","sense_key":"word","pos":"noun","count":4,"source_member":"l2.xml"},
        ]
        result = build_candidates(greek, latin)
        self.assertEqual(result["candidate_count"], 2)
        by_greek = {tuple(row["greek_lemmas"]): row for row in result["candidates"]}
        self.assertIn(("λόγος",), by_greek)
        self.assertNotIn(("λέγω",), by_greek)
        self.assertEqual(by_greek[("λόγος",)]["latin_lemmas"], ["dictum", "verbum"])
        self.assertFalse(by_greek[("λόγος",)]["epistemic_status"].startswith("CERTIFIED"))

    def test_no_shared_sense_is_a_non_pass_result(self):
        greek = [{"sense_key":"river","pos":"noun"}]
        latin = [{"sense_key":"horse","pos":"noun"}]
        result = build_candidates(greek, latin)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(extraction_status(greek, latin, result["candidate_count"]), "FAIL_NO_SHARED_SENSE_CANDIDATES")
        self.assertEqual(extraction_status([], latin, 0), "FAIL_NO_SOURCE_SENSE_RECORDS")

    def test_ambiguous_cartesian_group_is_skipped(self):
        greek = [{"entry_key":f"g{i}","entry_form":f"g{i}","sense_key":"common","sense":"common","pos":"noun","count":1,"source_member":f"g{i}.xml"} for i in range(51)]
        latin = [{"entry_key":f"l{i}","entry_form":f"l{i}","sense_key":"common","sense":"common","pos":"noun","count":1,"source_member":f"l{i}.xml"} for i in range(51)]
        result = build_candidates(greek, latin)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["alignment_diagnostics"]["groups_skipped_for_many_to_many_ambiguity"], 1)

    def test_rejects_archive_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "greek.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                info = tarfile.TarInfo("../escape.xml")
                payload = b"<lexicalentry><form>x</form></lexicalentry>"
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            with self.assertRaisesRegex(RuntimeError, "UNSAFE_MEMBER"):
                parse_archive(path, "grc")


if __name__ == "__main__":
    unittest.main(verbosity=2)
