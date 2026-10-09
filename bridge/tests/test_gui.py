"""Regression tests for the installed desktop entry and bounded GUI behavior."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUI = ROOT / "bridge/gui.py"
DESKTOP = ROOT / "debian/louksna-linux-bridge.desktop"
LAUNCHER = ROOT / "debian/louksna-linux-bridge.louksna"
RULES = (ROOT / "debian/rules").read_text()
CONTROL = (ROOT / "debian/control").read_text()


class GuiPackageTests(unittest.TestCase):
    def test_gui_is_valid_python_without_opening_a_display(self):
        ast.parse(GUI.read_text(encoding="utf-8"))

    def test_desktop_launcher_targets_installed_command(self):
        desktop = DESKTOP.read_text(encoding="utf-8")
        self.assertIn("Name=LOUKSNA Linux Bridge", desktop)
        self.assertIn("Exec=/usr/bin/louksna", desktop)
        self.assertIn("Terminal=false", desktop)
        self.assertIn("debian/louksna-linux-bridge.desktop", RULES)
        self.assertIn("debian/louksna-linux-bridge.louksna", RULES)
        self.assertIn("/usr/share/applications/louksna-linux-bridge.desktop", RULES)

    def test_package_declares_tkinter_runtime_dependency(self):
        self.assertIn("python3-tk", CONTROL)

    def test_panel_does_not_claim_certification_or_execute_arbitrary_shell(self):
        source = GUI.read_text(encoding="utf-8")
        self.assertIn("NO CERTIFICADO", source)
        self.assertIn("G23/G24", source)
        self.assertNotIn("shell=True", source)
        self.assertIn('["systemctl", "is-active", SERVICE]', source)


if __name__ == "__main__":
    unittest.main()
