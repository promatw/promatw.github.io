#!/usr/bin/env python3
"""Build and query the cross-month topic deduplication index."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
DATA_DIR = ROOT / "data"
TOPICS_PATH = DATA_DIR / "published_topics.json"
ALIASES_PATH = DATA_DIR / "published_topic_aliases.json"
PUBLISHED_URLS_PATH = DATA_DIR / "published_urls.json"

MONTHLY_SOURCES = {
    "2026-04-mm-monthly.md": "2026-03",
    "2026-04-monthly.md": "2026-04",
    "2026-05-monthly.md": "2026-05",
}

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}

KEYWORD_PATTERNS = [
    "adc",
    "anti-cd38",
    "asco",
    "ash",
    "bcma",
    "belantamab",
    "car-t",
    "cartitude",
    "ciltacabtagene",
    "cilta-cel",
    "daratumumab",
    "elranatamab",
    "elrexfio",
    "fda",
    "gprc5d",
    "iberdomide",
    "jsmm",
    "kbdca",
    "lenalidomide",
    "mezigdomide",
    "mgus",
    "mrd",
    "sdm",
    "talquetamab",
    "talvey",
    "tbmta",
    "teclistamab",
    "共同決策",
    "冒煙型",
    "加速核准",
    "高風險",
    "交流沙龍",
    "病友聚會",
    "骨髓瘤",
]


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean_text(value)).lower()
    value = value.removeprefix("🔹").strip()
    value = value.replace("骨髓腫", "骨髓瘤")
    value = value.replace("協同決策", "共同決策")
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", value)


def normalize_url(value: str) -> str:
    value = html.unescape(value.strip())
    if not value:
        return ""
    parts = urlsplit(value)
    scheme = parts.scheme.lower() or "https"
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    query = []
    for key, val in parse_qsl(parts.query, keep_blank_values=True):
        low = key.lower()
        if low.startswith("utm_") or low in TRACKING_PARAMS:
            continue
        query.append((key, val))
    query.sort()
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def extract_keywords(title: str, summary: str = "") -> list[str]:
    haystack = unicodedata.normalize("NFKC", f"{title} {summary}").lower()
    return sorted({keyword for keyword in KEYWORD_PATTERNS if keyword.lower() in haystack})


def frontmatter_value(content: str, key: str) -> str:
    match = re.search(rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_cards(content: str) -> list[dict[str, str]]:
    cards = []
    pattern = re.compile(r"<h3[^>]*>(?P<title>[\s\S]*?)</h3>(?P<body>[\s\S]*?)(?=<h3|<h2|$)")
    for match in pattern.finditer(content):
        title = clean_text(match.group("title")).removeprefix("🔹").strip()
        body = match.group("body")
        source_match = re.search(r"來源：(?P<source>[\s\S]*?)</p>", body)
        source = clean_text(source_match.group("source")) if source_match else ""
        link_match = re.search(r'<a\s+href="(?P<url>[^"]+)"[^>]*>閱讀原文</a>', body)
        url = html.unescape(link_match.group("url")) if link_match else ""
        paragraph_matches = re.findall(r"<p[^>]*>([\s\S]*?)</p>", body)
        summaries = []
        for paragraph in paragraph_matches:
            text = clean_text(paragraph)
            if text.startswith("來源：") or "閱讀原文" in text:
                continue
            if text:
                summaries.append(text)
        cards.append({"title": title, "source": source, "url": url, "summary": " ".join(summaries)})
    return cards


def topic_id(title: str) -> str:
    digest = hashlib.sha256(normalize_title(title).encode("utf-8")).hexdigest()[:12]
    return f"topic-{digest}"


def load_aliases() -> list[dict[str, str]]:
    if not ALIASES_PATH.exists():
        return []
    return json.loads(ALIASES_PATH.read_text(encoding="utf-8-sig")).get("aliases", [])


def rebuild() -> dict:
    alias_rows = load_aliases()
    alias_to_canonical = {
        normalize_title(row["alias_title"]): row["canonical_title"] for row in alias_rows
    }
    grouped: dict[str, dict] = {}
    url_to_key: dict[str, str] = {}
    source_months: set[str] = set()

    source_specs = [(filename, report_month, "monthly") for filename, report_month in MONTHLY_SOURCES.items()]
    source_specs.extend(
        (path.name, path.name[:7], "weekly")
        for path in sorted(POSTS_DIR.glob("????-??-??-mm-weekly.md"))
    )

    for filename, report_month, report_kind in source_specs:
        path = POSTS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing report source: {path}")
        content = path.read_text(encoding="utf-8")
        report_slug = frontmatter_value(content, "slug")
        cards = parse_cards(content) if report_kind == "monthly" else parse_weekly(content)
        source_months.add(report_month)
        for card in cards:
            canonical_title = alias_to_canonical.get(normalize_title(card["title"]), card["title"])
            key = normalize_title(canonical_title)
            normalized_card_url = normalize_url(card["url"])
            if normalized_card_url and normalized_card_url in url_to_key:
                key = url_to_key[normalized_card_url]
                canonical_title = grouped[key]["title"]
            entry = grouped.setdefault(
                key,
                {
                    "topic_id": topic_id(canonical_title),
                    "title": canonical_title,
                    "normalized_title": key,
                    "title_aliases": [],
                    "urls": [],
                    "keywords": [],
                    "first_published": report_month,
                    "report_slugs": [],
                    "sources": [],
                },
            )
            if card["title"] != canonical_title and card["title"] not in entry["title_aliases"]:
                entry["title_aliases"].append(card["title"])
            if card["url"] and card["url"] not in entry["urls"]:
                entry["urls"].append(card["url"])
            if normalized_card_url:
                url_to_key[normalized_card_url] = key
            if report_slug and report_slug not in entry["report_slugs"]:
                entry["report_slugs"].append(report_slug)
            if card["source"] and card["source"] not in entry["sources"]:
                entry["sources"].append(card["source"])
            entry["keywords"] = sorted(
                set(entry["keywords"]) | set(extract_keywords(card["title"], card["summary"]))
            )
            entry["first_published"] = min(entry["first_published"], report_month)

    by_title = {entry["title"]: entry for entry in grouped.values()}
    missing_canonicals = []
    for row in alias_rows:
        entry = by_title.get(row["canonical_title"])
        if not entry:
            missing_canonicals.append(row["canonical_title"])
            continue
        alias = row["alias_title"]
        if alias != entry["title"] and alias not in entry["title_aliases"]:
            entry["title_aliases"].append(alias)

    if missing_canonicals:
        raise ValueError(f"Alias canonical titles not found: {sorted(set(missing_canonicals))}")

    topics = sorted(grouped.values(), key=lambda item: (item["first_published"], item["title"]))
    for entry in topics:
        entry["title_aliases"].sort()
        entry["urls"].sort(key=normalize_url)
        entry["report_slugs"].sort()
        entry["sources"].sort()

    payload = {
        "schema_version": 1,
        "description": "跨月份已發布主題索引，供週報候選在寫入前進行網址與語意去重。",
        "last_updated": "2026-07-31",
        "source_months": sorted(source_months),
        "topic_count": len(topics),
        "topics": topics,
    }
    TOPICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def load_index() -> dict:
    if not TOPICS_PATH.exists():
        raise FileNotFoundError(f"Run rebuild first: {TOPICS_PATH}")
    return json.loads(TOPICS_PATH.read_text(encoding="utf-8-sig"))


def published_url_set(index: dict) -> set[str]:
    urls = {normalize_url(url) for topic in index["topics"] for url in topic.get("urls", [])}
    if PUBLISHED_URLS_PATH.exists():
        old = json.loads(PUBLISHED_URLS_PATH.read_text(encoding="utf-8-sig"))
        urls.update(normalize_url(url) for url in old.get("urls", []))
    return {url for url in urls if url}


def check_candidate(title: str, url: str = "", source: str = "") -> dict:
    index = load_index()
    normalized_candidate = normalize_title(title)
    normalized_candidate_url = normalize_url(url)

    if normalized_candidate_url and normalized_candidate_url in published_url_set(index):
        for topic in index["topics"]:
            if normalized_candidate_url in {normalize_url(value) for value in topic.get("urls", [])}:
                return result("duplicate", "exact_url", 1.0, title, url, source, topic)
        return result("duplicate", "published_url_database", 1.0, title, url, source, None)

    best_topic = None
    best_score = 0.0
    best_reason = ""
    candidate_keywords = set(extract_keywords(title))

    for topic in index["topics"]:
        names = [topic["title"], *topic.get("title_aliases", [])]
        for name in names:
            normalized_name = normalize_title(name)
            if normalized_candidate == normalized_name:
                return result("duplicate", "exact_title_or_alias", 1.0, title, url, source, topic)
            score = SequenceMatcher(None, normalized_candidate, normalized_name).ratio()
            if score > best_score:
                best_score = score
                best_topic = topic
                best_reason = "title_similarity"

        overlap = candidate_keywords & set(topic.get("keywords", []))
        if len(overlap) >= 2 and best_score < 0.72:
            semantic_score = min(0.79, 0.55 + 0.08 * len(overlap))
            if semantic_score > best_score:
                best_score = semantic_score
                best_topic = topic
                best_reason = f"keyword_overlap:{','.join(sorted(overlap))}"

    if best_score >= 0.82:
        status = "duplicate"
    elif best_score >= 0.62:
        status = "possible_duplicate"
    else:
        status = "new"
    return result(status, best_reason or "no_close_match", best_score, title, url, source, best_topic)


def result(status: str, reason: str, score: float, title: str, url: str, source: str, topic: dict | None) -> dict:
    return {
        "status": status,
        "reason": reason,
        "score": round(score, 3),
        "candidate": {"title": title, "url": url, "source": source},
        "matched_topic": None
        if topic is None
        else {
            "topic_id": topic["topic_id"],
            "title": topic["title"],
            "first_published": topic["first_published"],
            "report_slugs": topic["report_slugs"],
        },
    }


def parse_weekly(content: str) -> list[dict[str, str]]:
    rows = []
    pattern = re.compile(r"<h2[^>]*>(?P<title>[\s\S]*?)</h2>(?P<body>[\s\S]*?)(?=<h2|$)")
    for match in pattern.finditer(content):
        title = clean_text(match.group("title")).removeprefix("🔹").strip()
        body = match.group("body")
        source_match = re.search(r"來源：</strong>(?P<source>[\s\S]*?)(?:　｜|</p>)", body)
        source = clean_text(source_match.group("source")) if source_match else ""
        link_match = re.search(r'<a\s+href="(?P<url>[^"]+)"[^>]*>閱讀原文</a>', body)
        url = html.unescape(link_match.group("url")) if link_match else ""
        paragraph_matches = re.findall(r"<p[^>]*>([\s\S]*?)</p>", body)
        summaries = []
        for paragraph in paragraph_matches:
            text = clean_text(paragraph)
            if text.startswith("來源：") or "閱讀原文" in text:
                continue
            if text:
                summaries.append(text)
        rows.append({"title": title, "source": source, "url": url, "summary": " ".join(summaries)})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("rebuild", help="Rebuild published_topics.json from monthly reports")

    check_parser = subparsers.add_parser("check", help="Check one weekly candidate")
    check_parser.add_argument("--title", required=True)
    check_parser.add_argument("--url", default="")
    check_parser.add_argument("--source", default="")

    audit_parser = subparsers.add_parser("audit-weekly", help="Audit all entries in one weekly Markdown file")
    audit_parser.add_argument("path", type=Path)

    args = parser.parse_args()
    if args.command == "rebuild":
        payload = rebuild()
        print(json.dumps({"path": str(TOPICS_PATH), "topic_count": payload["topic_count"]}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "check":
        print(json.dumps(check_candidate(args.title, args.url, args.source), ensure_ascii=False, indent=2))
        return 0

    path = args.path if args.path.is_absolute() else ROOT / args.path
    rows = parse_weekly(path.read_text(encoding="utf-8"))
    output = [check_candidate(row["title"], row["url"], row["source"]) for row in rows]
    counts = {status: sum(item["status"] == status for item in output) for status in ("duplicate", "possible_duplicate", "new")}
    print(json.dumps({"file": str(path), "counts": counts, "results": output}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
