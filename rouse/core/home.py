"""Where the tree is.

`--memory ./memory` was fine while rouse was one repo's convention. It
stops being fine the moment an agent has no repo to stand in — one that
answers messages, one that runs as a daemon, one started by launchd from
`/` — because then the working directory means nothing and every wrapper
invents its own answer to a question that should have exactly one.

So there is a standard place, and an order for finding it:

    1. --memory <dir>     explicit, and explicit always wins
    2. $ROUSE_HOME        this agent's tree, wherever it keeps it
    3. ./memory           the project you are standing in
    4. ~/.rouse           the global one

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

ENV = "ROUSE_HOME"
LOCAL = "memory"        # rung 3: the project you're standing in
GLOBAL = "~/.rouse"     # rung 4: the standard entrypoint, any agent

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
    local = (Path.cwd() if cwd is None else Path(cwd)) / LOCAL
    return local if local.is_dir() else tree()


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
