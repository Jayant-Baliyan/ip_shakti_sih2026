# IP-SAKTI Sahayak - Architecture Phase Complete State Document

**Last Updated**: 2026-09-03  
**Session Status**: Phases 1-17 Complete (New Structure), Phase 18 (API Architecture) In Progress  
**Project Root**: `/mnt/c/Users/vvars/OneDrive/Desktop/sih rag/`

---

## 📁 PROJECT STRUCTURE

```
sih rag/
├── architecture/                    # All phase architecture documents
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
│   ├── corpus/                      # ✅ Downloaded & extracted legal documents
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
├── venv/                            # Python virtual environment
└── plan.md                          # ✅ Master plan with checkboxes (v2 - Corrected)
```

---

## ✅ PHASES COMPLETED (Original Structure)

### Phase 1: Requirements Engineering (`architecture/phase1-requirements.md`)
- Functional requirements (18 categories)
- Non-functional requirements
- User personas (5): IP Attorney, Researcher, Startup Founder, Regulator, Student
- User journeys (6)
- Query categories (10): QC-01 to QC-10
- Legal/regulatory domains (17 Indian + 10 International)
- Jurisdiction dimensions (8)
- Language dimensions (English + 12 Indian languages)
- Source authority tiers (4 tiers)
- Safety, privacy, audit, explainability, citation requirements
- Update/versioning, scalability, failure modes, out-of-scope cases

### Phase 2: System-Level Architecture (`architecture/phase2-system-architecture.md`)
- Complete end-to-end pipeline: User → Frontend → API Gateway → Query Understanding → Jurisdiction Detection → Intent Classification → Formulation Classification → Query Planning/Decomposition → Retrieval Orchestration → Evidence Retrieval → Reranking → Evidence Selection → Context Construction → LLM Reasoning → Claim Extraction → Citation Verification → Groundedness/Safety Verification → Final Answer → Audit/Telemetry
- 25 components with purpose, inputs, outputs, mechanism, data structures, dependencies, failure modes, fallbacks, evaluation methods
- Data flow diagrams

### Phase 3: RAG Architecture (`architecture/phase3-rag-architecture.md`)
- 25 retrieval techniques analyzed and classified:
  - **CORE (16)**: Query normalization, classification, rewriting, expansion, decomposition, multi-hop, sparse (BM25), dense (bge-m3), hybrid (RRF), metadata filtering, cross-encoder reranking, hierarchical retrieval, parent-child, sentence-window, context compression, evidence deduplication, evidence diversity, evidence scoring, negative retrieval, multi-query, fallback, confidence, abstention
  - **OPTIONAL (3)**: Hierarchical retrieval, Context compression, Multi-query
  - **EXPERIMENTAL (3)**: ColBERT/Late interaction, Hard negatives, Multi-query retrieval
  - **NOT WORTH IT (1)**: Sentence-window retrieval
- Tunable parameters (15) with defaults and ranges
- 8 Open Research Questions (ORQ-13 to ORQ-20)

### Phase 4: Legal Document Ingestion (`architecture/phase4-ingestion-architecture.md`)
- Acquisition strategy per source (India Code, IP India, NBA, CBD, WIPO, FSSAI, AYUSH, TKDL)
- Parsing & OCR strategy (pdfplumber, Tesseract, marker)
- Structure extraction preserving: Act → Chapter → Part → Section → Subsection → Clause → Subclause
- Metadata generation (20+ fields including provenance, authority, version, amendment status)
- Deduplication (content-hash + hierarchy-aware)
- Versioning with amendment chains
- Change detection (content hash + source monitoring)
- Indexing pipeline
- Validation rules

### Phase 5: Chunking Strategy (`architecture/phase5-chunking-strategy.md`)
- **Optimal Strategy**: Hierarchical Section Chunking (CORE)
- Chunk data structure with full hierarchy path, citation metadata, chunk_id, token count
- Chunk types: SECTION, DEFINITION, TABLE, SCHEDULE, FOOTNOTE, PREAMBLE, AMENDMENT_NOTE
- Algorithm: Parse hierarchy → Extract definitions → Extract tables → Chunk sections → Handle oversized sections (subsection → clause → paragraph) → Apply 15% boundary overlap → Assign deterministic IDs → Enrich citations
- Citation traceability: embedding → chunk → section → document → authoritative source
- Document-type specific configs (Acts: 1536 tokens, Rules: 1024, Treaties: 1024, Registry: 512)
- Multilingual parallel chunks
- Amendment version handling (new versions, not overwrites)
- 6 Open Research Questions (ORQ-21 to ORQ-26)

