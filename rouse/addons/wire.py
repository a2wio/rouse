"""Telling the agent the tree is there.

Everything else in here is inert until something tells the model its
memory exists. That last step is one pasted paragraph, and it is where
installs die: the tree is on disk, the cli is on the path, and the model
never hears about either — so nothing is ever written, nothing ever
comes due, and rouse looks like it did nothing.

`rouse init --wire` does it in the same run. It appends one block to the
files an agent already reads on its own, and the block is addressed to
the model rather than about it: run this, read that, here is what the
clock will ask you.

Two rules, both about not being rude with somebody's repo.

**It only appends to a file that is already there.** No `CLAUDE.md`
means this isn't Claude Code, and a file rouse invented would be a file
nobody reads — an install that looks done and isn't. So it prints the
block and says where to put it.

**A marker makes the second run a no-op.** `--wire` will be run again —
by a reinstall, by somebody who forgot, by an agent following
install.txt — and a second copy of the same paragraph is how an
instruction file starts contradicting itself.
"""

import os
import shutil
from pathlib import Path

from ..core import home, layout

# the files an agent reads at session start without being asked to.
# Anything else — .cursor/rules, a system prompt in somebody's harness —
# is a paste, because rouse cannot know it is read
FILES = ("CLAUDE.md", "AGENTS.md")

# an html comment: nothing where the file is rendered, and the thing the
# second run looks for. Stable on purpose — change it and every file
# carrying the old one gets a second block
MARKER = "<!-- rouse -->"
END = "<!-- /rouse -->"


def cli() -> str:
    """`rouse` when the console script is on the path, `python3 -m rouse`
    when this is a checkout somebody vendored.

    The block is an instruction a model will run verbatim, so it has to
    be the form that works on this box, not the one that reads best.
    """
    return "rouse" if shutil.which("rouse") else "python3 -m rouse"


def where(memory: Path, root: Path | None = None) -> str:
    """The tree as the file being wired should name it: relative to the
    project when there is one, `~/.rouse` when there isn't."""
    memory = Path(memory)
    if root is None:
        return home.display(memory)
    return Path(os.path.relpath(memory, root)).as_posix()


def block(memory: Path, root: Path | None = None) -> str:
    """What gets appended. Short, because it is read every session and
    competes with everything else in that file."""
    tree, run = where(memory, root), cli()
    return f"""\
{MARKER}
## memory

Your memory lives in `{tree}`, and it can come and find you.

- Run `{run} pack` at the start of a session and work from what it
  prints: what you believe, what has come up, what has stopped moving,
  and what the probes read this second.
- Read `{tree}/{layout.INSTRUCTIONS}` before you write anything into
  memory. It says what goes where, and which files carry a clock.
- `{run} due` lists what the clock would wake you about, one line each.
{END}
"""


def append(path: Path, text: str) -> bool:
    """Add the block to one file, once. Says whether it wrote."""
    was = path.read_text(encoding="utf-8")
    if MARKER in was:
        return False
    joined = text if not was.strip() else was.rstrip("\n") + "\n\n" + text
    path.write_text(joined, encoding="utf-8")
    return True


def wire(root: Path, memory: Path) -> list[tuple[Path, bool]]:
    """Wire every agent file that exists in `root`.

    Reports per file rather than a count: a run that appended to
    AGENTS.md and left CLAUDE.md alone because it was already wired is
    two different pieces of news, and both of them matter to whoever is
    watching the install scroll past.
    """
    text = block(memory, root)
    return [(path, append(path, text))
            for name in FILES if (path := Path(root) / name).is_file()]
