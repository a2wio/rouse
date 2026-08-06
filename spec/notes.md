# notes — durable memory

`memory/notes/` is the part that looks like every other memory system:
what the agent learned and wants to still know next week. The
conventions around it are what make the rest work.

    ---
    updated: 2026-03-14
    keywords: postgres, migrations, staging, rollback
    probes: staging-migration-state
    origin: owner
    origin-turn: 20260314-091200-a1b2c3
    ---

    Staging runs migrations on deploy; production does not. A rollback
    on staging is `make db-rollback`, which is destructive and takes the
    whole schema back one step, not one table.

- `updated` — the day the content last changed. Yours to keep true.
- `keywords` — comma-separated, generous. See below.
- `probes` — optional; names from `memory/probes.md`. See `probes.md`.
- `origin`, `origin-turn` — machine fields. See `provenance.md`. Never
  type these.

## keywords are the index

There is no embedding store here and there does not need to be. The
retrieval path is: the pack lists recently-touched files in full, and
collapses everything older to *name + age + keywords*. The agent reads
that list and decides what to open.

So keywords are not tags for tidiness, they are the only handle future
sessions have on a file they can't afford to open. Write the words
someone would grep for, including the ones not in the text: synonyms,
error strings, the name of the person who asked, the ticket number.
Twenty keywords on a file is normal and costs one line.

    keywords: postgres, migrations, staging, rollback, make db-rollback,
              destructive, schema, deploy

## grouping

Notes go in subdirectories by *kind of thing*, not by project:

    notes/people/      who you work with, what they want, how they talk
    notes/projects/    things being built
    notes/craft/       how you work — conventions, tooling, hard-won limits
    notes/design/      design documents, decisions and their reasons

Four is a suggestion. The rule that matters is that a new note lands in
a group that already exists, and a note that fits none of them stays
flat in `notes/` until enough of its kind pile up to earn a directory.
Directories created in advance stay empty; directories created on
demand describe what you actually think about.

## the discipline

**Update, don't accumulate.** One topic, one file. A second note on the
same subject is how a memory system starts contradicting itself. When
something turns out to be wrong, edit the sentence — or delete the file
— rather than appending a correction under it. A file that carries both
the old claim and the new one will eventually be read one line too
early.

**Never a bare present-tense sentence about the outside world.**
"The staging cluster runs 1.29" is true the day you write it and
silently wrong the day after. Anything with a source of truth outside
the agent's head gets one of two treatments: a `probes:` line, so the
current value renders beside the file, or a dated entry, so it reads as
history instead of as fact.

    ✗  the staging cluster runs 1.29
    ✓  2026-03-14: staging was on 1.29 when the upgrade PR opened
    ✓  probes: staging-k8s-version

**Silent by default.** Writing memory is not an event worth narrating.
The agent should update notes at the end of a turn the way a person
closes a tab — without announcing it, and without asking permission.
