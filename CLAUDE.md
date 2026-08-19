# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository maintains a curated collection of research papers on spatial omics prediction, specifically focusing on methods that predict spatial transcriptomics and other molecular information from histology images (primarily H&E). The data is managed in a bidirectional sync between a CSV database and a formatted README table.

## Full Pipeline (see also `WORKFLOW.md`)

When the user asks to run the weekly update, follow these steps in order:

### Step 1 — Fetch papers (Python scripts)

Run both search scripts to populate `temp/`:

```bash
python tools/arxiv/arxiv_search.py
python tools/journal/journal_search.py --all-topics --days 30
```

This produces raw results (`temp/*_results_*.txt`) and draft tables (`temp/ARXIV_*.md`, `temp/JOURNAL_*.md`, `temp/PREPRINT_*.md`).

### Step 2 — Curate & extract metadata

Read each `temp/*_results_*.txt` file. For every paper:
1. Read the abstract and decide: **relevant method paper** or **biology application** (skip)
2. For relevant papers, extract from the abstract:
   - **Assignment**: what the method predicts/does
   - **Modalities**: input data types (H&E, ST, scRNA-seq, etc.)
   - **Platform**: spatial platform (Visium, Xenium, MERFISH, etc.)
   - **Code**: GitHub/repo URL if mentioned
3. Update `temp/ARXIV_*.md` and `temp/JOURNAL_*.md` with the extracted metadata

### Step 3 — Triage into README vs RELATED

Classify each relevant paper:
- **Prediction methods** (H&E → gene expression, cell types, proteins) → add to `README.md`
- **Analysis/tools** (clustering, segmentation, integration, imputation, simulation) → add to `RELATED.md`
- **Biology applications** that merely use ST as a tool → skip entirely

### Step 4 — Update README.md & RELATED.md

Insert new rows into the correct table using the standard format (see Table Format below). Maintain date-descending sort. Update the last-update date in the first line of each file.

### Step 5 — Generate weekly report

Create `reports/WEEKLY_YYYY-MM-DD.md` from `reports/WEEKLY_TEMPLATE.md`:
- **Journal papers**: 1-month window only
- **arXiv papers**: 7-day window
- Each entry has 3 lines: title+link, keywords, summary
- Save triage notes to `temp/WEEKLY_REPORT_YYYY-MM-DD.md`

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

```bash
python tools/arxiv/arxiv_search.py                          # default: prediction, 7 days
python tools/arxiv/arxiv_search.py --topic analysis --days 14
python tools/arxiv/arxiv_search.py --all-topics
python tools/arxiv/arxiv_search.py --max-results 100
```

**Arguments:**
- `-t, --topic {prediction,analysis}` — select topic (default: prediction)
- `-d, --days N` — fetch from last N days (default: 7, use 0 for all since 2023)
- `-a, --all-topics` — run all topics (overrides --topic)
- `-m, --max-results N` — max results per query (default: 50)

### Output Files

- `temp/arxiv_results_YYYY-MM-DD.txt` — raw results with title, link, date, and abstract
- `temp/ARXIV_YYYY-MM-DD.md` — markdown table with metadata defaulting to `-`

### Search Topics

**Prediction (15 queries):** Spatial omics prediction, spatial transcriptomics inference/prediction, gene expression prediction from histology, cell type deconvolution, spatial proteomics prediction, H&E-to-omics deep learning methods.

**Analysis (15 queries):** Normalization, batch correction, clustering, spatial domain identification, segmentation, differential expression, spatially variable genes, data integration, alignment, imputation, denoising, imaging mass cytometry, multiplexed imaging analysis, spatial proteomics analysis, multi-modal spatial omics.

Results are deduplicated by arXiv ID and sorted by date descending.

## Journal & Preprint Search Pipeline

`tools/journal/journal_search.py` searches high-impact journals and preprint servers (bioRxiv/medRxiv) via the **Europe PMC API** for spatial omics papers. Stdlib only — no pip installs required.

### Target Journals

**Methods / Spatial / Omics / Tech:** Nature Methods, Genome Research, Cell Systems, Trends in Biotechnology, Trends in Genetics, Nature Communications, Science Translational Medicine.

**AI / Machine Learning:** Nature Machine Intelligence, Information Fusion, IEEE Trans. Knowl. Data Eng., IEEE Trans. Medical Imaging.

**Genomics / Computational Biology:** Briefings in Bioinformatics, Cell Reports Methods, Patterns, eLife.

**Reviews:** Nature Reviews Molecular Cell Biology, Nature Reviews Cancer, Annual Review of Genomics and Human Genetics.

### Preprint Servers

bioRxiv and medRxiv preprints are searched automatically via Europe PMC's `SRC:PPR` source filter. Preprint search runs in parallel with journal search using the same keyword queries.

