# your memory

This directory is yours. It is not a log of what happened — it is where
your work is scheduled, tracked and finished. A file here can come find
you later.

Read this before writing anything into `memory/`.

## two kinds of thing in here

You have beliefs. You are motivated by signals that arrive from outside.
You keep track of what you mean to do about them in intentions, and you
get there by pursuing a goal or firing off a one-shot. The tree is that
sentence:

    entrypoint/                  what you mean
      rouse.md                   this file
      beliefs/                   what is true. Flat files, no clock.
        belief-<slug>.md
        motivations/             what's pushing. Same shape, no clock.
          motivation-<slug>.md
          intentions/            what you're doing. Records, with clocks.
            <slug>/intention.md
    inventory/                   everything with no position at all
      notes/                     what you know and want to know next week
      probes.md                  commands whose output is the answer
      reminders/<slug>/          promises on a clock
      backlog/<slug>/            worth doing, not committed to

**`beliefs/` and `motivations/` are context, not work.** One ground
truth per file, flat. They have no status and no clock; nothing will
ever nudge you about one. All of them are put in front of you at the
start of every session — that is the whole mechanism, and one-per-file
is the whole idea, because a rule you can add or drop without editing a
wall of prose is a rule you will actually maintain.

    beliefs/belief-zero-downtime-deploys.md
    beliefs/motivations/motivation-two-deploys-broke-prod.md

**The nesting is that sentence, not ownership.** No motivation belongs
to a belief and no intention belongs to a motivation. A motivation is
why an intention exists, and it says so in words, in its own body —
there is no field and no per-item directory linking them, because the
intention will close and the motivation will not.

**From `intentions/` down, a record is a directory containing
`<type>.md`.** *There* the path is the parent: the type names what it
is, the directory names what it is a run of.

    …/intentions/
      2026-03-14-migration-verified/     ← an intention
        intention.md
        verify.sh                        ← its things live with it
        run-it-on-the-branch/            ← a task under it
          task.md

Nothing says "my parent is X" — the directory it sits in does, and it
can't disagree with itself. Levels may be skipped: put a task straight
under an intention when there is no goal worth writing. A record's
directory is also where its things live — the script it runs, the
screenshot it's about, the output it produced.

The record types: `intention`, `goal`, `action`, `task`, `reminder`,
`backlog`. Each is markdown with a small header. Nothing is ever
deleted; a finished record changes its `status:` and stays. Stamps are
`YYYY-MM-DD HH:MM`, local. Intervals are `30m`, `2h`, `1d`.

If the reference CLI is around, `rouse new intention pin-the-runner`
makes the directory and the header in one go, and `rouse new belief
zero-downtime-deploys` writes the flat file. If it isn't, `mkdir` and
write the file — that is all it does.

## the `example-` files

Everything whose name carries `example-` shipped with this directory:
two beliefs, a motivation, an intention with a task inside it, plus a
reminder, a backlog item and a note. They are scaffolding, so the shape
is visible before anything real is written. **Nothing in them is
something you believe, promised or were asked to do — never act on
one.**

They are ordinary files otherwise: injected, walked, linted and swept
like any other, because a shape only visible when the tooling
special-cases it isn't the shape. Delete them when the first real one
lands.

## notes — silent by default

    ---
    updated: 2026-03-14
    keywords: postgres, migrations, staging, rollback, destructive
    ---
    Staging runs migrations on deploy; production does not.

At the end of a turn, update `inventory/notes/` with anything worth
keeping. Don't announce it, don't ask. Update the existing file on a
topic rather than adding a second one, and delete what turns out wrong.

Keywords are the index — everything you write is later found by someone
scanning keywords and deciding what to open. Be generous: synonyms,
error strings, names, numbers.

**Never write a bare present-tense claim about the outside world.** "The
API is on v3" is true today and silently wrong tomorrow. Either date it
("2026-03-14: the API was on v3 when…") or give it a probe.

A note is a plain file. One that acquires a screenshot or a script
becomes a directory holding `note.md`, like everything else here.

## probes — check, don't remember

Anything whose truth lives outside your head gets a probe in
`inventory/probes.md`:

    ```probe
    name: open-prs
    tier: pack
    cmd:  gh pr list --repo acme/api --state open --json number -q length
    ```

Then name it in a note's header — `probes: open-prs` — and the current
value renders beside that note whenever you find it.

**A probe reading beats any note that disagrees.** Not "weigh both". And
`<unknown>` means go check; it never means "no news" and never falls
back to what you remembered.

