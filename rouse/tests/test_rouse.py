"""What proves the reference implementation does what spec/ says.

Run: python3 -m unittest discover -s rouse/tests -t .
"""

import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rouse import (context, files, layout, levels, pack, probes,  # noqa: E402
                   scaffold, sweep)

HOUR = 3600
LADDER = layout.INTENTIONS


def stamp(offset_s: float) -> str:
    return files.stamp(time.time() + offset_s)


class Tree(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.memory = self.dir / "memory"
        for name in (layout.BELIEFS, layout.MOTIVATIONS, layout.INTENTIONS,
                     layout.NOTES, layout.REMINDERS, layout.BACKLOG):
            (self.memory / name).mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.dir)

    def rec(self, where: str, type_: str, header: dict,
            body: str = "the body") -> Path:
        """A record: a directory holding `<type>.md`. `where` is relative
        to the memory root and names the directory, not the file."""
        path = self.memory / where / f"{type_}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        head = "\n".join(f"{k}: {v}" for k, v in header.items())
        path.write_text(f"---\n{head}\n---\n\n{body}\n")
        return path

    def module(self, type_: str, slug: str, body: str = "what is true",
               header: dict | None = None) -> Path:
        """A context module: one flat `<type>-<slug>.md`, no clock."""
        path = self.memory / context.HOMES[type_] / f"{type_}-{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        head = "\n".join(f"{k}: {v}" for k, v in (header or {}).items())
        path.write_text(f"---\n{head}\n---\n\n{body}\n")
        return path

    def note(self, rel: str, header: dict, body: str = "the body") -> Path:
        path = self.memory / layout.NOTES / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        head = "\n".join(f"{k}: {v}" for k, v in header.items())
        path.write_text(f"---\n{head}\n---\n\n{body}\n")
        return path

    def records(self):
        return levels.Records(self.memory)

    def one(self, type_: str) -> levels.Record:
        found = self.records().of(type_)
        self.assertEqual(len(found), 1)
        return found[0]


class Header(Tree):
    def test_reads_fields_and_stops_at_the_fence(self):
        path = self.note("a.md", {"updated": "2026-03-14",
                                  "keywords": "one, two"},
                         "body: not-a-field")
        self.assertEqual(files.head(path),
                         {"updated": "2026-03-14", "keywords": "one, two"})

    def test_no_header_is_none_not_an_exception(self):
        path = self.memory / layout.NOTES / "plain.md"
        path.write_text("just prose\n")
        self.assertIsNone(files.head(path))

    def test_unterminated_header_is_not_a_record(self):
        path = self.memory / layout.NOTES / "bad.md"
        path.write_text("---\nstatus: open\nand then nothing\n")
        self.assertIsNone(files.head(path))

    def test_set_fields_replaces_in_place_and_appends(self):
        path = self.rec(f"{LADDER}/x", "intention",
                        {"status": "open", "nudges": "1"})
        files.set_fields(path, nudges=2, swept="2026-03-14 09:00")
        head = files.head(path)
        self.assertEqual(head["nudges"], "2")
        self.assertEqual(head["swept"], "2026-03-14 09:00")
        self.assertEqual(head["status"], "open")

    def test_set_fields_never_touches_the_body(self):
        path = self.rec(f"{LADDER}/x", "intention", {"status": "open"},
                        "a line\n\n---\n\nand a fence in the body")
        before = files.body(path)
        files.set_fields(path, swept="2026-03-14 09:00")
        self.assertEqual(files.body(path), before)

    def test_intervals_and_stamps(self):
        self.assertEqual(files.parse_interval("30m"), 1800)
        self.assertEqual(files.parse_interval("2h"), 7200)
        self.assertEqual(files.parse_interval("1d"), 86400)
        self.assertIsNone(files.parse_interval("soon"))
        self.assertIsNone(files.parse_stamp("tomorrow"))
        self.assertAlmostEqual(files.parse_stamp("2026-03-14"),
                               files.parse_stamp("2026-03-14 00:00"))


