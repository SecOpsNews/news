import gzip
import http.server
import io
import os
import sys

COMPRESSIBLE = (".html", ".css", ".js", ".json", ".svg", ".txt", ".xml", ".rss", ".opml")


class GzipHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        if not (accepts_gzip and path.endswith(COMPRESSIBLE) and os.path.isfile(path)):
            return super().send_head()
        with open(path, "rb") as source:
            body = gzip.compress(source.read())
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        return io.BytesIO(body)


def handler(*args, **kwargs):
    return GzipHandler(*args, directory=sys.argv[1], **kwargs)


if __name__ == "__main__":
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