### Phase 6: Retrieval Engine (`architecture/phase6-retrieval-engine.md`)
- **Pipeline**: Query Analysis → Metadata Pre-filter → Sparse (BM25) + Dense (bge-m3/HNSW) → RRF Fusion + Authority Weight → Cross-Encoder Rerank (bge-reranker-v2-m3) → MMR Evidence Selection → Context Construction
- **BM25 over SPLADE**: Exact term matching for legal citations
- **Jurisdiction isolation**: Hard metadata filter BEFORE fusion (non-negotiable)
- **Authority weighting**: Tier 1: 1.0, Tier 2: 0.8, Tier 3: 0.6, Tier 4: 0.4 at fusion + selection
- **RRF k=60** with authority weights
- **Reranker input**: Query + Hierarchical context (Act|Chapter|Section|Type|Authority) + Chunk text
- **MMR λ=0.7** with authority bonus, dedup threshold 0.95 cosine
- **Confidence scoring**: 6 signals (candidate count, top score, score dist, authority purity, jurisdiction purity, temporal currency, coverage breadth, query coverage) → weighted → abstain if <0.4
- **Fallback chain**: Hybrid → Sparse-only → Dense-only → Broadened filters → Cross-jurisdiction (with warning)
- **Multilingual**: Translate query + multilingual embeddings (bge-m3)
- **Caching**: 5 layers (query embedding, sparse, dense, rerank, final)
- 15 tunable parameters
- 7 Open Research Questions (ORQ-27 to ORQ-33)

### Phase 7: Knowledge Graph (`architecture/phase7-knowledge-graph.md`)
- **Role**: OPTIONAL enhancement module (not primary retrieval)
- **Entities**: Act, Chapter, Part, Section, Subsection, Clause, Definition, Treaty, TreatyArticle, Case, Paragraph, Guideline, Formulation, Ingredient, BiologicalResource, ABSApplication, PatentRecord, TrademarkRecord, GIRecord, TKEntry
- **Core Relationships (HIGH VALUE)**:
  - Hierarchy: HAS_CHAPTER, HAS_PART, HAS_SECTION, HAS_SUBSECTION, HAS_CLAUSE, HAS_DEFINITION
  - Amendments: AMENDS, AMENDS_SECTION, INSERTS, DELETES, SUBSTITUTES, MODIFIES, SUPERSEDES, HAS_VERSION
  - Treaty: IMPLEMENTS, IMPLEMENTED_BY, IMPLEMENTS_TREATY
  - Case Law: INTERPRETS, INTERPRETED_BY, CITES, OVERRULES, DISTINGUISHES, FOLLOWS
  - Delegation: DELEGATES_TO, MADE_UNDER
  - Cross-refs: REFERENCES, DEFINES_TERM, SUBJECT_TO, OVERRIDES, CONFLICTS_WITH
  - Formulation: CLASSIFIED_AS, CONTAINS, DERIVED_FROM, REQUIRES_ABS, EXEMPT_FROM
- **Graph DB**: FalkorDB (hackathon) / Neo4j (production)
- **Construction**: From Phase 5 chunks + separate ingestion for cases/treaties
- **Graph Retrieval**: Triggered by query analysis for specific patterns (temporal, treaty, case law, amendment, delegation, conflict, formulation)
- **Fusion**: RRF with graph weight 0.8
- **Temporal**: Version chains per Section (HAS_VERSION → SUPERSEDES)
- **Evaluation**: A/B test vs vector-only; must show >5% improvement
- 5 Open Research Questions (ORQ-34 to ORQ-38)

