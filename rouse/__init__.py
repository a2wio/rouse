"""rouse — memory with a clock.

A reference implementation of the conventions in `spec/`. Stdlib only,
no dependencies, and small on purpose: the claim being made here is that
this is a set of agreements, not a platform.

    from rouse import levels, pack

    print(pack.render("memory"))
    for item in levels.due(levels.Records("memory")):
        print(item.id, item.reason)
"""

__version__ = "0.1.0"
