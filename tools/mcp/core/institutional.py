"""
Institutional access for paywalled papers.

Supports three access methods:
  1. EZproxy URL rewriting (most common — rewrites publisher URLs through library proxy)
  2. Browser cookie import (reuse an authenticated session from Chrome/Firefox)
  3. HTTP/SOCKS proxy (route through institutional network)

Configuration lives in config.json under "institutional_access".
"""

import http.cookiejar
import json
import re
import sqlite3
import struct
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests

from .database import CONFIG_PATH


def get_institutional_config() -> dict:
    """Load institutional access settings from config.json."""
    config = json.loads(CONFIG_PATH.read_text())
    return config.get("institutional_access", {})


def _build_session(config: dict) -> requests.Session:
    """Build a requests.Session with institutional credentials applied."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
    })

    # Load cookies
    cookie_path = config.get("cookie_file")
    if cookie_path:
        cookies = _load_cookies(Path(cookie_path))
        session.cookies.update(cookies)

    # Set proxy
    proxy = config.get("proxy")
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    return session


def _load_cookies(cookie_path: Path) -> dict:
    """Load cookies from a Netscape/Mozilla cookie file or browser profile.

    Supports:
      - Netscape cookie.txt (exported via browser extension)
      - Direct {name: value} JSON file
    """
    if not cookie_path.exists():
        return {}

    suffix = cookie_path.suffix.lower()

    # JSON cookie file: {"name": "value", ...}
    if suffix == ".json":
        return json.loads(cookie_path.read_text())

    # Netscape cookie.txt format (exported by "Get cookies.txt" extensions)
    cookies = {}
    try:
        cj = http.cookiejar.MozillaCookieJar()
        cj.load(str(cookie_path), ignore_discard=True, ignore_expires=True)
        for cookie in cj:
            cookies[cookie.name] = cookie.value
    except Exception:
        # Fallback: parse manually
        for line in cookie_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
    return cookies


def rewrite_url_for_ezproxy(url: str, ezproxy_prefix: str) -> str:
    """Rewrite a publisher URL to go through EZproxy.

    Two EZproxy modes:
      - Prefix mode: https://proxy.library.edu/login?url=https://doi.org/...
      - Rewrite mode: https://doi-org.proxy.library.edu/...

    We detect the mode from the ezproxy_prefix format.
    """
    if not ezproxy_prefix:
        return url

    # Mode 1: prefix URL (contains "login?url=" or ends with "?url=")
    if "login?url=" in ezproxy_prefix or ezproxy_prefix.endswith("?url="):
        base = ezproxy_prefix.rstrip("=") + "="
        return f"{base}{url}"

    # Mode 2: hostname rewrite (e.g., "proxy.case.edu")
    # nature.com -> nature-com.proxy.case.edu
    parsed = urlparse(url)
    host = parsed.hostname or ""
    rewritten_host = host.replace(".", "-") + "." + ezproxy_prefix
    new = parsed._replace(netloc=rewritten_host)
    return urlunparse(new)


def get_authenticated_session() -> tuple[requests.Session, dict]:
    """Return a session configured for institutional access, plus the config."""
    config = get_institutional_config()
    if not config.get("enabled", False):
        return requests.Session(), config
    return _build_session(config), config


def _resolve_publisher_pdf_url(doi_or_url: str) -> list[str]:
    """Generate candidate PDF URLs for a DOI or publisher URL.

    Many publishers serve PDFs at predictable paths. We try these
    before falling back to the raw URL, since authenticated sessions
    sometimes need the direct PDF endpoint rather than the landing page.
    """
    urls = []
    url = doi_or_url

    # If it's a DOI, build the doi.org URL
    if url.startswith("10."):
        urls.append(f"https://doi.org/{url}")
        url = f"https://doi.org/{url}"

    # Nature / Springer
    if "nature.com/articles/" in url:
        urls.append(url.rstrip("/") + ".pdf")
    if "link.springer.com/article/" in url:
        urls.append(url.replace("/article/", "/content/pdf/") + ".pdf")

    # Wiley
    if "onlinelibrary.wiley.com/doi/" in url:
        urls.append(url.replace("/doi/", "/doi/pdfdirect/"))

    # bioRxiv / medRxiv
    if "biorxiv.org/content/" in url or "medrxiv.org/content/" in url:
        urls.append(url.rstrip("/") + ".full.pdf")

    # Science / AAAS
    if "science.org/doi/" in url:
        urls.append(url.replace("/doi/", "/doi/pdf/"))

    # OUP (Bioinformatics, NAR, etc.)
    if "academic.oup.com/" in url:
        urls.append(url.rstrip("/") + "?redirectedFrom=PDF")

    # The original URL as final fallback
    if url not in urls:
        urls.append(url)

    return urls


def download_with_institutional_access(
    url: str,
    dest: Path,
    timeout: int = 30,
) -> Path | None:
    """Download a URL using institutional access if configured.

    Tries in order:
      1. EZproxy-rewritten URL with cookies/proxy
      2. Publisher-specific PDF URLs with institutional session
      3. Direct URL with cookies/proxy (OpenAthens/CAS sessions)
      4. Plain unauthenticated request (fallback)
    """
    config = get_institutional_config()

    if not config.get("enabled", False):
        return _try_download(url, dest, requests.Session(), timeout)

    session = _build_session(config)
    ezproxy = config.get("ezproxy_prefix", "")

    # Attempt 1: EZproxy rewrite (if configured)
    if ezproxy:
        proxy_url = rewrite_url_for_ezproxy(url, ezproxy)
        result = _try_download(proxy_url, dest, session, timeout)
        if result:
            return result

    # Attempt 2: Publisher-specific PDF URLs with institutional session
    for pdf_url in _resolve_publisher_pdf_url(url):
        result = _try_download(pdf_url, dest, session, timeout)
        if result:
            return result

    # Attempt 3: Plain fallback
    return _try_download(url, dest, requests.Session(), timeout)


def _try_download(url: str, dest: Path, session: requests.Session, timeout: int) -> Path | None:
    """Attempt a single download. Returns path on success, None on failure."""
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None

        content_type = resp.headers.get("content-type", "").lower()

        # Verify it's actually a PDF (not a login page)
        if "pdf" in content_type:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            return dest

        # Some servers don't set content-type; check magic bytes
        if len(resp.content) > 10000 and resp.content[:5] == b"%PDF-":
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            return dest

    except Exception:
        pass
    return None


def get_startup_status() -> dict:
    """Quick check of institutional access readiness — used on first tool call.

    Returns a status dict with:
      - ready: bool — True if cookies exist and are non-empty
      - message: str — human-readable status/setup instructions
    """
    config = get_institutional_config()

    if not config.get("enabled", False):
        return {
            "ready": False,
            "message": (
                "Institutional access is DISABLED.\n"
                "To access paywalled papers (Nature, Wiley, etc.) via CWRU:\n"
                "  1. Run:  python tools/mcp/export_cookies.py\n"
                "  2. Set \"enabled\": true in tools/mcp/config.json\n"
                "  3. Restart Claude Code to reload the MCP server.\n"
                "Without this, only open-access papers (arXiv, bioRxiv) can be downloaded."
            ),
        }

    cookie_file = config.get("cookie_file", "")
    if cookie_file:
        from .database import MCP_ROOT
        cookie_path = Path(cookie_file)
        if not cookie_path.is_absolute():
            cookie_path = MCP_ROOT / cookie_file
        if not cookie_path.exists():
            return {
                "ready": False,
                "message": (
                    f"Institutional access is enabled but cookie file not found: {cookie_path}\n"
                    "Run:  python tools/mcp/export_cookies.py\n"
                    "Then restart Claude Code."
                ),
            }
        # Check if cookie file has content
        content = cookie_path.read_text().strip()
        data_lines = [l for l in content.splitlines() if l.strip() and not l.startswith("#")]
        if not data_lines:
            return {
                "ready": False,
                "message": (
                    f"Cookie file exists but is empty: {cookie_path}\n"
                    "Re-run:  python tools/mcp/export_cookies.py"
                ),
            }

        return {
            "ready": True,
            "cookies": len(data_lines),
            "message": f"Institutional access ready ({len(data_lines)} cookies loaded).",
        }

    # Enabled but no cookie file configured — maybe using proxy only
    proxy = config.get("proxy", "")
    if proxy:
        return {
            "ready": True,
            "message": f"Institutional access ready (proxy: {proxy}).",
        }

    return {
        "ready": False,
        "message": (
            "Institutional access is enabled but no cookie_file or proxy configured.\n"
            "Run:  python tools/mcp/export_cookies.py"
        ),
    }


def check_access(test_doi: str = "10.1038/s41592-024-02410-7") -> dict:
    """Test institutional access by trying to reach a known paywalled paper.

    Returns status dict with what worked and what didn't.
    """
    config = get_institutional_config()
    result = {
        "enabled": config.get("enabled", False),
        "ezproxy_prefix": config.get("ezproxy_prefix", ""),
        "cookie_file": config.get("cookie_file", ""),
        "proxy": config.get("proxy", ""),
        "tests": {},
    }

    url = f"https://doi.org/{test_doi}"
    session = _build_session(config) if config.get("enabled") else requests.Session()

    # Test direct access
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        is_pdf = "pdf" in resp.headers.get("content-type", "").lower()
        result["tests"]["direct"] = {
            "status": resp.status_code,
            "is_pdf": is_pdf,
            "content_type": resp.headers.get("content-type", ""),
        }
    except Exception as e:
        result["tests"]["direct"] = {"error": str(e)}

    # Test with institutional session
    if config.get("enabled"):
        ezproxy = config.get("ezproxy_prefix", "")
        if ezproxy:
            proxy_url = rewrite_url_for_ezproxy(url, ezproxy)
            try:
                resp = session.get(proxy_url, timeout=15, allow_redirects=True)
                is_pdf = "pdf" in resp.headers.get("content-type", "").lower()
                has_pdf_magic = len(resp.content) > 100 and resp.content[:5] == b"%PDF-"
                result["tests"]["ezproxy"] = {
                    "rewritten_url": proxy_url,
                    "status": resp.status_code,
                    "is_pdf": is_pdf or has_pdf_magic,
                    "content_type": resp.headers.get("content-type", ""),
                    "size_bytes": len(resp.content),
                }
            except Exception as e:
                result["tests"]["ezproxy"] = {"error": str(e)}

        try:
            resp = session.get(url, timeout=15, allow_redirects=True)
            is_pdf = "pdf" in resp.headers.get("content-type", "").lower()
            result["tests"]["session"] = {
                "status": resp.status_code,
                "is_pdf": is_pdf,
                "content_type": resp.headers.get("content-type", ""),
            }
        except Exception as e:
            result["tests"]["session"] = {"error": str(e)}

    return result