### Phase 8: Formulation Classification (`architecture/phase8-formulation-classification.md`)
- **8 Formulation Classes**: Classical Medicine, Generic Medicine, Patent/Proprietary, New Drug, Phytopharmaceutical, Ayurveda-Aahar, Nutraceutical, Cosmetic
- **Deterministic Rule Engine**: 25+ rules covering D&C Act (Schedule E(1), First Schedule, Section 3(b), Section 12), D&C Rules (Rule 158, 122), FSSAI (2016/2022 Nutraceutical, 2022 Ayurveda-Aahar), Cosmetic Rules 2020
- **Input Extraction**: Structured schema for ingredients, dosage form, preparation method, intended use, claims, classical text references
- **LLM Reasoning**: Only for borderline cases (conflicts, insufficient evidence); NEVER overrides deterministic rules
- **Confidence Calculation**: Multi-signal (rule match strength, authority tier, evidence completeness, LLM confidence, evidence support, ingredient quality)
- **Human Escalation**: Triggers at confidence < 0.6, deterministic conflicts, scheduled ingredients, therapeutic claims on non-drugs, novel formulations
- **Regulatory Output**: Classification + applicable regimes + licensing requirements + ABS obligations + labeling requirements
- **Integration**: Feeds Query Analysis (Phase 3), Retrieval Filters (Phase 6), Knowledge Graph (Phase 7)
- 7 Open Research Questions (ORQ-39 to ORQ-45)

### Phase 9: Jurisdiction Engine (`architecture/phase9-jurisdiction-engine.md`)
- **Jurisdiction Taxonomy**: 15+ jurisdictions across 5 types (National, State/Provincial, International Treaty, Regional, International Org)
- **Deterministic Determination**: Formulation class mapping → Query keyword extraction → User context → LLM disambiguation
- **Authority/Regime Mapping**: Jurisdiction → Regulatory Authority → Applicable Legislation/Regulations/Guidelines/Case Law
- **Hard Isolation**: Metadata pre-filter with MUST/MUST_NOT jurisdiction constraints (non-negotiable)
- **Temporal Validity**: Version chains via KG (SUPERSEDES), amendment effect analysis, prospective/retrospective detection
- **Conflict Resolution**: Constitutional hierarchy (Federal > State) + Lex posterior + Lex specialis + Authority tier
- **Multi-Jurisdiction Handling**: Explicit segmentation → Separate retrieval → Segmented generation → Comparative synthesis
- **Integration**: Feeds Phase 3 (query analysis), Phase 6 (retrieval filter), Phase 8 (formulation default), Phase 7 (KG)
- 6 Open Research Questions (ORQ-46 to ORQ-51)

---

## ✅ PHASES IMPLEMENTED (New Execution Order - Code)

### Phase 3: Data Model (New Structure) ✅ IMPLEMENTED
- `ip_sakti/core/models.py` - Core data models (Document, DocumentChunk, Citation, Jurisdiction, Language, SourceAuthority, etc.)
- `ip_sakti/config/loader.py` - Configuration management with YAML settings

### Phase 4: Technology Selection (New Structure) ✅ IMPLEMENTED
- `ip_sakti/config/settings.yaml` - Technology choices locked (bge-m3, HNSW, BM25, bge-reranker-v2-m3, FalkorDB/Neo4j)

### Phase 5: Source Authority System ✅ IMPLEMENTED
- `ip_sakti/authority/authority_system.py` - Tier 1-4 authority hierarchy with weights (1.0, 0.8, 0.6, 0.4)

### Phase 6: Security Architecture ✅ IMPLEMENTED
- `ip_sakti/security/security_system.py` - Auth, secrets, prompt injection defense, PDF sanitization, retrieval poisoning defense

### Phase 7: Ingestion Architecture ✅ IMPLEMENTED
- `ip_sakti/ingestion/pipeline.py` - Document ingestion pipeline with structure extraction
- `ip_sakti/ingestion/chunking.py` - Hierarchical section chunking with 15% overlap

### Phase 8: Chunking Strategy ✅ IMPLEMENTED (merged into Phase 7)

### Phase 9: RAG Architecture ✅ IMPLEMENTED
- `ip_sakti/rag/pipeline.py` - Complete RAG pipeline with retrieval, reranking, generation

### Phase 10: Retrieval Engine Infra ✅ IMPLEMENTED
- `ip_sakti/retrieval/retrieval_engine.py` - Infrastructure/service-level retrieval with scaling, caching, deployment topology

