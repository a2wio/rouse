# runs — tasks and reminders

The ladder is intent. These two are the things that actually execute:
a task is work handed to somebody else, a reminder is a promise on a
clock. Both are files, and that is the point — **delegation and
follow-through have no existence outside the filesystem**, so neither
can be scheduled and forgotten.

---

## tasks — `memory/tasks/`

A background job. The conversational side of an agent writes one and
carries on; a worker picks it up and appends its result to the same
file.

    ---
    status: pending           pending | running | done | failed | cancelled
    category: engineering     a label for humans, not a router
    model: default            optional — who does the work
    reasoning: medium         optional — low | medium | high
    intention: 2026-03-14-migration-verified
    action: 2026-03-14-run-it-on-the-branch
    repo: acme/api            optional — whatever your runner needs
    ---
    What to find out or do, why it's wanted, and what a useful answer
    looks like.

The lifecycle is the contract:

    pending     written, nothing has picked it up
    running     a worker has it. Stamped by the runner, not the model.
    done        finished, result appended below the header
    failed      it ran and could not
    cancelled   stopped on purpose. See below.

**The result goes in the file, not just in a reply.** A job whose output
exists only in a chat window is a job the next session cannot learn
from.

### why a task file is a scheduler

Three properties fall out of it being a file and not a queue entry:

- **Restartable.** A crashed runner leaves `running` on disk. Whatever
  comes back can see the job, see that nothing is holding it, and decide.
- **Inspectable.** `grep -l 'status: pending' memory/tasks/*.md` is the
  queue depth, and it is also a probe.
- **Attributable.** `intention:` and `action:` link the run to the thing
  it is a run *of*, which is what makes the sweeper stay quiet — see
  below — and what makes an outcome judgeable later.

### movement, upward

While a task is `pending` or `running`, **nothing above it in the ladder
is nudged.** The work is in flight; a nudge would be noise. When it
finishes, the levels above it become due again — which is exactly the
right moment to ask the only question that matters: *did that close it?*

That is the whole integration between the two halves of this spec. A
task naming no `intention:` behaves normally; it just doesn't count as
movement for anything.

### cancelling

One line in the header, written the moment the operator changes their
mind:

    cancel: 2026-03-14 14:12

The runner sees it, stops the worker (after any tool call in flight
finishes, so nothing is left half-written), and the file records
`status: cancelled`. Nothing is sent — a cancel needs no announcement,
it was asked for.

The one thing a cancel must not do quietly is hide side effects. If the
dead job had already pushed a branch, sent an email, or opened a PR, the
operator has to hear about it, because a restart never makes a push
un-happen. **A cancelled job's outward actions are part of its result.**

### checkpoints

A long job can append a line to its own file mid-run:

    checkpoint: opened PR #51

Which reaches whatever is watching as progress, distinct from a result.
The bar for writing one is high on purpose: something the waiting side
would want to know *before* the job finishes — a push, a block, or the
job turning out to be a different job than the brief said. Ordinary
progress is not a checkpoint; no line is the default and costs nothing.

---

## reminders — `memory/reminders/`

A clock and a body. This is how an agent reaches out first.

    ---
    due: 2026-03-15 09:00
    status: pending           pending | fired | done | expired
    channel: default          optional — where to deliver
    intention: 2026-03-14-migration-verified
    ---
    What this is about, what to say, tone notes for future-you.

- `due` is local time, `YYYY-MM-DD HH:MM`; date alone means midnight.
- The clock checks every minute. When one is due, the agent is woken
  with the body and whatever it produces is delivered as *the agent
  reaching out*, not as a reply.
- After firing, the file sits at `fired`. Set it `done` when handled, or
  set a fresh `due` + `pending` to re-arm. That is also how recurring
  things work.

So "I'll remind you at nine" is a promise the agent can make and keep —
by writing the file in the same turn it says the words.

### nagging — for things a human has to do

A single polite ping and a quiet close is exactly the failure this
prevents. Add `nag:` and the reminder re-arms itself:

    ---
    due: 2026-03-15 19:30
    status: pending
    nag: 2h
    backoff: 2                optional — multiplier, or `fixed`
    max-fires: 10             optional — ceiling
    expires: 2026-03-20       optional — the other ceiling
    ---
    What they have to do, and tone notes for future-you.

- Presence of `nag:` is what makes it nagging. The value is the re-nudge
  interval.
- **The loop re-arms it, not the model.** Fresh `due`, bumped `fires:`,
  `set:` backfilled with the original due. `fires:` and `set:` are
  machine fields.
- **Firing is not completing.** A nudge that went out leaves the file
  open no matter what the agent said while sending it. `status: done` is
  written by the agent in a normal turn, when the human says it's done.
  That is the only way one ends early.
- The interval doubles each time by default, capped at a day.
- Ceilings exist so a nag can't outlive its usefulness: after
  `max-fires:` (default 10) or past `expires:`, one last wake says it is
  being dropped — **say so** — and the file closes as `expired`.
- Each wake should carry the nudge number and when it was first set.
  That is the escalation dial: casual, then blunt, then openly annoying.
  The wording is the agent's; the loop only counts.

### stuck reminders

A nagging file found resting at `fired` — a crash mid-fire, a dead
daemon — is stuck. The loop must notice and flip it back to `pending`,
so the nudge goes out late instead of never. Late is recoverable; never
is the thing being prevented.
