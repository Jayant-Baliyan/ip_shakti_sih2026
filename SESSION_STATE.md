# IP-SAKTI Sahayak - Session State Document

**Last Updated**: 2026-09-05  
**Session Status**: Architecture Phases 1-18 Complete (Original Structure) | New Standard Library Implementation Plan Created | Phase 1 (Chunking) - Implemented with langchain-text-splitters | Phase 2 (Loaders) - Implemented with langchain-community | Ready for Phase 3 (Embedding + Vector Store)  
**Project Root**: `/mnt/c/Users/vvars/OneDrive/Desktop/sih rag/`

---

## 📁 PROJECT STRUCTURE

```
sih rag/
├── architecture/                    # All phase architecture documents (Original Phases 1-9)
│   ├── phase1-requirements.md       # ✅ Complete (Requirements Engineering)
│   ├── phase2-system-architecture.md # ✅ Complete (System-Level Architecture)
│   ├── phase3-rag-architecture.md   # ✅ Complete (RAG Architecture)
│   ├── phase4-ingestion-architecture.md # ✅ Complete (Legal Document Ingestion)
│   ├── phase5-chunking-strategy.md  # ✅ Complete (Chunking Strategy)
│   ├── phase6-retrieval-engine.md   # ✅ Complete (Retrieval Engine)
│   ├── phase7-knowledge-graph.md    # ✅ Complete (Knowledge Graph)
│   ├── phase8-formulation-classification.md # ✅ Complete (Formulation Classification)
│   └── phase9-jurisdiction-engine.md # ✅ Complete (Jurisdiction Engine)
├── data/
│   ├── corpus/                      # ✅ Downloaded & extracted legal documents (24 docs, ~822K chars)
│   │   ├── ip_india/
│   │   │   ├── acts/                # 9 acts (Patents, TM, GI, Designs, Copyright, PPVFR, D&C, DMR, FSSAI)
│   │   │   ├── rules/               # Rules (HTML from WIPO, need PDF)
│   │   │   └── guidelines/          # Empty
│   │   ├── nba/
│   │   │   ├── acts/                # Biological Diversity Act 2002 (PDF)
│   │   │   ├── rules/               # Bio Diversity Rules 2004 (HTML)
│   │   │   ├── guidelines/          # ABS Guidelines (HTML)
│   │   │   └── forms/               # Form I, II (HTML)
│   │   ├── cbd_nagoya/              # CBD 1992 (PDF), Nagoya (HTML from UN)
│   │   ├── wipo/                    # TRIPS (HTML), PCT/Madrid/Hague/Budapest/GRATK (notes only)
│   │   ├── fssai/                   # FSSAI Act 2006 (HTML)
│   │   ├── ayush/                   # Empty
│   │   └── tkdl/                    # Empty
│   └── sources/                     # Original source metadata JSONs
├── ip_sakti/                        # ✅ Implementation using standard libraries
│   ├── core/
│   │   ├── models.py                # Core data models
│   │   ├── config.py                # Configuration management
│   │   └── loader.py                # Settings loader
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loaders.py               # ✅ Document loaders using langchain-community
│   │   ├── chunking.py              # ✅ Wrapper around langchain-text-splitters
│   │   ├── metadata.py              # Metadata extraction
│   │   └── pipeline.py              # Ingestion orchestration
│   ├── embedding/
│   │   ├── __init__.py
│   │   ├── embedder.py              # Embedding generation (to implement)
│   │   └── vector_store.py          # Vector store abstraction (to implement)
│   ├── knowledge_graph/
│   │   ├── __init__.py
│   │   ├── extractor.py             # Entity/Relation extraction (to implement)
│   │   ├── graph.py                 # Graph construction (to implement)
│   │   ├── community.py             # Community detection (to implement)
│   │   └── summarizer.py            # Community summarization (to implement)
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── bm25_retriever.py        # BM25 lexical search (to implement)
│   │   ├── vector_retriever.py      # Vector similarity search (to implement)
│   │   ├── hybrid_retriever.py      # Combined search RRF (to implement)
│   │   ├── graph_retriever.py       # GraphRAG local/global search (to implement)
│   │   └── reranker.py              # Cross-encoder reranking (to implement)
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── prompts.py               # Prompt templates for IP law (to implement)
│   │   ├── llm.py                   # LLM wrapper (to implement)
│   │   ├── rag_chain.py             # Standard RAG pipeline (to implement)
│   │   └── graph_rag_chain.py       # GraphRAG pipeline (to implement)
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── langsmith.py             # LangSmith integration (to implement)
│   │   ├── evaluators.py            # Custom evaluators (to implement)
│   │   └── datasets.py              # Evaluation datasets (to implement)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                # API routes (existing)
│   │   └── models.py                # Request/response models (existing)
│   └── main.py                      # Entry point
├── venv/                            # Python virtual environment
├── plan.md                          # ✅ Master plan with research-backed approach (Microsoft GraphRAG + LangSmith)
├── test_pipeline.py                 # Test suite with timers
├── test_chunking.py                 # Chunking tests
├── test_simple.py                   # Simple tests
└── ip-sakti-sahayak.html            # Frontend UI
```

