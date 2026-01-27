# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository maintains a curated collection of research papers on spatial omics prediction, specifically focusing on methods that predict spatial transcriptomics and other molecular information from histology images (primarily H&E). The data is managed in a bidirectional sync between a CSV database and a formatted README table.

## Workflow

Use Claude Code to:
1. **Add new papers** directly to `README.md` and `RELATED.md` tables.
2. **Reformat** existing tables when column layout or styling changes.

The `update/` directory is a temporary staging area where raw paper info can be saved (e.g., `update/20251209_conference.txt`) before being processed into the README tables.

## Table Format

Both `README.md` and `RELATED.md` use the same column order:

| Published | Title | Assignment | Modalities | Platform | Code |
| --- | --- | --- | --- | --- | --- |

- **Published**: Date and publisher combined, e.g., `2026-01-05 Nature Medicine`
- **Title**: Paper title as a markdown link to the paper URL
- **Assignment**: What the method predicts (maps from CSV field `Predicting target`)
- **Modalities**: Input data types, e.g., "H&E", "H&E + ST"
- **Platform**: Spatial platform, e.g., "Seq(Visium)", "Both"
- **Code**: Link to code repo as `[Repo](url)`, or `-` if unavailable

Papers are sorted by publication date (newest first), split into "Journal & Preprint Papers" and "Conference Papers" sections.

### Date Handling
- Dates normalized to ISO format (YYYY-MM-DD)
- Invalid dates fall back to `datetime.date.min` for sorting

### Link Formatting
- Title links to DOI (preferred) or paper URL
- Code column displays `[Repo](url)` or `-`
- Missing values render as `-`

## Data Validation

When adding new papers:
- Required: Title, PublishedDate, Publisher
- Date format: YYYY-MM-DD
- Links: Full URLs (https://)
- Modalities: "H&E", "H&E + ST", "H&E + mIF", etc.
- Platform: "Seq(Visium)", "Both", "mIF co-registered", etc.

## arXiv Search Pipeline

`tools/arxiv_search.py` searches arXiv for spatial omics prediction papers and generates output files. Stdlib only — no pip installs required.

### Two-Step Workflow

**Step 1 — Run the script:**
```bash
python tools/arxiv_search.py
```
Produces:
- `tools/output/arxiv_results.txt` — raw results with title, link, date, and abstract
- `ARXIV.md` — markdown table with Assignment/Modalities/Platform/Code defaulting to `-`

**Step 2 — Claude Code curates:**
Read `tools/output/arxiv_results.txt`, extract Assignment/Modalities/Platform from abstracts, and update `ARXIV.md` with proper metadata.

### Search Queries
The script runs 15 queries covering: spatial omics, spatial transcriptomics, spatial proteomics, gene expression prediction from histology, cell type deconvolution, and H&E-to-omics deep learning methods. Results are deduplicated by arXiv ID and sorted by date descending.

## Project Goal

Per user instructions: The goal is to use pretrained networks from papers in this collection. When working with papers, prioritize those with available code repositories (Code field populated).

Always update last update date in first line
