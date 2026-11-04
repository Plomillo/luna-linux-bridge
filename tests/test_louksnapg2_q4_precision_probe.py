import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HistoricalQ4PrecisionWorkflowTests(unittest.TestCase):
    def test_probe_runs_only_on_the_active_repair_branch(self):
        workflow = (ROOT / ".github" / "workflows" / "louksnapg2-q4-precision-probes.yml").read_text(encoding="utf-8")
        self.assertIn("repair/louksnapg2-gpu-foundation-20261103", workflow)
        self.assertIn("if: github.ref == 'refs/heads/repair/louksnapg2-gpu-foundation-20261103'", workflow)

    def test_historical_q4_source_commit_is_pinned_and_fetched_shallowly(self):
        workflow = (ROOT / ".github" / "workflows" / "louksnapg2-q4-precision-probes.yml").read_text(encoding="utf-8")
        self.assertIn("Q4_COMMIT: fa8b64b1319605e050c2064f955f5fbf47951908", workflow)
        self.assertIn('git fetch --no-tags --depth=1 origin "$Q4_COMMIT"', workflow)
        self.assertIn('git worktree add --detach "$RUNNER_TEMP/louksnapg2-q4" "$Q4_COMMIT"', workflow)

    def test_candidate_probe_is_local_offline_and_preserves_artifacts(self):
        workflow = (ROOT / ".github" / "workflows" / "louksnapg2-q4-precision-probes.yml").read_text(encoding="utf-8")
        self.assertIn('HF_HUB_OFFLINE: "1"', workflow)
        self.assertIn('TRANSFORMERS_OFFLINE: "1"', workflow)
        self.assertIn("tools/louksnapg2_q4_precision_probe.py", workflow)
        self.assertIn("Preserve Q2-to-Q4 model evaluation evidence", workflow)
        self.assertIn("retention-days: 90", workflow)

    def test_probe_covers_all_four_factorized_neural_models(self):
        workflow = (ROOT / ".github" / "workflows" / "louksnapg2-q4-precision-probes.yml").read_text(encoding="utf-8")
        for domain in ("D01_CEREBRO", "D03_TRANSCRIPCION", "D04_TRADUCTOR_INTELIGENTE", "D06_SISTEMA_INTELIGENTE"):
            self.assertIn("- " + domain, workflow)



    def test_precision_probe_calls_native_cajita_adapters_without_auxiliary_router(self):
        source = (ROOT / "tools" / "louksnapg2_historical_weight_probe.py").read_text(encoding="utf-8")
        evaluate = source.split("def evaluate(",1)[1].split("def subprocess_evaluate(",1)[0]
        self.assertIn("adapters.execute_task(request, root, timeout_cap=1800)", evaluate)
        self.assertIn('"DIRECT_CAJITA_TASK_ADAPTER_EXECUTE_TASK"', evaluate)
        self.assertIn('"auxiliary_router_imported":False', evaluate)
        self.assertIn('"service_dispatch_used":False', evaluate)
        self.assertNotIn("LouksnapG2Runtime", evaluate)
        self.assertNotIn("evaluator.run_case(", evaluate)
        self.assertIn('"auxiliary_engine_execution_performed":False', evaluate)
        self.assertIn('"fallback_engine_execution_performed":False', evaluate)


    def test_historical_native_probe_imports_time_for_elapsed_measurement(self):
        source = (ROOT / "tools" / "louksnapg2_historical_weight_probe.py").read_text(encoding="utf-8")
        self.assertIn("import time", source)
        self.assertIn("time.monotonic()", source)

    def test_pre_q2_probe_workflow_runs_on_repair_branch_without_gptoss_lfs_dependency(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "louksnapg2-historical-weight-probes.yml").read_text(encoding="utf-8")
        self.assertIn("repair/louksnapg2-gpu-foundation-20261103", workflow)
        self.assertIn("fetch-depth: 1", workflow)
        self.assertIn('git fetch --no-tags --depth=1 origin "$HISTORICAL_COMMIT"', workflow)
        self.assertNotIn("git lfs pull", workflow)
        self.assertIn("D03_TRANSCRIPCION", workflow)
        self.assertIn("D04_TRADUCTOR_INTELIGENTE", workflow)
        self.assertIn("FULL DIRECT NATIVE Q2 VS PRE-Q2 FACTOR EVIDENCE", workflow)

    def test_precision_probe_workflows_run_inside_exact_one_gib_one_cpu_cgroup(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("louksnapg2-q4-precision-probes.yml", "louksnapg2-historical-weight-probes.yml"):
            workflow = (root / ".github" / "workflows" / name).read_text(encoding="utf-8")
            self.assertIn("container:\\n      image: ubuntu:24.04\\n      options: --memory=1g --memory-swap=1g --cpus=1", workflow)
            self.assertNotIn("sudo apt-get", workflow)

if __name__ == "__main__":
    unittest.main()
