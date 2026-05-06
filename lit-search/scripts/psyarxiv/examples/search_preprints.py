#!/usr/bin/env python3
"""Search PsyArxiv preprints by title / description / tag substring + date range.

The OSF API has no full-text 'q' filter, so 'search' here means:
  - filter[title]      icontains-style substring (phrase order matters)
  - filter[description] icontains on abstract
  - filter[tags]       substring on free-text tags
Combine with --date-from / --date-to to bound recency.

For broader keyword recall, run multiple times with synonym variants and
deduplicate by id (or use the --any flag to OR a comma-separated list of terms
across the chosen field client-side).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from osf_client import OSFClient, flatten_preprint  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--title", help="substring to match in title (phrase, ordered)")
    p.add_argument("--description", help="substring to match in abstract/description")
    p.add_argument("--tag", help="substring to match in tags")
    p.add_argument("--subject", help="subject text or UUID (e.g. 'Cognitive Psychology')")
    p.add_argument("--date-from", help="filter[date_published][gte] (YYYY-MM-DD)")
    p.add_argument("--date-to", help="filter[date_published][lte] (YYYY-MM-DD)")
    p.add_argument("--sort", default="-date_published",
                   help="sort field; default newest first (date_published, -date_published, "
                        "date_modified, title)")
    p.add_argument("--limit", type=int, default=20, help="max records to return (default 20)")
    p.add_argument("--any", dest="any_terms",
                   help="comma-separated terms to OR client-side against the chosen field "
                        "(--title or --description). Each term issues a separate query and "
                        "results are deduplicated by id.")
    p.add_argument("--any-field", choices=["title", "description", "tag"], default="title",
                   help="field to OR over when --any is set (default title)")
    p.add_argument("--count-only", action="store_true",
                   help="print only the total count for the filter combo")
    args = p.parse_args()

    client = OSFClient()

    if args.count_only:
        total = client.get_total(
            title=args.title,
            description=args.description,
            tags=args.tag,
            subjects=args.subject,
            date_published_gte=args.date_from,
            date_published_lte=args.date_to,
        )
        print(json.dumps({"total": total}))
        return 0

    seen: dict[str, dict] = {}

    def run_query(**kwargs) -> None:
        for item in client.search_preprints(
            sort=args.sort, max_results=args.limit, **kwargs
        ):
            pid = item.get("id")
            if pid and pid not in seen:
                seen[pid] = flatten_preprint(item)

    base_kwargs = dict(
        subjects=args.subject,
        date_published_gte=args.date_from,
        date_published_lte=args.date_to,
    )

    if args.any_terms:
        terms = [t.strip() for t in args.any_terms.split(",") if t.strip()]
        for term in terms:
            kw = dict(base_kwargs)
            kw[{"title": "title", "description": "description", "tag": "tags"}[args.any_field]] = term
            run_query(**kw)
            if len(seen) >= args.limit:
                break
    else:
        run_query(
            title=args.title,
            description=args.description,
            tags=args.tag,
            **base_kwargs,
        )

    results = list(seen.values())[: args.limit]
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
