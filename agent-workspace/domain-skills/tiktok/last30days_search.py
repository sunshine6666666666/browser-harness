"""TikTok Browser search adapter for last30days.

Runs inside browser-harness (`browser-harness -c 'exec(open(...).read())'`).
First-version read-only collector: searches logged-in Agent Chrome TikTok pages
and emits raw TikTok dicts compatible with last30days normalize._normalize_shortform_video.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus, urlparse

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...
    def wait(seconds: float = 1.0) -> None: ...


def _extract_search_videos(limit: int = 12) -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const abs = href => href ? new URL(href, location.origin).href.split('?')[0] : '';
      const out = [];
      const seen = new Set();
      const anchors = Array.from(document.querySelectorAll('a[href*="/video/"]'));
      for (const a of anchors) {
        const href = abs(a.getAttribute('href'));
        if (!href || seen.has(href)) continue;
        seen.add(href);
        let box = a;
        for (let i = 0; i < 10 && box && box.parentElement; i++) {
          box = box.parentElement;
          const txt = norm(box.innerText || box.textContent || '');
          if (txt.length > 40 && /\b(@|#)|\d|天前|小时前|分钟前|ago|\d-\d|\d{4}-\d/.test(txt)) break;
        }
        const txt = norm((box && (box.innerText || box.textContent)) || a.innerText || a.textContent || '');
        const img = (box && box.querySelector('img')) || a.querySelector('img');
        const author = (href.match(/tiktok\.com\/@([^/]+)/) || [])[1] || '';
        const videoId = (href.match(/\/video\/(\d+)/) || [])[1] || '';
        out.push({
          url: href,
          video_id: videoId,
          author_name: author,
          text: txt.slice(0, 900),
          anchor_text: norm(a.innerText || a.textContent || ''),
          image_alt: img ? norm(img.getAttribute('alt') || '') : '',
          source_layer: 'browser_tiktok_search_anchor'
        });
        if (out.length >= %d) break;
      }
      const body = document.body.innerText || '';
      return {
        url: location.href,
        title: document.title,
        items: out,
        login_wall: /Log in|Sign up|登录|注册/.test(body) && out.length === 0,
        body_head: body.slice(0, 600)
      };
    })()
    """ % limit)


