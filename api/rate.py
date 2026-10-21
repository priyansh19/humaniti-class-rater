"""Vercel serverless endpoint: POST JSON {transcript?: str, url?: str} -> rating.
Transcript-only (no Whisper/torch/OpenCV). LLM judge auto-enabled if an approved provider key is set."""
import ipaddress
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests  # noqa: E402

from classq import transcript as T  # noqa: E402
from classq.llm import enabled as llm_enabled
from classq.pipeline import THEME_TEXT, assess  # noqa: E402

MAX_BYTES = 3_000_000


def _check_url(url: str):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("Only http(s) links are allowed")
    for info in socket.getaddrinfo(u.hostname, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Link resolves to a private address")


def fetch(url: str) -> str:
    _check_url(url)
    r = requests.get(url, timeout=10, stream=True, allow_redirects=False)
    r.raise_for_status()
    data = b""
    for chunk in r.iter_content(65536):
        data += chunk
        if len(data) > MAX_BYTES:
            raise ValueError("Transcript too large (>3 MB)")
    return data.decode("utf-8", errors="ignore")


def rate(body: dict) -> dict:
    text = body.get("transcript") or ""
    if not text and body.get("url"):
        text = fetch(body["url"])
    if len(text) > MAX_BYTES:
        raise ValueError("Transcript too large (>3 MB)")
    cues = T.parse_any(text)
    if len(cues) < 3:
        raise ValueError("Could not parse a transcript (need a VTT or 'Speaker: text' lines)")
    f = {"text": T.features(cues), "evidence": T.evidence(cues), "excerpt": T.excerpt(cues)}
    r = assess(f, use_llm=llm_enabled(), multimodal=False)
    r["features"] = f["text"]
    r["evidence"] = f["evidence"][:25]
    r["theme_labels"] = {k: THEME_TEXT[k][0] for k in r["themes"]}
    return r


class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"ok": True, "llm_enabled": llm_enabled()})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 4_000_000:
                return self._send(413, {"error": "Request too large (Vercel limit ~4.5 MB)"})
            body = json.loads(self.rfile.read(n) or b"{}")
            self._send(200, rate(body))
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # pragma: no cover
            self._send(500, {"error": f"{type(e).__name__}: {e}"})
