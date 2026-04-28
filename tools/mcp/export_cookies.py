"""
Export browser cookies for institutional (CWRU) library access.

Three modes:
  1. --browser chrome|firefox  — extract cookies directly from browser profile
  2. --manual                  — open a URL, you log in, cookies are captured
  3. (no args)                 — auto-detect Chrome or Firefox

Saves to tools/mcp/data/cookies.txt in Netscape format.

Usage:
    python tools/mcp/export_cookies.py
    python tools/mcp/export_cookies.py --browser chrome
    python tools/mcp/export_cookies.py --browser firefox
    python tools/mcp/export_cookies.py --manual
"""

import argparse
import http.cookiejar
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT = DATA_DIR / "cookies.txt"

# Domains whose cookies we need for publisher access via OpenAthens/CAS
RELEVANT_DOMAINS = [
    ".case.edu",
    "login.case.edu",
    ".openathens.net",
    ".nature.com",
    ".springer.com",
    ".springerlink.com",
    ".wiley.com",
    ".onlinelibrary.wiley.com",
    ".oup.com",
    ".academic.oup.com",
    ".sciencedirect.com",
    ".elsevier.com",
    ".cell.com",
    ".science.org",
    ".aaas.org",
    ".pnas.org",
    ".tandfonline.com",
    ".ieee.org",
    ".ieeexplore.ieee.org",
    ".acm.org",
    ".dl.acm.org",
    ".jstor.org",
    ".ebscohost.com",
    ".proquest.com",
    ".oxfordjournals.org",
    ".biomedcentral.com",
    ".bmc.com",
    ".frontiersin.org",
    ".mdpi.com",
    ".plos.org",
    ".bioinformatics.org",
]


