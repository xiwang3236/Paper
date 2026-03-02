#!/usr/bin/env python3
"""Fetch first figures from papers in a weekly report and generate a newspaper-style HTML page.

Stdlib only — no pip installs required.

Usage:
    python tools/figures/fetch_figures.py --report reports/WEEKLY_2026-02-01.md
    python tools/figures/fetch_figures.py --report reports/WEEKLY_2026-02-01.md --output custom.html
    python tools/figures/fetch_figures.py --report reports/WEEKLY_2026-02-01.md --skip-download
"""

import argparse
import base64
import mimetypes
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 30

PREDICTION_KEYWORDS = {
    "gene expression prediction",
    "cell-type deconvolution",
    "cell type deconvolution",
    "transcriptome reconstruction",
    "spatial proteomics prediction",
}


def _classify_topic(paper):
    """Classify a paper as 'prediction' or 'analysis' based on keywords."""
    for kw in paper.get("keywords", []):
        kw_lower = kw.lower()
        for pred_kw in PREDICTION_KEYWORDS:
            if pred_kw in kw_lower:
                return "prediction"
    return "analysis"


# ---------------------------------------------------------------------------
# 1. Parse weekly report
# ---------------------------------------------------------------------------

def parse_weekly_report(path: str) -> list[dict]:
    """Extract papers from a weekly report markdown file."""
    text = Path(path).read_text(encoding="utf-8")
    papers = []

    # Pattern: - [**Title**](URL) — DATE, *Publisher*   OR   — DATE (arXiv)
    entry_re = re.compile(
        r"^- \[\*\*(.+?)\*\*\]\((.+?)\)\s*—\s*(\d{4}-\d{2}-\d{2})(?:,\s*\*(.+?)\*)?",
        re.MULTILINE,
    )
    # Keywords line: backtick-delimited tags
    kw_re = re.compile(r"`([^`]+)`")

    matches = list(entry_re.finditer(text))
    for i, m in enumerate(matches):
        title, url, date, publisher = m.group(1), m.group(2), m.group(3), m.group(4)
        # Text between this match and the next (or end)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        keywords = kw_re.findall(block)
        # Summary is the last non-empty paragraph (after keywords line)
        lines = [l.strip() for l in block.strip().splitlines()
                 if l.strip() and not l.strip().startswith("`") and not l.strip().startswith("#")]
        summary = lines[-1] if lines else ""

        papers.append({
            "title": title,
            "url": url,
            "date": date,
            "publisher": publisher or "arXiv",
            "keywords": keywords,
            "summary": summary,
        })

    return papers


# ---------------------------------------------------------------------------
# 2. HTML parser helpers
# ---------------------------------------------------------------------------

class FigureImageFinder(HTMLParser):
    """Find the first <img> inside a <figure> tag, or the first large image."""

    def __init__(self):
        super().__init__()
        self.in_figure = False
        self.figure_img = None
        self.all_imgs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "figure":
            self.in_figure = True
        if tag == "img" and "src" in d:
            self.all_imgs.append(d["src"])
            if self.in_figure and self.figure_img is None:
                self.figure_img = d["src"]

    def handle_endtag(self, tag):
        if tag == "figure":
            self.in_figure = False

    @property
    def best_image(self):
        return self.figure_img or (self.all_imgs[0] if self.all_imgs else None)


class ArxivFigureFinder(HTMLParser):
    """Find first figure image in arxiv HTML papers."""

    def __init__(self):
        super().__init__()
        self.in_figure = False
        self.figure_img = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = d.get("class", "")
        if tag in ("figure", "div") and "ltx_figure" in cls:
            self.in_figure = True
            self.depth += 1
        if tag == "img" and self.in_figure and self.figure_img is None:
            src = d.get("src", "")
            if src:
                self.figure_img = src

    def handle_endtag(self, tag):
        if tag in ("figure", "div") and self.in_figure:
            self.depth -= 1
            if self.depth <= 0:
                self.in_figure = False


# ---------------------------------------------------------------------------
# 3. Fetch figure URLs
# ---------------------------------------------------------------------------

