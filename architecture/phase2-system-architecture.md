# Phase 2: System-Level Architecture
## IP-SAKTI Sahayak - Complete System Architecture Specification

**Status:** COMPLETE  
**Version:** 1.0  
**Date:** 2026-09-02

---

## 1. Executive Architecture Overview

### 1.1 High-Level System Goals

IP-SAKTI Sahayak is a **jurisdiction-aware, source-cited, multilingual RAG system** for Indian and international Intellectual Property, Traditional Knowledge, Ayurveda, Biodiversity, and Access & Benefit Sharing legal regimes.

**Core Principles:**
- **Jurisdiction Isolation**: Never mix laws from different jurisdictions
- **Citation-First Generation**: Every claim traceable to authoritative evidence
- **Authority-Weighted Retrieval**: Tier 1 sources preferred for legal claims
- **Safe Abstention**: Explicit decline when evidence insufficient
- **Deterministic + AI Hybrid**: Rules for classification, LLM for reasoning
- **Auditability**: Full traceability from answer → claim → evidence → source

### 1.2 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL ACTORS                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   End User  │  │  Legal      │  │   Admin     │  │   Sources   │        │
│  │  (Personas) │  │  Expert     │  │  (Ops)      │  │  (Ingest)   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼───────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Authentication │ Rate Limiting │ Request Routing │ API Versioning │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CORE QUERY PIPELINE                                 │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  QUERY       │  │  JURISDICTION│  │  INTENT &    │  │  FORMULATION │   │
│  │  UNDERSTANDING│  │  ENGINE      │  │  CLASSIFIER  │  │  CLASSIFIER  │   │
│  │              │  │              │  │              │  │              │   │
│  │ • Language   │  │ • Detect/    │  │ • 10 query   │  │ • Ingredients│   │
│  │   Detect     │  │   Select     │  │   categories │  │ • Classical  │   │
│  │ • Normalize  │  │ • Authority  │  │ • Intent     │  │   ref check  │   │
│  │ • Rewrite    │  │   mapping    │  │   labels     │  │ • Rule engine│   │
│  │ • Decompose  │  │ • Temporal   │  │ • Confidence │  │ • LLM reason │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│         └─────────────────┼─────────────────┼─────────────────┘           │
│                           ▼                 ▼                             │
│                    ┌────────────────────────────────┐                     │
│                    │       QUERY PLANNER            │                     │
│                    │  • Multi-hop plan              │                     │
│                    │  • Retrieval strategy per hop  │                     │
│                    │  • Jurisdiction filters        │                     │
│                    │  • Authority tier filters      │                     │
│                    └──────────────┬─────────────────┘                     │
│                                   │                                     │
│                                   ▼                                     │
│                    ┌────────────────────────────────┐                     │
│                    │     RETRIEVAL ORCHESTRATOR     │                     │
│                    │                                │                     │
│                    │  ┌──────────┐ ┌──────────┐    │                     │
│                    │  │ SPARSE   │ │ DENSE    │    │                     │
│                    │  │ (BM25/   │ │ (Vector  │    │                     │
│                    │  │ SPLADE)  │ │ + Hybrid)│    │                     │
│                    │  └────┬─────┘ └────┬─────┘    │                     │
│                    │       │            │           │                     │
│                    │       └────┬───────┘           │                     │
│                    │            ▼                   │                     │
│                    │  ┌──────────────────┐          │                     │
│                    │  │ FUSION (RRF/     │          │                     │
│                    │  │  Weighted)       │          │                     │
│                    │  └────────┬─────────┘          │                     │
│                    │           ▼                    │                     │
│                    │  ┌──────────────────┐          │                     │
│                    │  │ RERANKER         │          │                     │
│                    │  │ (Cross-encoder)  │          │                     │
│                    │  └────────┬─────────┘          │                     │
│                    │           ▼                    │                     │
│                    │  ┌──────────────────┐          │                     │
│                    │  │ EVIDENCE         │          │                     │
│                    │  │ SELECTOR         │          │                     │
│                    │  │ (Diversity,      │          │                     │
│                    │  │  Authority,      │          │                     │
│                    │  │  Relevance)      │          │                     │
│                    │  └────────┬─────────┘          │                     │
│                    └───────────┼────────────────────┘                     │
│                                │                                        │
│                                ▼                                        │
│                    ┌────────────────────────────────┐                     │
│                    │     CONTEXT BUILDER            │                     │
│                    │  • Parent-child expansion      │                     │
│                    │  • Hierarchical context        │                     │
│                    │  • Citation mapping            │                     │
│                    │  • Token budget management     │                     │
│                    └──────────────┬─────────────────┘                     │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌────────────────────────────────┐                     │
│                    │     LLM REASONING              │                     │
│                    │  • Evidence-grounded generation│                     │
│                    │  • Claim extraction            │                     │
│                    │  • Citation insertion          │                     │
│                    │  • Jurisdiction tagging        │                     │
│                    └──────────────┬─────────────────┘                     │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌────────────────────────────────┐                     │
│                    │     VERIFICATION LAYER         │                     │
│                    │  • Citation verification       │                     │
│                    │  • Groundedness check          │                     │
│                    │  • Claim-evidence entailment   │                     │
│                    │  • Jurisdiction consistency    │                     │
│                    │  • Hallucination detection     │                     │
│                    │  • Authority validation        │                     │
│                    └──────────────┬─────────────────┘                     │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌────────────────────────────────┐                     │
│                    │     FINAL ANSWER               │                     │
│                    │  • Structured response         │                     │
│                    │  • Citations with authority    │                     │
│                    │  • Confidence scores           │                     │
│                    │  • Abstention if needed        │                     │
│                    │  • Escalation triggers         │                     │
│                    └────────────────────────────────┘                     │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA & KNOWLEDGE LAYER                              │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  VECTOR INDEX   │  │  LEXICAL INDEX  │  │  KNOWLEDGE      │            │
│  │  (Dense +       │  │  (BM25/SPLADE)  │  │  GRAPH          │            │
│  │  Multilingual)  │  │                 │  │  (Entities +    │            │
│  │                 │  │                 │  │  Relations)     │            │
│  │  - Chunks       │  │  - Full text    │  │                 │            │
│  │  - Embeddings   │  │  - Sections     │  │  - Law, Section,│            │
│  │  - Metadata     │  │  - Metadata     │  │    Clause, Treaty│           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  DOCUMENT STORE │  │  METADATA DB    │  │  SOURCE REGISTRY│            │
│  │  (PostgreSQL +  │  │  (PostgreSQL)   │  │  (Versioned,    │            │
│  │  Object Storage)│  │                 │  │  Authority-tiered)│          │
│  │                 │  │  - Chunks       │  │                 │            │
│  │  - Original PDF │  │  - Embeddings   │  │  - Source info  │            │
│  │  - Extracted    │  │  - Entities     │  │  - Version hist │            │
│  │    text         │  │  - Relations    │  │  - Change log   │            │
│  │  - Versions     │  │  - Queries      │  │  - Access level │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INGESTION & INDEXING PIPELINE                         │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  ACQUISITION │  │  PARSING &   │  │  CHUNKING &  │  │  INDEXING &  │   │
│  │  (Scheduled, │  │  STRUCTURE   │  │  METADATA    │  │  VALIDATION  │   │
│  │  Webhook,    │  │  EXTRACTION  │  │  GENERATION  │  │              │   │
│  │  Manual)     │  │              │  │              │  │  • Vector    │   │
│  │              │  │  • OCR       │  │  • Legal-    │  │    upsert    │   │
│  │  • HTTP/     │  │  • Layout    │  │    section   │  │  • Lexical   │   │
│  │    FTP       │  │  • Hierarchy │  │  • Semantic  │  │    upsert    │   │
│  │  • API       │  │  • Tables    │  │  • Metadata  │  │  • Graph     │   │
│  │  • Browser   │  │  • Footnotes │  │    enrich    │  │    upsert    │   │
│  │    (PW)      │  │  • Amendments│  │  • Dedupe    │  │  • Validate  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Component Catalog

