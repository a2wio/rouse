"""rouse — memory with a clock.

    rouse init [dir]      drop the skeleton in — --global lays it at ~/.rouse
    rouse pack            the context block, for session start
    rouse due             what the clock would wake about, one line each
    rouse sweep           the tick loop, with a wake sink
    rouse new             a record, or a belief/motivation
    rouse promote         a backlog item becomes an intention
    rouse tree            the context layers and the records, as they sit
    rouse check           lint the memory tree
    rouse stamp           write provenance — for a wrapper, not the model

Every verb but `init` and `stamp` finds the tree the same way: --memory,
then $ROUSE_HOME, then ./memory, then ~/.rouse. See rouse/home.py.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

from . import (context, files, home, layout, levels, pack, probes, scaffold,
               sweep)

SKELETON = Path(__file__).resolve().parents[1] / "skeleton"
ORIGINS = ("owner", "agent", "system", "untrusted", "unknown")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rouse", description=__doc__.strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    where = (f"the memory tree (default: ${home.ENV}, else ./{home.LOCAL}, "
             f"else {home.GLOBAL})")
    ap.add_argument("--memory", default=None, type=Path, help=where)

    # the same flag on both sides, so `rouse --memory X pack` and
    # `rouse pack --memory X` both work. SUPPRESS is what stops the
    # subparser's default from clobbering a value given before the verb.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--memory", type=Path, default=argparse.SUPPRESS,
                        help=where)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="drop the skeleton in")
    p.add_argument("target", nargs="?", type=Path)
    p.add_argument("--global", dest="globally", action="store_true",
                   help=f"lay it at {home.GLOBAL} — the tree an agent with "
                        "no project to stand in still has")

    p = sub.add_parser("pack", help="the context block for session start",
                       parents=[common])
    p.add_argument("--budget-ms", type=int, default=probes.BUDGET_MS)
    p.add_argument("--query", help="what this turn is about, if you know — "
                                   "motivations it doesn't touch collapse to "
                                   "one line each. Beliefs always go in whole")

    sub.add_parser("due", help="what the clock would wake about",
                   parents=[common])
    sub.add_parser("check", help="lint the memory tree", parents=[common])
    sub.add_parser("tree", help="the layers and the records as they sit",
                   parents=[common])

    p = sub.add_parser("new", help="make a record, or a context module",
                       parents=[common])
    p.add_argument("type", choices=layout.WRITABLE)
    p.add_argument("slug")
    p.add_argument("--under", help="the slug of the record it sits under, "
                                   "or a path inside the memory directory. "
                                   "Not for a belief or a motivation — "
                                   "those sit under nothing")

    p = sub.add_parser("promote", help="a backlog item becomes an intention",
                       parents=[common])
    p.add_argument("slug")
    p.add_argument("--under", help="the record it belongs inside, if any")

    p = sub.add_parser("sweep", help="the tick loop", parents=[common])
    p.add_argument("--sink", default="file",
                   choices=("file", "exec", "webhook", "stdout"))
    p.add_argument("--url", help="for --sink webhook")
    p.add_argument("--once", action="store_true", help="one tick, then exit")
    p.add_argument("--every", type=float, default=60.0)
    p.add_argument("argv", nargs="*", help="for --sink exec: the command")

    p = sub.add_parser("stamp", help="write provenance onto memory files")
    p.add_argument("--origin", required=True, choices=ORIGINS)
    p.add_argument("--turn", help="an opaque id for the turn that wrote them")
    p.add_argument("files", nargs="+", type=Path)

    args = ap.parse_args(argv)
    # `init` makes a tree and `stamp` writes onto files it was handed;
    # every other verb reads one, and has to be told where it is or work
    # it out (home.py)
    if args.cmd not in ("init", "stamp"):
        args.memory = home.resolve(args.memory)
        if not args.memory.is_dir():
            print(f"no memory tree at {home.display(args.memory)}",
                  file=sys.stderr)
            print("looked: " + ", ".join(home.ORDER), file=sys.stderr)
            print(f"`rouse init` makes one here, `rouse init --global` "
                  f"makes {home.GLOBAL}", file=sys.stderr)
            return 2
    return globals()[f"cmd_{args.cmd}"](args)


def cmd_init(args) -> int:
    """Lay the skeleton down — in a project, or at the global home.

    `--global` is the whole of the standard-entrypoint idea: an agent
    with no checkout to stand in still has somewhere its memory lives,
    and every other verb finds it without being told (spec/home.md).
    """
    if not SKELETON.is_dir():
        print(f"no skeleton at {SKELETON} — run this from a rouse checkout",
              file=sys.stderr)
        return 2
    if args.globally and args.target is not None:
        print(f"--global lays the tree at {home.GLOBAL} — it doesn't take a "
              "directory as well", file=sys.stderr)
        return 2
    target = (home.tree() if args.globally
              else (args.target or Path(".")) / home.LOCAL)
    if target.exists():
        print(f"{home.display(target)} already exists — not touching it",
              file=sys.stderr)
        return 2
    shutil.copytree(SKELETON / "memory", target)
    shown = home.display(target)
    print(f"wrote {shown}")
    if scaffold.git_init(target):
        print(f"git repository at {shown} — the diffs are the record of what "
              "it changed its mind about")
    print()
    print("add one line to whatever your agent reads at session start")
    print("(CLAUDE.md, AGENTS.md, .cursor/rules, the system prompt):")
    print()
    print(f"    Your memory lives in `{shown}`. "
          f"Read `{shown}/{layout.INSTRUCTIONS}` before using it.")
    print()
    print("that is tier 0 and it works. For the clock:")
    print(f"    python3 -m rouse pack  --memory {shown}   # at session start")
    print(f"    python3 -m rouse sweep --memory {shown}   # between sessions")
    if args.globally:
        print()
        print(f"anything run with no --memory and no ./{home.LOCAL} beside "
              "it finds this tree on its own.")
        print(f"one tree per agent, though — the next one gets its own with "
              f"{home.ENV}=<dir>.")
    return 0


def cmd_pack(args) -> int:
    sys.stdout.write(pack.render(args.memory, budget_ms=args.budget_ms,
                                 query=args.query))
    return 0


def cmd_due(args) -> int:
    now = time.time()
    for item in levels.due(levels.Records(args.memory), now):
        print(f"{item.id}\t{item.reason}\t{files.ago(now - item.since)}"
              f"\t{item.rel}")
    return 0


def cmd_tree(args) -> int:
    sys.stdout.write(scaffold.render_tree(args.memory))
    return 0


def cmd_new(args) -> int:
    try:
        path = scaffold.new(args.memory, args.type, args.slug, args.under)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(path)
    if blank := scaffold.blanks(path):
        print("fill in: " + ", ".join(blank))
    return 0


def cmd_promote(args) -> int:
    try:
        path = scaffold.promote(args.memory, args.slug, args.under)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(path)
    if blank := scaffold.blanks(path):
        print("fill in: " + ", ".join(blank)
              + " — a promoted item without a closes-when is a backlog item "
                "with a clock attached")
    return 0


def cmd_sweep(args) -> int:
    if args.sink == "exec":
        if not args.argv:
            print("--sink exec needs a command", file=sys.stderr)
            return 2
        sink = sweep.ExecSink(args.argv)
    elif args.sink == "webhook":
        if not args.url:
            print("--sink webhook needs --url", file=sys.stderr)
            return 2
        sink = sweep.WebhookSink(args.url)
    elif args.sink == "stdout":
        def sink(item, text, now):
            print(f"--- {item.id}\n{text}")
            return True
    else:
        sink = sweep.FileSink(args.memory)

    if args.once:
        for record, sent in sweep.tick(args.memory, sink):
            print(f"{record}: {'sent' if sent else 'NOT DELIVERED'}")
        return 0
    sweep.loop(args.memory, sink, every=args.every,
               on_tick=lambda line: print(line, flush=True))
    return 0


def cmd_stamp(args) -> int:
    """Provenance, from outside the model's reach.

    If the model can call this with an --origin of its choosing, you have
    rebuilt the hole this field exists to close (spec/provenance.md).
    """
    for path in args.files:
        if path.suffix == ".md" and files.head(path) is not None:
            files.set_fields(path, origin=args.origin, origin_turn=args.turn)
    return 0


# everything a record header carries and a context module has no use
# for. One of these on a belief means somebody expected it to be swept.
CLOCK_FIELDS = ("status", "opened", "last-moved", "stale-after",
                "closes-when", "success-when", "due", "swept", "nudges")

# the context layers are injected whole, every session, forever. This is
# roughly two thousand tokens of them — past it, "keep them few" has
# stopped being true and the pack has started costing real money.
CONTEXT_BUDGET = 8000


def _context(memory: Path) -> list[str]:
    """Lint the two static layers. They have no clock, so almost nothing
    can be wrong with one — which leaves exactly three things that can.

    The layers nest by one directory each — `motivations/` inside
    `beliefs/`, `intentions/` inside `motivations/` — and that one is
    legal. Any other directory in there is somebody putting a ground
    truth inside a ground truth.
    """
    warnings = []
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
    size = sum(len(m.text()) for m in context.layers(memory))
    if size > CONTEXT_BUDGET:
        warnings.append(f"{layout.ENTRYPOINT}: {size} characters of beliefs "
                        f"and motivations, over {CONTEXT_BUDGET} — every "
                        "session pays for all of it. If everything is a "
                        "belief, nothing is")
    return warnings


def cmd_check(args) -> int:
    """Lint. Errors are things that make a record untrackable; warnings
    are things that make it less useful."""
    memory = Path(args.memory)
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

    for line in errors:
        print(f"error: {line}")
    for line in warnings:
        print(f"warn:  {line}")
    if not errors and not warnings:
        print("clean")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
