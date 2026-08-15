"""neon — the memory tree, mirrored into postgres, so recall stops being
a grep.

The pack hands the agent an index: every note it has, collapsed to name,
age and keywords, and it works because the keywords were written by the
same reader that later needs them (`spec/notes.md`). It stops working at
a size — a thousand notes is thirty thousand characters of index, and the
thing you needed was one sentence in the body of one of them.

So this is a second index, and it is only an index:

    the files are the memory. This is a copy you can query.

Sync is one-way and always has been the whole design. Nothing here ever
writes a memory file, nothing here is a source of truth, and a row that
disagrees with a file is wrong by definition — which is why `sync` is
safe to run at any moment and why a lost database costs a re-sync and
nothing else. The alternative — memory that lives in postgres and is
written through — buys nothing the tree doesn't already give (git
history, a diff for what it changed its mind about, an agent that works
with the network down) and costs the one property everything else in
rouse is built on: you can read your agent's memory in a text editor.

**The neon cli, not a driver.** Everything that leaves this machine goes
through `neonctl` and `psql`, both of which the person already installed
and authenticated. That is what keeps `pip install rouse` free of
dependencies (`rouse/plugins/__init__.py`), and it means the credential
handling is somebody else's problem: `neonctl` holds the login, hands
back a connection uri on demand, and this module never stores one, never
prints one, and never puts one on a command line where `ps` can read it.

**Branches are the interesting part.** A neon branch is a copy-on-write
fork of the database, made in a second. Point one agent at a branch and
you can ask what it would have recalled if a fortnight had gone
differently — `fork` below, and the honest limits of it in
`spec/plugins.md`.

This is the tool half; the half the model reads is `../skills/`. It
imports `rouse.…` by name rather than by dots — a plugin's code sits four
directories down, and `from ....core import files` is not a line anybody
should have to count.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from rouse.core import context, files, home, layout, levels, pack

NAME = "neon"

# one schema, fixed. The database may be shared with an application, and
# a memory index that scatters tables through `public` is one nobody can
# drop cleanly. Not configurable: a name you can change is a name that
# has to be discovered before anyone can write a query by hand.
SCHEMA = "rouse"

SQL = Path(__file__).resolve().parent / "schema.sql"

# the two overrides, and neither is a setting. The branch is per-run
# because that is the whole point of a fork — one session against a
# different past, without editing the tree it is reading. The uri is for
# a box that has a secret but no neonctl login: CI, a daemon, a worker
# in a container.
ENV_BRANCH = "ROUSE_NEON_BRANCH"
ENV_URI = "ROUSE_NEON_URI"

# where psql hides when it isn't on the path. libpq is keg-only under
# homebrew, which is the commonest case by a distance.
PSQL_ELSEWHERE = ("/opt/homebrew/opt/libpq/bin/psql",
                  "/usr/local/opt/libpq/bin/psql",
                  "/Applications/Postgres.app/Contents/Versions/latest/bin/psql")

# what a recall prints per hit, before the snippet: the pack's own index
# line. Two shapes for the same thing would be two things to learn.
HIT = "  {path} ({age}{keywords})"


class Fail(Exception):
    """Something outside this process said no, in a way the person can
    fix. Printed as one line, never as a traceback."""


# -- talking to the outside -------------------------------------------


def neon_cli() -> str:
    for name in ("neonctl", "neon"):
        if found := shutil.which(name):
            return found
    raise Fail("no neon cli on the path: `npm i -g neonctl`, then "
               f"`neonctl auth` — or set ${ENV_URI} if this box has a "
               "connection uri and no login")


def psql_bin() -> str:
    if found := shutil.which("psql"):
        return found
    for path in PSQL_ELSEWHERE:
        if Path(path).is_file():
            return path
    raise Fail("no psql on the path — `brew install libpq` (and it is "
               "keg-only, so add its bin to PATH)")


def _out(argv: list[str]) -> str:
    try:
        done = subprocess.run(argv, capture_output=True, text=True)
    except OSError as exc:
        raise Fail(f"{Path(argv[0]).name}: {exc}") from None
    if done.returncode != 0:
        raise Fail(f"{Path(argv[0]).name}: "
                   + (done.stderr.strip() or f"exit {done.returncode}"))
    return done.stdout.strip()


def _project(cfg: dict) -> str:
    """The project id, or the one sentence that fixes its absence. Every
    verb that leaves the machine needs it, and `KeyError` is not an
    instruction."""
    if project := (cfg.get("project") or "").strip():
        return project
    raise Fail(f"no project in {layout.PLUGINS}/{NAME}.md — put the neon "
               "project id there (`neonctl projects list`)")


def uri(cfg: dict) -> str:
    """A connection uri, from the cli that holds the login.

    Asked for every time rather than cached: a cached uri is a credential
    on disk that outlives the session it was got for, and `neonctl` is
    the thing whose job that already is.
    """
    if raw := os.environ.get(ENV_URI):
        return raw.strip()
    # the project first: an unfilled header is the likelier mistake and
    # the one the person can fix without installing anything
    project = _project(cfg)
    argv = [neon_cli(), "connection-string"]
    if branch := cfg.get("branch"):
        argv.append(branch)
    argv += ["--project-id", project,
             "--database-name", cfg.get("database") or "neondb"]
    if role := cfg.get("role"):
        argv += ["--role-name", role]
    return _out(argv)


def pgenv(raw: str) -> dict:
    """A uri, taken apart into the environment libpq reads.

    Not `psql "$URI"`. A connection string on a command line is in `ps`
    for every process on the box and in the shell history of whoever
    copied it, and this one belongs to a database somebody's agent
    remembers things in.
    """
    parts = urlsplit(raw)
    env = {"PGHOST": parts.hostname or "",
           "PGUSER": unquote(parts.username or ""),
           "PGPASSWORD": unquote(parts.password or ""),
           "PGDATABASE": parts.path.lstrip("/") or "neondb",
           "PGSSLMODE": "require"}
    if parts.port:
        env["PGPORT"] = str(parts.port)
    for key, value in parse_qsl(parts.query):
        if key in ("sslmode", "options", "channel_binding"):
            env[f"PG{key.replace('_', '').upper()}"] = value
    return env


def psql(cfg: dict, sql: str, *, variables: dict | None = None) -> str:
    """One round trip. Script on stdin, rows out as tab-separated lines.

    `ON_ERROR_STOP` matters more here than it looks: without it a failed
    statement in the middle of a sync scrolls past and the exit code says
    everything is fine.
    """
    argv = [psql_bin(), "-X", "-q", "-t", "-A", "-F", "\t",
            "-v", "ON_ERROR_STOP=1"]
    for key, value in (variables or {}).items():
        argv += ["-v", f"{key}={value}"]
    argv.append("-f-")
    env = dict(os.environ, **pgenv(uri(cfg)))
    try:
        done = subprocess.run(argv, input=sql, capture_output=True, text=True,
                              env=env)
    except OSError as exc:
        raise Fail(f"psql: {exc}") from None
    if done.returncode != 0:
        # the whole of what psql said, minus the caret art. Keeping only
        # the last line — which was the first version of this — reports a
        # syntax error as a lone `^`
        said = [line for line in done.stderr.strip().splitlines()
                if line.strip() not in ("", "^")]
        raise Fail("psql: " + " / ".join(said[:3] or ["failed"]))
    return done.stdout


# -- the tree, as rows -------------------------------------------------


def rows(memory: Path) -> list[dict]:
    """Every file in the tree that has a header, as one row each.

    Read off `core/` rather than re-walked: the context layers come from
    `context.layers`, the records from `levels.Records`, the notes from
    `pack.notes`. A second walk is a second answer to what a record is,
    and the one that disagrees with the sweeper is the one that silently
    stops indexing something.
    """
    memory = Path(memory)
    found = []
    for module in context.layers(memory):
        found.append(_row(memory, module.path, module.type, module.slug, None))
    records = levels.Records(memory)
    for rec in records.all():
        parent = records.parent(rec)
        found.append(_row(memory, rec.path, rec.type, rec.slug,
                          str(parent.rel) if parent else None))
    for path in pack.notes(memory):
        slug = path.parent.name if path.name == "note.md" else path.stem
        found.append(_row(memory, path, "note", slug, None))
    return found


def _row(memory: Path, path: Path, kind: str, slug: str,
         parent: str | None) -> dict:
    head = files.head(path) or {}
    raw = path.read_bytes()
    keywords = [word.strip() for word in (head.get("keywords") or "").split(",")
                if word.strip()]
    return {"path": Path(path).relative_to(memory).as_posix(),
            "kind": kind, "slug": slug, "parent": parent,
            "status": (head.get("status") or "").strip() or None,
            "keywords": keywords, "head": head, "body": files.body(path),
            # utc, because the row is read by whatever timezone asks
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime(path.stat().st_mtime)),
            # the file's bytes: what makes a re-sync of an unchanged tree
            # a no-op instead of a rewrite of every row
            "sha": hashlib.sha256(raw).hexdigest()}


def copy_lines(found: list[dict]) -> str:
    """The rows as COPY text-format data: one json document per line.

    json.dumps never emits a literal newline or tab inside a string, so
    the only thing COPY needs escaping for is the backslash — which is
    the whole reason the payload is json rather than a column per field.
    """
    return "".join(json.dumps(row, ensure_ascii=False).replace("\\", "\\\\")
                   + "\n" for row in found)


SYNC = """
BEGIN;
CREATE TEMP TABLE incoming (doc jsonb) ON COMMIT DROP;
COPY incoming (doc) FROM stdin;
{data}\\.
WITH parsed AS (
  SELECT r.* FROM incoming, jsonb_to_record(doc)
    AS r(path text, kind text, slug text, parent text, status text,
         keywords text[], head jsonb, body text, mtime timestamptz, sha text)
), written AS (
  INSERT INTO {schema}.memory AS m
    (path, kind, slug, parent, status, keywords, head, body, mtime, sha)
  SELECT path, kind, slug, parent, status, keywords, head, body, mtime, sha
    FROM parsed
  ON CONFLICT (path) DO UPDATE SET
    kind = excluded.kind, slug = excluded.slug, parent = excluded.parent,
    status = excluded.status, keywords = excluded.keywords,
    head = excluded.head, body = excluded.body, mtime = excluded.mtime,
    sha = excluded.sha, synced_at = now()
  WHERE m.sha IS DISTINCT FROM excluded.sha
  RETURNING 1
), gone AS (
  DELETE FROM {schema}.memory
   WHERE path NOT IN (SELECT path FROM parsed)
  RETURNING 1
), ran AS (
  INSERT INTO {schema}.sync (only_row, ran_at, files)
  SELECT true, now(), count(*) FROM parsed
  ON CONFLICT (only_row) DO UPDATE
    SET ran_at = now(), files = excluded.files
  RETURNING 1
)
SELECT (SELECT count(*) FROM parsed), (SELECT count(*) FROM written),
       (SELECT count(*) FROM gone);
