---
description: the memory tree, mirrored into postgres, so recall stops being a grep
project:
database: neondb
---

# neon

The `.rouse/` tree, copied into a postgres database, so that finding
something can be a query instead of a grep. One table, full-text search
over the bodies, and a `recall` that prints paths.

**The files are still the memory.** Sync goes one way, tree to database,
and a row that disagrees with a file is wrong by definition. Losing the
database costs a re-sync and nothing else.

## the header above

- `project:` — the neon project id (`neonctl projects list`). The one
  thing that has to be filled in.
- `database:` — which database in it. `neondb` unless you made another.
- `branch:` — add this line to pin the tree to one neon branch. With no
  line it uses the project's default.
- `role:` — add this line if the branch has more than one postgres role.
  A project shared with an application usually does, and `neonctl` will
  not guess between them.
- `skills:` — written by `rouse plugin add`: where the skill was laid
  down, so `rouse plugin remove` can take back exactly that and nothing
  else. Not yours to edit.

The connection itself is `neonctl`'s job. Nothing here stores a
connection string, prints one, or puts one on a command line. It logs in
one of three ways, in this order: `$ROUSE_NEON_URI` if the box has a
connection string and no login, `$NEON_API_KEY` for anything headless —
CI, a daemon, a container — and otherwise whatever `neonctl auth` left
behind. With none of the three, `neonctl` goes looking for a browser and
spends a silent minute waiting for one, so a fresh box fails slowly
before it fails clearly. Set one of the three first.

## how it is used

The instructions the agent reads are the skill this installed — in
`.claude/skills/rouse-neon/`, `.codex/skills/rouse-neon/`, or wherever
that CLI keeps them. If your agent has no skills, the surface is small
enough to read from the help:

    rouse neon --help
