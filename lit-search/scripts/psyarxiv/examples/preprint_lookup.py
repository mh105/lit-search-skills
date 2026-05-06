#!/usr/bin/env python3
"""Fetch one PsyArxiv preprint by ID, including contributors.

OSF preprint IDs are 5-character GUIDs (e.g. fu6de). Versioned forms like
'fu6de_v1' also resolve. The script returns the full attribute set plus a
flattened contributor list.

Usage:
  preprint_lookup.py fu6de
  preprint_lookup.py --no-contributors fu6de
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from osf_client import OSFClient, flatten_preprint  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("preprint_id", help="OSF preprint ID (5-char GUID, optionally _vN)")
    p.add_argument("--no-contributors", action="store_true",
                   help="skip the /contributors/ follow-up call")
    p.add_argument("--flat", action="store_true",
                   help="return only the flattened summary (skip relationships/links)")
    args = p.parse_args()

    client = OSFClient()
    envelope = client.get_preprint(args.preprint_id)
    item = envelope["data"]

    out: dict = flatten_preprint(item) if args.flat else {
        "id": item["id"],
        "attributes": item["attributes"],
        "relationships": list(item["relationships"].keys()),
        "links": item.get("links", {}),
    }

    if not args.no_contributors:
        contribs = []
        for c in client.get_contributors(args.preprint_id):
            user = c.get("embeds", {}).get("users", {}).get("data", {}) or {}
            contribs.append({
                "bibliographic": c.get("attributes", {}).get("bibliographic"),
                "permission": c.get("attributes", {}).get("permission"),
                "name": (user.get("attributes") or {}).get("full_name"),
                "user_id": user.get("id"),
            })
        out["contributors"] = contribs

    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
