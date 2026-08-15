"""What proves the plugin layer is as small as it claims: a skill where
the agent already looks, a tool it names, one file in the tree saying it
is on — and a tree that works with nothing turned on.

Nothing in here talks to a database. The neon plugin's network half is
three subprocess calls; what is worth testing is the half that turns a
memory tree into rows, and that is pure.

Every test that touches an agent directory patches `Path.home` first.
A test suite that installs a skill into whoever ran it is a test suite
that edits the machine.

Run: python3 -m unittest discover -s rouse/tests -t .
"""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rouse import cli, plugins  # noqa: E402
from rouse.addons import check  # noqa: E402
from rouse.core import files, layout, pack  # noqa: E402
from rouse.plugins.neon import tool as neon  # noqa: E402
from rouse.tests.fixtures import LADDER, Tree  # noqa: E402


class Plugged(Tree):
    """A tree with a home directory of its own, so nothing here can
    reach the machine that is running the tests."""

    def setUp(self):
        super().setUp()
        self.home = self.dir / "home"
        self.home.mkdir()
        patch = mock.patch.object(Path, "home", staticmethod(lambda: self.home))
        patch.start()
        self.addCleanup(patch.stop)

    def agent(self, name: str, *, at_home: bool = False) -> Path:
        """An agent cli that has run here before — which is the only
        thing that makes it a place to put a skill."""
        base = self.home if at_home else self.dir
        (base / plugins.AGENTS[name]).mkdir(parents=True, exist_ok=True)
        return base / plugins.AGENTS[name] / plugins.SKILLS


class Discovery(Plugged):
    def test_a_plugin_is_a_directory_with_a_manifest(self):
        self.assertIn("neon", plugins.available())
        for name in plugins.available():
            self.assertTrue(plugins.manifest(name).is_file())
            self.assertTrue(plugins.described(name))

    def test_every_shipped_skill_is_a_skill_the_agent_would_read(self):
        """A SKILL.md with no name and no description is a file the CLI
        lists as nothing and never loads."""
        for name in plugins.available():
            self.assertTrue(plugins.shipped(name), name)
            for agent, at in plugins.shipped(name).items():
                head = files.head(at / "SKILL.md")
                self.assertEqual(head["name"], f"{plugins.PREFIX}{name}")
                self.assertTrue(head["description"], (name, agent))

    def test_a_tree_starts_with_none_on(self):
        self.assertEqual(plugins.enabled(self.memory), [])


class Adding(Plugged):
    def test_the_skill_lands_where_that_agent_looks(self):
        self.agent("claude-code")
        path, wrote = plugins.add(self.memory, "neon", {"project": "quiet-sky"})
        self.assertEqual(list(wrote), ["claude-code"])
        self.assertTrue((wrote["claude-code"] / "SKILL.md").is_file())
        self.assertEqual(wrote["claude-code"].name, "rouse-neon")
        self.assertEqual(path, self.memory / layout.PLUGINS / "neon.md")

    def test_every_agent_that_is_here_gets_one(self):
        self.agent("claude-code")
        self.agent("codex")
        _, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        self.assertEqual(sorted(wrote), ["claude-code", "codex"])

    def test_the_project_beats_the_home_directory(self):
        here = self.agent("claude-code")
        self.agent("claude-code", at_home=True)
        _, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        self.assertEqual(wrote["claude-code"].parent, here)

    def test_an_agent_that_only_lives_in_the_home_directory(self):
        mine = self.agent("codex", at_home=True)
        _, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        self.assertEqual(wrote["codex"].parent, mine)

    def test_nothing_is_installed_for_an_agent_that_isnt_here(self):
        """The rule `--wire` follows about CLAUDE.md: rouse doesn't make
        a directory your agent hasn't got. The plugin still goes on —
        the tool works, and what is missing is the telling."""
        _, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        self.assertEqual(wrote, {})
        self.assertEqual(plugins.enabled(self.memory), ["neon"])
        self.assertFalse((self.dir / ".claude").exists())
        self.assertFalse((self.home / ".claude").exists())

    def test_naming_one_makes_the_directory(self):
        """Explicit always wins, the same as `--memory`: somebody who
        types the agent's name has said where they want it."""
        _, wrote = plugins.add(self.memory, "neon", {"project": "x"},
                               ["claude-code"])
        self.assertTrue((wrote["claude-code"] / "SKILL.md").is_file())
        self.assertEqual(wrote["claude-code"].parent,
                         self.dir / ".claude" / "skills")

    def test_the_answers_go_into_the_header_of_the_copy(self):
        self.agent("claude-code")
        path, _ = plugins.add(self.memory, "neon", {"project": "quiet-sky-42"})
        self.assertEqual(files.head(path)["project"], "quiet-sky-42")
        self.assertEqual(plugins.settings(self.memory, "neon")["database"],
                         "neondb")

    def test_what_it_wrote_is_recorded_relative_to_the_tree(self):
        """A memory tree is a repository that travels. An absolute path
        in a header is a path that is wrong on the second machine."""
        self.agent("claude-code")
        path, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        self.assertEqual(files.head(path)["skills"],
                         ".claude/skills/rouse-neon")
        self.assertEqual(plugins.recorded(self.memory, "neon"),
                         [wrote["claude-code"]])

    def test_add_never_overwrites(self):
        plugins.add(self.memory, "neon", {"project": "mine"})
        with self.assertRaises(ValueError):
            plugins.add(self.memory, "neon", {"project": "theirs"})
        self.assertEqual(plugins.settings(self.memory, "neon")["project"],
                         "mine")

    def test_an_unknown_plugin_is_a_value_error(self):
        with self.assertRaises(ValueError):
            plugins.add(self.memory, "bigtable", {})

    def test_an_unknown_agent_is_a_value_error_before_anything_is_written(self):
        with self.assertRaises(ValueError):
            plugins.add(self.memory, "neon", {}, ["emacs"])
        self.assertEqual(plugins.enabled(self.memory), [])

    def test_blanks_are_the_fields_nobody_filled_in(self):
        plugins.add(self.memory, "neon", {})
        self.assertEqual(plugins.blanks(self.memory, "neon"), ["project"])
        files.set_fields(plugins.installed(self.memory, "neon"),
                         project="quiet-sky-42")
        self.assertEqual(plugins.blanks(self.memory, "neon"), [])


