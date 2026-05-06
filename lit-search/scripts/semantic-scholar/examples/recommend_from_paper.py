"""Single-seed recommendations: given ONE good paper, get related papers.

GET /recommendations/v1/papers/forpaper/{paper_id}
  --from recent   (default) pulls from papers published in the last ~60 days across all fields
  --from all-cs   restricts candidate pool to all CS papers (use only for CS topics)

For neuroscience/psych work, --from recent is usually right.

Examples:
  python recommend_from_paper.py DOI:10.1038/nature14066 --limit 50
  python recommend_from_paper.py 649def34f8be52c8b66281af98ae884c09aef38b
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import LEAN_PAPER_FIELDS, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paper_id", help="Any S2 paper ID format: hash, CorpusId:N, DOI:..., ARXIV:..., PMID:..., etc.")
    p.add_argument("--limit", type=int, default=100, help="Max 500")
    p.add_argument("--from", dest="from_pool", choices=["recent", "all-cs"], default="recent")
    p.add_argument("--fields", default=LEAN_PAPER_FIELDS,
                   help="Recommendations endpoints reject `tldr`, so the default omits it.")
    args = p.parse_args()

    res = S2Client().recommend_from_paper(
        args.paper_id, fields=args.fields, limit=args.limit, from_pool=args.from_pool
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
