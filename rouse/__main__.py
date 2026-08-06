"""rouse — memory with a clock.

    rouse init [dir]      drop the skeleton in, print the one line to wire
    rouse pack            the context block, for session start
    rouse due             what the clock would wake about, one line each
    rouse sweep           the tick loop, with a wake sink
    rouse check           lint the memory tree
    rouse stamp           write provenance — for a wrapper, not the model
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

from . import files, levels, pack, probes, sweep

SKELETON = Path(__file__).resolve().parents[1] / "skeleton"
ORIGINS = ("owner", "agent", "system", "untrusted", "unknown")
LADDER_DIRS = ("beliefs", "motivations", "goals", "actions")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rouse", description=__doc__.strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--memory", default=Path("memory"), type=Path,
                    help="the memory directory (default: ./memory)")

    # the same flag on both sides, so `rouse --memory X pack` and
    # `rouse pack --memory X` both work. SUPPRESS is what stops the
    # subparser's default from clobbering a value given before the verb.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--memory", type=Path, default=argparse.SUPPRESS,
                        help="the memory directory (default: ./memory)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="drop the skeleton in")
    p.add_argument("target", nargs="?", default=".", type=Path)
    p.add_argument("--ladder", action="store_true",
                   help="also create beliefs/ motivations/ goals/ actions/")

    p = sub.add_parser("pack", help="the context block for session start",
                       parents=[common])
    p.add_argument("--budget-ms", type=int, default=probes.BUDGET_MS)

    sub.add_parser("due", help="what the clock would wake about",
                   parents=[common])
    sub.add_parser("check", help="lint the memory tree", parents=[common])

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
    return globals()[f"cmd_{args.cmd}"](args)


def cmd_init(args) -> int:
    if not SKELETON.is_dir():
        print(f"no skeleton at {SKELETON} — run this from a rouse checkout",
              file=sys.stderr)
        return 2
    target = args.target / "memory"
    if target.exists():
        print(f"{target} already exists — not touching it", file=sys.stderr)
        return 2
    shutil.copytree(SKELETON / "memory", target)
    if args.ladder:
        for name in LADDER_DIRS:
            (target / name).mkdir()
            (target / name / ".gitkeep").touch()
    try:
        target = target.relative_to(Path.cwd())
    except ValueError:
        pass
    print(f"wrote {target}")
    print()
    print("add one line to whatever your agent reads at session start")
    print("(CLAUDE.md, AGENTS.md, .cursor/rules, the system prompt):")
    print()
    print(f"    Your memory lives in `{target}`. "
          f"Read `{target}/rouse.md` before using it.")
    print()
    print("that is tier 0 and it works. For the clock:")
    print(f"    python3 -m rouse pack  --memory {target}   # at session start")
    print(f"    python3 -m rouse sweep --memory {target}   # between sessions")
    return 0


def cmd_pack(args) -> int:
    sys.stdout.write(pack.render(args.memory, budget_ms=args.budget_ms))
    return 0


def cmd_due(args) -> int:
    now = time.time()
    found = levels.due(levels.Records(args.memory), now)
    for item in found:
        print(f"{item.id}\t{item.reason}\t{files.ago(now - item.since)}")
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


def cmd_check(args) -> int:
    """Lint. Errors are things that make a record untrackable; warnings
    are things that make it less useful."""
    memory = Path(args.memory)
    records = levels.Records(memory)
    errors, warnings = [], []

    def rel(path):
        return path.relative_to(memory) if memory in path.parents else path

    for name in (*levels.LEVELS, *levels.RUNS, "backlog"):
        records.level(name)
    for path in records.broken:
        errors.append(f"{rel(path)}: no header — nothing can track this")

    known = {path.stem for name in (*levels.LEVELS, *levels.RUNS)
             for path, _ in records.level(name)}

    for name in (*levels.LEVELS, *levels.RUNS, "backlog"):
        for path, head in records.level(name):
            where = rel(path)
            for field, parse in (("stale-after", files.parse_interval),
                                 ("nag", files.parse_interval),
                                 ("last-moved", files.parse_stamp),
                                 ("due", files.parse_stamp),
                                 ("opened", files.parse_stamp)):
                if head.get(field) and parse(head[field]) is None:
                    errors.append(f"{where}: unparseable {field}: "
                                  f"{head[field]!r}")
            if (parent := head.get("parent")) and levels.stem(parent) not in known:
                warnings.append(f"{where}: parent {parent!r} doesn't exist")
            if name == "intentions" and not head.get("closes-when"):
                warnings.append(f"{where}: no closes-when — you can't tell "
                                "when this is finished")
            if name == "backlog":
                for field in ("stale-after", "last-moved", "parent"):
                    if head.get(field):
                        warnings.append(f"{where}: backlog items have no "
                                        f"clock — drop {field}, or promote "
                                        "this to an intention")
            if name == "reminders" and not head.get("due"):
                errors.append(f"{where}: a reminder with no due is not a "
                              "reminder")

    for path, head in records.level("beliefs"):
        if not any(level == "motivations"
                   for level, _, _ in records.children(path.stem)):
            warnings.append(f"{rel(path)}: no motivation under this belief — "
                            "it's a slogan until something acts on it")

    for path in sorted((memory / "notes").rglob("*.md")):
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
    quiet_ok = {p.name for p in probes.read(memory / "probes.md")
                if p.unknown_ok}
    for name, value in readings:
        if value == probes.UNKNOWN and name not in quiet_ok:
            warnings.append(f"probes.md: {name} answered <unknown>")
    if spent > probes.BUDGET_MS:
        warnings.append(f"probes.md: the pack tier took {spent}ms of its "
                        f"{probes.BUDGET_MS}ms — move something to demand")

    for line in errors:
        print(f"error: {line}")
    for line in warnings:
        print(f"warn:  {line}")
    if not errors and not warnings:
        print("clean")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
