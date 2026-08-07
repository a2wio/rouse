"""`python3 -m rouse` — the same entry point the `rouse` command is.

Two ways in, one implementation: `pip install` puts `rouse` on the path
via `rouse.cli:main`, and a checkout somebody vendored has no console
script and runs this instead. Anything that behaved differently between
them would be a bug found by exactly the people least able to report it.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
