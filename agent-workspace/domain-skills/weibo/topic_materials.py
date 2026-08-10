"""Weibo topic-materials helper for Browser Harness (图片素材库落地工具).

Downloads original images of a Weibo hot topic into a local material library
so downstream vision/OCR/辨证 can consume them offline. Videos are NOT
downloaded (out of scope).

Depends on sibling `topic_facts` for post material: the calling session must
FIRST load topic_facts.py the same way, e.g.

    exec(open(".../weibo/topic_facts.py").read())
    exec(open(".../weibo/topic_materials.py").read())
    lib = fetch_topic_materials(url, out_dir)

Downloads use a Weibo Referer header (Sina CDN may otherwise 403).

Output layout under <out_dir>:
  <out_dir>/<topic_slug>/
    manifest.json     # every post + local image paths + meta (for downstream)
    images/
      <idx>-<n>.jpg   # images named by post index
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def terminal(cmd: str) -> dict: ...
    def fetch_topic_facts(topic_url, max_pages=5, stale_pages=None, limit=None) -> dict: ...


def _slugify(name):
    """Safe filesystem slug from a topic name."""
    name = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name).strip("_")
    return name[:80] or "topic"


def _download_image(url, dest, referer="https://weibo.com/"):
    """Download one image via curl with Referer. Returns dest or None."""
    try:
        res = subprocess.run(
            [
                "curl", "-sL", "-o", dest,
                "-w", "%{http_code}",
                "-H", "Referer: %s" % referer,
                url,
            ],
            capture_output=True, text=True, timeout=30,
        )
        code = res.stdout.strip()
        if code == "200" and os.path.exists(dest) and os.path.getsize(dest) > 1000:
            return dest
    except Exception:
        pass
    if os.path.exists(dest):
        try:
            os.remove(dest)
        except Exception:
            pass
    return None


def fetch_topic_materials(topic_url, out_dir, max_pages=5, stale_pages=None,
                          limit=None, max_images_per_post=None):
    """Collect a topic's posts and download original images to a library.

    Args:
      topic_url: s.weibo.com search URL (from hot-rank entry href).
      out_dir: root directory for the material library.
      max_pages / stale_pages / limit: forwarded to fetch_topic_facts.
      max_images_per_post: optional cap (None = all images).

    Returns:
    {
      "topic": str, "page_count": int, "post_count": int,
      "downloaded": int, "failed": int,
      "library_dir": str, "manifest_path": str,
      "manifest": [post entries with local_images],
    }
    """
    facts = fetch_topic_facts(
        topic_url, max_pages=max_pages, stale_pages=stale_pages, limit=limit
    )

    topic_slug = _slugify(facts["topic"])
    library_dir = os.path.join(out_dir, topic_slug)
    images_dir = os.path.join(library_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    manifest = []
    downloaded = 0
    failed = 0

    for idx, post in enumerate(facts["posts"], 1):
        entry = dict(post)
        entry["local_images"] = []
        urls = post.get("images") or []
        if max_images_per_post:
            urls = urls[:max_images_per_post]
        for n, url in enumerate(urls, 1):
            dest = os.path.join(images_dir, "%03d-%d.jpg" % (idx, n))
            ok = _download_image(url, dest)
            if ok:
                entry["local_images"].append(dest)
                downloaded += 1
            else:
                failed += 1
        # keep text short in manifest to stay lean
        if entry.get("text"):
            entry["text"] = entry["text"][:500]
        manifest.append(entry)

    manifest_path = os.path.join(library_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "topic": facts["topic"],
                "page_count": facts["page_count"],
                "post_count": len(manifest),
                "images_downloaded": downloaded,
                "images_failed": failed,
                "generated_by": "weibo/topic_materials.py",
                "posts": manifest,
            },
            fh, ensure_ascii=False, indent=2,
        )

    return {
        "topic": facts["topic"],
        "page_count": facts["page_count"],
        "post_count": len(manifest),
        "downloaded": downloaded,
        "failed": failed,
        "library_dir": library_dir,
        "manifest_path": manifest_path,
        "manifest": manifest,
    }


def run(topic_url=None, out_dir="/tmp/weibo_materials", max_pages=5, limit=None):
    """CLI entry for exec(open(...).read()) under Browser Harness."""
    if not topic_url:
        import hot_rank  # same-dir sibling for fallback topic source
        rows = hot_rank.fetch_hot_rank("social", 1)
        topic_url = rows[0]["href"]
    lib = fetch_topic_materials(
        topic_url, out_dir, max_pages=max_pages, limit=limit
    )
    print("=== 话题: %s ===" % lib["topic"])
    print("素材库目录: %s" % lib["library_dir"])
    print("帖子: %d | 下载图片: %d | 失败: %d | 页数: %d" % (
        lib["post_count"], lib["downloaded"], lib["failed"], lib["page_count"]))
    for i, p in enumerate(lib["manifest"], 1):
        if p["local_images"]:
            print("%d. %s [%s] 图%d: %s" % (
                i, p["author"], p["source_type"], len(p["local_images"]),
                p["local_images"][0]))
    return lib
