"""`rouse init` — the only verb a person runs before there is a tree.

It is almost entirely printing, and that is the job: this is the one
screen anybody reads, so it says what it made, what it wired, what it
refused to wire and why, and what the two tiers above tier 0 are. The
work underneath is four calls into `addons/`.
"""

import sys
from pathlib import Path

from ..addons import scaffold, wire
from ..core import home, layout


def cmd_init(args) -> int:
    """Lay the skeleton down — in a project, or at the global home.

    `--global` is the whole of the standard-entrypoint idea: an agent
    with no checkout to stand in still has somewhere its memory lives,
    and every other verb finds it without being told (spec/home.md).

    `--wire` is the step after, done in the same run, because a tree the
    agent was never told about is the commonest way this ends up doing
    nothing (rouse/addons/wire.py). It is also the one flag with
    something left to do when the tree is already there, so with it an
    existing `memory/` is news rather than an error.
    """
    if not scaffold.SKELETON.is_dir():
        print(f"no skeleton at {scaffold.SKELETON} — run this from a rouse "
              "checkout", file=sys.stderr)
        return 2
    if args.globally and args.target is not None:
        print(f"--global lays the tree at {home.GLOBAL} — it doesn't take a "
              "directory as well", file=sys.stderr)
        return 2
    target = (home.tree() if args.globally
              else (args.target or Path(".")) / home.LOCAL)
    shown = home.display(target)
    if target.exists():
        if not args.wire:
            print(f"{shown} already exists — not touching it",
                  file=sys.stderr)
            return 2
        print(f"{shown} already exists — leaving it alone")
    else:
        scaffold.lay(target)
        print(f"wrote {shown}")
        if scaffold.git_init(target):
            print(f"git repository at {shown} — the diffs are the record of "
                  "what it changed its mind about")
    print()
    if args.wire:
        _wire(args, target)
    else:
        run = wire.cli()
        print("add one line to whatever your agent reads at session start")
        print("(CLAUDE.md, AGENTS.md, .cursor/rules, the system prompt):")
        print()
        print(f"    Your memory lives in `{shown}`. "
              f"Read `{shown}/{layout.INSTRUCTIONS}` before using it.")
        print()
        print("that is tier 0 and it works. For the clock:")
        print(f"    {run} pack  --memory {shown}   # at session start")
        print(f"    {run} sweep --memory {shown}   # between sessions")
    # the one layer the skeleton deliberately doesn't ship, so this line
    # is the only place a person finds out it exists
    print()
    print(f"optional: `{shown}/{layout.PERSONA}` is how this agent talks — "
          "written, it goes")
    print("into every session above the beliefs. `rouse new persona` starts "
          "one. An agent")
    print("that only reviews code doesn't want one; anything a person talks "
          "to does.")
    if args.globally:
        print()
        print(f"anything run with no --memory and no ./{home.LOCAL} beside "
              "it finds this tree on its own.")
        print(f"one tree per agent, though — the next one gets its own with "
              f"{home.ENV}=<dir>.")
    return 0


def _wire(args, target: Path) -> None:
    """`--wire`: the block, into the files this project already has.

    Everything it can't do, it prints instead. A wire that quietly
    created a `CLAUDE.md` in a repo that never had one would be an
    install that looks finished and is read by nobody, which is the
    exact failure `--wire` exists to remove.
    """
    def paste(where: str, text: str) -> None:
        print(f"paste this into {where}:")
        print()
        print("\n".join(f"    {line}" if line else ""
                        for line in text.splitlines()))

    root = target.parent
    names = " or ".join(wire.FILES)
    if args.globally:
        # ~/.rouse has no project around it, and what this agent reads at
        # session start is its own global config — a file in somebody's
        # home directory that `init` has no business appending to
        print(f"nothing to wire: {home.GLOBAL} has no project around it.")
        paste("whatever this agent reads at session start "
              "(~/.claude/CLAUDE.md,\n~/.codex/AGENTS.md, a system prompt)",
              wire.block(target))
    elif done := wire.wire(root, target):
        for path, appended in done:
            print(f"{'wired' if appended else 'already wired'} "
                  f"{home.display(path)}")
    else:
        print(f"no {names} in {home.display(root)} — nothing wired.")
        print("rouse doesn't make a file your agent hasn't got.")
        paste(f"whichever one it reads ({names})", wire.block(target, root))
    print()
    print("the pack is tier 1, at session start. Tier 2 is the clock:")
    print(f"    {wire.cli()} sweep --memory {home.display(target)}   "
          "# between sessions")
