"""Where the tree is.

`--memory ./memory` was fine while rouse was one repo's convention. It
stops being fine the moment an agent has no repo to stand in — one that
answers messages, one that runs as a daemon, one started by launchd from
`/` — because then the working directory means nothing and every wrapper
invents its own answer to a question that should have exactly one.

So there is a standard place, and an order for finding it:

    1. --memory <dir>     explicit, and explicit always wins
    2. $ROUSE_HOME        this agent's tree, wherever it keeps it
    3. ./.rouse           the project you are standing in
    4. ~/.rouse           the global one

Rungs 3 and 4 are the same name twice, and that is the point: the tree is
`.rouse`, in a project or in a home directory, so there is one word to
learn and a path that reads the same wherever it is written down. It is
dotted because it is the agent's, not the project's — it sits beside
`.git` and `.claude` rather than in the middle of somebody's source.

Only rung 3 asks whether the directory is really there, and that is what
makes `~/.rouse` a fallback rather than a fifth thing to configure: a
project that has a tree gets it, a project that doesn't gets the agent's
own, and nobody has to set anything either way.

The env var beats the project because it is how you say *which agent
this is*, and that is the one thing the filesystem cannot guess. Which
is also the rule underneath all of it: **one tree per agent**. Two
agents sharing one is two agents reading each other's beliefs out of the
same pack and being nudged about work neither of them took on, with no
way afterwards to tell who meant what. `spec/home.md` states it as a
rule; `ROUSE_HOME` is how the second agent gets its own.
"""

import os
from pathlib import Path

from . import layout

ENV = "ROUSE_HOME"
LOCAL = ".rouse"        # rung 3: the project you're standing in
GLOBAL = "~/.rouse"     # rung 4: the standard entrypoint, any agent

# what rung 3 was called before the tree got its own name. Still found,
# because a tree that stops being found is an agent that has forgotten
# everything, and that is a rude thing for an upgrade to do
WAS = "memory"

# the order in the words the CLI prints when it found nothing
ORDER = ("--memory", f"${ENV}", f"./{LOCAL}", GLOBAL)


def resolve(explicit=None, *, env=None, cwd=None) -> Path:
    """The memory tree, by the order above. Nothing here creates or
    checks anything except rung 3 — a resolver that made directories
    would put an empty tree wherever a typo pointed."""
    env = os.environ if env is None else env
    if explicit is not None:
        return Path(explicit)
    if named := env.get(ENV):
        return Path(named).expanduser()
    here = Path.cwd() if cwd is None else Path(cwd)
    if (local := here / LOCAL).is_dir():
        return local
    # a `./memory` from before the rename, and only if it really is a
    # tree: `memory/` is somebody's source directory in plenty of repos,
    # and picking one of those up would be worse than finding nothing
    if (was := here / WAS / layout.INSTRUCTIONS).is_file():
        return was.parent.parent
    return tree()


def tree() -> Path:
    """`~/.rouse`, expanded now rather than at import. `$HOME` moves —
    under `sudo -u`, inside a test — and a module constant does not."""
    return Path(GLOBAL).expanduser()


def display(path) -> str:
    """The path as a person would type it: relative to the working
    directory when it is under it, `~/…` when it is under home. Printed
    and pasted into a system prompt, never parsed back."""
    path = Path(path)
    for base, prefix in ((Path.cwd(), ""), (Path.home(), "~/")):
        try:
            return prefix + str(path.relative_to(base))
        except ValueError:
            continue
    return str(path)
