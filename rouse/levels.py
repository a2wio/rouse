"""The table, and the arithmetic both readers share.

One sweeper, not five (design/clock.md). Every level does the same three
steps — read the header, ask whether it is moving, decide if it is due —
and what differs is a default interval and an extra clock. That is a
table, and this is the table.

The walk is in here too, because containment is the filesystem now
(layout.py): a record's parent is the nearest enclosing record directory,
so the tree is read once and every question below is a lookup.

Two callers import this and must never disagree: the sweeper, which wakes
the agent, and the pack, which prints how many things are stale.
"""

import time
from pathlib import Path

from . import files, layout

# Whatever a file asks for, this is the shortest a nudge cycle may be.
# `stale-after: 1m`, by typo or by enthusiasm, would nudge every minute
# until the agent stopped reading nudges — after which the clock cannot
# catch the real ones either.
NUDGE_FLOOR = 15 * 60

# for the two types that run, the states that count as still live
OPEN_STATES = {"task": ("pending", "running"), "reminder": ("pending",)}

# any of these in `status:` means ended, at every level
CLOSED = frozenset({"done", "dropped", "retired", "abandoned", "expired",
                    "cancelled", "failed", "released", "promoted"})


class Record:
    """One directory, one `<type>.md`, one header."""

    __slots__ = ("type", "dir", "path", "head", "rel")

    def __init__(self, type_: str, dir_: Path, path: Path, head: dict,
                 rel: Path):
        self.type = type_
        self.dir = dir_
        self.path = path
        self.head = head
        self.rel = rel          # the directory, relative to the memory root

    @property
    def slug(self) -> str:
        return self.dir.name

    @property
    def id(self) -> str:
        """`intention/2026-03-14-migration-verified` — what a human says
        out loud. `rel` is the unambiguous one when two branches of the
        tree happen to use the same slug."""
        return f"{self.type}/{self.slug}"

    def __repr__(self) -> str:
        return f"<{self.id}>"


def closed(rec: Record) -> bool:
    status = (rec.head.get("status") or "").strip().lower()
    if rec.type in OPEN_STATES:
        return (status or "pending") not in OPEN_STATES[rec.type]
    if status in CLOSED:
        return True
    # an action is answered the moment its outcome is written, whatever
    # its status line says — the outcome IS the judgment that was owed
    return rec.type == "action" and bool((rec.head.get("outcome") or "").strip())


def moved_at(rec: Record) -> float:
    """`last-moved` is the agent's to stamp; `opened` and the file's own
    mtime stand in, so a hand-written file missing a field goes stale on
    schedule rather than never."""
    return (files.parse_stamp(rec.head.get("last-moved"))
            or files.parse_stamp(rec.head.get("opened"))
            or rec.path.stat().st_mtime)


class Level:
    def __init__(self, name, *, stale_after, question, clock=None):
        self.name = name
        self.default = stale_after
        self.question = question
        self._clock = clock

    def clock(self, rec: Record, records) -> float:
        return self._clock(rec, records) if self._clock else 0.0

    def stale_after(self, head: dict) -> float:
        secs = files.parse_interval(head.get("stale-after"))
        return max(float(secs if secs is not None else self.default),
                   NUDGE_FLOOR)

    def due_at(self, rec: Record, records) -> float:
        """The later of when it last moved, when it was last nudged, and
        its own clock — plus how long it may sit still. Counting the
        nudge is what stops a sweep nobody acted on from repeating every
        tick."""
        last = max(moved_at(rec),
                   files.parse_stamp(rec.head.get("swept")) or 0.0,
                   self.clock(rec, records))
        return last + self.stale_after(rec.head)


SWEPT: tuple[Level, ...] = (
    Level("motivation", stale_after=7 * 86400,
          question="nothing has been open under this for a while — are you "
                   "still acting on it, or is it time to retire it?"),
    Level("intention", stale_after=2 * 3600,
          question="this has stopped moving. Move it, or drop it out loud."),
    # a goal is stale on a different condition: the last outcome LANDED
    # and no next action was issued, which can happen seconds after
    # something moved. Hence the clock, and an hour rather than two.
    Level("goal", stale_after=3600, clock=lambda rec, r: r.last_ending(rec),
          question="the last thing under this ended and nothing followed. "
                   "What's the next attempt?"),
    Level("action", stale_after=86400,
          question="no task under this and no outcome on it. Did you do it, "
                   "and did it do what you meant?"),
)

BY_NAME = {level.name: level for level in SWEPT}


