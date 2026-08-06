"""The static layers: beliefs and motivations.

Everything else in this package is a record — it has a status, a clock,
and two ways of ending. These two have none of that. They are ground
truths about the world the agent works in, and the only thing that ever
happens to one is that a person writes it or deletes it.

    beliefs/belief-zero-downtime-deploys.md
    motivations/motivation-keep-the-deploy-trustworthy.md

Flat files, one fact each, `<type>-<slug>.md`. Flat because nothing ever
sits under one of these, and one per file because this is a system
prompt cut into modules: a rule can be added, dropped, reviewed or
copied to another agent without editing a wall of prose. The pack
injects all of them, whole, at the top of every session.

A motivation differs from a belief only in what it is about — a belief
is about the world, a motivation is about what you are currently for,
and so it is the shorter-lived of the two. It holds the intentions under
it in the sense that it says why they exist. It does not hold them in
the filesystem; nothing does.
"""

from pathlib import Path

from . import files, layout

HOMES = {"belief": layout.BELIEFS, "motivation": layout.MOTIVATIONS}


class Module:
    """One file, one ground truth."""

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
    """Every module of one type. Not recursive: a directory under
    `beliefs/` is a mistake rather than a nesting, and `check` says so
    instead of the reader quietly inventing a hierarchy."""
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
        out.append(f"{type_}s — ground truth, always true, not news:")
        for module in found:
            out.append(f"  [{module.slug}]")
            for line in module.text().splitlines():
                out.append(f"  {line}".rstrip())
            out.append("")
    return out
