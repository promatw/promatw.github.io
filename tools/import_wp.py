"""
WordPress → Hugo content importer for HealthTree TW static backup site.

Fetches all published posts via WP REST API, downloads inline images,
and writes Markdown files with Hugo front matter into healthtree-static/content/posts/.

Usage:
    python tools/import_wp.py

No external dependencies — uses only Python stdlib.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

# ---------- config ----------
WP_BASE = "https://healthtreetw.org"
API_URL = f"{WP_BASE}/wp-json/wp/v2/posts"
PAGES_API_URL = f"{WP_BASE}/wp-json/wp/v2/pages"
# 此檔位於 <hugo-root>/tools/import_wp.py，所以 parent.parent = Hugo 站台根目錄
HUGO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = HUGO_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
IMAGES_DIR = HUGO_ROOT / "static" / "images"

# WP page slug → 在 Hugo 內 content/<filename>.md 落地。只匯入這個白名單內
# 的頁面（其他 WP page 多半是分類選單頁，不需要對應實體 .md）。
PAGE_SLUG_WHITELIST = {"about"}

# WP category slug → Chinese display name
# 文章 front matter 的 categories 值用英文 slug（保留 ASCII URL），中文顯示名稱
# 由 content/categories/<slug>/_index.md 的 title 提供。這樣 Hugo 自動產生的
# term page (/categories/know/ 等) 才會跟主選單的硬編碼 URL 對得上。
CATEGORY_MAP = {
    "life": "日常保健",
    "event": "活動花絮",
    "know": "認識 MM",
    "status": "醫療進展",
}

USER_AGENT = "HealthTreeTW-Importer/1.0 (+static backup site)"


# ---------- slug normalization ----------
# Hugo + 中文 URL 在某些瀏覽器/CDN 表現不穩定（雙重編碼問題），且日後
# 自動發布的腳本也會以英文 slug 為準，所以 import 階段就把中文 slug 統一
# 轉成 ASCII fallback。原始 WP slug 仍記錄在 front matter 的 original_url。
def ascii_slug_fallback(raw_slug: str, date_iso: str) -> str:
    """
    Decode WP slug; if it's pure ASCII keep as-is, otherwise generate
    a deterministic English slug from date + content-type heuristics.
    """
    decoded = urllib.parse.unquote(raw_slug)
    if decoded.isascii():
        return decoded

    date_part = date_iso[:10]            # YYYY-MM-DD
    year_month = date_iso[:7]            # YYYY-MM

    # detect duplicate suffix like "-2" / "-3" from WP
    suffix_match = re.search(r"-(\d+)$", decoded)
    suffix = f"-{suffix_match.group(1)}" if suffix_match else ""

    if "月報" in decoded:
        return f"{year_month}-mm-monthly{suffix}"
    if "週報" in decoded:
        return f"{date_part}-mm-weekly{suffix}"
    if "摘要" in decoded:
        return f"{date_part}-mm-digest{suffix}"
    # generic fallback: use date + post id
    return f"{date_part}-post{suffix}"


# ---------- http helpers ----------
def http_get_json(url: str) -> tuple[object, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        headers = {k.lower(): v for k, v in resp.getheaders()}
    return json.loads(body), headers


def http_download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return False  # already present; skip
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return True


# ---------- content processing ----------
UPLOADS_PATTERN = re.compile(
    r"""https?://(?:www\.)?healthtreetw\.org/wp-content/uploads/([^\s"'<>)]+)""",
    re.IGNORECASE,
)

# 「閱讀原文」連結修正：原站很多文章把 URL 寫成純文字（"閱讀原文：https://..."）
# 而沒有包成 <a> 標籤，造成在備份站完全無法點擊。這裡把它改寫成正常 anchor。
# 對比：
#   壞 → <p style="...">👉 閱讀原文：https://example.com/foo</p>
#   好 → <p>👉 <a href="https://example.com/foo" target="_blank" rel="noopener">閱讀原文</a></p>
# 全形/半形冒號都接受。URL 後可有空白或直接接 </p>。
# 樣式 inline-style 一併移除，視覺上會用瀏覽器預設超連結色（跟原本能點的版本一致）。
READ_ORIGINAL_PATTERN = re.compile(
    r"""<p[^>]*>\s*👉\s*閱讀原文\s*[：:]\s*(https?://[^\s<"']+?)\s*</p>""",
    re.IGNORECASE,
)


