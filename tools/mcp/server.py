"""
Spatial Omics Paper Knowledge Base — MCP Server.

5 tools: search_papers, ingest_paper, discover_papers, query_knowledge,
         check_institutional_access.
Works with Claude Code, Claude Desktop, and Gemini CLI.
"""

import json
import traceback

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from core.search import search_papers
from core.ingest import ingest_paper
from core.discovery import discover_papers
from core.query import query_knowledge
from core.institutional import check_access, get_startup_status

server = Server("paper-kb")

# ── First-call banner ────────────────────────────────────────────
# On the very first tool call of a session, prepend institutional
# access status so the user (and the LLM) know whether paywall
# bypass is working.
_shown_startup_banner = False


def _maybe_startup_banner() -> str | None:
    """Return the startup banner once, then None forever."""
    global _shown_startup_banner
    if _shown_startup_banner:
        return None
    _shown_startup_banner = True
    status = get_startup_status()
    ready = status.get("ready", False)
    tag = "READY" if ready else "ACTION NEEDED"
    return (
        f"[paper-kb] Institutional access: {tag}\n"
        f"{status['message']}\n"
        f"{'─' * 50}"
    )


# ── MCP Prompts ──────────────────────────────────────────────────
# These show up in Claude Desktop's prompt picker and in clients
# that support the prompts/list capability.

@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="setup-institutional-access",
            description=(
                "Configure CWRU institutional login to download paywalled papers. "
                "Walks through cookie export and config setup."
            ),
        ),
        types.Prompt(
            name="paper-kb-status",
            description="Check paper knowledge base status: paper count, institutional access, DB health.",
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> types.GetPromptResult:
    if name == "setup-institutional-access":
        status = get_startup_status()
        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            "I want to set up institutional access for the paper-kb MCP server "
                            "so I can download paywalled papers through my CWRU library login.\n\n"
                            f"Current status:\n{status['message']}\n\n"
                            "Guide me through the setup. The steps are:\n"
                            "1. Export browser cookies after logging into login.case.edu/cas/login\n"
                            "2. Enable institutional_access in tools/mcp/config.json\n"
                            "3. Test with check_institutional_access tool\n\n"
                            "The export script is: python tools/mcp/export_cookies.py"
                        ),
                    ),
                )
            ],
        )

    if name == "paper-kb-status":
        inst_status = get_startup_status()
        try:
            from core.database import get_db, get_collection
            conn = get_db()
            paper_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            conn.close()
            collection = get_collection()
            chunk_count = collection.count()
            db_info = f"Papers: {paper_count}, Chunks: {chunk_count}"
        except Exception as e:
            db_info = f"DB error: {e}"

        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Paper KB status:\n"
                            f"  {db_info}\n"
                            f"  Institutional access: {inst_status['message']}"
                        ),
                    ),
                )
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")


# ── Tools ────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_papers",
            description=(
                "Semantic search across the spatial omics paper knowledge base. "
                "Uses sentence-transformer embeddings to find relevant paper passages. "
                "Returns ranked text chunks with paper metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "year_min": {
                        "type": "integer",
                        "description": "Only papers from this year onward",
                    },
                    "year_max": {
                        "type": "integer",
                        "description": "Only papers up to this year",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Filter by spatial platform (Visium, Xenium, MERFISH, etc.)",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 8,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="ingest_paper",
            description=(
                "Add a paper to the knowledge base by DOI, URL, or local PDF path. "
                "Fetches metadata, downloads open-access PDFs, extracts text, "
                "and creates searchable embeddings. "
                "Use source='readme' to bulk-ingest all papers from README.md."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {
                        "type": "string",
                        "description": "Paper DOI (e.g., 10.1038/s41592-025-02795-z)",
                    },
                    "url": {
                        "type": "string",
                        "description": "Paper URL (arXiv, Nature, bioRxiv — auto-resolves to DOI)",
                    },
                    "pdf_path": {
                        "type": "string",
                        "description": "Absolute path to a local PDF file",
                    },
                    "source": {
                        "type": "string",
                        "description": "Set to 'readme' to bulk-ingest all papers from README.md",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata overrides (title, year, assignment, modalities, platform, code_url)",
                    },
                },
            },
        ),
        types.Tool(
            name="discover_papers",
            description=(
                "Search external databases for new spatial omics papers. "
                "Searches PubMed, Semantic Scholar, Crossref, Europe PMC, and arXiv. "
                "Returns candidates with metadata and flags papers already in the knowledge base."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search topic query",
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["pubmed", "semantic_scholar", "crossref", "europe_pmc", "arxiv"],
                        },
                        "description": "Which sources to search (default: pubmed, semantic_scholar, europe_pmc)",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Only papers within this many days",
                        "default": 30,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results per source",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="query_knowledge",
            description=(
                "Deep knowledge retrieval from the paper database. "
                "Actions: 'full_text' (complete paper text), 'metadata' (structured fields), "
                "'list_papers' (all papers with basic info), 'sql' (custom SELECT query)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["full_text", "metadata", "list_papers", "sql"],
                        "description": "What to retrieve",
                    },
                    "paper_id": {
                        "type": "string",
                        "description": "Paper ID or DOI (for full_text and metadata actions)",
                    },
                    "sql": {
                        "type": "string",
                        "description": "SQL SELECT query (for sql action)",
                    },
                    "params": {
                        "type": "array",
                        "description": "Query parameters for SQL placeholders",
                        "items": {},
                    },
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="check_institutional_access",
            description=(
                "Test institutional access configuration. "
                "Verifies EZproxy, cookies, and proxy settings by attempting "
                "to reach a known paywalled paper. Run this after configuring "
                "institutional_access in config.json."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "test_doi": {
                        "type": "string",
                        "description": "DOI to test access with (default: a Nature Methods paper)",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "search_papers":
            result = search_papers(**arguments)
        elif name == "ingest_paper":
            result = ingest_paper(**arguments)
        elif name == "discover_papers":
            result = discover_papers(**arguments)
        elif name == "query_knowledge":
            result = query_knowledge(**arguments)
        elif name == "check_institutional_access":
            result = check_access(**arguments)
        else:
            result = f"Unknown tool: {name}"

        text = (
            result
            if isinstance(result, str)
            else json.dumps(result, indent=2, ensure_ascii=False)
        )

        # Prepend startup banner on first call
        banner = _maybe_startup_banner()
        if banner:
            text = f"{banner}\n\n{text}"

        return [types.TextContent(type="text", text=text)]
    except Exception as exc:
        return [
            types.TextContent(
                type="text",
                text=f"Error in {name}: {exc}\n\n{traceback.format_exc()}",
            )
        ]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
