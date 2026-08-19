"""Search Europe PMC for spatial omics papers in high-impact journals and preprint servers."""

import urllib.request
import urllib.parse
import json
import datetime
import os
import argparse

JOURNALS = {
# Methods / Spatial / Omics / Tech (IF >10)
"Nature Methods": "1548-7091",                  # Gold standard for new experimental & computational methods
"Genome Research": "1088-9051",                 # High-impact functional & computational genomics
"Cell Systems": "2405-4712",                    # Systems biology + computational modeling
"Trends in Biotechnology": "0167-7799",         # High-citation reviews on biotech & methods
"Trends in Genetics": "0168-9525",               # Reviews in genomics, regulation, and methods
"Nature Communications": "2041-1723",            # Broad, high-impact biology & computational work
"Science Translational Medicine": "1946-6234",   # Translational & clinical tech applications

# AI / Machine Learning / Data Science (IF >10)
"Nature Machine Intelligence": "2522-5839",      # Top-tier AI/ML journal (methods + theory)
"Information Fusion": "1566-2535",               # Multimodal data fusion, ML-heavy
"IEEE Trans. Knowl. Data Eng.": "1041-4347",     # Data mining, ML systems, graphs
"IEEE Trans. Medical Imaging": "0278-0062",      # Medical imaging + deep learning (very relevant)

# Genomics / Computational Biology (IF >10)
"Briefings in Bioinformatics": "1477-4054",      # Review-heavy, very high citation rate
"Cell Reports Methods": "2667-2375",             # Cell-family methods journal
"Patterns": "2666-3899",                         # Data science + ML across disciplines
"eLife": "2050-084X",                            # Strong methods + computational biology

# Reviews (Very High Citation Power)
"Nature Reviews Molecular Cell Biology": "1471-0072",  # Mechanistic & systems-level biology
"Nature Reviews Cancer": "1474-1768",                  # Spatial & omics-heavy cancer reviews
"Annual Review of Genomics and Human Genetics": "1527-8204", # Authoritative genomics reviews

}

QUERY_TOPICS = {
    "prediction": [
        '"spatial omics" AND "prediction"',
        '"spatial omics" AND "deep learning"',
        '"spatial transcriptomics" AND "inference"',
        '"spatial transcriptomics" AND "prediction"',
        '"spatial transcriptomics" AND "deep learning"',
        '"spatial transcriptomics" AND "gene expression"',
        '"spatial gene expression" AND "histology"',
        '"gene expression prediction" AND "histology"',
        '"cell type" AND "spatial transcriptomics" AND "prediction"',
        '"cell type deconvolution" AND "spatial"',
        '"spatial proteomics" AND "prediction"',
        '"spatial proteomics" AND "deep learning"',
        '"histology" AND "transcriptomics" AND "prediction"',
        '"H&E" AND "gene expression" AND "predict"',
        '"pathology" AND "spatial transcriptomics" AND "neural network"',
    ],
    "analysis": [
        '"spatial transcriptomics" AND "normalization"',
        '"spatial transcriptomics" AND "batch correction"',
        '"spatial transcriptomics" AND "clustering"',
        '"spatial domain" AND "identification"',
        '"spatial omics" AND "segmentation"',
        '"spatial transcriptomics" AND "differential expression"',
        '"spatially variable genes"',
        '"spatial omics" AND "integration"',
        '"spatial transcriptomics" AND "alignment"',
        '"spatial transcriptomics" AND "imputation"',
        '"spatial transcriptomics" AND "denoising"',
        '"imaging mass cytometry"',
        '"multiplexed imaging" AND "analysis"',
        '"spatial proteomics" AND "analysis"',
        '"multi-modal" AND "spatial omics"',
    ],
}

PREPRINT_SERVERS = ["bioRxiv", "medRxiv"]