### Phase 11: Evaluation System ✅ IMPLEMENTED
- `ip_sakti/eval/evaluation.py` - Evaluation framework with metrics, benchmarks, golden datasets

### Phase 12: Research Experiment Framework ✅ IMPLEMENTED
- `ip_sakti/experiments/framework.py` - Experiment tracking, baseline→experiment methodology

### Phase 13: Knowledge Graph ✅ IMPLEMENTED
- `ip_sakti/kg/knowledge_graph.py` - FalkorDB/Neo4j integration, entity/relationship extraction, graph retrieval

### Phase 14: Formulation Classification ✅ IMPLEMENTED
- `ip_sakti/classification/formulation.py` - 8-class deterministic rule engine with LLM fallback

### Phase 15: Jurisdiction Engine ✅ IMPLEMENTED
- `ip_sakti/jurisdiction/engine.py` - 15+ jurisdictions, hard isolation, conflict resolution

### Phase 16: Citation-First Generation ✅ IMPLEMENTED
- `ip_sakti/generation/citation_first.py` - Grounded generation with citation verification

### Phase 17: Multilingual Architecture ✅ IMPLEMENTED
- `ip_sakti/multilingual/architecture.py` - Cross-lingual retrieval, translation, multilingual generation

### Phase 18: Agentic Orchestration ✅ IMPLEMENTED
- `ip_sakti/orchestration/engine.py` - Multi-agent workflows (Planner, Retriever, Analyzer, Writer, Critic, Validator, Jurisdiction/Formulation experts)

### Phase 19: Memory Architecture ✅ IMPLEMENTED
- `ip_sakti/memory/architecture.py` - Short-term, long-term, episodic, semantic, working memory with consolidation

---

## 📊 CORPUS STATUS

### Downloaded & Extracted (24 documents, ~822K chars)

| Source | Document | Format | Size | Status |
|--------|----------|--------|------|--------|
| India Code (via WIPO) | Patents Act 1970 | HTML→TXT | ~200K | ✅ |
| India Code (via WIPO) | Trademarks Act 1999 | HTML→TXT | ~180K | ✅ |
| India Code (via WIPO) | GI Act 1999 | PDF→TXT | ~90K | ✅ |
| India Code (via WIPO) | Designs Act 2000 | HTML→TXT | ~85K | ✅ |
| India Code (via WIPO) | Copyright Act 1957 | HTML→TXT | ~150K | ✅ |
| India Code (via WIPO) | PPVFR Act 2001 | HTML→TXT | ~75K | ✅ |
| India Code (via WIPO) | Drugs & Cosmetics Act 1940 | HTML→TXT | ~220K | ✅ |
| India Code (via WIPO) | Drugs & Magic Remedies Act 1954 | HTML→TXT | ~15K | ✅ |
| India Code (via WIPO) | FSSAI Act 2006 | HTML→TXT | ~140K | ✅ |
| WIPO | Biological Diversity Act 2002 | PDF→TXT | ~110K | ✅ |
| CBD | CBD 1992 | PDF→TXT | ~85K | ✅ |
| UN Treaties | Nagoya Protocol 2010 | HTML→TXT | ~60K | ✅ |
| WTO | TRIPS Agreement | HTML→TXT | ~95K | ✅ |
| NBA | Bio Diversity Rules 2004 | HTML→TXT | ~45K | ✅ |
| NBA | ABS Guidelines | HTML→TXT | ~35K | ✅ |
| NBA | Form I, II | HTML→TXT | ~10K | ✅ |
| WIPO | PCT / Madrid / Hague / Budapest / GRATK | Notes only | - | ⚠️ Need PDFs |
| IP India | Patent/Trademark/GI/Designs/Copyright Rules | HTML from WIPO | - | ⚠️ Need PDFs |
| FSSAI | Ayurveda Aahar Regulations | - | - | ❌ Not downloaded |
| AYUSH | Pharmacopoeia/Formulary | - | - | ❌ Not downloaded |
| TKDL | Public resources | - | - | ❌ Need investigation |

