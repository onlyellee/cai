#!/usr/bin/env python3
"""Fix misplaced i18n imports in v0.7.4 site-packages files."""
import os

SITE_CAI = "/Users/inteligence-q/.local/python312/python/lib/python3.12/site-packages/cai"

files = [
    "repl/commands/config.py",
    "repl/commands/help.py",
    "repl/commands/run.py",
    "repl/commands/cost.py",
    "repl/commands/model.py",
    "repl/commands/agent.py",
    "repl/commands/memory.py",
    "repl/commands/quickstart.py",
    "repl/commands/env.py",
    "repl/commands/merge.py",
    "repl/commands/history.py",
]

IMPORT_LINE = "from cai.i18n import t\n"

for f in files:
    fp = os.path.join(SITE_CAI, f)
    with open(fp, 'r') as fh:
        lines = fh.readlines()

    # Remove ALL existing i18n import lines (wherever they are)
    cleaned = [l for l in lines if l.strip() != "from cai.i18n import t"]

    # Find the last top-level import line (not indented)
    insert_at = 0
    for i, line in enumerate(cleaned):
        stripped = line.strip()
        if not line[0:1].isspace() and (stripped.startswith('import ') or stripped.startswith('from ')):
            insert_at = i + 1

    # Insert the import at the correct position
    cleaned.insert(insert_at, IMPORT_LINE)

    with open(fp, 'w') as fh:
        fh.writelines(cleaned)

    print(f"  OK {f}: import at line {insert_at + 1}")

print("\nDone!")
