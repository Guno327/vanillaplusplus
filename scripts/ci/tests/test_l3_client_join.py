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


class TestParseGuiReply(unittest.TestCase):
    """#62 round 2: parse_gui_reply() is main()'s replacement for
    parse_gui_dump() in the gui-check loop - it must accept BOTH landed
    reply kinds as a pass, not just a screen dump (see its own docstring
    for why treating only the dump as a pass was itself a bug: 3 real L3
    runs landed the "no active screen" reply and still failed under the
    old check)."""

    def setUp(self):
        self.parse = _load_l3().parse_gui_reply
        self.NO_SCREEN = _load_l3().GUI_NO_SCREEN_TEXT

    def test_returns_none_when_no_reply_landed(self):
        self.assertIsNone(self.parse(""))
        self.assertIsNone(self.parse("[12:00:00] [Render thread/INFO]: nothing to see\n"))

    def test_launcher_rejection_is_not_a_landed_reply(self):
        self.assertIsNone(self.parse("Couldn't find command for '[gui]', did you mean 'help'?\n"))

    def test_no_screen_reply_is_a_pass(self):
        """The literal hmc-specifics answers with when Minecraft.getScreen()
        is null - jar-verified as a real, landed relay, and the EXPECTED
        answer for a healthy client with no menu open."""
        kind, text = self.parse(f"{self.NO_SCREEN}\n")
        self.assertEqual(kind, "none")
        self.assertEqual(text, self.NO_SCREEN)

    def test_screen_dump_is_a_pass(self):
        slice_ = "Screen: net.minecraft.client.gui.screens.TitleScreen\nButtons:\n"
        kind, text = self.parse(slice_)
        self.assertEqual(kind, "screen")
        self.assertTrue(text.startswith("Screen: net.minecraft.client.gui.screens.TitleScreen"))

    def test_stuck_loading_screen_still_reported_as_screen_kind(self):
        """The #49 regression this whole check exists to catch - a client
        stuck on ReceivingLevelScreen/GenericDirtMessageScreen - must still
        surface via the ("screen", ...) branch so the caller's regex check
        against it still fires. A real Minecraft client can never report
        GUI_NO_SCREEN_TEXT while stuck on one of these (they are real,
        non-null GuiScreen instances)."""
        slice_ = "Screen: net.minecraft.client.gui.screens.ReceivingLevelScreen\nButtons:\n"
        kind, text = self.parse(slice_)
        self.assertEqual(kind, "screen")
        self.assertIn("ReceivingLevelScreen", text)

    def test_last_landed_reply_wins_when_both_kinds_present(self):
        """Resends can land in either order across multiple attempts; only
        the chronologically LAST landed reply reflects current state."""
        mixed_none_last = (
            "Screen: net.minecraft.client.gui.screens.TitleScreen\n"
            f"{self.NO_SCREEN}\n"
        )
        kind, text = self.parse(mixed_none_last)
        self.assertEqual(kind, "none")

        mixed_screen_last = (
            f"{self.NO_SCREEN}\n"
            "Screen: net.minecraft.client.gui.screens.TitleScreen\n"
        )
        kind, text = self.parse(mixed_screen_last)
        self.assertEqual(kind, "screen")
        self.assertTrue(text.startswith("Screen: net.minecraft.client.gui.screens.TitleScreen"))


class TestGuiResendTuning(unittest.TestCase):
    """#62 round 2's other half: the resend budget/cadence themselves. Not
    testing main()'s live loop (that needs a real client), just the tuning
    constants it reads - regression coverage so a future edit can't
    accidentally shrink the budget back down without at least changing a
    visible, reviewed number."""

    def setUp(self):
        self.module = _load_l3()

    def test_gui_timeout_increased_from_original_45s(self):
        self.assertGreater(self.module.GUI_TIMEOUT_S, 45)

    def test_resend_cadence_is_at_least_as_fast_as_before(self):
        """Old cadence was effectively one resend every 2*4=8 seconds."""
        old_cadence_s = 2 * 4
        new_cadence_s = self.module.GUI_RESEND_POLL_S * self.module.GUI_RESEND_CHECKS
        self.assertLessEqual(new_cadence_s, old_cadence_s)

    def test_new_budget_allows_meaningfully_more_attempts_than_before(self):
        old_attempts = 45 // (2 * 4)
        new_attempts = self.module.GUI_TIMEOUT_S // (
            self.module.GUI_RESEND_POLL_S * self.module.GUI_RESEND_CHECKS
        )
        self.assertGreater(new_attempts, old_attempts * 2)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(_load_l3()))
    return tests


if __name__ == "__main__":
    unittest.main()
