# home — where the tree is

A memory tree has to be findable by something that was not told where it
is. An agent started by launchd from `/`, a worker with no checkout, a
second process that only knows the agent's name: all of them need the
same answer, and "pass `--memory`" is not an answer, it is a thing each
wrapper gets to invent differently.

So there is one order, and every implementation uses it:

    1. --memory <dir>     explicit, and explicit always wins
    2. $ROUSE_HOME        this agent's tree, wherever it keeps it
    3. ./memory           the project you are standing in
    4. ~/.rouse           the global one

**`~/.rouse` is the standard entrypoint.** Any agent may assume it
exists without being configured, and anything that lays a tree down for
an agent with no project should put it there. That is the whole of the
convention: one path, spelled the same everywhere, so pointing a new
tool at an existing memory is nothing more than not overriding it.

Rung 3 is the only one that asks whether the directory is really there.
That asymmetry is deliberate — a project that has a tree gets its own, a
project that doesn't falls through to the agent's, and nobody sets
anything in either case. Rungs 1 and 2 are taken as given: a path that
was named explicitly and does not exist is an error worth seeing, not a
reason to quietly use a different tree.

Project beats global because a tree that belongs to a repo should travel
with it and be reviewed with it. The env var beats the project because
it is how you say *which agent this is* — and that is the one thing the
filesystem cannot work out on its own.

## one tree per agent

**Two agents must never share a memory tree.** Not a project one, not
`~/.rouse`, not "just for now".

The pack injects the persona, every belief and every motivation, whole, at
the top of every session (`pack.md`). So a shared tree is one agent
silently adopting another's ground truths — and its voice, since there is
one `persona.md` per tree and it is not addressed to anybody — and then
being nudged about intentions it never formed, and writing its own into a
directory where the other one will read them as its own next session. Nothing in a
record says who wrote it, because until now nothing had to: a tree
*was* an agent. Sharing one deletes the only thing making the ladder
mean anything, which is that the agent whose intention it is, is the
agent who gets asked about it.

`ROUSE_HOME` is how the second agent gets its own:

    ROUSE_HOME=~/.rouse-reviewer   agent two
    ROUSE_HOME=~/.rouse-oncall     agent three

The failure is quiet and it looks like the system working, which is why
it is written down here rather than left to good sense. If two agents
genuinely need the same fact, copy the belief file into both trees —
one ground truth per file is what makes that a one-line operation, and
it is the reason the context layers are cut into files at all.

## laying one down

    rouse init              ./memory, in the project you're in
    rouse init <dir>        <dir>/memory
    rouse init --global     ~/.rouse

Both modes give the tree a git repository of its own when it hasn't got
one already — no git on the box, or a tree laid down inside an existing
checkout, and it is skipped. Nothing ever commits into a repository it
did not create.

That is not decoration. The record of what an agent changed its mind
about is the history of these files: what it believed last week is one
diff away, and a tree at `~/.rouse` has no project repository to carry
that for it. An implementation may skip the git part; one that does
should say so, because a tree with no history is a tree where a belief
can change with nobody able to say when.