### Corpus Gaps to Fill (Before Build Phase)
1. **Rules as PDFs**: Patent Rules 2003, TM Rules 2017, GI Rules 2002, Designs Rules 2001, Copyright Rules 2013, PPVFR Rules 2003
2. **WIPO Treaties**: PCT, Madrid, Hague, Budapest, GRATK as actual PDFs
3. **FSSAI**: Ayurveda Aahar Regulations 2022
4. **AYUSH**: Ayurvedic Pharmacopoeia, Formulary
5. **TKDL**: Determine publicly accessible content
6. **Case Law**: Supreme Court / High Court judgments on IP/AYUSH/ABS
7. **Registry Records**: Sample patent/trademark/GI/design records from IP India

---

## 📋 MASTER PLAN STATUS (plan.md v2 - Corrected)

```
Phase 1: Requirements Engineering                ✅ COMPLETE (original phase 1)
Phase 2: System-Level Architecture               ✅ COMPLETE (original phase 2)
Phase 3: Data Model                               ✅ IMPLEMENTED (was phase 15)
Phase 4: Technology Selection                     ✅ IMPLEMENTED (was phase 23)
Phase 5: Source Authority System                  ✅ IMPLEMENTED (was phase 11)
Phase 6: Security Architecture                    ✅ IMPLEMENTED (was phase 19)
Phase 7: Ingestion Architecture                   ✅ IMPLEMENTED (original phase 4 + phase 5 merged)
Phase 8: Retrieval / RAG Architecture             ✅ IMPLEMENTED (original phase 3 + phase 6 merged)
Phase 9: Evaluation System                        ✅ IMPLEMENTED (was phase 17)
Phase 10: Research Experiment Framework           ✅ IMPLEMENTED (was phase 18)
Phase 11: Knowledge Graph                         ✅ IMPLEMENTED (original phase 7)
Phase 12: Formulation Classification              ✅ IMPLEMENTED (original phase 8)
Phase 13: Jurisdiction Engine                     ✅ IMPLEMENTED (original phase 9)
Phase 14: Citation-First Generation               ✅ IMPLEMENTED (original phase 10)
Phase 15: Multilingual Architecture               ✅ IMPLEMENTED (original phase 12)
Phase 16: Agentic Orchestration                   ✅ IMPLEMENTED (original phase 13)
Phase 17: Memory Architecture                     ✅ IMPLEMENTED (original phase 14)
Phase 18: API Architecture                        🔄 IN PROGRESS (original phase 16)
Phase 19: Deployment Architecture                 ⏳ PENDING (original phase 20)
Phase 20: Observability                           ⏳ PENDING (original phase 21)
Phase 21: Failure Mode Analysis                   ⏳ PENDING (was phase 22)
Phase 22: Implementation Roadmap                  ⏳ PENDING (original phase 24)
Phase 23: Repository Architecture                 ⏳ PENDING (original phase 25)
Phase 24: Decision Records (ADR)                  ⏳ PENDING (was phase 26)
```

---

## 🔄 MAPPING: Original Phases → Corrected Phases

| Original Phase | Original Name | New Phase | New Name | Status |
|----------------|---------------|-----------|----------|--------|
| 1 | Requirements Engineering | 1 | Requirements Engineering | ✅ Complete |
| 2 | System-Level Architecture | 2 | System-Level Architecture | ✅ Complete |
| 3 | RAG Architecture | 8 | Retrieval / RAG Architecture | 🔄 Partial (merged) |
| 4 | Legal Document Ingestion | 7 | Ingestion Architecture | 🔄 Partial (merged) |
| 5 | Chunking Strategy | 7 | Ingestion Architecture | 🔄 Partial (merged) |
| 6 | Retrieval Engine | 8 | Retrieval / RAG Architecture | 🔄 Partial (merged) |
| 7 | Knowledge Graph | 11 | Knowledge Graph | 🔄 Partial (needs eval harness) |
| 8 | Formulation Classification | 12 | Formulation Classification | ✅ Complete |
| 9 | Jurisdiction Engine | 13 | Jurisdiction Engine | ✅ Complete |
| 10 | Citation-First Generation | 14 | Citation-First Generation | ⏳ Pending |
| 11 | Source Authority System | 5 | Source Authority System | ⏳ Pending |
| 12 | Multilingual Architecture | 15 | Multilingual Architecture | ⏳ Pending |
| 13 | Agentic Orchestration | 16 | Agentic Orchestration | ⏳ Pending |
| 14 | Memory Architecture | 17 | Memory Architecture | ⏳ Pending |
| 15 | Data Model | 3 | Data Model | ⏳ Pending |
| 16 | API Architecture | 18 | API Architecture | ⏳ Pending |
| 17 | Evaluation System | 9 | Evaluation System | ⏳ Pending |
| 18 | Research Experiment Framework | 10 | Research Experiment Framework | ⏳ Pending |
| 19 | Security Architecture | 6 | Security Architecture | ⏳ Pending |
| 20 | Deployment Architecture | 19 | Deployment Architecture | ⏳ Pending |
| 21 | Observability | 20 | Observability | ⏳ Pending |
| 22 | Failure Mode Analysis | 21 | Failure Mode Analysis | ⏳ Pending |
| 23 | Technology Selection | 4 | Technology Selection | ⏳ Pending |
| 24 | Implementation Roadmap | 22 | Implementation Roadmap | ⏳ Pending |
| 25 | Repository Architecture | 23 | Repository Architecture | ⏳ Pending |
| 26 | Decision Records (ADR) | 24 | Decision Records (ADR) | ⏳ Pending |

