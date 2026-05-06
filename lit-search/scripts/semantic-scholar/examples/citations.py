"""Walk citations or references of a paper, paginated.

  --direction citing      papers that CITE this paper (forward)
  --direction referenced  papers this paper CITES (its bibliography, backward)

Edge fields include: contexts (snippet of citing text), intents (background|methodology|result),
isInfluential (S2's influential-citation flag), and the citing/cited paper sub-object.

Examples:
  python citations.py 649def34f8be52c8b66281af98ae884c09aef38b --direction citing --max 200
  python citations.py DOI:10.1038/nature14066 --direction referenced
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import CITING_EDGE_FIELDS, REFERENCED_EDGE_FIELDS, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paper_id")
    p.add_argument("--direction", choices=["citing", "referenced"], default="citing")
    p.add_argument("--max", type=int, default=None, help="Cap on total edges")
    p.add_argument("--fields", default=None,
                   help="Override fields. Defaults to CITING_EDGE_FIELDS or "
                        "REFERENCED_EDGE_FIELDS based on --direction (the two "
                        "endpoints reject each other's namespace).")
    args = p.parse_args()

    client = S2Client()
    if args.direction == "citing":
        fields = args.fields or CITING_EDGE_FIELDS
        edges = list(client.paper_citations_all(args.paper_id, fields=fields, max_results=args.max))
    else:
        fields = args.fields or REFERENCED_EDGE_FIELDS
        edges = list(client.paper_references_all(args.paper_id, fields=fields, max_results=args.max))

    print(json.dumps({
        "paperId": args.paper_id,
        "direction": args.direction,
        "count": len(edges),
        "data": edges,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
