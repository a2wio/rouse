"""What proves `addons/` does what spec/ says — writing records,
wiring the agent file, and the linter over both.

Run: python3 -m unittest discover -s rouse/tests -t .
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rouse import cli  # noqa: E402
from rouse.addons import scaffold, wire  # noqa: E402
from rouse.core import files, home, layout, levels  # noqa: E402
from rouse.tests.fixtures import LADDER, Tree  # noqa: E402


class Scaffold(Tree):
    def test_new_makes_a_directory_and_a_type_file(self):
        path = scaffold.new(self.memory, "intention", "verify-the-migration")
        self.assertEqual(path.name, "intention.md")
        self.assertEqual(path.parent.name, "verify-the-migration")
        self.assertEqual(path.parent.parent, self.memory / layout.INTENTIONS)
        self.assertEqual(files.head(path)["status"], "open")

    def test_new_under_a_slug_nests_it(self):
        scaffold.new(self.memory, "intention", "verify-it")
        path = scaffold.new(self.memory, "task", "run-it", under="verify-it")
        records = levels.Records(self.memory)
        self.assertEqual(records.parent(records.of("task")[0]).id,
                         "intention/verify-it")
        self.assertTrue(path.exists())

    def test_new_writes_a_belief_as_one_flat_file(self):
        path = scaffold.new(self.memory, "belief", "zero-downtime-deploys")
        self.assertEqual(path.parent, self.memory / layout.BELIEFS)
        self.assertEqual(path.name, "belief-zero-downtime-deploys.md")
        self.assertEqual(list(files.head(path)), [])

    def test_a_new_belief_has_an_empty_fence_and_nothing_in_it(self):
        """Nothing in a belief's header is the writer's — the fence is
        there so a wrapper can stamp `origin:` onto the one layer that
        goes into every single turn."""
        path = scaffold.new(self.memory, "belief", "plan-before-code")
        self.assertTrue(path.read_text().startswith("---\n---\n"))
        self.assertEqual(scaffold.blanks(path), [])
        files.set_fields(path, origin="owner")
        self.assertEqual(files.head(path)["origin"], "owner")

    def test_new_writes_a_motivation_with_the_field_that_has_a_reader(self):
        path = scaffold.new(self.memory, "motivation", "two-deploys-broke")
        self.assertEqual(list(files.head(path)), ["keywords"])

    def test_a_belief_cannot_be_put_under_anything(self):
        scaffold.new(self.memory, "intention", "verify-it")
        with self.assertRaises(ValueError):
            scaffold.new(self.memory, "belief", "x", under="verify-it")

    def test_new_puts_a_reminder_in_the_inventory(self):
        path = scaffold.new(self.memory, "reminder", "pay-the-invoice")
        self.assertEqual(path.parent.parent,
                         self.memory / layout.REMINDERS)

    def test_new_refuses_to_clobber(self):
        scaffold.new(self.memory, "intention", "x")
        with self.assertRaises(ValueError):
            scaffold.new(self.memory, "intention", "x")

    def test_promote_moves_the_directory_and_keeps_its_things(self):
        scaffold.new(self.memory, "backlog", "pin-the-runner")
        item = self.memory / layout.BACKLOG / "pin-the-runner"
        (item / "notes.txt").write_text("what was said\n")
        path = scaffold.promote(self.memory, "pin-the-runner")

        self.assertFalse(item.exists())
        self.assertEqual(path.name, "intention.md")
        self.assertTrue((path.parent / "notes.txt").exists())
        head = files.head(path)
        self.assertEqual(head["status"], "open")
        self.assertEqual(head["was"], f"{layout.BACKLOG}/pin-the-runner")
        self.assertTrue(head["promoted"])
        self.assertEqual([r.id for r in levels.Records(self.memory).all()],
                         ["intention/pin-the-runner"])

    def test_promote_lands_at_the_top_of_the_intentions(self):
        scaffold.new(self.memory, "backlog", "pin-the-runner")
        path = scaffold.promote(self.memory, "pin-the-runner")
        self.assertEqual(path.parent.parent, self.memory / layout.INTENTIONS)
        records = levels.Records(self.memory)
        self.assertIsNone(records.parent(records.of("intention")[0]))

    def test_the_tree_lists_context_flat_and_nests_the_records(self):
        self.module("belief", "zero-downtime")
        self.module("motivation", "keep-it-honest")
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{LADDER}/i/t", "task", {"status": "pending"})
        out = scaffold.render_tree(self.memory)
        self.assertEqual(out.splitlines(),
                         ["beliefs:",
                          "  zero-downtime",
                          "",
                          "motivations:",
                          "  keep-it-honest",
                          "",
                          "intention i  [open]",
                          "  task t  [pending]"])

    def test_new_persona_writes_the_root_file_with_an_empty_fence(self):
        path = scaffold.new(self.memory, "persona")
        self.assertEqual(path, self.memory / layout.PERSONA)
        self.assertEqual(files.head(path), {})
        self.assertEqual(scaffold.blanks(path), [])

    def test_the_persona_takes_no_name(self):
        """One voice per tree, said with a path. Two of them is two
        agents, and the second one wants its own tree."""
        with self.assertRaises(ValueError) as caught:
            scaffold.new(self.memory, "persona", "friendly")
        self.assertIn("one voice per tree", str(caught.exception))

    def test_the_persona_cannot_be_put_under_anything(self):
        with self.assertRaises(ValueError):
            scaffold.new(self.memory, "persona", None, "some-intention")

    def test_a_record_still_needs_a_name(self):
        with self.assertRaises(ValueError):
            scaffold.new(self.memory, "intention")

    def test_the_tree_says_there_is_a_persona_and_nothing_when_there_isnt(self):
        self.module("belief", "zero-downtime")
        self.assertNotIn("persona", scaffold.render_tree(self.memory))
        self.persona()
        self.assertIn("persona (how you talk", scaffold.render_tree(self.memory))


class Check(Tree):
    def check(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["check", "--memory", str(self.memory)])
        return code, buf.getvalue()

    def test_a_clean_tree_is_clean(self):
        (self.memory / layout.PROBES).write_text("")
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clean")

    def test_a_record_written_as_a_flat_file_is_caught(self):
        (self.memory / layout.PROBES).write_text("")
        (self.memory / LADDER / "verify-it.md").write_text(
            "---\nstatus: open\n---\n\nthe old shape\n")
        code, out = self.check()
        self.assertIn("a record is a directory holding <type>.md", out)

    def test_a_context_module_without_its_type_prefix_is_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        (self.memory / layout.BELIEFS / "zero-downtime.md").write_text(
            "---\n---\n\ndeploys stay up\n")
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("name it belief-zero-downtime.md", out)

    def test_a_clock_field_on_a_belief_is_flagged(self):
        """The whole misreading, caught by the linter: a belief with a
        status is somebody expecting it to be swept."""
        (self.memory / layout.PROBES).write_text("")
        self.module("belief", "x", header={"status": "held",
                                           "stale-after": "7d"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("context has no clock and no lifecycle", out)

    def test_keywords_on_a_belief_are_flagged(self):
        """The same family as a clock on a belief: a field whose only
        reader retrieves things, on the one layer that is never
        retrieved. Somebody expected their beliefs to be looked up."""
        (self.memory / layout.PROBES).write_text("")
        self.module("belief", "x", header={"keywords": "deploy, rollout"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("keywords on a belief — nothing reads them", out)

    def test_keywords_on_a_motivation_are_not(self):
        """Same field, one directory down, and there it has a reader."""
        (self.memory / layout.PROBES).write_text("")
        self.module("motivation", "x", header={"keywords": "deploy, prod"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clean")

    def test_no_persona_is_never_a_finding(self):
        """Optional is a rule. A tree without one is clean, and this is
        the test that stops somebody helpfully warning about it."""
        (self.memory / layout.PROBES).write_text("")
        self.module("belief", "x")
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clean")

    def test_a_persona_with_a_clock_is_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        self.persona(header={"status": "open", "stale-after": "7d"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("status, stale-after in a persona", out)

    def test_keywords_on_a_persona_are_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        self.persona(header={"keywords": "voice, tone"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("keywords on a persona — nothing reads them", out)

    def test_a_persona_anywhere_but_the_root_is_flagged(self):
        """It parses, it reads like the real thing, and nothing injects
        it — the layer is a fixed path."""
        (self.memory / layout.PROBES).write_text("")
        (self.memory / layout.ENTRYPOINT / "persona.md").write_text(
            "---\n---\n\nyou are terse\n")
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("the persona is one file at the tree root", out)

    def test_a_persona_at_the_root_is_clean(self):
        (self.memory / layout.PROBES).write_text("")
        self.persona()
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clean")

    def test_the_persona_is_paid_for_out_of_the_same_budget(self):
        """One number for all three layers: what is being defended is the
        per-turn bill, which doesn't care which file it came from."""
        (self.memory / layout.PROBES).write_text("")
        self.persona(body="v" * 5000)
        for i in range(4):
            self.module("belief", f"long-{i}", body="b" * 1000)
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("If everything is a belief, nothing is", out)
        self.assertIn("persona", out)
        self.assertIn("belief", out)

    def test_a_directory_under_beliefs_is_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        nested = self.memory / layout.BELIEFS / "deploys" / "belief-x.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("---\n---\n\nnested\n")
        code, out = self.check()
        self.assertIn("Nothing sits under a ground truth", out)

    def test_the_layer_below_is_the_one_directory_that_belongs(self):
        """`motivations/` inside `beliefs/` and `intentions/` inside
        `motivations/` are the nesting; everything else in there is a
        ground truth put inside a ground truth."""
        (self.memory / layout.PROBES).write_text("")
        self.module("belief", "zero-downtime")
        self.module("motivation", "denis-said-so")
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clean")

    def test_a_stray_directory_under_motivations_is_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        (self.memory / layout.MOTIVATIONS / "signals").mkdir(parents=True)
        code, out = self.check()
        self.assertIn("the only one that belongs here is intentions/", out)

    def test_too_much_context_is_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        for i in range(9):
            self.module("belief", f"long-{i}", body="x" * 1000)
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("If everything is a belief, nothing is", out)

    def test_an_intention_with_nothing_above_it_is_not_a_warning(self):
        """The orphan rule is gone with the lineage: there is nothing
        above an intention to be orphaned from."""
        (self.memory / layout.PROBES).write_text("")
        self.rec(f"{LADDER}/a", "intention",
                 {"status": "open", "closes-when": "x"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clean")

    def test_a_leftover_parent_field_is_flagged(self):
        (self.memory / layout.PROBES).write_text("")
        self.rec(f"{LADDER}/a", "intention",
                 {"status": "open", "closes-when": "x", "parent": "m"})
        code, out = self.check()
        self.assertIn("containment is the path now", out)

    def test_a_reminder_with_no_due_is_an_error(self):
        (self.memory / layout.PROBES).write_text("")
        self.rec(f"{layout.REMINDERS}/r", "reminder", {"status": "pending"})
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("not a reminder", out)


class Wire(unittest.TestCase):
    """`rouse init --wire`: the block, into the file the agent already
    reads.

    This is the step that decides whether anything else in here ever
    runs. A tree nobody told the model about is a tree that stays empty,
    so the flag is worth the same care as the sweep.
    """

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.home = self.dir / "home"
        self.proj = self.dir / "proj"
        self.home.mkdir()
        self.proj.mkdir()
        env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(home.ENV, None)

    def reads(self, name: str, text: str = "# the project\n") -> Path:
        """A file the agent reads at session start, already in the repo."""
        path = self.proj / name
        path.write_text(text)
        return path

    def init(self, *argv) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["init", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_it_appends_to_the_file_the_agent_already_reads(self):
        claude = self.reads("CLAUDE.md")
        code, out, _ = self.init(str(self.proj), "--wire")
        self.assertEqual(code, 0)
        text = claude.read_text()
        self.assertIn(wire.MARKER, text)
        self.assertIn("rouse pack", text)
        self.assertIn(f"{home.LOCAL}/{layout.INSTRUCTIONS}", text)
        self.assertIn("rouse due", text)
        self.assertIn("wired", out)

    def test_what_was_already_in_the_file_stays_in_it(self):
        claude = self.reads("CLAUDE.md", "# rules\n\nnever push to main.\n")
        self.init(str(self.proj), "--wire")
        self.assertIn("never push to main.", claude.read_text())

    def test_both_of_them_when_a_project_has_both(self):
        files_ = [self.reads(name) for name in wire.FILES]
        self.init(str(self.proj), "--wire")
        for path in files_:
            self.assertIn(wire.MARKER, path.read_text(), path.name)

    def test_a_second_wire_does_not_append_twice(self):
        claude = self.reads("CLAUDE.md")
        self.init(str(self.proj), "--wire")
        code, out, _ = self.init(str(self.proj), "--wire")
        # a tree that is already there is news rather than an error when
        # --wire is on: a reinstall has to be able to reach the wiring,
        # and this is the run the marker exists for
        self.assertEqual(code, 0)
        self.assertEqual(claude.read_text().count(wire.MARKER), 1)
        self.assertIn("already wired", out)

    def test_a_tree_somebody_laid_yesterday_can_still_be_wired(self):
        claude = self.reads("CLAUDE.md")
        self.assertEqual(self.init(str(self.proj))[0], 0)
        self.assertNotIn(wire.MARKER, claude.read_text())
        self.assertEqual(self.init(str(self.proj), "--wire")[0], 0)
        self.assertIn(wire.MARKER, claude.read_text())

    def test_without_the_flag_an_existing_tree_is_still_an_error(self):
        self.init(str(self.proj))
        code, _, err = self.init(str(self.proj))
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)

    def test_with_no_agent_file_it_prints_the_block_and_makes_nothing(self):
        code, out, _ = self.init(str(self.proj), "--wire")
        self.assertEqual(code, 0)
        self.assertIn(wire.MARKER, out)
        for name in wire.FILES:
            self.assertFalse((self.proj / name).exists(), name)
            self.assertIn(name, out)

    def test_the_global_tree_has_no_project_to_wire(self):
        code, out, _ = self.init("--global", "--wire")
        self.assertEqual(code, 0)
        self.assertIn(wire.MARKER, out)
        self.assertIn(f"~/.rouse/{layout.INSTRUCTIONS}", out)
        for name in wire.FILES:
            self.assertFalse((self.home / name).exists(), name)

    def test_the_block_names_the_command_that_works_on_this_box(self):
        """It is an instruction a model runs verbatim. Vendored, there is
        no `rouse` on the path and the block has to say so."""
        tree = self.proj / home.LOCAL
        with mock.patch.object(shutil, "which", return_value="/usr/bin/rouse"):
            self.assertIn("`rouse pack`", wire.block(tree, self.proj))
        with mock.patch.object(shutil, "which", return_value=None):
            self.assertIn("`python3 -m rouse pack`", wire.block(tree,
                                                               self.proj))

if __name__ == "__main__":
    unittest.main()