class Walk(Tree):
    """Containment is the filesystem — this is what that buys."""

    def test_the_type_file_names_the_level(self):
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{LADDER}/i/g", "goal", {"status": "open"})
        self.assertEqual(sorted(r.id for r in self.records().all()),
                         ["goal/g", "intention/i"])

    def test_the_parent_is_the_directory_above(self):
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{LADDER}/i/g", "goal", {"status": "open"})
        records = self.records()
        goal = records.of("goal")[0]
        self.assertEqual(records.parent(goal).id, "intention/i")
        self.assertEqual([r.id for r in records.children(
            records.of("intention")[0])], ["goal/g"])

    def test_levels_may_be_skipped(self):
        """An intention holding a task directly: the task's parent is the
        intention, because it is the nearest record above it."""
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{LADDER}/i/t", "task", {"status": "running"})
        records = self.records()
        task = records.of("task")[0]
        self.assertEqual(records.parent(task).id, "intention/i")

    def test_a_top_level_record_has_no_parent(self):
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        records = self.records()
        self.assertIsNone(records.parent(records.of("intention")[0]))

    def test_the_nesting_of_the_level_directories_is_not_lineage(self):
        """An intention sits three directories deep and still has nothing
        above it. `beliefs/motivations/intentions/` is the sentence the
        tree tells; a level directory is not a record, so no path can say
        which motivation an intention answers."""
        self.module("belief", "zero-downtime")
        self.module("motivation", "denis-said-the-deploys-broke-twice")
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        records = self.records()
        self.assertEqual(len(records.all()), 1)
        self.assertIsNone(records.parent(records.of("intention")[0]))

    def test_assets_beside_a_record_are_not_records(self):
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        (self.memory / LADDER / "i" / "verify.sh").write_text("#!/bin/sh\n")
        (self.memory / LADDER / "i" / "output.md").write_text("what it said\n")
        self.assertEqual([r.id for r in self.records().all()], ["intention/i"])

    def test_a_note_called_task_md_is_not_a_task(self):
        self.note("craft/task.md", {"keywords": "k"})
        self.assertEqual(self.records().all(), [])

    def test_two_type_files_in_one_directory_is_a_conflict(self):
        self.rec(f"{LADDER}/x", "intention", {"status": "open"})
        self.rec(f"{LADDER}/x", "goal", {"status": "open"})
        records = self.records()
        records.all()
        self.assertEqual(len(records.conflicts), 1)

    def test_a_record_file_at_the_memory_root_is_ignored(self):
        (self.memory / "intention.md").write_text("---\nstatus: open\n---\n")
        self.assertEqual(self.records().all(), [])

    def test_the_context_layers_are_not_records(self):
        """Nothing in the record walker knows beliefs exist — no status
        to read, no clock to feed, and no way for one to be somebody's
        parent however deep the tree puts it."""
        self.module("belief", "zero-downtime-deploys")
        self.module("motivation", "two-deploys-broke-prod")
        self.assertEqual(self.records().all(), [])


class Context(Tree):
    """The static layers: flat files, injected whole, never swept."""

    def test_a_module_is_named_by_its_file_minus_the_type_prefix(self):
        self.module("belief", "zero-downtime-deploys")
        found = context.read(self.memory, "belief")
        self.assertEqual([m.id for m in found], ["belief/zero-downtime-deploys"])

    def test_both_layers_are_read_in_order(self):
        self.module("motivation", "ship-it")
        self.module("belief", "deploys-are-boring")
        self.assertEqual([m.id for m in context.layers(self.memory)],
                         ["belief/deploys-are-boring", "motivation/ship-it"])

    def test_a_module_with_no_header_at_all_still_reads(self):
        path = self.memory / layout.BELIEFS / "belief-bare.md"
        path.write_text("deploys never take the site down\n")
        found = context.read(self.memory, "belief")
        self.assertEqual(found[0].text(), "deploys never take the site down")

    def test_nothing_in_the_layers_is_ever_due(self):
        self.module("belief", "old", header={"keywords": "k"})
        self.module("motivation", "older", header={"keywords": "k"})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_subdirectory_is_not_a_nested_belief(self):
        """Lineage above an intention is the thing this shape does not
        have. A directory in `beliefs/` is a mistake, not a hierarchy."""
        nested = self.memory / layout.BELIEFS / "deploys" / "belief-x.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("---\n---\n\nnested\n")
        self.assertEqual(context.read(self.memory, "belief"), [])

    def test_the_layers_nest_by_exactly_one_directory_each(self):
        self.assertTrue(layout.MOTIVATIONS.startswith(f"{layout.BELIEFS}/"))
        self.assertTrue(layout.INTENTIONS.startswith(f"{layout.MOTIVATIONS}/"))

    def test_a_motivation_is_not_read_as_a_belief_of_the_layer_above(self):
        """The layers nest, the items in them don't: the reader of
        `beliefs/` stops at the directory instead of descending into the
        signals below it."""
        self.module("belief", "zero-downtime")
        self.module("motivation", "denis-said-the-deploys-broke-twice")
        self.assertEqual([m.id for m in context.read(self.memory, "belief")],
                         ["belief/zero-downtime"])


