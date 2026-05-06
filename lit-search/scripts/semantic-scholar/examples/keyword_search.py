"""Keyword search — auto-routes between /paper/search (relevance) and /paper/search/bulk.

Use cases:
  - Default (limit <= 100, no boolean operators): /paper/search relevance ranking with rich nested fields.
  - --bulk OR boolean operators detected (|, +, -, *, ~) OR --max > 100: /paper/search/bulk
    paginated by token, supports sorting, narrower default fields.

Examples:
  python keyword_search.py "hippocampal replay" --year 2018- --limit 25
  python keyword_search.py "hippocampal replay" --bulk --max 500 --sort citationCount:desc
  python keyword_search.py '("place cells" | "grid cells") + entorhinal -review' --bulk --max 200
"""

from __future__ import annotations

import argparse
import json
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import (
    DEFAULT_PAPER_FIELDS,
    LEAN_PAPER_FIELDS,
    NEURO_FIELDS_OF_STUDY,
    S2Client,
)


_BOOLEAN_OPS = re.compile(r"[|*~]|(?<=\S)\s+[+\-]\S")


def _looks_boolean(query: str) -> bool:
    return bool(_BOOLEAN_OPS.search(query))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20, help="Per-page limit for /paper/search (max 100)")
    p.add_argument("--max", type=int, default=None, help="Total results cap for --bulk mode")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--year", default=None, help='e.g. "2020-2024", "2018-", "-2010"')
    p.add_argument("--fields-of-study", default=NEURO_FIELDS_OF_STUDY,
                   help="Comma-separated. Empty string disables. Default tuned for neuro/psych.")
    p.add_argument("--publication-types", default=None,
                   help="e.g. JournalArticle,Review")
    p.add_argument("--venue", default=None)
    p.add_argument("--open-access-pdf", action="store_true")
    p.add_argument("--min-citation-count", type=int, default=None)
    p.add_argument("--fields", default=None,
                   help="Comma-separated S2 fields. Defaults: rich for relevance, lean for bulk.")
    p.add_argument("--bulk", action="store_true", help="Force /paper/search/bulk")
    p.add_argument("--sort", default=None, help="Bulk only. e.g. citationCount:desc, publicationDate:desc")
    args = p.parse_args()

    fos = args.fields_of_study or None
    use_bulk = args.bulk or _looks_boolean(args.query) or (args.max and args.max > 100)
    client = S2Client()

    if use_bulk:
        fields = args.fields or LEAN_PAPER_FIELDS
        results = list(client.paper_bulk_search_all(
            args.query,
            fields=fields,
            sort=args.sort,
            year=args.year,
            publication_types=args.publication_types,
            venue=args.venue,
            fields_of_study=fos,
            open_access_pdf=args.open_access_pdf,
            min_citation_count=args.min_citation_count,
            max_results=args.max,
        ))
        print(json.dumps({"mode": "bulk", "count": len(results), "data": results}, indent=2, ensure_ascii=False))
    else:
        fields = args.fields or DEFAULT_PAPER_FIELDS
        res = client.paper_search(
            args.query,
            fields=fields,
            limit=args.limit,
            offset=args.offset,
            year=args.year,
            publication_types=args.publication_types,
            venue=args.venue,
            fields_of_study=fos,
            open_access_pdf=args.open_access_pdf,
            min_citation_count=args.min_citation_count,
        )
        res["mode"] = "relevance"
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
