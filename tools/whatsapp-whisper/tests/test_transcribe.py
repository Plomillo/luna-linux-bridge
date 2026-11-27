"""Regression tests for WhatsApp export parsing.

Run from the repository root:
    python -m unittest discover -s tools/whatsapp-whisper/tests -v
"""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "transcribe.py"
SPEC = importlib.util.spec_from_file_location("whatsapp_transcribe", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ParseChatTests(unittest.TestCase):
    def test_spanish_export_dates_and_meridiem(self):
        source = (
            "4/1/2026, 12:01\u202fa.\u202fm. - Lyx: medianoche\n"
            "4/1/2026, 12:30\u202fp.\u202fm. - Diego: mediodía\n"
            "4/1/2026, 3:43\u202fa.\u202fm. - Lyx: madrugada"
        )
        rows = MODULE.parse_chat(source)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["timestamp"].hour, 0)
        self.assertEqual(rows[1]["timestamp"].hour, 12)
        self.assertEqual(rows[2]["timestamp"].hour, 3)
        self.assertEqual(rows[0]["timestamp"].day, 4)
        self.assertEqual(rows[0]["timestamp"].month, 1)

    def test_multiline_message_is_preserved(self):
        source = (
            "4/1/2026, 4:01 a. m. - Diego: Padre, es Dios.\n"
            "Hijo, es Dios hecho carne.\n"
            "Espíritu Santo, es mensajero.\n"
            "4/1/2026, 4:02 a. m. - Lyx: entendido"
        )
        rows = MODULE.parse_chat(source)
        self.assertEqual(len(rows), 2)
        self.assertIn("Hijo, es Dios hecho carne.", rows[0]["body"])
        self.assertIn("Espíritu Santo, es mensajero.", rows[0]["body"])
        self.assertEqual(rows[1]["sender"], "Lyx")

    def test_system_event_without_sender_separator(self):
        source = "4/1/2026, 3:43 a. m. - Los mensajes están cifrados."
        rows = MODULE.parse_chat(source)
        self.assertEqual(rows[0]["sender"], "SYSTEM")
        self.assertIn("cifrados", rows[0]["body"])

    def test_whatsapp_bidi_mark_is_removed_from_audio_attachment_name(self):
        body = "\u200ePTT-20261012-WA0052.opus (archivo adjunto)"
        self.assertEqual(
            MODULE.find_attachment_name(body),
            "PTT-20261012-WA0052.opus",
        )

    def test_sender_name_and_colons_in_message(self):
        source = "4/1/2026, 4:05 p. m. - Lyx: hora: 16:05"
        rows = MODULE.parse_chat(source)
        self.assertEqual(rows[0]["sender"], "Lyx")
        self.assertEqual(rows[0]["body"], "hora: 16:05")


if __name__ == "__main__":
    unittest.main()
