from __future__ import annotations
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from louksnapg_whisper_fullrank_quantization import resolve_artifact_root
class WhisperArtifactLayoutTests(unittest.TestCase):
    def test_direct_layout(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            self.assertEqual(resolve_artifact_root(p),p.resolve())
    def test_nested_github_artifact_layout(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"artifact"; p.mkdir(); (p/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            self.assertEqual(resolve_artifact_root(p.parent),p.resolve())
    def test_ambiguous_layout_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            (p/"artifact").mkdir(); (p/"artifact/fullrank_manifest.json").write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError,"WHISPER_ARTIFACT_ROOT_AMBIGUOUS"): resolve_artifact_root(p)
if __name__=="__main__": unittest.main()
