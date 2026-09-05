# IP-SAKTI Sahayak — Implementation Plan (Using Standard Libraries + Research Best Practices)

## Research Summary

Based on comprehensive web research including Microsoft GraphRAG paper and LangSmith documentation:

### Microsoft GraphRAG Key Findings:
1. **Knowledge Graph Construction**: Extract entities/relations from documents using LLM, build graph with communities
2. **Community Detection**: Use Leiden algorithm for hierarchical community detection
3. **Community Summaries**: Generate summaries for each community for global queries
4. **Query Types**: 
   - Local search: Entity-centric, uses entity→community→chunks
   - Global search: Map-reduce over community summaries
   - Drift search: Intermediate, uses community summaries + raw chunks
5. **Better than Vector RAG**: 30-50% better on global questions, handles multi-hop reasoning

### LangSmith Key Findings:
1. **Tracing**: Automatic tracing of LLM calls, chains, agents
2. **Evaluation**: Built-in evaluators for correctness, relevance, hallucination
3. **Datasets**: Curated test sets for regression testing
4. **Feedback**: Human feedback collection and analytics
5. **Dashboards**: Real-time metrics, latency, token usage, cost tracking

### Standard Libraries to Use (Battle-tested):

| Component | Library | Purpose |
|-----------|---------|---------|
| Text Splitting | langchain-text-splitters | RecursiveCharacterTextSplitter (hierarchical) |
| Document Loading | langchain-community | PDF, DOCX, HTML, TXT, Markdown loaders |
| Embeddings | sentence-transformers | Local models (bge, e5, gte families) |
| Vector Store | chromadb / faiss | Vector similarity search |
| BM25 | rank-bm25 | Lexical search |
| Reranking | sentence-transformers | Cross-encoder (bge-reranker) |
| Knowledge Graph | networkx + Leiden | Graph construction & community detection |
| LLM | langchain-openai / ollama | LLM integration |
| Orchestration | langgraph | Agent workflows |
| API | fastapi | REST API |
| Config | pydantic-settings | Configuration management |
| Monitoring | langsmith | Tracing, evaluation, dashboards |

## Architecture Overview (Enhanced with GraphRAG)

```
+---------------------------------------------------------------+
|                        IP-SAKTI Pipeline                       |
+---------------------------------------------------------------+
|                                                               |
|  1. INGESTION LAYER                                           |
|     +- Document Loader (langchain-community loaders)         |
|     +- Text Splitter (langchain-text-splitters)              |
|     +- Metadata Extractor (LLM-based)                        |
|     +- Entity/Relation Extractor (for GraphRAG)              |
|                                                               |
|  2. EMBEDDING LAYER                                           |
|     +- Embedding Models (sentence-transformers: bge-m3, e5)  |
|     +- Vector Store (ChromaDB for persistence, FAISS)        |
|     +- BM25 Index (rank-bm25 for lexical search)             |
|                                                               |
|  3. KNOWLEDGE GRAPH LAYER (GraphRAG)                         |
|     +- Entity/Relation Extraction (LLM-based)                |
|     +- Graph Construction (NetworkX)                         |
|     +- Community Detection (Leiden algorithm)                |
|     +- Community Summarization (LLM)                         |
|                                                               |
|  4. RETRIEVAL LAYER                                           |
|     +- Hybrid Search: BM25 + Vector (weighted fusion)        |
|     +- GraphRAG Local Search: Entity to Community to Chunks  |
|     +- GraphRAG Global Search: Map-reduce over Communities   |
|     +- Reranker (Cross-encoder: bge-reranker-v2-m3)         |
|     +- Query Expansion (LLM-based)                           |
|                                                               |
|  5. GENERATION LAYER (RAG)                                    |
|     +- LLM Integration (LangChain + LangGraph)               |
|     +- Structured Prompts for IP Law                         |
|     +- Citation & Source Tracking                            |
|     +- Response Formatter                                    |
|                                                               |
|  6. MONITORING & EVALUATION (LangSmith)                      |
|     +- Tracing (automatic)                                   |
|     +- Evaluation Datasets                                   |
|     +- Custom Evaluators (hallucination, citation accuracy)  |
|     +- Dashboard (latency, tokens, cost, quality)            |
|                                                               |
+---------------------------------------------------------------+
```

## Implementation Phases

