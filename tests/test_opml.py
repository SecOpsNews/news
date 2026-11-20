import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("opml", ROOT / "_python" / "opml.py")
opml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opml)

WORKFLOW = """
name: RSS Test
on:
    workflow_dispatch:
jobs:
    CISA:
        runs-on: ubuntu-latest
        steps:
            - uses: guilhem/rss-issues-action@0.5.2
              with:
                  feed: "https://www.cisa.gov/alerts.xml"
                  prefix: "[CISA]"
                  labels: "CISA"
    TroyHunt:
        runs-on: ubuntu-latest
        steps:
            - uses: guilhem/rss-issues-action@0.5.2
              with:
                  feed: "https://www.troyhunt.com/rss/"
                  prefix: "[TroyHunt]"
                  labels: "TroyHunt"
    ITGovernance:
        runs-on: ubuntu-latest
        steps:
            - uses: guilhem/rss-issues-action@0.5.2
              with:
                  feed: "https://www.itgovernance.co.uk/blog/feed"
                  prefix: "[IT Governance]"
                  labels: "ITGovernance"
    Unknown:
        runs-on: ubuntu-latest
        steps:
            - uses: guilhem/rss-issues-action@0.5.2
              with:
                  feed: "https://example.com/feed?a=1&b=2"
                  prefix: "[Mystery]"
                  labels: "Mystery"
"""

SOURCES = {
    "CISA": ("CISA", "advisory"),
    "TroyHunt": ("Troy Hunt", "blog"),
    "ITGovernance": ("IT Governance", "news"),
}


def write(tmp_path, text=WORKFLOW):
    path = tmp_path / "rss_test.yml"
    path.write_text(text)
    return [path]


def test_reads_every_feed_job(tmp_path):
    feeds = opml.read_feeds(write(tmp_path), SOURCES)
    assert [f["url"] for f in feeds] == [
        "https://www.cisa.gov/alerts.xml",
        "https://www.troyhunt.com/rss/",
        "https://www.itgovernance.co.uk/blog/feed",
        "https://example.com/feed?a=1&b=2",
    ]


def test_names_and_categories_come_from_sources(tmp_path):
    feeds = {f["url"]: f for f in opml.read_feeds(write(tmp_path), SOURCES)}
    assert feeds["https://www.cisa.gov/alerts.xml"]["title"] == "CISA"
    assert feeds["https://www.cisa.gov/alerts.xml"]["category"] == "advisory"
    assert feeds["https://www.itgovernance.co.uk/blog/feed"]["title"] == "IT Governance"


def test_unknown_label_falls_back_to_news(tmp_path):
    feeds = {f["url"]: f for f in opml.read_feeds(write(tmp_path), SOURCES)}
    assert feeds["https://example.com/feed?a=1&b=2"]["title"] == "Mystery"
    assert feeds["https://example.com/feed?a=1&b=2"]["category"] == "news"


def test_skips_jobs_without_a_feed(tmp_path):
    text = WORKFLOW + """
    Other:
        runs-on: ubuntu-latest
        steps:
            - run: echo hi
"""
    assert len(opml.read_feeds(write(tmp_path, text), SOURCES)) == 4


def test_duplicate_feed_urls_are_listed_once(tmp_path):
    paths = write(tmp_path)
    second = tmp_path / "rss_again.yml"
    second.write_text(WORKFLOW)
    assert len(opml.read_feeds(paths + [second], SOURCES)) == 4


def test_opml_is_valid_and_grouped(tmp_path):
    feeds = opml.read_feeds(write(tmp_path), SOURCES)
    root = ET.fromstring(opml.build_opml(feeds))
    assert root.tag == "opml" and root.get("version") == "2.0"
    groups = {g.get("text"): g for g in root.find("body")}
    assert list(groups) == ["Headlines", "Advisories", "Blogs"]
    news = [o.get("xmlUrl") for o in groups["Headlines"]]
    assert news == ["https://www.itgovernance.co.uk/blog/feed", "https://example.com/feed?a=1&b=2"]
    first = groups["Advisories"][0]
    assert first.get("type") == "rss" and first.get("text") == "CISA" and first.get("title") == "CISA"


def test_opml_has_no_timestamp_so_unchanged_feeds_make_no_commit(tmp_path):
    feeds = opml.read_feeds(write(tmp_path), SOURCES)
    assert opml.build_opml(feeds) == opml.build_opml(feeds)
    assert "dateCreated" not in opml.build_opml(feeds)


def test_real_workflows_parse():
    paths = sorted((ROOT / ".github" / "workflows").glob("rss_*.yml"))
    feeds = opml.read_feeds(paths, opml.load_sources())
    assert len(feeds) >= 30
    assert all(f["url"].startswith("http") for f in feeds)
