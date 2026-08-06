"""The tree: the two static layers, the record tree, and the inventory.

There are two different kinds of thing in here and they are not the same
kind of thing at all.

**Context layers** — `beliefs/` and `motivations/` — are flat files, one
ground truth each. No status, no clock, no lifecycle. They are the
modular system prompt: the pack injects them whole at the top of every
session, and that is the entire mechanism. Modularity is the point — one
fact per file, so a fact can be added, dropped or shared without editing
a wall of prose.

**Records** — `intentions/` and everything under it — are the half with
a clock:

    A record is a DIRECTORY containing `<type>.md`.
    The type names the level. The path names the parent.

So this is an intention, and the task inside it is a run of that
intention:

    …/intentions/2026-03-14-migration-verified/
      intention.md
      run-it-on-the-branch/task.md

No field says that, which is the point — a field can disagree with the
tree, and then somebody has to decide which one is lying.

**The level directories nest, and that nesting is the story, not
containment**:

    entrypoint/
      rouse.md
      beliefs/
        belief-<slug>.md
        motivations/
          motivation-<slug>.md
          intentions/
            <slug>/intention.md

An agent has beliefs; it is motivated by signals from outside; it keeps
track of what it means to do in intentions. Reading down the path is
reading that sentence. What the path does NOT say is which motivation an
intention answers — no item ever contains another item across levels,
and `parent()` below only ever finds a *record*, which none of these
three directories is. Path-is-parent applies from `intentions/` down.

The two halves at the top: `entrypoint/` is what you mean — the
instruction file, the context layers, and the records. `inventory/` is
everything with no position: notes, probes, reminders, parked items.
"""

# the two halves
ENTRYPOINT = "entrypoint"
INVENTORY = "inventory"

INSTRUCTIONS = "entrypoint/rouse.md"

# the static layers: flat `<type>-<slug>.md` files, injected wholesale.
# Each one holds the layer below it, and nothing else that is a directory.
BELIEFS = "entrypoint/beliefs"
MOTIVATIONS = "entrypoint/beliefs/motivations"

# the top of the record tree
INTENTIONS = "entrypoint/beliefs/motivations/intentions"

# the one subdirectory each context layer may hold: the next layer down.
# Anything else in there is somebody nesting one ground truth inside
# another, which is the lineage this shape does not have.
NESTS = {"belief": "motivations", "motivation": "intentions"}

NOTES = "inventory/notes"
PROBES = "inventory/probes.md"
REMINDERS = "inventory/reminders"
BACKLOG = "inventory/backlog"

# the sweeper's own scratch: cached demand readings, undelivered wakes
SCRATCH = ".rouse"

# the static layers, in the order the pack prints them
CONTEXT = ("belief", "motivation")

# levels of intent that are records — nested, clocked, swept
LADDER = ("intention", "goal", "action")

# the things that run
RUNS = ("task", "reminder")

# every type whose `<type>.md` makes a directory a record
TYPES = (*LADDER, *RUNS, "backlog")

# everything `rouse new` knows how to write
WRITABLE = (*CONTEXT, *TYPES)

# where `rouse new` puts one when nothing says otherwise. Records
# default to the top of the record tree; you nest them by naming what
# they sit under.
HOMES = {"belief": BELIEFS, "motivation": MOTIVATIONS,
         "reminder": REMINDERS, "backlog": BACKLOG}


def home(type_: str) -> str:
    return HOMES.get(type_, INTENTIONS)
