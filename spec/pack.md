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
      intention/migration-verified — 4h ago
        at: entrypoint/beliefs/motivations/intentions/migration-verified
        closes-when: the staging migration has run once with me watching
      action/ask-about-the-rollback — 2d ago
        at: entrypoint/beliefs/motivations/intentions/migration-verified/ask-about-it

    persona — how you talk, not what you know — not news:
      You are a front-end developer talking to a client who is not
      technical. Short answers. Say what you'd do, not the four options.

    beliefs — ground truth, always true, not news:
      [zero-downtime-deploys]
      Deployments always happen with no downtime. A rollout that needs a
      maintenance window is a rollout that went wrong earlier.

      [plan-before-code]
      Writing code starts in plan mode. Say what the change is, which
      files it touches, and how it will be checked — then write it.

    motivations — signals that arrived — standing context, not news:
      [two-deploys-broke-prod]
      Two deploys broke prod this month and the operator said they no
      longer trust a green check on this pipeline.

    ladder: 4 intentions · 1 goal · 2 tasks — the open ones are under
      entrypoint/beliefs/motivations/intentions/

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

## the six things it must contain

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

**4. The context layers, in full.** `persona.md` if the tree has one,
then every file in `beliefs/` and `motivations/`, body and all — one
non-recursive pass each of the latter two, since `motivations/` sits
inside `beliefs/` and a recursive read would print it twice. This is the
one place the pack carries content rather than pointers, and the reason is
that these files have no clock and no lifecycle: there is no fresher
version of one to go and read, so a copy in the window cannot drift from
the file. They are the instructions rather than memory being quoted, and
cutting them into modules is what lets this block be assembled from files
instead of maintained as prose.

**Inside the block the order is persona, beliefs, motivations** — not by
importance but because that is the order it reads in: who is talking, what
they hold true, what reached them this week. **An absent persona prints
nothing at all** — no header, no empty block, no invented default. Most
trees haven't got one and that is not a gap; see `persona.md`.

Label them all as standing truth rather than news. A model handed a
paragraph at the top of a session will otherwise treat it as something
that just came in and reply to it.

The one exception is the query, below — and it never touches a belief or
the persona.

**5. The memory index.** Recently-touched files listed with their
keywords; everything older collapsed to name, age, keywords, origin.
The model chooses what to open. This is retrieval by table of contents,
and it works better than it should because the keywords were written by
the same reader that later needs them.

**6. What is unlisted.** The count of what was collapsed out, and how to
reach it. Never let the pack imply it is complete — an agent that thinks
the pack is the memory will never grep, and grep is most of the
retrieval.

**Every count in the pack names where the counted things are.** That
applies to the `ladder:` line as much as to the notes index, and it was
learned the hard way: counts on their own read as a pointer, and when
nothing is due there is no other route to a record, so a model told
`1 intention · 1 task` and given no path goes looking for a file called
`ladder`. The roots on the line cost eleven words and are read off the
records rather than off each level's default home — a reminder can sit
inside the intention it belongs to, and then the inventory is the wrong
place to send anybody.

## the query — the rules always, the signals when they're about this

A caller that knows what the turn is about may say so:

    rouse pack --query "the staging migration keeps failing on deploy"

**A belief is never affected by it, and neither is the persona.** Not
thinned, not collapsed, not reordered. The asymmetry is the whole point and it is one sentence: **a
rule you didn't retrieve still binds, and a signal only matters when
it's relevant.** An agent that fails to recall "writing code starts in
plan mode" does not thereby stop being expected to plan — the rule was
never a lookup, it was the instructions. Gating a belief on a keyword
match is how you build an agent that follows its own conventions
whenever they happen to be mentioned. The persona is the same argument
one step further: an agent asked about invoices is not thereby a
different agent, and a voice that arrives only on matching turns is a
voice nobody would call consistent.

A motivation is the other case exactly. It is a signal that arrived from
outside, it is about something, and something is what it is about.

