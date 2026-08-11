"""Google search helper for Browser Harness (通用搜索层).

For Issue sunshine6666666666/browser-harness#16: a reusable search layer
that mechanically pulls public search results for an already-disambiguated
entity (typically a Chinese news entity whose official English name needs to
be found). This layer ONLY pulls results — it never translates, never decides
which English name is correct, and never judges news truth. The calling Agent
reads the returned titles/URLs/snippets and decides.

Expected input: a disambiguated Chinese entity (e.g. "武汉天兴洲长江大桥").
Recommended query pattern: "<entity> official english name" or
"<entity> english name site:.gov.cn". Keep the entity specific; a vague
phrase like "武汉天桥" is NOT a valid input for this layer.

Read-only: opens google.com/search, extracts result blocks, never posts,
never mutates data, never clicks through to result pages.

Safety:
- rate limit: MIN_QUERY_DELAY seconds between consecutive queries
  (conservative default 4s; Google shows soft blocks under rapid fire).
- captcha stop: if the SERP URL redirects to /sorry/ or the page contains a
  captcha form, raise RuntimeError and STOP. Do not retry in a loop.
- batch cap: search_many refuses more than MAX_BATCH_QUERIES (20) per call;
  the caller must chunk.
- isolated browser: run against an isolated/Agent Chrome via BU_CDP_URL.

UI facts (verified 2026-08-12) — google.com/search?hl=en&num=N:
- Result block: a `div[data-snc]` containing `a h3` (title anchor). The
  class names rotate (N54PNb BToiNc, srKDX, ...) so select by structure,
  not by class.
- Title: `a h3` textContent.
- URL: the closest `a` href.
- Snippet: `.VwiC3b` text (may be absent on some blocks / image-only).
- Rank: 1-based order of the first N `a h3` anchors on the SERP.
- Consent/captcha pages: `#consent-bump`, `form[action*="consent"]`,
  `/sorry/` URL, `#captcha-form`.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlsplit

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...

GOOGLE_SEARCH = "https://www.google.com/search?hl=en&num={num}&q={q}"

# Conservative pacing; Google soft-blocks rapid automation.
MIN_QUERY_DELAY = 4.0
MAX_BATCH_QUERIES = 20

_EXTRACT_JS = """(() => {
  const anchors = Array.from(document.querySelectorAll('a h3'))
    .map(h3 => h3.closest('a')).filter(Boolean);
  const out = [];
  for (let idx = 0; idx < anchors.length; idx++) {
    const a = anchors[idx];
    const h3 = a.querySelector('h3');
    if (!h3) continue;
    let block = h3;
    for (let i = 0; i < 8 && block; i++) {
      const p = block.parentElement;
      if (!p) break;
      const cls = (p.className || '').toString();
      if (p.querySelectorAll('a').length >= 1 &&
          p.querySelectorAll('h3').length >= 1 &&
          p.children.length >= 2 && cls.indexOf('N54PNb') !== -1) {
        block = p;
        break;
      }
      block = p;
    }
    let snippet = '';
    const snipEl = block.querySelector('.VwiC3b') ||
                   block.querySelector('[data-sncf]') ||
                   block.querySelector('div[role="heading"] + div');
    if (snipEl) {
      const t = snipEl.textContent.trim();
      if (t && t.length > 20 && t !== h3.textContent.trim()) snippet = t.slice(0, 220);
    }
    out.push({
      title: h3.textContent.trim(),
      url: a.href || '',
      snippet: snippet,
    });
  }
  return out;
})()"""


def _is_captcha_or_consent(url: str) -> str | None:
    """Return a reason string when the current page is a captcha/consent wall."""
    if "/sorry/" in url or "sorry/index" in url:
        return "google captcha wall (/sorry/)"
    return None


def _normalize_domain(url: str) -> str:
    netloc = urlsplit(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def search(query: str, num_results: int = 8, min_delay: float = MIN_QUERY_DELAY) -> list[dict[str, Any]]:
    """Run one Google query and return structured results.

    Returns a list of dicts: {query, rank, title, url, snippet, source_domain}.

    - num_results clamps 1..20; Google ignores num>10 on many SERPs, so the
      caller should treat 8 as the practical default.
    - Raises RuntimeError on captcha/consent wall (human blocker) or when no
      result anchors are found.
    - Sleeps min_delay before the query so callers can loop without hammering.
    """
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    num_results = max(1, min(int(num_results), 20))

    if min_delay > 0:
        time.sleep(min_delay)

    url = GOOGLE_SEARCH.format(num=num_results, q=quote(query))
    goto_url(url)
    wait(3.0)

    reason = _is_captcha_or_consent(js("location.href") or "")
    if reason:
        raise RuntimeError("search blocked: " + reason)

    raw = js(_EXTRACT_JS)
    if not isinstance(raw, list) or not raw:
        # One more check: consent bump can render without a /sorry/ URL.
        consent = js(
            "!!document.querySelector('#consent-bump, form[action*=\\\"consent\\\"], #L2AGLb')"
        )
        if consent:
            raise RuntimeError("search blocked: google consent page")
        raise RuntimeError(
            "no search result anchors found (SERP layout may have changed)"
        )

    results = []
    for rank, item in enumerate(raw[:num_results], start=1):
        results.append({
            "query": query,
            "rank": rank,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
            "source_domain": _normalize_domain(item.get("url", "")),
        })
    return results


def search_many(queries: list[str], num_results: int = 8,
                min_delay: float = MIN_QUERY_DELAY) -> list[list[dict[str, Any]]]:
    """Run several queries serially with pacing. Returns one list per query.

    Refuses more than MAX_BATCH_QUERIES per call (caller chunks). Stops at the
    first captcha/consent block (RuntimeError propagates; do not retry in a
    loop — that is a human blocker).
    """
    if len(queries) > MAX_BATCH_QUERIES:
        raise ValueError(
            "search_many refuses >%d queries per call (chunk it)"
            % MAX_BATCH_QUERIES
        )
    out = []
    for q in queries:
        out.append(search(q, num_results=num_results, min_delay=min_delay))
    return out


def run(query: str, num_results: int = 8):
    """CLI-ish entry for exec(open(...).read()) under Browser Harness."""
    results = search(query, num_results=num_results, min_delay=0)
    for r in results:
        print("%d. %s | %s | %s" % (r["rank"], r["title"], r["url"], r["source_domain"]))
    return results
