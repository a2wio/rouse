# your memory

This directory is yours. It is not a log of what happened — it is where
your work is scheduled, tracked and finished. A file here can come find
you later.

Read this before writing anything into `memory/`.

## the shape

    notes/        what you know and want to still know next week
    probes.md     commands whose output is the answer
    intentions/   what you mean to make true
    tasks/        work handed to a background worker
    reminders/    promises on a clock
    backlog/      worth doing, not committed to

Every file is markdown with a small header. One thing per file. Flat
directories — a record names its parent in a field, never by living
inside it. Nothing is ever deleted; a finished record changes its
`status:` and stays.

Stamps are `YYYY-MM-DD HH:MM`, local. Intervals are `30m`, `2h`, `1d`.

## notes — silent by default

    ---
    updated: 2026-03-14
    keywords: postgres, migrations, staging, rollback, destructive
    ---
    Staging runs migrations on deploy; production does not.

At the end of a turn, update `notes/` with anything worth keeping. Don't
announce it, don't ask. Update the existing file on a topic rather than
adding a second one, and delete what turns out to be wrong.

Keywords are the index — everything you write is later found by someone
scanning keywords and deciding what to open. Be generous: synonyms,
error strings, names, numbers.

**Never write a bare present-tense claim about the outside world.** "The
API is on v3" is true today and silently wrong tomorrow. Either date it
("2026-03-14: the API was on v3 when…") or give it a probe.

## probes — check, don't remember

Anything whose truth lives outside your head gets a probe in
`probes.md`:

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
file, in the same turn you say it:

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

Not everything you say gets a file. An intention is something you'd be
embarrassed to have silently abandoned.

`swept:` and `nudges:` are not yours. Leave them alone.

## tasks — delegating is writing a file

Real work — research, code, long reads — goes to a worker. Say you're on
it, write the file in the same turn, carry on:

    ---
    status: pending
    category: engineering
    intention: 2026-03-14-migration-verified
    ---
    What to find out or do, why it's wanted, what a useful answer looks
    like.

The worker appends its result to the same file. While a task is pending
or running, nothing above it gets nudged — the work is in flight.

If it's called off, add one line to the header and move on:

    cancel: 2026-03-14 14:12

If a cancelled or failed job had already done something outward — pushed
a branch, sent something, opened a PR — say so. A restart doesn't make a
push un-happen.

## reminders — you can reach out first

    ---
    due: 2026-03-15 09:00
    status: pending
    ---
    What this is about, and what to say.

"I'll remind you at nine" is a promise you can keep: write the file in
the same turn you say it. When it fires you're woken with the body, and
what you produce is delivered as you reaching out. Then close it
(`status: done`) or set a fresh `due` to re-arm.

For something a person has to actually *do*, add `nag: 2h` — it re-arms
itself and keeps nudging until they say it's done. Firing is not
completing. Only they can end it early.

## backlog — no clock, no nudge

    ---
    status: open
    opened: 2026-03-14
    keywords: tooling, rollback, someday
    ---
    What it is and why it's worth doing.

Nothing will ever remind you about these. That's the point: the moment
you catch yourself writing `stale-after: 30d` on an intention to keep it
quiet, what you wanted was a backlog file.

The price of the silence is that an item leaves in exactly two ways:
**promoted** to an intention, or **dropped out loud**. Never by quietly
ceasing to exist.

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
