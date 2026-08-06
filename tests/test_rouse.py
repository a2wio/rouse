"""What proves the reference implementation does what spec/ says.

Run: python3 -m unittest discover -s tests -t .
"""

import shutil
import tempfile
import time
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rouse import files, levels, pack, probes, sweep  # noqa: E402

HOUR = 3600


def stamp(offset_s: float) -> str:
    return files.stamp(time.time() + offset_s)


class Tree(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.memory = self.dir / "memory"
        for name in ("notes", "intentions", "tasks", "reminders", "backlog",
                     "beliefs", "motivations", "goals", "actions"):
            (self.memory / name).mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, rel: str, header: dict, body: str = "the body") -> Path:
        path = self.memory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        head = "\n".join(f"{k}: {v}" for k, v in header.items())
        path.write_text(f"---\n{head}\n---\n\n{body}\n")
        return path

    def records(self):
        return levels.Records(self.memory)


class Header(Tree):
    def test_reads_fields_and_stops_at_the_fence(self):
        path = self.write("notes/a.md", {"updated": "2026-03-14",
                                         "keywords": "one, two"},
                          "body: not-a-field")
        self.assertEqual(files.head(path),
                         {"updated": "2026-03-14", "keywords": "one, two"})

    def test_no_header_is_none_not_an_exception(self):
        path = self.memory / "notes/plain.md"
        path.write_text("just prose\n")
        self.assertIsNone(files.head(path))

    def test_unterminated_header_is_not_a_record(self):
        path = self.memory / "notes/bad.md"
        path.write_text("---\nstatus: open\nand then nothing\n")
        self.assertIsNone(files.head(path))

    def test_set_fields_replaces_in_place_and_appends(self):
        path = self.write("intentions/x.md", {"status": "open", "nudges": "1"})
        files.set_fields(path, nudges=2, swept="2026-03-14 09:00")
        head = files.head(path)
        self.assertEqual(head["nudges"], "2")
        self.assertEqual(head["swept"], "2026-03-14 09:00")
        self.assertEqual(head["status"], "open")

    def test_set_fields_never_touches_the_body(self):
        path = self.write("intentions/x.md", {"status": "open"},
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


class Due(Tree):
    def test_an_intention_that_stopped_moving_is_due(self):
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-3 * HOUR),
                                       "closes-when": "it's true"})
        found = levels.due(self.records())
        self.assertEqual([i.id for i in found], ["intentions/a"])
        self.assertEqual(found[0].reason, "stopped")

    def test_a_fresh_one_is_not(self):
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-10 * 60)})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_closed_one_is_never_due(self):
        for status in ("done", "dropped"):
            self.write(f"intentions/{status}.md",
                       {"status": status, "last-moved": stamp(-100 * HOUR)})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_running_task_underneath_counts_as_movement(self):
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-3 * HOUR)})
        self.write("tasks/t.md", {"status": "running", "intention": "a"})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_finished_task_stops_counting(self):
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-3 * HOUR)})
        self.write("tasks/t.md", {"status": "done", "intention": "a"})
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["intentions/a"])

    def test_the_fifteen_minute_floor_holds_over_the_file(self):
        self.write("intentions/a.md", {"status": "open", "stale-after": "1m",
                                       "last-moved": stamp(-5 * 60)})
        self.assertEqual(levels.due(self.records()), [])

    def test_swept_delays_the_next_nudge(self):
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-9 * HOUR),
                                       "swept": stamp(-10 * 60), "nudges": "1"})
        self.assertEqual(levels.due(self.records()), [])

    def test_beliefs_are_never_swept(self):
        self.write("beliefs/b.md", {"status": "held",
                                    "opened": stamp(-400 * 24 * HOUR)})
        self.assertEqual(levels.due(self.records()), [])

    def test_a_motivation_with_an_open_child_is_quiet(self):
        self.write("motivations/m.md", {"status": "open",
                                        "last-moved": stamp(-30 * 24 * HOUR)})
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-5 * 60),
                                       "parent": "motivations/m"})
        self.assertEqual(levels.due(self.records()), [])

    def test_an_action_with_an_outcome_is_answered(self):
        self.write("actions/a.md", {"status": "open",
                                    "last-moved": stamp(-40 * HOUR),
                                    "outcome": "as-expected"})
        self.assertEqual(levels.due(self.records()), [])

    def test_review_fires_even_while_something_moves_underneath(self):
        self.write("goals/g.md", {"status": "open",
                                  "last-moved": stamp(-5 * 60),
                                  "opened": stamp(-30 * 24 * HOUR),
                                  "review-every": "7d"})
        self.write("actions/a.md", {"status": "open", "parent": "goals/g",
                                    "last-moved": stamp(-5 * 60)})
        found = levels.due(self.records())
        self.assertEqual([(i.id, i.reason) for i in found],
                         [("goals/g", "review")])

    def test_a_due_reminder_fires(self):
        self.write("reminders/r.md", {"due": stamp(-60), "status": "pending"})
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["reminders/r"])

    def test_a_future_reminder_does_not(self):
        self.write("reminders/r.md", {"due": stamp(HOUR), "status": "pending"})
        self.assertEqual(levels.due(self.records()), [])


