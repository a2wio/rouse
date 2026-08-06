"""The tree: what a record is, and where its two halves live.

One rule covers all of it:

    A record is a DIRECTORY containing `<type>.md`.
    The type names the level. The path names the parent.

So this is an intention, its parent is the motivation one directory up,
and its grandparent is a belief:

    entrypoint/green-deploy-isnt-a-migration/keep-the-deploy-trustworthy/
        2026-03-14-migration-verified/intention.md

No field says any of that, which is the point — a field can disagree with
the tree, and then somebody has to decide which one is lying.

Two reasons this beats the flat directories and a `parent:` field:

- a record usually acquires files. The script it runs, the screenshot it
  is about, the diff it produced. A record that is a directory has
  somewhere to put them, and they travel with it.
- `tree` should show the ladder. With containment in a field, reading
  who-descends-from-what means opening every file in the tree.

The two halves: `entrypoint/` is intent — the instruction file and every
record that has a position in the ladder. `inventory/` is everything with
no position: notes, probes, reminders, parked items.
"""

# the two halves
ENTRYPOINT = "entrypoint"
INVENTORY = "inventory"

INSTRUCTIONS = "entrypoint/rouse.md"
NOTES = "inventory/notes"
PROBES = "inventory/probes.md"
REMINDERS = "inventory/reminders"
BACKLOG = "inventory/backlog"

# the sweeper's own scratch: cached demand readings, undelivered wakes
SCRATCH = ".rouse"

# levels of intent, top to bottom
LADDER = ("belief", "motivation", "intention", "goal", "action")

# the things that run
RUNS = ("task", "reminder")

# every type whose `<type>.md` makes a directory a record
TYPES = (*LADDER, *RUNS, "backlog")

# where `rouse new` puts one when nothing says otherwise. Ladder records
# and tasks default to the top of the ladder; you nest them by naming
# what they sit under.
HOMES = {"reminder": REMINDERS, "backlog": BACKLOG}


def home(type_: str) -> str:
    return HOMES.get(type_, ENTRYPOINT)
