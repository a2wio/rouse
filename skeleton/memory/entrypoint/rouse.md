# your memory

This directory is yours. It is not a log of what happened — it is where
your work is scheduled, tracked and finished. A file here can come find
you later.

Read this before writing anything into `memory/`.

## the one rule

**A record is a directory containing `<type>.md`.** The type names what
it is; the path names what it belongs to.

    entrypoint/green-deploy-isnt-a-migration/     ← a belief
      belief.md
      keep-the-deploy-trustworthy/                ← a motivation under it
        motivation.md
        2026-03-14-migration-verified/            ← an intention under that
          intention.md
          run-it-on-the-branch/                   ← a task under that
            task.md

Nothing says "my parent is X" — the directory it sits in does, and it
can't disagree with itself. Levels may be skipped: put a task straight
under an intention when there is no goal worth writing.

A record's directory is also where its things live. The script it runs,
the screenshot it's about, the output it produced — they sit beside
`<type>.md` and travel with it.

    entrypoint/                what you mean, and everything under it
      rouse.md                 this file
    inventory/                 everything with no place in the ladder
      notes/                   what you know and want to know next week
      probes.md                commands whose output is the answer
      reminders/<slug>/        promises on a clock
      backlog/<slug>/          worth doing, not committed to

The types: `belief`, `motivation`, `intention`, `goal`, `action`, `task`,
`reminder`, `backlog`.

Every record file is markdown with a small header. Nothing is ever
deleted; a finished record changes its `status:` and stays. Stamps are
`YYYY-MM-DD HH:MM`, local. Intervals are `30m`, `2h`, `1d`.

If the reference CLI is around, `rouse new intention pin-the-runner
--under keep-the-deploy-trustworthy` makes the directory and the header
in one go. If it isn't, `mkdir` and write the file — that is all it does.

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

## intentions — you can't quietly drop one

Anything you said you'd do that has no other trigger — nobody will
message you about it, no job will finish and remind you — goes in a
record, in the same turn you say it:

    entrypoint/…/2026-03-14-migration-verified/intention.md

    ---
    status: open
    opened: 2026-03-14 15:40
    last-moved: 2026-03-14 15:40
    stale-after: 2h
    closes-when: the migration has run once with me watching
    ---
    Why this exists, and what picking it back up looks like.

Put it under the motivation it serves. If there isn't one written down,
put it at the top of `entrypoint/` — an unmoored intention should look
unmoored.

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
**promoted** — the directory moves into the ladder and becomes an
intention — or **dropped out loud**. Never by quietly ceasing to exist.

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
