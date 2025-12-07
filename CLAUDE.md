# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository maintains a curated collection of research papers on spatial omics prediction, specifically focusing on methods that predict spatial transcriptomics and other molecular information from histology images (primarily H&E). The data is managed in a bidirectional sync between a CSV database and a formatted README table.

## Core Architecture

The project uses a **bidirectional synchronization** pattern between two representations of the same data:

1. **Source of Truth (CSV)**: `data/papers.csv` contains complete metadata for each paper including fields like Title, PublishedDate, Publisher, Modalities, SpatialPlatform, Predicting target, Summary, Tags, Link, and Code.

2. **Public View (README)**: `README.md` displays a curated subset of these fields in a markdown table, auto-generated and sorted by publication date (newest first).

### Data Flow

- **CSV → README**: Use `python scripts/generate_readme.py` to render the README table from the CSV data. This is the primary workflow for updates.
- **README → CSV**: Use `python scripts/update_csv_from_readme.py` to sync manual edits from README back to the CSV. This preserves existing CSV fields not shown in the README.

### Shared Utilities

Both sync scripts rely on `scripts/_table_utils.py` which provides:
- `parse_published_date()`: Parses dates from multiple formats (YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY, MM-DD-YYYY)
- `split_markdown_link()`: Extracts label and URL from markdown link syntax

## Common Commands

### Update README from CSV
```bash
python scripts/generate_readme.py
```
Use this after adding or editing papers in `data/papers.csv`. The README will be regenerated with papers sorted by publication date (newest first).

### Sync CSV from README
```bash
python scripts/update_csv_from_readme.py
```
Use this if papers were manually edited in the README table. Merges README changes back into the CSV while preserving fields like Summary, Tags, and VenueType that aren't displayed in the README.

## Key Design Patterns

### Table Column Mapping
The README displays a subset of CSV fields with some renaming:
- `PublishedDate` → "Published"
- `SpatialPlatform` → "Platform"
- `Predicting target` → "Assignment"

Header aliases (in `update_csv_from_readme.py`) handle variations in README header text.

### Date Handling
- Dates are parsed flexibly but normalized to ISO format (YYYY-MM-DD) in both CSV and README
- Invalid dates fall back to `datetime.date.min` for sorting purposes

### Link Formatting
- Title links to DOI (preferred) or Link field
- Link column displays "[Link](url)"
- Code column displays "[Repo](url)"
- Missing values render as "-"

## Data Validation

When adding new papers to CSV:
- Required fields: Title, PublishedDate
- Date format: Prefer YYYY-MM-DD for consistency
- Links: Full URLs (https://)
- Modalities: Common patterns include "H&E", "H&E + ST", "H&E + mIF"
- Platform: "Seq(Visium)", "Both", "mIF co-registered", etc.

## Project Goal

Per user instructions: The goal is to use pretrained networks from papers in this collection. When working with papers, prioritize those with available code repositories (Code field populated).