| Component | Type | Responsibility | Interface | Scaling |
|-----------|------|----------------|-----------|---------|
| **API Gateway** | Service | Auth, routing, rate limit, versioning | REST + WebSocket | Horizontal |
| **Query Understanding** | Service | Language detect, normalize, rewrite, decompose | gRPC | Horizontal |
| **Jurisdiction Engine** | Service | Detect/select jurisdiction, authority mapping | gRPC | Horizontal (stateless) |
| **Intent Classifier** | Service | 10-category classification + confidence | gRPC | Horizontal (batched) |
| **Formulation Classifier** | Service | Rule engine + LLM classification | gRPC | Horizontal |
| **Query Planner** | Service | Multi-hop retrieval plan generation | gRPC | Single-leader |
| **Retrieval Orchestrator** | Service | Coordinate sparse/dense/graph retrieval | gRPC | Horizontal |
| **Sparse Retriever** | Service | BM25/SPLADE search | gRPC | Horizontal (sharded) |
| **Dense Retriever** | Service | Vector similarity search | gRPC | Horizontal (sharded) |
| **Graph Retriever** | Service | Graph traversal + vector hybrid | gRPC | Horizontal |
| **Reranker** | Service | Cross-encoder scoring | gRPC | GPU-horizontal |
| **Evidence Selector** | Service | Diversity, authority, relevance filtering | gRPC | Horizontal |
| **Context Builder** | Service | Parent-child, hierarchical context, citations | gRPC | Horizontal |
| **LLM Reasoning** | Service | Evidence-grounded generation | gRPC | GPU-horizontal |
| **Verification Layer** | Service | Citation check, groundedness, entailment | gRPC | Horizontal |
| **Answer Formatter** | Service | Structured output, citations, confidence | gRPC | Horizontal |
| **Ingestion Pipeline** | Workers | Acquisition → Parse → Chunk → Index | Async queue | Horizontal workers |
| **Vector Index** | Infra | Dense vector storage + search | gRPC/REST | Sharded + replicas |
| **Lexical Index** | Infra | BM25/SPLADE storage + search | gRPC/REST | Sharded + replicas |
| **Graph DB** | Infra | Knowledge graph storage + traversal | Bolt/HTTP | Clustered |
| **Document Store** | Infra | PostgreSQL + Object storage | SQL/S3 | Primary + replicas |
| **Metadata DB** | Infra | Chunks, embeddings, entities, queries | SQL | Primary + replicas |

