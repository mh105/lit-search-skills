"""Semantic Scholar API client for the lit-search skill.

Endpoints covered:
  Graph API (https://api.semanticscholar.org/graph/v1):
    /paper/search            relevance keyword search (limit <= 100)
    /paper/search/bulk       bulk filter + boolean query (1000/page, token-paginated)
    /paper/search/match      closest title match (single result)
    /paper/autocomplete      query autocomplete suggestions
    /paper/{id}              paper details
    /paper/batch             POST batch up to 500 IDs
    /paper/{id}/citations    citing-paper edges (offset-paginated)
    /paper/{id}/references   referenced-paper edges (offset-paginated)
    /snippet/search          text snippet match in full text
    /author/search           name-based author search
    /author/{id}             author details
    /author/{id}/papers      author's papers (offset-paginated)
    /author/batch            POST batch authors

  Recommendations API (https://api.semanticscholar.org/recommendations/v1):
    /papers/forpaper/{id}    single-seed recommendations (from=recent|all-cs)
    /papers/                 POST multi-seed (positivePaperIds + negativePaperIds)

Authentication: header `x-api-key`. Set S2_API_KEY in env (or .env in any parent dir).
Rate limit with key: 1 RPS across all endpoints. Without key: shared 5000/5min pool.

See ./references/ for the canonical endpoint catalog (markdown + endpoints.db).
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterator, Optional, Sequence

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


def _load_dotenv_if_present() -> None:
    cwd = os.getcwd()
    for _ in range(5):
        candidate = os.path.join(cwd, ".env")
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            except OSError:
                pass
            return
        nxt = os.path.dirname(cwd)
        if nxt == cwd:
            break
        cwd = nxt


_load_dotenv_if_present()


GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"
RECS_BASE = "https://api.semanticscholar.org/recommendations/v1"

# Rich field set, with `tldr`. Accepted by /paper/search (relevance), /paper/{id},
# /paper/search/match, and /paper/batch. Reject `tldr` on /paper/search/bulk,
# /author/{id}/papers, and the recommendations endpoints — use LEAN_PAPER_FIELDS
# (or any custom set without `tldr`) for those.
DEFAULT_PAPER_FIELDS = (
    "paperId,title,authors,year,venue,publicationVenue,publicationTypes,"
    "publicationDate,citationCount,influentialCitationCount,referenceCount,"
    "isOpenAccess,openAccessPdf,externalIds,fieldsOfStudy,s2FieldsOfStudy,"
    "abstract,tldr"
)

# Lean, portable field set. No `tldr` so it works on every paper-returning
# endpoint, including bulk search, author papers, and recommendations.
LEAN_PAPER_FIELDS = (
    "paperId,title,authors,year,venue,citationCount,externalIds,openAccessPdf"
)

# Full author detail. `aliases` is accepted by /author/{id} and /author/batch
# but rejected by /author/search — use AUTHOR_SEARCH_FIELDS for that endpoint.
DEFAULT_AUTHOR_FIELDS = (
    "authorId,name,aliases,affiliations,homepage,paperCount,citationCount,hIndex,url"
)

AUTHOR_SEARCH_FIELDS = (
    "authorId,name,affiliations,homepage,paperCount,citationCount,hIndex,url"
)

# Edge fields are direction-specific: /citations accepts `citingPaper.*` only,
# /references accepts `citedPaper.*` only. Mixing both directions in a single
# request returns 400 from either endpoint.
CITING_EDGE_FIELDS = (
    "contexts,intents,isInfluential,"
    "citingPaper.paperId,citingPaper.title,citingPaper.year,citingPaper.authors,"
    "citingPaper.venue,citingPaper.citationCount,citingPaper.externalIds"
)

REFERENCED_EDGE_FIELDS = (
    "contexts,intents,isInfluential,"
    "citedPaper.paperId,citedPaper.title,citedPaper.year,citedPaper.authors,"
    "citedPaper.venue,citedPaper.citationCount,citedPaper.externalIds"
)

PUBLICATION_TYPES = (
    "Review", "JournalArticle", "CaseReport", "ClinicalTrial", "Conference",
    "Dataset", "Editorial", "LettersAndComments", "MetaAnalysis", "News",
    "Study", "Book", "BookSection",
)

FIELDS_OF_STUDY = (
    "Computer Science", "Medicine", "Chemistry", "Biology", "Materials Science",
    "Physics", "Geology", "Psychology", "Art", "History", "Geography",
    "Sociology", "Business", "Political Science", "Economics", "Philosophy",
    "Mathematics", "Engineering", "Environmental Science",
    "Agricultural and Food Sciences", "Education", "Law", "Linguistics",
)

NEURO_FIELDS_OF_STUDY = "Biology,Medicine,Psychology"


class S2Error(RuntimeError):
    pass


class S2Client:
    def __init__(
        self,
        api_key: Optional[str] = None,
        graph_base: str = GRAPH_BASE,
        recs_base: str = RECS_BASE,
        retries: int = 5,
        backoff_factor: float = 1.5,
        backoff_jitter: float = 0.5,
        min_interval: float = 0.0,
        timeout: float = 60.0,
    ):
        self.api_key = (
            api_key
            or os.getenv("S2_API_KEY")
            or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        )
        self.graph_base = graph_base.rstrip("/")
        self.recs_base = recs_base.rstrip("/")
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_request_at = 0.0
        self.session = Session()
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            backoff_jitter=backoff_jitter,
            respect_retry_after_header=True,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _headers(self) -> dict:
        h = {"User-Agent": "lit-search-skill/0.1 (semantic-scholar)"}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        delta = time.monotonic() - self._last_request_at
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last_request_at = time.monotonic()

    def _get(self, base: str, path: str, params: Optional[dict] = None) -> Any:
        self._throttle()
        url = f"{base}{path}"
        r = self.session.get(
            url, headers=self._headers(), params=_clean(params), timeout=self.timeout
        )
        if r.status_code >= 400:
            raise S2Error(f"GET {url} -> {r.status_code}: {r.text[:500]}")
        return r.json()

    def _post(
        self,
        base: str,
        path: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> Any:
        self._throttle()
        url = f"{base}{path}"
        r = self.session.post(
            url,
            headers=self._headers(),
            params=_clean(params),
            json=json_body,
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise S2Error(f"POST {url} -> {r.status_code}: {r.text[:500]}")
        return r.json()

    def paper_search(
        self,
        query: str,
        *,
        fields: str = DEFAULT_PAPER_FIELDS,
        limit: int = 20,
        offset: int = 0,
        year: Optional[str] = None,
        publication_types: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        open_access_pdf: bool = False,
        min_citation_count: Optional[int] = None,
        publication_date_or_year: Optional[str] = None,
    ) -> dict:
        if limit > 100:
            raise ValueError("paper_search limit must be <= 100; use paper_bulk_search for larger sweeps")
        params = {
            "query": query,
            "fields": fields,
            "limit": limit,
            "offset": offset,
            "year": year,
            "publicationTypes": publication_types,
            "venue": venue,
            "fieldsOfStudy": fields_of_study,
            "minCitationCount": min_citation_count,
            "publicationDateOrYear": publication_date_or_year,
        }
        if open_access_pdf:
            params["openAccessPdf"] = ""
        return self._get(self.graph_base, "/paper/search", params)

    def paper_bulk_search(
        self,
        query: str,
        *,
        fields: str = LEAN_PAPER_FIELDS,
        sort: Optional[str] = None,
        token: Optional[str] = None,
        year: Optional[str] = None,
        publication_types: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        open_access_pdf: bool = False,
        min_citation_count: Optional[int] = None,
        publication_date_or_year: Optional[str] = None,
    ) -> dict:
        params = {
            "query": query,
            "fields": fields,
            "sort": sort,
            "token": token,
            "year": year,
            "publicationTypes": publication_types,
            "venue": venue,
            "fieldsOfStudy": fields_of_study,
            "minCitationCount": min_citation_count,
            "publicationDateOrYear": publication_date_or_year,
        }
        if open_access_pdf:
            params["openAccessPdf"] = ""
        return self._get(self.graph_base, "/paper/search/bulk", params)

    def paper_bulk_search_all(
        self,
        query: str,
        *,
        max_results: Optional[int] = None,
        **kwargs,
    ) -> Iterator[dict]:
        token = None
        emitted = 0
        while True:
            page = self.paper_bulk_search(query, token=token, **kwargs)
            for p in page.get("data") or []:
                yield p
                emitted += 1
                if max_results is not None and emitted >= max_results:
                    return
            token = page.get("token")
            if not token:
                return

    def paper_match(self, query: str, *, fields: str = DEFAULT_PAPER_FIELDS) -> dict:
        return self._get(
            self.graph_base, "/paper/search/match", {"query": query, "fields": fields}
        )

    def paper_autocomplete(self, query: str) -> dict:
        return self._get(self.graph_base, "/paper/autocomplete", {"query": query})

    def paper_get(self, paper_id: str, *, fields: str = DEFAULT_PAPER_FIELDS) -> dict:
        return self._get(self.graph_base, f"/paper/{paper_id}", {"fields": fields})

    def paper_batch(
        self,
        ids: Sequence[str],
        *,
        fields: str = DEFAULT_PAPER_FIELDS,
        batch_size: int = 100,
    ) -> list:
        out: list = []
        ids = list(ids)
        for i in range(0, len(ids), batch_size):
            chunk = ids[i : i + batch_size]
            res = self._post(
                self.graph_base,
                "/paper/batch",
                params={"fields": fields},
                json_body={"ids": chunk},
            )
            out.extend(res or [])
        return out

    def paper_citations(
        self,
        paper_id: str,
        *,
        fields: str = CITING_EDGE_FIELDS,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        return self._get(
            self.graph_base,
            f"/paper/{paper_id}/citations",
            {"fields": fields, "limit": limit, "offset": offset},
        )

    def paper_references(
        self,
        paper_id: str,
        *,
        fields: str = REFERENCED_EDGE_FIELDS,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        return self._get(
            self.graph_base,
            f"/paper/{paper_id}/references",
            {"fields": fields, "limit": limit, "offset": offset},
        )

    def paper_citations_all(
        self,
        paper_id: str,
        *,
        fields: str = CITING_EDGE_FIELDS,
        max_results: Optional[int] = None,
    ) -> Iterator[dict]:
        yield from self._paginate_offset(
            f"/paper/{paper_id}/citations", {"fields": fields}, max_results
        )

    def paper_references_all(
        self,
        paper_id: str,
        *,
        fields: str = REFERENCED_EDGE_FIELDS,
        max_results: Optional[int] = None,
    ) -> Iterator[dict]:
        yield from self._paginate_offset(
            f"/paper/{paper_id}/references", {"fields": fields}, max_results
        )

    def snippet_search(
        self,
        query: str,
        *,
        limit: int = 10,
        fields_of_study: Optional[str] = None,
    ) -> dict:
        return self._get(
            self.graph_base,
            "/snippet/search",
            {"query": query, "limit": limit, "fieldsOfStudy": fields_of_study},
        )

    def author_search(
        self,
        query: str,
        *,
        fields: str = AUTHOR_SEARCH_FIELDS,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        return self._get(
            self.graph_base,
            "/author/search",
            {"query": query, "fields": fields, "limit": limit, "offset": offset},
        )

    def author_get(self, author_id: str, *, fields: str = DEFAULT_AUTHOR_FIELDS) -> dict:
        return self._get(
            self.graph_base, f"/author/{author_id}", {"fields": fields}
        )

    def author_papers(
        self,
        author_id: str,
        *,
        fields: str = LEAN_PAPER_FIELDS,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        return self._get(
            self.graph_base,
            f"/author/{author_id}/papers",
            {"fields": fields, "limit": limit, "offset": offset},
        )

    def author_papers_all(
        self,
        author_id: str,
        *,
        fields: str = LEAN_PAPER_FIELDS,
        max_results: Optional[int] = None,
    ) -> Iterator[dict]:
        yield from self._paginate_offset(
            f"/author/{author_id}/papers", {"fields": fields}, max_results
        )

    def author_batch(
        self, ids: Sequence[str], *, fields: str = DEFAULT_AUTHOR_FIELDS
    ) -> list:
        return self._post(
            self.graph_base,
            "/author/batch",
            params={"fields": fields},
            json_body={"ids": list(ids)},
        )

    def recommend_from_paper(
        self,
        paper_id: str,
        *,
        fields: str = LEAN_PAPER_FIELDS,
        limit: int = 100,
        from_pool: str = "recent",
    ) -> dict:
        return self._get(
            self.recs_base,
            f"/papers/forpaper/{paper_id}",
            {"fields": fields, "limit": limit, "from": from_pool},
        )

    def recommend_from_pool(
        self,
        positive_ids: Sequence[str],
        negative_ids: Sequence[str] = (),
        *,
        fields: str = LEAN_PAPER_FIELDS,
        limit: int = 100,
    ) -> dict:
        body = {
            "positivePaperIds": list(positive_ids),
            "negativePaperIds": list(negative_ids),
        }
        return self._post(
            self.recs_base,
            "/papers/",
            params={"fields": fields, "limit": limit},
            json_body=body,
        )

    def _paginate_offset(
        self,
        path: str,
        params: dict,
        max_results: Optional[int],
        page_size: int = 1000,
    ) -> Iterator[dict]:
        offset = 0
        emitted = 0
        while True:
            page_params = {**params, "limit": page_size, "offset": offset}
            page = self._get(self.graph_base, path, page_params)
            data = page.get("data") or []
            for item in data:
                yield item
                emitted += 1
                if max_results is not None and emitted >= max_results:
                    return
            if len(data) < page_size:
                return
            offset += page_size


def _clean(params: Optional[dict]) -> Optional[dict]:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}
