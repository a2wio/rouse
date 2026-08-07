"""What a minimal install could live without.

Nothing here runs on the `pack` or `sweep` path. Delete this directory
and an agent still gets its context block at session start and still
gets woken when something stops moving; what it loses is every
convenience around writing memory rather than reading it.

    scaffold  making records, moving them, drawing what is on disk
    wire      telling the agent the tree exists, in the file it reads
    check     the linter: what makes a record untrackable, and what
              makes it merely useless

They may import from `core/`. Nothing in `core/` may import from here.
"""