---

## 3. Data Flow Design

### 3.1 Query Flow (End-to-End)

```
User Query (text + optional params)
         │
         ▼
┌─────────────────────────────────────┐
│ API Gateway                         │
│ - Validate auth                     │
│ - Rate limit check                  │
│ - Extract: language_hint,           │
│   jurisdiction_hint, user_id        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Query Understanding Service         │
│ Input: raw_query, hints             │
│ Output: QueryUnderstanding          │
│   - normalized_query (en)           │
│   - original_query                  │
│   - detected_language               │
│   - rewritten_queries[]             │
│   - decomposed_subqueries[]         │
│   - query_type                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Jurisdiction Engine                 │
│ Input: normalized_query, hints      │
│ Output: JurisdictionContext         │
│   - primary_jurisdiction            │
│   - secondary_jurisdictions[]       │
│   - applicable_authorities[]        │
│   - temporal_scope                  │
│   - confidence                      │
│   - detection_signals               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Intent Classifier                   │
│ Input: normalized_query, jurisdiction│
│ Output: IntentClassification        │
│   - category (QC-01..QC-10)         │
│   - confidence                      │
│   - sub_intents[]                   │
│   - required_evidence_types[]       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Formulation Classifier (conditional)│
│ Input: query, ingredients, context  │
│ Output: FormulationClassification   │
│   - category (classical/proprietary/│
│     phytopharma/ayurveda-aahar/etc) │
│   - confidence                      │
│   - rule_trace                      │
│   - llm_reasoning                   │
│   - escalation_required             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Query Planner                       │
│ Input: all above contexts           │
│ Output: RetrievalPlan               │
│   - hops[]                          │
│     - subquery                      │
│     - retrieval_strategy            │
│     - jurisdiction_filter           │
│     - authority_filter              │
│     - source_type_filter            │
│     - top_k                         │
│   - fusion_strategy                 │
│   - rerank_config                   │
│   - evidence_selection_config       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Retrieval Orchestrator              │
│ Input: RetrievalPlan                │
│ For each hop (parallel):            │
│   - Execute Sparse Retrieval        │
│   - Execute Dense Retrieval         │
│   - Execute Graph Retrieval (opt)   │
│   - Apply Metadata Filters          │
│   - Fuse Results (RRF)              │
│ Output: CandidateEvidencePool       │
│   - candidates[] with scores        │
│   - retrieval_metadata              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Reranker                            │
│ Input: CandidateEvidencePool        │
│ Output: RerankedEvidence            │
│   - top_k reranked with             │
│     cross-encoder scores            │
│   - score breakdown                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Evidence Selector                   │
│ Input: RerankedEvidence             │
│ Output: SelectedEvidence            │
│   - evidence[] (diverse, auth, rel) │
│   - selection_reasoning             │
│   - coverage_analysis               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Context Builder                     │
│ Input: SelectedEvidence             │
│ Output: LLMContext                  │
│   - context_chunks[] with           │
│     citation_locators               │
│   - parent_chunks for hierarchy     │
│   - token_count                     │
│   - citation_map (claim_id→evidence)│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ LLM Reasoning Service               │
│ Input: LLMContext, original_query,  │
│        jurisdiction, language       │
│ Output: RawAnswer                   │
│   - answer_text                     │
│   - claims[] with evidence_refs     │
│   - citations[]                     │
│   - confidence_per_claim            │
│   - jurisdiction_tags per claim     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Verification Layer                  │
│ Input: RawAnswer, SelectedEvidence  │
│ Output: VerifiedAnswer              │
│   - verified_claims[]               │
│   - failed_claims[]                 │
│   - citation_verification_results   │
│   - groundedness_score              │
│   - hallucination_flags             │
│   - jurisdiction_conflicts          │
│   - authority_warnings              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Answer Formatter                    │
│ Input: VerifiedAnswer               │
│ Output: FinalResponse               │
│   - answer (in query language)      │
│   - citations[] (full CR schema)    │
│   - confidence (overall)            │
│   - abstention (bool + reason)      │
│   - escalation (bool + reason)      │
│   - trace_id                        │
└──────────────┬──────────────────────┘
               │
               ▼
        Audit Logger (async)
        Returns FinalResponse
```

### 3.2 Ingestion Flow