def _fetch_url(url: str) -> str:
    """Fetch URL content as text."""
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _fetch_bytes(url: str) -> tuple[bytes, str]:
    """Fetch URL content as bytes, return (data, content_type)."""
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=TIMEOUT) as resp:
        ct = resp.headers.get("Content-Type", "image/png")
        return resp.read(), ct


def fetch_figure_url_arxiv(paper_url: str) -> str | None:
    """Fetch first figure from arxiv HTML rendering."""
    arxiv_id = paper_url.rstrip("/").split("/")[-1]
    html_url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        html = _fetch_url(html_url)
    except Exception:
        return None

    parser = ArxivFigureFinder()
    parser.feed(html)
    if parser.figure_img:
        # Base URL needs trailing slash so relative paths resolve correctly
        return urljoin(html_url + "/", parser.figure_img)
    return None


def _nature_figure_url(doi: str) -> str | None:
    """Construct Nature/Springer figure URL from DOI.

    Nature renders figures via JS, so we construct the MediaObjects URL directly.
    Pattern: media.springernature.com/lw685/springer-static/image/art%3A{doi}/MediaObjects/{id}_Fig1_HTML.png
    """
    # doi like 10.1038/s41467-026-68487-0
    parts = doi.split("/", 1)
    if len(parts) != 2:
        return None
    suffix = parts[1]  # e.g. s41467-026-68487-0
    # Build MediaObjects ID: replace - with _ in the suffix
    # s41467-026-68487-0 -> 41467_2026_68487 (strip leading 's', expand 2-digit year)
    m = re.match(r"s?(\d+)-(\d+)-(\d+)-\d+", suffix)
    if not m:
        return None
    journal_id, year_short, article_num = m.group(1), m.group(2), m.group(3)
    # Expand 2-digit year to 4-digit
    if len(year_short) == 3:
        year = "2" + year_short  # e.g. 026 -> 2026
    elif len(year_short) <= 2:
        yr = int(year_short)
        year = str(2000 + yr) if yr < 100 else year_short
    else:
        year = year_short
    obj_id = f"{journal_id}_{year}_{article_num}_Fig1_HTML"
    encoded_doi = doi.replace("/", "%2F")
    fig_url = (
        f"https://media.springernature.com/lw685/springer-static/image/"
        f"art%3A{encoded_doi}/MediaObjects/{obj_id}.png"
    )
    # Verify it exists
    try:
        req = Request(fig_url, method="HEAD", headers=HEADERS)
        with urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                return fig_url
    except Exception:
        pass
    return None


def _resolve_doi(doi_url: str) -> str | None:
    """Resolve a DOI URL to its final redirect target without downloading the page."""
    try:
        req = Request(doi_url, headers=HEADERS)
        with urlopen(req, timeout=TIMEOUT) as resp:
            return resp.url
    except Exception:
        return None


def fetch_figure_url_doi(paper_url: str) -> str | None:
    """Fetch first figure from a DOI/journal page."""
    # Try Nature/Springer direct construction first
    doi_match = re.search(r"(10\.\d{4,}/[^\s]+)$", paper_url)
    if doi_match:
        doi = doi_match.group(1)
        if "10.1038/" in doi:
            url = _nature_figure_url(doi)
            if url:
                return url

    # For OUP and other publishers, resolve DOI and try scraping
    final_url = paper_url
    if "doi.org" in paper_url:
        resolved = _resolve_doi(paper_url)
        if resolved:
            final_url = resolved

    try:
        html = _fetch_url(final_url)
    except Exception:
        return None

    parser = FigureImageFinder()
    parser.feed(html)
    img = parser.best_image
    if img:
        # Filter out tracking pixels, logos, ads
        if any(x in img.lower() for x in ("track", "pixel", "logo", "ad?", "doubleclick", "beacon")):
            return None
        return urljoin(final_url, img)
    return None


def _oup_graphical_abstract(doi_url: str) -> str | None:
    """Try to fetch OUP graphical abstract or first figure via their specific patterns."""
    # OUP pages often block scrapers; try the article figures page
    resolved = _resolve_doi(doi_url)
    if not resolved or "academic.oup.com" not in resolved:
        return None
    # Try appending /figures to get the figures-only page
    figs_url = resolved.rstrip("/")
    if "#" in figs_url:
        figs_url = figs_url.split("#")[0]
    # OUP figure images often at: oup.silverchair-cdn.com/.../article_id/fig1.png
    # This is hard to predict, so we fall back to scraping
    try:
        req = Request(figs_url, headers={**HEADERS, "Accept": "text/html"})
        with urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        parser = FigureImageFinder()
        parser.feed(html)
        img = parser.best_image
        if img:
            return urljoin(figs_url, img)
    except Exception:
        pass
    return None