COMMIT;
"""

RECALL = """
SELECT 'meta', count(*),
       coalesce((SELECT extract(epoch from ran_at)::bigint
                   FROM {schema}.sync), 0)
  FROM {schema}.memory;
SELECT 'hit', path, kind, coalesce(status, ''),
       array_to_string(keywords, ', '),
       extract(epoch from now() - mtime)::bigint,
       -- tabs and newlines out: the row is read back as tab-separated
       -- fields, and a body containing a tab would otherwise arrive as
       -- an extra column
       translate(ts_headline('english', body,
                   websearch_to_tsquery('english', :'q'),
                   'MaxFragments=1,MaxWords=20,MinWords=8,'
                   'StartSel=<<,StopSel=>>'), E'\\n\\t', '  ')
  FROM {schema}.memory
 WHERE tsv @@ websearch_to_tsquery('english', :'q')
   AND (:'kind' = '' OR kind = :'kind')
   AND (:'open' = '' OR status IN ('open', 'pending', 'running'))
 ORDER BY ts_rank(tsv, websearch_to_tsquery('english', :'q')) DESC,
          mtime DESC
 LIMIT :lim;
"""

STATUS = """
SELECT 'rows', count(*),
       coalesce((SELECT extract(epoch from ran_at)::bigint
                   FROM {schema}.sync), 0)
  FROM {schema}.memory;