def _extract_video_detail(limit_comments: int = 5) -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const href = location.href.split('?')[0];
      const body = document.body.innerText || '';
      const comments = [];
      const candidates = Array.from(document.querySelectorAll('[data-e2e*="comment"], [class*="comment" i]'));
      const seen = new Set();
      for (const c of candidates) {
        const txt = norm(c.innerText || c.textContent || '');
        if (!txt || txt.length < 8 || txt.length > 500 || seen.has(txt)) continue;
        if (/评论|Comment|Reply|回复/.test(txt) && txt.length < 30) continue;
        seen.add(txt);
        comments.push({text: txt.slice(0, 400), author: '', digg_count: 0, date: ''});
        if (comments.length >= %d) break;
      }
      const descNodes = Array.from(document.querySelectorAll('[data-e2e*="desc"], [data-e2e*="browse-video-desc"], h1, h2'));
      const desc = descNodes.map(e => norm(e.innerText || e.textContent || '')).find(Boolean) || '';
      return {
        url: href,
        title: document.title,
        body_head: body.slice(0, 1200),
        description: desc.slice(0, 900),
        top_comments: comments,
      };
    })()
    """ % limit_comments)


def _num(text: str) -> int | None:
    text = str(text or '').strip().replace(',', '').lower()
    if not text:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*([kmb万千]?)', text)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    mult = {'k': 1000, 'm': 1000000, 'b': 1000000000, '千': 1000, '万': 10000}.get(unit, 1)
    return int(val * mult)


def _date_from_visible(text: str) -> str | None:
    now = datetime.now(timezone.utc).date()
    t = str(text or '')
    m = re.search(r'(\d+)\s*(?:分钟前|分钟|minute|minutes|min)', t, re.I)
    if m:
        return now.isoformat()
    m = re.search(r'(\d+)\s*(?:小时前|小时|hour|hours|hr)', t, re.I)
    if m:
        return now.isoformat()
    m = re.search(r'(\d+)\s*(?:天前|天|day|days)', t, re.I)
    if m:
        return (now - timedelta(days=int(m.group(1)))).isoformat()
    m = re.search(r'(?<!\d)(\d{1,2})-(\d{1,2})(?!\d)', t)
    if m:
        year = now.year
        month, day = int(m.group(1)), int(m.group(2))
        try:
            d = datetime(year, month, day).date()
            if d > now + timedelta(days=2):
                d = datetime(year - 1, month, day).date()
            return d.isoformat()
        except ValueError:
            return None
    m = re.search(r'(20\d{2})-(\d{1,2})-(\d{1,2})', t)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date().isoformat()
        except ValueError:
            return None
    return None


def _hashtags(text: str) -> list[str]:
    return list(dict.fromkeys(h.strip('#').lower() for h in re.findall(r'#[\w\u4e00-\u9fff.-]+', text or '') if h.strip('#')))


def _clean_text(raw: str, alt: str = '', detail: dict[str, Any] | None = None) -> str:
    detail = detail or {}
    desc = str(detail.get('description') or '').strip()
    if desc:
        return desc[:700]
    text = str(raw or alt or '').strip()
    lines = [ln.strip() for ln in re.split(r'\n+', text) if ln.strip()]
    drop = {'TikTok', '综合', '用户', '视频', '直播', '照片'}
    kept = [ln for ln in lines if ln not in drop]
    return ' '.join(kept)[:700]


def _to_last30days_tiktok_item(item: dict[str, Any], detail: dict[str, Any] | None = None, index: int = 0) -> dict[str, Any]:
    detail = detail or {}
    text = _clean_text(item.get('text') or '', item.get('image_alt') or '', detail)
    handle = str(item.get('author_name') or '')
    url = str(item.get('url') or detail.get('url') or '')
    vid = str(item.get('video_id') or '') or (re.search(r'/video/(\d+)', url or '') or ['',''])[1]
    likes = _num(item.get('anchor_text') or '')
    engagement = {'views': 0, 'likes': likes or 0, 'comments': 0, 'shares': 0}
    return {
        'id': vid or f'TKBROWSER{index + 1}',
        'video_id': vid or f'TKBROWSER{index + 1}',
        'text': text,
        'url': url,
        'author_name': handle,
        'date': _date_from_visible(' '.join([str(item.get('text') or ''), str(detail.get('body_head') or '')])),
        'engagement': engagement,
        'hashtags': _hashtags(text),
        'duration': None,
        'relevance': 0.5,
        'why_relevant': f'TikTok browser result: {text[:80]}' if text else 'TikTok browser result',
        'caption_snippet': '',
        'top_comments': detail.get('top_comments') or [],
        'metadata': {
            'adapter': 'browser_tiktok_search',
            'source_layer': item.get('source_layer') or 'browser_tiktok_search',
            'browser_raw': {
                'anchor_text': item.get('anchor_text') or '',
                'image_alt': item.get('image_alt') or '',
                'detail_title': detail.get('title') or '',
            },
        },
    }


def _build_last30days_payload(result: dict[str, Any]) -> dict[str, Any]:
    search_items = list((result.get('search') or {}).get('items') or [])
    detail_by_url = result.get('detail_by_url') or {}
    items = [_to_last30days_tiktok_item(item, detail_by_url.get(item.get('url') or ''), i) for i, item in enumerate(search_items)]
    return {
        'source': 'tiktok',
        'adapter': 'browser_tiktok_search',
        'compatible_with': 'last30days raw tiktok items -> normalize._normalize_shortform_video',
        'items': items,
        'items_by_source': {'tiktok': items},
        'notes': [
            'First browser tier collects visible search/detail/comment signals only.',
            'Spoken-word transcript remains a deeper enrichment step, not included in this browser tier.',
        ],
    }


def run(query: str = 'OpenAI Codex', limit: int = 10, detail_limit: int = 3, close_tabs: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {'query': query, 'ok': False, 'search': {}, 'detail_by_url': {}}
    search_url = f'https://www.tiktok.com/search?q={quote_plus(query)}'
    new_tab(search_url)
    wait_for_load()
    wait(5.0)
    for _ in range(4):
        js('window.scrollBy(0, 1000)')
        wait(1.0)
    search = _extract_search_videos(limit=limit)
    result['search'] = search
    for item in list(search.get('items') or [])[: max(0, detail_limit)]:
        url = item.get('url')
        if not url:
            continue
        new_tab(url)
        wait_for_load()
        wait(4.0)
        result['detail_by_url'][url] = _extract_video_detail(limit_comments=5)
    result['ok'] = bool(search.get('items') or [])
    result['last30days'] = _build_last30days_payload(result)
    return result


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
