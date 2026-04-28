"""
Paper discovery from external sources: PubMed, Semantic Scholar, Crossref, Europe PMC, arXiv.
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests

from .database import get_db


DEFAULT_SOURCES = ["pubmed", "semantic_scholar", "europe_pmc"]


def discover_papers(
    query: str,
    sources: list[str] | None = None,
    days_back: int = 30,
    max_results: int = 10,
) -> list[dict]:
    """Search external APIs for candidate papers."""
    chosen = sources or DEFAULT_SOURCES
    handlers = {
        "pubmed": _search_pubmed,
        "semantic_scholar": _search_semantic_scholar,
        "crossref": _search_crossref,
        "europe_pmc": _search_europe_pmc,
        "arxiv": _search_arxiv,
    }

    results = []
    for source in chosen:
        handler = handlers.get(source)
        if not handler:
            continue
        try:
            found = handler(query=query, days_back=days_back, max_results=max_results)
            results.extend(found)
        except Exception as exc:
            results.append({
                "title": "", "doi": "", "source": source,
                "error": str(exc),
            })

    # Deduplicate by DOI
    seen = set()
    unique = []
    for r in results:
        doi = r.get("doi", "")
        if doi and doi in seen:
            continue
        if doi:
            seen.add(doi)
        unique.append(r)

    # Mark which are already ingested
    conn = get_db()
    for r in unique:
        doi = r.get("doi", "")
        if doi:
            existing = conn.execute("SELECT id FROM papers WHERE doi = ?", (doi,)).fetchone()
            r["already_ingested"] = existing is not None
        else:
            r["already_ingested"] = False
    conn.close()

    return unique


def _search_pubmed(query: str, days_back: int, max_results: int) -> list[dict]:
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": f"{query} AND ({since}[PDAT] : 3000[PDAT])",
            "retmax": max_results,
            "retmode": "json",
        },
        timeout=15,
    )
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    summary_resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        timeout=15,
    )
    summaries = summary_resp.json().get("result", {})

    results = []
    for pmid in ids:
        info = summaries.get(pmid, {})
        doi = ""
        for id_obj in info.get("articleids", []):
            if id_obj.get("idtype") == "doi":
                doi = id_obj["value"]
                break

        results.append({
            "title": info.get("title", ""),
            "doi": doi,
            "authors": ", ".join(a.get("name", "") for a in info.get("authors", [])),
            "year": int(info.get("pubdate", "0")[:4]) if info.get("pubdate") else None,
            "source": "pubmed",
            "journal": info.get("source", ""),
            "abstract": "",
            "full_text_available": False,
        })

    return results


def _search_semantic_scholar(query: str, days_back: int, max_results: int) -> list[dict]:
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    resp = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={
            "query": query,
            "fields": "title,authors,year,abstract,journal,externalIds,openAccessPdf",
            "limit": max_results,
            "publicationDateOrYear": f"{since}:",
        },
        timeout=15,
    )
    papers = resp.json().get("data", [])

    results = []
    for p in papers:
        ext = p.get("externalIds") or {}
        pdf_info = p.get("openAccessPdf") or {}
        journal_info = p.get("journal") or {}
        results.append({
            "title": p.get("title", ""),
            "doi": ext.get("DOI", ""),
            "authors": ", ".join(a.get("name", "") for a in (p.get("authors") or [])),
            "year": p.get("year"),
            "source": "semantic_scholar",
            "journal": journal_info.get("name", ""),
            "abstract": p.get("abstract", ""),
            "full_text_available": bool(pdf_info.get("url")),
            "pdf_url": pdf_info.get("url", ""),
        })

    return results


def _search_crossref(query: str, days_back: int, max_results: int) -> list[dict]:
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    resp = requests.get(
        "https://api.crossref.org/works",
        params={
            "query": query,
            "filter": f"from-pub-date:{since}",
            "rows": max_results,
            "sort": "published",
            "order": "desc",
        },
        timeout=15,
    )
    items = resp.json().get("message", {}).get("items", [])

    results = []
    for item in items:
        title_parts = item.get("title", [])
        title = title_parts[0] if title_parts else ""
        authors_list = item.get("author", [])
        authors = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list
        )
        date_parts = item.get("published", {}).get("date-parts", [[None]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        results.append({
            "title": title,
            "doi": item.get("DOI", ""),
            "authors": authors,
            "year": year,
            "source": "crossref",
            "journal": ", ".join(item.get("container-title", [])),
            "abstract": "",
            "full_text_available": False,
        })

    return results


def _search_europe_pmc(query: str, days_back: int, max_results: int) -> list[dict]:
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    resp = requests.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": f"{query} AND FIRST_PDATE:[{since} TO *]",
            "format": "json",
            "pageSize": max_results,
            "resultType": "core",
            "sort": "FIRST_PDATE desc",
        },
        timeout=15,
    )
    items = resp.json().get("resultList", {}).get("result", [])

    results = []
    for item in items:
        results.append({
            "title": item.get("title", ""),
            "doi": item.get("doi", ""),
            "authors": item.get("authorString", ""),
            "year": int(item.get("pubYear", 0)) or None,
            "source": "europe_pmc",
            "journal": item.get("journalTitle", ""),
            "abstract": item.get("abstractText", ""),
            "full_text_available": item.get("isOpenAccess") == "Y",
        })

    return results


def _search_arxiv(query: str, days_back: int, max_results: int) -> list[dict]:
    resp = requests.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": f"all:{query}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        },
        timeout=15,
    )
    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    cutoff = datetime.now() - timedelta(days=days_back)
    results = []

    for entry in root.findall("atom:entry", ns):
        published = entry.find("atom:published", ns)
        if published is not None and published.text:
            pub_date = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
            if pub_date.replace(tzinfo=None) < cutoff:
                continue

        title_elem = entry.find("atom:title", ns)
        summary_elem = entry.find("atom:summary", ns)
        id_elem = entry.find("atom:id", ns)
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
                    if a.find("atom:name", ns) is not None]

        arxiv_url = id_elem.text.strip() if id_elem is not None else ""
        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

        results.append({
            "title": title_elem.text.strip() if title_elem is not None else "",
            "doi": f"10.48550/arXiv.{arxiv_id}" if arxiv_id else "",
            "authors": ", ".join(authors),
            "year": int(published.text[:4]) if published is not None and published.text else None,
            "source": "arxiv",
            "journal": "arXiv",
            "abstract": summary_elem.text.strip() if summary_elem is not None else "",
            "full_text_available": True,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
        })

    return results
