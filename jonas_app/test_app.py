import os, tempfile, unittest
from pathlib import Path
import app

class JonasAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = Path(self.tmp.name) / "test.sqlite3"
        app.init_db()
    def tearDown(self):
        self.tmp.cleanup()
    def call(self, method, path, body=None):
        return app.dispatch(method, path, body or {})
    def test_budget_reserve_blocks_overrun(self):
        status, _ = self.call("POST", "/api/budgets", {"id":"b1","limit":"10","reserve":"2"})
        self.assertEqual(status, 201)
        status, result = self.call("POST", "/api/budgets/b1/spend", {"amount":"8.01","idempotency_key":"x"})
        self.assertEqual(status, 409)
        self.assertIn("reserve", result["error"])
    def test_spend_idempotency(self):
        self.call("POST", "/api/budgets", {"id":"b1","limit":"10","reserve":"1"})
        status, first = self.call("POST", "/api/budgets/b1/spend", {"amount":"2","idempotency_key":"same"})
        self.assertEqual(status, 201)
        status, second = self.call("POST", "/api/budgets/b1/spend", {"amount":"2","idempotency_key":"same"})
        self.assertEqual(status, 200)
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["budget"]["spent"], second["budget"]["spent"])
    def test_halt_denies_spend(self):
        self.call("POST", "/api/budgets", {"id":"b1","limit":"10","reserve":"0"})
        self.call("POST", "/api/budgets/b1/halt", {})
        status, _ = self.call("POST", "/api/budgets/b1/spend", {"amount":"1","idempotency_key":"x"})
        self.assertEqual(status, 423)
    def test_savings_gate(self):
        status, good = self.call("POST", "/api/savings/evaluate", {"baseline_cost":"100","candidate_cost":"89","quality_pass":True,"critical_regression":False})
        self.assertEqual(status, 200); self.assertTrue(good["accepted"])
        _, bad = self.call("POST", "/api/savings/evaluate", {"baseline_cost":"100","candidate_cost":"95","quality_pass":True,"critical_regression":False})
        self.assertFalse(bad["accepted"])
    def test_event_chain_verifies(self):
        self.call("POST", "/api/budgets", {"id":"b1","limit":"10","reserve":"1"})
        with app.connect() as con:
            self.assertTrue(app.verify_chain(con)["valid"])

if __name__ == "__main__":
    unittest.main()