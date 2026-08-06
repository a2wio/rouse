# the clock

Design, not implementation. `rouse/` is one implementation of this; the
point of writing it down separately is that anyone can write another in
whatever language their agent already runs in, and the files stay
compatible.

## one sweeper, not four

The levels differ in a default interval, a definition of movement, and
the sentence used to wake the agent. That is a table, not four programs.

    level        interval   own clock                 extra
    intention    2h         —
    goal         1h         newest ending underneath  review-every
    action       1d         —
    task         —          —                         no clock; see below
    reminder     per-file   —                         nag re-arm

Beliefs and motivations are not in the table and never join it. They are
context — flat files with no status and no lifecycle (`spec/ladder.md`)
— and the sweeper does not read them at all. A level joins the table
when it has its own condition, not when it exists; running the intention
clock over things that are simply true produces nudges that were never
coming, which is precisely the noise that makes a nudge stop working.

A task has no clock of its own either. It is in the walk because it is
what keeps everything above it quiet, and it is somebody else's runner
that ends it.

The sweeper walks the record tree once and takes a record's level from
the name of its `<type>.md` and its parent from the directory above it
(see `spec/README.md`). One walk, one dictionary, and every "is anything
open under this" question is a lookup rather than a scan.

The arithmetic every row shares:

    due_at = max(last-moved, swept, own clock) + stale-after
    floored at 15 minutes
    skipped entirely while anything open sits inside it

`swept:` in that max is what stops a nudge the agent didn't act on from
repeating every tick. It is a machine field for the same reason.

Header-only reads, always. A sweep over a thousand files should stop at
each closing `---`; the bodies are for the model and cost real time to
read. This is also why every clock-relevant fact lives in the header.

## two readers, one implementation

The due-arithmetic has two callers and they must never disagree:

    the sweeper   wakes the agent when something comes due
    the pack      prints "2 records have stopped moving"

If the pack says two and the daemon nudges about three, the operator
stops believing both. Put the arithmetic in one place and import it
twice — in `rouse/` that is `levels.py`, read by `sweep.py` and
`pack.py`.

## seam one: injection

Where the pack goes in. Every agent has some version of this:

    Claude Code    CLAUDE.md, or a session-start hook that appends
    Codex          AGENTS.md
    Cursor         .cursor/rules
    a raw SDK      the system prompt, or a first user message
    a cron script  a heredoc in the shell script

Rouse does not integrate with any of them. It prints to stdout, and the
wiring is one line in whatever the host already reads. The contract is
just: **the pack is fresh at the moment the session starts**, because
its whole content is time-relative.

A cached pack is a wrong pack. If the host can only read a static file,
regenerate that file at session start rather than on a timer.

## seam two: the wake sink

Where a nudge goes out. Three shapes cover everything, in ascending
order of how much infrastructure they need:

**nudge file** (`--sink file`, the default). The wake is written to
`memory/.rouse/nudges/<stamp>-<type>-<slug>.md` and the *next* pack opens
with it. No delivery, no network, nothing to run but the sweeper — and
if the sweeper isn't running either, tier 1's due-list produces the same
information at session start. This is the honest floor: the wake is
never lost, it is only late.

**exec** (`--sink exec -- ./notify.sh`). The wake is handed to a command
on stdin. This is the seam for anything at all: start a session, send a
message, page someone, write to a queue. A non-zero exit means not
delivered, and the sweeper leaves the record un-stamped so it comes back.

**webhook** (`--sink webhook https://…`). A JSON POST. Same contract as
exec: non-2xx means not delivered.

### what a sink owes you

- **At most once per record per tick.** The agent is being told about a
  thing, not about a row. A record due for two reasons produces one
  wake, and the rarer reason wins — a review question that keeps losing
  to a staleness question is a review that never happens.
- **Failure means not delivered.** Stamp `swept:` after the sink
  succeeds, never before. The cost of a duplicate nudge is annoyance;
  the cost of a swallowed one is the exact failure the ladder exists to
  prevent.
- **Undelivered is countable.** Whatever a sink can't deliver stays
  visible — as a file in `nudges/`, or a line in a probe. A wake that
  failed and left no trace is indistinguishable from a wake that was
  never due, and that gap is where the promises go.

## what the wake should say

The record's body, plus three facts the model cannot infer: which level
this is, how long it has sat still, and which nudge number this is.

    intention/migration-verified — nudge 2, last moved 4h ago
    at: entrypoint/beliefs/motivations/intentions/migration-verified
    closes-when: the staging migration has run once with me watching

    <the body>

The nudge number is the escalation dial. Nothing in the clock decides
tone; it only counts.

**The wake must not sound like a daemon reporting.** Whatever the agent
produces from it should read as the agent thinking of the thing again.
That is a prompt concern rather than a clock concern, but it is where
most of these systems feel like software, so it belongs in the
instruction file — see `skeleton/memory/entrypoint/rouse.md`.

## delivery, and what is deliberately not here

A serious deployment needs a delivery ledger: every wake written down
before it is sent, marked when it lands, retried when it doesn't, and
counted when it is given up on. That is a real component and it is not
in v0 — the `file` sink is a degenerate ledger (the file *is* the
record, and it stays until read) and it is enough to be honest at this
scale.

Also deliberately absent: quiet hours, priorities, dedup across
channels, and anything resembling a scheduler DSL. Every one of them is
a real need for somebody and none of them is needed to prove the thesis.

## the concurrency rule

Two things may write the same record: the sweeper stamping `swept:`, and
the agent editing the body. Neither may clobber the other.

The rule that avoids locking entirely: **the sweeper only ever rewrites
machine fields in the header, by line, in place.** It never rewrites a
body it has read, and it re-reads the header immediately before
stamping. Under that rule the worst case is a lost `swept:` stamp, which
costs one duplicate nudge, and never a lost line of memory.
