"""
Deep knowledge retrieval: full text, metadata, paper listing, SQL queries.
"""

import json
from pathlib import Path
from typing import Optional

from .database import get_db


def query_knowledge(
    action: str,
    paper_id: Optional[str] = None,
    sql: Optional[str] = None,
    params: Optional[list] = None,
) -> dict | str | list:
    """Dispatch knowledge queries by action type."""
    if action == "full_text":
        return _get_full_text(paper_id)
    elif action == "metadata":
        return _get_metadata(paper_id)
    elif action == "list_papers":
        return _list_papers()
    elif action == "sql":
        return _run_sql(sql, params)
    else:
        return {"error": f"Unknown action: {action}. Use: full_text, metadata, list_papers, sql"}


def _get_full_text(paper_id: str) -> str:
    if not paper_id:
        return "Error: paper_id required for full_text action"

    conn = get_db()
    row = conn.execute(
        "SELECT pdf_path, title, abstract FROM papers WHERE id = ? OR doi = ?",
        (paper_id, paper_id),
    ).fetchone()
    conn.close()

    if not row:
        return f"Paper not found: {paper_id}"

    # Try PDF extraction first
    if row["pdf_path"]:
        pdf_path = Path(row["pdf_path"])
        if pdf_path.exists():
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
                if pages:
                    return f"# {row['title']}\n\n" + "\n\n".join(pages)
            except Exception as exc:
                return f"Error reading PDF: {exc}"

    # Fall back to abstract
    if row["abstract"]:
        return f"# {row['title']}\n\nAbstract:\n{row['abstract']}\n\n(Full text not available — PDF not ingested)"

    return f"No text available for: {row['title']}"


def _get_metadata(paper_id: str) -> dict:
    if not paper_id:
        return {"error": "paper_id required for metadata action"}

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM papers WHERE id = ? OR doi = ?",
        (paper_id, paper_id),
    ).fetchone()
    conn.close()

    if not row:
        return {"error": f"Paper not found: {paper_id}"}

    record = dict(row)
    for field in ("topics", "methods_used", "key_findings"):
        if record.get(field):
            try:
                record[field] = json.loads(record[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return record


def _list_papers() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, doi, title, year, journal, assignment, modalities, platform, "
        "code_url, content_source, metadata_status "
        "FROM papers ORDER BY year DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _run_sql(sql: str, params: list | None = None) -> list[dict] | dict:
    if not sql:
        return {"error": "sql parameter required for sql action"}

    # Only allow SELECT
    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries allowed"}

    conn = get_db()
    try:
        rows = conn.execute(sql, params or []).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        return {"error": str(exc)}
    finally:
        conn.close()
