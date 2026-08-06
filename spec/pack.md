# the pack — what the agent is handed at session start

A memory directory is useless if the model doesn't know what is in it.
The pack is the one block of text injected at the top of a session: not
the memory, but *an index of the memory plus everything that is true
right now*.

Keep it small. It is paid for on every single turn, so the budget is a
design constraint and not an afterthought — target a couple of thousand
tokens, and spend them on pointers rather than content.

    now: Saturday 2026-03-14 09:12 UTC

    measured just now — these beat any memory file that disagrees,
    and `<unknown>` means go check, not "no news":
      open-prs: 3
      deploy-state: green (2026-03-14 08:40)
      jobs-in-flight: 1
      disk-free: <unknown>

    due: 2 record(s) want you
      intention/2026-03-14-migration-verified — 4h ago
        at: entrypoint/liability/keep-the-deploy-trustworthy/2026-03-14-migration-verified
        closes-when: the staging migration has run once with me watching
      action/2026-03-12-ask-about-the-rollback — 2d ago
        at: entrypoint/liability/keep-the-deploy-trustworthy/ask-about-it

    ladder: 3 beliefs · 2 motivations · 4 intentions · 1 goal

    fresh memory (read what's relevant):
      inventory/notes/projects/api.md (2h ago — postgres, migrations,
        staging, rollback) [owner]
      inventory/notes/craft/deploys.md (yesterday — pipeline, green,
        skipped, evidence) [agent]

    older memory (scan the keywords, open what matters):
      inventory/notes/people/ops-team.md (9d ago — ops, escalation,
        pager, on-call, who-to-ask) [owner]
      ... 40 more

    not listed: 212 closed records older than 12h. They are on disk,
    unmoved — grep memory/ finds any of them by name or content.

## the five things it must contain

**1. Now.** The date and time, spelled out, with the day of the week.
Models are confidently wrong about what day it is, and every relative
age below depends on this line.

**2. Probe readings.** Fresh, measured this second, with the explicit
instruction that they outrank any file. `<unknown>` renders as
`<unknown>`; see `probes.md`.

**3. What is due.** Anything the clock would wake about, with the path
to it — nesting means the name alone no longer says where to look. In
tier 1 — no daemon — this block *is* the clock: overdue records surface
at the top of every session rather than never.

**4. The memory index.** Recently-touched files listed with their
keywords; everything older collapsed to name, age, keywords, origin.
The model chooses what to open. This is retrieval by table of contents,
and it works better than it should because the keywords were written by
the same reader that later needs them.

**5. What is unlisted.** The count of what was collapsed out, and how to
reach it. Never let the pack imply it is complete — an agent that thinks
the pack is the memory will never grep, and grep is most of the
retrieval.

## ages, not timestamps

Every age is relative and computed at render: `2h ago`, `yesterday`,
`9d ago`. A raw timestamp makes the model do arithmetic it gets wrong,
and — worse — a file dated in the header reads as current no matter how
old it is. "Something from yesterday is something from yesterday, not
something that just happened" is the whole reason the ages are there.

## ordering

Volatile first, durable last: now, probes, due, then the index. If the
context window forces truncation it will eat the tail, and the tail
should be the part that can be re-read on demand.

## what the pack must never do

- **Never substitute a remembered value for a failed probe.** Covered in
  `probes.md`; it is the one rule with no exceptions.
- **Never present the index as the memory.** See (5).
- **Never dump bodies.** A pack that includes note contents stops being
  an index and becomes a second, worse copy of the memory that goes
  stale inside the context window.
- **Never omit provenance.** `[untrusted]` and `[unknown]` are part of
  the line, not a detail.
