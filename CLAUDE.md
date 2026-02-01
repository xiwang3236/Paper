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

`tools/arxiv/arxiv_search.py` searches arXiv for spatial omics papers with topic-based filtering and configurable time windows. Stdlib only — no pip installs required.

### Usage

**Default behavior (prediction topic, last 7 days):**
```bash
python tools/arxiv/arxiv_search.py
```

**CLI Options:**
```bash
# Analysis topic, last 14 days
python tools/arxiv/arxiv_search.py --topic analysis --days 14

# All topics, last week
python tools/arxiv/arxiv_search.py --all-topics

# All papers since 2023
python tools/arxiv/arxiv_search.py --days 0

# Custom max results per query
python tools/arxiv/arxiv_search.py --max-results 100
```

**Arguments:**
- `-t, --topic {prediction,analysis}` - Select topic (default: prediction)
- `-d, --days N` - Fetch from last N days (default: 7, use 0 for all since 2023)
- `-a, --all-topics` - Run all topics (overrides --topic)
- `-m, --max-results N` - Max results per query (default: 50)

### Output Files

All output files are saved to `tools/arxiv/output/`:

**Single topic mode:**
- `tools/arxiv/output/arxiv_results.txt` — raw results with title, link, date, and abstract
- `tools/arxiv/output/ARXIV.md` — markdown table with Assignment/Modalities/Platform/Code defaulting to `-`

**All topics mode:**
- `tools/arxiv/output/arxiv_results_{topic}.txt` — per-topic raw results
- `tools/arxiv/output/ARXIV_{topic}.md` — per-topic markdown tables
- `tools/arxiv/output/arxiv_results_all.txt` — combined results
- `tools/arxiv/output/ARXIV_all.md` — combined markdown table

### Two-Step Workflow

**Step 1 — Run the script** (as shown above)

**Step 2 — Claude Code curates:**
Read `tools/arxiv/output/arxiv_results.txt`, extract Assignment/Modalities/Platform from abstracts, and update `tools/arxiv/output/ARXIV.md` with proper metadata.

### Search Topics

**Prediction (15 queries):** Spatial omics prediction, spatial transcriptomics inference/prediction, gene expression prediction from histology, cell type deconvolution, spatial proteomics prediction, H&E-to-omics deep learning methods.

**Analysis (15 queries):** Normalization, batch correction, clustering, spatial domain identification, segmentation, differential expression, spatially variable genes, data integration, alignment, imputation, denoising, imaging mass cytometry, multiplexed imaging analysis, spatial proteomics analysis, multi-modal spatial omics.

Results are deduplicated by arXiv ID and sorted by date descending.

## Journal Search Pipeline

`tools/arxiv/journal_search.py` searches high-impact journals via the **Europe PMC API** for spatial omics papers. Stdlib only — no pip installs required.

### Target Journals

Nature Methods, Nature Genetics, Bioinformatics, Nature Machine Intelligence, npj Artificial Intelligence, Nature Communications, Nature Computational Science.

### Usage

**Default behavior (prediction topic, last 30 days):**
```bash
python tools/arxiv/journal_search.py
```

**CLI Options:**
```bash
# Analysis topic, last 60 days
python tools/arxiv/journal_search.py --topic analysis --days 60

# All topics
python tools/arxiv/journal_search.py --all-topics

# Specific journal only
python tools/arxiv/journal_search.py --journal "Nature Methods"

# Custom max results per query
python tools/arxiv/journal_search.py --max-results 200
```

**Arguments:**
- `-t, --topic {prediction,analysis}` - Select topic (default: prediction)
- `-d, --days N` - Fetch from last N days (default: 30, use 0 for all since 2023)
- `-a, --all-topics` - Run all topics (overrides --topic)
- `-j, --journal NAME` - Filter to a single journal
- `-m, --max-results N` - Max results per query (default: 100)

### Output Files

All output files are saved to `tools/arxiv/output/`:

