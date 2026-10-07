import importlib.util
import json
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parent.parent / "github_adapter.py"
spec = importlib.util.spec_from_file_location("lrb_github", PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class GitHubAdapterTests(unittest.TestCase):
    def test_write_routes_rejected(self):
        with self.assertRaisesRegex(ValueError, "NOT_ALLOWLISTED"):
            adapter.read_github("/dispatches")

    def test_no_host_authorization_from_github_status(self):
        report = adapter.status({"workflow_runs": [
            {"id": 1, "status": "completed", "conclusion": "success",
             "name": "unit-only", "head_sha": "abc"}]})
        self.assertFalse(report["host_execution_authorized"])
        self.assertFalse(report["github_write_authorized"])
        self.assertEqual(report["g24"], "NOT_EXECUTED")

    def test_fake_status_does_not_certify(self):
        result = adapter.status({"workflow_runs": [{"status": "success",
                "conclusion": "success", "name": "mock"}]})
        self.assertFalse(result["host_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