class Due(Tree):
    def test_an_intention_that_stopped_moving_is_due(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR),
                                              "closes-when": "it's true"})
        found = levels.due(self.records())
        self.assertEqual([i.id for i in found], ["intention/a"])
        self.assertEqual(found[0].reason, "stopped")

    def test_a_fresh_one_is_not(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-10 * 60)})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_closed_one_is_never_due(self):
        for status in ("done", "dropped"):
            self.rec(f"{LADDER}/{status}", "intention",
                     {"status": status, "last-moved": stamp(-100 * HOUR)})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_running_task_underneath_counts_as_movement(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR)})
        self.rec(f"{LADDER}/a/t", "task", {"status": "running"})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_finished_task_stops_counting(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR)})
        self.rec(f"{LADDER}/a/t", "task", {"status": "done"})
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["intention/a"])

    def test_a_task_elsewhere_in_the_tree_is_not_movement(self):
        """The v0 mistake this shape removes: a `intention: a` field on a
        task in another directory used to keep `a` quiet."""
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR)})
        self.rec(f"{LADDER}/b/t", "task", {"status": "running"})
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["intention/a"])

    def test_the_fifteen_minute_floor_holds_over_the_file(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "stale-after": "1m",
                                              "last-moved": stamp(-5 * 60)})
        self.assertEqual(levels.due(self.records()), [])

    def test_swept_delays_the_next_nudge(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-9 * HOUR),
                                              "swept": stamp(-10 * 60),
                                              "nudges": "1"})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_goal_with_an_open_action_is_quiet(self):
        self.rec(f"{LADDER}/i/g", "goal",
                 {"status": "open", "last-moved": stamp(-30 * 24 * HOUR)})
        self.rec(f"{LADDER}/i/g/a", "action",
                 {"status": "open", "last-moved": stamp(-5 * 60)})
        self.assertEqual(levels.due(self.records()), [])

    def test_an_action_with_an_outcome_is_answered(self):
        self.rec(f"{LADDER}/a", "action", {"status": "open",
                                           "last-moved": stamp(-40 * HOUR),
                                           "outcome": "as-expected"})
        self.assertEqual(levels.due(self.records()), [])

    def test_review_fires_even_while_something_moves_underneath(self):
        self.rec(f"{LADDER}/g", "goal", {"status": "open",
                                         "last-moved": stamp(-5 * 60),
                                         "opened": stamp(-30 * 24 * HOUR),
                                         "review-every": "7d"})
        self.rec(f"{LADDER}/g/a", "action", {"status": "open",
                                             "last-moved": stamp(-5 * 60)})
        found = levels.due(self.records())
        self.assertEqual([(i.id, i.reason) for i in found],
                         [("goal/g", "review")])

    def test_a_due_reminder_fires(self):
        self.rec(f"{layout.REMINDERS}/r", "reminder",
                 {"due": stamp(-60), "status": "pending"})
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["reminder/r"])

    def test_a_future_reminder_does_not(self):
        self.rec(f"{layout.REMINDERS}/r", "reminder",
                 {"due": stamp(HOUR), "status": "pending"})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_reminder_nested_under_an_intention_is_movement(self):
        self.rec(f"{LADDER}/a", "intention", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR)})
        self.rec(f"{LADDER}/a/r", "reminder",
                 {"due": stamp(HOUR), "status": "pending"})
        self.assertEqual(levels.due(self.records()), [])


