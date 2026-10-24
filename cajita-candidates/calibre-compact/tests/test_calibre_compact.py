import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

MODULE_PATH = Path(__file__).resolve().parents[1] / "calibre_compact.py"
SPEC = importlib.util.spec_from_file_location("calibre_compact", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class FormatPolicyTests(unittest.TestCase):
    def test_pdf_to_epub_allowed(self):
        module.validate_format_pair(Path("input.pdf"), Path("output.epub"))

    def test_epub_to_pdf_allowed(self):
        module.validate_format_pair(Path("input.epub"), Path("output.pdf"))

    def test_markdown_to_epub_allowed(self):
        module.validate_format_pair(Path("input.md"), Path("output.epub"))

    def test_reject_unsupported_input(self):
        with self.assertRaises(module.CandidateError):
            module.validate_format_pair(Path("input.mobi"), Path("output.epub"))

    def test_reject_unsupported_output(self):
        with self.assertRaises(module.CandidateError):
            module.validate_format_pair(Path("input.epub"), Path("output.mobi"))

    def test_reject_same_format(self):
        with self.assertRaises(module.CandidateError):
            module.validate_format_pair(Path("input.epub"), Path("output.epub"))


class ArtifactValidationTests(unittest.TestCase):
    def test_pdf_magic(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.pdf"
            path.write_bytes(b"%PDF-1.7\n" + b"x" * 200)
            module.validate_output(path, ".pdf")

    def test_reject_invalid_pdf(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.pdf"
            path.write_bytes(b"not a pdf" + b"x" * 200)
            with self.assertRaises(module.CandidateError):
                module.validate_output(path, ".pdf")

    def test_epub_container(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.epub"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "mimetype",
                    "application/epub+zip",
                    compress_type=zipfile.ZIP_STORED,
                )
                archive.writestr(
                    "META-INF/container.xml",
                    '<?xml version="1.0"?><container><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
                )
                archive.writestr("OEBPS/content.opf", "<package></package>")
                archive.writestr("OEBPS/content.xhtml", "<html><body>fixture</body></html>")
            module.validate_output(path, ".epub")

    def test_reject_epub_without_first_mimetype(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.epub"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", "x")
                archive.writestr("mimetype", "application/epub+zip")
                archive.writestr("OEBPS/content.opf", "<package/>")
            with self.assertRaises(module.CandidateError):
                module.validate_output(path, ".epub")


if __name__ == "__main__":
    unittest.main(verbosity=2)
