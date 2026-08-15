"""Plugins: a skill for the agent, a tool for it to run, one file in the
tree saying it is on.

Everything else in rouse is a convention about markdown, and that is what
makes a tree portable. A plugin is the one door out of that — a database,
a search index, whatever a particular agent needs that a directory of
files cannot do on its own — and it is shaped so the exception stays one.

    rouse/plugins/neon/
      plugin.md              the settings it needs, and what it is
      skills/
        claude-code/SKILL.md   the instructions, in that CLI's shape
        codex/SKILL.md
      tool/                  the code those instructions tell it to run

**A plugin is a skill.** The instructions are not something rouse invents
a way to show the model: they are a SKILL.md, laid down where that agent
CLI already looks for skills, and the CLI surfaces it the same way it
surfaces every other skill on the box. What the skill tells the model to
run is `rouse <name> …`, which is the tool. So installing one is a copy
into `.claude/skills/` or `.codex/skills/`, and nothing has to teach a
model a new mechanism.

**Presence is the switch.** A plugin is on in a tree when
`entrypoint/plugins/<name>.md` is there, and off when it isn't. No
registry, no enabled-list to get out of step with what is on disk — the
same reason the persona layer is a path rather than a setting
(`spec/persona.md`).

**That file is the settings, and the receipt.** Its header is what the
plugin's code reads — which project, which database — and it also records
every skill directory the install wrote, which is the only way `remove`
can take back exactly what `add` put down and nothing else.

Two rules a plugin does not get to break:

- **No python dependencies.** `pip install rouse` installs rouse and
  nothing else, and that is a claim this repo makes out loud. A plugin
  may need an external CLI on the path — that is the user's install and
  it fails loudly with instructions — but it may never add to
  `dependencies`.
- **It doesn't write memory.** A plugin reads the tree and talks to the
  outside. The only files it ever writes are its own: the one in the tree
  that says it is on, and the skills it lays down for the agent.

Nothing in `core/` imports this. The dependency runs one way — a plugin
may use core, core may not know a plugin exists — so an install with no
plugins is the rouse that was there before.
"""

import importlib
import shutil
import sys
from pathlib import Path

from ..core import files, layout

DIR = Path(__file__).resolve().parent

# the manifest, in every plugin: the header is the settings this plugin
# needs, the body is what it is. It is the file that gets copied into the
# tree, so a plugin with no manifest is a plugin nothing can turn on
MANIFEST = "plugin.md"

# the two directories a plugin is made of, and neither is optional in
# spirit: `skills/` is how the model finds out, `tool/` is what it runs
SKILLS = "skills"
TOOL = "tool"

# the agent CLIs, and the directory each keeps its own things in. A skill
# goes at `<that>/skills/<name>`, which is the one shape both of these
# agree on — a third one is a line here and a directory in the plugin.
AGENTS = {"claude-code": ".claude", "codex": ".codex"}

# what the skill is called once it is installed. Prefixed, because it
# lands in a directory somebody else's skills also live in, and because
# `remove` will not delete a directory that isn't named like ours
PREFIX = "rouse-"

# header fields that are the mechanism rather than somebody's answer, so
# `blanks` doesn't ask anyone to fill them in
RESERVED = ("description", "skills")


def available() -> list[str]:
    """Every plugin this install ships. A directory holding a manifest is
    one; anything else in here is not."""
    return sorted(path.name for path in DIR.iterdir()
                  if path.is_dir() and (path / MANIFEST).is_file())


def manifest(name: str) -> Path:
    return DIR / name / MANIFEST


def described(name: str) -> str:
    return (files.head(manifest(name)) or {}).get("description", "")


def shipped(name: str) -> dict[str, Path]:
    """The skills this plugin ships, by agent. A plugin that ships none is
    allowed: the tool still works, nothing tells the model about it."""
    root = DIR / name / SKILLS
    return {agent: root / agent for agent in AGENTS
            if (root / agent / "SKILL.md").is_file()}


def where(memory: Path) -> Path:
    return Path(memory) / layout.PLUGINS


def installed(memory: Path, name: str) -> Path:
    return where(memory) / f"{name}.md"


def enabled(memory: Path) -> list[str]:
    """What this tree has turned on, whether or not this install ships the
    code for it. A tree written on another machine still says what it
    expects, and `rouse plugin` prints that difference rather than hiding
    the file."""
    root = where(memory)
    return sorted(path.stem for path in root.glob("*.md")) if root.is_dir() \
        else []


def settings(memory: Path, name: str) -> dict:
    """The header of the tree's copy: this agent's answers for this
    plugin. Empty when it isn't on — the caller says so, because it is the
    one that knows what it was about to do."""
    path = installed(memory, name)
    return (files.head(path) or {}) if path.is_file() else {}


def blanks(memory: Path, name: str) -> list[str]:
    """Header fields the plugin needs and nobody has filled in yet. Same
    idea as `scaffold.blanks`: the thing that will fail in a minute, said
    now."""
    return [key for key, value in settings(memory, name).items()
            if not value and key not in RESERVED]


# -- where a skill goes -------------------------------------------------