def find_chrome_cookies_db() -> Path | None:
    """Locate Chrome's Cookies database."""
    candidates = [
        Path.home() / ".config/google-chrome/Default/Cookies",
        Path.home() / ".config/google-chrome/Profile 1/Cookies",
        Path.home() / ".config/chromium/Default/Cookies",
        Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies",
        Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Network/Cookies",
        Path.home() / ".config/google-chrome/Default/Network/Cookies",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_firefox_cookies_db() -> Path | None:
    """Locate Firefox's cookies.sqlite."""
    ff_dirs = [
        Path.home() / ".mozilla/firefox",
        Path.home() / "Library/Application Support/Firefox/Profiles",
        Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles",
    ]
    for ff_dir in ff_dirs:
        if not ff_dir.exists():
            continue
        # Find default profile
        for profile in sorted(ff_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            db = profile / "cookies.sqlite"
            if db.exists():
                return db
    return None


def extract_firefox_cookies(db_path: Path) -> list[dict]:
    """Extract relevant cookies from Firefox's cookies.sqlite."""
    # Copy to temp file to avoid locking issues
    tmp = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(db_path, tmp)

    cookies = []
    try:
        conn = sqlite3.connect(str(tmp))
        # Build WHERE clause for relevant domains
        domain_clauses = " OR ".join(
            f"host LIKE '%{d.lstrip('.')}'" for d in RELEVANT_DOMAINS
        )
        rows = conn.execute(
            f"SELECT host, path, isSecure, expiry, name, value "
            f"FROM moz_cookies WHERE {domain_clauses}"
        ).fetchall()
        for host, path, secure, expiry, name, value in rows:
            cookies.append({
                "domain": host,
                "path": path or "/",
                "secure": bool(secure),
                "expiry": expiry,
                "name": name,
                "value": value,
            })
        conn.close()
    finally:
        tmp.unlink(missing_ok=True)
    return cookies


def extract_chrome_cookies(db_path: Path) -> list[dict]:
    """Extract relevant cookies from Chrome's Cookies DB.

    Note: Chrome encrypts cookie values on Linux (v80+). If decryption
    fails, we skip those cookies — the manual method is recommended instead.
    """
    tmp = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(db_path, tmp)

    cookies = []
    try:
        conn = sqlite3.connect(str(tmp))
        domain_clauses = " OR ".join(
            f"host_key LIKE '%{d.lstrip('.')}'" for d in RELEVANT_DOMAINS
        )
        rows = conn.execute(
            f"SELECT host_key, path, is_secure, expires_utc, name, value, encrypted_value "
            f"FROM cookies WHERE {domain_clauses}"
        ).fetchall()

        for host, path, secure, expiry, name, value, enc_value in rows:
            # Try plaintext first
            if value:
                cookie_val = value
            elif enc_value:
                cookie_val = _try_decrypt_chrome(enc_value)
                if not cookie_val:
                    continue  # Can't decrypt, skip
            else:
                continue

            # Chrome stores expiry as microseconds since 1601-01-01
            if expiry and expiry > 0:
                unix_expiry = (expiry / 1_000_000) - 11644473600
            else:
                unix_expiry = 0

            cookies.append({
                "domain": host,
                "path": path or "/",
                "secure": bool(secure),
                "expiry": int(unix_expiry),
                "name": name,
                "value": cookie_val,
            })
        conn.close()
    finally:
        tmp.unlink(missing_ok=True)
    return cookies


def _try_decrypt_chrome(encrypted: bytes) -> str | None:
    """Attempt to decrypt Chrome cookies on Linux.

    Chrome on Linux uses AES-128-CBC with a key derived from 'peanuts'
    (or from the system keyring). This is a best-effort attempt.
    """
    if not encrypted:
        return None

    # v10 encryption (Linux default without keyring)
    if encrypted[:3] == b"v10":
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            import hashlib

            # Default password is 'peanuts', 1 iteration, 16-byte key
            key = hashlib.pbkdf2_hmac("sha1", b"peanuts", b"saltysalt", 1, dklen=16)
            iv = b" " * 16
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted[3:]) + decryptor.finalize()
            # Remove PKCS7 padding
            pad_len = decrypted[-1]
            if pad_len <= 16:
                decrypted = decrypted[:-pad_len]
            return decrypted.decode("utf-8", errors="replace")
        except Exception:
            return None

    # v11 (uses system keyring — harder to decrypt without it)
    return None


def write_netscape_cookies(cookies: list[dict], output: Path):
    """Write cookies in Netscape cookie.txt format."""
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Netscape HTTP Cookie File", f"# Exported {datetime.now().isoformat()}", ""]
    for c in cookies:
        http_only = "TRUE" if c["domain"].startswith(".") else "FALSE"
        secure = "TRUE" if c["secure"] else "FALSE"
        lines.append(
            f"{c['domain']}\t{http_only}\t{c['path']}\t{secure}\t{c['expiry']}\t{c['name']}\t{c['value']}"
        )
    output.write_text("\n".join(lines) + "\n")


def export_from_browser(browser: str) -> int:
    """Export cookies from a browser profile."""
    if browser == "firefox":
        db = find_firefox_cookies_db()
        if not db:
            print("ERROR: Firefox cookies database not found.")
            print("Make sure Firefox is installed and you've visited publisher sites while logged in.")
            return 1
        print(f"Found Firefox cookies: {db}")
        cookies = extract_firefox_cookies(db)
    elif browser == "chrome":
        db = find_chrome_cookies_db()
        if not db:
            print("ERROR: Chrome cookies database not found.")
            return 1
        print(f"Found Chrome cookies: {db}")
        cookies = extract_chrome_cookies(db)
        if not cookies:
            print("WARNING: No cookies extracted. Chrome may encrypt cookies.")
            print("Try: python export_cookies.py --browser firefox")
            print("  or: python export_cookies.py --manual")
            return 1
    else:
        print(f"Unknown browser: {browser}")
        return 1

    write_netscape_cookies(cookies, OUTPUT)
    print(f"\nExported {len(cookies)} cookies to {OUTPUT}")

    # Show which domains we got
    domains = sorted(set(c["domain"] for c in cookies))
    print(f"\nDomains covered ({len(domains)}):")
    for d in domains:
        print(f"  {d}")

    return 0


def export_manual():
    """Guide user through manual cookie export."""
    print("=" * 60)
    print("  Manual Cookie Export for CWRU Library Access")
    print("=" * 60)
    print()
    print("Step 1: Install a cookie export browser extension:")
    print("  Chrome: 'Get cookies.txt LOCALLY' extension")
    print("  Firefox: 'cookies.txt' by Lennon Hill")
    print()
    print("Step 2: Open your browser and go to:")
    print("  https://login.case.edu/cas/login")
    print("  Log in with your CWRU credentials.")
    print()
    print("Step 3: Visit a paywalled journal to trigger OpenAthens:")
    print("  e.g., https://www.nature.com/articles/s41592-024-02410-7")
    print("  (click 'Access through your institution' if prompted)")
    print()
    print("Step 4: Use the extension to export cookies for the current site.")
    print("  Then visit login.case.edu and export those cookies too.")
    print("  Save/append all exports to a single file.")
    print()
    print(f"Step 5: Save the cookies.txt file to:")
    print(f"  {OUTPUT}")
    print()
    print("Or, if you already have a cookies.txt file, copy it now:")
    print(f"  cp /path/to/cookies.txt {OUTPUT}")
    print()

    # Wait for user
    answer = input("Have you saved the cookies file? [y/N] ").strip().lower()
    if answer == "y" and OUTPUT.exists():
        # Count cookies
        count = sum(1 for line in OUTPUT.read_text().splitlines()
                    if line.strip() and not line.startswith("#"))
        print(f"\nFound {count} cookies in {OUTPUT}")
        print("Done! Enable institutional access in config.json:")
        print('  "institutional_access": { "enabled": true, ... }')
        return 0
    elif answer == "y":
        print(f"\nFile not found at {OUTPUT}")
        return 1
    else:
        print("\nNo worries. Run this script again when ready.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Export browser cookies for CWRU library access")
    parser.add_argument("--browser", choices=["chrome", "firefox"],
                        help="Extract from browser profile directly")
    parser.add_argument("--manual", action="store_true",
                        help="Guided manual export with browser extension")
    args = parser.parse_args()

    if args.manual:
        return export_manual()

    if args.browser:
        return export_from_browser(args.browser)

    # Auto-detect
    print("Auto-detecting browser...")
    for browser in ["firefox", "chrome"]:
        db_finder = find_firefox_cookies_db if browser == "firefox" else find_chrome_cookies_db
        if db_finder():
            print(f"Found {browser}")
            return export_from_browser(browser)

    print("No browser cookies database found. Using manual mode.")
    return export_manual()


if __name__ == "__main__":
    sys.exit(main())
