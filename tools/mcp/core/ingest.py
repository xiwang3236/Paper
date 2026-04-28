"""
Paper ingestion: DOI/URL resolution, PDF download, text extraction, chunking.
"""

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from .database import (
    DATA_PATH,
    PROJECT_ROOT,
    chunk_text,
    embed_chunks,
    get_collection,
    get_db,
    make_paper_id,
    store_metadata,
)
from .institutional import download_with_institutional_access

PDF_CACHE = DATA_PATH / "pdfs"
ARXIV_API = "https://export.arxiv.org/api/query"


def _remove_paper(paper_id: str):
    """Remove a paper's metadata and embeddings so it can be re-ingested."""
    conn = get_db()
    conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()
    try:
        collection = get_collection()
        # Remove all chunks for this paper
        results = collection.get(where={"paper_id": paper_id})
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass  # Collection may not have entries yet


def _resolve_doi(url: str) -> str | None:
    """Extract DOI from common paper URL patterns."""
    if not url:
        return None

    # Already a DOI
    if url.startswith("10."):
        return url

    # doi.org links
    m = re.search(r"doi\.org/(10\.\d{4,}/[^\s]+)", url)
    if m:
        return m.group(1)

    # Nature articles: nature.com/articles/sXXXXX
    m = re.search(r"nature\.com/articles/(s\d+-\d+-\d+-\w)", url)
    if m:
        return f"10.1038/{m.group(1)}"

    # arXiv
    m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,})", url)
    if m:
        return f"10.48550/arXiv.{m.group(1)}"

    # bioRxiv
    m = re.search(r"biorxiv\.org/content/(10\.\d{4,}/[\d.]+)", url)
    if m:
        return m.group(1)

    # OUP (academic.oup.com) — DOI often in URL path
    m = re.search(r"academic\.oup\.com/\w+/article/[\w/]+", url)
    if m:
        # Try to extract from the page or use Crossref title lookup
        return None

    # sciencedirect
    m = re.search(r"sciencedirect\.com/science/article/pii/(\w+)", url)
    if m:
        return None  # Need Crossref lookup

    return None


def _resolve_doi_by_title(title: str) -> str | None:
    """Resolve DOI via Crossref title search."""
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params={"query.title": title, "rows": 1},
            timeout=15,
        )
        items = resp.json().get("message", {}).get("items", [])
        if items:
            return items[0].get("DOI")
    except Exception:
        pass
    return None


def _fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch metadata and PDF from arXiv API."""
    try:
        resp = requests.get(ARXIV_API, params={"id_list": arxiv_id}, timeout=15)
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return {}

        title_elem = entry.find("atom:title", ns)
        summary_elem = entry.find("atom:summary", ns)
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
                    if a.find("atom:name", ns) is not None]
        published = entry.find("atom:published", ns)

        year = None
        if published is not None and published.text:
            year = int(published.text[:4])

        return {
            "title": title_elem.text.strip() if title_elem is not None else "",
            "authors": ", ".join(authors),
            "year": year,
            "abstract": summary_elem.text.strip() if summary_elem is not None else "",
            "journal": "arXiv",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        }
    except Exception:
        return {}


def _fetch_semantic_scholar(doi: str) -> dict:
    """Fetch metadata from Semantic Scholar."""
    try:
        resp = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "title,authors,year,abstract,journal,openAccessPdf,externalIds"},
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        authors = ", ".join(a.get("name", "") for a in (data.get("authors") or []))
        pdf_info = data.get("openAccessPdf") or {}
        journal_info = data.get("journal") or {}
        return {
            "title": data.get("title", ""),
            "authors": authors,
            "year": data.get("year"),
            "abstract": data.get("abstract", ""),
            "journal": journal_info.get("name", ""),
            "pdf_url": pdf_info.get("url", ""),
        }
    except Exception:
        return {}


def _download_pdf(url: str, paper_id: str) -> Path | None:
    """Download PDF to cache directory, using institutional access if configured."""
    PDF_CACHE.mkdir(parents=True, exist_ok=True)
    pdf_path = PDF_CACHE / f"{paper_id}.pdf"
    if pdf_path.exists():
        return pdf_path
    return download_with_institutional_access(url, pdf_path, timeout=30)


def _extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path), strict=False)
        pages = []
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    pages.append(text)
            except Exception:
                continue
        return "\n\n".join(pages)
    except Exception:
        return ""


def _find_existing_pdf(doi: str, title: str) -> Path | None:
    """Look for an existing PDF in the project's pdfs/ directories."""
    search_dirs = [
        PROJECT_ROOT / "pdfs" / "journal",
        PROJECT_ROOT / "pdfs" / "conference",
        PROJECT_ROOT / "Knowlege-based-archive" / "pdfs",
    ]
    for pdf_dir in search_dirs:
        if not pdf_dir.exists():
            continue
        for pdf_file in pdf_dir.glob("*.pdf"):
            # Match by DOI in filename or title similarity
            name_lower = pdf_file.stem.lower().replace("-", " ").replace("_", " ")
            if doi and doi.replace("/", "_").lower() in name_lower:
                return pdf_file
            if title and title[:30].lower() in name_lower:
                return pdf_file
    return None


