# rouse

Memory with a clock.

Nearly every memory system for agents is recall: the agent asks, the
store answers, and if the agent never asks then the memory never
happened. Rouse is recall plus a clock. A file in here can come find the
model — because it came due, or because it stopped moving and somebody
was promised it wouldn't.

    recall   agent asks  -> memory answers
    rouse    memory asks -> agent answers

The second half is the whole product. It is also why this is a set of
conventions and not a database: a record that has to wake something
needs a lifecycle, and a lifecycle is easier to see in a file you can
open than in a row you have to query.

The third thing in here is smaller and stops most of the damage: some
facts should never be remembered at all. A probe is a named command
whose output is the answer, and its reading beats any note that
disagrees — because a memory system's characteristic failure isn't
forgetting, it's remembering confidently.

## the memory is the executive, not the archive

The usual framing is that memory sits beside the work — the agent does
things, and afterwards writes down what happened. Here the files *are*
the work.

A task file is how a job gets scheduled. An intention file is how
follow-through gets enforced. A reminder is how the agent keeps a
promise it made out loud. Delegation is a file appearing; cancellation
is a line added to it. Nothing is scheduled anywhere else, so nothing
can be scheduled and forgotten.

What holds that together is that **every level has a different contract
with time**:

    belief       no clock. Nothing ever nudges you about one.
    motivation   never reaches done. Stale when nothing is open under it.
    intention    nudged when it stops moving. Ends done, or dropped out loud.
    goal         a loop. Stale when the last outcome landed and no next move was made.
    action       one shot. Carries the outcome — whether the thing became true.
    task         a run. pending -> running -> done/failed/cancelled.
    reminder     a clock and a body. Fires, then closes or re-arms.
    backlog      no clock at all, and may not evaporate.

Pick the level by the contract you want, not by how big the thing feels.
The moment you write `stale-after: 30d` on an intention to keep the
nudges quiet, the thing you wanted was a backlog item.

## two layers

**Conventions** — the file formats and the rules above. Markdown with
frontmatter, one thing per file, flat directories, containment by a
`parent:` field rather than by path. These need no software at all. An
agent that has read the instruction file can follow them with nothing
but read and write.

**The clock** — one sweeper that reads the headers, decides what is due,
and delivers a wake. This is the part that needs a process, and it is
deliberately the second half, because adoption dies when step one is
"run my daemon".

## the install floor

Three tiers. Each one is real on its own; you never have to reach the
last.

**Tier 0 — copy a directory.** `memory/` plus the instruction file, and
one line in whatever your agent already reads:

    Your memory lives in `memory/`. Read `memory/rouse.md` before using it.

Zero processes. You get recall, the lifecycle contracts, and an agent
that knows a dropped intention is a failure. That is most of the value
and it costs one commit.

**Tier 1 — run one command at session start.** `rouse pack` prints a
context block: what is overdue, what moved recently, what the probes say
right now. Feed it to the model however your agent takes context.

    python3 -m rouse pack >> .agent/context.md

Still zero daemons, and you have a clock — sampled at session
boundaries. Overdue things surface at the top of every session instead
of never.

**Tier 2 — run the sweeper.** `rouse sweep` ticks every minute and
delivers a wake the moment something comes due, to a file, a command, or
a webhook. Now the clock runs *between* sessions: the model can be woken
by nothing having happened.

What tier 2 buys over tier 1 is the thing tier 1 cannot fake: a nudge
that arrives when nobody has opened a session. Worth a lot for an agent
that runs unattended, worth nothing for one that only exists while
you're typing at it — which is why it isn't the floor.

## agent-agnostic on purpose

Rouse assumes markdown files and a shell. It does not assume a chat
platform, a model vendor, or a runtime. Two seams do the wiring, and
both are text:

    injection   `rouse pack` -> whatever your agent reads at session start
                (CLAUDE.md, AGENTS.md, a system prompt, a --context flag)
    wake sink   `rouse sweep` -> a nudge file, a command, or an HTTP POST

Claude Code, Codex, Cursor, pi, a cron job with `curl` — if it can read
a file at startup and be started by something, it can be roused.
`design/clock.md` has the seams in detail, including what a sink owes
you (at-most-once delivery, and a wake that cannot be silently lost).

## layout

    spec/            the conventions, one file per idea. The product.
      notes.md         durable memory: frontmatter, keywords, grouping
      probes.md        named commands whose output beats any note
      provenance.md    where a file came from, stamped by machinery
      ladder.md        beliefs -> motivations -> intentions -> goals -> actions
      runs.md          tasks and reminders: delegation and promises as files
      backlog.md       the level with no clock, and its two exits
      pack.md          what gets injected at session start
    skeleton/        the drop-in: `memory/` and the instruction file
    design/clock.md  the sweeper, the two seams, the delivery contract
    rouse/           a reference implementation. stdlib python, no deps.
    tests/           what proves the reference implementation works

There is no install step and no package on PyPI. `rouse/` is a plain
python package — vendor the directory, or run it out of a checkout.
Every `rouse …` in this README means `python3 -m rouse …`.

## start here

Read `spec/README.md`. It is short and it is the actual product; the
code exists to prove the conventions are mechanical, not to be the
thing you depend on.

To try it:

    python3 -m rouse init ./scratch      # drop the skeleton
    python3 -m rouse pack --memory ./scratch/memory
    python3 -m rouse check --memory ./scratch/memory

Rouse was extracted from a personal agent harness that has been running
against these conventions daily. The parts that are specific to that
agent — its voice, its moods, its channels — are not here and are not
coming; what is here is the part that turned out to be about memory.
