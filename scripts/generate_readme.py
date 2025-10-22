#!/usr/bin/env python3
"""Render the README table from data/papers.csv."""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "papers.csv"
OUTPUT_PATH = ROOT / "README.md"

TABLE_HEADERS = [
    "Published",
    "Title",
    "Modalities",
    "Platform",
    "Assignment",
    "Publisher",
    "Link",
    "Code",
]

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
)

def _parse_date(row: Dict[str, str]) -> dt.date:
    """Prefer PublishedDate; returns datetime.date.min when parsing fails."""
    parsed = _parse_published_date(row.get("PublishedDate", ""))
    if parsed:
        return parsed
    return dt.date.min


def _parse_published_date(value: str) -> Optional[dt.date]:
    cleaned = value.strip()
    if not cleaned:
        return None
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _format_title(row: Dict[str, str]) -> str:
    title = row.get("Title", "").strip() or "Untitled"
    doi = row.get("DOI", "").strip()
    link = row.get("Link", "").strip()
    if doi:
        target = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        return f"[{title}]({target})"
    if link:
        return f"[{title}]({link})"
    return title


def _format_link(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        return "-"
    return f"[{label}]({value})"


def _format_row(row: Dict[str, str]) -> List[str]:
    published_date = _parse_published_date(row.get("PublishedDate", ""))
    published_value = (
        published_date.isoformat()
        if published_date
        else row.get("PublishedDate", "").strip() or "-"
    )

    formatted = {
        "Published": published_value,
        "Title": _format_title(row),
        "Modalities": row.get("Modalities", "").strip() or "-",
        "Platform": row.get("SpatialPlatform", "").strip() or "-",
        "Assignment": row.get("Predicting target", "").strip() or "-",
        "Publisher": row.get("Publisher", "").strip() or "-",
        "Link": _format_link(row.get("Link", ""), "Link"),
        "Code": _format_link(row.get("Code", ""), "Repo"),
    }
    return [formatted[column] for column in TABLE_HEADERS]


def load_rows() -> List[Dict[str, str]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing data file: {DATA_PATH}")
    with DATA_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            _normalize_row(row)
            for row in reader
            if any(value.strip() for value in row.values())
        ]


def _normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    normalized = {key: (value or "") for key, value in row.items()}
    normalized.setdefault("Predicting target", "")
    normalized.setdefault("SpatialPlatform", "")
    normalized.setdefault("Modalities", "")
    normalized.setdefault("Publisher", "")
    normalized.setdefault("Link", "")
    normalized.setdefault("Code", "")
    normalized.setdefault("PublishedDate", "")
    normalized.setdefault("Title", "")
    return normalized


def build_table(rows: List[Dict[str, str]]) -> str:
    header = " | ".join(TABLE_HEADERS)
    divider = " | ".join(["---"] * len(TABLE_HEADERS))
    lines = [f"| {header} |", f"| {divider} |"]
    for row in rows:
        formatted = _format_row(row)
        lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join(lines)


def render() -> None:
    rows = load_rows()
    rows.sort(key=_parse_date, reverse=True)
    issued = dt.datetime.utcnow().date().isoformat()
    table = build_table(rows)
    content = f"""# Spatial Omics Prediction Papers\n\nAuto-generated from `data/papers.csv`. Last update: {issued}.\n\n{table}\n\n> Update the table via `python scripts/generate_readme.py`.\n"""
    OUTPUT_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    render()
