#!/usr/bin/env python3
"""Check that the links in a learning tree still work.

Usage:
    python check_links.py <tree-folder>        # every URL in nodes/*.md
    python check_links.py --url https://...    # one or more explicit URLs
    options: --timeout 10  --workers 8  --json

Result per URL:
    ok        reachable (a final-URL change is reported as a note)
    blocked   the site refused our request (401/403/429...): unverified, NOT proven dead
    broken    404/410/400-ish: the page is gone
    error     network failure, timeout or 5xx: try again later

YouTube watch/playlist/shorts links are checked through YouTube's oEmbed
endpoint, which reports removed or private videos that the normal page does
not, and gives the video title as a bonus.

Safety: a tree you received from someone else may list URLs that point at your
own machine or network (localhost, 192.168.x.x, ...). Those are skipped as
`blocked` unless you pass --allow-private, and redirects into private addresses
are refused.

Exit code 1 if anything is `broken`. Standard library only. Needs internet
access (some sandboxes restrict it; run this where the network is open).
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = "Mozilla/5.0 (compatible; learning-tree-linkcheck/0.1)"
URL_RE = re.compile(r"https?://[^\s<>\"\]]+")
YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def extract_urls(text):
    urls = []
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?'")
        while u.endswith(")") and u.count(")") > u.count("("):
            u = u[:-1]
        urls.append(u)
    return urls


def is_youtube(url):
    p = urllib.parse.urlparse(url)
    if p.netloc.lower() not in YT_HOSTS:
        return False
    if p.netloc.lower() == "youtu.be":
        return len(p.path.strip("/")) > 0
    return p.path == "/watch" or p.path.startswith(("/playlist", "/shorts/"))


ALLOW_PRIVATE = False


def _is_private_host(host):
    """True if `host` resolves to a loopback/private/link-local/reserved address."""
    if not host:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return False        # cannot resolve: let the request fail with a normal error
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return True
    return False


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme not in ("http", "https"):
            raise urllib.error.URLError(f"redirect to {parsed.scheme or 'unknown'}: refused")
        if not ALLOW_PRIVATE and _is_private_host(parsed.hostname):
            raise urllib.error.URLError("redirect to a private address refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SafeRedirect)


def _request(url, method, timeout):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            body = r.read(65536) if method == "GET" else b""
            return r.status, r.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, b""


def _classify(code):
    if 200 <= code < 400:
        return "ok"
    if code in (401, 403, 405, 406, 429, 451, 999):
        return "blocked"
    if code >= 500:
        return "error"
    return "broken"


def _same(a, b):
    norm = lambda u: re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
    return norm(a) == norm(b)


def check_youtube(url, timeout):
    api = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url, safe="")
    code, _, body = _request(api, "GET", timeout)
    if code == 200:
        try:
            title = json.loads(body.decode("utf-8", "replace")).get("title", "")
        except ValueError:
            title = ""
        return {"status": "ok", "code": code, "note": f"title: {title}" if title else ""}
    if code == 404:
        return {"status": "broken", "code": code, "note": "video removed or private"}
    if code == 401:
        return {"status": "blocked", "code": code, "note": "embedding disabled; unverified"}
    return {"status": _classify(code), "code": code, "note": "oEmbed check"}


def check_url(url, timeout=10):
    if not ALLOW_PRIVATE and _is_private_host(urllib.parse.urlparse(url).hostname):
        return {"url": url, "status": "blocked", "code": None,
                "note": "private/local address skipped (use --allow-private to check it)"}
    try:
        if is_youtube(url):
            res = check_youtube(url, timeout)
        else:
            code, final, _ = _request(url, "HEAD", timeout)
            if code >= 400:  # many servers mishandle HEAD; retry with GET
                code, final, _ = _request(url, "GET", timeout)
            res = {"status": _classify(code), "code": code, "note": ""}
            if res["status"] == "ok" and not _same(url, final):
                res["note"] = f"redirects to {final}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        reason = getattr(e, "reason", e)
        res = {"status": "error", "code": None, "note": str(reason)}
    res["url"] = url
    return res


def collect(folder):
    found = {}
    for md in sorted(Path(folder).rglob("*.md")):
        if md.name == "overview.md":
            continue
        for u in extract_urls(md.read_text(encoding="utf-8-sig")):
            found.setdefault(u, []).append(str(md.relative_to(folder)))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check learning-tree links.")
    ap.add_argument("folder", nargs="?", help="tree folder to scan for URLs")
    ap.add_argument("--url", action="append", default=[], help="check this URL (repeatable)")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-private", action="store_true",
                    help="also check localhost / private-network addresses")
    args = ap.parse_args(argv)
    global ALLOW_PRIVATE
    ALLOW_PRIVATE = args.allow_private

    sources = {}
    if args.folder:
        sources.update(collect(args.folder))
    for u in args.url:
        sources.setdefault(u, ["(argument)"])
    if not sources:
        ap.error("give a tree folder or at least one --url")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(lambda u: check_url(u, args.timeout), sorted(sources)))
    for r in results:
        r["files"] = sources[r["url"]]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        order = {"broken": 0, "error": 1, "blocked": 2, "ok": 3}
        for r in sorted(results, key=lambda r: order[r["status"]]):
            code = f" {r['code']}" if r["code"] else ""
            note = f" - {r['note']}" if r["note"] else ""
            where = "" if r["status"] == "ok" else f"  (in {', '.join(r['files'])})"
            print(f"[{r['status'].upper()}{code}] {r['url']}{note}{where}")
        counts = {k: sum(1 for r in results if r["status"] == k) for k in order}
        print("\n" + ", ".join(f"{v} {k}" for k, v in counts.items()))
    return 1 if any(r["status"] == "broken" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
