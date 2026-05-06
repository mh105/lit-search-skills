#!/usr/bin/env python3
"""Enumerate PsyArxiv's subject taxonomy (~234 entries).

PsyArxiv uses the bepress Digital Commons taxonomy. The endpoint returns each
subject with `id` (UUID), `text` (display name), and `taxonomy_name`. Subjects
form a hierarchy; `parent` and `children` relationships expose the tree.

filter[subjects] on /preprints/ accepts either id or text — both alias to the
same constraint server-side.

Usage:
  list_subjects.py                 # human-readable preview
  list_subjects.py --json          # full JSON dump (single array)
  list_subjects.py --dump PATH     # write JSON to PATH and report count
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from osf_client import OSFClient  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true", help="print full JSON array")
    p.add_argument("--dump", help="write JSON array to PATH")
    p.add_argument("--limit", type=int, help="cap output (debug only)")
    args = p.parse_args()

    client = OSFClient()
    rows = []
    for s in client.list_subjects():
        rows.append({
            "id": s["id"],
            "text": s["attributes"].get("text"),
            "taxonomy_name": s["attributes"].get("taxonomy_name"),
            "parent_id": (s.get("relationships", {}).get("parent", {}).get("data") or {}).get("id"),
        })
        if args.limit and len(rows) >= args.limit:
            break

    if args.dump:
        Path(args.dump).write_text(json.dumps(rows, indent=2, ensure_ascii=False))
        print(f"wrote {len(rows)} subjects to {args.dump}")
        return 0

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    print(f"{len(rows)} subjects")
    for r in rows[:30]:
        parent = f" <- {r['parent_id']}" if r["parent_id"] else ""
        print(f"  {r['id']}  {r['text']}{parent}")
    if len(rows) > 30:
        print(f"  ... ({len(rows) - 30} more)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