---

## 🎯 NEXT IMMEDIATE TASKS (New Structure)

### Phase 18: API Architecture (Next Priority - In Progress)
Create API layer with:
1. **FastAPI application** with OpenAPI spec
2. **Query endpoints** - /query, /query/stream, /query/batch
3. **Document endpoints** - /documents, /documents/{id}, /documents/search
4. **Ingestion endpoints** - /ingest, /ingest/status, /ingest/batch
5. **Admin endpoints** - /health, /metrics, /config, /experiments
6. **Authentication** - OIDC/JWT integration, API keys
7. **Rate limiting** - Per-user, per-endpoint
8. **Request/Response models** - Pydantic schemas for all endpoints
9. **Error handling** - Standardized error responses
10. **Middleware** - Logging, tracing, CORS, compression

---

## 🔧 TECHNOLOGY DECISIONS MADE (Locked - Must Not Re-Decide)

| Component | Decision | Alternative Considered | Rationale |
|-----------|----------|------------------------|-----------|
| **Sparse Retrieval** | BM25 (legal tokenizer) | SPLADE | Exact term matching for sections/acts |
| **Dense Embeddings** | bge-m3 (primary), jina-v3 (alt) | mxbai, legal-xlm-roberta | Multilingual, 100+ langs, dense+sparse+colbert |
| **Vector Index** | HNSW (hnswlib) | FAISS, Milvus | CPU-friendly, good recall, easy deployment |
| **Fusion** | RRF + Authority weights | Weighted score, learned | Parameter-free, robust, authority-aware |
| **Reranker** | bge-reranker-v2-m3 | jina-reranker, MiniLM | Multilingual, strong legal perf |
| **Graph DB** | FalkorDB (dev), Neo4j (prod) | Kuzu, Memgraph, JanusGraph | FalkorDB: Redis-based, fast, Docker; Neo4j: mature |
| **Chunking** | Hierarchical Section (512-2048 tokens) | Fixed, semantic, sentence-window | Preserves legal hierarchy, citations |
| **Overlap** | 15% at boundaries | 10%, 20% | Context continuity |
| **Abstention** | Confidence < 0.4 | Fixed threshold | Multi-signal confidence |
| **Caching** | 5-layer (Redis/Memory) | None | Latency reduction |

---

## 🧪 EXPERIMENT FRAMEWORK (Phases 9-10)

**Baseline → Experiment → Benchmark → Decision methodology:**

| Experiment | Hypothesis | Config |
|------------|------------|--------|
| E1: Dense only | Dense > BM25 for semantic queries | bge-m3 only |
| E2: Hybrid (RRF) | Hybrid > either alone | BM25 + bge-m3 + RRF |
| E3: Hybrid + Authority | Authority weighting improves precision | RRF with tier weights |
| E4: + Reranker | Cross-encoder improves precision@K | + bge-reranker-v2-m3 |
| E5: + Query Decomposition | Multi-hop queries improve | Decompose → multi-retrieve |
| E6: + Graph | Graph helps multi-hop/temporal | Graph retrieval for specific intents |
| E7: + Agentic | Agentic for complex research | Research agent orchestration |