def fetch_figure_url(paper_url: str) -> str | None:
    """Dispatch to the right fetcher based on URL."""
    if "arxiv.org" in paper_url:
        return fetch_figure_url_arxiv(paper_url)
    # Try OUP-specific approach for Bioinformatics etc.
    if "10.1093/" in paper_url:
        url = _oup_graphical_abstract(paper_url)
        if url:
            return url
    return fetch_figure_url_doi(paper_url)


# ---------------------------------------------------------------------------
# 4. Download images
# ---------------------------------------------------------------------------

def _sanitize_id(url: str) -> str:
    """Create a filesystem-safe ID from a URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", path) or "unknown"


def _placeholder_svg() -> bytes:
    """Generate a placeholder SVG for papers without figures."""
    return (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
        b'<rect width="400" height="300" fill="#f0f0f0"/>'
        b'<text x="200" y="150" text-anchor="middle" font-family="sans-serif" '
        b'font-size="18" fill="#999">No figure available</text></svg>'
    )


def download_figure(paper_url: str, cache_dir: str, skip_download: bool = False) -> tuple[str, str, bool]:
    """Download the first figure for a paper. Returns (file_path, mime_type, has_figure).

    If skip_download is True or download fails, returns a placeholder with has_figure=False.
    """
    paper_id = _sanitize_id(paper_url)
    paper_dir = os.path.join(cache_dir, paper_id)
    os.makedirs(paper_dir, exist_ok=True)

    # Check cache — placeholder SVGs count as no-figure
    for existing in os.listdir(paper_dir):
        if existing.startswith("figure1"):
            fpath = os.path.join(paper_dir, existing)
            mime = mimetypes.guess_type(fpath)[0] or "image/png"
            is_placeholder = (existing == "figure1.svg" and
                              Path(fpath).read_bytes() == _placeholder_svg())
            return fpath, mime, not is_placeholder

    if skip_download:
        return _save_placeholder(paper_dir)

    print(f"  Fetching figure for: {paper_url}")
    fig_url = fetch_figure_url(paper_url)
    if not fig_url:
        print(f"    No figure found")
        return _save_placeholder(paper_dir)

    try:
        data, ct = _fetch_bytes(fig_url)
        # Determine extension
        ext = _ext_from_url_or_ct(fig_url, ct)
        fpath = os.path.join(paper_dir, f"figure1{ext}")
        Path(fpath).write_bytes(data)
        mime = mimetypes.guess_type(fpath)[0] or ct.split(";")[0].strip()
        print(f"    Saved: {fpath}")
        return fpath, mime, True
    except Exception as e:
        print(f"    Download failed: {e}")
        return _save_placeholder(paper_dir)


def _ext_from_url_or_ct(url: str, content_type: str) -> str:
    """Guess file extension from URL path or content-type."""
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and ext.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
        return ext.lower()
    ct = content_type.split(";")[0].strip().lower()
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
        "image/webp": ".webp",
    }
    return mapping.get(ct, ".png")


def _save_placeholder(paper_dir: str) -> tuple[str, str, bool]:
    fpath = os.path.join(paper_dir, "figure1.svg")
    Path(fpath).write_bytes(_placeholder_svg())
    return fpath, "image/svg+xml", False


# ---------------------------------------------------------------------------
# 5. Generate HTML
# ---------------------------------------------------------------------------

def _img_to_base64(fpath: str, mime: str) -> str:
    data = Path(fpath).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weekly Figures — {date}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; background: #FFFFFF; color: #000000; padding: 0; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 0 1rem 2rem; }}
  .banner {{ background: #8B1E1E; text-align: center; padding: 1rem 1rem 0.6rem; margin: 0 0 0; }}
  .banner h1 {{ color: #FFFFFF; font-size: 1.4rem; font-weight: bold; letter-spacing: 0.05em; margin-bottom: 0.3rem; }}
  .banner h1 a {{ color: #FFFFFF; text-decoration: none; }}
  .banner h1 a:hover {{ text-decoration: underline; }}
  .tagline {{ text-align: center; font-size: 1.8rem; font-weight: bold; margin: 1.2rem 0 0; }}
  .tagline .red {{ color: #8B1E1E; }}
  .tagline-sub {{ text-align: center; font-size: 1.8rem; font-weight: normal; color: #000000; margin: 0 0 0.2rem; }}
  .header-rule {{ border: none; border-top: 1px solid #8B1E1E; margin: 0.3rem auto; width: 60%; }}
  .header-rule2 {{ border: none; border-top: 1px solid #8B1E1E; margin: 0.15rem auto 0.5rem; width: 60%; }}
  .signature {{ text-align: center; font-size: 0.72rem; color: #4A4A4A; margin-bottom: 0.3rem; }}
  .signature a {{ color: #8B1E1E; text-decoration: none; }}
  .signature a:hover {{ text-decoration: underline; }}
  .subtitle {{ text-align: center; color: #4A4A4A; font-size: 0.72rem; font-style: italic; margin-bottom: 2rem; }}
  .section-title {{ font-size: 1rem; font-weight: bold; color: #000000; margin: 1.8rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 2px solid #8B1E1E; }}
  .grid {{ display: grid; grid-template-columns: 1fr; gap: 1.2rem; }}
  @media (min-width: 900px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
  .card {{ background: #FFFFFF; border: 1px solid #D9D9D9; border-top: 3px solid #8B1E1E; overflow: hidden; display: flex; flex-direction: column; }}
  .card img {{ width: 100%; height: 260px; object-fit: contain; background: #F5F5F5; border-bottom: 1px solid #D9D9D9; }}
  .card-body {{ padding: 0.8rem 1rem; flex: 1; }}
  .card-body h2 {{ font-size: 0.95rem; font-weight: bold; margin-bottom: 0.3rem; line-height: 1.3; }}
  .card-body h2 a {{ color: #8B1E1E; text-decoration: none; }}
  .card-body h2 a:hover {{ text-decoration: underline; }}
  .meta {{ font-size: 0.72rem; color: #4A4A4A; margin-bottom: 0.4rem; }}
  .keywords {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.4rem; }}
  .kw {{ background: #F2F2F2; color: #4A4A4A; font-size: 0.7rem; font-weight: bold; padding: 2px 7px; border: 1px solid #D9D9D9; }}
  .summary {{ font-size: 0.78rem; line-height: 1.5; color: #000000; }}
  .section-divider {{ color: #4A4A4A; font-size: 0.72rem; margin: 2rem 0 1rem; padding-bottom: 0.3rem; border-bottom: 1px solid #D9D9D9; }}
  .nofig-grid {{ display: grid; grid-template-columns: 1fr; gap: 1.2rem; }}
  .card-nofig {{ background: #FFFFFF; border: 1px solid #D9D9D9; border-left: 3px solid #8B1E1E; padding: 0.8rem 1rem; }}
  .card-nofig h2 {{ font-size: 0.95rem; font-weight: bold; margin-bottom: 0.3rem; line-height: 1.3; }}
  .card-nofig h2 a {{ color: #8B1E1E; text-decoration: none; }}
  .card-nofig h2 a:hover {{ text-decoration: underline; }}
  .card-nofig .meta {{ font-size: 0.72rem; color: #4A4A4A; margin-bottom: 0.4rem; }}
  .card-nofig .keywords {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.4rem; }}
  .card-nofig .summary {{ font-size: 0.78rem; line-height: 1.5; color: #000000; }}
  .highlight-box {{ background: #FDF6F6; border: 1px solid #D9D9D9; border-top: 3px solid #8B1E1E; padding: 1.2rem 1.5rem; margin: 1.5rem 0; }}
  .highlight-title {{ font-size: 1rem; font-weight: bold; color: #8B1E1E; margin-bottom: 0.8rem; }}
  .highlight-table {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; margin-bottom: 0.8rem; }}
  .highlight-table th {{ text-align: left; padding: 0.35rem 0.5rem; border-bottom: 2px solid #8B1E1E; font-size: 0.72rem; color: #4A4A4A; }}
  .highlight-table td {{ padding: 0.35rem 0.5rem; border-bottom: 1px solid #D9D9D9; }}
  .highlight-table a {{ color: #8B1E1E; text-decoration: none; }}
  .highlight-table a:hover {{ text-decoration: underline; }}
  .highlight-notes {{ font-size: 0.75rem; color: #4A4A4A; line-height: 1.6; margin-top: 0.5rem; }}
  .highlight-notes li {{ margin-bottom: 0.3rem; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="banner"><h1><a href="https://github.com/xiwang3236/Paper">AI-Scholar</a></h1></div>
<div class="container">
<p class="tagline"><span class="red">Predictive Modeling in Spatial Omics</span></p>
<p class="tagline-sub">Recent Advances</p>
<p class="signature">&#9993; <a href="mailto:xxw962@case.edu">xxw962@case.edu</a> &nbsp;&middot;&nbsp; &#128736; <a href="https://github.com/xiwang3236/paper">GitHub</a></p>
<hr class="header-rule">
<hr class="header-rule2">
<p class="subtitle">{date}</p>
{highlight_section}
{prediction_section}
{analysis_section}
</div>
</body>
</html>
"""

