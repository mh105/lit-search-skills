"""Text snippet search across full-text papers (not the same as paper search).

Returns short text snippets that match the query, with the source paper attached. Useful when
you remember a specific phrasing but not which paper it's from.

Examples:
  python snippet_search.py "place cells encode location"
  python snippet_search.py "default mode network" --fields-of-study Psychology,Medicine --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import NEURO_FIELDS_OF_STUDY, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10, help="Max 1000")
    p.add_argument("--fields-of-study", default=NEURO_FIELDS_OF_STUDY,
                   help="Empty string disables filter.")
    args = p.parse_args()

    fos = args.fields_of_study or None
    print(json.dumps(
        S2Client().snippet_search(args.query, limit=args.limit, fields_of_study=fos),
        indent=2, ensure_ascii=False
    ))


if __name__ == "__main__":
    main()
