import unittest
from pathlib import Path
from audit_source import parse_slt_listing, safe_member_path


class ArchiveSafetyTests(unittest.TestCase):
    def test_parse_slt_listing_excludes_archive_header(self):
        archive = Path("input.7z")
        output = """Path = input.7z
Type = 7z
Physical Size = 12

Path = bible.pdf
Size = 100
Folder = -

Path = folder
Size = 0
Folder = +
"""
        entries = parse_slt_listing(output, archive)
        self.assertEqual([e["Path"] for e in entries], ["bible.pdf", "folder"])

    def test_safe_relative_path(self):
        self.assertTrue(safe_member_path({"Path": "Books/Genesis.pdf"}))
        self.assertFalse(safe_member_path({"Path": "../outside.pdf"}))
        self.assertFalse(safe_member_path({"Path": "/absolute.pdf"}))
        self.assertFalse(safe_member_path({"Path": "C:\\outside.pdf"}))
        self.assertFalse(safe_member_path({"Path": "link", "Symbolic Link": "target"}))


if __name__ == "__main__":
    unittest.main()
