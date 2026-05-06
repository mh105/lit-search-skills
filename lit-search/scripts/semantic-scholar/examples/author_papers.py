"""List all papers for a known authorId, paginated.

If you only have a name, run author_search.py first to get the authorId.

Examples:
  python author_papers.py 1741101         # all papers (paginated)
  python author_papers.py 1741101 --max 50
  python author_papers.py 1741101 --max 200 --fields paperId,title,year,venue,citationCount
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import LEAN_PAPER_FIELDS, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("author_id")
    p.add_argument("--max", type=int, default=None, help="Cap on total results")
    p.add_argument("--fields", default=LEAN_PAPER_FIELDS)
    args = p.parse_args()

    client = S2Client()
    papers = list(client.author_papers_all(args.author_id, fields=args.fields, max_results=args.max))
    print(json.dumps({"authorId": args.author_id, "count": len(papers), "data": papers},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
