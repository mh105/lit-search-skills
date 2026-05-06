"""Get full details for a single paper by any S2-accepted ID.

Accepted ID formats:
  649def34f8be52c8b66281af98ae884c09aef38b   (Semantic Scholar paperId, 40-char hex)
  CorpusId:215416146
  DOI:10.18653/v1/N18-3011
  ARXIV:2106.15928
  MAG:112218234
  ACL:W12-3903
  PMID:19872477
  PMCID:2323736
  URL:https://...

Examples:
  python paper_lookup.py DOI:10.1038/nature14066
  python paper_lookup.py PMID:25390967 --fields paperId,title,abstract,tldr,openAccessPdf
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import DEFAULT_PAPER_FIELDS, S2Client


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paper_id")
    p.add_argument("--fields", default=DEFAULT_PAPER_FIELDS)
    args = p.parse_args()
    print(json.dumps(S2Client().paper_get(args.paper_id, fields=args.fields), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