class Records:
    """The whole tree, walked once.

    Header-only reads: a walk over a thousand records stops at each
    closing `---`, because every clock-relevant fact lives in the header.
    """

    def __init__(self, memory: Path):
        self.memory = Path(memory)
        self.broken: list[Path] = []      # `<type>.md` with no header
        self.conflicts: list[Path] = []   # two `<type>.md` in one directory
        self._by_dir: dict[Path, Record] | None = None
        self._children: dict[Path, list[Record]] | None = None

    # -- the walk ---------------------------------------------------

    def _walk(self) -> dict[Path, Record]:
        if self._by_dir is not None:
            return self._by_dir
        found: dict[Path, Record] = {}
        notes = self.memory / layout.NOTES
        for path in sorted(self.memory.rglob("*.md")):
            if path.stem not in layout.TYPES:
                continue
            if layout.SCRATCH in path.parts:
                continue
            # a note may legitimately be called `task.md`; notes are
            # indexed, never swept, so the whole subtree is off limits
            if notes == path.parent or notes in path.parents:
                continue
            directory = path.parent
            if directory == self.memory:
                continue          # a record needs a directory of its own
            head = files.head(path)
            if head is None:
                self.broken.append(path)
                continue
            if directory in found:
                self.conflicts.append(path)
                continue
            found[directory] = Record(path.stem, directory, path, head,
                                      directory.relative_to(self.memory))
        self._by_dir = found
        return found

    def all(self) -> list[Record]:
        return list(self._walk().values())

    def of(self, type_: str) -> list[Record]:
        return [r for r in self._walk().values() if r.type == type_]

    # -- containment, which is now just the path ---------------------

    def parent(self, rec: Record) -> Record | None:
        """The nearest enclosing record directory. Levels may be skipped:
        an intention with no goal under it holds its task directly, and
        the task's parent is the intention."""
        by_dir = self._walk()
        directory = rec.dir.parent
        while True:
            if directory in by_dir:
                return by_dir[directory]
            if directory == self.memory or directory == directory.parent:
                return None
            directory = directory.parent

    def ancestors(self, rec: Record):
        seen = rec
        while (seen := self.parent(seen)) is not None:
            yield seen

    def children(self, rec: Record) -> list[Record]:
        if self._children is None:
            index: dict[Path, list[Record]] = {}
            for child in self._walk().values():
                if (parent := self.parent(child)) is not None:
                    index.setdefault(parent.dir, []).append(child)
            self._children = index
        return self._children.get(rec.dir, [])

    def moving(self, rec: Record) -> bool:
        """Something is open under it. Nudging about work already in
        flight is the noise that makes nudges stop working."""
        return any(not closed(child) for child in self.children(rec))

    def last_ending(self, rec: Record) -> float:
        return max((moved_at(child) for child in self.children(rec)
                    if closed(child)), default=0.0)


class Due:
    """A record that has earned a wake."""

    def __init__(self, rec: Record, reason: str, question: str, since: float):
        self.rec = rec
        self.reason = reason        # 'stopped' | 'review' | 'due' | 'nag'
        self.question = question
        self.since = since

    type = property(lambda self: self.rec.type)
    path = property(lambda self: self.rec.path)
    head = property(lambda self: self.rec.head)
    slug = property(lambda self: self.rec.slug)
    id = property(lambda self: self.rec.id)
    rel = property(lambda self: self.rec.rel)

    def nudges(self) -> int:
        try:
            return int(self.head.get("nudges") or self.head.get("fires") or 0)
        except ValueError:
            return 0


def _review(rec: Record) -> tuple[float, float] | None:
    """`review-every:` — the slow "do I still want this", and the one
    clock that fires while something IS moving underneath, because that
    question doesn't depend on whether an action is in flight."""
    every = files.parse_interval(rec.head.get("review-every"))
    if every is None:
        return None
    last = (files.parse_stamp(rec.head.get("reviewed"))
            or files.parse_stamp(rec.head.get("opened"))
            or rec.path.stat().st_mtime)
    return last, last + every


def due(records: Records, now: float | None = None) -> list[Due]:
    """Everything the clock would wake about, in table order, at most one
    wake per record. The rarer question wins when two are due — a review
    that keeps losing to a staleness nudge is a review that never
    happens."""
    now = time.time() if now is None else now
    found: list[Due] = []
    for level in SWEPT:
        for rec in sorted(records.of(level.name), key=lambda r: r.rel):
            if closed(rec):
                continue
            swept = files.parse_stamp(rec.head.get("swept")) or 0.0
            review = _review(rec)
            if review and review[1] <= now and swept + NUDGE_FLOOR <= now:
                found.append(Due(rec, "review", "do you still want this, and "
                                 "is it still possible?", review[0]))
                continue
            if records.moving(rec):
                continue
            if level.due_at(rec, records) <= now:
                found.append(Due(rec, "stopped", level.question,
                                 max(moved_at(rec), level.clock(rec, records))))
    found.extend(reminders_due(records, now))
    return found


def reminders_due(records: Records, now: float) -> list[Due]:
    """The simplest clock in the system: a stamp and a body."""
    found = []
    for rec in sorted(records.of("reminder"), key=lambda r: r.rel):
        if closed(rec):
            continue
        when = files.parse_stamp(rec.head.get("due"))
        if when is None or when > now:
            continue
        nagging = bool(files.parse_interval(rec.head.get("nag")))
        found.append(Due(rec, "nag" if nagging else "due",
                         "deliver this, as you reaching out — not as a "
                         "system reporting.", when))
    return found


def next_nag(head: dict, now: float) -> tuple[float | None, str] | None:
    """Where a nagging reminder goes after firing: `(next due, "")`, or
    `(None, which ceiling stopped it)`. None means this isn't a nag.

    Firing is not completing. Only the person it is aimed at ends one
    early, and they do it by saying so, not by receiving a nudge."""
    interval = files.parse_interval(head.get("nag"))
    if not interval:
        return None
    fires = int(head.get("fires") or 0) + 1
    try:
        ceiling = int(head.get("max-fires") or 10)
    except ValueError:
        ceiling = 10
    expires = files.parse_stamp(head.get("expires"))
    if fires >= ceiling:
        return None, "max-fires"
    if expires and expires <= now:
        return None, "expires"
    raw = (head.get("backoff") or "2").strip().lower()
    factor = 1.0 if raw == "fixed" else float(raw or 2)
    step = min(interval * (factor ** (fires - 1)), 86400.0)
    return now + max(step, NUDGE_FLOOR), ""
