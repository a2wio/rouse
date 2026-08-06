"""Named commands whose output is the answer.

`probes.md` is re-read on every render, so a probe written this minute
renders in the next pack with nothing restarted. A probe you have to
deploy is a probe nobody adds.

The one rule with no exceptions: a probe that fails, times out or blows
the budget renders `<unknown>`, and `<unknown>` never, ever degrades
into a remembered value. See spec/probes.md.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

FENCE = re.compile(r"^```probe\s*$")
UNKNOWN = "<unknown>"
BUDGET_MS = 150          # the whole pack tier shares this
TTL_S = 300              # default reuse window for demand probes


class Probe:
    def __init__(self, name, tier, cmd, ttl=None, unknown_ok=False):
        self.name = name
        self.tier = tier
        self.cmd = cmd
        self.ttl = ttl
        self.unknown_ok = unknown_ok


def read(path: Path) -> list[Probe]:
    """Every probe in a probes.md. Anything outside a fence is prose."""
    if not path.exists():
        return []
    found, block = [], None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if block is None:
            if FENCE.match(line):
                block = {}
            continue
        if line.strip() == "```":
            if block.get("name") and block.get("cmd"):
                found.append(Probe(
                    block["name"], (block.get("tier") or "demand").lower(),
                    block["cmd"], ttl=_int(block.get("ttl")),
                    unknown_ok=(block.get("unknown-ok", "")
                                .lower() in ("yes", "true"))))
            block = None
            continue
        if m := re.match(r"^([a-z-]+):\s*(.*)$", line.strip()):
            block[m.group(1)] = m.group(2).strip()
    return found


def _int(raw):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def run(probe: Probe, memory: Path, timeout: float) -> str:
    env = dict(os.environ, MEMORY=str(memory), ROOT=str(memory.parent))
    try:
        out = subprocess.run(probe.cmd, shell=True, cwd=memory, env=env,
                             capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return UNKNOWN
    if out.returncode != 0:
        return UNKNOWN
    value = " ".join(out.stdout.strip().splitlines()).strip()
    return value or "<empty>"


def readings(memory: Path, tier: str = "pack",
             budget_ms: int = BUDGET_MS) -> list[tuple[str, str]]:
    """Run one tier and return `(name, value)`, in file order.

    The budget is shared across the tier, not per probe: what matters is
    what the whole thing costs on the session-start path. Whatever the
    budget runs out on renders `<unknown>`, which is the correct answer
    — it means go check.
    """
    probes = [p for p in read(memory / "probes.md") if p.tier == tier]
    if tier != "pack":
        return [(p.name, _cached(p, memory)) for p in probes]
    deadline = time.monotonic() + budget_ms / 1000
    out = []
    for probe in probes:
        left = deadline - time.monotonic()
        out.append((probe.name,
                    run(probe, memory, left) if left > 0.005 else UNKNOWN))
    return out


def _cached(probe: Probe, memory: Path) -> str:
    """Demand probes may reuse a reading for `ttl` seconds — they leave
    the machine, and the subject rarely changes inside a minute."""
    store = memory / ".rouse" / "probes.json"
    ttl = probe.ttl if probe.ttl is not None else TTL_S
    now = time.time()
    try:
        cache = json.loads(store.read_text())
    except (OSError, ValueError):
        cache = {}
    hit = cache.get(probe.name)
    if hit and now - hit.get("at", 0) < ttl and hit.get("value") != UNKNOWN:
        return hit["value"]
    value = run(probe, memory, timeout=10)
    cache[probe.name] = {"at": now, "value": value}
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(cache))
    return value
