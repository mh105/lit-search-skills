"""Single-seed recommendations: given ONE good paper, get related papers.

Default (--from recent): runs TWO complementary routes and MERGES them:
  1. GET /recommendations/v1/papers/forpaper/{id}?from=recent
       -> papers published in ~the last 60 days FROM TODAY, independent of the
          seed's age (a well-cited seed keeps attracting recent related work).
          Broader net, more peer-reviewed journals, some topical drift.
  2. POST /recommendations/v1/papers/ with positivePaperIds=[seed]
       -> co-citation pool, tighter to the seed's subtopic, preprint-heavy.
The two routes overlap only ~40%, so merging maximizes recall. Results are
deduped (by paperId, then DOI, then title) and each carries a "_sources" tag.
Both routes are recency-biased; for canonical older work cross-check PubMed
find_related_articles.

--from all-cs: bypasses the merge and runs a single pure CS-pool query
  (forpaper?from=all-cs). Use ONLY when the topic is clearly computer science.
  (`from` accepts only `recent` and `all-cs` -- the API has no field-specific
  pool such as "all-neuroscience".)

Exit codes (so the caller can distinguish outcomes):
  0  success -> {"seed", "routes", "count", "recommendedPapers"} JSON on stdout
  2  seed did not resolve in Semantic Scholar -> check the DOI/PMID/arXiv/hash
  3  transient failure (network / rate-limit after the client's retries) -> retry
  4  seed is valid but produced ZERO recommendations (confirmed NOT a rate-limit)

Examples:
  python recommend_from_paper.py DOI:10.1038/ncomms14637 --limit 50
  python recommend_from_paper.py 649def34f8be52c8b66281af98ae884c09aef38b
  python recommend_from_paper.py ARXIV:1706.03762 --from all-cs   # CS topics only
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from s2_client import LEAN_PAPER_FIELDS, S2Client, S2Error

from requests import RequestException


def _die(msg: str, code: int) -> None:
    print(f"recommend_from_paper: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _dedup_key(p: dict) -> str:
    ext = p.get("externalIds") or {}
    return (
        p.get("paperId")
        or ext.get("DOI")
        or (p.get("title") or "").strip().lower()
        or str(id(p))
    )


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("paper_id", help="Any S2 paper ID format: hash, CorpusId:N, DOI:..., ARXIV:..., PMID:..., etc.")
    p.add_argument("--limit", type=int, default=100,
                   help="Max 500, applied PER route (the merged union may be larger)")
    p.add_argument("--from", dest="from_pool", choices=["recent", "all-cs"], default="recent",
                   help="recent (default) = merge from=recent + single-seed pool; "
                        "all-cs = pure CS-pool query, no merge (CS topics only)")
    p.add_argument("--fields", default=LEAN_PAPER_FIELDS,
                   help="Recommendations endpoints reject `tldr`, so the default omits it.")
    args = p.parse_args()

    client = S2Client()

    # Preflight: confirm the seed resolves, and capture its title for provenance.
    # A 4xx here means the ID is bad (exit 2); a transport error means rate-limit
    # or network trouble after the client's retries (exit 3).
    try:
        seed = client.paper_get(args.paper_id, fields="paperId,title,year")
    except S2Error as e:
        _die(f"seed '{args.paper_id}' did not resolve to any Semantic Scholar paper "
             f"({e}). Double-check the DOI / PMID / arXiv ID / S2 hash.", 2)
    except RequestException as e:
        _die(f"could not reach Semantic Scholar to resolve the seed "
             f"(network/rate-limit after retries: {e}). Transient -- retry shortly.", 3)

    # Build the route list: merge for the default, single pure query for all-cs.
    if args.from_pool == "all-cs":
        routes = [("all-cs", lambda: client.recommend_from_paper(
            args.paper_id, fields=args.fields, limit=args.limit, from_pool="all-cs"))]
    else:
        routes = [
            ("recent", lambda: client.recommend_from_paper(
                args.paper_id, fields=args.fields, limit=args.limit, from_pool="recent")),
            ("pool", lambda: client.recommend_from_pool(
                [args.paper_id], fields=args.fields, limit=args.limit)),
        ]

    # Run each route; collect results and per-route errors (a single route
    # failing should not sink the whole call).
    collected = []
    errors = []
    for label, fn in routes:
        try:
            collected.append((label, fn().get("recommendedPapers") or []))
        except (S2Error, RequestException) as e:
            errors.append((label, e))
            print(f"recommend_from_paper: route '{label}' failed ({e}); continuing.",
                  file=sys.stderr)

    # Merge + dedup, preserving order and tagging which route(s) found each paper.
    merged = {}
    order = []
    for label, papers in collected:
        for paper in papers:
            k = _dedup_key(paper)
            if k not in merged:
                rec = dict(paper)
                rec["_sources"] = [label]
                merged[k] = rec
                order.append(k)
            elif label not in merged[k]["_sources"]:
                merged[k]["_sources"].append(label)
    recs = [merged[k] for k in order]

    # Decide the exit signal for an empty result set.
    if not recs:
        route_names = ", ".join(label for label, _ in routes)
        if errors and not collected:
            _die("every recommendation route failed (network/rate-limit after "
                 "retries). Transient -- retry shortly.", 3)
        if errors:
            failed = ", ".join(label for label, _ in errors)
            _die(f"no recommendations returned, but route(s) [{failed}] errored -- this "
                 "may be a transient rate-limit. Retry shortly before concluding the "
                 "seed has none.", 3)
        seed_title = seed.get("title") or args.paper_id
        _die(f"seed resolved ('{seed_title}') but returned ZERO recommendations across "
             f"[{route_names}] -- confirmed NOT a rate-limit (all routes returned "
             "normally). Double-check the seed is the paper you intended.", 4)

    out = {
        "seed": {
            "input": args.paper_id,
            "paperId": seed.get("paperId"),
            "title": seed.get("title"),
            "year": seed.get("year"),
        },
        "routes": [label for label, _ in routes],
        "count": len(recs),
        "recommendedPapers": recs,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
