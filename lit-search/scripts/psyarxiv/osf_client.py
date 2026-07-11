"""OSF API v2 client scoped to PsyArxiv preprints.

Public functions assume `OSF_TOKEN` is in the environment (auto-loaded from a
.env beside this script if present). The OSF Preprints
endpoint follows JSON:API conventions: filtering via `filter[field]=value`,
sparse fieldsets via `fields[preprints]=...`, link-based pagination via
`links.next` URLs, and standard `data/attributes/relationships/links` envelopes.

Critical constraint discovered empirically:
  There is NO full-text `filter[q]` on `/preprints/`. Keyword discovery is
  restricted to substring matches against `title`, `description`, or `tags`.
  Multi-word `filter[title]=working memory` is a phrase substring (word order
  matters: "memory working" returns zero hits).
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator


def _load_dotenv_if_present() -> None:
    # Look beside this client first (scripts/psyarxiv/.env), then the cwd and up
    # to 5 parent dirs. Own-dir wins so a per-engine .env drop-in works
    # regardless of where the script is invoked from. Mirrors s2_client.py.
    search_dirs = [os.path.dirname(os.path.abspath(__file__))]
    cwd = os.getcwd()
    for _ in range(5):
        search_dirs.append(cwd)
        nxt = os.path.dirname(cwd)
        if nxt == cwd:
            break
        cwd = nxt
    for d in search_dirs:
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, _, v = line.partition("=")
                        k = k.strip()
                        if k in os.environ:
                            continue  # real shell / settings.json env wins
                        v = v.strip().strip('"').strip("'")
                        # A value of the form $(...) is run in a shell and
                        # replaced by its stdout, so a .env can pull a live
                        # value from the user's shell profile at runtime
                        # instead of freezing a copy of the secret.
                        if v.startswith("$(") and v.endswith(")"):
                            try:
                                v = subprocess.run(
                                    v[2:-1], shell=True, text=True,
                                    capture_output=True, timeout=15,
                                ).stdout.strip()
                            except Exception:
                                v = ""
                        if v:
                            os.environ[k] = v
            except OSError:
                pass
            return


_load_dotenv_if_present()

BASE_URL = "https://api.osf.io/v2"
PSYARXIV = "psyarxiv"

# Lean default field set — keeps a 100-record page near 30 KB instead of 300 KB.
DEFAULT_PREPRINT_FIELDS = [
    "title",
    "description",
    "doi",
    "date_published",
    "date_modified",
    "subjects",
    "tags",
    "is_published",
    "reviews_state",
    "preprint_doi_created",
]

# page[size] caps at 100 server-side regardless of value sent.
MAX_PAGE_SIZE = 100


class OSFError(RuntimeError):
    pass


class OSFClient:
    def __init__(self, token: str | None = None, provider: str = PSYARXIV, timeout: int = 30):
        self.token = token or os.environ.get("OSF_TOKEN", "")
        if not self.token:
            raise OSFError("OSF_TOKEN env var not set")
        self.provider = provider
        self.timeout = timeout

    def _request(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.api+json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise OSFError(f"OSF API {e.code}: {body[:500]}") from None

    def _build_url(self, path: str, params: dict[str, Any] | None) -> str:
        url = BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        return url

    def _paginate(
        self,
        path: str,
        params: dict[str, Any],
        max_pages: int | None = None,
        max_results: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        url = self._build_url(path, params)
        page = 0
        yielded = 0
        while url:
            data = self._request(url)
            for item in data.get("data", []):
                yield item
                yielded += 1
                if max_results and yielded >= max_results:
                    return
            page += 1
            if max_pages and page >= max_pages:
                return
            url = data.get("links", {}).get("next")

    def search_preprints(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        tags: str | None = None,
        subjects: str | None = None,
        date_published_gte: str | None = None,
        date_published_lte: str | None = None,
        sort: str = "-date_published",
        fields: list[str] | None = None,
        page_size: int = MAX_PAGE_SIZE,
        max_pages: int | None = None,
        max_results: int | None = None,
        extra_filters: dict[str, str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield preprint records matching the given filters.

        All keyword arguments map to JSON:API filter fields. `title`, `description`,
        and `tags` perform substring matches (case-insensitive icontains by default).
        Combining multiple filters is AND across fields.
        """
        params: dict[str, Any] = {
            "filter[provider]": self.provider,
            "page[size]": min(page_size, MAX_PAGE_SIZE),
            "sort": sort,
        }
        if title is not None:
            params["filter[title]"] = title
        if description is not None:
            params["filter[description]"] = description
        if tags is not None:
            params["filter[tags]"] = tags
        if subjects is not None:
            params["filter[subjects]"] = subjects
        if date_published_gte:
            params["filter[date_published][gte]"] = date_published_gte
        if date_published_lte:
            params["filter[date_published][lte]"] = date_published_lte
        if fields is not None:
            params["fields[preprints]"] = ",".join(fields)
        if extra_filters:
            params.update(extra_filters)

        yield from self._paginate(
            "/preprints/", params, max_pages=max_pages, max_results=max_results
        )

    def get_total(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        tags: str | None = None,
        subjects: str | None = None,
        date_published_gte: str | None = None,
        date_published_lte: str | None = None,
        extra_filters: dict[str, str] | None = None,
    ) -> int:
        """Cheap headcount — fetch one row and read links.meta.total."""
        params: dict[str, Any] = {
            "filter[provider]": self.provider,
            "page[size]": 1,
            "fields[preprints]": "title",
        }
        if title is not None:
            params["filter[title]"] = title
        if description is not None:
            params["filter[description]"] = description
        if tags is not None:
            params["filter[tags]"] = tags
        if subjects is not None:
            params["filter[subjects]"] = subjects
        if date_published_gte:
            params["filter[date_published][gte]"] = date_published_gte
        if date_published_lte:
            params["filter[date_published][lte]"] = date_published_lte
        if extra_filters:
            params.update(extra_filters)
        url = self._build_url("/preprints/", params)
        data = self._request(url)
        return data.get("links", {}).get("meta", {}).get("total", 0)

    def get_preprint(self, preprint_id: str, fields: list[str] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if fields is not None:
            params["fields[preprints]"] = ",".join(fields)
        url = self._build_url(f"/preprints/{preprint_id}/", params or None)
        return self._request(url)

    def get_contributors(self, preprint_id: str, page_size: int = MAX_PAGE_SIZE) -> Iterator[dict[str, Any]]:
        params = {"page[size]": min(page_size, MAX_PAGE_SIZE)}
        yield from self._paginate(f"/preprints/{preprint_id}/contributors/", params)

    def list_subjects(self, page_size: int = MAX_PAGE_SIZE) -> Iterator[dict[str, Any]]:
        params = {"page[size]": min(page_size, MAX_PAGE_SIZE)}
        yield from self._paginate(f"/providers/preprints/{self.provider}/subjects/", params)


def flatten_preprint(item: dict[str, Any]) -> dict[str, Any]:
    """Collapse a JSON:API preprint entity into a flat dict for CLI output."""
    a = item.get("attributes", {})
    links = item.get("links", {})
    # `subjects` is a list of lists (taxonomy hierarchies). Flatten to leaf text.
    subjects_flat: list[str] = []
    for cluster in a.get("subjects", []) or []:
        if cluster:
            subjects_flat.append(cluster[-1].get("text", ""))
    return {
        "id": item.get("id"),
        "title": a.get("title"),
        "description": a.get("description"),
        "doi": a.get("doi"),
        "date_published": a.get("date_published"),
        "date_modified": a.get("date_modified"),
        "tags": a.get("tags", []),
        "subjects": subjects_flat,
        "is_published": a.get("is_published"),
        "reviews_state": a.get("reviews_state"),
        "html_url": links.get("html"),
        "preprint_doi": links.get("preprint_doi"),
    }
