# the ladder — five levels of intent

Everything that wakes an agent is somebody else's trigger: a message, a
finished job, a clock. "I'll check the rest myself" has none of those.
So it sits, and the operator finds out by asking.

The ladder is the fix, and it is one sentence: **not moving is a trigger
too.**

    belief        ground truth. No clock, ever.
      motivation  a standing why. Never reaches done.
        intention what you mean to make true. Nudged when it stops moving.
          goal    a loop with a success condition.
            action one shot — and the only level that carries an outcome.

Five flat directories under `memory/`. Containment is the `parent:`
field, by file stem, never by path:

    parent: 2026-03-01-be-answerable-for-what-i-promise
    parent: motivations/2026-03-01-be-answerable-for-what-i-promise

Both forms mean the same thing; the directory prefix is allowed because
it reads better. A record with no parent is fine — the field makes *why
does this exist* answerable, it is not a requirement.

## the shared arithmetic

One sweeper walks all of it. Every level does the same three steps —
read the header, ask whether it is moving, wake if it isn't — and what
differs per level is the directory, the interval, and the question.

    due_at = max(last-moved, swept, the level's own clock) + stale-after

Two rules apply everywhere:

**Nothing is swept while something is open under it.** Work in flight is
not a stalled intention, and nudging about it is the noise that makes
nudges stop working — after which they can't catch the real ones.

**Fifteen minutes floors everything**, whatever a file asks for. A typo
that says `stale-after: 1m` would otherwise nudge every minute until
the agent stopped reading nudges.

Shared fields, at every level:

    status        which of that level's states it is in
    opened        when it started
    last-moved    when it last moved. YOURS to stamp.
    stale-after   30m / 2h / 1d. Omit for the level's default.
    parent        the record above it, by stem
    swept         machine field — when it was last nudged
    nudges        machine field — how many times

`last-moved` missing falls back to `opened`, then to the file's own
mtime — so a hand-written file with no fields goes stale on schedule
rather than never.

---

## beliefs — `memory/beliefs/`

Ground truth about the world the agent works in. **Never swept. Nothing
nudges you about a belief, ever.**

    ---
    status: held
    learned: 2026-02-11
    ---
    A green deploy does not mean the migration ran. The check goes green
    on the container starting, and the migration step is allowed to be
    skipped without failing anything.

    Taught by: twice this quarter, staging served the old schema for a
    day behind a green pipeline.
    Would stop believing it if: the pipeline started failing on a skipped
    migration.

Writing one is a real act, not a note. It carries the day it was
learned, what taught it, and what would make you stop believing it.
Keep them few. If everything is a belief, nothing is.

A belief with no motivation under it is a slogan — worth flagging in a
lint pass, not worth a wake.

## motivations — `memory/motivations/`

A standing why. An intention with no done state: it never closes, it
only spawns children.

    ---
    status: open              open | review | retired
    opened: 2026-02-11
    last-moved: 2026-03-14 09:00
    parent: beliefs/green-deploy-isnt-a-migration
    signals: nobody asks "did the migration actually run" anymore
    ---
    Keep the deploy trustworthy — the pipeline should be evidence, not
    a vibe.

**Stale when nothing is open under it for 7 days.** That is the only
condition, and it is the right one: a motivation with no children means
either you have quietly stopped acting on it, or you are acting on it
without having written anything down. Both are worth a question.

Ends `retired`, out loud, the way an intention ends `dropped`.
`status: review` counts as open and keeps being swept — parking one in
review forever is evaporation with extra steps.

## intentions — `memory/intentions/`

The load-bearing level. What you mean to make true.

    ---
    status: open              open | done | dropped
    opened: 2026-03-14 15:40
    last-moved: 2026-03-14 15:40
    stale-after: 2h
    closes-when: the staging migration has run once with me watching
    parent: motivations/keep-the-deploy-trustworthy
    ---
    I said I'd verify the migration myself rather than trust the green
    check. Until I've watched it run, I haven't.

- `closes-when` — one line, written as something you could actually
  check. "It's better" is not checkable; "the migration has run once
  with me watching" is.
- Default `stale-after` is 2h.

**Write it in the same turn you say the thing.** Not everything said
becomes a file — an intention is something you would be embarrassed to
have quietly dropped.

### the two endings

**An intention cannot evaporate.** It ends exactly two ways:

- `status: done` — it is true now. Say so.
- `status: dropped` — you are letting it go. **Say so, and say why.** A
  quiet drop is the exact failure the level exists to stop.

Either way it earns a line in `memory/notes/` afterwards; the dropped
ones teach more than the done ones. The file stays where it is —
closed, not deleted.

If a sweep catches something whose next move honestly isn't yours, say
that, and push `last-moved` forward so it comes back later.

## goals — `memory/goals/`

A loop rather than a one-shot: try, judge, revise, try again.

    ---
    status: open              open | done | abandoned
    opened: 2026-03-14 18:00
    last-moved: 2026-03-14 18:00
    parent: intentions/2026-03-14-migration-verified
    success-when: two consecutive deploys need no manual step
    falsifiers: the manual step turns out to be a platform limit
    review-every: 7d
    waiting-on: their infra team to answer
    ---
    What winning looks like, and what to try next.

The trigger is what makes this its own level. An intention is stale when
nothing moved. **A goal is stale when the last outcome landed and no
next action was issued** — which can happen five seconds after something
moved. Default 1h after the newest ending underneath.

`review-every:` is the only clock that fires *while* something is moving
underneath, because whether you still want the thing does not depend on
whether an action is in flight. It stamps `reviewed:`. For a long
horizon whose success can't be evaluated yet, that review is the whole
check: stop looking for success, start looking for what would kill it.
`abandoned` with the falsifier that fired is a real outcome, not a
failure.

## actions — `memory/actions/`

The one-shot below an intention or a goal, and the only level that
carries the field nothing else has.

    ---
    status: open              open | done | dropped
    opened: 2026-03-14 18:00
    last-moved: 2026-03-14 18:00
    parent: intentions/2026-03-14-migration-verified
    closes-when: I've run it on the branch and read the output
    outcome:                  as-expected | surprising | contradicts
    ---
    What you meant to do — and, once judged, what actually became true.

**`outcome:` is the judgment.** Not what a worker did — a task saying
`done` means the job ran, which is not the same as the thing you wanted
becoming true. Nothing writes it for you.

Where it lands next is what the three words are for:

    as-expected   closes it.
    surprising    open the intention that just became obvious.
    contradicts   name the belief you are no longer sure of.

That last one is the back edge: the bottom of the ladder is how the top
of it gets revised. Without it the beliefs are decoration.

**Zero tasks is the normal case.** An action you did yourself in a turn
is a file you write and judge in the same turn. Swept after 1d with no
task under it and no outcome on it.

## the defaults, in one table

    level         stale-after   own clock                  ends
    belief        never         —                          held / released
    motivation    7d            —                          retired
    intention     2h            —                          done / dropped
    goal          1h            last ending underneath     done / abandoned
    action        1d            —                          done / dropped (+ outcome)

All of them are guesses that should be configurable, and all of them err
quiet. A nudge system is judged by whether its nudges are still read
after a month.
