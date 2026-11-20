import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "Mozilla/5.0 (compatible; SecOpsNews feed check; +https://secops.thechels.uk)"
ORDER = {"broken": 0, "warn": 1, "ok": 2}


def read_opml(path):
    feeds = []
    body = ET.parse(path).getroot().find("body")
    for group in body:
        for outline in group.iter("outline"):
            if outline.get("xmlUrl"):
                feeds.append({"title": outline.get("text"), "url": outline.get("xmlUrl"), "group": group.get("text")})
    return feeds


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(5_000_000)
    except urllib.error.HTTPError as e:
        return e.code, b""


def _local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _items(count, kind):
    if count == 0:
        return "warn", f"{kind}, no items"
    return "ok", f"{kind}, {count} item{'s' if count != 1 else ''}"


def classify(status, body):
    if status != 200:
        return "broken", f"HTTP {status}" + (" (blocked)" if status in (401, 403, 429) else "")
    text = body.lstrip()
    if text[:1] == b"{":
        try:
            data = json.loads(body)
        except ValueError:
            return "broken", "not a feed"
        if "jsonfeed.org" in str(data.get("version", "")):
            return _items(len(data.get("items") or []), "JSON Feed")
        return "broken", "not a feed"
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        if b"<html" in text[:2000].lower() or text[:15].lower().startswith(b"<!doctype html"):
            return "broken", "not a feed (HTML page)"
        return "broken", "not a feed"
    tag = _local(root.tag)
    if tag == "rss":
        return _items(sum(1 for e in root.iter() if _local(e.tag) == "item"), "RSS")
    if tag == "feed":
        return _items(sum(1 for e in root.iter() if _local(e.tag) == "entry"), "Atom")
    if tag == "rdf":
        return _items(sum(1 for e in root.iter() if _local(e.tag) == "item"), "RSS 1.0")
    if tag == "html":
        return "broken", "not a feed (HTML page)"
    return "broken", "not a feed"


def check(feed, fetcher=None):
    fetcher = fetcher or fetch
    try:
        status, detail = classify(*fetcher(feed["url"]))
    except (OSError, ValueError) as e:
        status, detail = "broken", f"couldn't fetch ({e})"
    return {**feed, "status": status, "detail": detail}


def report(results):
    results = sorted(results, key=lambda r: (ORDER[r["status"]], r["group"], r["title"]))
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ORDER}
    lines = [
        "# Feed health",
        "",
        f"{counts['broken']} broken, {counts['warn']} with no items, {counts['ok']} OK, of {len(results)} feeds.",
        "",
        "| Feed | Group | Result | URL |",
        "|---|---|---|---|",
    ]
    marks = {"broken": "❌", "warn": "⚠️", "ok": "✅"}
    for r in results:
        lines.append(f"| {r['title']} | {r['group']} | {marks[r['status']]} {r['detail']} | {r['url']} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else ROOT / "feeds.opml"
    feeds = read_opml(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda f: check(f, fetch), feeds))
    text = report(results)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(text)
    return 1 if any(r["status"] == "broken" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