SELECT 'kind', kind, count(*) FROM {schema}.memory
 GROUP BY kind ORDER BY count(*) DESC, kind;
"""


# -- the verbs ---------------------------------------------------------


def cmd_init(args, cfg) -> int:
    """The schema, applied. Idempotent — every statement in schema.sql is
    `IF NOT EXISTS`, because the second person to run this is the
    commonest case and it should be boring."""
    psql(cfg, SQL.read_text(encoding="utf-8").replace("{schema}", SCHEMA))
    print(f"schema {SCHEMA} ready on {_target(cfg)}")
    print(f"now: {_run_as()} {NAME} sync")
    return 0


def cmd_sync(args, cfg) -> int:
    found = rows(args.memory)
    if not found:
        raise Fail(f"nothing to sync: no memory files under {args.memory}")
    out = psql(cfg, SYNC.format(schema=SCHEMA, data=copy_lines(found)))
    line = [part for part in out.strip().splitlines() if part]
    total, written, gone = (line[-1].split("\t") + ["0", "0"])[:3] if line \
        else ("0", "0", "0")
    print(f"{total} files · {written} changed · {gone} removed "
          f"· {_target(cfg)}")
    return 0


def cmd_recall(args, cfg) -> int:
    """Ask the index. Prints paths, never bodies — the snippet is there to
    decide what to open, and the file is what gets read.

    It also says when it is behind. An index that quietly answers out of
    a week-old copy is worse than no index: the agent's own rule is that
    a stale reading means go and check, never "no news"
    (`spec/probes.md`).
    """
    out = psql(cfg, RECALL.format(schema=SCHEMA),
               variables={"q": args.query, "lim": max(1, args.limit),
                          "kind": args.kind or "", "open": "1" if args.open else ""})
    newest, hits = 0.0, []
    for line in out.splitlines():
        parts = line.split("\t")
        if parts[0] == "meta":
            ran = int(parts[2] or 0)
            newest = max((path.stat().st_mtime for path in _files(args.memory)),
                         default=0.0)
            if newest > ran:
                # the age of the newest file, not the size of the gap:
                # "behind by 0s ago" was the first version of this line
                print(f"index is behind — something was written "
                      f"{files.ago(time.time() - newest)} and isn't in it. "
                      f"`{_run_as()} {NAME} sync` first")
        elif parts[0] == "hit":
            # padded and cut to the six the printer wants: a stray tab in
            # somebody's keywords line should cost a squashed snippet,
            # not a traceback in the middle of a search
            hits.append((parts[1:7] + [""] * 6)[:6])
    if not hits:
        print(f"nothing for {args.query!r}"
              + (f" in {args.kind}s" if args.kind else ""))
        return 1
    for path, kind, status, keywords, age, snippet in hits:
        mark = f"{kind}" + (f", {status}" if status else "")
        print(HIT.format(path=path, age=files.ago(float(age)),
                         keywords=f" — {keywords}" if keywords else "")
              + f" [{mark}]")
        if snippet.strip():
            print(f"      {snippet.strip()}")
    return 0


def cmd_status(args, cfg) -> int:
    """One line, because the reason this exists is to be a probe:

        ```probe
        name: memory-index
        tier: demand
        cmd:  rouse neon status
        ```
    """
    out = psql(cfg, STATUS.format(schema=SCHEMA))
    total, synced, kinds = "0", 0, []
    for line in out.splitlines():
        parts = line.split("\t")
        if parts[0] == "rows":
            total, synced = parts[1], int(parts[2] or 0)
        elif parts[0] == "kind":
            kinds.append(f"{parts[2]} {parts[1]}")
    age = files.ago(time.time() - synced) if synced else "never"
    print(f"{total} rows · {', '.join(kinds[:4])} · synced {age} "
          f"· {_target(cfg)}")
    return 0


def cmd_fork(args, cfg) -> int:
    """A branch of the database: the agent's memory as it is now, forked.

    What this forks is the index, not the tree — the files are still the
    files, and two agents pointed at two branches of one tree read the
    same memory through different copies of it. Forking the memory itself
    is that plus a fork of the tree, which git already does; the pair is
    the experiment, and `spec/plugins.md` says so at length.
    """
    argv = [neon_cli(), "branches", "create", "--project-id", _project(cfg),
            "--name", args.name]
    if parent := (cfg.get("branch") or ""):
        argv += ["--parent", parent]
    _out(argv)
    print(f"branch {args.name} — off {parent or 'the default branch'}")
    print(f"one session against it:  {ENV_BRANCH}={args.name} "
          f"{_run_as()} {NAME} recall …")
    print(f"this tree, for good:     branch: {args.name}  "
          f"in {layout.PLUGINS}/{NAME}.md")
    return 0


def cmd_branches(args, cfg) -> int:
    print(_out([neon_cli(), "branches", "list",
                "--project-id", _project(cfg)]))
    return 0


def cmd_sql(args, cfg) -> int:
    """The escape hatch, read-only.

    Read-only because the index is derived: an UPDATE here would survive
    exactly until the next sync and be believed in the meantime. Anything
    that should be true belongs in a file.
    """
    statement = args.statement.strip().rstrip(";")
    print(psql(cfg, f"BEGIN READ ONLY;\n{statement};\nCOMMIT;").rstrip())
    return 0


# -- plumbing ----------------------------------------------------------


def _files(memory: Path) -> set[Path]:
    """The same set `rows()` builds, without opening anything. Stats only,
    because this runs on the way to every recall and all it has to answer
    is whether something is newer than the index."""
    memory = Path(memory)
    seen = {module.path for module in context.layers(memory)}
    seen |= {rec.path for rec in levels.Records(memory).all()}
    return seen | set(pack.notes(memory))


def _target(cfg: dict) -> str:
    """Which database this ran against, with no credential in it."""
    if os.environ.get(ENV_URI):
        return f"${ENV_URI}"
    where = cfg.get("branch") or "default branch"
    return f"{cfg.get('project', '?')}/{where}"


def _run_as() -> str:
    return "rouse" if shutil.which("rouse") else "python3 -m rouse"


def config(memory: Path) -> dict:
    """This tree's answers: the header of its `neon.md`, with the two
    per-run overrides applied."""
    from rouse import plugins        # local: the layer imports us lazily
    cfg = dict(plugins.settings(memory, NAME))
    if branch := os.environ.get(ENV_BRANCH):
        cfg["branch"] = branch.strip()
    return cfg


VERBS = {"init": cmd_init, "sync": cmd_sync, "recall": cmd_recall,
         "status": cmd_status, "fork": cmd_fork, "branches": cmd_branches,
         "sql": cmd_sql}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="rouse neon",
        description="the memory tree, mirrored into postgres, so recall "
                    "stops being a grep. The files stay the memory; this "
                    "is a copy you can query")
    ap.add_argument("--memory", default=None, type=Path)
    sub = ap.add_subparsers(dest="verb", required=True)
    sub.add_parser("init", help=f"create the {SCHEMA} schema")
    sub.add_parser("sync", help="the tree, into the index")
    p = sub.add_parser("recall", help="search the index; prints paths")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--kind", help="note, intention, task, belief, …")
    p.add_argument("--open", action="store_true",
                   help="only records that haven't ended")
    sub.add_parser("status", help="rows, kinds, how old the index is")
    p = sub.add_parser("fork", help="a neon branch of the index")
    p.add_argument("name")
    sub.add_parser("branches", help="the branches of this project")
    p = sub.add_parser("sql", help="read-only sql against the index")
    p.add_argument("statement")
    return ap


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    args.memory = home.resolve(args.memory)
    if not args.memory.is_dir():
        print(f"no memory tree at {home.display(args.memory)}", file=sys.stderr)
        return 2
    cfg = config(args.memory)
    if not cfg and not os.environ.get(ENV_URI):
        print(f"{NAME} isn't on in this tree: `{_run_as()} plugin add {NAME} "
              "project=<neon project id>`", file=sys.stderr)
        return 2
    try:
        return VERBS[args.verb](args, cfg)
    except Fail as exc:
        print(f"{NAME}: {exc}", file=sys.stderr)
        return 2