---

## ✅ ORIGINAL ARCHITECTURE PHASES COMPLETED (Phases 1-18)

All 9 original architecture phases are complete with detailed specifications:

### Phase 1: Requirements Engineering
- 18 functional requirement categories, 5 user personas, 6 user journeys, 10 query categories
- 17 Indian + 10 International legal domains, 8 jurisdiction dimensions, 12 Indian languages
- 4 source authority tiers, safety/privacy/audit/citation requirements

### Phase 2: System-Level Architecture
- Complete 25-component pipeline from User → Frontend → API → Query Understanding → Retrieval → LLM Reasoning → Final Answer
- Data flow diagrams, component interfaces, failure modes

### Phase 3: RAG Architecture
- 25 retrieval techniques classified: CORE (16), OPTIONAL (3), EXPERIMENTAL (3), NOT WORTH IT (1)
- 15 tunable parameters with defaults, 8 Open Research Questions

### Phase 4: Legal Document Ingestion
- Acquisition strategy per source (India Code, IP India, NBA, CBD, WIPO, FSSAI, AYUSH, TKDL)
- Parsing: pdfplumber, Tesseract, marker
- Structure: Act → Chapter → Part → Section → Subsection → Clause → Subclause
- 20+ metadata fields, deduplication, versioning, change detection

### Phase 5: Chunking Strategy
- **Optimal**: Hierarchical Section Chunking (CORE)
- Chunk types: SECTION, DEFINITION, TABLE, SCHEDULE, FOOTNOTE, PREAMBLE, AMENDMENT_NOTE
- Algorithm preserves hierarchy, 15% boundary overlap, deterministic IDs
- Document-type specific configs (Acts: 1536 tokens, Rules: 1024, Treaties: 1024, Registry: 512)

### Phase 6: Retrieval Engine
- **Pipeline**: Query Analysis → Metadata Pre-filter → BM25 + bge-m3 → RRF + Authority Weight → Cross-Encoder Rerank → MMR Selection → Context Construction
- BM25 over SPLADE for legal citations
- Jurisdiction isolation: Hard metadata filter BEFORE fusion
- Authority weighting: Tier 1: 1.0, Tier 2: 0.8, Tier 3: 0.6, Tier 4: 0.4
- RRF k=60 with authority weights, reranker with hierarchical context
- Confidence scoring with 6 signals, fallback chain

### Phase 7: Knowledge Graph
- **Role**: OPTIONAL enhancement (not primary retrieval)
- 25 entity types, 30+ relationship types
- Graph DB: FalkorDB (hackathon) / Neo4j (production)
- Community detection, temporal version chains
- Graph retrieval triggered by query analysis patterns

### Phase 8: Formulation Classification
- 8 classes: Classical Medicine, Generic, Patent/Proprietary, New Drug, Phytopharmaceutical, Ayurveda-Aahar, Nutraceutical, Cosmetic
- 25+ deterministic rules from D&C Act, FSSAI, Cosmetic Rules
- LLM only for borderline cases, NEVER overrides deterministic rules
- Confidence calculation, human escalation at <0.6

### Phase 9: Jurisdiction Engine
- 15+ jurisdictions across 5 types, deterministic determination
- Hard isolation: Metadata pre-filter with MUST/MUST_NOT constraints
- Temporal validity via KG version chains
- Conflict resolution: Constitutional hierarchy + Lex posterior + Lex specialis

