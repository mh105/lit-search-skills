"""Resolve a known paper title to its S2 paperId via /paper/search/match.

Returns the single best title match. Use the resulting paperId as input to other endpoints
(recommend_from_paper, paper_citations, etc).

Examples:
  python title_match.py "Construction of the Literature Graph in Semantic Scholar"
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import DEFAULT_PAPER_FIELDS, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("title")
    p.add_argument("--fields", default=DEFAULT_PAPER_FIELDS)
    args = p.parse_args()

    print(json.dumps(S2Client().paper_match(args.title, fields=args.fields), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
