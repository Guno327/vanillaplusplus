import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lint_rhino  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestFindTryScopedDeclarations(unittest.TestCase):
    def test_const_directly_in_try_is_flagged(self):
        text = """
        function f() {
            try {
                const x = 1
            } catch (e) {}
        }
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][2], "const")

    def test_const_in_catch_is_exempt(self):
        text = """
        try {
            doSomething()
        } catch (e) {
            const fallback = [1, 2, 3]
        }
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_const_in_finally_is_exempt(self):
        text = """
        try {
            doSomething()
        } finally {
            const cleanup = true
        }
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_const_in_nested_function_inside_try_is_exempt(self):
        text = """
        try {
            array.forEach(function (item) {
                const x = item
            })
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_const_in_nested_block_inside_try_is_exempt(self):
        text = """
        try {
            if (condition) {
                const x = 1
            }
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_let_directly_in_try_is_not_flagged(self):
        # Ground truth (DECISIONS.md #8's own before/after fix verification,
        # plus the entire codebase's established convention): `let` directly
        # in a try body is the correct, boot-verified-safe pattern, unlike
        # `const`. See lint_rhino.py's module docstring for the full
        # reasoning behind not flagging `let`.
        text = """
        try {
            let x = 1
            let y = 2
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_for_of_const_header_directly_in_try_is_exempt(self):
        text = """
        try {
            for (const nodeId of nodeIds) {
                doThing(nodeId)
            }
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_for_classic_const_header_directly_in_try_is_exempt(self):
        text = """
        try {
            for (const i = 0; i < 10; i++) {
                doThing(i)
            }
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_const_in_nested_try_is_flagged(self):
        text = """
        try {
            try {
                const inner = 1
            } catch (e2) {}
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(len(findings), 1)

    def test_const_outside_any_try_is_not_flagged(self):
        text = """
        const TOP_LEVEL = 1
        function f() {
            const inFunction = 2
        }
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_const_inside_string_or_comment_is_not_flagged(self):
        text = """
        try {
            // const fake = 1
            /* const alsoFake = 2 */
            let real = "try { const x = 1 }"
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_const_inside_template_literal_is_not_flagged(self):
        text = """
        try {
            let msg = `value is ${x} in try { const y = 1 }`
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(findings, [])

    def test_multiple_const_in_try_are_all_flagged(self):
        text = """
        try {
            const a = 1
            const b = 2
        } catch (e) {}
        """
        findings = lint_rhino.find_try_scoped_declarations(text)
        self.assertEqual(len(findings), 2)


class TestLintRhinoCli(unittest.TestCase):
    def test_clean_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            kubejs = Path(tmp) / "pack" / "kubejs" / "server_scripts"
            kubejs.mkdir(parents=True)
            (kubejs / "clean.js").write_text(
                "try {\n    let x = 1\n} catch (e) {}\n", encoding="utf-8"
            )
            self.assertEqual(lint_rhino.main([tmp]), 0)

    def test_dirty_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            kubejs = Path(tmp) / "pack" / "kubejs" / "server_scripts"
            kubejs.mkdir(parents=True)
            (kubejs / "dirty.js").write_text(
                "try {\n    const x = 1\n} catch (e) {}\n", encoding="utf-8"
            )
            self.assertEqual(lint_rhino.main([tmp]), 1)

    def test_real_repo_kubejs_tree_passes(self):
        kubejs_dir = REPO_ROOT / "pack" / "kubejs"
        if not kubejs_dir.is_dir():
            self.skipTest(f"not running inside the repo (no kubejs/ found at {kubejs_dir})")
        self.assertEqual(lint_rhino.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