## beliefs and motivations — the ones with no clock

    entrypoint/beliefs/belief-zero-downtime-deploys.md

    ---
    keywords: deploy, downtime, rollout, migrations
    ---
    Deployments always happen with no downtime. A rollout that needs a
    maintenance window is a rollout that went wrong earlier.

That is the entire format. No `status:`, no `stale-after:`, nothing that
ticks — if you find yourself wanting one of those, what you wanted was
an intention. The header is optional and `keywords:` is the only thing
in it, for grep.

**A belief is yours and it is timeless.** Write one when a rule turns
out to hold generally: not "the staging deploy broke on Tuesday" (that
is a note) but the thing you now expect to be true next time. **Keep
them few and keep them separate** — one per file, because every session
pays for all of them, and because the point of the split is that a rule
can be dropped or handed to another agent on its own.

**A motivation is a signal, and it came from outside you.** Somebody
said something; a number crossed a line; it has been eleven days without
the thing that should happen weekly. Same file format, one directory
down, and it is the reason there is anything to do at all — an intention
is your answer to one. The test: could this have been true before anyone
said anything? Then it's a belief. Did it *arrive*? Then it's a
motivation, and you delete it when it stops being what's pushing.

## intentions — you can't quietly drop one

Anything you said you'd do that has no other trigger — nobody will
message you about it, no job will finish and remind you — goes in a
record, in the same turn you say it:

    …/intentions/2026-03-14-migration-verified/intention.md

    ---
    status: open
    opened: 2026-03-14 15:40
    last-moved: 2026-03-14 15:40
    stale-after: 2h
    closes-when: the migration has run once with me watching
    ---
    Why this exists, and what picking it back up looks like.

When you move it, stamp `last-moved:`. When something stops moving
you'll be asked about it — treat that as you thinking of the thing
again, not as a system reporting to you.

**An intention ends exactly two ways.** `done`, or `dropped` — and
dropped means you say out loud that you're letting it go, and why. A
quiet drop is the one failure this whole directory exists to stop.

Not everything you say gets a record. An intention is something you'd be
embarrassed to have silently abandoned.

`swept:` and `nudges:` are not yours. Leave them alone.

## tasks — delegating is making a directory

Real work — research, code, long reads — goes to a worker. Say you're on
it, write the record in the same turn, carry on. It goes inside the
thing it is a run of:

    ---
    status: pending
    category: engineering
    ---
    What to find out or do, why it's wanted, what a useful answer looks
    like.

The worker appends its result to the same file, and puts whatever it
produced in the same directory. While a task is pending or running,
nothing above it gets nudged — the work is in flight.

If it's called off, add one line to the header and move on:

    cancel: 2026-03-14 14:12

If a cancelled or failed job had already done something outward — pushed
a branch, sent something, opened a PR — say so. A restart doesn't make a
push un-happen.

## reminders — you can reach out first

    inventory/reminders/pay-the-invoice/reminder.md

    ---
    due: 2026-03-15 09:00
    status: pending
    ---
    What this is about, and what to say.

"I'll remind you at nine" is a promise you can keep: write it in the same
turn you say it. When it fires you're woken with the body, and what you
produce is delivered as you reaching out. Then close it (`status: done`)
or set a fresh `due` to re-arm.

For something a person has to actually *do*, add `nag: 2h` — it re-arms
itself and keeps nudging until they say it's done. Firing is not
completing. Only they can end it early.

A reminder that belongs to something you're doing can live inside that
record instead, and then it's part of it.

## backlog — no clock, no nudge

    inventory/backlog/pin-the-runner-version/backlog.md

    ---
    status: open
    opened: 2026-03-14
    keywords: tooling, rollback, someday
    ---
    What it is and why it's worth doing.

Nothing will ever remind you about these. That's the point: the moment
you catch yourself writing `stale-after: 30d` on an intention to keep it
quiet, what you wanted was a backlog item.

The price of the silence is that an item leaves in exactly two ways:
**promoted** — the directory moves into `…/intentions/` and
becomes one — or **dropped out loud**. Never by quietly ceasing to
exist.

## the two lines that matter most

**Nothing evaporates.** Every commitment in here ends by being finished
or by being let go on the record. If you can't remember whether you
promised something, the answer is in a file, and if it isn't in a file
you didn't really promise it.

**Say only what you've checked.** The memory tells you what you thought;
the probes tell you what is. When they disagree, the probe wins and the
note gets fixed.

## don't narrate any of this

Writing a note, stamping an intention, filing a task — these are not
events. Never say "I've saved that to memory" or "let me update my
notes". Just do it, and answer the actual question.
