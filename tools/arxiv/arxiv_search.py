"""Search arXiv for spatial omics prediction papers and generate formatted output."""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import datetime
import os
import argparse

QUERY_TOPICS = {
    "prediction": [
        # Spatial omics broad
        'all:"spatial omics" AND all:"prediction"',
        'all:"spatial omics" AND all:"deep learning"',
        # Spatial transcriptomics
        'all:"spatial transcriptomics" AND all:"inference"',
        'all:"spatial transcriptomics" AND all:"prediction"',
        'all:"spatial transcriptomics" AND all:"deep learning"',
        'all:"spatial transcriptomics" AND all:"gene expression"',
        'all:"spatial gene expression" AND all:"histology"',
        # Gene / cell type prediction from images
        'all:"gene expression prediction" AND all:"histology"',
        'all:"cell type" AND all:"spatial transcriptomics" AND all:"prediction"',
        'all:"cell type deconvolution" AND all:"spatial"',
        # Spatial proteomics
        'all:"spatial proteomics" AND all:"prediction"',
        'all:"spatial proteomics" AND all:"deep learning"',
        # H&E image to omics
        'all:"histology" AND all:"transcriptomics" AND all:"prediction"',
        'all:"H&E" AND all:"gene expression" AND all:"predict"',
        'all:"pathology" AND all:"spatial transcriptomics" AND all:"neural network"',
    ],
    "analysis": [
        # Preprocessing and normalization
        'all:"spatial transcriptomics" AND all:"normalization"',
        'all:"spatial transcriptomics" AND all:"batch correction"',
        # Clustering and domain identification
        'all:"spatial transcriptomics" AND all:"clustering"',
        'all:"spatial domain" AND all:"identification"',
        'all:"spatial omics" AND all:"segmentation"',
        # Statistical analysis
        'all:"spatial transcriptomics" AND all:"differential expression"',
        'all:"spatially variable genes"',
        # Data integration and alignment
        'all:"spatial omics" AND all:"integration"',
        'all:"spatial transcriptomics" AND all:"alignment"',
        # Data imputation and denoising
        'all:"spatial transcriptomics" AND all:"imputation"',
        'all:"spatial transcriptomics" AND all:"denoising"',
        # Platform-specific analysis
        'all:"imaging mass cytometry"',
        'all:"multiplexed imaging" AND all:"analysis"',
        'all:"spatial proteomics" AND all:"analysis"',
        'all:"multi-modal" AND all:"spatial omics"',
    ]
}
MAX_RESULTS = 50
ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


