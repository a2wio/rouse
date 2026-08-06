"""The table, and the arithmetic both readers share.

One sweeper, not five (design/clock.md). Every level does the same three
steps — read the header, ask whether it is moving, decide if it is due —
and what differs is a directory, an interval, and an extra clock. That
is a table, and this is the table.

Two callers import this and must never disagree: the sweeper, which
wakes the agent, and the pack, which prints how many things are stale.
"""

import time
from pathlib import Path

from . import files

# Whatever a file asks for, this is the shortest a nudge cycle may be.
# `stale-after: 1m`, by typo or by enthusiasm, would nudge every minute
# until the agent stopped reading nudges — after which the clock cannot
# catch the real ones either.
NUDGE_FLOOR = 15 * 60

# levels of intent. Beliefs are absent on purpose and never join: nothing
# nudges you about a belief.
LEVELS = ("beliefs", "motivations", "intentions", "goals", "actions")

# the things that run. Value = the states that count as still live.
RUNS = {"tasks": ("pending", "running"), "reminders": ("pending",)}

# any of these in `status:` means ended, at every level
CLOSED = frozenset({"done", "dropped", "retired", "abandoned",
                    "expired", "cancelled", "failed", "released"})


def stem(raw: str) -> str:
    """`motivations/keep-it-honest` and `keep-it-honest` are the same id.
    The directory prefix reads better; it never means anything."""
    return (raw or "").strip().strip("/").split("/")[-1].removesuffix(".md")


def closed(level: str, head: dict) -> bool:
    status = (head.get("status") or "").strip().lower()
    if level in RUNS:
        return (status or "pending") not in RUNS[level]
    if status in CLOSED:
        return True
    # an action is answered the moment its outcome is written, whatever
    # its status line says — the outcome IS the judgment that was owed
    return level == "actions" and bool((head.get("outcome") or "").strip())


def moved_at(head: dict, path: Path) -> float:
    """`last-moved` is the agent's to stamp; `opened` and the file's own
    mtime stand in, so a hand-written file missing a field goes stale on
    schedule rather than never."""
    return (files.parse_stamp(head.get("last-moved"))
            or files.parse_stamp(head.get("opened"))
            or path.stat().st_mtime)


class Level:
    def __init__(self, name, *, stale_after, question, clock=None):
        self.name = name
        self.default = stale_after
        self.question = question
        self._clock = clock

    def clock(self, stem_: str, records) -> float:
        return self._clock(stem_, records) if self._clock else 0.0

    def stale_after(self, head: dict) -> float:
        secs = files.parse_interval(head.get("stale-after"))
        return max(float(secs if secs is not None else self.default),
                   NUDGE_FLOOR)

    def due_at(self, head: dict, path: Path, records) -> float:
        """The later of when it last moved, when it was last nudged, and
        its own clock — plus how long it may sit still. Counting the
        nudge is what stops a sweep nobody acted on from repeating every
        tick."""
        last = max(moved_at(head, path),
                   files.parse_stamp(head.get("swept")) or 0.0,
                   self.clock(path.stem, records))
        return last + self.stale_after(head)


SWEPT: tuple[Level, ...] = (
    Level("motivations", stale_after=7 * 86400,
          question="nothing has been open under this for a while — are you "
                   "still acting on it, or is it time to retire it?"),
    Level("intentions", stale_after=2 * 3600,
          question="this has stopped moving. Move it, or drop it out loud."),
    # a goal is stale on a different condition: the last outcome LANDED
    # and no next action was issued, which can happen seconds after
    # something moved. Hence the clock, and an hour rather than two.
    Level("goals", stale_after=3600, clock=lambda s, r: r.last_ending(s),
          question="the last thing under this ended and nothing followed. "
                   "What's the next attempt?"),
    Level("actions", stale_after=86400,
          question="no task under this and no outcome on it. Did you do it, "
                   "and did it do what you meant?"),
)

BY_NAME = {level.name: level for level in SWEPT}


