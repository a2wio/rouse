"""The linter: what makes a record untrackable, and what makes it useless.

Errors are the first kind — a file with no header, a reminder with no
due, a stale-after nothing can parse. Something in the tree is a
commitment nobody is tracking, and the exit code says so.

Warnings are the second — a belief carrying a clock, a note with no
keywords, a context block that has quietly grown to cost real money
every session. Nothing is broken; the tree is just doing less than it
looks like it is doing.

It returns the two lists rather than printing them, because the exit
code is the caller's business and this is also the thing a CI step or an
editor wants to call.
"""

import time
from pathlib import Path

from ..core import context, files, layout, levels, pack, probes

# everything a record header carries and a context module has no use
# for. One of these on a belief means somebody expected it to be swept.
CLOCK_FIELDS = ("status", "opened", "last-moved", "stale-after",
                "closes-when", "success-when", "due", "swept", "nudges")

# the context layers are injected whole, every session, forever. This is
# roughly two thousand tokens of them — past it, "keep them few" has
# stopped being true and the pack has started costing real money.
#
# ONE number for all three layers, including the persona. A second budget
# would be a second thing to tune, and what is actually being defended
# here is the per-turn cost, which does not care which file it came from:
# a lavish persona and a wall of beliefs are the same bill.
CONTEXT_BUDGET = 8000


def lint(memory: Path) -> tuple[list[str], list[str]]:
    """Every finding in the tree, as `(errors, warnings)`."""
    memory = Path(memory)
    records = levels.Records(memory)
    errors, warnings = [], []

    def rel(path):
        return path.relative_to(memory) if memory in path.parents else path

    all_records = records.all()
    for path in records.broken:
        errors.append(f"{rel(path)}: no header — nothing can track this")
    for path in records.conflicts:
        errors.append(f"{rel(path)}: a second record file in the same "
                      "directory — one record, one directory")

    warnings += _context(memory)

    # the flat-layout mistake: a record written as `<slug>.md` instead of
    # `<slug>/<type>.md`. An .md beside a record file is an asset and
    # fine; an .md in a directory that is nobody's record is a lost file.
    homes = {r.dir for r in all_records}
    # flat by design, and not this rule's business: the two context
    # layers (`_context` above has already had its say) and the
    # instruction file
    flat = {memory / layout.BELIEFS, memory / layout.MOTIVATIONS}
    for root in (layout.ENTRYPOINT, layout.REMINDERS, layout.BACKLOG):
        for path in sorted((memory / root).rglob("*.md")):
            if path.stem in layout.TYPES or path.parent in homes:
                continue
            if path.parent in flat or path == memory / layout.INSTRUCTIONS:
                continue
            warnings.append(f"{rel(path)}: not a record and not beside one — "
                            "a record is a directory holding <type>.md")

    seen: dict[tuple[str, str], Path] = {}
    for rec in all_records:
        where = rec.rel
        for field, parse in (("stale-after", files.parse_interval),
                             ("nag", files.parse_interval),
                             ("review-every", files.parse_interval),
                             ("last-moved", files.parse_stamp),
                             ("due", files.parse_stamp),
                             ("opened", files.parse_stamp)):
            if rec.head.get(field) and parse(rec.head[field]) is None:
                errors.append(f"{where}: unparseable {field}: "
                              f"{rec.head[field]!r}")
        if rec.head.get("parent"):
            warnings.append(f"{where}: a `parent:` field — containment is "
                            "the path now, and two answers is one too many")
        if (key := (rec.type, rec.slug)) in seen:
            warnings.append(f"{where}: same name as {seen[key]} — the slug is "
                            "how you'll say it out loud, so make it unique")
        else:
            seen[key] = where

        if rec.type == "intention" and not rec.head.get("closes-when"):
            warnings.append(f"{where}: no closes-when — you can't tell "
                            "when this is finished")
        if rec.type == "backlog":
            for field in ("stale-after", "last-moved"):
                if rec.head.get(field):
                    warnings.append(f"{where}: backlog items have no clock — "
                                    f"drop {field}, or promote this")
            if records.children(rec):
                warnings.append(f"{where}: something is nested under a "
                                "backlog item, and nothing will ever sweep it")
        if rec.type == "reminder" and not rec.head.get("due"):
            errors.append(f"{where}: a reminder with no due is not a reminder")

    for path in pack.notes(memory):
        head = files.head(path)
        if head is None:
            warnings.append(f"{rel(path)}: no header — it won't be indexed")
        elif not head.get("keywords"):
            warnings.append(f"{rel(path)}: no keywords — nothing will find it")

    warnings += _probes(memory)
    return errors, warnings


