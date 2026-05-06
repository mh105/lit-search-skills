"""Bulk-fetch up to thousands of papers by ID via POST /paper/batch.

Input: file with one paper ID per line, or repeated --id flags.
Auto-batches into chunks of 100. The S2 API returns null for IDs it can't resolve.

Examples:
  python paper_batch.py --id-file pmids.txt --fields paperId,title,year,abstract,authors
  python paper_batch.py --id DOI:10.1038/nature14066 --id PMID:25390967
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from s2_client import DEFAULT_PAPER_FIELDS, S2Client


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
    p.add_argument("--id", action="append", default=[], help="Paper ID (repeatable)")
    p.add_argument("--id-file", default=None, help="File: one paper ID per line")
    p.add_argument("--fields", default=DEFAULT_PAPER_FIELDS)
    p.add_argument("--batch-size", type=int, default=100, help="Per-request batch size; max 500")
    args = p.parse_args()

    ids = list(args.id) + _read_ids(args.id_file)
    if not ids:
        p.error("at least one ID is required (--id or --id-file)")

    res = S2Client().paper_batch(ids, fields=args.fields, batch_size=args.batch_size)
    print(json.dumps({"requested": len(ids), "returned": len(res), "data": res},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