class Records:
    """Every header one sweep needs, read once."""

    def __init__(self, memory: Path):
        self.memory = Path(memory)
        self.broken: list[Path] = []
        self._levels: dict[str, list[tuple[Path, dict]]] = {}
        self._children: dict[str, list[tuple[str, Path, dict]]] | None = None

    def level(self, name: str) -> list[tuple[Path, dict]]:
        if name not in self._levels:
            found = []
            for path in sorted((self.memory / name).glob("*.md")):
                head = files.head(path)
                if head is None:
                    self.broken.append(path)
                else:
                    found.append((path, head))
            self._levels[name] = found
        return self._levels[name]

    def children(self, stem_: str) -> list[tuple[str, Path, dict]]:
        if self._children is None:
            index: dict[str, list] = {}
            for name in (*LEVELS, *RUNS):
                for path, head in self.level(name):
                    if parent := head.get("parent"):
                        index.setdefault(stem(parent), []).append(
                            (name, path, head))
            # a run names what it is a run OF with `intention:` /
            # `action:` rather than `parent:`, and both count as movement
            for name in RUNS:
                for path, head in self.level(name):
                    for field in ("intention", "action", "goal"):
                        if value := head.get(field):
                            index.setdefault(stem(value), []).append(
                                (name, path, head))
            self._children = index
        return self._children.get(stem_, [])

    def moving(self, stem_: str) -> bool:
        """Something is open under it. Nudging about work already in
        flight is the noise that makes nudges stop working."""
        return any(not closed(level, head)
                   for level, _, head in self.children(stem_))

    def last_ending(self, stem_: str) -> float:
        return max((moved_at(head, path)
                    for level, path, head in self.children(stem_)
                    if closed(level, head)), default=0.0)


class Due:
    """A record that has earned a wake."""

    def __init__(self, level: str, path: Path, head: dict, reason: str,
                 question: str, since: float):
        self.level = level
        self.path = path
        self.head = head
        self.reason = reason        # 'stopped' | 'review' | 'due' | 'nag'
        self.question = question
        self.since = since

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def id(self) -> str:
        return f"{self.level}/{self.path.stem}"

    def nudges(self) -> int:
        try:
            return int(self.head.get("nudges") or self.head.get("fires") or 0)
        except ValueError:
            return 0


def _review(head: dict, path: Path) -> tuple[float, float] | None:
    """`review-every:` — the slow "do I still want this", and the one
    clock that fires while something IS moving underneath, because that
    question doesn't depend on whether an action is in flight."""
    every = files.parse_interval(head.get("review-every"))
    if every is None:
        return None
    last = (files.parse_stamp(head.get("reviewed"))
            or files.parse_stamp(head.get("opened"))
            or path.stat().st_mtime)
    return last, last + every


def due(records: Records, now: float | None = None) -> list[Due]:
    """Everything the clock would wake about, in table order, at most one
    wake per record. The rarer question wins when two are due — a review
    that keeps losing to a staleness nudge is a review that never
    happens."""
    now = time.time() if now is None else now
    found: list[Due] = []
    for level in SWEPT:
        for path, head in records.level(level.name):
            if closed(level.name, head):
                continue
            swept = files.parse_stamp(head.get("swept")) or 0.0
            review = _review(head, path)
            if review and review[1] <= now and swept + NUDGE_FLOOR <= now:
                found.append(Due(level.name, path, head, "review",
                                 "do you still want this, and is it still "
                                 "possible?", review[0]))
                continue
            if records.moving(path.stem):
                continue
            if level.due_at(head, path, records) <= now:
                found.append(Due(level.name, path, head, "stopped",
                                 level.question,
                                 max(moved_at(head, path),
                                     level.clock(path.stem, records))))
    found.extend(reminders_due(records, now))
    return found


def reminders_due(records: Records, now: float) -> list[Due]:
    """The simplest clock in the system: a stamp and a body."""
    found = []
    for path, head in records.level("reminders"):
        if closed("reminders", head):
            continue
        when = files.parse_stamp(head.get("due"))
        if when is None or when > now:
            continue
        nagging = bool(files.parse_interval(head.get("nag")))
        found.append(Due("reminders", path, head, "nag" if nagging else "due",
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