CARD_TEMPLATE = """\
<div class="card">
  <img src="{img_src}" alt="Figure from {title}">
  <div class="card-body">
    <h2><a href="{url}">{title}</a></h2>
    <div class="meta">{date} &middot; {publisher}</div>
    <div class="keywords">{kw_html}</div>
    <p class="summary">{summary}</p>
  </div>
</div>"""

CARD_NOFIG_TEMPLATE = """\
<div class="card-nofig">
  <h2><a href="{url}">{title}</a></h2>
  <div class="meta">{date} &middot; {publisher}</div>
  <div class="keywords">{kw_html}</div>
  <p class="summary">{summary}</p>
</div>"""

NOFIG_SECTION_TEMPLATE = """\
<p class="section-divider">Papers without figures</p>
<div class="nofig-grid">
{cards}
</div>"""

HIGHLIGHT_SECTION_TEMPLATE = """\
<div class="highlight-box">
  <div class="highlight-title">Topic Highlight: Gene Normalization Methods</div>
  <table class="highlight-table">
    <tr><th>Paper</th><th>Normalization Method</th><th>Applied To</th><th>Tools</th></tr>
{rows}
  </table>
  <div class="highlight-notes">
    <strong>Key Takeaways</strong>
    <ul>
      <li>Most prediction methods use <strong>log transformation + min-max scaling</strong> or <strong>SCTransform</strong> for target gene expression.</li>
      <li><strong>Total count normalization</strong> followed by log transform is the most common baseline; Harmony adds batch correction across slices.</li>
      <li><strong>STRank</strong> challenges conventional normalization — rank-based losses may preserve statistical properties better than count normalization.</li>
      <li>Benchmarking studies show method-specific normalization choices can <strong>significantly affect prediction performance</strong>.</li>
    </ul>
  </div>
</div>"""


