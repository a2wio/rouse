# probes — the things you check instead of remember

A probe is a named command whose **output is the answer**. Not a note
about how to check something; the check itself, run now, rendered where
the agent is already looking.

This is the piece most memory systems don't have, and it is the reason
the rest can be trusted. A memory system's characteristic failure is not
forgetting — it is remembering confidently. The note says the repo is
private; it went public last night; the agent has a sentence in its own
handwriting saying otherwise and no reason to doubt it. The fix is not a
better note. It is not having a note.

`inventory/probes.md` holds them, one fenced block each. A probe has no
clock and nothing above it, which is what makes `inventory/` its home.

    ```probe
    name: open-prs
    tier: demand
    ttl:  60
    cmd:  gh pr list --repo acme/api --state open --json number -q length
    ```

    How many PRs are waiting. `0` is a real answer, not a failure.

Everything outside a fence is prose nobody parses — write the *why*
there, next to the probe, where a future reader will find it.

## fields

    name   what it's called: in the pack, and in a note's `probes:` line
    tier   pack | demand — when it runs
    cmd    shell. cwd is the memory directory; $MEMORY is it, $ROOT its
           parent. `$ROOT` is the project when the tree is `./memory`
           and is the home directory when it is `~/.rouse` — a probe
           that means "here" should say `$MEMORY`.
    ttl    seconds a reading may be reused. demand only; pack always
           measures fresh.

## tier is a latency decision

`pack` runs on **every** session start, and the whole tier shares a
budget (default 150ms). So: local commands only. `git log -1`, a file's
age, a `grep -c` over a directory. Anything that leaves the machine is
hundreds of milliseconds spent on a fact that is usually irrelevant.

`demand` runs when the subject comes up. A note names the probe in its
frontmatter, and any search that surfaces that note carries the fresh
value back with it. That is the trick that makes probes cheap: you pay
for the network call in the turn where somebody actually asked.

## `<unknown>` never falls back to memory

A probe that fails, times out, or misses the budget renders exactly:

    open-prs: <unknown>

`<unknown>` means *go check*. It does not mean "no news" and it must
never, ever degrade into the last-known value or into whatever a note
said. A probe that quietly falls back to memory is worse than no probe,
because it launders a stale claim as a fresh one — the agent now has a
wrong answer wearing a timestamp.

Some probes are *designed* to go quiet: they read a file that a daemon
rewrites, so silence means the daemon is down, which is information.
Mark those `unknown-ok: yes` so a conformance check doesn't treat the
silence as a broken command.

## the rule for the agent

Anything with a source of truth outside your head gets a probe, and
**the probe's reading beats any note that disagrees.** Not "consider
both". The note is a memory of a fact; the probe is the fact.

Adding a probe should be live immediately — the reference
implementation re-reads `probes.md` on every render, so a probe written
this minute renders in the next pack with no restart. Keep it that way
in your own implementation; a probe you have to deploy is a probe
nobody adds.

## what makes a good one

    ✓  is the deploy green            a command, one line of output
    ✓  how many jobs are in flight    a count that changes hourly
    ✓  what's the head commit         the thing memory gets wrong most
    ✗  what did we decide about auth  no source of truth outside; that's a note
    ✗  full `kubectl get pods -A`     forty lines is not an answer

One line of output. If reading the probe's output takes longer than
running it, it's a command, not a probe.