**With a query, a motivation whose keywords the query touches goes in
whole; the rest collapse to one line each** — slug and age, nothing
else:

    motivations — signals that arrived — standing context, not news:
      [two-deploys-broke-prod]
      Two deploys broke prod this month and the operator said they no
      longer trust a green check on this pipeline.

      not matched by this turn — whole in
      entrypoint/beliefs/motivations/:
        [invoice-still-unpaid] — 6d ago
        [runner-flaked-twice] — 2d ago

**Never drop one silently.** A motivation that vanished from the pack is
a signal nobody knows exists, which is worse than one that cost forty
tokens — the line is the difference between cheap and invisible, and the
same rule as (6).

**Without a query every motivation goes in whole**, which is the
behaviour to implement first and the one to fall back to. `--query` is
an optimisation on a block that was already affordable; a wrapper with
nothing sensible to put in it should pass nothing.

### the matching rule, exactly

Two implementations must produce the same pack from the same tree, so
this is specified to the character and is deliberately stupid:

1. **Terms.** Lowercase the query, split on any run of characters that
   is not a letter, a digit or a hyphen, discard empties. Hyphens
   survive: `zero-downtime` is one term.
2. **Keywords.** Split the motivation's `keywords:` on commas, strip,
   lowercase.
3. **Match.** The two sets intersect. That is all.

No stemming, no plurals, no synonyms, no substrings, no scoring, no
ranking, no cutoff. `deploys` does not match `deploy` and it is not
supposed to — a matcher with opinions is a matcher two implementations
disagree about, and the failure mode of missing one is a collapsed line
the agent can still see and open.

**A motivation with no keywords at all is always injected whole.** There
is nothing to gate on, and an absent field is not a filter. This is also
why `keywords:` on a motivation is worth writing and never required.

**`keywords:` on a belief is a lint warning** (`ladder.md`). It is the
misunderstanding this section exists to prevent, written into a file:
somebody expected their beliefs to be retrieved.

## ages, not timestamps

Every age is relative and computed at render: `2h ago`, `yesterday`,
`9d ago`. A raw timestamp makes the model do arithmetic it gets wrong,
and — worse — a file dated in the header reads as current no matter how
old it is. "Something from yesterday is something from yesterday, not
something that just happened" is the whole reason the ages are there.

## ordering

Now, probes, due, the context layers, then the index. Two rules produce
that order and they point the same way: **the freshest facts first**,
because the rest of the session is wrong without them, and **the
re-readable block last**, because truncation eats the tail and a notes
index is the one part an agent can reconstruct with a grep.

The context layers sit in between rather than at the very end for that
second reason. They are the least volatile thing in the pack, but losing
them costs the standing rules for the whole session, and nothing else in
here will remind the model to go and read them.

## what the pack must never do

- **Never substitute a remembered value for a failed probe.** Covered in
  `probes.md`; it is the one rule with no exceptions.
- **Never present the index as the memory.** See (6).
- **Never dump a note body.** A pack that includes note contents stops
  being an index and becomes a second, worse copy of the memory that
  goes stale inside the context window. The context layers are the only
  bodies in here, and they are the only bodies that cannot go stale
  mid-session.
- **Never gate a belief or the persona on a query.** Whatever `--query`
  says, both go in whole. See above; it is the one thing in here a
  retrieval instinct will get wrong.
- **Never let the context layers grow unbounded.** They are paid for on
  every turn forever. Past a couple of thousand tokens, warn — "keep
  them few" is a rule with a number behind it. **One budget covers all
  three layers**, persona included: a second number would be a second
  thing to tune, and what is being defended is the per-turn bill, which
  does not care which file the characters came from. Say the split in the
  warning, though — "trim your context" without a breakdown gets the
  wrong layer trimmed.
- **Never omit provenance.** `[untrusted]` and `[unknown]` are part of
  the line, not a detail.
