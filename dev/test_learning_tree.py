#!/usr/bin/env python3
"""Regression tests for the learning-tree scripts. Standard library only.

Run:  python3 dev/test_learning_tree.py            (from the project root)
      python3 dev/test_learning_tree.py -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SK = ROOT / "learning-tree"
SCRIPTS = SK / "scripts"
EXAMPLE = SK / "assets" / "example-tree"
sys.path.insert(0, str(SCRIPTS))

import check_links  # noqa: E402
import canvas_export  # noqa: E402
import export  # noqa: E402
import treelib  # noqa: E402
from validate_tree import validate  # noqa: E402


def run(script, *args, check=False):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                       capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError(f"{script} failed: {r.stderr}{r.stdout}")
    return r


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tree = self.tmp / "tree"
        shutil.copytree(EXAMPLE, self.tree)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def progress(self):
        t, b = treelib.load_tree(self.tree)
        return treelib.compute_progress(t, b)

    def node(self, res, nid):
        return next(r for g in res["gears"] for r in g["nodes"] if r["id"] == nid)


class TestExampleTree(Base):
    def test_example_is_clean(self):
        t, b = treelib.load_tree(self.tree)
        errors, warnings = validate(t, b)
        self.assertEqual((errors, warnings), ([], []))

    def test_progress_numbers(self):
        res = self.progress()
        self.assertEqual(res["percent"], 6.2)
        self.assertEqual(self.node(res, "git-basics:mental-model")["status"], "done")
        self.assertEqual(self.node(res, "git-basics:branching")["status"], "locked")
        self.assertEqual(res["next"][0]["id"], "git-basics:commits-history")


class TestCountingRules(Base):
    def write(self, name, body):
        p = self.tree / "nodes" / name
        p.write_text(body, encoding="utf-8")
        return p

    def test_optional_alternatives_and_fences_do_not_count(self):
        p = self.write("x.md", "---\nid: git-basics:x\n---\n# X\n## Alternatives (optional)\n- [ ] not counted\n"
                       "## Todos\n- [x] real\n- [ ] stretch (optional)\n```\n- [ ] in fence\n```\n- [ ] real two\n")
        info = treelib.parse_node_file(p)
        self.assertEqual((info["checked"], info["total"]), (1, 2))

    def test_acceptance_criteria_count_and_emoji_heading(self):
        p = self.write("y.md", "# Y\n## ✅ Todos\n- [x] a\n### Sub\n- [ ] b\n## Acceptance criteria\n- [ ] c\n")
        self.assertEqual(treelib.parse_node_file(p)["total"], 3)

    def test_skipped_excluded_from_percentage(self):
        t, b = treelib.load_tree(self.tree)
        before = treelib.compute_progress(t, b)["percent"]
        for n in t["nodes"]:
            if n["id"] == "git-basics:branching":
                n["skipped"] = True
        after = treelib.compute_progress(t, b)
        self.assertGreater(after["percent"], before)
        self.assertEqual(self.node(after, "git-basics:branching")["status"], "skipped")

    def test_unexpanded_gears_keep_overall_below_100(self):
        t, b = treelib.load_tree(self.tree)
        for n in t["nodes"]:
            if n["type"] in ("skill", "capstone"):
                n["done"] = True
        for f in (self.tree / "nodes").glob("*.md"):
            f.write_text(f.read_text().replace("- [ ]", "- [x]"), encoding="utf-8")
        res = treelib.compute_progress(t, b)
        self.assertEqual(res["gears"][0]["percent"], 100.0)
        self.assertLess(res["percent"], 50)

    def test_cycle_detected(self):
        t, b = treelib.load_tree(self.tree)
        for n in t["nodes"]:
            if n["id"] == "git-basics:mental-model":
                n["requires"] = ["git-basics:branching"]
        errors, _ = validate(t, b)
        self.assertTrue(any("cycle" in e for e in errors))


class TestValidatorWarnings(Base):
    def warnings(self):
        t, b = treelib.load_tree(self.tree)
        return validate(t, b)[1]

    def test_primary_checks(self):
        p = self.tree / "nodes" / "branching.md"
        t = p.read_text()
        p.write_text(t.replace("(https://example.com/video-5)", "").replace("(https://example.com/article-4)", ""), encoding="utf-8")
        self.assertTrue(any("no link" in w for w in self.warnings()))

    def test_fill_placeholders_flagged(self):
        r = run("edit_tree.py", self.tree, "add", "skill", "x1", "--title", "X", "--parent", "foundations",
                "--hours", 2, "--scaffold")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any("<fill:" in w for w in self.warnings()))


class TestEditTree(Base):
    def test_tick_by_index_text_range_and_roundtrip(self):
        n = self.tree / "nodes" / "commits-history.md"
        orig = n.read_text()
        self.assertEqual(run("edit_tree.py", self.tree, "tick", "commits-history", "2-3").returncode, 0)
        self.assertEqual(self.node(self.progress(), "git-basics:commits-history")["checked"], 3)
        self.assertEqual(run("edit_tree.py", self.tree, "untick", "commits-history", "2-3").returncode, 0)
        self.assertEqual(n.read_text(), orig)

    def test_ambiguous_and_out_of_range_change_nothing(self):
        n = self.tree / "nodes" / "commits-history.md"
        orig = n.read_text()
        self.assertEqual(run("edit_tree.py", self.tree, "tick", "commits-history", "9").returncode, 1)
        self.assertEqual(run("edit_tree.py", self.tree, "tick", "commits-history", "e").returncode, 1)
        self.assertEqual(run("edit_tree.py", self.tree, "tick", "no-such-node", "1").returncode, 1)
        self.assertEqual(n.read_text(), orig)

    def test_skip_roundtrip_leaves_tree_json_byte_identical(self):
        orig = (self.tree / "tree.json").read_text()
        run("edit_tree.py", self.tree, "skip", "branching", check=True)
        self.assertIn('"skipped": true', (self.tree / "tree.json").read_text())
        run("edit_tree.py", self.tree, "unskip", "branching", check=True)
        self.assertEqual((self.tree / "tree.json").read_text(), orig)

    def test_add_rejects_duplicates_and_unknown_parent(self):
        self.assertEqual(run("edit_tree.py", self.tree, "add", "skill", "branching", "--title", "d",
                             "--parent", "foundations").returncode, 1)
        self.assertEqual(run("edit_tree.py", self.tree, "add", "skill", "q", "--title", "d",
                             "--parent", "nope").returncode, 1)

    def test_invalid_result_is_not_written(self):
        orig = (self.tree / "tree.json").read_text()
        r = run("edit_tree.py", self.tree, "add", "skill", "z", "--title", "z", "--parent", "foundations",
                "--requires", "git-basics:ghost", "--hours", 2, "--scaffold")
        self.assertEqual(r.returncode, 1)
        self.assertEqual((self.tree / "tree.json").read_text(), orig)
        self.assertFalse((self.tree / "nodes" / "z.md").exists())

    def test_minimal_mode_done_flag(self):
        d = self.tmp / "mini"
        d.mkdir()
        (d / "tree.json").write_text(json.dumps({
            "schema_version": 1, "tree_id": "mini", "title": "M", "config": {"mode": "minimal"},
            "nodes": [{"id": "mini:a", "type": "gear", "title": "A", "parent": None, "requires": []},
                      {"id": "mini:a1", "type": "skill", "title": "A1", "parent": "mini:a", "requires": [], "est_hours": 2}]}))
        run("edit_tree.py", d, "tick", "a1", check=True)
        self.assertTrue(json.loads((d / "tree.json").read_text())["nodes"][1]["done"])
        run("edit_tree.py", d, "untick", "a1", check=True)
        self.assertNotIn("done", json.loads((d / "tree.json").read_text())["nodes"][1])


class TestExport(Base):
    def test_links_idempotent_and_do_not_change_progress(self):
        before = self.progress()["percent"]
        run("export.py", self.tree, "--no-zip", check=True)
        snap = {p.name: p.read_text() for p in (self.tree / "nodes").glob("*.md")}
        r = run("export.py", self.tree, "--no-zip", check=True)
        self.assertNotIn("Updated link block", r.stdout)
        self.assertEqual(snap, {p.name: p.read_text() for p in (self.tree / "nodes").glob("*.md")})
        self.assertEqual(self.progress()["percent"], before)
        self.assertIn("Unlocks: [Capstone", snap["branching.md"])

    def test_no_node_links_flag(self):
        orig = (self.tree / "nodes" / "branching.md").read_text()
        run("export.py", self.tree, "--no-zip", "--no-node-links", check=True)
        self.assertEqual((self.tree / "nodes" / "branching.md").read_text(), orig)

    def test_zip_skips_symlinks(self):
        secret = self.tmp / "secret.txt"
        secret.write_text("do not ship")
        try:
            (self.tree / "leak.txt").symlink_to(secret)
        except OSError:
            self.skipTest("symlinks unavailable")
        out = self.tmp / "o.zip"
        run("export.py", self.tree, "-o", out, check=True)
        import zipfile
        names = zipfile.ZipFile(out).namelist()
        self.assertFalse(any("leak.txt" in n for n in names))
        self.assertTrue(any(n.endswith("tree.json") for n in names))

    def test_canvas_structure(self):
        t, b = treelib.load_tree(self.tree)
        c = canvas_export.build_canvas(t, treelib.compute_progress(t, b), "Learning/git")
        ids = [n["id"] for n in c["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in c["edges"]:
            self.assertIn(e["fromNode"], ids)
            self.assertIn(e["toNode"], ids)
        self.assertEqual(sum(1 for n in c["nodes"] if n["type"] == "group"), 4)
        self.assertTrue(any("[[Learning/git/nodes/mental-model|open]]" in n.get("text", "") for n in c["nodes"]))


class TestLinkChecker(unittest.TestCase):
    def setUp(self):
        check_links.ALLOW_PRIVATE = False

    def test_private_addresses_are_skipped_by_default(self):
        for u in ("http://127.0.0.1:9/x", "http://localhost/x", "http://192.168.1.1/x", "http://169.254.169.254/"):
            r = check_links.check_url(u, timeout=1)
            self.assertEqual(r["status"], "blocked", u)

    def test_redirect_handler_refuses_private_and_non_http(self):
        h = check_links._SafeRedirect()
        for target in ("http://127.0.0.1/x", "ftp://example.com/x", "file:///etc/passwd"):
            with self.assertRaises(Exception):
                h.redirect_request(None, None, 302, "", {}, target)

    def test_url_extraction_and_youtube_detection(self):
        self.assertEqual(check_links.extract_urls("see (https://a.com/x_(y)) and https://b.com."),
                         ["https://a.com/x_(y)", "https://b.com"])
        self.assertTrue(check_links.is_youtube("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(check_links.is_youtube("https://youtu.be/abc"))
        self.assertFalse(check_links.is_youtube("https://youtube.com/@channel"))


if __name__ == "__main__":
    unittest.main()
