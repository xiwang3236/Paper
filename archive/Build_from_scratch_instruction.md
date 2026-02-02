```python
# Create the environment
conda create -n aischolar python=3.11 -y

# Activate it
conda activate aischolar

# Install core dependencies
pip install --upgrade pip
pip install anthropic biopython chromadb networkx python-dotenv pyyaml requests arxiv openai elevenlabs
```


# Big picture
```python
┌─────────────────┐
│ Paper Ingestion │ → PubMed/arXiv APIs
└────────┬────────┘
         ↓
┌─────────────────┐
│ Processing      │ → Extract metadata, abstracts, full text
│ & Embedding     │ → Generate embeddings (Claude/OpenAI)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Knowledge Graph │ → Neo4j or NetworkX
│ + Vector Store  │ → ChromaDB/FAISS for semantic search
└────────┬────────┘
         ↓
┌─────────────────┐
│ RAG Query Layer │ → Claude API with retrieval
└────────┬────────┘
         ↓
┌─────────────────┐
│ Podcast Gen     │ → Claude for script + ElevenLabs/OpenAI TTS
└─────────────────┘
```
