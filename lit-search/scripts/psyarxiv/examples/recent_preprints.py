#!/usr/bin/env python3
"""Newest-first PsyArxiv feed (the primary 'recent preprints' use case).

Pulls the most recently published PsyArxiv preprints, optionally restricted by
date floor, subject, or tag. This is the analogue of bioRxiv's
get_latest_preprints workflow but for psychology.

Defaults:
  --since           none (no date floor)
  --limit           50
  --fields          lean subset (title, description, doi, dates, subjects, tags)

Pagination caps at 100 per page server-side. The script paginates until
--limit is reached or results are exhausted.
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from osf_client import OSFClient, flatten_preprint  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--since", help="date floor (YYYY-MM-DD). e.g. 2026-04-01")
    p.add_argument("--days", type=int,
                   help="convenience: --days 7 sets --since to 7 days ago")
    p.add_argument("--subject", help="subject text or UUID to restrict feed")
    p.add_argument("--tag", help="tag substring to restrict feed")
    p.add_argument("--limit", type=int, default=50, help="max records (default 50)")
    p.add_argument("--full-attrs", action="store_true",
                   help="return full attribute set instead of flattened summary")
    args = p.parse_args()

    since = args.since
    if not since and args.days:
        since = (date.today() - timedelta(days=args.days)).isoformat()

    client = OSFClient()
    items = []
    fields = None  # client default
    if args.full_attrs:
        fields = []  # request all fields by omitting fields[preprints]
        # Note: passing fields=[] means we still send sparse fieldsets but with no
        # restriction — explicit None below to skip the param entirely.
        fields = None

    for item in client.search_preprints(
        subjects=args.subject,
        tags=args.tag,
        date_published_gte=since,
        sort="-date_published",
        max_results=args.limit,
        fields=fields,
    ):
        items.append(item if args.full_attrs else flatten_preprint(item))

    print(json.dumps(items, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
