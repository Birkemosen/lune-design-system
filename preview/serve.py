#!/usr/bin/env python3
"""Server farve-previewet uden at kopiere den byggede HTML."""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "/touch": ROOT / "examples/touch/dist/preview-da.html",
    "/v6": ROOT / "examples/v6/dist/preview-da.html",
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        src = PAGES.get(path)
        if src is None:
            return super().do_GET()
        html = src.read_text(encoding="utf-8")
        title = "Lune Touch" if path == "/touch" else "Lune V6"
        html = html.replace("<title>Lune Touch</title>", f"<title>{title}</title>", 1)
        html = html.replace("<title>Lune V6</title>", f"<title>{title}</title>", 1)
        html = html.replace(
            "</head>",
            '<link rel="stylesheet" href="/preview/vibrant.css?v=4"></head>',
            1,
        )
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("http://127.0.0.1:8765/touch", flush=True)
    server.serve_forever()
