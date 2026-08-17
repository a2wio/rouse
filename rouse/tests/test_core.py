"""What proves `core/` does what spec/ says — the header, the walk,
the layers, what is due, the sweep, the probes and the pack.

Run: python3 -m unittest discover -s rouse/tests -t .
"""

import ast
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rouse import cli  # noqa: E402
from rouse.core import (context, files, home, layout, levels,  # noqa: E402
                        pack, probes, sweep)
from rouse.tests.fixtures import HOUR, LADDER, Tree, stamp  # noqa: E402


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


class Persona(Tree):
    """The optional layer above the other two: one file, no clock, and a
    tree without it is a tree, not a tree missing something."""

    def test_it_is_one_file_at_the_root(self):
        self.persona()
        module = context.persona(self.memory)
        self.assertEqual(module.path, self.memory / "persona.md")
        self.assertEqual(module.type, "persona")

    def test_no_persona_is_an_answer_and_not_a_problem(self):
        self.assertIsNone(context.persona(self.memory))
        self.assertEqual(context.render(self.memory), [])

    def test_it_leads_the_context_block(self):
        """Not by importance — by reading order: who is talking, what
        they hold true, what reached them."""
        self.persona(body="you are terse")
        self.module("belief", "plan-first", body="plan before code")
        self.module("motivation", "client-waiting", body="they want it friday")
        out = "\n".join(context.render(self.memory))
        self.assertLess(out.index("you are terse"), out.index("plan before"))
        self.assertLess(out.index("plan before"), out.index("they want it"))

    def test_it_counts_as_a_layer_for_whatever_adds_up_the_bill(self):
        self.persona()
        self.module("belief", "x")
        self.assertEqual([m.type for m in context.layers(self.memory)],
                         ["persona", "belief"])

    def test_it_is_not_a_record_however_hard_the_walker_looks(self):
        self.persona(header={"status": "open"})
        self.assertEqual(levels.Records(self.memory).all(), [])
        self.assertEqual(levels.due(self.records()), [])

    def test_it_has_no_slug_to_print_because_there_is_one_of_it(self):
        self.persona(body="you are terse")
        out = "\n".join(context.render(self.memory))
        self.assertIn("persona — how you talk", out)
        self.assertNotIn("[persona]", out)