MAX_RESULTS = 100
EUROPEPMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TODAY = datetime.date.today().isoformat()
OUTPUT_DIR = os.path.join(REPO_ROOT, "temp")
OUTPUT_TXT = os.path.join(OUTPUT_DIR, f"journal_results_{TODAY}.txt")
OUTPUT_MD = os.path.join(OUTPUT_DIR, f"JOURNAL_{TODAY}.md")


def build_issn_clause(journal_filter: str | None = None) -> str:
    """Build ISSN OR clause, optionally filtered to a single journal."""
    if journal_filter:
        issn = JOURNALS.get(journal_filter)
        if not issn:
            raise ValueError(
                f"Unknown journal: {journal_filter}. "
                f"Available: {', '.join(JOURNALS.keys())}"
            )
        return f'ISSN:"{issn}"'
    parts = [f'ISSN:"{issn}"' for issn in JOURNALS.values()]
    return "(" + " OR ".join(parts) + ")"


def fetch_europepmc(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """Fetch results from Europe PMC REST API using cursor-based pagination."""
    results = []
    page_size = min(max_results, 1000)
    cursor = "*"

    while len(results) < max_results:
        params = urllib.parse.urlencode({
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "cursorMark": cursor,
            "resultType": "core",
        })
        url = f"{EUROPEPMC_API}?{params}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        entries = data.get("resultList", {}).get("result", [])
        if not entries:
            break
        results.extend(entries)

        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return results[:max_results]


def parse_entries(raw_entries: list[dict]) -> list[dict]:
    """Extract structured paper info from Europe PMC JSON results."""
    papers = []
    for entry in raw_entries:
        title = entry.get("title", "").strip()
        if not title:
            continue

        doi = entry.get("doi", "")
        link = f"https://doi.org/{doi}" if doi else ""
        date = entry.get("firstPublicationDate", "")
        abstract = entry.get("abstractText", "")
        if abstract:
            abstract = " ".join(abstract.split())
        journal_info = entry.get("journalInfo", {})
        journal_obj = journal_info.get("journal", {})
        journal = journal_obj.get("title", "")

        papers.append({
            "id": doi or title,
            "title": title.rstrip("."),
            "link": link,
            "date": date,
            "abstract": abstract or "",
            "journal": journal,
        })
    return papers


def get_min_date(days: int) -> str:
    """Calculate minimum date. days=0 means all since 2023-01-01."""
    if days == 0:
        return "2023-01-01"
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    return cutoff.isoformat()


def deduplicate(all_entries: list[dict], min_date: str) -> list[dict]:
    """Deduplicate by ID (DOI) and filter by date."""
    seen: set[str] = set()
    unique = []
    for e in all_entries:
        if e["id"] not in seen and e["date"] >= min_date:
            seen.add(e["id"])
            unique.append(e)
    return unique


def write_txt(papers: list[dict], path: str, topic: str, days: int) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    min_date = get_min_date(days)
    today = datetime.date.today().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Journal Spatial Omics Papers - Topic: {topic}\n")
        f.write(f"Search period: {min_date} to {today}")
        if days > 0:
            f.write(f" ({days} days)\n")
        else:
            f.write(" (all papers since 2023)\n")
        f.write(f"Total papers: {len(papers)}\n")
        f.write("=" * 80 + "\n\n")

        for p in papers:
            f.write(f"Title: {p['title']}\n")
            f.write(f"Journal: {p['journal']}\n")
            f.write(f"Link: {p['link']}\n")
            f.write(f"Date: {p['date']}\n")
            f.write(f"Abstract: {p['abstract']}\n")
            f.write("---\n")


def write_md(papers: list[dict], path: str, topic: str, days: int) -> None:
    today = datetime.date.today().isoformat()
    min_date = get_min_date(days)

    topic_title = topic.capitalize() if topic != "all" else "All Topics"
    lines = [
        f"# Journal Spatial Omics Papers - {topic_title}",
        "",
        f"Last update: {today}.",
        "",
    ]
    if days > 0:
        lines.append(f"Search period: {min_date} to {today} ({days} days).")
    else:
        lines.append(f"Search period: {min_date} to {today} (all papers since 2023).")
    lines.extend([
        "",
        "Auto-generated by `python tools/journal/journal_search.py`.",
        "",
        "| Published | Title | Assignment | Modalities | Platform | Code |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for p in papers:
        title_cell = f"[{p['title']}]({p['link']})" if p["link"] else p["title"]
        lines.append(f"| {p['date']} {p['journal']} | {title_cell} | - | - | - | - |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Search Europe PMC for spatial omics papers in high-impact journals and preprint servers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: prediction topic, last 30 days (journals + preprints)
  python tools/journal/journal_search.py

  # Analysis topic, last 60 days
  python tools/journal/journal_search.py --topic analysis --days 60

  # All topics
  python tools/journal/journal_search.py --all-topics

  # Specific journal only
  python tools/journal/journal_search.py --journal "Nature Methods"

  # Journals only, no preprints
  python tools/journal/journal_search.py --no-preprints
"""
    )
    parser.add_argument(
        "-t", "--topic",
        choices=["prediction", "analysis"],
        default="prediction",
        help="Select topic (default: prediction)"
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=30,
        help="Fetch from last N days (default: 30, use 0 for all since 2023)"
    )
    parser.add_argument(
        "-a", "--all-topics",
        action="store_true",
        help="Run all topics (overrides --topic)"
    )
    parser.add_argument(
        "-j", "--journal",
        type=str,
        default=None,
        help="Filter to a single journal (e.g. 'Nature Methods')"
    )
    parser.add_argument(
        "-m", "--max-results",
        type=int,
        default=MAX_RESULTS,
        help=f"Max results per query (default: {MAX_RESULTS})"
    )
    parser.add_argument(
        "--no-preprints",
        action="store_true",
        help="Skip bioRxiv/medRxiv preprint search"
    )
    return parser.parse_args()


def fetch_and_process_topic(
    topic: str, min_date: str, max_results: int, journal_filter: str | None = None
) -> list[dict]:
    """Fetch and process papers for a single topic."""
    print(f"\n=== Processing topic: {topic} ===")
    issn_clause = build_issn_clause(journal_filter)
    today = datetime.date.today().isoformat()
    keywords = QUERY_TOPICS[topic]
    all_entries: list[dict] = []

    for kw in keywords:
        query = f"{issn_clause} AND ({kw}) AND FIRST_PDATE:[{min_date} TO {today}]"
        print(f"Querying: {kw}")
        try:
            raw = fetch_europepmc(query, max_results)
            entries = parse_entries(raw)
            print(f"  Found {len(entries)} results")
            all_entries.extend(entries)
        except Exception as e:
            print(f"  Error fetching results: {e}")

    papers = deduplicate(all_entries, min_date)
    papers.sort(key=lambda p: p["date"], reverse=True)
    print(f"Total unique papers for {topic}: {len(papers)}")
    return papers


def fetch_and_process_preprints(
    topic: str, min_date: str, max_results: int
) -> list[dict]:
    """Fetch and process preprints (bioRxiv/medRxiv) for a single topic."""
    print(f"\n=== Processing preprints for topic: {topic} ===")
    today = datetime.date.today().isoformat()
    keywords = QUERY_TOPICS[topic]
    all_entries: list[dict] = []

    for kw in keywords:
        query = f"(SRC:PPR) AND ({kw}) AND FIRST_PDATE:[{min_date} TO {today}]"
        print(f"Querying preprints: {kw}")
        try:
            raw = fetch_europepmc(query, max_results)
            entries = parse_entries(raw)
            # Fill in journal name for preprints that lack it
            for e in entries:
                if not e["journal"]:
                    e["journal"] = "bioRxiv"
            print(f"  Found {len(entries)} results")
            all_entries.extend(entries)
        except Exception as e:
            print(f"  Error fetching results: {e}")

    papers = deduplicate(all_entries, min_date)
    papers.sort(key=lambda p: p["date"], reverse=True)
    print(f"Total unique preprints for {topic}: {len(papers)}")
    return papers


def merge_and_deduplicate(
    topic_results: dict[str, list[dict]], min_date: str
) -> list[dict]:
    all_entries = []
    for papers in topic_results.values():
        all_entries.extend(papers)
    papers = deduplicate(all_entries, min_date)
    papers.sort(key=lambda p: p["date"], reverse=True)
    return papers


def main() -> None:
    args = parse_arguments()
    min_date = get_min_date(args.days)
    print(f"Searching for papers from {min_date} onwards")

    if args.journal:
        print(f"Filtering to journal: {args.journal}")

    if args.all_topics:
        topics = list(QUERY_TOPICS.keys())
    else:
        topics = [args.topic]

    topic_results = {}
    preprint_results = {}

    for topic in topics:
        # Journal search
        papers = fetch_and_process_topic(topic, min_date, args.max_results, args.journal)
        topic_results[topic] = papers

        if not papers:
            print(f"No journal papers found for topic: {topic}")

        # Preprint search (bioRxiv/medRxiv)
        if not args.no_preprints and not args.journal:
            preprints = fetch_and_process_preprints(topic, min_date, args.max_results)
            preprint_results[topic] = preprints
            if not preprints:
                print(f"No preprints found for topic: {topic}")

        # Per-topic output (journals only)
        if papers:
            if args.all_topics:
                txt_path = os.path.join(OUTPUT_DIR, f"journal_results_{topic}_{TODAY}.txt")
                md_path = os.path.join(OUTPUT_DIR, f"JOURNAL_{topic}_{TODAY}.md")
            else:
                txt_path = OUTPUT_TXT
                md_path = OUTPUT_MD

            write_txt(papers, txt_path, topic, args.days)
            print(f"Wrote {txt_path}")

            write_md(papers, md_path, topic, args.days)
            print(f"Wrote {md_path}")

        # Per-topic preprint output
        if preprint_results.get(topic):
            if args.all_topics:
                pp_txt = os.path.join(OUTPUT_DIR, f"preprint_results_{topic}_{TODAY}.txt")
                pp_md = os.path.join(OUTPUT_DIR, f"PREPRINT_{topic}_{TODAY}.md")
            else:
                pp_txt = os.path.join(OUTPUT_DIR, f"preprint_results_{TODAY}.txt")
                pp_md = os.path.join(OUTPUT_DIR, f"PREPRINT_{TODAY}.md")

            write_txt(preprint_results[topic], pp_txt, f"{topic} (preprints)", args.days)
            print(f"Wrote {pp_txt}")

            write_md(preprint_results[topic], pp_md, f"{topic} (preprints)", args.days)
            print(f"Wrote {pp_md}")

    # Combined output across all topics
    if args.all_topics and len(topic_results) > 1:
        print("\n=== Creating combined output ===")
        combined_papers = merge_and_deduplicate(topic_results, min_date)
        print(f"Total unique journal papers across all topics: {len(combined_papers)}")

        combined_txt = os.path.join(OUTPUT_DIR, f"journal_results_all_{TODAY}.txt")
        combined_md = os.path.join(OUTPUT_DIR, f"JOURNAL_all_{TODAY}.md")

        write_txt(combined_papers, combined_txt, "all", args.days)
        print(f"Wrote {combined_txt}")

        write_md(combined_papers, combined_md, "all", args.days)
        print(f"Wrote {combined_md}")

        if preprint_results:
            combined_preprints = merge_and_deduplicate(preprint_results, min_date)
            print(f"Total unique preprints across all topics: {len(combined_preprints)}")

            pp_txt = os.path.join(OUTPUT_DIR, f"preprint_results_all_{TODAY}.txt")
            pp_md = os.path.join(OUTPUT_DIR, f"PREPRINT_all_{TODAY}.md")

            write_txt(combined_preprints, pp_txt, "all (preprints)", args.days)
            print(f"Wrote {pp_txt}")

            write_md(combined_preprints, pp_md, "all (preprints)", args.days)
            print(f"Wrote {pp_md}")


if __name__ == "__main__":
    main()
