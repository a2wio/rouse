# the rouse spec

Eight files. Read them in this order; each one assumes the ones above
it.

    home.md          where the tree is, and one tree per agent
    notes.md         durable memory — the frontmatter every file carries
    probes.md        the facts you check instead of remember
    provenance.md    where a file came from, and why the model can't say
    ladder.md        the five levels of intent, and their clocks
    runs.md          tasks and reminders — the two things that actually run
    backlog.md       worth doing, not committed to
    pack.md          what the agent is handed at session start

## the rules underneath all of it

**Context is flat; work is nested.**

    memory/
      entrypoint/
        rouse.md
        beliefs/           belief-<slug>.md        flat, no clock, injected
          motivations/     motivation-<slug>.md    flat, no clock, injected
            intentions/    <slug>/intention.md     records, with clocks
      inventory/
        notes/  probes.md  reminders/  backlog/

`beliefs/` and `motivations/` are one ground truth per file and nothing
else — no status, no clock, no lifecycle. A belief is internal and
timeless; a motivation is an external signal that arrived. The pack puts
all of them in front of the model at the start of every session; they
are a system prompt cut into modules, and the modules are the point. See
`ladder.md`.

**The nesting of those directories is a sentence, not containment.** An
agent has beliefs, is motivated by signals, keeps track in intentions.
Reading down the path reads that. It does not say that a motivation
belongs to a belief or that an intention belongs to a motivation —
nothing says that, and an implementation must not infer it. Exactly one
directory is legal inside each layer, and it is the layer below.

**A record is a directory containing `<type>.md`.** From `intentions/`
down — that is where path-is-parent starts, because that is where the
things in the path are records. The type names the level — `intention`,
`goal`, `action`, `task`, `reminder`, `backlog` — and the directory it
sits in names its parent.

    …/intentions/verify-it/run-it-on-the-branch/task.md

is a task, and what it is a run of is the intention above it, and
nothing in any header says so. Containment used to be a `parent:` field;
a field can disagree with the tree, and then something has to decide
which one is lying.

It also gives every record somewhere to keep its things — the script it
runs, the screenshot it is about, the output it produced — and it makes
`tree` show what is a run of what instead of a pile of directories.

**Two halves at the top.** `entrypoint/` is what you mean: the
instruction file, the context layers, and the records. `inventory/` is
what has no position at all — `notes/`, `probes.md`, `reminders/`,
`backlog/`.

**One tree per agent, and it is found, not passed.** `--memory`, then
`$ROUSE_HOME`, then `./memory`, then `~/.rouse`. Two agents sharing a
tree read each other's beliefs out of the same pack; see `home.md`.

**One thing per record.** A record is the unit of everything: of recall,
of staleness, of a wake. Two topics in one means two clocks fighting over
one `last-moved`.

**Frontmatter is the interface.** Everything a clock, a linter or an
index needs is in the header. Bodies are for the model. No implementation
may need to read a body to decide anything, which is what keeps a sweep
over a thousand records cheap.

**A field exists only where something reads it.** Every field in here
names its reader — `stale-after` is read by the sweep, `keywords` by the
index and by `pack --query`, `origin` by the pack's own rendering. A
field carried by a kind of file that has no reader for it is worse than
clutter: somebody fills it in, and then believes the thing it implies.
`keywords:` on a belief was exactly that — a belief is injected whole on
every turn and is never looked up, so the field said "these get
retrieved" about the one layer that never is. It is a lint warning now.

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

**The examples are ordinary files.** A skeleton ships two beliefs, a
motivation and an intention with a task in it, every slug prefixed
`example-`, so the shape is visible before anything has been written. No
implementation may special-case that prefix — they are injected, walked,
linted and swept like anything else. They are scaffolding rather than
memory, which makes them the one thing in the tree that is meant to be
removed.

## what a conforming implementation must do

Five things, and nothing else is required:

0. **Find the tree in the order above** — `--memory`, `$ROUSE_HOME`,
   `./memory`, `~/.rouse` — and never let two agents onto one. An
   implementation that invents its own order is one an existing memory
   can't be pointed at; see `home.md`.
1. **Inject the context layers.** Every file in `beliefs/` and
   `motivations/`, whole, at the top of every session. They are the only
   bodies that belong in a pack. Thinning the motivations by relevance
   is optional (`pack.md`); thinning the beliefs is never allowed.
2. **Walk and parse.** Find every `<type>.md`, read the header subset
   above, and take each record's parent to be the nearest enclosing
   *record* directory. `beliefs/`, `motivations/` and `intentions/` are
   not records, so a top-level intention has no parent however deep the
   path is.
3. **Compute due** — `due_at = max(last-moved, swept, the level's own
   clock) + stale-after`, floored at 15 minutes, and never for a record
   with something open under it.
4. **Deliver a wake** — at most once per record per tick, and record
   that it delivered. A wake that is lost quietly is the failure mode
   this whole system exists to prevent; see `design/clock.md`.

Everything else — the pack format, the probe runner, the linter, `new`
and `promote` — is convenience. `rouse/` implements all of it in stdlib
python, comments included, in under fourteen hundred lines. That number
is the real claim being made here: this is a set of agreements, not a
platform.
