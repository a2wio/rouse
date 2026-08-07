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
    ├── persona.md                     how it talks. Optional — see below.
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

**`persona.md` is the same kind of file one layer higher, and most trees
haven't got one.** It says how the agent talks — register, length, what it
never sounds like — and it sits above `entrypoint/` because it is what
everything below is read *through*: the same belief comes out as a
different sentence in a different voice. Optional is a rule, not a
shrug. An agent that reads diffs in CI gets its register from whatever
wraps it and should skip the file; anything a person actually talks to
wants one, and for those it is the highest-value file in the tree, because
it is the one that is wrong in every single reply when it is wrong. Absent,
it prints nothing and warns about nothing. `rouse new persona` starts one,
and the skeleton deliberately ships no example — the layer is found by
path, so a placeholder would be an unmarked personality injected into
every session. See `spec/persona.md`.

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

## where the tree lives

A project's tree is `./memory`. An agent with no project to stand in has
`~/.rouse`, and that path is the convention: any agent may assume it,
and pointing a second tool at an existing memory is a matter of not
overriding it. Rouse looks in this order and stops at the first answer:

    --memory <dir>     explicit, wins
    $ROUSE_HOME        this agent's tree, wherever it keeps it
    ./memory           the project you're standing in
    ~/.rouse           the global one

    python3 -m rouse init            # ./memory
    python3 -m rouse init --global   # ~/.rouse

Both give the tree its own git repository if it hasn't got one, because
what an agent changed its mind about is a diff.

**One tree per agent, always.** Two agents sharing one read each other's
beliefs out of the same pack and get nudged about work neither of them
took on. `ROUSE_HOME=~/.rouse-reviewer` is how the second one gets its
own.

## install

    pip install git+https://github.com/a2wio/rouse
    cd your-project
    rouse init --wire

That is the whole of it. `init` lays `memory/` down; `--wire` appends a
short block to the `CLAUDE.md` or `AGENTS.md` you already have, telling
the agent to run `rouse pack` at session start and to read
`memory/entrypoint/rouse.md` before it writes anything. Both files if you
have both. Nothing you didn't already have gets created — with neither of
them it prints the block and says where to put it — and a second run
appends nothing, so a reinstall is safe.

**Or hand it to the agent.** Send it this line and it does the three
above:

    install rouse for this project: https://a2w.io/rouse/install.txt

Then open a session and ask it what it is carrying. Nothing else changes
about how you work: the agent runs one command at the start and writes
files instead of forgetting.

## how much of it you run

Three tiers. Each one is real on its own; you never have to reach the
last.

**Tier 0 — copy `rouse/skeleton/memory/` in.** Then one line in whatever
your agent already reads (CLAUDE.md, AGENTS.md, a system prompt):

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
persona if you wrote one, your beliefs and motivations in full, what is
overdue, what moved recently, what the probes say this second. Still no
daemon, but now there is a clock, sampled at session boundaries.

    rouse pack >> .agent/context.md            # ./memory or ~/.rouse
    ROUSE_HOME=~/.rouse-oncall rouse pack      # a named agent's
    rouse pack --query "$PROMPT"               # thin the signals

`--query` is optional and only ever touches the motivations: the ones it
doesn't match shrink to a line, and the persona and every belief still go
in whole. A rule you didn't retrieve still binds; a signal only matters
when it's about what you're doing.

**Tier 2 — `rouse sweep`.** Ticks every minute and delivers a wake the
moment something comes due, to a file, a command, or a webhook. Only this
tier can nudge you when nobody has opened a session, which is the whole
reason to run a daemon and the reason it isn't the floor.

Both seams are text. The pack goes into whatever your agent reads; the
wake comes out to a nudge file, a command, or an HTTP POST. Claude Code,
Codex, Cursor, a cron job with `curl`: if it can read a file at startup
and be started by something, it can be roused.

## the repo

    spec/            the conventions, one file per idea. This is the product.
    design/          the clock — the two seams and the delivery contract
    rouse/           a reference implementation. stdlib python, no deps.
    rouse/skeleton/  the drop-in memory/, shipped inside the package

`pip install` puts `rouse` on the path and nothing else on your machine —
there are no dependencies, and there won't be any. You can also skip the
install entirely: `rouse/` is a plain python package, so vendor the
directory or run it out of a checkout, and every `rouse …` above becomes
`python3 -m rouse …`.

    python3 -m rouse init ./scratch
    python3 -m rouse --memory ./scratch/memory tree
    python3 -m rouse --memory ./scratch/memory check

Read `spec/README.md` next. It is short, and it is the actual product;
the code is there to prove the conventions are mechanical, not to be the
thing you depend on.