### Usage

```bash
python tools/journal/journal_search.py                              # default: prediction, 30 days (journals + preprints)
python tools/journal/journal_search.py --topic analysis --days 60
python tools/journal/journal_search.py --all-topics
python tools/journal/journal_search.py --journal "Nature Methods"
python tools/journal/journal_search.py --max-results 200
python tools/journal/journal_search.py --no-preprints               # journals only, skip bioRxiv/medRxiv
```

**Arguments:**
- `-t, --topic {prediction,analysis}` — select topic (default: prediction)
- `-d, --days N` — fetch from last N days (default: 30, use 0 for all since 2023)
- `-a, --all-topics` — run all topics (overrides --topic)
- `-j, --journal NAME` — filter to a single journal (disables preprint search)
- `-m, --max-results N` — max results per query (default: 100)
- `--no-preprints` — skip bioRxiv/medRxiv preprint search

### Output Files

**Journal results:**
- `temp/journal_results_YYYY-MM-DD.txt` — raw results with title, journal, link, date, and abstract
- `temp/JOURNAL_YYYY-MM-DD.md` — markdown table

**Preprint results:**
- `temp/preprint_results_YYYY-MM-DD.txt` — raw bioRxiv/medRxiv results
- `temp/PREPRINT_YYYY-MM-DD.md` — markdown table

When using `--all-topics`, per-topic files are generated (e.g., `journal_results_prediction_*.txt`, `preprint_results_analysis_*.txt`) plus combined `*_all_*` files.

Results are deduplicated by DOI and sorted by date descending.

## Weekly Report

The `reports/` directory contains curated weekly reports of new spatial omics papers.

### Template

`reports/WEEKLY_TEMPLATE.md` defines the report format. Each paper entry has 3 lines:
1. Title as markdown link + date + publisher
2. Keyword tags in backticks
3. 1-2 sentence summary from abstract

### Report Rules

- Journal papers: **1-month window** only
- arXiv and bioRxiv preprints: **1-month window** (same as journals)
- Papers sorted date descending within each section
- Only computational method papers — no biology applications
- Split into "Papers from High-Impact Journals" and "Papers from arXiv and bioRxiv"

### Keywords

Use concise, consistent domain keywords in backticks, e.g.:
`gene expression prediction`, `spatial domain detection`, `cell segmentation`, `foundation model`, `multi-omics integration`, `graph neural network`, `cell-cell communication`, `data integration`, `simulation`, `clone tracing`

### Output

Reports are saved as `reports/WEEKLY_YYYY-MM-DD.md` with one file per search run.

## Figure Newspaper Generation

`tools/figures/fetch_figures.py` fetches first figures from papers in a weekly report and generates a Nature Methods-inspired HTML newspaper page. Stdlib only — no pip installs required.

### Usage

```bash
python tools/figures/fetch_figures.py --report reports/WEEKLY_2026-02-01.md
python tools/figures/fetch_figures.py --report reports/WEEKLY_2026-02-01.md --output custom.html
python tools/figures/fetch_figures.py --report reports/WEEKLY_2026-02-01.md --skip-download
```

**Arguments:**
- `--report PATH` — path to a `WEEKLY_*.md` report (required)
- `--output PATH` — custom output HTML path (default: `{report}_figures.html`)
- `--skip-download` — use cached figures or placeholders instead of fetching

### Output

- Figures cached in `temp/figures/` (one subdirectory per paper)
- HTML saved alongside the report, e.g., `reports/WEEKLY_2026-02-01_figures.html`

### Layout

- **Header**: Dark red banner with "AI-Scholar" linking to the GitHub repo, followed by "Predictive Modeling in Spatial Omics" (red, bold) and "Recent Advances" (black)
- **Signature**: Email (xxw962@case.edu) and GitHub link
- **Sections**: "Papers from High-Impact Journals" and "Papers from arXiv and bioRxiv", each with a 2-column card grid (single-column on narrow viewports)
- **Figure cards**: Image on top, title, date/publisher, bold keyword pills, summary
- **No-figure cards**: Compact text-only cards with left red border accent, grouped at the bottom under "Papers without figures"

### Style

Color palette: white background, dark red accents (`#8B1E1E`), gray borders (`#D9D9D9`), Arial font throughout. Sharp corners, no rounded borders. Print-journal aesthetic.

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

### Citation Format

When answering based on knowledge base, cite papers clearly:
- Use paper titles from INDEX.md
- Reference specific findings from summaries/papers
- Include publication venue when relevant

## Project Goal

Per user instructions: The goal is to use pretrained networks from papers in this collection. When working with papers, prioritize those with available code repositories (Code field populated).

Always update last update date in first line
