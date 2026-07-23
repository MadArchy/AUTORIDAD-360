"""Servidor del blog público Juan Vásquez — rutas limpias + SEO básico."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

SITE_ORIGIN = os.environ.get("PUBLIC_BLOG_ORIGIN", "http://127.0.0.1:3002").rstrip("/")
API_BASE = os.environ.get(
    "NEXT_PUBLIC_API_URL",
    os.environ.get("VITE_API_URL", "http://127.0.0.1:8012/api/v1"),
).rstrip("/")


def _fetch_published() -> list[dict]:
    try:
        with urllib.request.urlopen(f"{API_BASE}/blog/published", timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []


def _robots_body() -> bytes:
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        f"Sitemap: {SITE_ORIGIN}/sitemap.xml\n"
    )
    return body.encode("utf-8")


def _sitemap_body() -> bytes:
    posts = _fetch_published()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [
        f"  <url><loc>{escape(SITE_ORIGIN)}/</loc><lastmod>{now}</lastmod>"
        f"<changefreq>daily</changefreq><priority>1.0</priority></url>"
    ]
    for post in posts:
        slug = str(post.get("slug") or "").strip()
        if not slug:
            continue
        loc = f"{SITE_ORIGIN}/blog/{urllib.parse.quote(slug)}"
        lastmod = (post.get("published_at") or post.get("updated_at") or now)[:10]
        urls.append(
            f"  <url><loc>{escape(loc)}</loc><lastmod>{escape(lastmod)}</lastmod>"
            f"<changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return xml.encode("utf-8")


class BlogHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path == "/robots.txt":
            self._send_bytes(_robots_body(), "text/plain; charset=utf-8")
            return
        if path == "/sitemap.xml":
            self._send_bytes(_sitemap_body(), "application/xml; charset=utf-8")
            return
        if path in {"/blog", "/"}:
            self.path = "/index.html"
        elif path.startswith("/blog/"):
            self.path = "/post.html"
        super().do_GET()

    def _send_bytes(self, payload: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[blog] {self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 3002), BlogHandler)
    print(f"Blog público {SITE_ORIGIN} (API {API_BASE})", flush=True)
    server.serve_forever()
