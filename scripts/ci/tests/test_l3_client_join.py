"""Fast-tier coverage for the pure helpers inside `scripts/tests/l3_client_join.py`.

L3 itself (a live client join against a booted server on the Incus host) can
never run in the fast tier, but its *parsing* logic is ordinary pure Python
and is exactly the part that failed silently in issue #62: the `gui` screen
check passed vacuously because nothing verified what a landed reply actually
looks like. `parse_gui_dump()` now carries that jar-verified ground truth in
its docstring as executable doctests; this module runs them on every PR so
the ground truth cannot rot unnoticed.

The L3 script is loaded by path rather than imported by name because
`scripts/tests/` is not a package and shares no import root with
`scripts/ci/`.
"""

import doctest
import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
L3_PATH = REPO_ROOT / "scripts" / "tests" / "l3_client_join.py"


def _load_l3():
    spec = importlib.util.spec_from_file_location("l3_client_join", L3_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestL3ScriptIsImportable(unittest.TestCase):
    def test_module_has_no_import_time_side_effects(self):
        """Importing the L3 script must be inert - it defines constants and
        functions and does its work only under main(). If that ever stops
        being true, this test breaks before the doctest suite below does
        something surprising (like launching a client)."""
        module = _load_l3()
        self.assertTrue(callable(module.parse_gui_dump))
        self.assertTrue(callable(module.main))


class TestParseGuiDump(unittest.TestCase):
    """Cases beyond the doctests, kept here rather than in the docstring so
    the docstring stays readable as documentation."""

    def setUp(self):
        self.parse = _load_l3().parse_gui_dump

    def test_returns_none_when_no_reply_landed(self):
        self.assertIsNone(self.parse(""))
        self.assertIsNone(self.parse("[12:00:00] [Render thread/INFO]: nothing to see\n"))

    def test_no_gui_displayed_reply_is_not_a_screen_dump(self):
        """hmc-specifics answers `gui` with this literal when no screen is up.
        That IS a successful relay, but it is not a screen dump, so the caller
        must keep resending rather than assert against it."""
        self.assertIsNone(self.parse("Minecraft is currently not displaying a Gui.\n"))

    def test_launcher_rejection_is_not_a_screen_dump(self):
        self.assertIsNone(self.parse("Couldn't find command for '[gui]', did you mean 'help'?\n"))

    def test_uses_the_last_dump_when_several_landed(self):
        """Duplicate `gui` deliveries are expected once the resend loop runs;
        the assertion must key on the most recent one, not the first."""
        slice_ = (
            "Screen: net.minecraft.client.gui.screens.ReceivingLevelScreen\n"
            "Buttons:\n\nTextFields:\n"
            "Screen: net.minecraft.client.gui.screens.inventory.InventoryScreen\n"
            "Buttons:\n\nTextFields:\n"
        )
        dump = self.parse(slice_)
        self.assertTrue(dump.startswith("Screen: net.minecraft.client.gui.screens.inventory."))
        self.assertNotIn("ReceivingLevelScreen", dump)

    def test_dump_is_returned_verbatim_from_the_marker_on(self):
        """The caller regex-searches the returned text for the failure
        screens, so everything after the marker has to survive intact."""
        slice_ = "noise\nScreen: some.Screen\nButtons:\n- Back\nTextFields:\n"
        self.assertEqual(self.parse(slice_), "Screen: some.Screen\nButtons:\n- Back\nTextFields:\n")


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(_load_l3()))
    return tests


if __name__ == "__main__":
    unittest.main()