class Removing(Plugged):
    def test_it_takes_back_the_skill_and_the_switch(self):
        self.agent("claude-code")
        path, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        _, gone = plugins.remove(self.memory, "neon")
        self.assertEqual(gone, [wrote["claude-code"]])
        self.assertFalse(wrote["claude-code"].exists())
        self.assertFalse(path.exists())
        self.assertEqual(plugins.enabled(self.memory), [])

    def test_it_leaves_the_other_skills_in_the_directory_alone(self):
        at = self.agent("claude-code")
        mine = at / "my-own-skill"
        mine.mkdir(parents=True)
        (mine / "SKILL.md").write_text("---\nname: my-own-skill\n---\n")
        plugins.add(self.memory, "neon", {"project": "x"})
        plugins.remove(self.memory, "neon")
        self.assertTrue((mine / "SKILL.md").is_file())

    def test_it_will_not_delete_something_that_is_not_a_skill(self):
        """The header is a file somebody can edit, and skills live in a
        directory full of other people's. A recorded path that no longer
        holds a SKILL.md is left where it is."""
        at = self.agent("claude-code")
        plugins.add(self.memory, "neon", {"project": "x"})
        (at / "rouse-neon" / "SKILL.md").unlink()
        (at / "rouse-neon" / "notes.txt").write_text("somebody's work")
        _, gone = plugins.remove(self.memory, "neon")
        self.assertEqual(gone, [])
        self.assertTrue((at / "rouse-neon" / "notes.txt").is_file())

    def test_removing_one_that_is_not_on(self):
        with self.assertRaises(ValueError):
            plugins.remove(self.memory, "neon")

    def test_adding_it_again_afterwards_works(self):
        self.agent("claude-code")
        plugins.add(self.memory, "neon", {"project": "x"})
        plugins.remove(self.memory, "neon")
        _, wrote = plugins.add(self.memory, "neon", {"project": "y"})
        self.assertTrue((wrote["claude-code"] / "SKILL.md").is_file())


class Pack(Plugged):
    def test_the_pack_says_nothing_when_nothing_is_on(self):
        self.assertNotIn("plugins:", pack.render(self.memory))

    def test_an_enabled_plugin_is_a_pointer_not_a_body(self):
        plugins.add(self.memory, "neon", {"project": "quiet-sky-42"})
        out = pack.render(self.memory)
        self.assertIn("plugins: neon", out)
        self.assertIn(f"{layout.PLUGINS}/neon.md", out)
        # the instructions themselves are the agent's skill: the pack
        # prints bodies for the context layers and nothing else
        self.assertNotIn("rouse neon recall", out)


