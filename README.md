# rouse

Memory with a clock.

Most agent memory is recall: the agent asks, the store answers, and if it
never asks, the memory never happened. Rouse adds the other direction. A
file in here can come find the model, because it came due or because it
stopped moving and somebody was promised it wouldn't.

    recall   agent asks  -> memory answers
    rouse    memory asks -> agent answers

## the shape

An agent **has beliefs** — clean code means this, deploys work like
that. It **is motivated** by signals from outside: somebody said
something, two deploys broke prod, it's been eleven days without a
restore drill. It keeps track of what it means to do about them in
**intentions**, and it gets there, or doesn't, by pursuing a **goal** or
firing off a one-shot **action**.

The tree is that sentence, read downward:

    memory/
    ├── entrypoint/
    │   ├── rouse.md                   the instruction file — point your agent here
    │   └── beliefs/                   internal, timeless. Injected every session.
    │       ├── belief-zero-downtime-deploys.md
    │       ├── belief-plan-before-code.md
    │       └── motivations/           external signals. Same shape, same injection.
    │           ├── motivation-two-deploys-broke-prod.md
    │           └── intentions/        what you're doing. Records, with clocks.
    │               └── 2026-03-14-migration-verified/
    │                   ├── intention.md
    │                   ├── verify.sh
    │                   └── run-it-on-the-branch/
    │                       └── task.md
    └── inventory/                     everything with no position at all
        ├── notes/                     what you want to still know next week
        ├── probes.md                  commands whose output is the answer
        ├── reminders/<slug>/reminder.md
        └── backlog/<slug>/backlog.md

**Beliefs and motivations are a system prompt cut into modules.** One
ground truth per file, no status, no clock, and all of them put in front
of the model at the start of every session. One per file is the point,
because a rule you can add, drop or hand to another agent on its own is
a rule you will keep maintaining. The difference between the two is
where it came from: a belief is the agent's, and holds regardless of the
week; a motivation *arrived*, and gets deleted when the signal stops
mattering.

**Those directories nest because the sentence does — not because the
files contain each other.** No motivation belongs to a belief and no
intention belongs to a motivation; there is no field for it and no
per-item nesting, and an intention four directories deep still has
nothing above it.

**From `intentions/` down, a record is a directory containing
`<type>.md`.** *There* the path really is the parent: the type names the
level, the directory names what it is a run of. These are the ones with
a contract about time — an intention is nudged when it stops moving, and
ends `done` or `dropped` out loud, never by evaporating. A backlog item
is never nudged at all, and pays for that by having no quiet exit
either. Pick by the contract you want, not by how big the thing feels.

Probes are the smaller third piece and they stop most of the damage: a
named command whose output *is* the answer, whose reading beats any note
that disagrees. Memory systems are assumed to fail by forgetting. They
fail by remembering confidently.

## install

Three tiers. Each one is real on its own; you never have to reach the
last.

**Tier 0 — copy `skeleton/memory/` in.** Then one line in whatever your
agent already reads (CLAUDE.md, AGENTS.md, a system prompt):

    Your memory lives in `memory/`. Read `memory/entrypoint/rouse.md`
    before using it.

Zero processes. You get the conventions and an agent that treats a
dropped intention as a failure.

What you copy in isn't empty: two example beliefs, a motivation, an
intention with a task inside it, plus an example reminder, backlog item
and note, every slug prefixed `example-`. So `rouse tree` prints a real
tree on the first run. Nothing special-cases them; delete them when your
first real one lands.

**Tier 1 — `rouse pack` at session start.** It prints one block: your
beliefs and motivations in full, what is overdue, what moved recently,
what the probes say this second. Still no daemon, but now there is a
clock, sampled at session boundaries.

    python3 -m rouse pack >> .agent/context.md

**Tier 2 — `rouse sweep`.** Ticks every minute and delivers a wake the
moment something comes due, to a file, a command, or a webhook. Only this
tier can nudge you when nobody has opened a session, which is the whole
reason to run a daemon and the reason it isn't the floor.

Both seams are text. The pack goes into whatever your agent reads; the
wake comes out to a nudge file, a command, or an HTTP POST. Claude Code,
Codex, Cursor, a cron job with `curl`: if it can read a file at startup
and be started by something, it can be roused.

## the repo

    spec/       the conventions, one file per idea. This is the product.
    skeleton/   the drop-in memory/
    design/     the clock — the two seams and the delivery contract
    rouse/      a reference implementation. stdlib python, no deps.

There is no PyPI package and no install step. `rouse/` is a plain python
package: vendor the directory, or run it out of a checkout. Every
`rouse …` above means `python3 -m rouse …`.

    python3 -m rouse init ./scratch
    python3 -m rouse --memory ./scratch/memory tree
    python3 -m rouse --memory ./scratch/memory check

Read `spec/README.md` next. It is short, and it is the actual product;
the code is there to prove the conventions are mechanical, not to be the
thing you depend on.