class Sweeping(Tree):
    def sent(self):
        seen = []

        def sink(item, text, now):
            seen.append((item.id, text))
            return True
        return seen, sink

    def test_delivery_stamps_swept_and_counts(self):
        path = self.rec(f"{LADDER}/a", "intention",
                        {"status": "open", "last-moved": stamp(-3 * HOUR)})
        seen, sink = self.sent()
        self.assertEqual(sweep.tick(self.memory, sink), [("intention/a", True)])
        self.assertEqual(files.head(path)["nudges"], "1")
        self.assertTrue(files.head(path)["swept"])
        self.assertIn("the body", seen[0][1])

    def test_the_wake_says_where_the_record_is(self):
        self.rec(f"{LADDER}/m/a", "intention",
                 {"status": "open", "last-moved": stamp(-3 * HOUR)})
        seen, sink = self.sent()
        sweep.tick(self.memory, sink)
        self.assertIn(f"at: {LADDER}/m/a", seen[0][1])

    def test_a_failed_sink_leaves_it_due(self):
        path = self.rec(f"{LADDER}/a", "intention",
                        {"status": "open", "last-moved": stamp(-3 * HOUR)})
        self.assertEqual(sweep.tick(self.memory, lambda *a: False),
                         [("intention/a", False)])
        self.assertIsNone(files.head(path).get("swept"))
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["intention/a"])

    def test_a_one_shot_reminder_closes_as_fired(self):
        path = self.rec(f"{layout.REMINDERS}/r", "reminder",
                        {"due": stamp(-60), "status": "pending"})
        sweep.tick(self.memory, self.sent()[1])
        self.assertEqual(files.head(path)["status"], "fired")

    def test_a_nag_rearms_itself_instead_of_closing(self):
        path = self.rec(f"{layout.REMINDERS}/r", "reminder",
                        {"due": stamp(-60), "status": "pending", "nag": "2h"})
        sweep.tick(self.memory, self.sent()[1])
        head = files.head(path)
        self.assertEqual(head["status"], "pending")
        self.assertEqual(head["fires"], "1")
        self.assertGreater(files.parse_stamp(head["due"]), time.time())

    def test_a_nag_stops_at_max_fires(self):
        path = self.rec(f"{layout.REMINDERS}/r", "reminder",
                        {"due": stamp(-60), "status": "pending", "nag": "2h",
                         "max-fires": "3", "fires": "2"})
        sweep.tick(self.memory, self.sent()[1])
        head = files.head(path)
        self.assertEqual(head["status"], "expired")
        self.assertEqual(head["ended"], "max-fires")

    def test_a_stuck_nag_is_revived(self):
        path = self.rec(f"{layout.REMINDERS}/r", "reminder",
                        {"due": stamp(-5 * HOUR), "status": "fired",
                         "nag": "2h", "fired": stamp(-2 * HOUR)})
        sweep.revive_stuck(self.records(), time.time())
        self.assertEqual(files.head(path)["status"], "pending")

    def test_the_file_sink_leaves_the_wake_on_disk(self):
        self.rec(f"{LADDER}/a", "intention",
                 {"status": "open", "last-moved": stamp(-3 * HOUR)})
        sweep.tick(self.memory, sweep.FileSink(self.memory))
        nudges = list((self.memory / layout.SCRATCH / "nudges").glob("*.md"))
        self.assertEqual(len(nudges), 1)
        self.assertIn("intention/a", nudges[0].read_text())

    def test_the_sweepers_own_scratch_is_not_walked(self):
        self.rec(f"{layout.SCRATCH}/nudges/a", "intention",
                 {"status": "open", "last-moved": stamp(-3 * HOUR)})
        self.assertEqual(self.records().all(), [])


class Probes(Tree):
    def probes_md(self, text):
        path = self.memory / layout.PROBES
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_output_is_the_answer(self):
        self.probes_md("```probe\nname: hi\ntier: pack\ncmd:  echo two words\n```\n")
        self.assertEqual(probes.readings(self.memory), [("hi", "two words")])

    def test_a_failing_probe_is_unknown_and_never_a_fallback(self):
        self.probes_md("```probe\nname: nope\ntier: pack\ncmd:  exit 3\n```\n")
        self.assertEqual(probes.readings(self.memory), [("nope", "<unknown>")])

    def test_prose_outside_a_fence_is_not_parsed(self):
        self.probes_md("name: notaprobe\ntier: pack\n\n"
                       "```probe\nname: real\ntier: pack\ncmd:  echo ok\n```\n")
        self.assertEqual([n for n, _ in probes.readings(self.memory)], ["real"])

    def test_the_tier_shares_one_budget(self):
        self.probes_md("```probe\nname: slow\ntier: pack\ncmd:  sleep 2\n```\n"
                       "```probe\nname: also\ntier: pack\ncmd:  echo ok\n```\n")
        started = time.monotonic()
        got = probes.readings(self.memory, budget_ms=100)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual(got, [("slow", "<unknown>"), ("also", "<unknown>")])

    def test_demand_probes_do_not_run_in_the_pack_tier(self):
        self.probes_md("```probe\nname: far\ntier: demand\ncmd:  echo ok\n```\n")
        self.assertEqual(probes.readings(self.memory, "pack"), [])