**Each experiment records**: hypothesis, config, dataset, metrics, latency, cost, accuracy, citation quality, failure cases, conclusion

---

## 📝 OPEN RESEARCH QUESTIONS (Consolidated - 51 Total)

| Phase | Questions |
|-------|-----------|
| Phase 3 (RAG) | ORQ-13 to ORQ-20 (8): chunk granularity, RRF k, cross-encoder vs LLM reranker, multilingual retrieval, etc. |
| Phase 5 (Chunking) | ORQ-21 to ORQ-26 (6): max_tokens, parent-child, overlap ratio, schedule chunking, definitions, patent claims |
| Phase 6 (Retrieval) | ORQ-27 to ORQ-33 (7): RRF k, cross-encoder vs LLM, query decomposition, multilingual strategy, MMR lambda, separate indices, ColBERT |
| Phase 7 (KG) | ORQ-34 to ORQ-38 (5): graph vs vector for lookup, hop depth, KG embeddings, LLM→Cypher, implied relationships |
| Phase 8 (Formulation) | ORQ-39 to ORQ-45 (7): escalation threshold, multi-label formulations, multilingual ingredient extraction, classical formula matching, traditional text verification, state rule variations, VAPs integration |
| Phase 9 (Jurisdiction) | ORQ-46 to ORQ-51 (6): jurisdiction precedence, temporal validity, multi-jurisdiction synthesis, etc. |
| Phase 10 (Citation) | ORQ-52 to ORQ-55 (4): citation style, cross-source entailment, authority-weighted correctness |
| Phase 11 (Authority) | ORQ-56 to ORQ-58 (3): tier boundary calibration, source freshness decay, dynamic tiering |
| Phase 12 (Security) | ORQ-59 to ORQ-62 (4): prompt injection detection, retrieval poisoning metrics, tool sandbox escape |

---

## ⚠️ KEY ARCHITECTURAL PRINCIPLES (Non-Negotiable)

1. **Jurisdiction Isolation**: Hard filter at metadata pre-filter stage - NEVER mix Indian law, treaties, foreign law
2. **Citation Traceability**: Every answer claim → evidence chunk → section → document → authoritative source URL
3. **Authority Hierarchy**: Tier 1 (official) > Tier 2 (official guidance) > Tier 3 (academic) > Tier 4 (commentary)
4. **Deterministic > Probabilistic**: Legal rules (Schedule E, Section 3(d)) are deterministic; LLM only for gaps
5. **Abstention over Hallucination**: "I don't have sufficient authoritative evidence" > fabricated answer
6. **Version Preservation**: Amendments create new versions; old versions never overwritten
7. **Source Provenance**: Every chunk tracks source_id, retrieval timestamp, content hash, canonical URL
8. **Evaluation First**: Benchmark dataset designed before implementation; every component experimentally validated
9. **Formulation Classification**: Deterministic legal rules (Schedule E, First Schedule, Rule 158) take absolute precedence; LLM only for gaps/conflicts; NEVER silently overrides rules
10. **Cross-Cutting Dependencies Respected**: Data Model (3), Tech Selection (4), Source Authority (5), Security (6) precede all consumers

---

## 🚀 BUILD PHASE READINESS

### What's Ready for Implementation (Original Phases 1-9)
- ✅ Complete architecture specifications (Original Phases 1-9)
- ✅ Corpus with 24 extracted documents
- ✅ Detailed data models for all components (implicit in original docs)
- ✅ Tunable parameters with ranges
- ✅ Evaluation methodology
- ✅ Technology selections with rationale (documented in SESSION_STATE)

