# backlog — the level with no clock

`memory/backlog/` sits beside the ladder and answers the thing the
sweeper cannot express: **worth doing, not committed to.**

    ---
    status: open              open | promoted | dropped
    opened: 2026-03-14
    keywords: backlog, migrations, rollback, tooling
    ---
    What it is, why it's worth doing, and what was said when it got
    parked.

No `last-moved`, no `stale-after`, no `parent`. **Nothing nudges you
about a backlog item, ever.**

## why it has to exist

Without it, everything that is worth doing eventually becomes an
intention, and every intention that isn't happening this week gets its
`stale-after` inflated to keep the sweep quiet. Then the nudges stop
meaning anything, and a system whose nudges don't mean anything is a
system with no clock.

So the tell is exact: **the moment you find yourself writing
`stale-after: 30d`, the thing you wanted was a backlog file.**

## the price of having no clock

An item may leave in exactly two ways:

- **promoted** — it becomes an intention with its own clock, and the
  backlog file records that it did.
- **dropped** — out loud, to the operator, with the reason. Same rule as
  a dropped intention.

Nothing else, and never silently. An item that quietly stops existing is
the failure the whole ladder was built against; the backlog is allowed
to have no clock *only* because it has no quiet exit.

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
