# the rouse spec

Seven files. Read them in this order; each one assumes the ones above
it.

    notes.md         durable memory — the frontmatter every file carries
    probes.md        the facts you check instead of remember
    provenance.md    where a file came from, and why the model can't say
    ladder.md        the five levels of intent, and their clocks
    runs.md          tasks and reminders — the two things that actually run
    backlog.md       worth doing, not committed to
    pack.md          what the agent is handed at session start

## the rules underneath all of it

**A record is a directory containing `<type>.md`.** The type names the
level — `belief`, `motivation`, `intention`, `goal`, `action`, `task`,
`reminder`, `backlog`. The directory it sits in names its parent.

    entrypoint/liability/keep-the-deploy-trustworthy/verify-it/intention.md

is an intention, under a motivation, under a belief, and nothing in any
header says so. Containment used to be a `parent:` field; a field can
disagree with the tree, and then something has to decide which one is
lying.

It also gives every record somewhere to keep its things — the script it
runs, the screenshot it is about, the output it produced — and it makes
`tree` show the ladder instead of a pile of directories.

**Two halves.** `entrypoint/` is intent: the instruction file and every
record with a position in the ladder. `inventory/` is what has no
position — `notes/`, `probes.md`, `reminders/`, `backlog/`.

**One thing per record.** A record is the unit of everything: of recall,
of staleness, of a wake. Two topics in one means two clocks fighting over
one `last-moved`.

**Frontmatter is the interface.** Everything a clock, a linter or an
index needs is in the header. Bodies are for the model. No implementation
may need to read a body to decide anything, which is what keeps a sweep
over a thousand records cheap.

**The header is a subset of YAML on purpose.** `key: value`, one line
each, no nesting, no lists, no anchors. A parser for it is thirty lines
of stdlib, so nobody has to install anything to read a memory file, and
a model writing one by hand cannot get it subtly wrong.

**Machine fields are not the model's.** Some fields are stamped by
whatever runs the clock and must never be typed by the model:
`swept:`, `nudges:`, `fires:`, `set:`, `origin:`, `origin-turn:`,
`delivered:`. Each spec file marks its own. The rule exists because a
field the model can write is a field an injected instruction can write.

**Stamps are local time, `YYYY-MM-DD HH:MM`.** Date alone means
midnight. Intervals are `30m` / `2h` / `1d`. Both are chosen so a human
editing a file by hand gets them right without looking anything up.

**Nothing is deleted.** A record that ends changes its `status:` and
stays where it is. The history of what you meant to do and didn't is
worth more than the tidiness.

**The examples are ordinary records.** A skeleton ships one example
chain, every slug prefixed `example-`, so the shape is visible before
anything has been written. No implementation may special-case that
prefix — they are walked, linted and swept like anything else. They are
scaffolding rather than memory, which makes them the one thing in the
tree that is meant to be removed.

## what a conforming implementation must do

Three things, and nothing else is required:

1. **Walk and parse.** Find every `<type>.md`, read the header subset
   above, and take each record's parent to be the nearest enclosing
   record directory.
2. **Compute due** — `due_at = max(last-moved, swept, the level's own
   clock) + stale-after`, floored at 15 minutes, and never for a record
   with something open under it.
3. **Deliver a wake** — at most once per record per tick, and record
   that it delivered. A wake that is lost quietly is the failure mode
   this whole system exists to prevent; see `design/clock.md`.

Everything else — the pack format, the probe runner, the linter, `new`
and `promote` — is convenience. `rouse/` implements all of it in stdlib
python, comments included, in under fourteen hundred lines. That number
is the real claim being made here: this is a set of agreements, not a
platform.
