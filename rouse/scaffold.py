"""Making records, moving records, and looking at the shape of them.

A record being a directory costs one `mkdir` more than a record being a
file, and that cost lands on the two types written most often. `rouse
new` is the answer to it: one command, one line of output, the header
already filled in with the fields that level owes.

It writes the two context layers too, and they go the other way — a
belief is one flat file with almost no header, because there is no clock
to feed and nothing will ever sit inside it.

`rouse promote` exists because the backlog's only honest exit — becoming
an intention — is a move across two trees, and a move that takes two
commands is a move somebody does halfway.
"""

import shutil
import subprocess
from pathlib import Path

from . import context, files, layout, levels

# what each level owes, in the order it reads best. `{now}` and `{day}`
# are filled in; anything left blank is the writer's job.
TEMPLATES: dict[str, tuple[list[tuple[str, str]], str]] = {
    "belief": ([("keywords", "")],
               "One ground truth about the world you work in, stated "
               "plainly and in the present tense.\n"),
    "motivation": ([("keywords", "")],
                   "The signal that arrived, from outside: who said it or "
                   "what happened, and what it is pressure to do.\n"),
    "intention": ([("status", "open"), ("opened", "{now}"),
                   ("last-moved", "{now}"), ("stale-after", "2h"),
                   ("closes-when", "")],
                  "What you mean to make true, and why.\n"),
    "goal": ([("status", "open"), ("opened", "{now}"),
              ("last-moved", "{now}"), ("success-when", ""),
              ("falsifiers", ""), ("review-every", "7d")],
             "What winning looks like, and what to try next.\n"),
    "action": ([("status", "open"), ("opened", "{now}"),
                ("last-moved", "{now}"), ("closes-when", ""),
                ("outcome", "")],
               "What you meant to do — and, once judged, what actually "
               "became true.\n"),
    "task": ([("status", "pending"), ("category", ""), ("opened", "{now}")],
             "What to find out or do, why it's wanted, and what a useful "
             "answer looks like.\n"),
    "reminder": ([("due", ""), ("status", "pending")],
                 "What this is about, what to say, tone notes for "
                 "future-you.\n"),
    "backlog": ([("status", "open"), ("opened", "{day}"), ("keywords", "")],
                "What it is, why it's worth doing, and what was said when "
                "it got parked.\n"),
}


def blanks(path: Path) -> list[str]:
    """Header fields the template left for the writer. Printed after
    `new`, because a record with an empty `due:` or `closes-when:` is the
    one thing the linter will shout about a minute later."""
    return [key for key, value in (files.head(path) or {}).items()
            if not value]


def resolve(memory: Path, under: str | None, type_: str) -> Path:
    """Where a new record goes. `--under` takes either a path relative to
    the memory root or the slug of an existing record; a slug is what a
    person actually has in their head."""
    memory = Path(memory)
    if not under:
        return memory / layout.home(type_)
    candidate = memory / under
    if candidate.is_dir():
        return candidate
    hits = [r for r in levels.Records(memory).all() if r.slug == under]
    if len(hits) == 1:
        return hits[0].dir
    if not hits:
        raise ValueError(f"no record or directory called {under!r}")
    raise ValueError(f"{under!r} is ambiguous: "
                     + ", ".join(str(r.rel) for r in hits))


def _write(path: Path, type_: str) -> Path:
    if path.exists():
        raise ValueError(f"{path} already exists — not touching it")
    fields, body = TEMPLATES[type_]
    now, day = files.stamp(), files.stamp()[:10]
    header = "\n".join(f"{k}: {v.format(now=now, day=day)}".rstrip()
                       for k, v in fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{header}\n---\n\n{body}", encoding="utf-8")
    return path


def new(memory: Path, type_: str, slug: str, under: str | None = None) -> Path:
    if type_ not in layout.WRITABLE:
        raise ValueError(f"{type_!r} is not a type rouse writes: "
                         + ", ".join(layout.WRITABLE))
    if type_ in layout.CONTEXT:
        if under:
            raise ValueError(f"a {type_} sits under nothing — it is context, "
                             "not a record")
        return _write(Path(memory) / context.HOMES[type_]
                      / f"{type_}-{slug}.md", type_)
    return _write(resolve(memory, under, type_) / slug / f"{type_}.md", type_)


def _move(src: Path, dst: Path) -> None:
    """`git mv` when there is a git to tell, so the history follows the
    record across the two trees. Plain move otherwise."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(["git", "-C", str(src.parent), "mv", str(src),
                           str(dst)], capture_output=True, text=True)
    if done.returncode != 0:
        shutil.move(str(src), str(dst))


def promote(memory: Path, slug: str, under: str | None = None) -> Path:
    """A backlog item becoming an intention: the directory moves, and it
    keeps its own record of having moved.

    No tombstone is left behind. The backlog is a list of what is still
    parked, and it stays readable by not accumulating the things that
    left; where this one came from is in its header and in git.
    """
    memory = Path(memory)
    hits = [r for r in levels.Records(memory).of("backlog") if r.slug == slug]
    if not hits:
        raise ValueError(f"no backlog item called {slug!r}")
    item = hits[0]
    was = str(item.rel)
    target = resolve(memory, under, "intention") / slug
    if target.exists():
        raise ValueError(f"{target} already exists")
    _move(item.dir, target)
    path = target / "intention.md"
    (target / "backlog.md").rename(path)
    now = files.stamp()
    files.set_fields(path, status="open", last_moved=now, stale_after="2h",
                     closes_when=item.head.get("closes-when") or "",
                     promoted=now, was=was)
    return path


def render_tree(memory: Path) -> str:
    """What is on disk, in the three shapes it comes in.

    The context layers list flat, because the items in them are flat —
    the directories nest, one layer per level, but a belief that appeared
    to contain a motivation would be the lineage this system deliberately
    doesn't have. The records nest for real, which is the payoff of
    containment being the filesystem: who is a run of what, without
    opening a file.
    """
    memory = Path(memory)
    records = levels.Records(memory)
    modules = context.layers(memory)
    roots = sorted((r for r in records.all() if records.parent(r) is None),
                   key=lambda r: (r.type, r.slug))
    if not roots and not modules:
        return "nothing written yet\n"
    out: list[str] = []

    for type_ in layout.CONTEXT:
        found = [m for m in modules if m.type == type_]
        if found:
            out.append(f"{type_}s:")
            out += [f"  {m.slug}" for m in found]
            out.append("")

    def walk(rec, depth):
        status = (rec.head.get("status") or "").strip()
        mark = "" if not status else f"  [{status}]"
        out.append(f"{'  ' * depth}{rec.type} {rec.slug}{mark}")
        for child in sorted(records.children(rec),
                            key=lambda r: (r.type, r.slug)):
            walk(child, depth + 1)

    ladder = [r for r in roots if r.rel.parts[0] == layout.ENTRYPOINT]
    rest = [r for r in roots if r.rel.parts[0] != layout.ENTRYPOINT]
    for root in ladder:
        walk(root, 0)
    if rest:
        if ladder:
            out.append("")
        out.append(f"{layout.INVENTORY}:")
        for root in rest:
            walk(root, 1)
    return "\n".join(out).rstrip("\n") + "\n"
