#!/usr/bin/env python3
"""Render the README table from data/papers.csv."""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "papers.csv"
OUTPUT_PATH = ROOT / "README.md"

TABLE_COLUMNS = [
    ("Year", "Year"),
    ("Published", "PublishedDate"),
    ("Title", "Title"),
    ("Modalities", "Modalities"),
    ("Platform", "SpatialPlatform"),
    ("Assignment", "Assignment"),
    ("Publisher", "Publisher"),
    ("Link", "Link"),
    ("Code", "Code"),
]


def _parse_date(row: Dict[str, str]) -> dt.date:
    """Prefer PublishedDate; fallback to Year."""
    published = row.get("PublishedDate", "").strip()
    if published:
        try:
            return dt.date.fromisoformat(published)
        except ValueError:
            pass
    year = row.get("Year", "").strip()
    if year:
        try:
            return dt.date(int(year), 1, 1)
        except ValueError:
            pass
    return dt.date.min


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
    formatted = {
        "Year": row.get("Year", "").strip() or "-",
        "Published": row.get("PublishedDate", "").strip() or "-",
        "Title": _format_title(row),
        "Modalities": row.get("Modalities", "").strip() or "-",
        "Platform": row.get("SpatialPlatform", "").strip() or "-",
        "Assignment": row.get("Assignment", "").strip() or "-",
        "Publisher": row.get("Publisher", "").strip() or "-",
        "Link": _format_link(row.get("Link", ""), "Link"),
        "Code": _format_link(row.get("Code", ""), "Repo"),
    }
    return [formatted[column] for column, _ in TABLE_COLUMNS]


def load_rows() -> List[Dict[str, str]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing data file: {DATA_PATH}")
    with DATA_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def build_table(rows: List[Dict[str, str]]) -> str:
    header = " | ".join(column for column, _ in TABLE_COLUMNS)
    divider = " | ".join(["---"] * len(TABLE_COLUMNS))
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