class Matching(Tree):
    """`pack --query`: which motivations are spent in full.

    The rule is deliberately stupid so that two implementations produce
    the same pack from the same tree (spec/pack.md).
    """

    def motivation(self, slug: str, keywords: str | None = None,
                   body: str = "a signal") -> context.Module:
        header = {"keywords": keywords} if keywords is not None else {}
        path = self.module("motivation", slug, body=body, header=header)
        return context.Module("motivation", path,
                              path.relative_to(self.memory))

    def test_terms_are_lowercased_and_split_on_everything_but_hyphens(self):
        self.assertEqual(context.terms("Deploy the ZERO-downtime thing!"),
                         {"deploy", "the", "zero-downtime", "thing"})

    def test_one_shared_term_is_a_match(self):
        module = self.motivation("broke-prod", "deploy, prod, incident")
        self.assertTrue(module.matches(context.terms("the prod rollout")))

    def test_no_shared_term_is_not(self):
        module = self.motivation("broke-prod", "deploy, prod, incident")
        self.assertFalse(module.matches(context.terms("the invoice is late")))

    def test_nothing_is_stemmed_and_that_is_on_purpose(self):
        """A matcher with opinions is a matcher two implementations
        disagree about. Missing one costs a collapsed line, not the file."""
        module = self.motivation("broke-prod", "deploy")
        self.assertFalse(module.matches(context.terms("two deploys broke it")))

    def test_no_keywords_at_all_is_always_injected(self):
        """An absent field is not a filter — there is nothing to gate on."""
        module = self.motivation("bare")
        self.assertTrue(module.matches(context.terms("anything at all")))

    def test_with_a_query_the_unmatched_collapse_to_one_line(self):
        self.motivation("broke-prod", "deploy, prod",
                        body="Two deploys broke prod this month.")
        self.motivation("invoice-unpaid", "invoice, billing",
                        body="The invoice has been unpaid for six days.")
        out = "\n".join(context.render(self.memory, query="the prod deploy"))
        self.assertIn("Two deploys broke prod this month.", out)
        self.assertNotIn("unpaid for six days", out)
        self.assertIn("[invoice-unpaid] — 0s ago", out)

    def test_nothing_ever_vanishes_from_the_pack_silently(self):
        """A signal that disappeared is one nobody knows to go and read.
        Cheap is the point; invisible is the failure."""
        self.motivation("invoice-unpaid", "invoice", body="pay it")
        out = "\n".join(context.render(self.memory, query="unrelated"))
        self.assertIn("not matched by this turn", out)
        self.assertIn(layout.MOTIVATIONS, out)
        self.assertIn("[invoice-unpaid]", out)

    def test_a_belief_is_never_gated_however_the_query_reads(self):
        """A rule you didn't retrieve still binds. This is the one thing
        in the pack a retrieval instinct gets wrong."""
        self.module("belief", "plan-before-code",
                    body="Writing code starts in plan mode.")
        out = "\n".join(context.render(self.memory, query="the invoice"))
        self.assertIn("Writing code starts in plan mode.", out)
        self.assertNotIn("not matched", out)

    def test_without_a_query_every_motivation_goes_in_whole(self):
        self.motivation("broke-prod", "deploy", body="prod broke twice")
        self.motivation("invoice-unpaid", "invoice", body="pay the invoice")
        out = "\n".join(context.render(self.memory))
        self.assertIn("prod broke twice", out)
        self.assertIn("pay the invoice", out)
        self.assertNotIn("not matched", out)

    def test_the_persona_is_never_gated_either(self):
        """One step past the belief argument: an agent asked about
        invoices is not thereby a different agent."""
        self.persona(body="you are terse and you never hedge")
        out = "\n".join(context.render(self.memory,
                                       query="nothing to do with any of it"))
        self.assertIn("you are terse and you never hedge", out)

    def test_an_empty_query_is_no_query(self):
        self.motivation("invoice-unpaid", "invoice", body="pay the invoice")
        self.assertIn("pay the invoice",
                      "\n".join(context.render(self.memory, query="")))


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

    def test_a_tree_that_lives_at_dot_rouse_is_not_its_own_scratch(self):
        # the scratch directory inside a tree is `.rouse`, and so is the
        # global home. Skipping that name anywhere in the path emptied
        # every ~/.rouse tree at once, which looked like a working
        # install right up until nothing was ever due
        tree = self.dir / layout.SCRATCH
        (tree / LADDER / "verify-it").mkdir(parents=True)
        (tree / LADDER / "verify-it" / "intention.md").write_text(
            "---\nstatus: open\n---\n\nthe body\n")
        self.assertEqual([r.type for r in levels.Records(tree).all()],
                         ["intention"])


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

    def test_a_query_thins_the_signals_and_leaves_the_rules_alone(self):
        self.module("belief", "plan-before-code",
                    body="Writing code starts in plan mode.")
        self.module("motivation", "invoice-unpaid", body="pay the invoice",
                    header={"keywords": "invoice, billing"})
        self.module("motivation", "broke-prod", body="prod broke twice",
                    header={"keywords": "deploy, prod"})
        out = pack.render(self.memory, query="the prod deploy went wrong")
        self.assertIn("Writing code starts in plan mode.", out)
        self.assertIn("prod broke twice", out)
        self.assertNotIn("pay the invoice", out)
        self.assertIn("[invoice-unpaid]", out)

    def test_the_cli_takes_the_query(self):
        self.module("motivation", "invoice-unpaid", body="pay the invoice",
                    header={"keywords": "invoice"})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["pack", "--memory", str(self.memory),
                      "--query", "the deploy"])
        self.assertNotIn("pay the invoice", buf.getvalue())
        self.assertIn("[invoice-unpaid]", buf.getvalue())

    def test_the_ladder_counts_say_where_the_counted_things_are(self):
        """A count with no path reads as a pointer to nothing. Found in a
        live session, which went hunting for a file called `ladder`."""
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{LADDER}/i/t", "task", {"status": "pending"})
        out = pack.render(self.memory)
        self.assertIn("ladder: 1 intention · 1 task", out)
        self.assertIn(f"under {LADDER}/", out)

    def test_a_nested_reminder_is_not_pointed_at_the_inventory(self):
        """The roots come off the records, not off each level's default
        home — a reminder can live inside the thing it belongs to."""
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{LADDER}/i/ping", "reminder",
                 {"status": "pending", "due": stamp(HOUR)})
        out = pack.render(self.memory)
        self.assertIn("1 intention · 1 reminder", out)
        self.assertIn(f"under {LADDER}/", out)
        self.assertNotIn(layout.REMINDERS, out)

    def test_both_roots_are_named_when_records_sit_in_both(self):
        self.rec(f"{LADDER}/i", "intention", {"status": "open"})
        self.rec(f"{layout.REMINDERS}/pay", "reminder",
                 {"status": "pending", "due": stamp(HOUR)})
        out = pack.render(self.memory)
        self.assertIn(f"under {LADDER}/, {layout.REMINDERS}/", out)

    def test_the_persona_goes_in_whole_above_the_beliefs(self):
        self.persona(body="You talk like a front-end dev in a hurry.")
        self.module("belief", "no-framework", body="A static page needs none.")
        out = pack.render(self.memory)
        self.assertIn("You talk like a front-end dev in a hurry.", out)
        self.assertLess(out.index("persona —"), out.index("beliefs —"))

    def test_a_tree_with_no_persona_prints_no_empty_block(self):
        self.module("belief", "x")
        out = pack.render(self.memory)
        self.assertNotIn("persona", out)

    def test_a_note_with_assets_is_indexed_by_its_directory(self):
        self.note("shipping/note.md", {"keywords": "shipping, ship"})
        (self.memory / layout.NOTES / "shipping" / "shot.png").write_bytes(b"x")
        out = pack.render(self.memory)
        self.assertIn("notes/shipping (", out)
        self.assertNotIn("notes/shipping/note.md", out)