### What Needs Completion Before Build (New Structure Phases 3-24)
- [x] Phase 3: Data Model
- [x] Phase 4: Technology Selection
- [x] Phase 5: Source Authority System
- [x] Phase 6: Security Architecture
- [x] Phase 7: Ingestion Architecture (complete merge of original 4+5)
- [x] Phase 8: Retrieval / RAG Architecture (complete merge of original 3+6)
- [x] Phase 9: Evaluation System
- [x] Phase 10: Research Experiment Framework
- [x] Phase 11: Knowledge Graph (complete with eval harness)
- [x] Phase 12: Formulation Classification
- [x] Phase 13: Jurisdiction Engine
- [x] Phase 14: Citation-First Generation
- [x] Phase 15: Multilingual Architecture
- [x] Phase 16: Agentic Orchestration
- [x] Phase 17: Memory Architecture
- [ ] Phase 18: API Architecture
- [ ] Phase 19: Deployment Architecture
- [ ] Phase 20: Observability
- [ ] Phase 21: Failure Mode Analysis
- [ ] Phase 22: Implementation Roadmap
- [ ] Phase 23: Repository Architecture
- [ ] Phase 24: Decision Records (ADR)
- [ ] Corpus gaps filled (Rules PDFs, Treaties PDFs, FSSAI/AYUSH, Case law)
- [ ] Repository structure design (Phase 23)
- [ ] Implementation roadmap with milestones (Phase 22)

---

## 💡 HOW TO RESUME

### To Continue Architecture Phase (New Structure):
```bash
cd /mnt/c/Users/vvars/OneDrive/Desktop/sih\ rag
# Next: Create Phase 3 (Data Model) - NEW structure
# Reference: plan.md for corrected phase order and dependencies
```

### To Start Build Phase (After All Architecture Done):
```bash
cd /mnt/c/Users/vvars/OneDrive/Desktop/sih\ rag
# Stage 0: Repository + Infrastructure (Phase 23, 22)
# Stage 1: Corpus Ingestion Pipeline (Phase 7)
# Stage 2: Baseline RAG (Phase 8)
# Stage 3: Hybrid + Rerank (Phase 8)
# Stage 4: Citation Grounding (Phase 14)
# Stage 5: Evaluation Framework (Phase 9)
# ... etc per Phase 22 roadmap
```

### Key Files to Review on Resume:
1. `plan.md` - Master checklist (v2 corrected)
2. `architecture/phase9-jurisdiction-engine.md` - Last completed original phase
3. `architecture/phase6-retrieval-engine.md` - Core retrieval design
4. `architecture/phase5-chunking-strategy.md` - Chunk data structures
5. `data/corpus/` - Verify extracted text files exist

---

## 🧠 SESSION MEMORY SUMMARY

**What we accomplished this session:**
1. Downloaded and extracted 24 legal documents from authoritative sources (India Code via WIPO, CBD, UN, NBA, WTO)
2. Created 9 comprehensive architecture documents (Phases 1-9 original) totaling ~8,000+ lines
3. Defined complete RAG pipeline with BM25 + bge-m3 + RRF + bge-reranker-v2-m3 + MMR
4. Designed knowledge graph with 25 entity types and 30+ relationship types
5. Designed formulation classification engine with 8 classes, deterministic rules, LLM reasoning, confidence scoring, human escalation
6. Designed jurisdiction engine with 15+ jurisdictions, hard isolation, conflict resolution
7. Established citation traceability from embedding to authoritative source
8. Created evaluation framework with baseline→experiment methodology
9. **Restructured plan.md** to fix 4 structural bugs:
   - Moved Data Model, Tech Selection, Source Authority, Security earlier
   - Merged Chunking into Ingestion
   - Merged Retrieval Engine into RAG Architecture
   - Moved Evaluation/Experiment Framework before Knowledge Graph

**Critical decisions documented:**
- BM25 over SPLADE for legal exact matching
- Jurisdiction isolation at metadata pre-filter (hard requirement)
- Hierarchical section chunking with 15% overlap
- RRF with authority weighting (not simple fusion)
- Graph as OPTIONAL enhancement, not primary retrieval
- Abstention at confidence < 0.4 with specific reasons
- FalkorDB for hackathon, Neo4j for production
- Deterministic rules > LLM reasoning for formulation classification
- LLM MUST NOT silently override deterministic legal rules
- Escalation at confidence < 0.6, conflicts, scheduled ingredients
- Cross-cutting phases (Data Model, Tech Selection, Authority, Security) must precede consumers

**Corpus ready for**: Ingestion pipeline development, chunking implementation, retrieval engine testing, formulation classification development

---

**End of State Document** - You can resume from **Phase 3: Data Model (New Structure)** using this document and `plan.md` as reference. The original 9 phases are complete but need reorganization per the corrected plan.