class Pack(Tree):
    def test_it_names_what_is_due_and_indexes_the_notes(self):
        self.note("projects/api.md", {"updated": "2026-03-14",
                                      "keywords": "postgres, staging",
                                      "origin": "owner"})
        self.rec(f"{LADDER}/m/a", "intention",
                 {"status": "open", "last-moved": stamp(-3 * HOUR),
                  "closes-when": "the migration ran"})
        (self.memory / layout.PROBES).write_text(
            "```probe\nname: jobs\ntier: pack\ncmd:  echo 0\n```\n")
        out = pack.render(self.memory)
        self.assertIn("jobs: 0", out)
        self.assertIn("intention/a", out)
        self.assertIn(f"at: {LADDER}/m/a", out)
        self.assertIn("closes-when: the migration ran", out)
        self.assertIn("notes/projects/api.md", out)
        self.assertIn("postgres, staging", out)
        self.assertIn("[owner]", out)
        self.assertIn("index, not the memory", out)

    def test_an_unstamped_note_reads_as_unknown_not_as_owner(self):
        self.note("x.md", {"updated": "2026-03-14", "keywords": "k"})
        self.assertIn("[unknown]", pack.render(self.memory))

    def test_no_note_bodies_leak_into_the_pack(self):
        self.note("x.md", {"keywords": "k"}, "SECRET BODY TEXT")
        self.assertNotIn("SECRET BODY TEXT", pack.render(self.memory))

    def test_the_context_layers_go_in_whole(self):
        """The one exception to pointers-not-bodies, and the reason the
        layers exist: this block IS the modular system prompt."""
        self.module("belief", "zero-downtime",
                    body="Deployments always happen with no downtime.")
        self.module("motivation", "keep-it-honest",
                    body="The pipeline should be evidence, not a vibe.")
        out = pack.render(self.memory)
        self.assertIn("Deployments always happen with no downtime.", out)
        self.assertIn("The pipeline should be evidence, not a vibe.", out)
        self.assertIn("[zero-downtime]", out)
        self.assertIn("[keep-it-honest]", out)

    def test_the_layers_are_labelled_as_standing_truth(self):
        """A paragraph at the top of a session reads as something that
        just came in unless the pack says otherwise."""
        self.module("belief", "x")
        self.assertIn("not news", pack.render(self.memory))

    def test_a_motivation_is_labelled_as_a_signal_and_still_not_news(self):
        """It is the one that really did arrive from outside, so it is
        the one most likely to be answered as if it just had."""
        self.module("motivation", "denis-said-so")
        out = pack.render(self.memory)
        self.assertIn("motivations — signals that arrived", out)
        self.assertIn("not news", out)

    def test_the_layers_land_above_the_index_and_below_what_is_due(self):
        self.module("belief", "zero-downtime")
        self.note("x.md", {"keywords": "k"})
        self.rec(f"{LADDER}/a", "intention",
                 {"status": "open", "last-moved": stamp(-3 * HOUR)})
        out = pack.render(self.memory)
        self.assertLess(out.index("intention/a"), out.index("beliefs —"))
        self.assertLess(out.index("beliefs —"), out.index("fresh memory"))

    def test_a_note_with_assets_is_indexed_by_its_directory(self):
        self.note("shipping/note.md", {"keywords": "shipping, ship"})
        (self.memory / layout.NOTES / "shipping" / "shot.png").write_bytes(b"x")
        out = pack.render(self.memory)
        self.assertIn("notes/shipping (", out)
        self.assertNotIn("notes/shipping/note.md", out)


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


class Check(Tree):
    def check(self):
        from rouse import __main__ as cli
        import io
        import contextlib
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


class Skeleton(unittest.TestCase):
    """What `rouse init` drops in. The examples are records like any
    other, which is exactly why they have to behave like records."""

    def setUp(self):
        import contextlib
        import io
        from rouse import __main__ as cli
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["init", str(self.dir)])
        self.memory = self.dir / "memory"

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
            self.assertEqual(list(files.head(module.path) or {}), ["keywords"])

    def test_it_survives_its_own_linter(self):
        import contextlib
        import io
        from rouse import __main__ as cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["check", "--memory", str(self.memory)])
        self.assertEqual(code, 0)
        self.assertNotIn("error:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
