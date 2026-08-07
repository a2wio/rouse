---
---

Placeholder — an example belief. Delete it, or rewrite it as one of
yours; it is a flat file, and the only thing in `beliefs/` that isn't a
file like this one is `motivations/`, the layer below.

Deployments always happen with no downtime. A rollout that needs a
maintenance window is a rollout that has gone wrong somewhere earlier —
treat the window as the bug, not as the plan.

Migrations are the usual reason this gets broken, so they are expand,
backfill, contract, in three separate deploys, and never a rename.
