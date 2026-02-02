# Workflow: Fetch → Curate → Update → Report

## Step 1 — Fetch papers (Python, automated)

```bash
# arXiv: last 7 days, prediction topic
python tools/arxiv/arxiv_search.py

# Journals: last 30 days, prediction + analysis
python tools/journal/journal_search.py --all-topics --days 30
```

**Output**:
- `temp/arxiv_results_YYYY-MM-DD.txt` — raw results with abstracts
- `temp/ARXIV_YYYY-MM-DD.md` — markdown table (metadata defaults to `-`)
- `temp/journal_results_YYYY-MM-DD.txt` — raw results with abstracts
- `temp/JOURNAL_YYYY-MM-DD.md` — markdown table (metadata defaults to `-`)

## Step 2 — Curate & extract metadata (Claude Code)

Read `temp/arxiv_results_*.txt` and `temp/journal_results_*.txt`. For each paper:
- Decide relevant or not (method paper vs biology application)
- Extract Assignment, Modalities, Platform from abstract
- Update `temp/ARXIV_*.md` and `temp/JOURNAL_*.md` tables with metadata

## Step 3 — Triage into README vs RELATED (Claude Code)

- **Prediction methods** (H&E → gene expression, cell types, etc.) → `README.md`
- **Analysis/tools** (clustering, segmentation, integration, etc.) → `RELATED.md`
- **Biology applications** → skip

## Step 4 — Update README.md & RELATED.md (Claude Code)

Add new paper rows to the correct table, maintaining date-descending sort. Update the last-update date in the first line.

## Step 5 — Generate weekly report (Claude Code)

Create `reports/WEEKLY_YYYY-MM-DD.md` from `reports/WEEKLY_TEMPLATE.md`:
- Journal papers: 1-month window
- arXiv papers: 7-day window
- Write keywords (line 2) and summary (line 3) per entry
- Save interim triage notes to `temp/WEEKLY_REPORT_YYYY-MM-DD.md`

## Summary

| Step | Tool | Input | Output |
|------|------|-------|--------|
| 1. Fetch | Python (auto) | arXiv API, Europe PMC API | `temp/*_results_*.txt`, `temp/*.md` |
| 2. Curate | Claude Code | `temp/*_results_*.txt` | Updated `temp/ARXIV_*.md`, `temp/JOURNAL_*.md` |
| 3. Triage | Claude Code | Curated tables | Classification per paper |
| 4. Update tables | Claude Code | Triage decisions | `README.md`, `RELATED.md` |
| 5. Report | Claude Code | All of the above | `reports/WEEKLY_YYYY-MM-DD.md` |

Steps 2–5 require Claude Code because they involve reading abstracts, judging relevance, and extracting structured information.
