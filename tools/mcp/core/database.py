"""
SQLite metadata store, ChromaDB vector store, and sentence-transformers embeddings.
"""

import hashlib
import json
import re
import sqlite3
from pathlib import Path

import chromadb

MCP_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MCP_ROOT.parent.parent
DATA_PATH = PROJECT_ROOT / "Knowlege-based-archive"
CHROMA_PATH = DATA_PATH / "chroma"
SQLITE_PATH = DATA_PATH / "papers.db"
CONFIG_PATH = MCP_ROOT / "config.json"

_embed_model = None


def get_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def get_embedding_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        config = get_config()
        model_name = config.get("embedding_model", "all-MiniLM-L6-v2")
        _embed_model = SentenceTransformer(model_name)
    return _embed_model


class SentenceTransformerEmbedding:
    """ChromaDB-compatible embedding function using sentence-transformers."""

    @staticmethod
    def name() -> str:
        return "sentence-transformer"

    def get_config(self) -> dict:
        return {"model": get_config().get("embedding_model", "all-MiniLM-L6-v2")}

    @classmethod
    def build_from_config(cls, config: dict):
        return cls()

    def __call__(self, input):
        model = get_embedding_model()
        # input is always a list of strings
        embeddings = model.encode(input, show_progress_bar=False)
        return embeddings.tolist()

    def embed_documents(self, input):
        return self.__call__(input)

    def embed_query(self, input):
        model = get_embedding_model()
        # input is a single string or list of strings from ChromaDB
        if isinstance(input, str):
            embedding = model.encode([input], show_progress_bar=False)
            return embedding[0].tolist()
        return self.__call__(input)


def get_chroma_client() -> chromadb.PersistentClient:
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_collection(client=None, name="spatial_omics_papers"):
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        embedding_function=SentenceTransformerEmbedding(),
        metadata={"hnsw:space": "cosine"},
    )


def get_db() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id              TEXT PRIMARY KEY,
            doi             TEXT UNIQUE,
            title           TEXT NOT NULL,
            authors         TEXT,
            year            INTEGER,
            journal         TEXT,
            abstract        TEXT,
            assignment      TEXT,
            modalities      TEXT,
            platform        TEXT,
            code_url        TEXT,
            topics          TEXT,
            methods_used    TEXT,
            key_findings    TEXT,
            pdf_path        TEXT,
            content_source  TEXT,
            content_length  INTEGER,
            added_date      TEXT,
            metadata_status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()


def make_paper_id(identifier: str) -> str:
    return hashlib.sha256(identifier.encode()).hexdigest()[:12]


def chunk_text(text: str, paper_id: str, max_chunk: int = 4000) -> list[dict]:
    """Split paper text into section-aware chunks."""
    section_pattern = re.compile(
        r"^(Abstract|Introduction|Background|Methods?|Materials?\s*and\s*Methods?|"
        r"Results?|Discussion|Conclusion|References|Acknowledgement|"
        r"Related\s*Work|Experiments?|Supplementary)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    splits = list(section_pattern.finditer(text))
    chunks = []
    seen_ids = set()

    if splits:
        for i, match in enumerate(splits):
            section_name = match.group(1).strip().lower()
            start = match.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            section_text = text[start:end].strip()

            if not section_text:
                continue

            for j in range(0, len(section_text), max_chunk):
                chunk = section_text[j:j + max_chunk].strip()
                if len(chunk) > 50:
                    chunk_id = f"{paper_id}_{section_name}_{j // max_chunk}"
                    # Deduplicate IDs from repeated section names
                    suffix = 0
                    while chunk_id in seen_ids:
                        suffix += 1
                        chunk_id = f"{paper_id}_{section_name}_{j // max_chunk}_v{suffix}"
                    seen_ids.add(chunk_id)
                    chunks.append({
                        "id": chunk_id,
                        "text": chunk,
                        "section": section_name,
                    })
    else:
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        current = ""
        idx = 0
        for para in paragraphs:
            if len(current) + len(para) > max_chunk:
                if current:
                    chunks.append({
                        "id": f"{paper_id}_p{idx}",
                        "text": current.strip(),
                        "section": "body",
                    })
                    idx += 1
                current = para
            else:
                current = current + "\n\n" + para if current else para
        if current.strip():
            chunks.append({
                "id": f"{paper_id}_p{idx}",
                "text": current.strip(),
                "section": "body",
            })

    return chunks


def embed_chunks(chunks: list[dict], metadata: dict, collection=None):
    """Embed and store text chunks in ChromaDB."""
    if not chunks:
        return

    if collection is None:
        collection = get_collection()

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = []
    for c in chunks:
        meta = {
            "paper_id": metadata.get("id", ""),
            "title": (metadata.get("title") or "")[:200],
            "authors": (metadata.get("authors") or "")[:200],
            "year": metadata.get("year") or 0,
            "doi": metadata.get("doi") or "",
            "section": c["section"],
            "assignment": metadata.get("assignment") or "",
            "modalities": metadata.get("modalities") or "",
            "platform": metadata.get("platform") or "",
            "topics": json.dumps(metadata.get("topics") or []),
        }
        metadatas.append(meta)

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def store_metadata(paper_id: str, meta: dict):
    """Insert or update paper metadata in SQLite."""
    conn = get_db()
    conn.execute("""
        INSERT INTO papers (id, doi, title, authors, year, journal, abstract,
            assignment, modalities, platform, code_url, topics, methods_used,
            key_findings, pdf_path, content_source, content_length, added_date,
            metadata_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        ON CONFLICT(id) DO UPDATE SET
            doi=excluded.doi, title=excluded.title, authors=excluded.authors,
            year=excluded.year, journal=excluded.journal, abstract=excluded.abstract,
            assignment=excluded.assignment, modalities=excluded.modalities,
            platform=excluded.platform, code_url=excluded.code_url,
            topics=excluded.topics, methods_used=excluded.methods_used,
            key_findings=excluded.key_findings, pdf_path=excluded.pdf_path,
            content_source=excluded.content_source, content_length=excluded.content_length,
            metadata_status=excluded.metadata_status
    """, (
        paper_id,
        meta.get("doi"),
        meta.get("title", "Unknown"),
        meta.get("authors"),
        meta.get("year"),
        meta.get("journal"),
        meta.get("abstract"),
        meta.get("assignment"),
        meta.get("modalities"),
        meta.get("platform"),
        meta.get("code_url"),
        json.dumps(meta.get("topics")) if meta.get("topics") else None,
        json.dumps(meta.get("methods_used")) if meta.get("methods_used") else None,
        json.dumps(meta.get("key_findings")) if meta.get("key_findings") else None,
        meta.get("pdf_path"),
        meta.get("content_source"),
        meta.get("content_length"),
        meta.get("metadata_status", "pending"),
    ))
    conn.commit()
    conn.close()
