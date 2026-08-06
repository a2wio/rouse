"""What the agent is handed at session start.

Volatile first, durable last: if the context window forces truncation it
eats the tail, and the tail should be the part that can be re-read on
demand. Pointers, never bodies — a pack that includes note contents is a
second, worse copy of the memory that goes stale inside the window.

Without a daemon, the `due:` block below IS the clock: overdue records
surface at the top of every session instead of never.
"""

import time
from pathlib import Path

from . import files, layout, levels, probes

FRESH_S = 36 * 3600      # listed in full above this age
MAX_OLDER = 60           # lines before the older list is truncated


def render(memory: Path, *, budget_ms: int = probes.BUDGET_MS,
           now: float | None = None) -> str:
    memory = Path(memory)
    now = time.time() if now is None else now
    records = levels.Records(memory)
    out = [time.strftime("now: %A %Y-%m-%d %H:%M %Z", time.localtime(now)), ""]

    if readings := probes.readings(memory, "pack", budget_ms):
        out.append("measured just now — these beat any memory file that "
                   "disagrees,")
        out.append("and `<unknown>` means go check, not \"no news\":")
        out += [f"  {name}: {value}" for name, value in readings]
        out.append("")

    out += _due(records, now) + _ladder(records) + _notes(memory, now)
    if records.broken:
        out.append("")
        out.append("no header, so nothing can track these: "
                   + ", ".join(str(p.relative_to(memory))
                               for p in records.broken[:5]))
    return "\n".join(out).rstrip() + "\n"


def _due(records: levels.Records, now: float) -> list[str]:
    found = levels.due(records, now)
    if not found:
        return []
    out = [f"due: {len(found)} record(s) want you"]
    for item in found:
        out.append(f"  {item.id} — {files.ago(now - item.since)}"
                   + (f", nudge {item.nudges() + 1}" if item.nudges() else ""))
        out.append(f"    at: {item.rel}")
        for field in ("closes-when", "success-when", "due"):
            if value := item.head.get(field):
                out.append(f"    {field}: {value}")
                break
    return out + [""]


def _ladder(records: levels.Records) -> list[str]:
    parts = []
    for name in (*layout.LADDER, *layout.RUNS):
        open_ = [r for r in records.of(name) if not levels.closed(r)]
        if open_:
            parts.append(f"{len(open_)} {name}{'s' if len(open_) > 1 else ''}")
    return [f"ladder: {' · '.join(parts)}", ""] if parts else []


def notes(memory: Path) -> list[Path]:
    """Every note. A note is normally a file; one that acquired a
    screenshot or a script becomes a directory holding `note.md`, the
    same shape every record has."""
    root = Path(memory) / layout.NOTES
    found = []
    for path in sorted(root.rglob("*.md")):
        if path.name == "note.md" or not (path.parent / "note.md").exists():
            found.append(path)
    return found


def _notes(memory: Path, now: float) -> list[str]:
    """Recently touched in full; everything else collapsed to name, age,
    keywords and origin. Retrieval by table of contents — it works
    because the keywords were written by the same reader that later needs
    them."""
    entries = []
    for path in notes(memory):
        head = files.head(path) or {}
        age = now - path.stat().st_mtime
        # a note that became a directory is named by the directory
        rel = (path.parent if path.name == "note.md" else path)
        entries.append((age, rel.relative_to(memory), head))
    entries.sort()
    fresh = [e for e in entries if e[0] <= FRESH_S]
    older = [e for e in entries if e[0] > FRESH_S]

    out = []
    if fresh:
        out.append("fresh memory (read what's relevant):")
        out += [_line(*e) for e in fresh]
        out.append("")
    if older:
        out.append("older memory (scan the keywords, open what matters):")
        out += [_line(*e) for e in older[:MAX_OLDER]]
        if len(older) > MAX_OLDER:
            out.append(f"  ... {len(older) - MAX_OLDER} more, on disk — "
                       "grep memory/ finds any of them")
        out.append("")
    out.append("this is an index, not the memory. Open what looks relevant; "
               "grep for what isn't here.")
    return out


def _line(age: float, rel: Path, head: dict) -> str:
    bits = [files.ago(age)]
    if keywords := head.get("keywords"):
        bits.append(keywords)
    origin = head.get("origin") or "unknown"
    return f"  {rel} ({' — '.join(bits)}) [{origin}]"
