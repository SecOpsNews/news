import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("feed_health", ROOT / "_python" / "feed_health.py")
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)

RSS = b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title><item><title>a</title></item></channel></rss>'
ATOM = b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>x</title><entry><title>a</title></entry></feed>'
RDF = b'<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"><item><title>a</title></item></rdf:RDF>'
JSONFEED = b'{"version": "https://jsonfeed.org/version/1.1", "title": "x", "items": [{"id": "1"}]}'
HTML = b"<!doctype html><html><head><title>Blog</title></head><body>hi</body></html>"
OPML = b"""<?xml version="1.0"?><opml version="2.0"><body>
<outline text="Headlines"><outline type="rss" text="A" xmlUrl="https://a.example/feed"/></outline>
<outline text="Blogs"><outline type="rss" text="B" xmlUrl="https://b.example/rss"/></outline>
</body></opml>"""


def test_reads_feeds_from_opml(tmp_path):
    path = tmp_path / "feeds.opml"
    path.write_bytes(OPML)
    assert fh.read_opml(path) == [
        {"title": "A", "url": "https://a.example/feed", "group": "Headlines"},
        {"title": "B", "url": "https://b.example/rss", "group": "Blogs"},
    ]


def test_recognises_rss_atom_rdf_and_json_feed():
    assert fh.classify(200, RSS) == ("ok", "RSS, 1 item")
    assert fh.classify(200, ATOM) == ("ok", "Atom, 1 item")
    assert fh.classify(200, RDF) == ("ok", "RSS 1.0, 1 item")
    assert fh.classify(200, JSONFEED) == ("ok", "JSON Feed, 1 item")


def test_empty_feed_is_a_warning():
    empty = b'<rss version="2.0"><channel><title>x</title></channel></rss>'
    assert fh.classify(200, empty) == ("warn", "RSS, no items")


def test_html_page_is_broken():
    assert fh.classify(200, HTML) == ("broken", "not a feed (HTML page)")


def test_garbage_is_broken():
    assert fh.classify(200, b"\x00\x01nonsense") == ("broken", "not a feed")


def test_http_errors_are_broken():
    assert fh.classify(404, b"") == ("broken", "HTTP 404")
    assert fh.classify(403, b"") == ("broken", "HTTP 403 (blocked)")


def test_check_uses_fetcher_and_reports_network_errors():
    def fetch(url):
        if "bad" in url:
            raise OSError("Name or service not known")
        return 200, RSS

    good = fh.check({"title": "Good", "url": "https://good.example", "group": "G"}, fetch)
    bad = fh.check({"title": "Bad", "url": "https://bad.example", "group": "G"}, fetch)
    assert good["status"] == "ok"
    assert bad["status"] == "broken" and "Name or service not known" in bad["detail"]


def test_report_lists_problems_first_and_counts():
    results = [
        {"title": "A", "url": "https://a", "group": "G", "status": "ok", "detail": "RSS, 3 items"},
        {"title": "B", "url": "https://b", "group": "G", "status": "broken", "detail": "HTTP 404"},
        {"title": "C", "url": "https://c", "group": "G", "status": "warn", "detail": "RSS, no items"},
    ]
    report = fh.report(results)
    assert report.splitlines()[0] == "# Feed health"
    assert "1 broken, 1 with no items, 1 OK, of 3 feeds." in report
    assert report.index("| B |") < report.index("| C |") < report.index("| A |")


def test_exit_code_fails_only_on_broken(tmp_path, monkeypatch):
    path = tmp_path / "feeds.opml"
    path.write_bytes(OPML)
    monkeypatch.setattr(fh, "fetch", lambda url: (200, RSS) if "a.example" in url else (200, b'<rss><channel/></rss>'))
    assert fh.main([str(path)]) == 0
    monkeypatch.setattr(fh, "fetch", lambda url: (404, b""))
    assert fh.main([str(path)]) == 1


def test_writes_summary_when_asked(tmp_path, monkeypatch):
    path = tmp_path / "feeds.opml"
    path.write_bytes(OPML)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(fh, "fetch", lambda url: (200, RSS))
    fh.main([str(path)])
    assert summary.read_text().startswith("# Feed health")