def _build_normalization_highlight(report_path: str) -> str:
    """Build the gene normalization highlight section from gene_normalization_methods.md."""
    report_dir = os.path.dirname(os.path.abspath(report_path))
    md_path = os.path.join(report_dir, "gene_normalization_methods.md")
    if not os.path.isfile(md_path):
        return ""
    text = Path(md_path).read_text(encoding="utf-8")
    # Parse table rows: | [Paper](url) | Method | Applied To | Tools |
    row_re = re.compile(
        r"^\|\s*\[(.+?)\]\((.+?)\)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
        re.MULTILINE,
    )
    rows = []
    for m in row_re.finditer(text):
        name, url, method, applied_to, tools = (
            m.group(1), m.group(2), m.group(3), m.group(4), m.group(5),
        )
        # Skip image normalization methods — only include gene expression normalization
        if "image" in applied_to.lower():
            continue
        rows.append(
            f'    <tr><td><a href="{url}">{name}</a></td>'
            f"<td>{method}</td><td>{applied_to}</td><td>{tools}</td></tr>"
        )
    if not rows:
        return ""
    return HIGHLIGHT_SECTION_TEMPLATE.format(rows="\n".join(rows))


def _render_card(paper: dict, template: str, img_src: str | None = None) -> str:
    kw_html = "".join(f'<span class="kw">{k}</span>' for k in paper["keywords"])
    fmt = dict(
        title=paper["title"].replace("&", "&amp;").replace("<", "&lt;"),
        url=paper["url"],
        date=paper["date"],
        publisher=paper["publisher"],
        kw_html=kw_html,
        summary=paper["summary"].replace("&", "&amp;").replace("<", "&lt;"),
    )
    if img_src is not None:
        fmt["img_src"] = img_src
    return template.format(**fmt)


