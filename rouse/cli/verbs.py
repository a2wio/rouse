"""One function per verb: call into core or addons, print, pick a code.

Nothing here decides anything. The tree has already been found by the
time one of these runs (`cli/__init__.py`), the work belongs to the
module it calls, and what is left is the part that is genuinely the
command line's: how a result reads on a terminal, and what the shell
gets back.
"""

import sys
import time

from .. import plugins
from ..addons import check, scaffold
from ..core import files, levels, pack, sweep


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


def cmd_plugin(args) -> int:
    """List what is here, or turn one on or off.

    The list prints both sides — what this install ships and what this
    tree has on — because the interesting case is when they differ: a tree
    copied from another machine names a plugin whose code isn't installed,
    and that is worth seeing rather than silently doing nothing.
    """
    if args.action is None:
        return _plugin_list(args)
    if not args.name:
        print("which plugin? " + ", ".join(plugins.available()),
              file=sys.stderr)
        return 2
    if args.action == "remove":
        return _plugin_remove(args)
    return _plugin_add(args)


def _plugin_list(args) -> int:
    on = plugins.enabled(args.memory)
    for name in sorted(set(plugins.available()) | set(on)):
        line = f"{'on ' if name in on else '   '} {name}"
        if name not in plugins.available():
            line += " — on here, but this install doesn't ship it"
        elif desc := plugins.described(name):
            line += f" — {desc}"
        print(line)
        if name not in on:
            continue
        for at in plugins.recorded(args.memory, name):
            print(f"      skill: {at}"
                  + ("" if (at / "SKILL.md").is_file() else "  [gone]"))
        if blank := plugins.blanks(args.memory, name):
            print(f"      fill in: {', '.join(blank)}")
    if not on:
        print("nothing on in this tree — `rouse plugin add <name>`")
    return 0


def _plugin_add(args) -> int:
    fields = {}
    for pair in args.settings:
        if "=" not in pair:
            print(f"{pair!r} is not key=value", file=sys.stderr)
            return 2
        key, value = pair.split("=", 1)
        fields[key.strip()] = value.strip()
    try:
        path, wrote = plugins.add(args.memory, args.name, fields, args.agent)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    for agent, at in wrote.items():
        print(f"skill for {agent}: {at}")
    if not wrote:
        # the tool works either way; what is missing is the half that
        # tells the model it exists, which is the half installs lose
        print("no agent skill installed — none of "
              + ", ".join(plugins.AGENTS) + " has a directory here, and "
              "rouse doesn't make one your agent hasn't got.")
        print(f"name one and it will: `rouse plugin add {args.name} "
              f"--agent claude-code`")
    print(path)
    if blank := plugins.blanks(args.memory, args.name):
        print("fill in: " + ", ".join(blank))
    print("it is on because that file is there")
    return 0


def _plugin_remove(args) -> int:
    try:
        path, gone = plugins.remove(args.memory, args.name)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    for at in gone:
        print(f"removed {at}")
    print(f"removed {path}")
    print(f"{args.name} is off. The code is still installed — "
          f"`rouse plugin add {args.name}` puts it back")
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


def cmd_check(args) -> int:
    """Lint. Errors are things that make a record untrackable; warnings
    are things that make it less useful."""
    errors, warnings = check.lint(args.memory)
    for line in errors:
        print(f"error: {line}")
    for line in warnings:
        print(f"warn:  {line}")
    if not errors and not warnings:
        print("clean")
    return 1 if errors else 0


def cmd_stamp(args) -> int:
    """Provenance, from outside the model's reach.

    If the model can call this with an --origin of its choosing, you have
    rebuilt the hole this field exists to close (spec/provenance.md).
    """
    for path in args.files:
        if path.suffix == ".md" and files.head(path) is not None:
            files.set_fields(path, origin=args.origin, origin_turn=args.turn)
    return 0
