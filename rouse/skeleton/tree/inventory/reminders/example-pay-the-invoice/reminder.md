---
due: 2099-01-01 09:00
status: pending
---

Placeholder — an example reminder, dated far enough out that it never
fires. Delete this directory; a real one carries a real `due:`.

When it comes due you are woken with this body, and what you say is
delivered as you reaching out — not as a system reporting. Then close it
(`status: done`) or set a fresh `due:` to re-arm it.

For something a person has to actually do, add `nag: 2h`: it re-arms
itself until they say it's done. Firing is not completing.