def _persona(memory: Path) -> list[str]:
    """Lint the voice. Three things can be wrong with it and its absence
    is not one of them — `spec/persona.md`, and the reason `check` on a
    fresh skeleton is silent about a file the skeleton doesn't ship.

    A `persona.md` somewhere other than the root is the one worth
    catching. It parses, it reads like the real thing, and nothing
    injects it: the layer is a fixed path, so a file in the wrong place
    is not a misconfigured persona, it is a file nobody will ever see.
    """
    warnings = []
    for path in sorted(memory.rglob(layout.PERSONA)):
        if path != memory / layout.PERSONA:
            warnings.append(
                f"{path.relative_to(memory)}: the persona is one file at the "
                f"tree root, and nothing reads one anywhere else. Move it to "
                f"{layout.PERSONA} or give it a name that says what it is")
    module = context.persona(memory)
    if module is None:
        return warnings
    head = files.head(module.path) or {}
    if late := [f for f in CLOCK_FIELDS if head.get(f)]:
        warnings.append(f"{layout.PERSONA}: {', '.join(late)} in a persona — "
                        "context has no clock and no lifecycle. A voice that "
                        "is finished on Tuesday was an intention")
    if head.get("keywords"):
        warnings.append(f"{layout.PERSONA}: keywords on a persona — nothing "
                        "reads them. It goes into the pack whole on every "
                        "turn and is never gated by a query, so there is "
                        "nothing to match against")
    return warnings


def _context(memory: Path) -> list[str]:
    """Lint the static layers. They have no clock, so almost nothing can
    be wrong with one — which leaves exactly three things that can.

    The layers nest by one directory each — `motivations/` inside
    `beliefs/`, `intentions/` inside `motivations/` — and that one is
    legal. Any other directory in there is somebody putting a ground
    truth inside a ground truth.
    """
    warnings = _persona(memory)
    for type_ in layout.CONTEXT:
        root = memory / context.HOMES[type_]
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            where = path.relative_to(memory)
            if path.is_dir():
                if path.name != layout.NESTS[type_]:
                    warnings.append(
                        f"{where}: a directory inside {type_}s/ — the only "
                        f"one that belongs here is {layout.NESTS[type_]}/, "
                        "the layer below. Nothing sits under a ground truth")
                continue
            if path.suffix != ".md":
                continue
            if not path.stem.startswith(f"{type_}-"):
                warnings.append(f"{where}: name it {type_}-{path.stem}.md, so "
                                "it still says what it is once it has been "
                                "copied somewhere else")
            head = files.head(path) or {}
            if late := [f for f in CLOCK_FIELDS if head.get(f)]:
                warnings.append(f"{where}: {', '.join(late)} in a {type_} — "
                                "context has no clock and no lifecycle. If "
                                "this one does, it wanted to be an intention")
            if type_ not in context.GATED and head.get("keywords"):
                warnings.append(
                    f"{where}: keywords on a {type_} — nothing reads them. "
                    "It goes into the pack whole on every turn, so it is "
                    "never looked up; keywords are for what gets retrieved, "
                    "which is notes and motivations under `pack --query`")
    modules = context.layers(memory)
    size = sum(len(m.text()) for m in modules)
    if size > CONTEXT_BUDGET:
        # name the split, because "trim your context" without a
        # breakdown gets the wrong layer trimmed
        by_type = ", ".join(
            f"{sum(len(m.text()) for m in modules if m.type == type_)} "
            f"{type_}" for type_ in (context.PERSONA, *layout.CONTEXT)
            if any(m.type == type_ for m in modules))
        warnings.append(f"context: {size} characters over {CONTEXT_BUDGET} "
                        f"({by_type}) — every session pays for all of it. If "
                        "everything is a belief, nothing is")
    return warnings


def _probes(memory: Path) -> list[str]:
    """Lint the readings, by taking them. The only check here that costs
    what the thing it is checking costs, which is the point: what it is
    really measuring is whether session start can afford them."""
    warnings = []
    started = time.monotonic()
    readings = probes.readings(memory, "pack")
    spent = int((time.monotonic() - started) * 1000)
    # a probe marked unknown-ok is *designed* to go quiet — it reads a
    # file some daemon writes, so silence is the reading (spec/probes.md)
    quiet_ok = {p.name for p in probes.read(probes.path_of(memory))
                if p.unknown_ok}
    for name, value in readings:
        if value == probes.UNKNOWN and name not in quiet_ok:
            warnings.append(f"{layout.PROBES}: {name} answered <unknown>")
    if spent > probes.BUDGET_MS:
        warnings.append(f"{layout.PROBES}: the pack tier took {spent}ms of "
                        f"its {probes.BUDGET_MS}ms — move something to demand")
    return warnings
