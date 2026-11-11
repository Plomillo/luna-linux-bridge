import unittest

import local_session as session


class LocalSessionTests(unittest.TestCase):
    def test_small_audio_is_not_treated_as_a_dispatch_file(self):
        result = session.LocalSession("s1").note_audio(b"hola")
        self.assertEqual("HOLD", result["status"])
        self.assertFalse(result["raw_audio_committed"])
        self.assertFalse(result["inference_ran"])
        self.assertEqual("127.0.0.1", result["bind_host"])
        self.assertEqual("NOT_GRANTED", result["certification"])

    def test_payload_over_dispatch_limit_fails_closed(self):
        result = session.LocalSession("s2").note_audio(b"x" * (64 * 1024 + 1))
        self.assertEqual("BLOCKED_PAYLOAD_EXCEEDS_GITHUB_DISPATCH", result["transport"])
        self.assertIn("LOCAL_MODEL_INFERENCE", result["forbidden_local"])

    def test_model_storage_is_rejected(self):
        refused = session.LocalSession("s3").refuse_model("whisper.bin")
        self.assertEqual("LOCAL_MODEL_STORAGE_FORBIDDEN", refused["reason"])


if __name__ == "__main__":
    unittest.main()