```
Source Trigger (scheduled/webhook/manual/API)
         │
         ▼
┌─────────────────────────────────────┐
│ Acquisition Worker                  │
│ - Fetch document (HTTP/FTP/Browser) │
│ - Validate content hash             │
│ - Check robots.txt / ToS            │
│ - Store raw in Object Storage       │
│ - Emit DocumentAcquired event       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Parsing Worker                      │
│ - Detect format (PDF/HTML/DOCX)     │
│ - OCR if scanned (Tesseract)        │
│ - Layout analysis (pdfplumber)      │
│ - Extract hierarchy:                │
│   Act → Chapter → Part → Section →  │
│   Subsection → Clause → Subclause   │
│ - Extract tables, footnotes,        │
│   schedules, annexures              │
│ - Emit DocumentParsed event         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Structure Extraction Worker         │
│ - Normalize section numbers         │
│ - Resolve cross-references          │
│ - Extract definitions               │
│ - Identify amendment markers        │
│ - Determine effective dates         │
│ - Detect superseded versions        │
│ - Assign source metadata:           │
│   source_id, authority_tier,        │
│   jurisdiction, doc_type,           │
│   version, publication_date,        │
│   canonical_url, content_hash       │
│ - Emit StructureExtracted event     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Chunking Worker                     │
│ - Legal-section chunking (primary)  │
│ - Parent-child hierarchy            │
│ - Sentence-window overlap           │
│ - Generate chunk metadata:          │
│   chunk_id, parent_chunk_id,        │
│   section_path, hierarchy_level,    │
│   token_count, language             │
│ - Emit ChunksGenerated event        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Embedding Worker                    │
│ - Generate dense embeddings         │
│   (multilingual model)              │
│ - Generate sparse vectors (SPLADE)  │
│ - Emit EmbeddingsGenerated event    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Indexing Worker                     │
│ - Upsert to Vector Index            │
│ - Upsert to Lexical Index           │
│ - Upsert to Graph DB (entities)     │
│ - Upsert to Document Store          │
│ - Upsert to Metadata DB             │
│ - Validate index consistency        │
│ - Emit DocumentIndexed event        │
└──────────────┬──────────────────────┘
               │
               ▼
        Versioning & Change Detection (async)
        - Compare with previous version
        - Generate diff
        - Flag affected citations
        - Update source registry
```

---

## 4. Query Flow Design

### 4.1 Query Understanding Component

**Purpose:** Transform raw user query into structured, normalized, decomposed queries optimized for retrieval.

