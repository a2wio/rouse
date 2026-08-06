# backlog — the level with no clock

`inventory/backlog/` sits beside the ladder and answers the thing the
sweeper cannot express: **worth doing, not committed to.**

    inventory/backlog/pin-the-runner-version/
      backlog.md

    ---
    status: open              open | promoted | dropped
    opened: 2026-03-14
    keywords: backlog, migrations, rollback, tooling
    ---
    What it is, why it's worth doing, and what was said when it got
    parked.

No `last-moved`, no `stale-after`. **Nothing nudges you about a backlog
item, ever.** It is in `inventory/` for exactly that reason: it has no
position in the record half, because a position in the record half is a
clock.

It is not a belief either, though both are quiet. A belief is something
that is true; a backlog item is something that isn't done. The quiet
comes from opposite directions and only one of them owes you an ending.

## why it has to exist

Without it, everything that is worth doing eventually becomes an
intention, and every intention that isn't happening this week gets its
`stale-after` inflated to keep the sweep quiet. Then the nudges stop
meaning anything, and a system whose nudges don't mean anything is a
system with no clock.

So the tell is exact: **the moment you find yourself writing
`stale-after: 30d`, the thing you wanted was a backlog item.**

## the price of having no clock

An item may leave in exactly two ways:

- **promoted** — it becomes an intention with its own clock.
- **dropped** — out loud, to the operator, with the reason. Same rule as
  a dropped intention. `status: dropped`, and it stays where it is.

Nothing else, and never silently. An item that quietly stops existing is
the failure the whole ladder was built against; the backlog is allowed
to have no clock *only* because it has no quiet exit.

## promotion is a move

Under the flat layout, promoting meant editing a field. Now it is what
it always was underneath — the thing changes level, so it changes place:

    git mv inventory/backlog/pin-the-runner-version \
           entrypoint/intentions/
    mv .../pin-the-runner-version/backlog.md .../intention.md

and the header becomes an intention's: `status: open`, a fresh
`last-moved`, a `stale-after`, and the `closes-when` it now owes. Two
fields record where it came from:

    promoted: 2026-03-14 15:40
    was: inventory/backlog/pin-the-runner-version

Everything the item had accumulated while it was parked — the link
somebody sent, the half-written script, the screenshot — moves with the
directory, which is most of why the directory exists.

**No tombstone is left behind.** The backlog is a list of what is still
parked, and it stays readable by not accumulating what has left; where
this one went is in git, and where it came from is in its own header.
`rouse promote <slug>` does the whole thing in one command, because a
two-command move is a move somebody does halfway.

## when to write one

- Something got parked. Write it in the same turn it was parked, with
  what was said.
- You noticed work worth doing that isn't now. Especially this one —
  it is the thought that otherwise dies in a session and reappears as
  the same discovery three weeks later.

A backlog that is never read is a landfill, so it gets read the way
notes do: it is indexed by keywords in the pack, and a periodic
gardening pass walks it and asks, per item, promote or drop. That pass
is the only thing that ever touches it on a schedule, and it touches the
directory, not any single item.
