"""Chunked uploads and safe link downloads."""
from __future__ import annotations

import ipaddress
import os
import re
import shutil
import socket
from urllib.parse import parse_qs, urlparse

import httpx

MAX_BYTES = 2 * 1024 ** 3
CHUNK = 8 * 1024 ** 2


class IngestError(ValueError):
    pass


def check_public_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise IngestError("Only http(s) links are supported")
    try:
        infos = socket.getaddrinfo(u.hostname, None)
    except socket.gaierror as e:
        raise IngestError("Link host could not be resolved") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise IngestError("Links to private or internal addresses are not allowed")


def normalise_link(url: str) -> str:
    """Turn Google Drive / Dropbox share links into direct-download URLs."""
    u = urlparse(url)
    if u.hostname in ("drive.google.com", "docs.google.com"):
        m = re.search(r"/d/([\w-]{10,})", u.path)
        fid = m.group(1) if m else (parse_qs(u.query).get("id") or [None])[0]
        if fid:
            return f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
    if u.hostname and u.hostname.endswith("dropbox.com"):
        return re.sub(r"([?&])dl=0", r"\1dl=1", url) if "dl=0" in url else url + ("&" if "?" in url else "?") + "dl=1"
    return url


def download(url: str, dest: str, on_progress=None, max_bytes: int = MAX_BYTES, max_redirects: int = 5) -> str:
    url = normalise_link(url)
    for _ in range(max_redirects + 1):
        check_public_url(url)                        # re-checked on every redirect hop
        with httpx.stream("GET", url, timeout=httpx.Timeout(30, read=120), follow_redirects=False) as r:
            if r.is_redirect:
                url = str(r.next_request.url) if r.next_request else r.headers["location"]
                continue
            if r.status_code != 200:
                raise IngestError(f"Link returned HTTP {r.status_code}")
            ctype = r.headers.get("content-type", "")
            if "text/html" in ctype:
                raise IngestError("Link points to a web page, not a media file (is the file shared publicly?)")
            total = int(r.headers.get("content-length") or 0)
            if total > max_bytes:
                raise IngestError("File is larger than 2 GB")
            n = 0
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes(1 << 20):
                    n += len(chunk)
                    if n > max_bytes:
                        raise IngestError("File is larger than 2 GB")
                    fh.write(chunk)
                    if on_progress and total:
                        on_progress(n / total)
            return dest
    raise IngestError("Too many redirects")


def fetch_text(url: str, max_bytes: int = 5_000_000) -> str:
    check_public_url(url)
    r = httpx.get(normalise_link(url), timeout=30, follow_redirects=False)
    if r.status_code != 200 or len(r.content) > max_bytes:
        raise IngestError("Could not fetch the transcript link")
    return r.text


class Uploads:
    """Chunk files live in <root>/<upload_id>/<n>.part and are assembled on completion."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _dir(self, uid: str) -> str:
        if not re.fullmatch(r"[a-f0-9]{16}", uid):
            raise IngestError("Bad upload id")
        return os.path.join(self.root, uid)

    def _size(self, d: str) -> int:
        with open(os.path.join(d, "meta")) as fh:
            return int(fh.read().split("\n")[0])

    def init(self, uid: str, size: int, filename: str) -> int:
        if size <= 0 or size > MAX_BYTES:
            raise IngestError("File must be between 1 byte and 2 GB")
        if not re.search(r"\.(mp4|mov|mkv|webm|m4v)$", filename, re.IGNORECASE):
            raise IngestError("Unsupported file type (use MP4, MOV, MKV or WEBM)")
        d = self._dir(uid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "meta"), "w") as fh:
            fh.write(f"{size}\n{filename}")
        return -(-size // CHUNK)

    def put(self, uid: str, n: int, data: bytes) -> None:
        d = self._dir(uid)
        size = self._size(d)
        n_chunks = -(-size // CHUNK)
        if not 0 <= n < n_chunks:
            raise IngestError("Chunk index out of range")
        expected = CHUNK if n < n_chunks - 1 else size - CHUNK * (n_chunks - 1)
        if len(data) != expected:
            raise IngestError(f"Chunk {n} has {len(data)} bytes, expected {expected}")
        tmp = os.path.join(d, f"{n}.tmp")
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, os.path.join(d, f"{n}.part"))   # atomic -> idempotent retries

    def complete(self, uid: str, dest: str) -> str:
        d = self._dir(uid)
        size = self._size(d)
        n_chunks = -(-size // CHUNK)
        missing = [i for i in range(n_chunks) if not os.path.exists(os.path.join(d, f"{i}.part"))]
        if missing:
            raise IngestError(f"Missing chunks: {missing[:10]}")
        with open(dest, "wb") as out:
            for i in range(n_chunks):
                with open(os.path.join(d, f"{i}.part"), "rb") as fh:
                    shutil.copyfileobj(fh, out)
        shutil.rmtree(d, ignore_errors=True)
        return dest
