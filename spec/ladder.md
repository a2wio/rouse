# the ladder — five levels of intent, in two halves

Everything that wakes an agent is somebody else's trigger: a message, a
finished job, a clock. "I'll check the rest myself" has none of those.
So it sits, and the operator finds out by asking.

The ladder is the fix, and it is one sentence: **not moving is a trigger
too.**

    belief      ground truth. No clock, ever.        ┐ context: flat files,
    motivation  what you are currently for.          ┘ injected every session

    intention   what you mean to make true. Nudged when it stops moving.
      goal      a loop with a success condition.
        action  one shot — and the only level that carries an outcome.

Five levels, with a line across the middle. **Beliefs and motivations
are context. Intentions and down are records.** Treating those as one
kind of thing is the mistake this spec is written against, and the
indentation above is the trap: the bottom three nest in the filesystem
and the top two do not nest in anything.

---

## the context half — `beliefs/` and `motivations/`

Flat files, one ground truth each:

    entrypoint/
      beliefs/
        belief-zero-downtime-deploys.md
        belief-plan-before-code.md
      motivations/
        motivation-keep-the-deploy-trustworthy.md

    ---
    keywords: deploy, downtime, rollout, migrations
    ---
    Deployments always happen with no downtime. A rollout that needs a
    maintenance window is a rollout that went wrong earlier.

**No status. No clock. No lifecycle. Nothing nested inside.** Nothing
sweeps one, nothing nudges about one, and there is no `done` for a thing
that is simply true. The header is optional, `keywords:` is the only
field anything reads, and it is there for grep rather than for a
machine.

**The pack injects all of them, whole, at the start of every session.**
That is the entire mechanism. These files are a system prompt cut into
modules, and modularity is the point: one fact per file means a rule can
be added, dropped, reviewed, or handed to a second agent without editing
a wall of prose, and it means the diff on a rule change is one line
rather than a paragraph.

The two directories differ only in what their files are about. A belief
is about the world: how deploys behave, what a green check means, how
this team works. A motivation is about what you are currently trying to
be true to, which makes it the shorter-lived of the two and makes it the
thing an intention serves.

**A motivation holds an intention semantically, not in the filesystem.**
It says why the intention exists, in its own body, in words. There is no
`motivation:` field on an intention and no directory nesting one inside
the other. Adding either costs something specific: the intention closes
and the motivation doesn't, so the link spends most of its life pointing
at something finished. If you want the connection written down, write
the sentence.

There is no orphan rule. Nothing is above an intention, so nothing can
be missing above it.

**Naming.** `belief-<slug>.md`, `motivation-<slug>.md`. The prefix
repeats the directory on purpose, so the file still says what it is
after somebody copies it into another repo. Given the point of splitting
them up, that is going to happen.

**Keep them few.** Every session pays for all of them. If everything is
a belief, nothing is; a linter that warns past a couple of thousand
tokens of context is doing you a favour.

---

## the record half — `intentions/` and down

**A record is a directory containing `<type>.md`.** The type names the
level; the directory it sits in names its parent.

    entrypoint/intentions/
      2026-03-14-migration-verified/            intention
        intention.md
        verify.sh
        run-it-on-the-branch/                   task
          task.md
          output.txt

No field says who the parent is, and that is the point — a field can
disagree with the tree, and then something has to decide which one is
lying. Two more things fall out of it:

- **a record's directory is where its things live.** The script it runs,
  the screenshot it is about, the output it produced. They sit beside
  `<type>.md`, and they move when it moves.
- **`tree` shows what is a run of what.** Without opening a file.

**Levels may be skipped.** A task can sit directly under an intention
when there is no goal worth writing; a parent is the *nearest* enclosing
record, not the one the table says should be there. Zero goals is the
normal case, and the tree should show what you actually wrote.

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

## intentions — `intention.md`

The load-bearing level, and the top of the record half.

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

That last one is the back edge, and it is the only traffic that runs
upward: the bottom of the record half is how the context half gets
revised. Without it the beliefs are decoration. It is a sentence in the
body naming the file — `belief-zero-downtime-deploys` — because it is a
thing a person has to read and then decide about, and because an
automatic edge from an action to a belief would be a machine quietly
rewriting its own ground truths.

**Zero tasks is the normal case.** An action you did yourself in a turn
is a record you write and judge in the same turn. Swept after 1d with no
task under it and no outcome on it.

## the defaults, in one table

    level         stale-after   own clock                  ends
    belief        —             —                          (deleted, or rewritten)
    motivation    —             —                          (deleted, or rewritten)
    intention     2h            —                          done / dropped
    goal          1h            last ending underneath      done / abandoned
    action        1d            —                          done / dropped (+ outcome)

The three that have numbers are guesses that should be configurable, and
all of them err quiet. A nudge system is judged by whether its nudges
are still read after a month.