def ingest_paper(
    doi: str | None = None,
    url: str | None = None,
    pdf_path: str | None = None,
    source: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Ingest a paper into the knowledge base."""

    # Bulk ingest from README
    if source == "readme":
        return _ingest_from_readme()

    # Resolve DOI from URL
    if not doi and url:
        doi = _resolve_doi(url)

    if not doi and not pdf_path:
        # Try title-based resolution if metadata has title
        if metadata and metadata.get("title"):
            doi = _resolve_doi_by_title(metadata["title"])
        if not doi:
            return {"status": "error", "reason": "Could not resolve DOI. Provide doi, url, or pdf_path."}

    paper_id = make_paper_id(doi or pdf_path)

    # Check if already exists
    conn = get_db()
    existing = conn.execute("SELECT id, content_source FROM papers WHERE id = ? OR doi = ?", (paper_id, doi)).fetchone()
    conn.close()
    if existing:
        # Allow re-ingestion if current content is abstract-only and a PDF is provided
        if existing[1] == "pdf" or not pdf_path:
            return {"status": "skipped", "paper_id": existing[0], "reason": "Already in knowledge base"}
        # Remove old entry so we can re-ingest with PDF
        _remove_paper(existing[0])
        paper_id = existing[0]

    # Fetch metadata
    meta = metadata or {}
    if doi:
        # Determine source
        arxiv_match = re.match(r"10\.48550/arXiv\.(\d{4}\.\d{4,})", doi)
        if arxiv_match:
            fetched = _fetch_arxiv_metadata(arxiv_match.group(1))
        else:
            fetched = _fetch_semantic_scholar(doi)

        # Merge: explicit metadata overrides fetched
        for k, v in fetched.items():
            if k not in meta or not meta[k]:
                meta[k] = v
        meta["doi"] = doi

    # Try to get PDF
    local_pdf = Path(pdf_path) if pdf_path else None
    if not local_pdf or not local_pdf.exists():
        local_pdf = _find_existing_pdf(doi or "", meta.get("title", ""))
    if not local_pdf and meta.get("pdf_url"):
        local_pdf = _download_pdf(meta["pdf_url"], paper_id)

    # Extract text
    text = ""
    content_source = "abstract"
    if local_pdf and local_pdf.exists():
        text = _extract_pdf_text(local_pdf)
        if text and len(text) > 500:
            content_source = "pdf"
            meta["pdf_path"] = str(local_pdf)

    if not text and meta.get("abstract"):
        text = meta["abstract"]

    if not text:
        return {"status": "error", "paper_id": paper_id, "reason": "No text extracted"}

    meta["id"] = paper_id
    meta["content_source"] = content_source
    meta["content_length"] = len(text)

    # Chunk and embed
    chunks = chunk_text(text, paper_id)
    collection = get_collection()
    embed_chunks(chunks, meta, collection)

    # Store metadata
    store_metadata(paper_id, meta)

    return {
        "status": "success",
        "paper_id": paper_id,
        "title": meta.get("title", ""),
        "content_source": content_source,
        "chunks": len(chunks),
        "content_length": len(text),
    }


def _parse_readme() -> list[dict]:
    """Parse README.md table and extract paper entries."""
    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        return []

    text = readme_path.read_text()
    papers = []

    # Match table rows: | date journal | [Title](url) | assignment | modalities | platform | code |
    row_pattern = re.compile(
        r"^\|\s*(\d{4}-\d{2}-\d{2})\s+(.+?)\s*\|\s*\[(.+?)\]\((.+?)\)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
        re.MULTILINE,
    )

    for m in row_pattern.finditer(text):
        date_str, journal, title, url, assignment, modalities, platform, code = m.groups()

        code_url = None
        code_match = re.search(r"\[.*?\]\((.+?)\)", code.strip())
        if code_match:
            code_url = code_match.group(1).strip()

        year = int(date_str[:4]) if date_str else None

        papers.append({
            "title": title.strip(),
            "url": url.strip(),
            "year": year,
            "journal": journal.strip(),
            "assignment": assignment.strip().rstrip("|"),
            "modalities": modalities.strip().rstrip("|"),
            "platform": platform.strip().rstrip("|"),
            "code_url": code_url,
        })

    return papers


def _ingest_from_readme() -> dict:
    """Bulk ingest all papers from README.md."""
    papers = _parse_readme()
    if not papers:
        return {"status": "error", "reason": "No papers found in README.md"}

    results = {"added": 0, "skipped": 0, "errors": 0, "details": []}

    for paper in papers:
        result = ingest_paper(
            url=paper["url"],
            metadata={
                "title": paper["title"],
                "year": paper["year"],
                "journal": paper["journal"],
                "assignment": paper["assignment"],
                "modalities": paper["modalities"],
                "platform": paper["platform"],
                "code_url": paper.get("code_url"),
            },
        )

        status = result.get("status", "error")
        if status == "success":
            results["added"] += 1
        elif status == "skipped":
            results["skipped"] += 1
        else:
            results["errors"] += 1

        results["details"].append({
            "title": paper["title"],
            "status": status,
            "reason": result.get("reason", ""),
        })

        time.sleep(1)  # Rate limiting

    results["status"] = "success"
    results["total"] = len(papers)
    return results