def fix_read_original_link(html: str) -> tuple[str, int]:
    """Wrap bare 'URL' next to '閱讀原文' in proper <a> anchors. Returns (new_html, n_fixes)."""
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        url = match.group(1).rstrip(".,;)）。、")  # 移除常見尾部標點
        return (
            f'<p>👉 <a href="{url}" target="_blank" rel="noopener">閱讀原文</a></p>'
        )

    new_html = READ_ORIGINAL_PATTERN.sub(repl, html)
    return new_html, count


def extract_and_rewrite_images(html: str) -> tuple[str, list[str]]:
    """
    Find all WP uploads URLs in the HTML, rewrite them to /images/<path>,
    and return (rewritten_html, list_of_original_urls).
    """
    originals: list[str] = []

    def repl(match: re.Match[str]) -> str:
        rel = match.group(1)
        full = match.group(0)
        originals.append(full)
        return f"/images/{rel}"

    new_html = UPLOADS_PATTERN.sub(repl, html)
    return new_html, originals


def download_images(urls: list[str]) -> tuple[int, int, list[str]]:
    downloaded = skipped = 0
    failures: list[str] = []
    for url in set(urls):
        rel = UPLOADS_PATTERN.match(url).group(1)
        dest = IMAGES_DIR / rel
        try:
            did = http_download(url, dest)
            if did:
                downloaded += 1
            else:
                skipped += 1
        except Exception as e:
            failures.append(f"{url} — {e!r}")
    return downloaded, skipped, failures


# ---------- front matter helpers ----------
def toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_frontmatter(
    title: str, date: str, lastmod: str, slug: str,
    categories: list[str], tags: list[str], original_url: str,
) -> str:
    lines = ["+++"]
    lines.append(f'title = "{toml_escape(title)}"')
    lines.append(f'date = "{date}"')
    if lastmod and lastmod != date:
        lines.append(f'lastmod = "{lastmod}"')
    lines.append(f'slug = "{toml_escape(slug)}"')
    if categories:
        cats = ", ".join(f'"{toml_escape(c)}"' for c in categories)
        lines.append(f"categories = [{cats}]")
    if tags:
        tgs = ", ".join(f'"{toml_escape(t)}"' for t in tags)
        lines.append(f"tags = [{tgs}]")
    lines.append(f'original_url = "{original_url}"')
    lines.append("draft = false")
    lines.append("+++")
    return "\n".join(lines) + "\n\n"


def extract_taxonomy(post: dict, taxonomy: str) -> list[dict]:
    """Return list of term dicts for the given taxonomy from _embedded."""
    embedded = post.get("_embedded", {})
    terms_groups = embedded.get("wp:term", [])
    result: list[dict] = []
    for group in terms_groups:
        for term in group:
            if term.get("taxonomy") == taxonomy:
                result.append(term)
    return result


# ---------- main ----------
def fetch_all_posts() -> list[dict]:
    """Fetch every published post, paging through the REST API."""
    all_posts: list[dict] = []
    page = 1
    per_page = 100
    while True:
        url = f"{API_URL}?per_page={per_page}&page={page}&status=publish&_embed=1"
        print(f"[fetch] page {page} …", flush=True)
        try:
            posts, _ = http_get_json(url)
        except urllib.error.HTTPError as e:
            if e.code == 400 and page > 1:
                break  # paged past end
            raise
        if not isinstance(posts, list) or not posts:
            break
        all_posts.extend(posts)
        if len(posts) < per_page:
            break
        page += 1
    return all_posts


