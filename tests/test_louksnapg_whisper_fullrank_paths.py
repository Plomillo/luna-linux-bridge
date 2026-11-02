from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from louksnapg_whisper_fullrank_quantization import resolve_artifact_root
class WhisperArtifactLayoutTests(unittest.TestCase):
    def test_direct_manifest_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            self.assertEqual(resolve_artifact_root(root),root.resolve())
    def test_single_nested_artifact_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); nested=root/"artifact"; nested.mkdir()
            (nested/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            self.assertEqual(resolve_artifact_root(root),nested.resolve())
    def test_nested_lca_and_download_artifact_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); nested=root/"artifact"/"work"/"artifact"; nested.mkdir(parents=True)
            (nested/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            self.assertEqual(resolve_artifact_root(root/"artifact"),nested.resolve())
    def test_ambiguous_manifest_layout_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            nested=root/"artifact"; nested.mkdir()
            (nested/"fullrank_manifest.json").write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError,"WHISPER_ARTIFACT_ROOT_AMBIGUOUS"):
                resolve_artifact_root(root)
if __name__=="__main__": unittest.main()
