# probes — the things I check instead of remember

A probe is a named command whose **output is the answer**. Not a note
about how to check something; the check itself.

Anything with a source of truth outside my head belongs here, and the
reading beats any note that disagrees. `<unknown>` means go check — it
never falls back to what I remembered.

One ` ```probe ` fence per probe. Everything outside a fence is prose
nobody parses, so write the *why* beside it.

    name   what it's called, here and in a note's `probes:` line
    tier   pack (every session, local, shares a 150ms budget)
           demand (when the subject comes up; may leave the machine)
    cmd    shell. cwd is this directory; $MEMORY is here, $ROOT its parent.
    ttl    seconds a reading may be reused. demand only.

## pack — every session, local, cheap

```probe
name: jobs-in-flight
tier: pack
cmd:  grep -lE '^status: (pending|running)' "$MEMORY"/tasks/*.md 2>/dev/null | wc -l | tr -d ' '
```

Background work not finished. `0` is the normal reading between jobs.
This is the number that decides whether "I'm on it" means anything right
now.

```probe
name: head-commit
tier: pack
cmd:  git -C "$ROOT" log -1 --format='%h %s' 2>/dev/null
```

What is actually committed. The answer to "did that land", which memory
gets wrong more than anything else.

## demand — when the subject comes up

These leave the machine, so they never run on the session-start path. A
note names them in its frontmatter:

    probes: open-prs

and any search that surfaces that note carries the fresh value with it.

```probe
name: open-prs
tier: demand
ttl:  60
cmd:  gh pr list --state open --json number,title -q '[.[]|"#\(.number) \(.title)"]|join("; ")'
```

Open PRs, by number and title. `<empty>` means none — a real answer, not
a failure.

---

Delete both examples and write your own. A probe you have to think about
before adding is a probe nobody adds.
