# the persona — how it talks, and why most trees haven't got one

    memory/persona.md

One file, at the root, above both halves. It says how this agent talks:
register, length, what it sounds like and what it never sounds like. It
does not say what the agent knows — that is a belief — and it does not
say what is pushing it this week, which is a motivation.

    ---
    ---
    You are a front-end developer talking to a client who is not
    technical. Short answers. Say what you'd do, not the four options.
    No hedging into "it depends" without then saying what it depends on.
    Never apologise for asking a question.

That is the whole format: a body, and a header with nothing of the
writer's in it. Same as a belief, for the same reason — it is injected
whole on every turn, so nothing ever looks it up, and the fence is there
empty only so a wrapper can stamp `origin:` (`provenance.md`).

**No clock, no status, no keywords.** A voice that is finished on Tuesday
was an intention. Keywords on it would say "this gets retrieved" about
the one file that is never gated by anything; `check` warns about both.

## it is a layer, not a field

The persona sits above `entrypoint/` rather than inside it because it is
what the layers below are read *through*. The same belief — "writing code
starts in plan mode" — produces a different sentence in a different
voice, and the voice is not a fact about the world, so it is not a belief.
Reading the tree downward now reads: this is who you are, this is what you
hold true, this is what reached you, this is what you are doing about it.

    persona.md         who is talking            ┐ context: injected
    entrypoint/                                  │ whole, every session
      beliefs/         what is true              │
        motivations/   what arrived              ┘
          intentions/  what you're doing         ← records, with clocks

**One per tree, and the path is how that is said.** There is no slug and
no `persona-<slug>.md`: two voices in one memory is two agents, and the
second one wants its own tree (`home.md`). A `persona.md` anywhere but
the root is a lint warning rather than a second persona, because nothing
will ever inject it — the layer is a fixed path, so a file in the wrong
place is not misconfigured, it is invisible.

## optional, and that is a rule

**An absent `persona.md` is not a finding.** Not a warning, not an empty
block in the pack, not a default personality invented to fill the space.
Every implementation must treat "no persona" as an ordinary tree.

The split is what kind of agent it is:

**A repo-scoped agent skips it.** A code reviewer wired into CI, a
migration checker, an agent that reads a diff and writes a comment — its
register comes from whatever wraps it, and there is nothing about how it
talks that would survive being written down. Writing one for it costs
tokens on every turn to say something nobody was unsure about.

**An agent a person talks to ships one.** A support agent, a pair
programmer, a friend, anything with a voice somebody would recognise or
complain about. For those it is the highest-value file in the tree,
because it is the one thing that is wrong in every single reply when it
is wrong, and the modularity argument applies harder here than anywhere:
a register you can edit in one file is a register you will actually fix.

The tell, when you are unsure: **would a stranger reading a reply be able
to say it came from this agent and not another one?** If yes, that
difference is worth a file. If no, you are about to write "be helpful and
concise" and pay for it forever.

## the skeleton does not ship one

Every other example in `skeleton/memory/` is prefixed `example-`, and
that prefix is what makes it safe: `rouse.md` can say "nothing in them is
something you believe — never act on one", and a reader can see which
files it means.

**That prefix cannot apply here.** The persona is found by path, so a
placeholder would have to be named exactly `persona.md` to be read at
all, and then it is an unmarked instruction about how to talk, injected
whole into every session of a tree that has just been created. The
skeleton would be shipping a personality.

So the layer is documented in `rouse.md` and in the README, `rouse init`
prints one line saying it exists, and `rouse new persona` writes it. The
cost is that it is the one part of the shape `rouse tree` does not show
you on the first run. That is the right trade: a missing file teaches
less than a wrong file misleads.
