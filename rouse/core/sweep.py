"""The tick: what is due, deliver it, write down that it went.

The ordering here is the only load-bearing thing in this file. Stamp
AFTER the sink succeeds, never before. A duplicate nudge costs
annoyance; a swallowed one is the exact failure the ladder exists to
prevent, so every ambiguity resolves toward sending again.
"""

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import files, layout, levels


def wake_text(item: levels.Due, now: float) -> str:
    """The record's body, plus the facts the model cannot infer: which
    level, where it sits, how long it sat, which nudge this is."""
    head = f"{item.id} — {item.reason}, last moved {files.ago(now - item.since)}"
    if n := item.nudges():
        head += f", nudge {n + 1}"
    lines = [head, f"at: {item.rel}"]
    for field in ("closes-when", "success-when", "outcome", "due"):
        if value := item.head.get(field):
            lines.append(f"{field}: {value}")
    lines += ["", item.question, "", files.body(item.path).strip()]
    return "\n".join(lines).rstrip() + "\n"


class FileSink:
    """The floor: the wake lands in memory/.rouse/nudges/ and the next
    pack opens with it. Nothing to run, nothing to reach — the wake is
    never lost, only late."""

    def __init__(self, memory: Path):
        self.dir = Path(memory) / layout.SCRATCH / "nudges"

    def __call__(self, item: levels.Due, text: str, now: float) -> bool:
        self.dir.mkdir(parents=True, exist_ok=True)
        name = time.strftime("%Y%m%d-%H%M", time.localtime(now))
        (self.dir / f"{name}-{item.type}-{item.slug}.md").write_text(
            text, encoding="utf-8")
        return True


class ExecSink:
    """The seam for anything at all: the wake on stdin, non-zero means
    not delivered."""

    def __init__(self, argv: list[str]):
        self.argv = argv

    def __call__(self, item, text, now) -> bool:
        try:
            done = subprocess.run(self.argv, input=text, text=True,
                                  timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0


class WebhookSink:
    def __init__(self, url: str):
        self.url = url

    def __call__(self, item, text, now) -> bool:
        payload = json.dumps({"record": item.id, "type": item.type,
                              "at": str(item.rel), "reason": item.reason,
                              "nudge": item.nudges() + 1,
                              "text": text}).encode()
        req = urllib.request.Request(
            self.url, data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return 200 <= res.status < 300
        except (urllib.error.URLError, OSError):
            return False


def record_sent(item: levels.Due, now: float) -> None:
    """Write down that it went out. Reminders re-arm themselves here —
    the loop does it, never the model, because firing is not completing
    and a nudge that went out leaves the file open regardless."""
    if item.type != "reminder":
        files.set_fields(item.path, swept=files.stamp(now),
                         nudges=item.nudges() + 1)
        return

    fires = int(item.head.get("fires") or 0) + 1
    nag = levels.next_nag(item.head, now)
    if nag is None:                                   # a one-shot
        files.set_fields(item.path, status="fired", fired=files.stamp(now))
        return
    when, ceiling = nag
    if when is None:                                  # nagged out
        files.set_fields(item.path, status="expired", fires=fires,
                         ended=ceiling)
        return
    files.set_fields(item.path, status="pending", due=files.stamp(when),
                     fires=fires, set=item.head.get("set")
                     or item.head.get("due"))


def revive_stuck(records: levels.Records, now: float,
                 after: float = 1800) -> list[Path]:
    """A nagging reminder resting at `fired` is stuck — a crash mid-fire,
    a dead daemon. Flip it back so the nudge goes out late instead of
    never. Late is recoverable."""
    revived = []
    for rec in records.of("reminder"):
        if (rec.head.get("status") or "").strip() != "fired":
            continue
        if not files.parse_interval(rec.head.get("nag")):
            continue
        fired = (files.parse_stamp(rec.head.get("fired"))
                 or rec.path.stat().st_mtime)
        if now - fired >= after:
            files.set_fields(rec.path, status="pending")
            revived.append(rec.path)
    return revived


def tick(memory: Path, sink, now: float | None = None) -> list[tuple[str, bool]]:
    """One pass. Returns `(record id, delivered)` for everything due."""
    now = time.time() if now is None else now
    records = levels.Records(memory)
    if revive_stuck(records, now):
        records = levels.Records(memory)   # headers just changed on disk
    out = []
    for item in levels.due(records, now):
        sent = bool(sink(item, wake_text(item, now), now))
        if sent:
            record_sent(item, now)
        out.append((item.id, sent))
    return out


def loop(memory: Path, sink, every: float = 60.0, on_tick=None) -> None:
    while True:
        try:
            results = tick(memory, sink)
        except Exception as exc:                      # a tick must not die
            results = []
            if on_tick:
                on_tick(f"tick failed: {exc!r}")
        if on_tick:
            for record, sent in results:
                on_tick(f"{record}: {'sent' if sent else 'NOT DELIVERED'}")
        time.sleep(every)
