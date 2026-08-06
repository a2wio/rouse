"""The static layers: beliefs and motivations.

Everything else in this package is a record — it has a status, a clock,
and two ways of ending. These two have none of that. They are context,
and the only thing that ever happens to one is that a person writes it
or deletes it.

    beliefs/belief-zero-downtime-deploys.md
    beliefs/motivations/motivation-two-deploys-broke-prod.md

Flat files, one fact each, `<type>-<slug>.md`. Flat because no belief
ever sits inside another belief, and one per file because this is a
system prompt cut into modules: a rule can be added, dropped, reviewed
or copied to another agent without editing a wall of prose. The pack
injects all of them, whole, at the top of every session.

The two differ in where they come from. A **belief** is internal and
timeless — how the world works, how this team works, what the agent
holds true regardless of the week. A **motivation** is external and
momentary — a signal that arrived: somebody said something, a number
crossed a line, it has been eleven days without a restore drill. It is
the reason there is anything to do at all, and an intention is the
agent's own answer to one.

`motivations/` living inside `beliefs/` is that sentence made visible
and nothing more. No motivation belongs to a belief, no intention
belongs to a motivation, and neither relationship is in the filesystem —
if you want the connection recorded, write the sentence in the body.
"""

from pathlib import Path

from . import files, layout

HOMES = {"belief": layout.BELIEFS, "motivation": layout.MOTIVATIONS}

# how each layer announces itself in the pack. Both end the same way and
# have to: a paragraph at the top of a session reads as something that
# just came in, and a motivation — which really did arrive once — is the
# one most likely to be replied to as if it just had.
LABELS = {"belief": "ground truth, always true, not news",
          "motivation": "signals that arrived — standing context, not news"}


class Module:
    """One file, one thing: a ground truth, or a signal."""

    __slots__ = ("type", "path", "rel")

    def __init__(self, type_: str, path: Path, rel: Path):
        self.type = type_
        self.path = path
        self.rel = rel

    @property
    def slug(self) -> str:
        """The name without its type prefix. `belief-zero-downtime.md`
        is the belief `zero-downtime`; the prefix is there so the file
        still says what it is once it has been copied somewhere else."""
        stem = self.path.stem
        prefix = f"{self.type}-"
        return stem[len(prefix):] if stem.startswith(prefix) else stem

    @property
    def id(self) -> str:
        return f"{self.type}/{self.slug}"

    def text(self) -> str:
        """The body. Unlike every record in here, a context module is
        read for its body every single session — that IS the injection,
        and it is why the header stays minimal."""
        return files.body(self.path).strip()

    def __repr__(self) -> str:
        return f"<{self.id}>"


def read(memory: Path, type_: str) -> list[Module]:
    """Every module of one type. Not recursive, and that is load-bearing
    now that the layers nest: the directory under `beliefs/` is the next
    layer down, not more beliefs. Anything else in there is a mistake,
    and `check` says so instead of the reader inventing a hierarchy."""
    root = Path(memory) / HOMES[type_]
    return [Module(type_, path, path.relative_to(memory))
            for path in sorted(root.glob("*.md"))]


def layers(memory: Path) -> list[Module]:
    found = []
    for type_ in layout.CONTEXT:
        found += read(memory, type_)
    return found


def render(memory: Path) -> list[str]:
    """The pack's context block: every module, in full.

    The pack's standing rule is that it prints pointers and never bodies,
    because a body in the pack is a second copy of the memory that goes
    stale inside the window. These are the exception, and the reason is
    exact: they have no clock, so there is no version of one that can go
    stale mid-session.
    """
    out: list[str] = []
    for type_ in layout.CONTEXT:
        found = read(memory, type_)
        if not found:
            continue
        out.append(f"{type_}s — {LABELS[type_]}:")
        for module in found:
            out.append(f"  [{module.slug}]")
            for line in module.text().splitlines():
                out.append(f"  {line}".rstrip())
            out.append("")
    return out
