#!/usr/bin/env python3
"""SCAFFOLD. Copies the reduced JSON this post needs into public/data/.

Deliberately thin. The reduction itself lives in probe/reduce_grid.py, which
scores from raw text and pools by condition; duplicating any of that here would
create a second definition of "correct" that could drift from the one the
sweeps and the RESULTS document use.

    python3 scripts/prepare.py

TODO: wire up. Should shell out to probe/reduce_grid.py for each sweep the post
references, then copy derived/*.json here.
"""
raise SystemExit("scaffold -- not implemented; see blog/README.md")