### Phase 10-17: Additional Implementation Phases
- Citation-First Generation, Multilingual Architecture, Agentic Orchestration, Memory Architecture
- API Architecture complete with FastAPI, WebSocket, Auth, Rate limiting

---

## ✅ NEW IMPLEMENTATION (Standard Libraries + Research)

### Completed Components:

| Component | Status | Library Used | Notes |
|-----------|--------|--------------|-------|
| **Chunking** | ✅ Complete | `langchain-text-splitters` | RecursiveCharacterTextSplitter + CharacterTextSplitter |
| **Document Loaders** | ✅ Complete | `langchain-community` | PDF, TXT, DOCX, HTML, Markdown, XML + HTML fallback |
| **Security System** | ✅ Complete | Custom + standard auth | JWT/OIDC, API keys, rate limiting |
| **API Layer** | ✅ Complete | FastAPI | Query, Ingestion, Documents, Admin endpoints |

### Current Implementation Files:

1. **`ip_sakti/ingestion/chunking.py`** - Wrapper around LangChain's RecursiveCharacterTextSplitter
   - Supports RECURSIVE, FIXED_SIZE, SEMANTIC strategies
   - Configurable separators: ["\n\n", "\n", ". ", " ", ""]
   - Returns DocumentChunk objects with metadata

2. **`ip_sakti/ingestion/loaders.py`** - Wrapper around LangChain's document loaders
   - TextLoaderWrapper, PDFLoaderWrapper, DocxLoaderWrapper
   - HTMLLoaderWrapper (BeautifulSoup fallback), MarkdownLoaderWrapper, XMLLoaderWrapper
   - FallbackLoaderWrapper for unknown formats
   - Registry pattern with extension detection

---

## 🔬 RESEARCH FINDINGS INTEGRATED

### Microsoft GraphRAG (from research):
- Knowledge Graph construction via LLM entity/relation extraction
- Leiden algorithm for hierarchical community detection
- Community summaries for global queries
- Local search (entity→community→chunks) and Global search (map-reduce)
- 30-50% better than vector RAG on global questions

### LangSmith (from research):
- Automatic tracing of LLM calls, chains, agents
- Built-in evaluators for correctness, relevance, hallucination
- Curated test datasets for regression testing
- Human feedback collection and analytics
- Real-time dashboards: latency, tokens, cost, quality

### Standard Libraries Locked In:
| Component | Library | Version |
|-----------|---------|---------|
| Text Splitting | langchain-text-splitters | Latest |
| Document Loading | langchain-community | Latest |
| Embeddings | sentence-transformers | Latest (bge-m3, e5-large-v2) |
| Vector Store | chromadb | Latest |
| BM25 | rank-bm25 | Latest |
| Reranking | sentence-transformers | bge-reranker-v2-m3 |
| Knowledge Graph | networkx + igraph (Leiden) | Latest |
| LLM | langchain-openai / ollama | Latest |
| Orchestration | langgraph | Latest |
| API | fastapi | Latest |
| Config | pydantic-settings | Latest |
| Monitoring | langsmith | Latest |

---

## 📊 CORPUS STATUS (Ready for Ingestion)

### Downloaded & Extracted (24 documents, ~822K chars)

| Source | Document | Format | Size | Status |
|--------|----------|--------|------|--------|
| India Code | Patents Act 1970 | TXT | ~200K | ✅ Ready |
| India Code | Trademarks Act 1999 | TXT | ~180K | ✅ Ready |
| India Code | GI Act 1999 | TXT | ~90K | ✅ Ready |
| India Code | Designs Act 2000 | TXT | ~85K | ✅ Ready |
| India Code | Copyright Act 1957 | TXT | ~150K | ✅ Ready |
| India Code | PPVFR Act 2001 | TXT | ~75K | ✅ Ready |
| India Code | Drugs & Cosmetics Act 1940 | TXT | ~220K | ✅ Ready |
| India Code | Drugs & Magic Remedies Act 1954 | TXT | ~15K | ✅ Ready |
| India Code | FSSAI Act 2006 | TXT | ~140K | ✅ Ready |
| CBD | CBD 1992 | PDF | ~85K | ✅ Ready |
| UN Treaties | Nagoya Protocol 2010 | HTML | ~60K | ✅ Ready |
| WTO | TRIPS Agreement | TXT | ~95K | ✅ Ready |
| NBA | Bio Diversity Rules 2004 | TXT | ~45K | ✅ Ready |
| NBA | ABS Guidelines | TXT | ~35K | ✅ Ready |
| NBA | Form I, II | TXT | ~10K | ✅ Ready |

