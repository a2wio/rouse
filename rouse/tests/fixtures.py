"""The memory tree every test writes into, and the two shorthands.

It belongs to none of the three files that use it, which is why it is
here rather than in whichever one happened to be written first.
"""

import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rouse.core import context, files, layout, levels  # noqa: E402

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

    def persona(self, body: str = "short answers, no hedging",
                header: dict | None = None) -> Path:
        """The voice: one file at the root, no slug, or none at all."""
        path = self.memory / layout.PERSONA
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