### Phase 1: Core Chunking (Research Complete)
- Use `langchain-text-splitters.RecursiveCharacterTextSplitter`
- Support multiple strategies via config
- Remove all custom chunking code

### Phase 2: Document Ingestion
- Use `langchain-community` document loaders
- Support: PDF, TXT, DOCX, HTML, Markdown
- Metadata extraction per document type

### Phase 3: Embedding & Vector Store
- Use `sentence-transformers` for local embeddings (bge-m3, e5-large-v2)
- Use `ChromaDB` for persistent vector storage
- Support FAISS for in-memory speed
- BM25 index using `rank-bm25`

### Phase 4: Knowledge Graph (GraphRAG - Microsoft Research)
- Entity/Relation extraction using LLM
- Graph construction with NetworkX
- Community detection with Leiden algorithm (igraph)
- Community summarization for global queries
- Local search (entity-centric) and Global search (map-reduce)

### Phase 5: Retrieval Engine
- Hybrid search: BM25 + Vector (RRF or weighted fusion)
- GraphRAG Local Search
- GraphRAG Global Search
- Reranker using cross-encoder
- Query expansion

### Phase 6: Generation (RAG)
- LangGraph for agent orchestration
- Structured prompts for IP law queries
- Citation and source tracking
- Streaming responses

### Phase 7: API & UI Integration
- FastAPI endpoints
- WebSocket for streaming
- LangSmith integration for monitoring
- Simple test UI

### Phase 8: Evaluation & Testing
- LangSmith datasets for regression
- Custom evaluators for IP law accuracy
- Performance benchmarks
- End-to-end integration tests

## File Structure (New)

```
ip_sakti/
+-- core/
|   +-- models.py           # Pydantic models (keep existing)
|   +-- config.py           # Settings via pydantic-settings
+-- ingestion/
|   +-- __init__.py
|   +-- loaders.py          # Document loaders using langchain
|   +-- chunking.py         # Wrapper around langchain-text-splitters
|   +-- metadata.py         # Metadata extraction
|   +-- pipeline.py         # Ingestion orchestration
+-- embedding/
|   +-- __init__.py
|   +-- embedder.py         # Embedding generation
|   +-- vector_store.py     # Vector store abstraction (ChromaDB/FAISS)
+-- knowledge_graph/
|   +-- __init__.py
|   +-- extractor.py        # Entity/Relation extraction (LLM)
|   +-- graph.py            # Graph construction (NetworkX)
|   +-- community.py        # Community detection (Leiden)
|   +-- summarizer.py       # Community summarization
+-- retrieval/
|   +-- __init__.py
|   +-- bm25_retriever.py   # BM25 lexical search
|   +-- vector_retriever.py # Vector similarity search
|   +-- hybrid_retriever.py # Combined search (RRF)
|   +-- graph_retriever.py  # GraphRAG local/global search
|   +-- reranker.py         # Cross-encoder reranking
+-- generation/
|   +-- __init__.py
|   +-- prompts.py          # Prompt templates for IP law
|   +-- llm.py              # LLM wrapper (OpenAI/Ollama)
|   +-- rag_chain.py        # Standard RAG pipeline
|   +-- graph_rag_chain.py  # GraphRAG pipeline
+-- monitoring/
|   +-- __init__.py
|   +-- langsmith.py        # LangSmith integration
|   +-- evaluators.py       # Custom evaluators
|   +-- datasets.py         # Evaluation datasets
+-- api/
|   +-- __init__.py
|   +-- routes.py           # API routes
|   +-- models.py           # Request/response models
+-- main.py                 # Entry point
```

## Test Strategy

- Create `test_pipeline.py` with timers and progress tracking
- Test each component independently
- End-to-end integration test
- Performance benchmarks
- LangSmith evaluation datasets

## Next Steps (Implementation Order)

1. **Phase 1**: Delete custom chunking - Implement new chunking using langchain-text-splitters
2. **Phase 2**: Create document loaders using langchain-community
3. **Phase 3**: Implement embedding + vector store (ChromaDB + BM25)
4. **Phase 4**: Implement Knowledge Graph (GraphRAG) - Microsoft research
5. **Phase 5**: Implement Retrieval Engine (Hybrid + GraphRAG)
6. **Phase 6**: Implement Generation (RAG + GraphRAG with LangGraph)
7. **Phase 7**: Add LangSmith monitoring
8. **Phase 8**: API + UI integration
9. **Phase 9**: Evaluation & Testing

Let's start implementation!