**Single topic mode:**
- `tools/arxiv/output/journal_results.txt` — raw results with title, journal, link, date, and abstract
- `tools/arxiv/output/JOURNAL.md` — markdown table

**All topics mode:**
- `tools/arxiv/output/journal_results_{topic}.txt` — per-topic raw results
- `tools/arxiv/output/JOURNAL_{topic}.md` — per-topic markdown tables
- `tools/arxiv/output/journal_results_all.txt` — combined results
- `tools/arxiv/output/JOURNAL_all.md` — combined markdown table

### Two-Step Workflow

Same as arXiv: run the script, then Claude Code curates by reading `journal_results.txt` and filling in Assignment/Modalities/Platform from abstracts.

Results are deduplicated by DOI and sorted by date descending.

## PDF Downloads

Paper PDFs are stored in `pdfs/` with subdirectories by section:
- `pdfs/journal/` — journal and preprint papers
- `pdfs/conference/` — conference papers

PDFs are git-ignored via `.gitignore`. When adding new papers, prefer linking to open-access PDF URLs (arXiv, CVF Open Access, MICCAI Open Access, AAAI OJS) so PDFs can be downloaded automatically.

### PDF URL Patterns by Source
- **arXiv**: Replace `/abs/` with `/pdf/` and append `.pdf`
- **Nature**: Append `.pdf` to article URL
- **bioRxiv**: Append `.full.pdf`
- **CVF Open Access**: Direct PDF links under `openaccess.thecvf.com/content/`
- **MICCAI Open Access**: `papers.miccai.org/miccai-{year}/paper/{id}_paper.pdf`
- **AAAI**: `ojs.aaai.org/index.php/AAAI/article/view/{id}/{pdf_id}`
- **OpenReview**: `openreview.net/pdf?id={forum_id}`
- **OUP / SPIE / Elsevier**: Often paywalled; may require manual download

## Knowledge Base

The `knowledge/` directory contains a searchable repository of paper content extracted from PDFs in `pdfs/`, enabling Claude Code to answer questions based on these papers.

### Directory Structure

```
knowledge/
├── INDEX.md              # Master index with topic-based organization
├── papers/               # Full extracted text from PDFs
│   ├── journal/
│   └── conference/
└── summaries/            # Structured summaries per paper
    ├── journal/
    └── conference/
```

### How to Query the Knowledge Base

When the user asks questions about papers, follow this workflow:

1. **First, search INDEX.md** to identify relevant papers by:
   - Method type (CNN, Transformer, GNN, etc.)
   - Prediction target (gene expression, cell types, spatial domains, etc.)
   - Input modality (H&E, microCT, mIF, etc.)
   - Spatial platform (Visium, Xenium, CODEX, etc.)
   - Research goal (see INDEX.md "Usage Guide" section)

2. **Then, read summaries** from `knowledge/summaries/{type}/{filename}.md` for:
   - Quick overview answers
   - Problem statement and method overview
   - Key contributions and results
   - Dataset information and code availability

3. **Finally, read full text** from `knowledge/papers/{type}/{filename}.md` for:
   - Detailed technical questions
   - Specific implementation details
   - Mathematical formulations
   - Experimental setup and ablation studies

### Example Queries

**"Which papers use graph neural networks?"**
1. Search INDEX.md → Method Type: GNN section
2. Read summaries for those papers
3. Cite specific papers with findings

**"What datasets are commonly used for benchmarking?"**
1. Search INDEX.md → Key Datasets section
2. Read summaries → Datasets Used field
3. Aggregate and report

**"How does VORTEX handle 3D prediction?"**
1. Find VORTEX in INDEX.md
2. Read summary for overview
3. Read full text (`AI-driven_3D_Spatial_Transcriptomics.md`) for technical details

### Citation Format

When answering based on knowledge base, cite papers clearly:
- Use paper titles from INDEX.md
- Reference specific findings from summaries/papers
- Include publication venue when relevant

## Project Goal

Per user instructions: The goal is to use pretrained networks from papers in this collection. When working with papers, prioritize those with available code repositories (Code field populated).

Always update last update date in first line
