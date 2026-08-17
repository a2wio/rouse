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
    rouse plugin          what this install ships, and what this tree uses
    rouse <plugin> …      run one — `rouse neon recall "…"`

Every verb but `init` and `stamp` finds the tree the same way: --memory,
then $ROUSE_HOME, then ./.rouse, then ~/.rouse. See rouse/core/home.py.

This file is the argument parser and the table below it, and nothing
else. Every verb is one call into `core/` or `addons/`, so what a flag
is named and what a verb does are two things you can change without
reading each other.

A plugin's own verbs are the one thing not in that table, and they are
dispatched before the parser runs: a plugin owns its flags, and putting
them here would mean importing every plugin on every run to ask what they
are called.
"""

import argparse
import sys
from pathlib import Path

from .. import plugins
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
    "plugin": verbs.cmd_plugin,
}

# the two that don't read an existing tree: `init` makes one, `stamp`
# writes onto files it was handed
ROOTLESS = ("init", "stamp")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `rouse neon sync` — the rest of the line belongs to the plugin,
    # including --memory, which it resolves the way everything else does.
    # Checked against what is installed rather than what this tree has on,
    # so a plugin that isn't on says so in its own words.
    if argv and argv[0] in plugins.available():
        return plugins.run(argv[0], argv[1:])
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

    p = sub.add_parser("plugin", help="what this install ships, and what "
                                      "this tree has on", parents=[common])
    p.add_argument("action", nargs="?", choices=("add", "remove"),
                   help="`add` lays the skill down where your agent finds "
                        "skills and turns the plugin on in this tree; "
                        "`remove` takes both back out")
    p.add_argument("name", nargs="?", help="which plugin")
    p.add_argument("settings", nargs="*", metavar="key=value",
                   help="written straight into the header of the copy in "
                        "the tree — `project=…`. Fields left out stay blank")
    p.add_argument("--agent", action="append", metavar="NAME",
                   help=f"which agent cli the skill is for "
                        f"({', '.join(plugins.AGENTS)}). Repeatable. With "
                        "none of these, every agent already on this box "
                        "that the plugin ships a skill for")

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
