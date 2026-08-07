"""The minimum: find the tree, read it, hand over the pack, run the clock.

Everything in here is on the path of the two things rouse actually
promises — `pack` at session start and `sweep` between sessions — so
nothing in here may import from `addons/` or `cli/`. That rule is the
whole point of the directory: an agent that only ever gets handed a
context block and nudged when something stops moving needs these eight
modules and not one more.

    home     where the tree is: --memory, $ROUSE_HOME, ./memory, ~/.rouse
    files    the header, and the two time formats every clock here reads
    layout   what lives where — the layers, the record tree, the inventory
    levels   the walk: records, their parents, and which are due
    context  the layers injected whole — persona, beliefs, motivations
    probes   named commands whose output is the answer
    pack     what the agent is handed at session start
    sweep    the tick loop, and where a wake is delivered

`probes` is in here rather than in `addons/` because the pack's first
block is what the probes read this second, and a pack that quietly
dropped it would still be called a pack while no longer beating the
memory files it claims to beat.
"""
