"""Multi-seed recommendations: curate from a pool of "yes" papers and (optional) "no" papers.

POST /recommendations/v1/papers/
  body: {positivePaperIds: [...], negativePaperIds: [...]}

This is the right endpoint when you have several papers from your reading list that
characterize the topic, and (optionally) a few you know are off-topic to push the
recommendations away from.

Input: text file(s) with one paper ID per line (any S2 ID format), or repeated --pos/--neg flags.

Examples:
  python recommend_from_pool.py --pos-file good.txt --neg-file bad.txt --limit 50
  python recommend_from_pool.py --pos DOI:10.1038/nature14066 --pos PMID:25390967 --limit 30
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from s2_client import LEAN_PAPER_FIELDS, S2Client


def _read_ids(path: str | None) -> list[str]:
    if not path:
        return []
    return [
        ln.strip()
        for ln in Path(path).read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pos", action="append", default=[], help="Positive paper ID (repeatable)")
    p.add_argument("--neg", action="append", default=[], help="Negative paper ID (repeatable)")
    p.add_argument("--pos-file", default=None, help="File: one positive paper ID per line")
    p.add_argument("--neg-file", default=None, help="File: one negative paper ID per line")
    p.add_argument("--limit", type=int, default=100, help="Max 500")
    p.add_argument("--fields", default=LEAN_PAPER_FIELDS,
                   help="Recommendations endpoints reject `tldr`, so the default omits it.")
    args = p.parse_args()

    positives = list(args.pos) + _read_ids(args.pos_file)
    negatives = list(args.neg) + _read_ids(args.neg_file)
    if not positives:
        p.error("at least one positive paper ID is required (--pos or --pos-file)")

    res = S2Client().recommend_from_pool(
        positive_ids=positives,
        negative_ids=negatives,
        fields=args.fields,
        limit=args.limit,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