SECTION_TEMPLATE = """\
<h2 class="section-title">{title}</h2>
<div class="grid">
{cards}
</div>"""


def _render_topic_section(title: str, fig_items: list, nofig_items: list) -> str:
    """Render a topic section with figure cards and no-figure cards."""
    if not fig_items and not nofig_items:
        return ""
    parts = [f'<h2 class="section-title">{title}</h2>']
    if fig_items:
        fig_cards = []
        for paper, fpath, mime in fig_items:
            fig_cards.append(_render_card(paper, CARD_TEMPLATE, img_src=_img_to_base64(fpath, mime)))
        parts.append(f'<div class="grid">\n{chr(10).join(fig_cards)}\n</div>')
    if nofig_items:
        nofig_cards = [_render_card(p, CARD_NOFIG_TEMPLATE) for p in nofig_items]
        parts.append(NOFIG_SECTION_TEMPLATE.format(cards="\n".join(nofig_cards)))
    return "\n".join(parts)


def generate_html(papers: list[dict], figures: list[tuple[str, str, bool]],
                  report_date: str, report_path: str = "") -> str:
    pred_fig, pred_nofig = [], []
    analysis_fig, analysis_nofig = [], []

    for paper, (fpath, mime, has_figure) in zip(papers, figures):
        topic = _classify_topic(paper)
        if topic == "prediction":
            if has_figure:
                pred_fig.append((paper, fpath, mime))
            else:
                pred_nofig.append(paper)
        else:
            if has_figure:
                analysis_fig.append((paper, fpath, mime))
            else:
                analysis_nofig.append(paper)

    highlight_section = _build_normalization_highlight(report_path) if report_path else ""
    prediction_section = _render_topic_section(
        "Spatial Omics Prediction Methods", pred_fig, pred_nofig)
    analysis_section = _render_topic_section(
        "Spatial Omics Analysis Tools", analysis_fig, analysis_nofig)

    return HTML_TEMPLATE.format(
        date=report_date,
        highlight_section=highlight_section,
        prediction_section=prediction_section,
        analysis_section=analysis_section,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate newspaper-style HTML with paper figures")
    parser.add_argument("--report", required=True, help="Path to WEEKLY_*.md report")
    parser.add_argument("--output", help="Output HTML path (default: derived from report)")
    parser.add_argument("--skip-download", action="store_true", help="Use placeholders instead of fetching")
    args = parser.parse_args()

    if not os.path.isfile(args.report):
        print(f"Error: report not found: {args.report}", file=sys.stderr)
        sys.exit(1)

    # Derive output path
    if args.output:
        out_path = args.output
    else:
        base = os.path.splitext(args.report)[0]
        out_path = base + "_figures.html"

    # Extract date from filename
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(args.report))
    report_date = date_match.group(1) if date_match else "unknown"

    # Parse
    print(f"Parsing: {args.report}")
    papers = parse_weekly_report(args.report)
    print(f"Found {len(papers)} papers")

    if not papers:
        print("No papers found in report.")
        sys.exit(0)

    # Download figures
    cache_dir = os.path.join("temp", "figures")
    os.makedirs(cache_dir, exist_ok=True)

    figures = []  # list of (path, mime, has_figure)
    for i, paper in enumerate(papers):
        print(f"[{i+1}/{len(papers)}] {paper['title'][:60]}")
        fig = download_figure(paper["url"], cache_dir, skip_download=args.skip_download)
        figures.append(fig)
        if not args.skip_download and i < len(papers) - 1:
            time.sleep(1)  # polite delay

    # Generate HTML
    html = generate_html(papers, figures, report_date, report_path=args.report)
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"\nGenerated: {out_path}")


if __name__ == "__main__":
    main()
