"""The header — reading it, and the two formats every clock here reads.

Deliberately not YAML. The header is `key: value`, one per line, no
nesting, so a parser for it is this file and nobody has to install
anything to read a memory file. See spec/README.md.

Two rules the rest of the package depends on:

- reads stop at the closing `---`. A sweep over a thousand records must
  never pay for a thousand bodies.
- writes only ever replace header lines, in place. `set_fields` cannot
  touch a body, which is what lets the sweeper stamp a file the model
  may be editing without a lock (design/clock.md).
"""

import os
import re
import time
from pathlib import Path

FENCE = "---"
KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s?(.*)$")
STAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2}))?")
INTERVAL = re.compile(r"^(\d+(?:\.\d+)?)\s*([smhdw])?$")

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def head(path: Path) -> dict | None:
    """Every header field, or None if the file has no header at all.

    A file in a level directory with no header is never swept — it can't
    be, there is no clock on it — and callers that have somewhere to
    print should say so once. Silence there is how a typo'd `---`
    becomes a commitment nobody is tracking.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            if fh.readline().strip() != FENCE:
                return None
            fields: dict[str, str] = {}
            for line in fh:
                if line.strip() == FENCE:
                    return fields
                if m := KEY.match(line.rstrip("\n")):
                    fields[m.group(1).strip().lower()] = m.group(2).strip()
            return None  # unterminated header: not a record
    except OSError:
        return None


def body(path: Path) -> str:
    """Everything after the header. Only wakes pay for this."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith(FENCE):
        return text
    end = text.find(f"\n{FENCE}", len(FENCE))
    return "" if end < 0 else text[end + len(FENCE) + 2:].lstrip("\n")


def set_fields(path: Path, **fields) -> None:
    """Write header fields, replacing in place and appending what's new.

    Re-reads immediately before writing, and never reconstructs the
    body — worst case under a concurrent edit is a lost stamp, which
    costs one duplicate nudge, and never a lost line of memory.
    """
    fields = {k.replace("_", "-"): v for k, v in fields.items() if v is not None}
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    if not lines or lines[0].strip() != FENCE:
        raise ValueError(f"{path}: no header to write into")
    try:
        close = next(i for i, line in enumerate(lines[1:], 1)
                     if line.strip() == FENCE)
    except StopIteration:
        raise ValueError(f"{path}: unterminated header") from None

    remaining = dict(fields)
    for i in range(1, close):
        if (m := KEY.match(lines[i])) and m.group(1).lower() in remaining:
            key = m.group(1).lower()
            lines[i] = f"{key}: {remaining.pop(key)}"
    for key, value in remaining.items():
        lines.insert(close, f"{key}: {value}")
        close += 1

    tmp = path.with_suffix(path.suffix + ".rouse-tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    os.replace(tmp, path)


def parse_stamp(raw) -> float | None:
    """`YYYY-MM-DD HH:MM` local, or a bare date meaning midnight."""
    if not raw:
        return None
    m = STAMP.match(str(raw).strip())
    if not m:
        return None
    year, month, day, hour, minute = m.groups()
    try:
        return time.mktime((int(year), int(month), int(day),
                            int(hour or 0), int(minute or 0), 0, 0, 0, -1))
    except (ValueError, OverflowError):
        return None


def parse_interval(raw) -> float | None:
    """`30m` / `2h` / `1d`. A bare number is seconds."""
    if not raw:
        return None
    m = INTERVAL.match(str(raw).strip().lower())
    if not m:
        return None
    return float(m.group(1)) * UNITS[m.group(2) or "s"]


def stamp(when: float | None = None) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(when or time.time()))


def ago(seconds: float) -> str:
    """Relative age, because a timestamp in a prompt reads as current
    however old it is (spec/pack.md)."""
    seconds = max(0.0, seconds)
    if seconds < 90:
        return f"{int(seconds)}s ago"
    if seconds < 5400:
        return f"{int(seconds // 60)}m ago"
    if seconds < 172800:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"
