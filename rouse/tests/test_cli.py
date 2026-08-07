"""What proves the entry point does what it says: the skeleton that
`rouse init` drops in, through the CLI a person actually types.

The examples in it are records like any other, which is exactly why they
have to behave like records.

Run: python3 -m unittest discover -s rouse/tests -t .
"""

import contextlib
import io
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rouse import cli  # noqa: E402
from rouse.addons import scaffold  # noqa: E402
from rouse.core import context, files, layout, levels, pack  # noqa: E402


class Skeleton(unittest.TestCase):
    """What `rouse init` drops in. The examples are records like any
    other, which is exactly why they have to behave like records."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["init", str(self.dir)])
        self.memory = self.dir / "memory"

    def test_it_ships_inside_the_package(self):
        """`pip install` takes the package and nothing beside it. A
        skeleton one directory up is an install that works right up until
        the first `rouse init`, on somebody else's machine."""
        self.assertEqual(scaffold.SKELETON.parent.name, "rouse")
        self.assertTrue((scaffold.SKELETON / "memory"
                         / layout.INSTRUCTIONS).is_file())

    def test_it_draws_both_shapes_on_the_first_run(self):
        out = scaffold.render_tree(self.memory).splitlines()
        self.assertEqual(out[0], "beliefs:")
        self.assertEqual(sorted(out[1:3]),
                         ["  example-plan-before-code",
                          "  example-zero-downtime-deploys"])
        self.assertIn("motivations:", out)
        self.assertIn("  example-two-deploys-broke-prod", out)
        # and the record half nests, which the context half must not
        records = out[out.index("intention example-verify-the-staging-migration"
                                "  [open]"):]
        self.assertEqual(records[1],
                         "  task example-run-it-on-the-branch  [pending]")
        self.assertIn("  reminder example-pay-the-invoice  [pending]", out)
        self.assertIn("  backlog example-pin-the-runner-version  [open]", out)

    def test_nothing_in_it_is_due_the_day_it_lands(self):
        # a skeleton whose first sweep nudges about a fake record teaches
        # the agent that nudges are noise, on day one
        found = levels.due(levels.Records(self.memory), time.time())
        self.assertEqual([item.id for item in found], [])

    def test_every_file_in_it_says_it_is_a_placeholder(self):
        paths = [r.path for r in levels.Records(self.memory).all()]
        paths += [m.path for m in context.layers(self.memory)]
        paths += pack.notes(self.memory)
        self.assertEqual(len(paths), 8)
        for path in paths:
            slug = path.parent.name if path.stem in layout.TYPES else path.stem
            self.assertIn("example-", slug, path)
            self.assertTrue(files.body(path).startswith("Placeholder"), path)

    def test_its_beliefs_are_flat_and_carry_no_clock(self):
        for module in context.layers(self.memory):
            self.assertEqual(module.path.parent.name, f"{module.type}s")
            fields = list(files.head(module.path) or {})
            # every field in here names something that reads it, and a
            # belief is injected whole on every turn, so nothing does
            self.assertEqual(fields, [] if module.type == "belief"
                             else ["keywords"])

    def test_it_survives_its_own_linter(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["check", "--memory", str(self.memory)])
        self.assertEqual(code, 0)
        self.assertNotIn("error:", buf.getvalue())

    def test_it_tells_the_agent_a_note_is_not_where_a_promise_goes(self):
        """The one thing a live session got wrong: it put "not checked
        yet" in a note body, where nothing sweeps it and nothing ever
        comes due. Both halves of the boundary have to be in the file."""
        # the prose is hard-wrapped, so match fragments, not sentences
        text = " ".join((self.memory / layout.INSTRUCTIONS).read_text().split())
        self.assertIn("in the future tense, it is not a note", text)
        self.assertIn("The tell is tense.", text)
        text = (self.memory / layout.INSTRUCTIONS).read_text()
        # and the boundary is stated in the section that wins, which is
        # the one telling it to write notes at the end of every turn
        notes = text.index("## notes")
        self.assertLess(notes, text.index("It is not where an unfinished"))
        self.assertLess(text.index("It is not where an unfinished"),
                        text.index("## probes"))

    def test_it_ships_no_persona_because_it_could_not_be_marked_as_one(self):
        """Every other example carries `example-` in its name and
        `rouse.md` can say never to act on those. The persona is found by
        path, so a placeholder would have to be called `persona.md` — an
        unmarked instruction about how to talk, in a tree ten seconds
        old. So the layer is documented and `init` says it exists."""
        self.assertFalse((self.memory / layout.PERSONA).exists())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["init", str(self.dir / "second")])
        self.assertIn("rouse new persona", buf.getvalue())

if __name__ == "__main__":
    unittest.main()
