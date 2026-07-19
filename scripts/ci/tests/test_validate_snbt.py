import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validate_snbt import (  # noqa: E402
    NbtArray,
    SNBTError,
    check_file,
    find_files,
    main,
    parse_snbt,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestParseSnbtValid(unittest.TestCase):
    def test_simple_compound(self):
        self.assertEqual(parse_snbt('{"a": 1, "b": "two"}'), {"a": 1, "b": "two"})

    def test_unquoted_keys_and_no_commas(self):
        text = """
        {
            ally_mode: "default"
            disable_protection: false
            count: 20
        }
        """
        self.assertEqual(
            parse_snbt(text),
            {"ally_mode": "default", "disable_protection": False, "count": 20},
        )

    def test_line_comments_are_ignored(self):
        text = """
        { # a leading comment
            a: 1 # trailing comment
            # a standalone comment line
            b: 2
        }
        """
        self.assertEqual(parse_snbt(text), {"a": 1, "b": 2})

    def test_number_type_suffixes(self):
        result = parse_snbt("{a: 1b, b: 2s, c: 3l, d: 1.5f, e: 2.5d, f: 42}")
        self.assertEqual(result, {"a": 1, "b": 2, "c": 3, "d": 1.5, "e": 2.5, "f": 42})

    def test_booleans(self):
        self.assertEqual(parse_snbt("{a: true, b: false}"), {"a": True, "b": False})

    def test_nested_compound_and_list(self):
        result = parse_snbt('{a: {x: 1, y: [1, 2, 3]}, b: []}')
        self.assertEqual(result, {"a": {"x": 1, "y": [1, 2, 3]}, "b": []})

    def test_single_and_double_quoted_strings_with_escapes(self):
        text = "{a: \"line\\nbreak\", b: 'it\\'s'}"
        result = parse_snbt(text)
        self.assertEqual(result["a"], "line\nbreak")
        self.assertEqual(result["b"], "it's")

    def test_typed_int_array(self):
        result = parse_snbt("{arr: [I; 1, 2, 3]}")
        self.assertIsInstance(result["arr"], NbtArray)
        self.assertEqual(result["arr"].array_type, "I")
        self.assertEqual(list(result["arr"]), [1, 2, 3])

    def test_typed_byte_and_long_arrays(self):
        result = parse_snbt("{b: [B; 1, 2], l: [L; 100, 200]}")
        self.assertEqual(result["b"].array_type, "B")
        self.assertEqual(result["l"].array_type, "L")

    def test_empty_typed_array(self):
        result = parse_snbt("{arr: [I;]}")
        self.assertEqual(list(result["arr"]), [])

    def test_plain_list_of_letters_is_not_mistaken_for_typed_array(self):
        # No semicolon after the first element -> plain 3-element list, not
        # a typed array, even though "I" happens to match a type letter.
        result = parse_snbt('{arr: ["I", "B", "L"]}')
        self.assertEqual(result["arr"], ["I", "B", "L"])
        self.assertNotIsInstance(result["arr"], NbtArray)

    def test_bare_top_level_compound_no_wrapping_braces(self):
        text = """
        a: 1
        b: "two"
        nested: { x: 1 }
        """
        self.assertEqual(parse_snbt(text), {"a": 1, "b": "two", "nested": {"x": 1}})

    def test_empty_file_parses_to_empty_compound(self):
        self.assertEqual(parse_snbt(""), {})

    def test_trailing_commas_between_members_are_optional_and_tolerated(self):
        # comma present between some members, absent between others
        result = parse_snbt("{a: 1, b: 2\nc: 3}")
        self.assertEqual(result, {"a": 1, "b": 2, "c": 3})


class TestParseSnbtErrors(unittest.TestCase):
    def test_unbalanced_brace_missing_close(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{"a": 1')

    def test_unbalanced_bracket_missing_close(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{"a": [1, 2, 3}')

    def test_unterminated_quoted_string(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{"a": "unterminated}')

    def test_unterminated_single_quoted_string(self):
        with self.assertRaises(SNBTError):
            parse_snbt("{a: 'unterminated}")

    def test_typed_array_with_non_number_element(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{arr: [I; 1, "not a number"]}')

    def test_typed_array_with_nested_compound_element(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{arr: [I; {a: 1}]}')

    def test_missing_colon_after_key(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{a 1}')

    def test_trailing_garbage_after_top_level_compound(self):
        with self.assertRaises(SNBTError):
            parse_snbt('{a: 1} garbage')

    def test_invalid_escape_sequence(self):
        with self.assertRaises(SNBTError):
            parse_snbt(r'{a: "bad \q escape"}')

    def test_error_reports_line_and_column(self):
        try:
            parse_snbt('{\n  "a": 1\n')
        except SNBTError as e:
            self.assertGreaterEqual(e.line, 1)
            self.assertGreaterEqual(e.col, 1)
        else:
            self.fail("expected SNBTError")


class TestValidateSnbtCli(unittest.TestCase):
    def test_valid_snbt_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir()
            (pack / "good.snbt").write_text('{a: 1, b: "two"}', encoding="utf-8")
            self.assertEqual(main([tmp]), 0)

    def test_ftbchunks_style_file_with_comments_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir()
            (pack / "ftbchunks-world.snbt").write_text(
                "# comment\n{\n\tally_mode: \"default\"\n\tflag: false\n}\n",
                encoding="utf-8",
            )
            self.assertEqual(main([tmp]), 0)

    def test_broken_snbt_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir()
            (pack / "broken.snbt").write_text('{a: 1', encoding="utf-8")
            self.assertEqual(main([tmp]), 1)

    def test_check_file_returns_none_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.snbt"
            path.write_text("{a: 1}", encoding="utf-8")
            self.assertIsNone(check_file(path))

    def test_check_file_returns_error_string_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.snbt"
            path.write_text("{a: 1", encoding="utf-8")
            err = check_file(path)
            self.assertIsNotNone(err)
            self.assertIn("line", err)

    def test_find_files_recurses(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            (pack / "sub" / "deeper").mkdir(parents=True)
            (pack / "a.snbt").write_text("{a: 1}", encoding="utf-8")
            (pack / "sub" / "deeper" / "b.snbt").write_text("{b: 2}", encoding="utf-8")
            (pack / "not_snbt.json").write_text("{}", encoding="utf-8")
            files = find_files(pack)
            self.assertEqual(len(files), 2)

    def test_real_repo_tree_passes(self):
        pack_dir = REPO_ROOT / "pack"
        if not pack_dir.is_dir():
            self.skipTest(f"not running inside the repo (no pack/ found at {pack_dir})")
        self.assertEqual(main([str(REPO_ROOT)]), 0)

    def test_real_ftbchunks_file_parses(self):
        path = REPO_ROOT / "pack" / "config" / "ftbchunks-world.snbt"
        if not path.is_file():
            self.skipTest(f"not running inside the repo (file not found: {path})")
        self.assertIsNone(check_file(path))


if __name__ == "__main__":
    unittest.main()
