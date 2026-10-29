from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from louksnapg2_functional_eval import (
    check_translation_en_es,
    check_translation_es_en,
    check_translation_en_fr,
    check_translation_fr_en,
)


class DirectionalTranslationQualityTests(unittest.TestCase):
    def test_english_source_sentence_is_rejected_as_english_to_spanish_translation(self):
        self.assertFalse(check_translation_en_es("The meeting starts at noon."))

    def test_spanish_target_preserving_meaning_passes(self):
        self.assertTrue(check_translation_en_es("La reunión empieza al mediodía."))

    def test_spanish_source_sentence_is_rejected_as_spanish_to_english_translation(self):
        self.assertFalse(check_translation_es_en("La reunión empieza al mediodía."))

    def test_english_target_preserving_meaning_passes(self):
        self.assertTrue(check_translation_es_en("The meeting starts at noon."))

    def test_english_source_sentence_is_rejected_as_english_to_french_translation(self):
        self.assertFalse(check_translation_en_fr("The book is on the table."))

    def test_french_target_preserving_meaning_passes(self):
        self.assertTrue(check_translation_en_fr("Le livre est sur la table."))

    def test_french_source_sentence_is_rejected_as_french_to_english_translation(self):
        self.assertFalse(check_translation_fr_en("Le livre est sur la table."))

    def test_english_translation_from_french_passes(self):
        self.assertTrue(check_translation_fr_en("The book is on the table."))


if __name__ == "__main__":
    unittest.main()
