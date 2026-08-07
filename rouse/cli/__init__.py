"""rouse — memory with a clock.

    rouse init [dir]      drop the skeleton in — --wire tells the agent,
                          --global lays it at ~/.rouse
    rouse pack            the context block, for session start
    rouse due             what the clock would wake about, one line each
    rouse sweep           the tick loop, with a wake sink
    rouse new             a record, or a context module (persona/belief/…)
    rouse promote         a backlog item becomes an intention
    rouse tree            the context layers and the records, as they sit
    rouse check           lint the memory tree
    rouse stamp           write provenance — for a wrapper, not the model

Every verb but `init` and `stamp` finds the tree the same way: --memory,
then $ROUSE_HOME, then ./memory, then ~/.rouse. See rouse/core/home.py.

This file is the argument parser and the table below it, and nothing
else. Every verb is one call into `core/` or `addons/`, so what a flag
is named and what a verb does are two things you can change without
reading each other.
"""

import argparse
import sys
from pathlib import Path

from ..addons import wire
from ..core import home, layout, probes
from . import install, verbs

ORIGINS = ("owner", "agent", "system", "untrusted", "unknown")

# the verb, and the one function it is. Nothing dispatches by name
# lookup: a table you can read top to bottom is the whole of what this
# module is for.
VERBS = {
    "init": install.cmd_init,
    "pack": verbs.cmd_pack,
    "due": verbs.cmd_due,
    "check": verbs.cmd_check,
    "tree": verbs.cmd_tree,
    "new": verbs.cmd_new,
    "promote": verbs.cmd_promote,
    "sweep": verbs.cmd_sweep,
    "stamp": verbs.cmd_stamp,
}

# the two that don't read an existing tree: `init` makes one, `stamp`
# writes onto files it was handed
ROOTLESS = ("init", "stamp")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.cmd not in ROOTLESS:
        args.memory = home.resolve(args.memory)
        if not args.memory.is_dir():
            return _no_tree(args.memory)
    return VERBS[args.cmd](args)


def parser() -> argparse.ArgumentParser:
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
    p.add_argument("--wire", action="store_true",
                   help="and tell the agent: append the block to the "
                        f"{' / '.join(wire.FILES)} already in the project. "
                        "Never makes one that isn't there, never appends "
                        "twice")

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
    # optional for exactly one type: `new persona` writes the root file,
    # and there is no second one to tell it apart from
    p.add_argument("slug", nargs="?")
    p.add_argument("--under", help="the slug of the record it sits under, "
                                   "or a path inside the memory directory. "
                                   "Not for a persona, a belief or a "
                                   "motivation — those sit under nothing")

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
    return ap


def _no_tree(memory: Path) -> int:
    """Where it looked, and the two commands that make one. A resolver
    that found nothing has to say which of four rungs it walked, or the
    answer reads as `--memory` being wrong."""
    print(f"no memory tree at {home.display(memory)}", file=sys.stderr)
    print("looked: " + ", ".join(home.ORDER), file=sys.stderr)
    print(f"`rouse init` makes one here, `rouse init --global` "
          f"makes {home.GLOBAL}", file=sys.stderr)
    return 2