def write_post(post: dict) -> tuple[str, list[str]]:
    title = unescape(post["title"]["rendered"])
    date_iso = post["date"]  # e.g. 2026-04-22T10:00:00
    modified_iso = post.get("modified", date_iso)
    # WP REST 回傳的 slug 為 URL-encoded 字串。中文 slug 統一改成 ASCII
    # 以避開 Hugo + 瀏覽器的雙重編碼問題；原始連結保留在 front matter 中。
    slug = ascii_slug_fallback(post["slug"], post["date"])
    original_url = post.get("link", "")

    # taxonomies — 用 WP 英文 slug 當作 categories 值，中文顯示由
    # content/categories/<slug>/_index.md 的 title 提供
    cat_terms = extract_taxonomy(post, "category")
    categories = []
    for term in cat_terms:
        wp_slug = term.get("slug", "")
        if wp_slug:
            categories.append(wp_slug)

    tag_terms = extract_taxonomy(post, "post_tag")
    tags = [t.get("name", "") for t in tag_terms if t.get("name")]

    # content
    raw_html = post["content"]["rendered"]
    rewritten, original_urls = extract_and_rewrite_images(raw_html)
    rewritten, n_link_fixes = fix_read_original_link(rewritten)

    fm = build_frontmatter(title, date_iso, modified_iso, slug, categories, tags, original_url)
    body = rewritten.strip() + "\n"

    out_path = POSTS_DIR / f"{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(fm + body, encoding="utf-8")
    return slug, original_urls, n_link_fixes


def fetch_all_pages() -> list[dict]:
    """Fetch every published page (WP `/pages` endpoint), paging through."""
    all_pages: list[dict] = []
    page = 1
    per_page = 100
    while True:
        url = f"{PAGES_API_URL}?per_page={per_page}&page={page}&status=publish"
        try:
            pages, _ = http_get_json(url)
        except urllib.error.HTTPError as e:
            if e.code == 400 and page > 1:
                break
            raise
        if not isinstance(pages, list) or not pages:
            break
        all_pages.extend(pages)
        if len(pages) < per_page:
            break
        page += 1
    return all_pages


def write_page(page: dict) -> tuple[str, list[str]]:
    """Write a WP page as a top-level Hugo content file (e.g. content/about.md)."""
    title = unescape(page["title"]["rendered"])
    slug = page["slug"]
    original_url = page.get("link", "")

    raw_html = page["content"]["rendered"]
    rewritten, original_urls = extract_and_rewrite_images(raw_html)
    rewritten, _ = fix_read_original_link(rewritten)

    # Page front matter (YAML, matches existing about.md style)
    fm_lines = ["---"]
    fm_lines.append(f'title: "{toml_escape(title)}"')
    fm_lines.append(f'url: "/{slug}/"')
    fm_lines.append("ShowReadingTime: false")
    fm_lines.append("ShowWordCount: false")
    fm_lines.append(f'original_url: "{original_url}"')
    fm_lines.append("---")
    fm = "\n".join(fm_lines) + "\n\n"
    body = rewritten.strip() + "\n"

    out_path = CONTENT_DIR / f"{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(fm + body, encoding="utf-8")
    return slug, original_urls


def main() -> int:
    print(f"Output posts dir: {POSTS_DIR}")
    print(f"Output images dir: {IMAGES_DIR}")

    posts = fetch_all_posts()
    print(f"[fetch] total posts: {len(posts)}")

    all_image_urls: list[str] = []
    written = 0
    total_link_fixes = 0
    for post in posts:
        slug, img_urls, n_link_fixes = write_post(post)
        all_image_urls.extend(img_urls)
        written += 1
        total_link_fixes += n_link_fixes
        suffix = f", {n_link_fixes} link fix(es)" if n_link_fixes else ""
        print(f"  wrote {slug}.md ({len(img_urls)} image refs{suffix})")
    print(f"[fix] total 閱讀原文 anchors rewritten: {total_link_fixes}")

    # Import whitelisted pages (e.g. About)
    pages = fetch_all_pages()
    pages_written = 0
    for pg in pages:
        if pg.get("slug") not in PAGE_SLUG_WHITELIST:
            continue
        result = write_page(pg)
        # write_page may return (slug, urls) or (slug, urls, n_fixes)
        slug, img_urls = result[0], result[1]
        all_image_urls.extend(img_urls)
        pages_written += 1
        print(f"  wrote {slug}.md (page, {len(img_urls)} image refs)")
    print(f"[fetch] wrote {pages_written} pages")

    print(f"\n[images] total unique refs: {len(set(all_image_urls))}")
    if all_image_urls:
        downloaded, skipped, failures = download_images(all_image_urls)
        print(f"[images] downloaded {downloaded}, skipped (existing) {skipped}")
        if failures:
            print(f"[images] FAILED {len(failures)}:")
            for f in failures:
                print(f"  - {f}")

    print(f"\n[done] wrote {written} posts, {pages_written} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
