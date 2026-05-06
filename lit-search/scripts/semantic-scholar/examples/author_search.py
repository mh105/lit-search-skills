"""Resolve an author by name -> list of {authorId, name, affiliations, paperCount, hIndex, ...}.

Use the returned authorId with author_papers.py to enumerate their papers.

Examples:
  python author_search.py "György Buzsáki"
  python author_search.py "Karl Friston" --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import AUTHOR_SEARCH_FIELDS, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--fields", default=AUTHOR_SEARCH_FIELDS)
    args = p.parse_args()

    res = S2Client().author_search(
        args.query, fields=args.fields, limit=args.limit, offset=args.offset
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