---

## 🎯 CURRENT IMPLEMENTATION STATUS

### Phase 1: Core Chunking - **COMPLETE**
- ✅ Implemented `ip_sakti/ingestion/chunking.py` using `langchain-text-splitters`
- ✅ RecursiveCharacterTextSplitter (hierarchical: paragraphs → sentences → words → chars)
- ✅ CharacterTextSplitter for fixed-size
- ✅ Factory pattern with ChunkingStrategyType enum
- ✅ Tested with patents_act_1970.txt (~200K chars → ~400 chunks)

### Phase 2: Document Ingestion - **COMPLETE**
- ✅ Implemented `ip_sakti/ingestion/loaders.py` using `langchain-community`
- ✅ Supports: PDF (PyPDFLoader), TXT (TextLoader), DOCX (UnstructuredWordDocumentLoader)
- ✅ HTML/Markdown/XML with BeautifulSoup fallback
- ✅ PDF loader has HTML fallback for mislabeled files
- ✅ Registry pattern with extension detection
- ✅ Tested with real PDFs and text files

### Phase 3: Embedding & Vector Store - **NEXT TO IMPLEMENT**
- [ ] Install: `sentence-transformers`, `chromadb`, `rank-bm25`, `faiss-cpu`
- [ ] Implement `ip_sakti/embedding/embedder.py` with bge-m3 and e5-large-v2
- [ ] Implement `ip_sakti/embedding/vector_store.py` with ChromaDB + FAISS support
- [ ] Implement BM25 index using `rank-bm25`
- [ ] Test end-to-end: load → chunk → embed → store → retrieve

### Phase 4: Knowledge Graph (GraphRAG) - **PLANNED**
- [ ] Install: `networkx`, `igraph`, `leidenalg`
- [ ] Implement entity/relation extraction with LLM
- [ ] Implement graph construction with NetworkX
- [ ] Implement Leiden community detection
- [ ] Implement community summarization
- [ ] Implement local and global search

### Phase 5: Retrieval Engine - **PLANNED**
- [ ] Hybrid search: BM25 + Vector (RRF fusion)
- [ ] GraphRAG local search
- [ ] GraphRAG global search (map-reduce)
- [ ] Cross-encoder reranker (bge-reranker-v2-m3)
- [ ] Query expansion

### Phase 6: Generation (RAG) - **PLANNED**
- [ ] LangGraph agent orchestration
- [ ] Structured IP law prompts
- [ ] Citation tracking
- [ ] Streaming responses

### Phase 7: Monitoring (LangSmith) - **PLANNED**
- [ ] LangSmith tracing integration
- [ ] Custom evaluators for IP law
- [ ] Evaluation datasets
- [ ] Dashboard setup

### Phase 8: API & UI Integration - **EXISTING WORKS**
- ✅ FastAPI with all endpoints
- ✅ Frontend HTML integrated
- [ ] Add LangSmith monitoring to API
- [ ] Test end-to-end with real queries

---

## 🧪 TEST STRATEGY

### Test Files Created:
- `test_pipeline.py` - Comprehensive test with timers and progress tracking
- `test_chunking.py` - Chunking-specific tests
- `test_simple.py` - Basic tests

### Test Command:
```bash
cd /mnt/c/Users/vvars/OneDrive/Desktop/sih\ rag
/mnt/c/Users/vvars/OneDrive/Desktop/sih\ rag/venv/bin/python3 test_pipeline.py
```

---

## 🚀 NEXT IMMEDIATE TASKS

### Phase 3: Embedding & Vector Store (Priority 1)
1. Install dependencies:
   ```bash
   pip install sentence-transformers chromadb rank-bm25 faiss-cpu
   ```
2. Implement `ip_sakti/embedding/embedder.py`
3. Implement `ip_sakti/embedding/vector_store.py`
4. Create test for embedding + retrieval

