# plugins — the one door out of the filesystem

Everything else in this spec is an agreement about markdown, and that is
what makes it portable: a tree works with nothing running, in any
language, on a laptop with no network. A plugin is the exception, and it
is shaped so the exception stays one.

**A plugin is a skill and the tool that skill runs.**

    rouse/plugins/neon/
      plugin.md                the settings it needs, and what it is
      skills/
        claude-code/SKILL.md   the instructions, in that CLI's shape
        codex/SKILL.md
      tool/                    the code those instructions tell it to run

The instructions are not a mechanism rouse invented. They are a SKILL.md,
laid down where that agent CLI already looks — `.claude/skills/`,
`.codex/skills/` — and surfaced the way every other skill on the box is.
What the skill tells the model to run is `rouse <name> …`. That is the
whole idea: **the code goes next to the memory so the agent knows it is
there, and the CLI is the tool.**

It also means the same plugin ships one directory per agent CLI, and
adding a third is a directory and a line in a table — the differences
between them are a path and a house style, not a design.

## on and off

**Presence is the switch.** A plugin is on in a tree when it has a file
in `entrypoint/plugins/`:

    .rouse/entrypoint/plugins/neon.md

and off when it hasn't. No registry, no enabled-list, no config key — the
same reason the persona layer is a path (`persona.md`) rather than a
setting. A list of what is on, kept somewhere other than the thing that
is on, is a list that will one day be wrong.

**That file is the settings.** Its header is what the plugin's code
reads:

    ---
    description: the memory tree, mirrored into postgres
    project: quiet-sky-42
    database: neondb
    skills: .claude/skills/rouse-neon
    ---

Frontmatter is already the interface everywhere else here (`README.md`),
and a second config format would be a second thing to keep true. An empty
value means somebody still has to fill it in, and `check` says so, the
same way it does for a `closes-when` nobody wrote.

**And it is the receipt.** `skills:` is every directory the install
wrote, relative to the directory the tree sits in — relative because a
memory tree is a repository that travels, and an absolute path in a
header is a path that is wrong on the second machine. It is the only way
`remove` can take back exactly what `add` put down: it deletes the
recorded directories, and only those, and only while they still look like
a skill this laid down.

**It is in `entrypoint/` because it is an instruction file.** It says
what this agent can reach, like `rouse.md` beside it. It is not a record:
no clock, no status, nothing sweeps it.

## where a skill lands

Beside the tree. A project tree at `./.rouse` puts skills in that
project's `.claude/skills/`; an agent's own tree at `~/.rouse` puts them
in `~/.claude/skills/`. One rule, and it falls out of the rule above it:
skills belong to the same scope as the memory they are about.

Nothing is ever created for an agent that isn't here. If a box has no
`.claude` and no `.codex`, `add` turns the plugin on, says no skill was
installed, and names the flag that would force one — the same rule
`--wire` follows about `CLAUDE.md`. An install that invents a directory
for an agent nobody runs is an install that looks finished and is read by
nobody.

## what the pack does with one

One line, and only when something is on:

    plugins: neon — the skill for one is your agent's;
    entrypoint/plugins/neon.md is what it is set to

A pointer, not a body. The agent's own CLI already has the instructions;
this line is for the session reading the pack, and the context layers are
the only bodies a pack carries (`pack.md`).

## what a plugin may not do

- **No python dependencies.** `pip install rouse` installs rouse and
  nothing else. A plugin may require an external CLI — the person
  installed it, it is on the path or it isn't, and the failure says which
  — but it may never add to `dependencies`. A memory framework whose
  install pulls a database driver has stopped being a set of agreements.
- **It doesn't write memory.** It reads the tree and talks to the
  outside. The only files it writes are its own: the one in the tree that
  says it is on, and the skills it lays down. Anything that should be
  true goes in a memory file, written by the agent, like everything else.
- **Nothing in `core/` may import one.** The dependency runs one way: a
  plugin may use core; core does not know plugins exist. `pack` prints
  the line above by globbing a directory, which is a fact about the tree
  rather than a call into anything. An install with no plugins is the
  rouse that was there before.

## database plugins

The first kind, and the one neon is: **a database plugin mirrors the
`.rouse/` tree into a database, and that is all it does.** It does not
invent a memory format, it does not become the place memory lives, and
nothing in it is true that isn't in a file.

Sync is one way. A row that disagrees with a file is wrong by
definition — which is why a sync is safe to run at any moment, why a lost
database costs a re-sync and nothing else, and why the agent still works
with the network down. The tempting version, memory that lives in
postgres and is written through, buys nothing the tree doesn't already
give (git history, a diff of what it changed its mind about, a text
editor) and costs the thing everything else here is built on.

## the first one: neon

`rouse/plugins/neon/` mirrors the tree into postgres so recall can be a
query instead of a grep. It shells out to `neonctl` for the connection
and `psql` for the SQL, which is what keeps the no-dependency rule above
and also means nobody here handles a credential.

    rouse plugin add neon project=quiet-sky-42
    rouse neon init && rouse neon sync
    rouse neon recall "the thing about annotations"

## forking, and what it actually forks

A neon branch is a copy-on-write fork of a database, made in a second.
`rouse neon fork tuesday` makes one, and `ROUSE_NEON_BRANCH=tuesday`
points a session at it.

What that forks is the *index*: two sessions, two copies of what can be
searched, one tree of files underneath. It is enough for the read-side
experiment — delete a fortnight of rows on a branch and ask what the
agent would have found without them — and it is not the same thing as
forking the memory. That needs the tree forked too, and the tree is
already a git repository (`home.md`), so the pair is `git worktree` plus
`neon fork`: same agent, two pasts, run both, diff what it did.

Nothing here implements the pair. It is written down because the shape of
the plugin should not accidentally rule it out, and because the
write-through version rules it out completely: the files are what make a
fork cheap, a diff readable, and a rollback a `git revert`.