def beside(memory: Path) -> Path:
    """The directory a tree lives in — the project for `./.rouse`, the
    home directory for `~/.rouse`. Skills land beside the memory they are
    about, so a project tree gets project skills and an agent's own tree
    gets that agent's own.

    Made absolute rather than resolved: a path printed here is one
    somebody has to recognise, and `/tmp` turning into `/private/tmp` on
    the way past a symlink is a path they will not."""
    return Path(memory).absolute().parent


def homes(memory: Path) -> dict[str, Path]:
    """The agent CLIs that are actually here, and where each keeps skills.

    Beside the tree first, then the user's own directory. Nothing is
    created: an agent that has never run on this box has no directory,
    and inventing one would be an install that looks finished and is read
    by nobody — the same rule `--wire` follows about CLAUDE.md
    (`rouse/addons/wire.py`).
    """
    root, found = beside(memory), {}
    for agent, dirname in AGENTS.items():
        for base in (root, Path.home()):
            if (base / dirname).is_dir():
                found[agent] = base / dirname / SKILLS
                break
    return found


def skill_dir(memory: Path, agent: str, name: str) -> Path:
    """Where this plugin's skill goes for one agent, whether or not that
    agent is here — `add --agent` names one that isn't, and then this is
    the directory it makes."""
    at = homes(memory).get(agent)
    return (at or beside(memory) / AGENTS[agent] / SKILLS) / f"{PREFIX}{name}"


def recorded(memory: Path, name: str) -> list[Path]:
    """The skills this tree says it laid down, as absolute paths.

    Written relative to the tree's own directory and read back the same
    way, because a memory tree is a git repository that travels: an
    absolute path in a header is a path that is wrong on the second
    machine.
    """
    raw = settings(memory, name).get("skills", "")
    return [beside(memory) / part.strip()
            for part in raw.split(",") if part.strip()]


def _relative(memory: Path, path: Path) -> str:
    root = beside(memory)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


# -- turning one on, and off --------------------------------------------


def add(memory: Path, name: str, fields: dict | None = None,
        agents: list[str] | None = None) -> tuple[Path, dict[str, Path]]:
    """Turn one on: the skills, then the file in the tree that says so.

    Never overwrites the file in the tree. It carries this agent's project
    id and possibly a paragraph somebody added for their own agent, and a
    second `add` that silently restored the shipped one would take both
    away.

    Returns the file and the skills it wrote, because the one caller
    prints them: an install that copied something into `~/.claude` and
    said nothing about it is a surprise in somebody's home directory.
    """
    if name not in available():
        raise ValueError(f"no plugin called {name!r}: "
                         + (", ".join(available()) or "none installed"))
    target = installed(memory, name)
    if target.exists():
        raise ValueError(f"{target} already exists — not touching it. "
                         f"`rouse plugin remove {name}` first, or edit it")
    ships = shipped(name)
    if unknown := [a for a in (agents or []) if a not in AGENTS]:
        raise ValueError(f"no agent called {unknown[0]!r}: "
                         + ", ".join(AGENTS))
    # named agents are taken as asked for, even ones with no directory
    # yet; found ones are only the ones already on this box
    wanted = agents if agents is not None else sorted(homes(memory))
    wrote = {}
    for agent in wanted:
        if agent not in ships:
            continue
        at = skill_dir(memory, agent, name)
        at.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ships[agent], at, dirs_exist_ok=True)
        wrote[agent] = at

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest(name).read_text(encoding="utf-8"),
                      encoding="utf-8")
    files.set_fields(target, **(fields or {}),
                     skills=", ".join(_relative(memory, path)
                                      for path in wrote.values()))
    return target, wrote


def remove(memory: Path, name: str) -> tuple[Path, list[Path]]:
    """Turn one off: the skills it wrote, then the file in the tree.

    It deletes only what the tree says it put there, and only if what is
    there still looks like a skill this laid down — the recorded path, the
    `rouse-` name, a SKILL.md inside it. A `remove` that took a directory's
    word for it is one wrong header away from deleting somebody's own
    skill, and skills live in a directory full of other people's.
    """
    path = installed(memory, name)
    if not path.is_file():
        raise ValueError(f"{name} isn't on in this tree")
    gone = []
    for at in recorded(memory, name):
        if at.name.startswith(PREFIX) and (at / "SKILL.md").is_file():
            shutil.rmtree(at)
            gone.append(at)
    path.unlink()
    return path, gone


def run(name: str, argv: list[str]) -> int:
    """Hand the rest of the command line to the plugin's tool.

    Imported here and not at module load: an install that ships a plugin
    nobody uses should pay nothing for it, and a plugin whose import blows
    up should break its own verb rather than every verb.
    """
    where = f"{__name__}.{name}.{TOOL}"
    try:
        module = importlib.import_module(where)
    except ModuleNotFoundError as exc:
        # a plugin is allowed to be a skill and nothing else — some of
        # them will be — and `rouse <name>` on one of those should say so
        # rather than print a traceback about a module nobody named
        if exc.name != where:
            raise
        print(f"{name} has instructions but no tool: nothing to run as "
              f"`rouse {name} …`", file=sys.stderr)
        return 2
    return module.main(argv)