class Sweeping(Tree):
    def sent(self):
        seen = []

        def sink(item, text, now):
            seen.append((item.id, text))
            return True
        return seen, sink

    def test_delivery_stamps_swept_and_counts(self):
        path = self.write("intentions/a.md", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR)})
        seen, sink = self.sent()
        self.assertEqual(sweep.tick(self.memory, sink), [("intentions/a", True)])
        self.assertEqual(files.head(path)["nudges"], "1")
        self.assertTrue(files.head(path)["swept"])
        self.assertIn("the body", seen[0][1])

    def test_a_failed_sink_leaves_it_due(self):
        path = self.write("intentions/a.md", {"status": "open",
                                              "last-moved": stamp(-3 * HOUR)})
        self.assertEqual(sweep.tick(self.memory, lambda *a: False),
                         [("intentions/a", False)])
        self.assertIsNone(files.head(path).get("swept"))
        self.assertEqual([i.id for i in levels.due(self.records())],
                         ["intentions/a"])

    def test_a_one_shot_reminder_closes_as_fired(self):
        path = self.write("reminders/r.md", {"due": stamp(-60),
                                             "status": "pending"})
        sweep.tick(self.memory, self.sent()[1])
        self.assertEqual(files.head(path)["status"], "fired")

    def test_a_nag_rearms_itself_instead_of_closing(self):
        path = self.write("reminders/r.md", {"due": stamp(-60),
                                             "status": "pending", "nag": "2h"})
        sweep.tick(self.memory, self.sent()[1])
        head = files.head(path)
        self.assertEqual(head["status"], "pending")
        self.assertEqual(head["fires"], "1")
        self.assertGreater(files.parse_stamp(head["due"]), time.time())

    def test_a_nag_stops_at_max_fires(self):
        path = self.write("reminders/r.md", {"due": stamp(-60),
                                             "status": "pending", "nag": "2h",
                                             "max-fires": "3", "fires": "2"})
        sweep.tick(self.memory, self.sent()[1])
        head = files.head(path)
        self.assertEqual(head["status"], "expired")
        self.assertEqual(head["ended"], "max-fires")

    def test_a_stuck_nag_is_revived(self):
        path = self.write("reminders/r.md", {"due": stamp(-5 * HOUR),
                                             "status": "fired", "nag": "2h",
                                             "fired": stamp(-2 * HOUR)})
        sweep.revive_stuck(self.records(), time.time())
        self.assertEqual(files.head(path)["status"], "pending")

    def test_the_file_sink_leaves_the_wake_on_disk(self):
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-3 * HOUR)})
        sweep.tick(self.memory, sweep.FileSink(self.memory))
        nudges = list((self.memory / ".rouse" / "nudges").glob("*.md"))
        self.assertEqual(len(nudges), 1)
        self.assertIn("intentions/a", nudges[0].read_text())


class Probes(Tree):
    def probes_md(self, text):
        (self.memory / "probes.md").write_text(text)

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
        self.write("notes/projects/api.md", {"updated": "2026-03-14",
                                             "keywords": "postgres, staging",
                                             "origin": "owner"})
        self.write("intentions/a.md", {"status": "open",
                                       "last-moved": stamp(-3 * HOUR),
                                       "closes-when": "the migration ran"})
        (self.memory / "probes.md").write_text(
            "```probe\nname: jobs\ntier: pack\ncmd:  echo 0\n```\n")
        out = pack.render(self.memory)
        self.assertIn("jobs: 0", out)
        self.assertIn("intentions/a", out)
        self.assertIn("closes-when: the migration ran", out)
        self.assertIn("notes/projects/api.md", out)
        self.assertIn("postgres, staging", out)
        self.assertIn("[owner]", out)
        self.assertIn("index, not the memory", out)

    def test_an_unstamped_note_reads_as_unknown_not_as_owner(self):
        self.write("notes/x.md", {"updated": "2026-03-14", "keywords": "k"})
        self.assertIn("[unknown]", pack.render(self.memory))

    def test_no_bodies_leak_into_the_pack(self):
        self.write("notes/x.md", {"keywords": "k"}, "SECRET BODY TEXT")
        self.assertNotIn("SECRET BODY TEXT", pack.render(self.memory))


if __name__ == "__main__":
    unittest.main()
