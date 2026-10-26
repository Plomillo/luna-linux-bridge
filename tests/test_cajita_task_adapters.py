from __future__ import annotations
import json, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import cajita_task_adapters as adapters

RUNTIME=Path(__file__).resolve().parents[1]/"cajita-luna-runtime"
def req(domain="D01_CEREBRO",op="generate_text",**payload):
    return {"schema":adapters.REQUEST_SCHEMA,"task_id":"unit-task-001","domain_id":domain,"operation":op,
            "input":payload,"limits":{"timeout_seconds":30,"max_new_tokens":2}}
class AdapterTests(unittest.TestCase):
    def test_docling_known_answer_fixture_is_legible_at_runtime_256px_bound(self):
        # Keep the lightweight unit suite independent of Pillow. G24 renders the
        # actual image; this contract prevents reintroducing tiny downsampled text.
        harness=Path(__file__).resolve().parents[1]/"tools"/"cajita_task_e2e.py"
        source=harness.read_text(encoding="utf-8")
        start=source.index("def make_image(path):")
        end=source.index("def run_case",start)
        fixture=source[start:end]
        for required in (
            'Image.new("RGB",(256,256),"white")',
            'ImageFont.truetype(regular,15)',
            'ImageFont.truetype(bold,24)',
            'ImageFont.truetype(bold,30)',
            'draw.text((12,190),"133.45",font=total,fill="black")',
        ):
            self.assertIn(required,fixture)
        self.assertNotIn('Image.new("RGB",(640,480)',fixture)
        self.assertIn('"id":"invoice-total-133-45"',source)

    def test_docling_e2e_profile_is_bounded_to_single_256px_view(self):
        source=RUNTIME/"5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/docling_30mb_runtime_v1.py"
        text=source.read_text(encoding="utf-8")
        self.assertIn("image_processor.do_image_splitting=False",text)
        self.assertIn("image_side=256",text)
        self.assertIn('image_processor.size={"longest_edge":image_side}',text)
        self.assertIn('image_processor.max_image_size={"longest_edge":image_side}',text)
        self.assertIn("not a quality-equivalence claim",text)
        self.assertIn("def prepare_bounded_square_image(image, side):",text)
        self.assertIn("image=prepare_bounded_square_image(image, image_side)",text)
        self.assertIn("proc.image_seq_len=image_seq_len",text)
        self.assertIn("image_seq_len=((image_side // patch_size) ** 2) // (scale_factor ** 2)",text)
        self.assertIn('canvas = Image.new("RGB", (side, side), (127, 127, 127))',text)
        harness=Path(__file__).resolve().parents[1]/"tools"/"cajita_task_e2e.py"
        e2e=harness.read_text(encoding="utf-8")
        self.assertIn('"task_id":"e2e-docling-image-extraction"',e2e)
        self.assertIn('"max_new_tokens":8',e2e)

    def test_five_model_contracts_and_plan_only_orchestration(self):
        report=adapters.registry_report()
        self.assertEqual(report["model_task_adapter_count"],5)
        self.assertEqual(report["synthetic_scope_registered_target_count"],5)
        self.assertEqual(report["canonical_target_count"],21)
        self.assertEqual(report["unregistered_target_count"],16)
        self.assertEqual(report["all_21_target_adapters"],"PARTIAL_REGISTRATION_ONLY_NOT_ESTABLISHED")
        self.assertEqual(report["reference_quality_equivalence"],"NOT_ESTABLISHED")
        self.assertEqual(report["global_certification"],"NOT_GRANTED")
        registered=[row for row in report["registered"] if row.get("target_id")]
        self.assertEqual(len(registered),5)
        self.assertTrue(all(row["registration_scope"]=="SYNTHETIC_TASK_EXECUTION_ONLY" for row in registered))
        self.assertTrue(all(row["certification"]=="NOT_GRANTED" for row in registered))
        self.assertEqual(report["registered"][-1]["status"],"PLAN_ONLY_FAIL_CLOSED")
        self.assertEqual(report["pdf_generation"],"NOT_REGISTERED")
    def test_unique_contracts_and_weight_pins(self):
        self.assertEqual(len(adapters.ADAPTERS),5)
        self.assertEqual(len({x["id"] for x in adapters.ADAPTERS.values()}),5)
        for x in adapters.ADAPTERS.values():
            self.assertEqual(len(x["sha"]),64);self.assertGreater(x["bytes"],0)
    def test_unknown_domain_operation_and_bad_schema_fail_closed(self):
        rows=[(req("D99_UNKNOWN","work"),"DOMAIN_TASK_ADAPTER_NOT_REGISTERED"),
              (req("D01_CEREBRO","translate_text",prompt="Hello"),"DOMAIN_OPERATION_NOT_REGISTERED"),
              ({"schema":"WRONG"},"REQUEST_SCHEMA_MISMATCH")]
        for row,pattern in rows:
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(adapters.AdapterError,pattern):adapters.normalize(row,RUNTIME)
    def test_input_and_token_limits(self):
        with self.assertRaisesRegex(adapters.AdapterError,"INPUT_TEXT_REQUIRED"):adapters.normalize(req(prompt=" "),RUNTIME)
        row=req(prompt="Hello");row["limits"]["max_new_tokens"]=129
        with self.assertRaisesRegex(adapters.AdapterError,"MAX_NEW_TOKENS_OUT_OF_RANGE"):adapters.normalize(row,RUNTIME)
    def test_translation_language_normalization_and_same_language_guard(self):
        row=adapters.normalize(req("D04_TRADUCTOR_INTELIGENTE","translate_text",text="Hi",src_lang="en",tgt_lang="es"),RUNTIME)
        self.assertEqual(row["input"]["src_lang"],"eng");self.assertEqual(row["input"]["tgt_lang"],"spa")
        with self.assertRaisesRegex(adapters.AdapterError,"SOURCE_AND_TARGET_LANGUAGE_IDENTICAL"):
            adapters.normalize(req("D04_TRADUCTOR_INTELIGENTE","translate_text",text="Hi",src_lang="eng",tgt_lang="en"),RUNTIME)
    def test_input_files_require_supported_format_and_reject_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);audio=root/"audio.wav";audio.write_bytes(b"audio")
            image=root/"image.png";image.write_bytes(b"image")
            self.assertEqual(adapters.normalize(req("D03_TRANSCRIPCION","transcribe_audio",audio_path=str(audio)),RUNTIME)["input_files"][0]["field"],"audio_path")
            self.assertEqual(adapters.normalize(req("D05_INTELIGENCIA_DOCUMENTAL","extract_document_image",image_path=str(image)),RUNTIME)["input_files"][0]["field"],"image_path")
            with self.assertRaisesRegex(adapters.AdapterError,"INPUT_FILE_FORMAT_NOT_SUPPORTED"):
                adapters.normalize(req("D03_TRANSCRIPCION","transcribe_audio",audio_path=str(image)),RUNTIME)
            link=root/"linked.wav";link.symlink_to(audio)
            with self.assertRaisesRegex(adapters.AdapterError,"SYMLINK_PATH_REJECTED"):
                adapters.normalize(req("D03_TRANSCRIPCION","transcribe_audio",audio_path=str(link)),RUNTIME)
    def test_execution_is_shell_free_offline_and_does_not_echo_prompt(self):
        row=req(prompt="PRIVATE_PROMPT_MUST_NOT_APPEAR")
        completed=subprocess.CompletedProcess(args=["python"],returncode=0,
            stdout=json.dumps({"status":"PASS_TASK_GENERATION","output_text":"A repository stores versioned files.","generated_token_count":2}),stderr="")
        integrity={"target_id":"D01_CEREBRO_ROOT","module_tree_sha256":"a"*64,"module_file_count":1,"module_bytes":10,
            "weight_manifest_sha256":"b"*64,"weight_path":"weight","weight_bytes":1,"weight_sha256":"c"*64}
        with patch.object(adapters,"verify_integrity",return_value=integrity),patch.object(adapters.subprocess,"run",return_value=completed) as run:
            result,code=adapters.execute_task(row,RUNTIME,60)
        self.assertEqual(code,0);self.assertEqual(result["status"],"PASS_FUNCTIONAL_EXECUTION")
        self.assertEqual(result["target_id"],"D01_CEREBRO_ROOT")
        self.assertFalse(run.call_args.kwargs["shell"]);self.assertIn("--task-json-stdin",run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs["env"]["HF_HUB_OFFLINE"],"1")
        self.assertNotIn("PRIVATE_PROMPT_MUST_NOT_APPEAR",json.dumps(result))
        self.assertEqual(result["certification"],"NOT_GRANTED")
    def test_orchestration_never_executes_plan(self):
        result,code=adapters.execute_task(req("D02_ORQUESTACION","route_plan",request_text="transcribe audio"),RUNTIME,60)
        self.assertEqual(code,3);self.assertIn(result["status"],{"PLAN_ONLY_BLOCKED","PLAN_READY_NOT_EXECUTED"})
        self.assertIsNone(result["target_id"])
        self.assertFalse(result["execution_authorized"])
    def test_runtime_cli_exposes_execute_task(self):
        result=subprocess.run([sys.executable,"-B",str(RUNTIME/"cajita_runtime.py"),"execute-task","--help"],
            capture_output=True,text=True,timeout=10,check=False)
        self.assertEqual(result.returncode,0,msg=result.stderr);self.assertIn("--request-json",result.stdout)
if __name__=="__main__":unittest.main(verbosity=2)
