import os
import tempfile
import unittest

from skill_diff_classify.structural import (
    find_skill_files,
    diff_frontmatter,
    diff_scripts,
    run_structural_pass,
)


class TestFindSkillFiles(unittest.TestCase):
    def test_finds_skill_md_and_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SKILL.md"), "w") as f:
                f.write("---\nallowed-tools: [read, write]\n---\n\nHello world.")
            with open(os.path.join(tmpdir, "helper.py"), "w") as f:
                f.write("def run(): pass\n")

            result = find_skill_files(tmpdir)
            self.assertIsNotNone(result["skill_md"])
            self.assertEqual(len(result["scripts"]), 1)
            self.assertIsNotNone(result["frontmatter"])

    def test_no_skill_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "helper.py"), "w") as f:
                f.write("def run(): pass\n")

            result = find_skill_files(tmpdir)
            self.assertIsNone(result["skill_md"])
            self.assertIsNone(result["frontmatter"])


class TestDiffFrontmatter(unittest.TestCase):
    def test_no_frontmatter(self):
        self.assertEqual(diff_frontmatter(None, None), [])

    def test_frontmatter_added(self):
        result = diff_frontmatter(None, "allowed-tools: [read]")
        self.assertTrue(any("Frontmatter added" in f for f in result))

    def test_frontmatter_removed(self):
        result = diff_frontmatter("allowed-tools: [read]", None)
        self.assertTrue(any("Frontmatter removed" in f for f in result))

    def test_frontmatter_unchanged(self):
        fm = "allowed-tools: [read, write]"
        self.assertEqual(diff_frontmatter(fm, fm), [])

    def test_frontmatter_changed(self):
        old = "allowed-tools: [read]\n"
        new = "allowed-tools: [read, write]\n"
        result = diff_frontmatter(old, new)
        self.assertTrue(any("write" in f for f in result))


class TestDiffScripts(unittest.TestCase):
    def test_no_scripts(self):
        self.assertEqual(diff_scripts([], []), [])

    def test_script_added(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "new.py")
            with open(path, "w") as f:
                f.write("def run(): pass\n")
            self.assertEqual(diff_scripts([], [path]), ["Script added: new.py"])

    def test_script_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "old.py")
            with open(path, "w") as f:
                f.write("def run(): pass\n")
            self.assertEqual(diff_scripts([path], []), ["Script removed: old.py"])

    def test_script_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "same.py")
            with open(path, "w") as f:
                f.write("def run(): pass\n")
            self.assertEqual(diff_scripts([path], [path]), [])

    def test_script_changed(self):
        with tempfile.TemporaryDirectory() as old_dir:
            with tempfile.TemporaryDirectory() as new_dir:
                old_path = os.path.join(old_dir, "tool.py")
                new_path = os.path.join(new_dir, "tool.py")
                with open(old_path, "w") as f:
                    f.write("def run(): return 'old'\n")
                with open(new_path, "w") as f:
                    f.write("def run(): return 'new'\n")
                result = diff_scripts([old_path], [new_path])
                self.assertTrue(any("tool.py" in f for f in result))


class TestRunStructuralPass(unittest.TestCase):
    def test_identical_dirs(self):
        with tempfile.TemporaryDirectory() as d1:
            with tempfile.TemporaryDirectory() as d2:
                for d in [d1, d2]:
                    with open(os.path.join(d, "SKILL.md"), "w") as f:
                        f.write("---\nallowed-tools: [read]\n---\n\nDo things.")
                result = run_structural_pass(d1, d2)
                self.assertEqual(result["findings"], [])
                self.assertFalse(result["undeterminable"])

    def test_no_skill_md_in_either(self):
        with tempfile.TemporaryDirectory() as d1:
            with tempfile.TemporaryDirectory() as d2:
                result = run_structural_pass(d1, d2)
                self.assertTrue(result["undeterminable"])