class Lint(Plugged):
    def test_an_unfilled_setting_is_a_warning(self):
        plugins.add(self.memory, "neon", {})
        errors, warnings = check.lint(self.memory)
        self.assertEqual(errors, [])
        self.assertTrue(any("cannot connect" in w for w in warnings), warnings)

    def test_a_filled_one_is_silent(self):
        self.agent("claude-code")
        plugins.add(self.memory, "neon", {"project": "quiet-sky-42"})
        _, warnings = check.lint(self.memory)
        self.assertFalse([w for w in warnings if "neon" in w], warnings)

    def test_a_skill_that_has_gone_missing_since(self):
        """The failure nothing else catches: the tool still runs and the
        model is never told it can."""
        self.agent("claude-code")
        _, wrote = plugins.add(self.memory, "neon", {"project": "x"})
        (wrote["claude-code"] / "SKILL.md").unlink()
        _, warnings = check.lint(self.memory)
        self.assertTrue(any("the skill is gone" in w for w in warnings),
                        warnings)

    def test_a_plugin_this_install_does_not_ship(self):
        (self.memory / layout.PLUGINS).mkdir(parents=True)
        (self.memory / layout.PLUGINS / "bigtable.md").write_text(
            "---\n---\n\nsomebody else's plugin\n")
        _, warnings = check.lint(self.memory)
        self.assertTrue(any("doesn't ship it" in w for w in warnings),
                        warnings)

    def test_the_switch_is_not_mistaken_for_a_record(self):
        """`entrypoint/` is the record half of the tree, and the linter
        shouts about loose .md files in it. A plugin's file is the third
        thing that is legitimately flat."""
        plugins.add(self.memory, "neon", {"project": "x"})
        _, warnings = check.lint(self.memory)
        self.assertFalse([w for w in warnings if "not a record" in w],
                         warnings)


class Dispatch(Plugged):
    def run_cli(self, argv) -> int:
        """The exit code, with the usage text kept out of the test run."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as caught:
                cli.main(argv)
        return caught.exception.code

    def test_a_plugin_name_is_a_verb(self):
        """`rouse neon …` never reaches the main parser — which is what
        lets a plugin have flags of its own."""
        self.assertEqual(self.run_cli(["neon", "--help"]), 0)

    def test_an_unknown_first_word_is_still_a_parser_error(self):
        self.assertEqual(self.run_cli(["bigtable", "sync"]), 2)


class Rows(Plugged):
    """The tree, as the index sees it."""

    def setUp(self):
        super().setUp()
        self.persona(body="short answers")
        self.module("belief", "zero-downtime", body="deploys never wait")
        self.note("craft/migrations.md",
                  {"updated": "2026-03-14", "keywords": "postgres, staging"},
                  body="staging runs migrations on deploy")
        self.rec(f"{LADDER}/verify-it", "intention",
                 {"status": "open", "closes-when": "it ran once"})
        self.rec(f"{LADDER}/verify-it/run-it", "task",
                 {"status": "pending", "category": "engineering"})

    def by_kind(self):
        return {row["kind"]: row for row in neon.rows(self.memory)}

    def test_every_layer_and_every_record_becomes_a_row(self):
        self.assertEqual(set(self.by_kind()),
                         {"persona", "belief", "note", "intention", "task"})

    def test_containment_is_carried_as_the_parent_path(self):
        rows = self.by_kind()
        self.assertEqual(rows["task"]["parent"], f"{LADDER}/verify-it")
        self.assertIsNone(rows["intention"]["parent"])

    def test_keywords_are_split_and_the_header_is_kept_whole(self):
        note = self.by_kind()["note"]
        self.assertEqual(note["keywords"], ["postgres", "staging"])
        self.assertEqual(note["head"]["updated"], "2026-03-14")
        self.assertIn("migrations on deploy", note["body"])

    def test_the_sha_is_the_file_and_changes_with_it(self):
        before = self.by_kind()["note"]["sha"]
        self.note("craft/migrations.md",
                  {"updated": "2026-03-15", "keywords": "postgres, staging"},
                  body="staging runs migrations on deploy, production does not")
        self.assertNotEqual(before, self.by_kind()["note"]["sha"])

    def test_copy_lines_are_one_json_document_each(self):
        self.note("craft/awkward.md", {"keywords": "escaping"},
                  body="a tab\there, a backslash \\ and\na newline")
        lines = neon.copy_lines(neon.rows(self.memory)).splitlines()
        self.assertEqual(len(lines), len(neon.rows(self.memory)))
        # what COPY does on the way in: `\\` back to `\`
        bodies = [json.loads(line.replace("\\\\", "\\"))["body"]
                  for line in lines]
        self.assertTrue(any("a tab\there" in body for body in bodies), bodies)


class Connection(unittest.TestCase):
    def test_a_uri_becomes_environment_and_never_an_argument(self):
        env = neon.pgenv("postgresql://me:s3cret@ep-cool-1.eu-central-1.aws."
                         "neon.tech/neondb?sslmode=require&"
                         "channel_binding=require")
        self.assertEqual(env["PGUSER"], "me")
        self.assertEqual(env["PGPASSWORD"], "s3cret")
        self.assertEqual(env["PGDATABASE"], "neondb")
        self.assertEqual(env["PGSSLMODE"], "require")
        self.assertEqual(env["PGCHANNELBINDING"], "require")

    def test_a_password_with_url_escapes_survives(self):
        env = neon.pgenv("postgresql://me:p%40ss%2Fword@host/db")
        self.assertEqual(env["PGPASSWORD"], "p@ss/word")


if __name__ == "__main__":
    unittest.main()
