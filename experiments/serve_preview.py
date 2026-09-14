# -*- coding: utf-8 -*-
"""Serve the C1 preview over Tailscale with copy-noise tolerant routing.

http.server drops stray backticks (the %60 from copied markdown code spans),
redirects any unknown single-char noise path to the index, and stays quiet on
favicon requests.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "output" / "creative_v2"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path: str) -> str:
        stripped = path.split("?", 1)[0].split("#", 1)[0]
        if stripped in ("/%60", "/`", "/%60/", "/%27", "/%22", "/%C2%B7"):
            return str(ROOT / "index.html")
        return super().translate_path(path)

    def send_head(self):  # favicon: answer 204 instead of a 404 log line
        if self.path.split("?", 1)[0] == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return None
        return super().send_head()


def main() -> int:
    bind = sys.argv[1] if len(sys.argv) > 1 else "100.84.28.40"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8210
    server = ThreadingHTTPServer((bind, port), PreviewHandler)
    print(f"serving {ROOT} at http://{bind}:{port}/", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
