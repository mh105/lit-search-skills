"""Build endpoints.db from the cached OpenAPI swagger files.

Schema:
  endpoints(api, base_url, path, method, category, operation_id, summary, description,
            parameters_json, request_body_json, response_200_json, example_url)
  filter_values(category, value, description)  -- enumerated filter taxonomies

Run:
  python build_endpoints_db.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
DB_PATH = HERE / "endpoints.db"

SPECS = [
    ("graph", "https://api.semanticscholar.org/graph/v1", RAW / "graph_swagger.json"),
    ("recommendations", "https://api.semanticscholar.org/recommendations/v1", RAW / "recommendations_swagger.json"),
]


def _merge_params(path_level: list, method_level: list) -> list:
    by_name: dict[str, dict] = {}
    for p in (path_level or []) + (method_level or []):
        if not isinstance(p, dict):
            continue
        name = p.get("name") or p.get("$ref") or json.dumps(p, sort_keys=True)
        by_name[name] = p
    return list(by_name.values())


def _example_url(api: str, base_url: str, path: str, method: str) -> str:
    if api == "graph":
        if path == "/paper/search":
            return f"{base_url}/paper/search?query=hippocampal+replay&fields=paperId,title,year"
        if path == "/paper/search/bulk":
            return f"{base_url}/paper/search/bulk?query=replay&year=2020-&fields=title,year"
        if path == "/paper/search/match":
            return f"{base_url}/paper/search/match?query=Construction+of+the+Literature+Graph"
        if path == "/paper/{paper_id}":
            return f"{base_url}/paper/DOI:10.1038/nature14066"
        if path == "/paper/batch" and method == "POST":
            return f"{base_url}/paper/batch  -d '{{\"ids\":[\"DOI:...\"]}}'"
        if path == "/paper/{paper_id}/citations":
            return f"{base_url}/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations?fields=title,year"
        if path == "/paper/{paper_id}/references":
            return f"{base_url}/paper/649def34f8be52c8b66281af98ae884c09aef38b/references"
        if path == "/author/search":
            return f"{base_url}/author/search?query=Buzsaki"
        if path == "/author/{author_id}/papers":
            return f"{base_url}/author/1741101/papers"
        if path == "/snippet/search":
            return f"{base_url}/snippet/search?query=place+cells"
    if api == "recommendations":
        if path == "/papers/forpaper/{paper_id}":
            return f"{base_url}/papers/forpaper/DOI:10.1038/nature14066?limit=50"
        if path == "/papers/" and method == "POST":
            return f"{base_url}/papers/  -d '{{\"positivePaperIds\":[\"...\"],\"negativePaperIds\":[]}}'"
    return ""


def build() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api TEXT NOT NULL,
            base_url TEXT NOT NULL,
            path TEXT NOT NULL,
            method TEXT NOT NULL,
            category TEXT,
            operation_id TEXT,
            summary TEXT,
            description TEXT,
            parameters_json TEXT,
            request_body_json TEXT,
            response_200_json TEXT,
            example_url TEXT
        );
        CREATE INDEX idx_endpoints_path ON endpoints(path);
        CREATE INDEX idx_endpoints_api ON endpoints(api);
        CREATE INDEX idx_endpoints_category ON endpoints(category);

        CREATE TABLE filter_values (
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            PRIMARY KEY (category, value)
        );
    """)

    for api, base_url, spec_path in SPECS:
        if not spec_path.exists():
            print(f"[skip] missing {spec_path}")
            continue
        spec = json.loads(spec_path.read_text())
        for path, path_obj in spec.get("paths", {}).items():
            shared_params = path_obj.get("parameters") or []
            for method in ("get", "post", "put", "delete", "patch"):
                op = path_obj.get(method)
                if not op:
                    continue
                params = _merge_params(shared_params, op.get("parameters") or [])
                body_param = next((p for p in params if p.get("in") == "body"), None)
                non_body_params = [p for p in params if p.get("in") != "body"]
                resp_200 = (op.get("responses") or {}).get("200") or {}
                tags = op.get("tags") or []
                cur.execute(
                    """INSERT INTO endpoints
                       (api, base_url, path, method, category, operation_id, summary, description,
                        parameters_json, request_body_json, response_200_json, example_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        api,
                        base_url,
                        path,
                        method.upper(),
                        tags[0] if tags else None,
                        op.get("operationId"),
                        op.get("summary"),
                        op.get("description"),
                        json.dumps(non_body_params, ensure_ascii=False),
                        json.dumps(body_param, ensure_ascii=False) if body_param else None,
                        json.dumps(resp_200, ensure_ascii=False),
                        _example_url(api, base_url, path, method.upper()),
                    ),
                )

    fields_of_study = [
        "Computer Science", "Medicine", "Chemistry", "Biology", "Materials Science",
        "Physics", "Geology", "Psychology", "Art", "History", "Geography", "Sociology",
        "Business", "Political Science", "Economics", "Philosophy", "Mathematics",
        "Engineering", "Environmental Science", "Agricultural and Food Sciences",
        "Education", "Law", "Linguistics",
    ]
    for v in fields_of_study:
        cur.execute(
            "INSERT INTO filter_values(category, value, description) VALUES (?, ?, ?)",
            ("fieldsOfStudy", v, "Top-level S2 field of study (filter on /paper/search and /paper/search/bulk)"),
        )

    publication_types = [
        "Review", "JournalArticle", "CaseReport", "ClinicalTrial", "Conference",
        "Dataset", "Editorial", "LettersAndComments", "MetaAnalysis", "News",
        "Study", "Book", "BookSection",
    ]
    for v in publication_types:
        cur.execute(
            "INSERT INTO filter_values(category, value, description) VALUES (?, ?, ?)",
            ("publicationTypes", v, "S2 publication type taxonomy"),
        )

    citation_intents = [
        ("background", "Cited as background context"),
        ("methodology", "Cited because methodology is used or compared"),
        ("result", "Cited because results are used or compared"),
    ]
    for v, desc in citation_intents:
        cur.execute(
            "INSERT INTO filter_values(category, value, description) VALUES (?, ?, ?)",
            ("intents", v, desc),
        )

    rec_pools = [
        ("recent", "Default. Last ~60 days across all fields of study."),
        ("all-cs", "All Computer Science papers regardless of date. Use only for CS topics."),
    ]
    for v, desc in rec_pools:
        cur.execute(
            "INSERT INTO filter_values(category, value, description) VALUES (?, ?, ?)",
            ("recommendations.from", v, desc),
        )

    bulk_sort = [
        ("paperId:asc", "Default. Stable order; ties broken by paperId."),
        ("paperId:desc", ""),
        ("publicationDate:asc", "Oldest first."),
        ("publicationDate:desc", "Newest first."),
        ("citationCount:asc", "Least-cited first."),
        ("citationCount:desc", "Most-cited first — common for surveying impact."),
    ]
    for v, desc in bulk_sort:
        cur.execute(
            "INSERT INTO filter_values(category, value, description) VALUES (?, ?, ?)",
            ("paper_search_bulk.sort", v, desc),
        )

    con.commit()
    n_endpoints = cur.execute("SELECT COUNT(*) FROM endpoints").fetchone()[0]
    n_filters = cur.execute("SELECT COUNT(*) FROM filter_values").fetchone()[0]
    con.close()
    print(f"Built {DB_PATH} — {n_endpoints} endpoints, {n_filters} filter values")


if __name__ == "__main__":
    build()