class Home(unittest.TestCase):
    """Finding the tree: --memory, then $ROUSE_HOME, then ./memory, then
    ~/.rouse.

    Everything in here overrides `$HOME` and clears `$ROUSE_HOME`. The
    first is so no test can lay a tree in the real home directory; the
    second is because a machine that happens to have one set would
    otherwise answer rung 2 to every question.
    """

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.home = self.dir / "home"
        self.work = self.dir / "work"
        self.home.mkdir()
        self.work.mkdir()
        env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(home.ENV, None)

    def cd(self, path):
        was = os.getcwd()
        os.chdir(path)
        self.addCleanup(os.chdir, was)

    def project(self) -> Path:
        (self.work / home.LOCAL).mkdir()
        return self.work / home.LOCAL

    def run_cli(self, *argv) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    # -- the four rungs ------------------------------------------------

    def test_the_flag_wins_over_everything(self):
        os.environ[home.ENV] = str(self.dir / "named")
        self.project()
        self.assertEqual(home.resolve(self.dir / "said-so", cwd=self.work),
                         self.dir / "said-so")

    def test_the_env_var_beats_a_project_tree(self):
        os.environ[home.ENV] = str(self.dir / "named")
        self.project()
        self.assertEqual(home.resolve(cwd=self.work), self.dir / "named")

    def test_the_env_var_expands_a_tilde(self):
        os.environ[home.ENV] = "~/.rouse-reviewer"
        self.assertEqual(home.resolve(cwd=self.work),
                         self.home / ".rouse-reviewer")

    def test_a_project_tree_beats_the_global_one(self):
        here = self.project()
        self.assertEqual(home.resolve(cwd=self.work), here)

    def test_with_no_project_tree_it_falls_through_to_the_home(self):
        self.assertEqual(home.resolve(cwd=self.work), self.home / ".rouse")

    def test_only_a_real_directory_answers_for_the_project(self):
        (self.work / home.LOCAL).write_text("not a tree")
        self.assertEqual(home.resolve(cwd=self.work), self.home / ".rouse")

    def test_a_tree_from_before_the_rename_is_still_found(self):
        """`./memory` was rung 3 until the tree got its own name. An
        upgrade that stopped finding one would be an agent that had
        forgotten everything, with nothing said about it."""
        was = self.work / home.WAS / layout.INSTRUCTIONS
        was.parent.mkdir(parents=True)
        was.write_text("the instructions")
        self.assertEqual(home.resolve(cwd=self.work), self.work / home.WAS)

    def test_a_project_that_merely_has_a_memory_directory_is_not_one(self):
        """The reason the rung above checks for the instruction file:
        `memory/` is somebody's source directory in plenty of repos, and
        writing an agent's beliefs into one would be worse than not
        finding a tree at all."""
        (self.work / home.WAS / "embeddings").mkdir(parents=True)
        self.assertEqual(home.resolve(cwd=self.work), self.home / ".rouse")

    def test_the_new_name_wins_over_the_old_one(self):
        (self.work / home.WAS / layout.INSTRUCTIONS).parent.mkdir(parents=True)
        (self.work / home.WAS / layout.INSTRUCTIONS).write_text("older")
        here = self.project()
        self.assertEqual(home.resolve(cwd=self.work), here)

    def test_a_named_tree_that_is_not_there_is_still_the_answer(self):
        # rungs 1 and 2 are taken as given. A path somebody typed and got
        # wrong is worth an error; falling quietly through to a different
        # tree is how an agent ends up writing into somebody else's
        os.environ[home.ENV] = str(self.dir / "gone")
        self.assertEqual(home.resolve(cwd=self.work), self.dir / "gone")

    # -- the same order, through the cli -------------------------------

    def test_the_cli_finds_the_global_tree_with_nothing_passed(self):
        self.cd(self.work)
        self.assertEqual(self.run_cli("init", "--global")[0], 0)
        code, out, _ = self.run_cli("tree")
        self.assertEqual(code, 0)
        self.assertIn("example-zero-downtime-deploys", out)

    def test_a_global_tree_shows_its_records_like_any_other(self):
        self.cd(self.work)
        self.run_cli("init", "--global")
        self.assertIn("intention example-verify-the-staging-migration",
                      self.run_cli("tree")[1])

    def test_the_project_tree_is_the_one_written_into(self):
        self.cd(self.work)
        self.run_cli("init", "--global")
        self.run_cli("init")
        self.assertEqual(self.run_cli("new", "belief", "only-here")[0], 0)
        self.assertIn("only-here", self.run_cli("tree")[1])
        self.assertFalse((self.home / ".rouse" / layout.BELIEFS
                          / "belief-only-here.md").exists())

    def test_with_no_tree_anywhere_it_says_where_it_looked(self):
        self.cd(self.work)
        code, _, err = self.run_cli("tree")
        self.assertEqual(code, 2)
        self.assertIn(home.ENV, err)
        self.assertIn("init --global", err)

    # -- laying one down -----------------------------------------------

    def test_init_global_lays_the_skeleton_at_the_home(self):
        self.assertEqual(self.run_cli("init", "--global")[0], 0)
        self.assertTrue((self.home / ".rouse" / layout.INSTRUCTIONS).is_file())

    def test_init_global_does_not_take_a_directory_as_well(self):
        self.assertEqual(self.run_cli("init", "--global", "elsewhere")[0], 2)
        self.assertFalse((self.home / ".rouse").exists())

    def test_init_will_not_lay_a_second_tree_over_the_first(self):
        self.run_cli("init", "--global")
        self.assertEqual(self.run_cli("init", "--global")[0], 2)

    @unittest.skipUnless(shutil.which("git"), "no git on this box")
    def test_a_global_tree_gets_a_history_of_its_own(self):
        self.run_cli("init", "--global")
        self.assertTrue((self.home / ".rouse" / ".git").is_dir())

    @unittest.skipUnless(shutil.which("git"), "no git on this box")
    def test_a_tree_laid_inside_a_checkout_is_left_alone(self):
        subprocess.run(["git", "init", "-q", str(self.work)],
                       capture_output=True, check=True)
        self.cd(self.work)
        self.run_cli("init")
        self.assertFalse((self.work / home.LOCAL / ".git").exists())

class Layering(unittest.TestCase):
    """`core/` is the minimum, and the only thing keeping it the minimum
    is that nothing in it can reach the other two.

    Stated in a docstring it is a convention, and a convention holds
    until the afternoon somebody needs one function from `scaffold`.
    """

    def test_core_imports_nothing_from_addons_cli_or_plugins(self):
        for path in sorted(Path(pack.__file__).parent.glob("*.py")):
            for node in ast.walk(ast.parse(path.read_text())):
                named = []
                if isinstance(node, ast.ImportFrom):
                    named = ["." * node.level + (node.module or "")]
                    # `from .. import addons` names it in the aliases
                    if node.level > 1:
                        named += [a.name for a in node.names]
                elif isinstance(node, ast.Import):
                    named = [a.name for a in node.names]
                for name in named:
                    # `plugins` is in here for the reason the other two
                    # are, and one more: a plugin talks to the network,
                    # and core reaching one would put a database in the
                    # middle of `pack`
                    outward = set(name.split(".")) & {"addons", "cli",
                                                      "plugins"}
                    self.assertFalse(outward, f"{path.name} imports {name}")


if __name__ == "__main__":
    unittest.main()
