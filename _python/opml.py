import ast
import os
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

import yaml

ROOT = Path(__file__).resolve().parent.parent

GROUPS = [
    ("news", "Headlines"),
    ("advisory", "Advisories"),
    ("cve", "Critical CVEs"),
    ("breach", "Breaches"),
    ("blog", "Blogs"),
    ("status", "Status pages"),
]


def load_sources(path=ROOT / "_python" / "feed-generator.py"):
    tree = ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "SOURCES" for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


def read_feeds(paths, sources):
    feeds, seen = [], set()
    for path in paths:
        workflow = yaml.safe_load(Path(path).read_text()) or {}
        for job in (workflow.get("jobs") or {}).values():
            for step in job.get("steps") or []:
                settings = step.get("with") or {}
                url = settings.get("feed")
                if not url or url in seen:
                    continue
                seen.add(url)
                label = str(settings.get("prefix", "")).strip("[]").replace(" ", "")
                title, category = sources.get(label, (label, "news"))
                feeds.append({"title": title, "url": url, "category": category})
    return feeds


def build_opml(feeds):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        "  <head>",
        "    <title>SecOpsNews feeds</title>",
        "    <ownerName>thechelsuk</ownerName>",
        "    <docs>https://opml.org/spec2.opml</docs>",
        "  </head>",
        "  <body>",
    ]
    for category, name in GROUPS:
        group = [f for f in feeds if f["category"] == category]
        if not group:
            continue
        lines.append(f"    <outline text={quoteattr(name)} title={quoteattr(name)}>")
        for f in group:
            lines.append(
                f"      <outline type=\"rss\" text={quoteattr(f['title'])} "
                f"title={quoteattr(f['title'])} xmlUrl={quoteattr(f['url'])}/>"
            )
        lines.append("    </outline>")
    lines += ["  </body>", "</opml>", ""]
    return "\n".join(lines)


def main():
    output = Path(os.environ.get("OPML_FILE", ROOT / "feeds.opml"))
    paths = sorted((ROOT / ".github" / "workflows").glob("rss_*.yml"))
    feeds = read_feeds(paths, load_sources())
    output.write_text(build_opml(feeds))
    print(f"Wrote {len(feeds)} feeds to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
