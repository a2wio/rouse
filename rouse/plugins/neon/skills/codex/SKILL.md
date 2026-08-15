---
name: rouse-neon
description: Search this agent's own rouse memory across the bodies of every note, belief, intention and task — use when the session-start index (names, ages, keywords) isn't enough to find what was written, when you half-remember a fact but not which file holds it, or when you want to ask about the shape of your own memory. Also how the index is kept current (`rouse neon sync`) after writing memory.
---

# neon — your memory, queryable

Your memory is the files in your `.rouse/` tree. This is a copy of them
in postgres that you can search, and nothing else. Nothing here is true
that isn't in a file, so when the index and the tree disagree, the tree
is right and the index is behind.

You reach for it when the index you were handed at session start isn't
enough: it lists names, ages and keywords, and sometimes the thing you
need is one sentence inside a body you had no reason to open.

Run these in the shell:

    rouse neon recall "argocd annotation ceiling"
    rouse neon recall "invoice" --kind note --limit 5
    rouse neon recall "migration" --open        # only what hasn't ended

It prints paths and a snippet. **Then you open the file** — the snippet
is for choosing, not for answering. Answering out of a snippet is how you
end up quoting a note you never read.

## keep it current

    rouse neon sync

One way, tree to index, and it is cheap: unchanged files aren't
rewritten. Run it when you have written memory and expect to search soon,
and don't think about it otherwise. `recall` tells you when the index is
behind — that line means run `sync`, not "close enough".

If it has never been set up here, that is two commands:

    rouse neon init      # the schema
    rouse neon sync      # the tree

## what it is for, and what it isn't

- Searching bodies, across everything: notes, intentions, tasks, beliefs.
  `grep` still works and is right for an exact string; this is for the
  time you don't know the word that was used.
- Asking about the shape of your own memory:
  `rouse neon sql "select status, count(*) from rouse.memory where kind =
  'intention' group by 1"`. Read-only, always.
- **Not** a place to write. Nothing you put in a row survives the next
  sync. If something should be true, it goes in a file.
- **Not** somewhere secrets go. The bodies of your memory files land in
  this database in full — if a file shouldn't leave the machine, it
  shouldn't be in the tree either.

## the settings

They live in the header of `entrypoint/plugins/neon.md` in your tree:
`project:` is the neon project id and is the one thing that has to be
filled in. `rouse neon status` says what the index looks like and how old
it is, and is shaped to be a probe:

    ```probe
    name: memory-index
    tier: demand
    cmd:  rouse neon status
    ```

## forking

`rouse neon fork <name>` makes a neon branch: the index as it is right
now, copied in a second, and a session pointed at it with
`ROUSE_NEON_BRANCH=<name>`. That forks what you can *search*, not what
you *are* — the tree is still one tree and the files are still shared.
Forking the memory itself means forking the tree too, which is git's job.