**Inputs:**
- `raw_query`: string (user's natural language)
- `language_hint`: optional ISO code
- `jurisdiction_hint`: optional jurisdiction ID
- `user_context`: optional (preferences, history)

**Outputs:**
```python
QueryUnderstanding:
  original_query: str
  normalized_query: str           # English, canonical form
  detected_language: str          # ISO 639-1
  rewritten_queries: List[str]    # Query expansion variants
  decomposed_subqueries: List[SubQuery]
  query_type: QueryType           # SIMPLE | COMPLEX | MULTI_HOP
  legal_terms_preserved: List[str]  # Terms NOT translated
```

**Mechanism:**
1. **Language Detection**: fastText/CLD3 on raw_query (confidence > 0.9)
2. **Legal Term Normalization**: Preserve terms of art using terminology dictionary
   - "Section 3(d)" → NOT translated
   - "prior art" → NOT translated  
   - "inventive step" → NOT translated
3. **Query Rewriting** (for retrieval):
   - Synonym expansion (legal synonyms dictionary)
   - Acronym expansion (PCT, D&C, ABS, etc.)
   - Temporal normalization ("latest amendment" → effective date)
4. **Query Decomposition** (for complex queries):
   - LLM-based decomposition into atomic sub-queries
   - Each sub-query tagged with required evidence type
   - Dependency graph between sub-queries

**Data Structures:**
```python
SubQuery:
  id: str
  text: str
  evidence_types: List[SourceType]  # LEGISLATION, RULE, CASE_LAW, etc.
  jurisdiction: Jurisdiction
  depends_on: List[str]  # subquery IDs
  retrieval_strategy: RetrievalStrategy
```

**Dependencies:** Terminology dictionary, Legal synonym map, LLM (for decomposition)

**Failure Modes:**
- Language detection low confidence → Default to English + flag
- Decomposition fails → Treat as single query
- Legal term preservation fails → Log warning, proceed

**Fallback:** Skip rewriting/decomposition; use raw query

**Evaluation:** 
- Language detection accuracy on test set
- Query rewriting recall improvement (A/B)
- Decomposition correctness (human eval)

---

### 4.2 Jurisdiction Engine

**Purpose:** Determine applicable jurisdiction(s), authority, legal regime, and temporal validity for a query.

**Inputs:**
- `normalized_query`: string
- `user_jurisdiction_hint`: optional
- `query_entities`: extracted legal references (sections, acts, treaties)

**Outputs:**
```python
JurisdictionContext:
  primary: Jurisdiction          # e.g., "India::Central"
  secondary: List[Jurisdiction]  # e.g., ["International::Nagoya"]
  applicable_authorities: List[Authority]  # e.g., ["NBA", "IP India", "WIPO"]
  temporal_scope: TemporalScope  # effective date range
  confidence: float
  detection_signals: Dict[str, float]
  conflicts: List[JurisdictionConflict]
```

**Mechanism:**
1. **Explicit Override**: User selection = 1.0 weight
2. **Entity-Based**: Extracted legal citations → their jurisdiction (0.9)
3. **Keyword Signals**: "Indian patent", "US trademark" → jurisdiction (0.8)
4. **Default**: User profile/location (0.3)
5. **Conflict Detection**: Multiple jurisdictions with high confidence → flag
6. **Authority Mapping**: Jurisdiction → Authoritative sources (Tier 1)

**Jurisdiction Taxonomy:**
```
Jurisdiction:
  id: str                    # "India::Central", "International::Nagoya"
  type: NATIONAL | INTERNATIONAL_TREATY | REGIONAL | FOREIGN_NATIONAL
  parent: Optional[str]      # For states: "India::Central"
  authorities: List[str]     # ["Parliament", "NBA", "IP India"]
  source_repositories: List[str]  # Corpus paths
```

**Temporal Validity:**
- Each document version has `effective_date` and `superseded_date`
- Query temporal scope defaults to "current" (now)
- Historical queries explicitly request date range

**Dependencies:** Source registry, Legal citation parser, User profile

**Failure Modes:**
- Multiple jurisdictions detected → Multi-jurisdiction answer (separate sections)
- No jurisdiction detected → Default to India::Central + low confidence flag
- Conflict between regimes → Present both with analysis

**Fallback:** Default to India::Central with explicit disclaimer

**Evaluation:**
- Jurisdiction detection accuracy on labeled queries
- Multi-jurisdiction handling correctness
- Authority mapping completeness

---

### 4.3 Intent & Query Classifier

**Purpose:** Classify query into one of 10 categories to determine retrieval strategy.

**Inputs:**
- `normalized_query`: string
- `jurisdiction_context`: JurisdictionContext
- `formulation_classification`: optional (if available)

**Outputs:**
```python
IntentClassification:
  category: QueryCategory  # QC-01..QC-10
  confidence: float
  sub_intents: List[SubIntent]
  required_evidence_types: List[SourceType]
  retrieval_strategy_hint: RetrievalStrategy
  is_factual: bool
  is_procedural: bool
  is_comparative: bool
```

**Categories (from Phase 1):**
| Code | Category | Strategy |
|------|----------|----------|
| QC-01 | Provision Lookup | Direct section lookup + vector |
| QC-02 | Procedural | Structured retrieval + guidelines |
| QC-03 | Classification | Rule engine + LLM reasoning |
| QC-04 | Compliance | Rule-based + evidence retrieval |
| QC-05 | Comparative | Multi-jurisdiction retrieval |
| QC-06 | Prior-Art | Specialized DB (TKDL, InPASS) |
| QC-07 | Case Law | Case law DB + citation network |
| QC-08 | Regulatory Pathway | Classification + provision lookup |
| QC-09 | Treaty Obligation | Treaty text + COP decisions + national law |
| QC-10 | Fact Verification | Authority-weighted retrieval |

**Mechanism:**
- Fine-tuned classifier (BERT/DeBERTa) on labeled queries
- Multi-label for queries spanning categories
- Confidence threshold: 0.7 for auto, <0.7 → clarifying question

**Dependencies:** Training dataset, Legal term embeddings

**Failure Modes:**
- Low confidence → Clarifying question to user
- Misclassification → Retrieval strategy mismatch (logged for retraining)

**Fallback:** Default to QC-01 (Provision Lookup) with broad retrieval

---

### 4.4 Formulation Classifier

**Purpose:** Deterministic + AI-assisted classification of Ayurveda/pharma formulations.

**Inputs:**
- `ingredients`: List[str]
- `dosage_form`: str
- `classical_reference`: optional str
- `preparation_method`: optional str
- `intended_use`: str
- `claims`: List[str]
- `manufacturing_method`: optional str

**Outputs:**
```python
FormulationClassification:
  category: FormulationCategory  # CLASSICAL | GENERIC | PROPRIETARY | 
                                   # NEW_DRUG | PHYTOPHARMACEUTICAL |
                                   # AYURVEDA_AAHAR | NUTRACEUTICAL |
                                   # COSMETIC | UNCERTAIN
  confidence: float
  rule_trace: List[RuleTrace]    # Deterministic rule matches
  llm_reasoning: str             # LLM explanation
  conflicting_evidence: List[Conflict]
  escalation_required: bool
  applicable_regulations: List[RegulationRef]
```

**Deterministic Rules (Priority Order):**
1. **Classical Medicine**: Classical text reference (Sahasrayogam, AFI, etc.) + traditional prep → Schedule E(1) D&C Rules Rule 158-B
2. **ASU Drug**: Therapeutic claims + not classical → D&C Act Section 3(a)
3. **Ayurveda-Aahar**: Food claims + FSSAI Ayurveda-Aahar Regulations 2022 schedule
4. **Phytopharmaceutical**: Standardized extract + clinical data → D&C Rules
5. **Proprietary/Non-classical**: New combination, no classical reference
6. **Cosmetic**: Topical, non-therapeutic claims
7. **Nutraceutical**: Food supplement claims

**LLM Reasoning:** Used ONLY when rules inconclusive or conflicting evidence. Never overrides deterministic legal rules.

**Dependencies:** Classical text database, VAPs classification, D&C Rules, FSSAI regulations

**Failure Modes:**
- Rule engine + LLM disagree → Flag for human escalation
- Insufficient information → UNCERTAIN + escalation
- Borderline claims → Conservative classification + disclaimer

**Fallback:** UNCERTAIN with escalation_required = true

---

### 4.5 Query Planner

**Purpose:** Generate optimal multi-hop retrieval plan based on query analysis.

**Inputs:**
- `query_understanding`: QueryUnderstanding
- `jurisdiction_context`: JurisdictionContext
- `intent_classification`: IntentClassification
- `formulation_classification`: optional

**Outputs:**
```python
RetrievalPlan:
  hops: List[RetrievalHop]
  fusion_strategy: FusionStrategy  # RRF | WEIGHTED | ADAPTIVE
  rerank_config: RerankConfig
  evidence_selection_config: EvidenceSelectionConfig
  max_total_tokens: int
  timeout_ms: int
```

```python
RetrievalHop:
  id: str
  subquery: str
  strategy: RetrievalStrategy  # SPARSE | DENSE | HYBRID | GRAPH | SPECIALIZED
  jurisdiction_filter: Jurisdiction
  authority_filter: List[AuthorityTier]  # [1, 2] for legal claims
  source_type_filter: List[SourceType]   # [LEGISLATION, RULE]
  top_k: int
  metadata_filters: Dict[str, Any]
```

**Strategies by Query Category:**
| Category | Strategy |
|----------|----------|
| QC-01 Provision Lookup | HYBRID (exact section + semantic) |
| QC-02 Procedural | HYBRID + GUIDELINE source_type |
| QC-03 Classification | RULE_ENGINE (deterministic) + HYBRID |
| QC-04 Compliance | HYBRID + REGULATION source_type |
| QC-05 Comparative | MULTI_JURISDICTION (parallel hops) |
| QC-06 Prior-Art | SPECIALIZED (TKDL/InPASS APIs) |
| QC-07 Case Law | GRAPH (citation network) + LEXICAL |
| QC-08 Regulatory Pathway | CLASSIFICATION + HYBRID |
| QC-09 Treaty Obligation | TREATY source_type + COP decisions |
| QC-10 Fact Verification | AUTHORITY_WEIGHTED (Tier 1 only) |

**Dependencies:** Retrieval strategy configs, Performance benchmarks

**Failure Modes:**
- Plan too complex → Simplify to single-hop HYBRID
- Timeout → Return partial results with warning

**Fallback:** Single-hop HYBRID with default top_k

---

## 5. Retrieval Orchestration

### 5.1 Retrieval Orchestrator

**Purpose:** Execute retrieval plan, coordinate multiple retrieval methods, fuse results.

**Inputs:** `RetrievalPlan`

**Outputs:** `CandidateEvidencePool`

**Mechanism:**
1. **Parallel Hop Execution**: Each hop runs independently
2. **Per-Hop Retrieval**:
   - Sparse: BM25/SPLADE on lexical index
   - Dense: Vector similarity on vector index
   - Graph: Entity-based traversal (optional)
   - Specialized: Direct API calls (InPASS, TMR, etc.)
3. **Metadata Filtering** (applied at index level):
   - Jurisdiction = primary/secondary
   - Authority tier ∈ filter
   - Source type ∈ filter
   - Language = query language or multilingual
   - Effective date ≤ query temporal scope
4. **Fusion**: Reciprocal Rank Fusion (RRF) with k=60
   - Weighted by authority tier (Tier 1: 1.0, Tier 2: 0.8, ...)
5. **Deduplication**: By content hash + section path
6. **Output**: Top-N candidates per hop with fused scores

**Data Structures:**
```python
CandidateEvidence:
  chunk_id: str
  document_id: str
  text: str
  section_path: str           # "Act > Chapter > Section > Clause"
  source_metadata: SourceMetadata
  sparse_score: float
  dense_score: float
  fused_score: float
  retrieval_hop: str
```

**Dependencies:** Vector index, Lexical index, Graph DB, Metadata DB

**Failure Modes:**
- Vector index down → Lexical only (degraded mode)
- Lexical index down → Vector only (degraded mode)
- Both down → Cached results + stale warning

**Fallback:** BM25-only on local SQLite FTS5 if both indexes unavailable

---

### 5.2 Sparse Retrieval

**Purpose:** Lexical/keyword-based retrieval for exact term matching.

**Method:** BM25 (primary) with SPLADE as optional enhancement

**Index:** Inverted index with:
- Full text of chunks
- Section headings as boosted fields
- Legal term dictionary for expansion

**Parameters (Tunable):**
- `top_k`: 50 (per hop)
- `bm25_k1`: 1.2, `bm25_b`: 0.75
- `splade_expansion`: optional

**Output:** Ranked list with BM25 scores

---

### 5.3 Dense Retrieval

**Purpose:** Semantic similarity retrieval for conceptual matching.

**Method:** Dense vector similarity (cosine/inner product)

**Embedding Model:** Multilingual (jina-embeddings-v3 or multilingual-e5-large)

**Index:** HNSW (Hierarchical Navigable Small World) with:
- Partitioned by language + jurisdiction
- Metadata filtering at query time

**Parameters (Tunable):**
- `top_k`: 50 (per hop)
- `ef_search`: 128
- `similarity_threshold`: 0.65

**Output:** Ranked list with cosine similarity scores

---

### 5.4 Hybrid Retrieval & Fusion

**Method:** Reciprocal Rank Fusion (RRF) with authority weighting

```
RRF_score = Σ (weight_i / (k + rank_i))
where weight_i = authority_tier_weight * source_type_weight
      k = 60 (standard)
```

**Authority Tier Weights:**
- Tier 1: 1.0
- Tier 2: 0.8
- Tier 3: 0.5
- Tier 4: 0.2

**Source Type Weights (for legal claims):**
- LEGISLATION: 1.0
- RULE: 0.95
- TREATY: 0.95
- REGISTRY_RECORD: 0.9
- GUIDELINE: 0.7
- CASE_LAW: 0.85
- ACADEMIC: 0.4
- SECONDARY: 0.2

**Output:** Fused ranked list

---

### 5.5 Reranker

**Purpose:** Cross-encoder precision reranking of fused candidates.

**Model:** Cross-encoder (e.g., jina-reranker-v2, bge-reranker-v2)

**Inputs:** Query + Candidate texts (batch)

**Outputs:** Reranked list with cross-encoder scores

**Parameters (Tunable):**
- `rerank_top_k`: 20 (from fused 100)
- `batch_size`: 32
- `score_threshold`: 0.5

---

### 5.6 Evidence Selector

**Purpose:** Select final evidence set balancing relevance, diversity, and authority.

**Inputs:** Reranked candidates

**Algorithm:**
1. **Relevance Filter**: Score > threshold
2. **Authority Boost**: Tier 1/2 prioritized
3. **Diversity**: MMR (Maximal Marginal Relevance) on embeddings
   - λ = 0.7 (relevance) vs 0.3 (diversity)
4. **Coverage**: Ensure coverage of all sub-queries
5. **Token Budget**: Fit within LLM context window (reserve 40% for generation)

**Output:** `SelectedEvidence` with selection reasoning

---

### 5.7 Context Builder

**Purpose:** Build LLM context with hierarchical expansion and citation mapping.

**Mechanism:**
1. **Parent-Child Expansion**: For each selected chunk, include parent chunk (full section)
2. **Hierarchical Context**: Build section path for citation locators
3. **Citation Map**: Assign claim IDs to evidence chunks
4. **Token Management**: Truncate lowest-relevance if over budget

**Output:** `LLMContext` with structured chunks and citation locators

---

## 6. LLM Reasoning & Verification

### 6.1 LLM Reasoning Service

**Purpose:** Generate answer grounded in evidence with citations.

**Inputs:**
- `LLMContext`: Structured evidence chunks with locators
- `original_query`: User's query
- `language`: Target response language
- `jurisdiction`: Primary jurisdiction
- `formulation_classification`: optional

**Prompt Template Structure:**
```
System: You are IP-SAKTI Sahayak, a jurisdiction-aware legal research assistant.
        Follow these rules:
        1. ONLY use provided evidence. Do not use external knowledge.
        2. Every legal claim MUST have a citation [doc_id:section].
        3. Tag each claim with jurisdiction: [India::Central] or [International::Nagoya]
        4. If evidence is insufficient, explicitly state what is missing.
        5. Never mix jurisdictions in a single claim.
        6. Preserve legal terminology in original language.

Evidence:
[EVIDENCE_1] Source: Patents Act 1970, Section 3(d)
             Jurisdiction: India::Central
             Authority: Tier 1
             Text: "The mere discovery of a new form of a known substance..."

[EVIDENCE_2] Source: ...

Query: "What does Section 3(d) of the Patents Act say about new forms?"

Response Format:
CLAIM: [claim text] [jurisdiction] [evidence_refs]
CITATION: [full citation per CR schema]
CONFIDENCE: [0.0-1.0]
```

**Outputs:** `RawAnswer` with claims, citations, confidence

**Model:** Instruction-tuned LLM (Llama-3.1-70B, GPT-4o, or fine-tuned)

**Parameters:** Temperature 0.1, Top-p 0.9, Max tokens 2048

---

### 6.2 Verification Layer

**Purpose:** Verify every claim against evidence before final output.

**Checks:**
1. **Citation Verification**: Each citation locator exists in evidence
2. **Groundedness**: Claim entailed by evidence (NLI model)
3. **Entailment**: Evidence → Claim (not just related)
4. **Jurisdiction Consistency**: Claim jurisdiction matches evidence
5. **Authority Validation**: Legal claims have Tier 1/2 evidence
6. **Hallucination Detection**: Unsupported claims flagged
7. **Completeness**: All sub-queries addressed

**Mechanism:**
- NLI model (DeBERTa-v3) for entailment
- Rule-based for citation format validation
- LLM-as-judge for complex verification (optional)

**Outputs:** `VerifiedAnswer` with verification results per claim

**Failure Handling:**
- Failed claims → Removed or marked unverified
- If >30% claims fail → Abstention triggered
- Jurisdiction conflicts → Flag in answer

---

## 7. Component Interfaces (gRPC Protobuf Sketches)

```protobuf
// Query Understanding
service QueryUnderstandingService {
  rpc Analyze(AnalyzeRequest) returns (AnalyzeResponse);
}

message AnalyzeRequest {
  string raw_query = 1;
  string language_hint = 2;
  string jurisdiction_hint = 3;
}

message AnalyzeResponse {
  string normalized_query = 1;
  string detected_language = 2;
  repeated string rewritten_queries = 3;
  repeated SubQuery decomposed_subqueries = 4;
  QueryType query_type = 5;
  repeated string legal_terms_preserved = 6;
}

// Jurisdiction Engine
service JurisdictionService {
  rpc Determine(DetermineRequest) returns (DetermineResponse);
}

message DetermineRequest {
  string normalized_query = 1;
  string user_hint = 2;
}

message DetermineResponse {
  Jurisdiction primary = 1;
  repeated Jurisdiction secondary = 2;
  repeated Authority applicable_authorities = 3;
  TemporalScope temporal_scope = 4;
  float confidence = 5;
  map<string, float> detection_signals = 6;
  repeated JurisdictionConflict conflicts = 7;
}

// Retrieval Orchestrator
service RetrievalService {
  rpc Retrieve(RetrieveRequest) returns (RetrieveResponse);
}

message RetrieveRequest {
  RetrievalPlan plan = 1;
}

message RetrieveResponse {
  repeated CandidateEvidence candidates = 1;
  RetrievalMetadata metadata = 2;
}

// LLM Reasoning
service ReasoningService {
  rpc Generate(GenerateRequest) returns (GenerateResponse);
}

message GenerateRequest {
  LLMContext context = 1;
  string original_query = 2;
  string language = 3;
  Jurisdiction jurisdiction = 4;
}

message GenerateResponse {
  string answer_text = 1;
  repeated Claim claims = 2;
  repeated Citation citations = 3;
  repeated float confidence_per_claim = 4;
  repeated Jurisdiction claim_jurisdictions = 5;
}
```

---

## 8. Failure Modes & Fallbacks (Per Component)

| Component | Failure Mode | Detection | Recovery | Fallback | User-Facing |
|-----------|--------------|-----------|----------|----------|-------------|
| Query Understanding | LLM timeout | Latency > 2s | Retry once | Skip rewrite/decompose | Slightly lower recall |
| Jurisdiction Engine | Conflicting signals | Confidence < 0.6 | Multi-jurisdiction mode | Default India + disclaimer | "Assuming India..." |
| Intent Classifier | Low confidence | Confidence < 0.7 | Clarifying question | Default QC-01 | "Could you clarify?" |
| Formulation Classifier | Rule/LLM disagree | Conflict flag | Human escalation queue | UNCERTAIN + escalate | "Consult expert" |
| Sparse Retriever | Index unavailable | Health check fail | Read replica | BM25 on local FTS5 | Degraded mode notice |
| Dense Retriever | Vector DB down | Connection error | Cached embeddings | Lexical-only | "Limited semantic search" |
| Reranker | GPU OOM | Error | Batch size reduction | Skip reranking | Lower precision |
| Evidence Selector | No candidates | Empty pool | Expand filters | "No authoritative source" | Clear statement |
| LLM Reasoning | API error/timeout | HTTP 5xx/timeout | Retry + fallback model | Template response | "Service limited" |
| Verification | NLI model down | Error | Skip entailment check | Citation-only check | Reduced verification |

---

## 9. Evaluation Methods Per Component

| Component | Metric | Target | Method |
|-----------|--------|--------|--------|
| Query Understanding | Language Detection Acc | >99% | Labeled test set |
| Query Understanding | Rewrite Recall Gain | >15% | A/B on retrieval |
| Jurisdiction Engine | Detection Accuracy | >95% | Labeled queries |
| Intent Classifier | Classification F1 | >90% | Test set per category |
| Formulation Classifier | Classification Acc | >85% | Expert-labeled cases |
| Retrieval (Sparse) | Recall@50 | >80% | Benchmark queries |
| Retrieval (Dense) | Recall@50 | >85% | Benchmark queries |
| Retrieval (Hybrid) | Recall@50 | >90% | Benchmark queries |
| Reranker | nDCG@10 improvement | >10% over fusion | Reranker eval set |
| Evidence Selector | Coverage | >95% sub-queries | Human eval |
| LLM Reasoning | Groundedness | >95% | NLI + human eval |
| LLM Reasoning | Citation Precision | >90% | Verification layer |
| Verification | Hallucination Detection | >95% | Adversarial test set |
| End-to-End | Answer Correctness | >85% | Expert evaluation |

---

## 10. Phase 2 Completion Checklist

- [x] End-to-end pipeline design documented
- [x] Component decomposition with responsibilities
- [x] Data flow design (query + ingestion)
- [x] Query flow with all intermediate data structures
- [x] Component interfaces specified (gRPC sketches)
- [x] Failure modes and fallbacks per component
- [x] Evaluation methods per component defined
- [x] Tunable parameters identified and marked
- [x] Jurisdiction isolation enforced at retrieval level
- [x] Citation-first generation designed
- [x] Verification layer designed
- [x] Authority-weighted retrieval specified

**Phase 2 Status: COMPLETE** ✅

---

## Next Phase: Phase 3 - RAG Architecture

**Entry Criteria:** Phase 2 architecture signed off  
**Exit Criteria:** Complete RAG architecture with technique evaluation matrix (Core/Optional/Experimental/Not Worth It)