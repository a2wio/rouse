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

## containment is the path

**A record is a directory containing `<type>.md`.** The type names the
level; the directory it sits in names its parent.

    entrypoint/
      green-deploy-isnt-a-migration/            belief
        belief.md
        keep-the-deploy-trustworthy/            motivation
          motivation.md
          2026-03-14-migration-verified/        intention
            intention.md
            verify.sh
            run-it-on-the-branch/               task
              task.md
              output.txt

No field says who the parent is, and that is the point — a field can
disagree with the tree, and then something has to decide which one is
lying. Two more things fall out of it:

- **a record's directory is where its things live.** The script it runs,
  the screenshot it is about, the output it produced. They sit beside
  `<type>.md`, and they move when it moves.
- **`tree` shows the ladder.** Who descends from what, without opening a
  file.

**Levels may be skipped.** A task can sit directly under an intention
when there is no goal worth writing; a parent is the *nearest* enclosing
record, not the one the table says should be there. Zero goals is the
normal case, and the tree should show what you actually wrote.

**Nothing is required above anything.** A record may sit at the top of
`entrypoint/`, and an intention with no motivation over it does exactly
that — it looks unmoored, because it is. `rouse check` warns and never
errors. The alternative, a required chain, means writing an intention
costs you inventing a motivation, which is how you get motivations that
are slogans.

Slugs are what you say out loud, so keep them unique across the tree; the
path is the id when two happen to collide.

## the shared arithmetic

One sweeper walks all of it. Every level does the same three steps —
read the header, ask whether it is moving, wake if it isn't — and what
differs per level is the interval and the question.

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
    swept         machine field — when it was last nudged
    nudges        machine field — how many times

`last-moved` missing falls back to `opened`, then to the file's own
mtime — so a hand-written file with no fields goes stale on schedule
rather than never.

---

## beliefs — `belief.md`

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

A belief with nothing under it is a slogan — worth flagging in a lint
pass, not worth a wake.

## motivations — `motivation.md`

A standing why. An intention with no done state: it never closes, it
only spawns children.

    ---
    status: open              open | review | retired
    opened: 2026-02-11
    last-moved: 2026-03-14 09:00
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

## intentions — `intention.md`

The load-bearing level. What you mean to make true.

    ---
    status: open              open | done | dropped
    opened: 2026-03-14 15:40
    last-moved: 2026-03-14 15:40
    stale-after: 2h
    closes-when: the staging migration has run once with me watching
    ---
    I said I'd verify the migration myself rather than trust the green
    check. Until I've watched it run, I haven't.

- `closes-when` — one line, written as something you could actually
  check. "It's better" is not checkable; "the migration has run once
  with me watching" is.
- Default `stale-after` is 2h.

**Write it in the same turn you say the thing.** Not everything said
becomes a record — an intention is something you would be embarrassed to
have quietly dropped.

### the two endings

**An intention cannot evaporate.** It ends exactly two ways:

- `status: done` — it is true now. Say so.
- `status: dropped` — you are letting it go. **Say so, and say why.** A
  quiet drop is the exact failure the level exists to stop.

Either way it earns a line in `inventory/notes/` afterwards; the dropped
ones teach more than the done ones. The directory stays where it is —
closed, not deleted, with everything it accumulated still in it.

If a sweep catches something whose next move honestly isn't yours, say
that, and push `last-moved` forward so it comes back later.

## goals — `goal.md`

A loop rather than a one-shot: try, judge, revise, try again.

    ---
    status: open              open | done | abandoned
    opened: 2026-03-14 18:00
    last-moved: 2026-03-14 18:00
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

## actions — `action.md`

The one-shot below an intention or a goal, and the only level that
carries the field nothing else has.

    ---
    status: open              open | done | dropped
    opened: 2026-03-14 18:00
    last-moved: 2026-03-14 18:00
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
of it gets revised. Without it the beliefs are decoration. It is also the
one relationship the tree cannot express — a contradicted belief is
somewhere else entirely — so it goes in the body, in words, where a
person will read it.

**Zero tasks is the normal case.** An action you did yourself in a turn
is a record you write and judge in the same turn. Swept after 1d with no
task under it and no outcome on it.

## the defaults, in one table

    level         stale-after   own clock                  ends
    belief        never         —                          held / released
    motivation    7d            —                          retired
    intention     2h            —                          done / dropped
    goal          1h            last ending underneath      done / abandoned
    action        1d            —                          done / dropped (+ outcome)

All of them are guesses that should be configurable, and all of them err
quiet. A nudge system is judged by whether its nudges are still read
after a month.