def fetch_arxiv(query: str, max_results: int = MAX_RESULTS) -> str:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API}?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_entries(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", NS):
        arxiv_id = entry.find("atom:id", NS).text.strip()
        # Skip feed-level result entries without real IDs
        if "/abs/" not in arxiv_id:
            continue
        title = " ".join(entry.find("atom:title", NS).text.split())
        abstract = " ".join(entry.find("atom:summary", NS).text.split())
        published = entry.find("atom:published", NS).text[:10]  # YYYY-MM-DD
        link = arxiv_id.replace("http://", "https://")
        entries.append({
            "id": arxiv_id.split("/abs/")[-1],
            "title": title,
            "link": link,
            "date": published,
            "abstract": abstract,
        })
    return entries


def get_min_date(days: int) -> str:
    """Calculate minimum date. days=0 means all since 2023-01-01."""
    if days == 0:
        return "2023-01-01"
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    return cutoff.isoformat()


def deduplicate(all_entries: list[dict], min_date: str) -> list[dict]:
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
        f.write(f"arXiv Spatial Omics Papers - Topic: {topic}\n")
        f.write(f"Search period: {min_date} to {today}")
        if days > 0:
            f.write(f" ({days} days)\n")
        else:
            f.write(" (all papers since 2023)\n")
        f.write(f"Total papers: {len(papers)}\n")
        f.write("=" * 80 + "\n\n")

        for p in papers:
            f.write(f"Title: {p['title']}\n")
            f.write(f"Link: {p['link']}\n")
            f.write(f"Date: {p['date']}\n")
            f.write(f"Abstract: {p['abstract']}\n")
            f.write("---\n")


def write_md(papers: list[dict], path: str, topic: str, days: int) -> None:
    today = datetime.date.today().isoformat()
    min_date = get_min_date(days)

    topic_title = topic.capitalize() if topic != "all" else "All Topics"
    lines = [
        f"# arXiv Spatial Omics Papers - {topic_title}",
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
        "Auto-generated by `python tools/arxiv/arxiv_search.py`.",
        "",
        "| Published | Title | Assignment | Modalities | Platform | Code |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for p in papers:
        title_cell = f"[{p['title']}]({p['link']})"
        lines.append(f"| {p['date']} arXiv | {title_cell} | - | - | - | - |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Search arXiv for spatial omics papers with topic-based filtering.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: prediction topic, last 7 days
  python tools/arxiv/arxiv_search.py

  # Analysis topic, last 14 days
  python tools/arxiv/arxiv_search.py --topic analysis --days 14

  # All topics, last week
  python tools/arxiv/arxiv_search.py --all-topics

  # All papers since 2023
  python tools/arxiv/arxiv_search.py --days 0
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
        default=7,
        help="Fetch from last N days (default: 7, use 0 for all since 2023)"
    )
    parser.add_argument(
        "-a", "--all-topics",
        action="store_true",
        help="Run all topics (overrides --topic)"
    )
    parser.add_argument(
        "-m", "--max-results",
        type=int,
        default=MAX_RESULTS,
        help=f"Max results per query (default: {MAX_RESULTS})"
    )
    return parser.parse_args()


def fetch_and_process_topic(topic: str, min_date: str, max_results: int) -> list[dict]:
    """Fetch and process papers for a single topic."""
    print(f"\n=== Processing topic: {topic} ===")
    queries = QUERY_TOPICS[topic]
    all_entries: list[dict] = []

    for q in queries:
        print(f"Querying: {q}")
        try:
            xml = fetch_arxiv(q, max_results)
            entries = parse_entries(xml)
            print(f"  Found {len(entries)} results")
            all_entries.extend(entries)
        except Exception as e:
            print(f"  Error fetching results: {e}")

    papers = deduplicate(all_entries, min_date)
    papers.sort(key=lambda p: p["date"], reverse=True)
    print(f"Total unique papers for {topic}: {len(papers)}")

    return papers


def merge_and_deduplicate(topic_results: dict[str, list[dict]], min_date: str) -> list[dict]:
    """Combine results from multiple topics and deduplicate."""
    all_entries = []
    for papers in topic_results.values():
        all_entries.extend(papers)

    papers = deduplicate(all_entries, min_date)
    papers.sort(key=lambda p: p["date"], reverse=True)
    return papers


def main() -> None:
    args = parse_arguments()

    # Calculate min_date from --days
    min_date = get_min_date(args.days)
    today = datetime.date.today().isoformat()
    print(f"Searching for papers from {min_date} onwards")

    # Determine topics to run
    if args.all_topics:
        topics = list(QUERY_TOPICS.keys())
    else:
        topics = [args.topic]

    # Fetch papers for each topic
    topic_results = {}
    for topic in topics:
        papers = fetch_and_process_topic(topic, min_date, args.max_results)
        topic_results[topic] = papers

        if not papers:
            print(f"No papers found for topic: {topic}")

    # Combine all papers from all topics
    print("\n=== Creating output ===")
    all_papers = merge_and_deduplicate(topic_results, min_date)

    if not all_papers:
        print("No papers found for any topic")
        return

    # Determine topic label for filename and content
    if args.all_topics:
        topic_label = "all"
    else:
        topic_label = args.topic

    print(f"Total unique papers: {len(all_papers)}")

    # Generate dated output files
    txt_path = os.path.join(OUTPUT_DIR, f"arxiv_results_{today}.txt")
    md_path = os.path.join(OUTPUT_DIR, f"ARXIV_{today}.md")

    write_txt(all_papers, txt_path, topic_label, args.days)
    print(f"Wrote {txt_path}")

    write_md(all_papers, md_path, topic_label, args.days)
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