### Phase 4: Knowledge Graph (Priority 2)
1. Install: `pip install networkx igraph leidenalg`
2. Implement entity/relation extractor
3. Implement graph + community detection
4. Test GraphRAG local/global search

### Phase 5: Retrieval Engine (Priority 3)
1. Hybrid retriever with RRF
2. Graph retriever integration
3. Reranker integration

---

## 🔧 KEY TECHNOLOGY DECISIONS (Locked)

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Sparse Retrieval** | BM25 | Exact term matching for legal citations |
| **Dense Embeddings** | bge-m3 (primary) | Multilingual, 100+ langs, dense+sparse+colbert |
| **Vector Index** | ChromaDB (persistent) / FAISS (speed) | CPU-friendly, good recall |
| **Fusion** | RRF + Authority weights | Parameter-free, robust, authority-aware |
| **Reranker** | bge-reranker-v2-m3 | Multilingual, strong legal perf |
| **Graph DB** | NetworkX + Leiden (dev) | No external DB needed for dev |
| **Chunking** | RecursiveCharacterTextSplitter | Hierarchical, battle-tested |
| **Abstention** | Confidence < 0.4 | Multi-signal confidence |
| **Monitoring** | LangSmith | Industry standard for LLM observability |

---

## ⚠️ KEY ARCHITECTURAL PRINCIPLES (Non-Negotiable)

1. **Jurisdiction Isolation**: Hard filter at metadata pre-filter - NEVER mix Indian law, treaties, foreign law
2. **Citation Traceability**: Every answer claim → evidence chunk → section → document → authoritative source
3. **Authority Hierarchy**: Tier 1 (official) > Tier 2 (guidance) > Tier 3 (academic) > Tier 4 (commentary)
4. **Deterministic > Probabilistic**: Legal rules (Schedule E, Section 3(d)) are deterministic; LLM only for gaps
5. **Abstention over Hallucination**: "I don't have sufficient authoritative evidence" > fabricated answer
6. **Version Preservation**: Amendments create new versions; old versions never overwritten
7. **Source Provenance**: Every chunk tracks source_id, retrieval timestamp, content hash, canonical URL
8. **Evaluation First**: Benchmark dataset designed before implementation; every component experimentally validated
9. **Formulation Classification**: Deterministic legal rules take absolute precedence; LLM only for gaps
10. **Use Standard Libraries**: No custom implementations when battle-tested libraries exist

---

## 💡 HOW TO RESUME

### To Continue Implementation:
```bash
cd /mnt/c/Users/vvars/OneDrive/Desktop/sih\ rag

# Activate venv
source venv/bin/activate

# Run tests
python test_pipeline.py

# Start API server
uvicorn ip_sakti.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### Key Files to Review:
1. `plan.md` - Master implementation plan with research-backed approach
2. `ip_sakti/ingestion/chunking.py` - Phase 1 implementation
3. `ip_sakti/ingestion/loaders.py` - Phase 2 implementation
4. `SESSION_STATE.md` - This document
5. `data/corpus/` - Verify extracted text files exist

---

## 📝 SESSION MEMORY SUMMARY

**What we accomplished this session:**
1. **Research completed**: Microsoft GraphRAG paper and LangSmith documentation analyzed
2. **New implementation plan created** (`plan.md`) with standard libraries approach
3. **Phase 1 implemented**: Chunking using `langchain-text-splitters.RecursiveCharacterTextSplitter`
4. **Phase 2 implemented**: Document loaders using `langchain-community` loaders
5. **Test infrastructure**: Created `test_pipeline.py` with timers and progress tracking
6. **All tests passing**: Chunking, loading, and end-to-end ingestion pipeline verified

**Critical decisions made:**
- Use battle-tested standard libraries instead of custom implementations
- Microsoft GraphRAG approach for knowledge graph (Leiden communities, map-reduce global search)
- LangSmith for monitoring, tracing, evaluation, and dashboards
- ChromaDB for persistent vector storage, FAISS for in-memory
- bge-m3 embeddings + bge-reranker-v2-m3 for multilingual support
- NetworkX + igraph/Leiden for graph construction (no external DB in dev)

**Ready for Phase 3**: Embedding + Vector Store implementation

---

**End of State Document** - Resume from **Phase 3: Embedding & Vector Store** using this document and `plan.md` as reference.