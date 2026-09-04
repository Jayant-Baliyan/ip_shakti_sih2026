# Phase 3: RAG Architecture
## IP-SAKTI Sahayak - Complete RAG Architecture Specification

**Status:** COMPLETE  
**Version:** 1.0  
**Date:** 2026-09-02

---

## 1. RAG Architecture Overview

### 1.1 Design Philosophy

The RAG architecture for IP-SAKTI is designed around **legal evidence retrieval** rather than general-purpose semantic search. Key differentiators:

| Traditional RAG | IP-SAKTI RAG |
|----------------|--------------|
| Single embedding space | Multi-space: sparse + dense + legal-structure |
| Fixed chunking | Legal-hierarchy-aware chunking (Act→Section→Clause) |
| Top-K retrieval | Multi-hop, jurisdiction-filtered, authority-weighted |
| Post-hoc citation | Citation-first generation with verification layer |
| Generic reranking | Legal-term-aware cross-encoder + MMR diversity |
| Single query | Query decomposition → multi-hop plan |

### 1.2 Core Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         RAG RETRIEVAL PIPELINE                                │
│                                                                              │
│  USER QUERY                                                                  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌──────────────────────────────────────────┐                               │
│  │           QUERY UNDERSTANDING             │                               │
│  │  • Language Detection                     │                               │
│  │  • Normalization (legal term canon)       │                               │
│  │  • Rewrite (decontextualize, expand)      │                               │
│  │  • Decompose (multi-hop sub-queries)      │                               │
│  └─────────────────┬─────────────────────────┘                               │
│                    │                                                         │
│                    ▼                                                         │
│  ┌──────────────────────────────────────────┐                               │
│  │           JURISDICTION ENGINE             │  (deterministic)             │
│  │  • Detect / Select jurisdiction           │                               │
│  │  • Map to authority sources               │                               │
│  │  • Temporal validity filter               │                               │
│  └─────────────────┬─────────────────────────┘                               │
│                    │                                                         │
│                    ▼                                                         │
│  ┌──────────────────────────────────────────┐                               │
│  │           QUERY PLANNER                   │                               │
│  │  • Build multi-hop retrieval plan         │                               │
│  │  • Per-hop: strategy, filters, K-values  │                               │
│  └─────────────────┬─────────────────────────┘                               │
│                    │                                                         │
│                    ▼                                                         │
│  ┌──────────────────────────────────────────┐                               │
│  │        RETRIEVAL ORCHESTRATOR             │                               │
│  │                                           │                               │
│  │  HOP 1                    HOP 2          │                               │
│  │  ┌─────────┐              ┌─────────┐    │                               │
│  │  │ SPARSE  │              │ SPARSE  │    │                               │
│  │  │ (BM25)  │              │ (BM25)  │    │                               │
│  │  └────┬────┘              └────┬────┘    │                               │
│  │       │                        │          │                               │
│  │  ┌────┴────┐              ┌────┴────┐    │                               │
│  │  │ DENSE   │              │ DENSE   │    │                               │
│  │  │ (Vec)   │              │ (Vec)   │    │                               │
│  │  └────┬────┘              └────┬────┘    │                               │
│  │       │                        │          │                               │
│  │       └──────────┬─────────────┘          │                               │
│  │                  ▼                        │                               │
│  │         ┌─────────────────┐               │                               │
│  │         │ METADATA FILTER │               │                               │
│  │         │ (Jurisdiction,  │               │                               │
│  │         │  Authority,     │               │                               │
│  │         │  DocType, Date) │               │                               │
│  │         └────────┬────────┘               │                               │
│  │                  ▼                        │                               │
│  │         ┌─────────────────┐               │                               │
│  │         │ FUSION (RRF)    │               │                               │
│  │         │ Weighted by     │               │                               │
│  │         │ Authority Tier  │               │                               │
│  │         └────────┬────────┘               │                               │
│  │                  ▼                        │                               │
│  │         ┌─────────────────┐               │                               │
│  │         │ CROSS-ENCODER   │               │                               │
│  │         │ RERANKER        │               │                               │
│  │         └────────┬────────┘               │                               │
│  │                  ▼                        │                               │
│  │         ┌─────────────────┐               │                               │
│  │         │ EVIDENCE        │               │                               │
│  │         │ SELECTOR        │               │                               │
│  │         │ (MMR + Auth +   │               │                               │
│  │         │  Relevance)     │               │                               │
│  │         └────────┬────────┘               │                               │
│  └──────────────────┼────────────────────────┘                               │
│                     │                                                         │
│                     ▼                                                         │
│         ┌─────────────────────────┐                                          │
│         │      CONTEXT BUILDER    │                                          │
│         │  • Parent-child expand  │                                          │
│         │  • Citation mapping     │                                          │
│         │  • Token budget mgmt    │                                          │
│         │  • Jurisdiction grouping│                                          │
│         └───────────┬─────────────┘                                          │
│                     │                                                         │
│                     ▼                                                         │
│         ┌─────────────────────────┐                                          │
│         │      LLM REASONING      │                                          │
│         │  • Citation-first gen   │                                          │
│         │  • Multi-check verify   │                                          │
│         └─────────────────────────┘                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Component Design

### 2.1 Query Normalization (CORE)

**Purpose:** Transform raw user input into canonical legal query form.

**Inputs:** Raw query string, detected language, conversation context

**Outputs:** Normalized query string, extracted entities, legal terms mapped

**Mechanism:**
```python
class QueryNormalizer:
    def normalize(self, query: str, lang: str) -> NormalizedQuery:
        # 1. Unicode normalization (NFC)
        # 2. Legal abbreviation expansion (e.g., "Sec." → "Section", "Art." → "Article")
        # 3. Indian legal term canonicalization:
        #    - "patent act" → "The Patents Act, 1970"
        #    - "tm rules" → "The Trade Marks Rules, 2017"
        #    - "bd act" → "The Biological Diversity Act, 2002"
        #    - "abs rules" → "The Biological Diversity (ABS) Rules, 2014"
        # 4. Citation normalization: "S. 3(d)" → "Section 3(d)", "Rule 13(2)" → "Rule 13(2)"
        # 5. Entity extraction: act names, section numbers, case citations, dates
        # 6. Temporal normalization: "latest amendment" → effective date lookup
        
        return NormalizedQuery(
            text=canonical_text,
            entities=extracted_entities,
            legal_terms=canonical_terms,
            temporal_refs=temporal_references
        )
```

**Data Structures:**
```protobuf
message NormalizedQuery {
  string canonical_text = 1;
  repeated LegalEntity entities = 2;
  repeated CanonicalTerm legal_terms = 3;
  repeated TemporalReference temporal_refs = 4;
  string detected_language = 5;
}

message LegalEntity {
  enum Type { ACT=0; SECTION=1; RULE=2; CASE=3; TREATY=4; AUTHORITY=5; DATE=6; }
  Type type = 1;
  string raw_text = 2;
  string canonical_id = 3;  // e.g., "INDIA:PATENTS_ACT:1970:S3D"
  float confidence = 4;
}
```

**Dependencies:** Legal terminology dictionary (maintained per jurisdiction), abbreviation database

**Failure Modes:**
- Unknown abbreviation → preserve original, flag for review
- Ambiguous reference (e.g., "Section 3" without act) → defer to planner for multi-hop resolution

**Fallback:** Skip normalization, pass raw query to retriever with lower confidence

**Evaluation:** 
- Term canonicalization accuracy on 500 labeled queries
- Entity extraction F1 > 90%
- End-to-end retrieval recall improvement > 15%

---

### 2.2 Query Classification (CORE)

**Purpose:** Classify query into one of 10 categories to drive retrieval strategy.

**Inputs:** Normalized query, jurisdiction, language

**Outputs:** QueryCategory, confidence, retrieval strategy hints

**Categories (from Phase 1):**
| Code | Category | Example | Retrieval Strategy |
|------|----------|---------|-------------------|
| QC-01 | Section Lookup | "What does Section 3(d) of Patents Act say?" | Direct section retrieval, parent-child expand |
| QC-02 | Cross-Section Synthesis | "What are patentability requirements in India?" | Multi-section retrieval, synthesis |
| QC-03 | Procedure/Process | "How to file a patent in India?" | Rule/guideline retrieval, sequential steps |
| QC-04 | Formulation Classification | "Is Chyawanprash a classical medicine?" | Rule engine + LLM reasoning |
| QC-05 | ABS Guidance | "What ABS approvals needed for neem export?" | NBA act/rules/forms, multi-hop |
| QC-06 | Prior Art / TK Search | "Prior art for turmeric wound healing?" | TKDL public + patent search |
| QC-07 | Regulatory Compliance | "FSSAI Ayurveda-Aahar labeling reqs?" | FSSAI act/rules + notifications |
| QC-08 | Treaty Obligation | "India's TRIPS Art 27.3(b) obligations?" | Treaty text + domestic implementation |
| QC-09 | Case Law Interpretation | "Novartis v Union of India Sec 3(d) ruling?" | Case law + cited sections |
| QC-10 | Comparative/Jurisdictional | "Patent term India vs US vs EU?" | Multi-jurisdiction (explicit) |

**Mechanism:**
```python
class QueryClassifier:
    def __init__(self):
        # Deterministic rules first (high precision patterns)
        self.rule_patterns = {
            QC_01: [r"section\s+\d+", r"article\s+\d+", r"rule\s+\d+"],
            QC_03: [r"how to", r"procedure for", r"process to", r"file.*application"],
            QC_04: [r"classical medicine", r"generic medicine", r"proprietary", r"ayurveda.*ahar"],
            QC_05: [r"access.*benefit", r"abs.*approval", r"biological resource", r"prior informed consent"],
        }
        
        # LLM classifier for ambiguous cases
        self.llm_classifier = LLMClassifier(prompt_template=CLASSIFICATION_PROMPT)
    
    def classify(self, query: NormalizedQuery) -> QueryClassification:
        # 1. Rule-based matching (deterministic, explainable)
        rule_match = self._match_rules(query)
        if rule_match.confidence > 0.85:
            return rule_match
        
        # 2. LLM classification with few-shot examples
        llm_result = self.llm_classifier.classify(query)
        
        # 3. Combine: if rule and LLM agree → high confidence
        #    if disagree → flag for human review, use lower confidence
        return self._combine(rule_match, llm_result)
```

**Data Structures:**
```protobuf
message QueryClassification {
  enum Category { QC_01=1; QC_02=2; QC_03=3; QC_04=4; QC_05=5; QC_06=6; QC_07=7; QC_08=8; QC_09=9; QC_10=10; }
  Category category = 1;
  float confidence = 2;
  RetrievalStrategyHints hints = 3;
  string reasoning = 4;
}

message RetrievalStrategyHints {
  int32 sparse_k = 1;           // e.g., 50
  int32 dense_k = 2;            // e.g., 50
  int32 rerank_k = 3;           // e.g., 20
  int32 final_k = 4;            // e.g., 8
  bool multi_hop = 5;           // true for QC-02, QC-05, QC-08, QC-10
  repeated string required_doc_types = 6;  // e.g., ["LEGISLATION", "RULE"]
  repeated string jurisdiction_hints = 7;
  bool needs_temporal_filter = 8;
}
```

**Dependencies:** Query normalizer output, few-shot examples per category

**Failure Modes:**
- Low confidence (< 0.6) → clarifying question to user
- Misclassification → retrieved evidence may be wrong type; verification layer catches

**Fallback:** Default to QC-02 (Cross-Section Synthesis) with broad retrieval

**Evaluation:**
- Classification accuracy on 1000 labeled queries per category
- Retrieval quality per category (recall@K)

---

### 2.3 Query Rewriting (CORE)

**Purpose:** Improve retrieval recall by generating alternative query formulations.

**Inputs:** Normalized query, classification, conversation history

**Outputs:** List of rewritten queries with weights

**Techniques:**
| Technique | When Applied | Method |
|-----------|--------------|--------|
| **Decontextualization** | Conversational queries | "What about Section 5?" → "What does Section 5 of the Patents Act, 1970 say?" |
| **Legal Synonym Expansion** | All queries | "patentability" → "patentability OR novelty OR inventive step OR industrial application" |
| **Hierarchical Expansion** | Section lookups | "Section 3(d)" → "Section 3(d) Patents Act 1970" + parent "Chapter II" |
| **Multi-lingual Rewrite** | Non-English queries | Hindi query → English legal terms + Hindi terms |
| **Temporal Expansion** | "Latest amendment" | Resolve to specific amendment act + date |

**Mechanism:**
```python
class QueryRewriter:
    def rewrite(self, query: NormalizedQuery, classification: QueryClassification) -> List[RewrittenQuery]:
        rewrites = []
        
        # 1. Decontextualization (if conversational)
        if query.has_conversation_context():
            rewrites.append(self._decontextualize(query))
        
        # 2. Legal synonym expansion (deterministic dictionary)
        rewrites.append(self._expand_legal_synonyms(query))
        
        # 3. Hierarchical expansion (legal structure aware)
        if classification.category in [QC_01, QC_02]:
            rewrites.extend(self._expand_hierarchy(query))
        
        # 4. Cross-lingual (if non-English)
        if query.detected_language != "en":
            rewrites.append(self._translate_legal_terms(query))
        
        # 5. Temporal resolution
        if query.has_temporal_refs():
            rewrites.append(self._resolve_temporal(query))
        
        # Weight rewrites: original=1.0, expanded=0.7, translated=0.8
        return rewrites
```

**Tunable Parameters:**
- `max_rewrites_per_query`: 5 (default)
- `synonym_expansion_weight`: 0.7
- `hierarchical_expansion_weight`: 0.8

**Evaluation:**
- Recall@50 improvement on benchmark: target > 15%
- Precision@10 impact: should not degrade > 5%

---

### 2.4 Query Decomposition / Multi-Hop Planning (CORE)

**Purpose:** Break complex queries into ordered sub-queries with retrieval strategy per hop.

**Inputs:** Classified query, normalized query, jurisdiction

**Outputs:** RetrievalPlan with ordered hops

**Query Categories → Decomposition Patterns:**

| Category | Decomposition Pattern |
|----------|----------------------|
| QC-01 (Section Lookup) | Single hop: direct section retrieval |
| QC-02 (Cross-Section) | Multi-hop: 1) Find relevant act → 2) Retrieve sections → 3) Synthesize |
| QC-03 (Procedure) | Sequential hops: 1) Identify governing rule → 2) Get steps → 3) Get forms/fees |
| QC-04 (Formulation) | 1) Extract ingredients → 2) Check classical refs → 3) Apply rules → 4) Check ABS |
| QC-05 (ABS Guidance) | 1) Identify biological resource → 2) Check VAPs list → 3) Determine approval type → 4) Get forms |
| QC-06 (Prior Art) | 1) Search TKDL public → 2) Search patent DB → 3) Cross-reference |
| QC-07 (Compliance) | 1) Identify applicable regulation → 2) Get specific requirements → 3) Get forms/checklists |
| QC-08 (Treaty) | 1) Get treaty article → 2) Find domestic implementing law → 3) Get relevant sections |
| QC-09 (Case Law) | 1) Find case → 2) Get cited sections → 3) Get subsequent treatment |
| QC-10 (Comparative) | Multi-jurisdiction: parallel hops per jurisdiction |

**Mechanism:**
```python
class QueryPlanner:
    def plan(self, query: NormalizedQuery, classification: QueryClassification, 
             jurisdiction: Jurisdiction) -> RetrievalPlan:
        
        plan = RetrievalPlan(query_id=uuid4())
        
        if classification.category == QC_01:
            plan.add_hop(Hop(
                sub_query=query.canonical_text,
                strategy=RetrievalStrategy.DIRECT_SECTION_LOOKUP,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["LEGISLATION"]),
                k=8
            ))
        
        elif classification.category == QC_02:
            # Hop 1: Identify relevant act/chapter
            plan.add_hop(Hop(
                sub_query=f"Which act governs {query.extracted_topic} in {jurisdiction}?",
                strategy=RetrievalStrategy.BROAD_SEARCH,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["LEGISLATION"]),
                k=10
            ))
            # Hop 2: Retrieve sections from identified act
            plan.add_hop(Hop(
                sub_query=f"Sections of {identified_act} on {query.extracted_topic}",
                strategy=RetrievalStrategy.SECTION_SEARCH,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["LEGISLATION"], parent_act=identified_act),
                k=20
            ))
            # Hop 3: Get rules/guidelines
            plan.add_hop(Hop(
                sub_query=f"Rules and guidelines under {identified_act} for {query.extracted_topic}",
                strategy=RetrievalStrategy.BROAD_SEARCH,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["RULE", "GUIDELINE"]),
                k=10
            ))
        
        elif classification.category == QC_05:  # ABS
            plan.add_hop(Hop(
                sub_query=f"Biological resource classification for {query.resource} in India",
                strategy=RetrievalStrategy.VAPS_LOOKUP,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["GUIDELINE", "NOTIFICATION"]),
                k=10
            ))
            plan.add_hop(Hop(
                sub_query=f"ABS approval process for {query.resource} export from India",
                strategy=RetrievalStrategy.PROCEDURE_SEARCH,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["RULE", "GUIDELINE", "REGISTRY_RECORD"]),
                k=10
            ))
            plan.add_hop(Hop(
                sub_query=f"Form I/II/III requirements for {query.resource}",
                strategy=RetrievalStrategy.FORM_LOOKUP,
                filters=MetadataFilters(jurisdiction=jurisdiction, doc_types=["REGISTRY_RECORD"]),
                k=5
            ))
        
        return plan
```

**Data Structures:**
```protobuf
message RetrievalPlan {
  string plan_id = 1;
  string original_query = 2;
  repeated Hop hops = 3;
}

message Hop {
  string hop_id = 1;
  string sub_query = 2;
  RetrievalStrategy strategy = 3;
  MetadataFilters filters = 4;
  int32 k = 5;
  bool depends_on_previous = 6;  // true for sequential hops
}

enum RetrievalStrategy {
  DIRECT_SECTION_LOOKUP = 0;
  BROAD_SEARCH = 1;
  SECTION_SEARCH = 2;
  PROCEDURE_SEARCH = 3;
  VAPS_LOOKUP = 4;      // NBA VAPs classification
  FORM_LOOKUP = 5;
  TREATY_ARTICLE_LOOKUP = 6;
  CASE_LAW_SEARCH = 7;
  PRIOR_ART_SEARCH = 8;
  MULTI_JURISDICTION_PARALLEL = 9;
}
```

---

### 2.5 Sparse Retrieval (CORE)

**Purpose:** Lexical matching for exact legal terms, section numbers, citations.

**Method:** BM25 with legal-term boosting (preferred over SPLADE for legal domain)

**Why BM25 over SPLADE:**
- Legal queries rely on exact term matching (section numbers, act names)
- SPLADE expansion introduces noise for legal terminology
- BM25 is deterministic, explainable, fast
- Can augment with legal synonym dictionary for expansion

**Configuration:**
```python
class SparseRetriever:
    def __init__(self):
        self.index = BM25Index(
            tokenizer=LegalTokenizer(),  # Preserves "Section 3(d)" as single token
            legal_boost_dict={
                "section": 2.0,
                "article": 2.0,
                "rule": 2.0,
                "clause": 1.5,
                "schedule": 1.5,
                "amendment": 1.5,
            }
        )
    
    def retrieve(self, query: str, filters: MetadataFilters, k: int) -> List[Candidate]:
        # Apply metadata filters at query time (jurisdiction, doc_type, authority_tier)
        # BM25 scoring with authority tier boost
        candidates = self.index.search(query, k=k*3, filters=filters)
        
        # Boost by authority tier
        for c in candidates:
            c.score *= AUTHORITY_TIER_BOOST[c.source.authority_tier]
        
        return top_k(candidates, k)
```

**Index Structure:**
- Field: `content` (full text)
- Field: `section_numbers` (extracted: "3(d)", "13(2)", etc.)
- Field: `act_name` (exact act title)
- Field: `jurisdiction` (INDIA, INTERNATIONAL, etc.)
- Field: `authority_tier` (1-4)
- Field: `doc_type` (LEGISLATION, RULE, etc.)
- Field: `effective_date` (for temporal filtering)

**Tunable Parameters:**
- `bm25_k1`: 1.2 (default), tune: 1.0-2.0
- `bm25_b`: 0.75 (default), tune: 0.5-1.0
- `legal_term_boost_factor`: 2.0
- `authority_tier_boost`: {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.3}

**Evaluation:**
- Recall@50 on legal section lookup queries
- Precision@10 on citation-heavy queries
- Latency: < 50ms for 1M docs

---

### 2.6 Dense Retrieval (CORE)

**Purpose:** Semantic similarity for conceptual queries, cross-lingual retrieval.

**Embedding Model Requirements:**
| Requirement | Specification |
|-------------|---------------|
| Multilingual | English + 15 Indian languages minimum |
| Legal domain adaptation | Fine-tuned on Indian legal corpus |
| Context length | ≥ 512 tokens (legal sections can be long) |
| Output dimension | 768 or 1024 |
| Inference latency | < 50ms per query |

**Recommended Models (in priority order):**
1. **jina-embeddings-v3** (multilingual, 8192 ctx, task-specific LoRA) - if available
2. **mixedbread-ai/mxbai-embed-large-v1** (1024 dim, multilingual, strong legal)
3. **BAAI/bge-m3** (multilingual, dense+sparse+colbert, 8192 ctx)
4. **sentence-transformers/paraphrase-multilingual-mpnet-base-v2** (fallback)

**Vector Index:** HNSW (Hierarchical Navigable Small World)
- `M`: 16 (connections per node)
- `ef_construction`: 200
- `ef_search`: 64 (tunable)
- Distance: Cosine similarity

**Metadata Filtering:** Pre-filter by jurisdiction + authority_tier before vector search (filter-then-search) for jurisdiction isolation guarantee.

**Mechanism:**
```python
class DenseRetriever:
    def __init__(self):
        self.embedder = LegalEmbedder(model="mixedbread-ai/mxbai-embed-large-v1")
        self.index = HNSWIndex(
            space="cosine",
            M=16,
            ef_construction=200,
            ef_search=64
        )
    
    def retrieve(self, query: str, filters: MetadataFilters, k: int) -> List[Candidate]:
        # 1. Embed query (with task prompt: "retrieve legal document")
        query_emb = self.embedder.encode([query], prompt_name="retrieval")[0]
        
        # 2. Pre-filter metadata (jurisdiction isolation enforced here)
        allowed_ids = self.metadata_store.filter(filters)
        
        # 3. Vector search with filter
        results = self.index.search(query_emb, k=k*3, filter_ids=allowed_ids)
        
        return [Candidate(doc_id=r.id, score=r.score, metadata=r.metadata) for r in results]
```

**Tunable Parameters:**
- `ef_search`: 64 (trade-off recall vs latency)
- `k_multiplier`: 3 (retrieve 3x for reranking)
- `min_score_threshold`: 0.3 (cosine similarity)

**Failure Modes:**
- Vector DB unavailable → fallback to sparse-only
- Embedding model timeout → cached embeddings for recent queries

**Evaluation:**
- Recall@50 vs sparse on semantic queries
- Cross-lingual retrieval quality (English query → Hindi doc)
- Latency percentiles (p50, p95, p99)

---

### 2.7 Hybrid Retrieval (CORE)

**Purpose:** Combine sparse + dense for best of both worlds.

**Fusion Method:** Reciprocal Rank Fusion (RRF) with authority weighting

**Why RRF over weighted sum:**
- Score normalization not needed across different scoring systems
- Robust to outliers
- Authority weighting applied as rank modifier, not score modifier

**Algorithm:**
```python
def hybrid_fusion(sparse_results: List[Candidate], 
                  dense_results: List[Candidate],
                  k: int = 60,
                  authority_weights: Dict[int, float] = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4}) -> List[Candidate]:
    """
    RRF with authority tier weighting.
    RRF score = sum(1 / (k + rank_i)) * authority_weight
    """
    doc_scores = defaultdict(float)
    doc_objects = {}
    
    for rank, cand in enumerate(sparse_results):
        weight = authority_weights.get(cand.metadata.authority_tier, 0.3)
        doc_scores[cand.doc_id] += weight / (k + rank + 1)
        doc_objects[cand.doc_id] = cand
    
    for rank, cand in enumerate(dense_results):
        weight = authority_weights.get(cand.metadata.authority_tier, 0.3)
        doc_scores[cand.doc_id] += weight / (k + rank + 1)
        if cand.doc_id not in doc_objects:
            doc_objects[cand.doc_id] = cand
    
    # Sort by fused score
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    
    return [doc_objects[doc_id] for doc_id, _ in sorted_docs[:k]]
```

**Tunable Parameters:**
- `rrf_k`: 60 (standard), tune: 20-100
- `authority_weights`: {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2}
- `sparse_weight` vs `dense_weight`: implicit in RRF, but can pre-scale

**Experimental Alternative (Optional):**
- **Weighted Score Fusion**: normalize scores to [0,1] per retriever, then weighted sum
- Only if RRF proves insufficient in experiments

---

### 2.8 Metadata Filtering (CORE - Jurisdiction Isolation)

**Purpose:** Hard filter at retrieval time to enforce jurisdiction isolation.

**Implementation:**
```python
class MetadataFilter:
    def apply(self, candidates: List[Candidate], filters: MetadataFilters) -> List[Candidate]:
        # HARD FILTERS (never bypassed)
        filtered = []
        for c in candidates:
            # Jurisdiction: must match exactly or be INTERNATIONAL treaty
            if filters.jurisdiction:
                if not self._jurisdiction_match(c.metadata.jurisdiction, filters.jurisdiction):
                    continue
            
            # Authority tier: minimum tier
            if filters.min_authority_tier and c.metadata.authority_tier > filters.min_authority_tier:
                continue
            
            # Document type
            if filters.doc_types and c.metadata.doc_type not in filters.doc_types:
                continue
            
            # Temporal: effective_date <= query_date
            if filters.as_of_date and c.metadata.effective_date > filters.as_of_date:
                continue
            
            # Superseded check: exclude superseded versions unless explicitly requested
            if c.metadata.is_superseded and not filters.include_superseded:
                continue
            
            filtered.append(c)
        
        return filtered
    
    def _jurisdiction_match(self, doc_jurisdiction: str, query_jurisdiction: str) -> bool:
        # Exact match
        if doc_jurisdiction == query_jurisdiction:
            return True
        # International treaties apply to all signatories
        if doc_jurisdiction == "INTERNATIONAL" and query_jurisdiction in TREATY_SIGNATORIES.get(query_jurisdiction, []):
            return True
        # India-specific: INTERNATIONAL treaties India is party to
        if query_jurisdiction == "INDIA" and doc_jurisdiction in INDIA_TREATY_PARTIES:
            return True
        return False
```

**Critical:** This filter runs BEFORE fusion/reranking - jurisdiction isolation is non-negotiable.

---

### 2.9 Cross-Encoder Reranking (CORE)

**Purpose:** Precise relevance scoring of query-chunk pairs.

**Model:** Cross-encoder fine-tuned on legal relevance data
- Base: `cross-encoder/ms-marco-MiniLM-L-6-v2` → fine-tune on Indian legal QA pairs
- Or: `BAAI/bge-reranker-v2-m3` (multilingual, strong zero-shot)

**Input:** Query + Candidate text (with section context)

**Output:** Relevance score [0,1]

**Mechanism:**
```python
class CrossEncoderReranker:
    def __init__(self):
        self.model = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
    
    def rerank(self, query: str, candidates: List[Candidate], top_k: int) -> List[Candidate]:
        # Prepare pairs: (query, candidate_text_with_context)
        pairs = []
        for c in candidates:
            # Include parent section heading for context
            text = self._build_candidate_text(c)
            pairs.append([query, text])
        
        # Batch inference
        scores = self.model.predict(pairs, batch_size=32)
        
        # Attach scores and sort
        for c, score in zip(candidates, scores):
            c.rerank_score = float(score)
        
        return sorted(candidates, key=lambda x: x.rerank_score, reverse=True)[:top_k]
    
    def _build_candidate_text(self, candidate: Candidate) -> str:
        # Include hierarchical context: Act > Chapter > Section > Clause
        parts = []
        if candidate.metadata.act_title:
            parts.append(f"Act: {candidate.metadata.act_title}")
        if candidate.metadata.chapter:
            parts.append(f"Chapter: {candidate.metadata.chapter}")
        if candidate.metadata.section:
            parts.append(f"Section: {candidate.metadata.section}")
        parts.append(candidate.text)
        return " | ".join(parts)
```

**Tunable Parameters:**
- `rerank_top_k`: 20 (from fusion output)
- `final_top_k`: 8 (to context builder)
- `batch_size`: 32 (GPU memory dependent)
- `max_length`: 512 tokens

**Evaluation:**
- nDCG@10 improvement over hybrid fusion: target > 10%
- Latency: < 200ms for 20 candidates

---

### 2.10 Evidence Selection (CORE)

**Purpose:** Select diverse, authoritative, non-redundant evidence for context.

**Algorithm:** Maximum Marginal Relevance (MMR) with authority weighting

```python
class EvidenceSelector:
    def select(self, candidates: List[Candidate], 
               final_k: int = 8,
               diversity_lambda: float = 0.5) -> List[Evidence]:
        """
        MMR: score = lambda * relevance + (1-lambda) * (1 - max_sim_to_selected)
        """
        selected = []
        remaining = candidates.copy()
        
        # Always include highest authority tier doc first
        remaining.sort(key=lambda x: (x.metadata.authority_tier, -x.rerank_score))
        selected.append(remaining.pop(0))
        
        while len(selected) < final_k and remaining:
            best_score = -1
            best_idx = -1
            
            for i, cand in enumerate(remaining):
                # Relevance component
                relevance = cand.rerank_score
                
                # Authority component
                authority = 1.0 / cand.metadata.authority_tier
                
                # Diversity component: max cosine similarity to already selected
                max_sim = max(
                    cosine_sim(cand.embedding, s.embedding) 
                    for s in selected
                ) if selected else 0
                
                diversity = 1 - max_sim
                
                # Combined score
                score = (diversity_lambda * relevance + 
                        (1 - diversity_lambda) * diversity +
                        0.1 * authority)
                
                if score > best_score:
                    best_score = score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return [self._to_evidence(c) for c in selected]
```

**Deduplication:**
- Near-duplicate detection (cosine > 0.95) → keep higher authority
- Same section from different versions → keep latest effective version

**Tunable Parameters:**
- `final_k`: 8 (context window limit)
- `diversity_lambda`: 0.5 (balance relevance vs diversity)
- `dedup_threshold`: 0.95

---

### 2.11 Context Building (CORE)

**Purpose:** Build LLM context with hierarchical expansion and citation mapping.

**Mechanism:**
```python
class ContextBuilder:
    def build(self, evidence: List[Evidence], token_budget: int = 8000) -> LLMContext:
        context_parts = []
        citation_map = {}  # citation_id -> evidence
        citation_counter = 0
        
        for ev in evidence:
            citation_counter += 1
            cite_id = f"[{citation_counter}]"
            citation_map[cite_id] = ev
            
            # Build chunk with hierarchical context
            chunk_text = self._build_chunk_with_context(ev, cite_id)
            
            # Check token budget
            if self._estimate_tokens(context_parts + [chunk_text]) > token_budget:
                # Try truncated version
                truncated = self._truncate_chunk(ev, cite_id, token_budget - self._estimate_tokens(context_parts))
                if truncated:
                    context_parts.append(truncated)
                break
            
            context_parts.append(chunk_text)
        
        return LLMContext(
            context_text="\n\n---\n\n".join(context_parts),
            citation_map=citation_map,
            total_tokens=self._estimate_tokens(context_parts),
            jurisdictions=set(e.metadata.jurisdiction for e in evidence)
        )
    
    def _build_chunk_with_context(self, evidence: Evidence, cite_id: str) -> str:
        parts = []
        m = evidence.metadata
        
        # Hierarchical header
        if m.act_title:
            parts.append(f"SOURCE: {m.act_title}")
        if m.chapter:
            parts.append(f"CHAPTER: {m.chapter}")
        if m.section:
            parts.append(f"SECTION: {m.section}")
        
        # Citation marker
        parts.append(f"{cite_id} {evidence.text}")
        
        # Source metadata
        parts.append(f"[Authority: Tier {m.authority_tier} | Jurisdiction: {m.jurisdiction} | "
                     f"Effective: {m.effective_date} | Source: {m.canonical_url}]")
        
        return "\n".join(parts)
```

**Parent-Child Expansion (Optional Module):**
- If chunk is a subsection, also include parent section heading
- If chunk references another section, include that section (if in corpus)
- Controlled by token budget

---

### 2.12 Hierarchical / Parent-Child Retrieval (OPTIONAL MODULE)

**Purpose:** Retrieve at section level, expand to parent/child for context.

**When to Use:** For queries requiring full section context (QC-01, QC-02)

**Implementation:**
```python
class HierarchicalRetriever:
    def __init__(self):
        # Chunks indexed at multiple granularities
        self.section_index = VectorIndex()      # Section-level chunks
        self.clause_index = VectorIndex()       # Clause-level chunks
        self.parent_map = {}                    # clause_id -> section_id
        self.child_map = defaultdict(list)      # section_id -> [clause_ids]
    
    def retrieve_with_expansion(self, query: str, k: int) -> List[Evidence]:
        # 1. Retrieve at section level (coarse)
        section_results = self.section_index.search(query, k=k)
        
        # 2. For each section, retrieve child clauses
        expanded = []
        for sec in section_results:
            expanded.append(sec)
            children = self.clause_index.search_by_ids(self.child_map[sec.id], k=3)
            expanded.extend(children)
        
        return self._deduplicate(expanded)[:k]
```

**Storage:** Each chunk stores `parent_chunk_id`, `child_chunk_ids`, `hierarchy_level`

**Evaluation:** Compare recall@K vs flat chunking on section-lookup queries

---

### 2.13 Late-Interaction Retrieval (ColBERT) (EXPERIMENTAL)

**Purpose:** Fine-grained token-level interaction for complex legal phrasing.

**Status:** EXPERIMENTAL - Only if cross-encoder reranker insufficient

**Model:** ColBERTv2 multilingual (if available) or mColBERT

**Trade-off:**
- Pros: Better for "Section 3(d) prevents evergreening" type queries
- Cons: Higher storage (token-level vectors), higher latency, complex infrastructure

**Decision Criteria:** Run experiment comparing nDCG@10 vs cross-encoder. If > 5% improvement, promote to OPTIONAL.

---

### 2.14 Context Compression (OPTIONAL MODULE)

**Purpose:** Reduce context tokens while preserving legal meaning.

**Techniques:**
| Technique | Legal Suitability |
|-----------|-------------------|
| LLM-based summarization | Risky - may lose legal nuance |
| Sentence selection (relevance) | Good - keep high-relevance sentences |
| Legal structure preservation | **Required** - never compress across section boundaries |

**Implementation (Safe Approach):**
```python
class LegalContextCompressor:
    def compress(self, context: LLMContext, target_tokens: int) -> LLMContext:
        # Never compress within a section/clause
        # Only: drop lowest-relevance sections/clauses entirely
        # Preserve: section numbers, headings, citations
        pass
```

---

### 2.15 Negative Retrieval / Hard Negatives (EXPERIMENTAL)

**Purpose:** Train better retriever/reranker using hard negatives.

**Method:**
1. For each positive (query, relevant_doc), find hard negatives:
   - Same act, different section
   - Same section, different jurisdiction
   - Semantically similar but legally distinct
2. Use in contrastive fine-tuning of embedder/reranker

**Status:** EXPERIMENTAL - Requires labeled relevance data

---

### 2.16 Retrieval Confidence & Abstention (CORE)

**Purpose:** Quantify retrieval quality; trigger abstention when evidence insufficient.

**Metrics:**
```python
class RetrievalConfidence:
    def compute(self, evidence: List[Evidence], query: NormalizedQuery) -> RetrievalConfidence:
        signals = {
            "num_candidates": len(evidence),
            "max_rerank_score": max(e.rerank_score for e in evidence) if evidence else 0,
            "mean_rerank_score": np.mean([e.rerank_score for e in evidence]) if evidence else 0,
            "authority_coverage": self._authority_coverage(evidence),
            "jurisdiction_purity": self._jurisdiction_purity(evidence),
            "section_coverage": self._section_coverage(evidence, query),
            "temporal_currency": self._temporal_currency(evidence),
        }
        
        # Heuristic confidence score
        confidence = (
            0.3 * min(signals["num_candidates"] / 8, 1.0) +
            0.3 * signals["max_rerank_score"] +
            0.2 * signals["authority_coverage"] +
            0.1 * signals["jurisdiction_purity"] +
            0.1 * signals["temporal_currency"]
        )
        
        return RetrievalConfidence(score=confidence, signals=signals, should_abstain=confidence < 0.4)
```

**Abstention Threshold:** 0.4 (tunable based on evaluation)

**User-Facing:** "I don't have sufficient authoritative evidence to answer this reliably. [Details on what's missing]"

---

## 3. Technique Classification Matrix

| Technique | Classification | Rationale |
|-----------|---------------|-----------|
| Query Normalization | **CORE** | Essential for legal term matching |
| Query Classification | **CORE** | Drives retrieval strategy |
| Query Rewriting | **CORE** | Significant recall improvement |
| Query Decomposition | **CORE** | Required for multi-hop queries |
| Sparse Retrieval (BM25) | **CORE** | Best for exact legal terms |
| Dense Retrieval | **CORE** | Needed for semantic/conceptual queries |
| Hybrid Retrieval (RRF) | **CORE** | Proven best-of-both-worlds |
| Metadata Filtering | **CORE** | Jurisdiction isolation is mandatory |
| Cross-Encoder Reranking | **CORE** | Critical for precision |
| Evidence Selection (MMR) | **CORE** | Diversity + authority essential |
| Context Building | **CORE** | Citation mapping required |
| Hierarchical/Parent-Child | **OPTIONAL** | Valuable for section lookup; adds complexity |
| Late-Interaction (ColBERT) | **EXPERIMENTAL** | High complexity; unproven for legal |
| Context Compression | **OPTIONAL** | Only safe structure-preserving variant |
| Negative/Hard Negative Mining | **EXPERIMENTAL** | Requires labeled data; future improvement |
| Multi-Query Retrieval | **OPTIONAL** | Covered by query decomposition |
| Retrieval Fallback | **CORE** | Sparse-only when dense fails |
| Retrieval Confidence | **CORE** | Required for safe abstention |
| Sentence-Window Retrieval | **NOT WORTH IT** | Legal hierarchy > fixed windows |

---

## 4. Tunable Parameters Registry

| Parameter | Default | Range | Tuning Method |
|-----------|---------|-------|---------------|
| `bm25_k1` | 1.2 | 1.0-2.0 | Grid search on dev set |
| `bm25_b` | 0.75 | 0.5-1.0 | Grid search |
| `legal_term_boost` | 2.0 | 1.5-3.0 | Ablation |
| `authority_tier_boost` | {1:1.0, 2:0.8, 3:0.6, 4:0.4} | - | Expert eval |
| `rrf_k` | 60 | 20-100 | Grid search |
| `sparse_k` | 50 | 30-100 | Recall@K curve |
| `dense_k` | 50 | 30-100 | Recall@K curve |
| `rerank_top_k` | 20 | 10-50 | nDCG@10 vs latency |
| `final_k` | 8 | 5-15 | Context window vs quality |
| `mmr_lambda` | 0.5 | 0.3-0.7 | Diversity vs relevance |
| `dedup_threshold` | 0.95 | 0.9-0.99 | Duplicate analysis |
| `abstention_threshold` | 0.4 | 0.3-0.5 | Safety eval |
| `ef_search` | 64 | 32-128 | Recall@K vs latency |
| `cross_encoder_model` | bge-reranker-v2-m3 | - | A/B test |

---

## 5. Data Structures Summary

```protobuf
# Core retrieval types
message CandidateEvidence {
  string doc_id = 1;
  string chunk_id = 2;
  string text = 3;
  ChunkMetadata metadata = 4;
  float sparse_score = 5;
  float dense_score = 6;
  float fused_score = 7;
  float rerank_score = 8;
  repeated float embedding = 9;  // for MMR diversity
}

message ChunkMetadata {
  string source_id = 1;
  string source_name = 2;
  SourceType source_type = 3;
  int32 authority_tier = 4;
  string jurisdiction = 5;
  string act_title = 6;
  string chapter = 7;
  string section = 8;
  string subsection = 9;
  string clause = 10;
  string canonical_url = 11;
  string effective_date = 12;
  bool is_superseded = 13;
  string parent_chunk_id = 14;
  repeated string child_chunk_ids = 15;
  int32 hierarchy_level = 16;  // 0=Act, 1=Chapter, 2=Section, 3=Subsection, 4=Clause
  string content_hash = 17;
  string version = 18;
}

message Evidence {
  string evidence_id = 1;
  CandidateEvidence candidate = 2;
  string citation_id = 3;  // e.g., "[1]"
  string hierarchical_context = 4;  // For display
}

message LLMContext {
  string context_text = 1;
  map<string, Evidence> citation_map = 2;  // citation_id -> evidence
  int32 total_tokens = 3;
  repeated string jurisdictions = 4;
  map<string, int32> authority_distribution = 5;
}
```

---

## 6. Open Research Questions (from Phase 3)

1. **ORQ-13:** Optimal chunk granularity for Indian legal hierarchy (section vs clause vs sub-clause)
2. **ORQ-14:** RRF k parameter for legal texts with authority weighting
3. **ORQ-15:** Cross-encoder vs LLM-as-reranker (cost/quality trade-off)
4. **ORQ-16:** Parent-child chunk ratio for optimal context
5. **ORQ-17:** Verification layer latency budget allocation
6. **ORQ-18:** Multilingual dense retrieval quality vs translation-based
7. **ORQ-19:** Optimal MMR lambda for legal evidence diversity
8. **ORQ-20:** Retrieval confidence calibration for abstention

---

## 7. Phase 3 Completion Checklist

- [x] Query normalization design with legal term canonicalization
- [x] Query classification (10 categories) with retrieval strategy hints
- [x] Query rewriting techniques (5 methods) with weights
- [x] Query decomposition / multi-hop planning per category
- [x] Sparse retrieval (BM25 with legal boosting)
- [x] Dense retrieval (multilingual embeddings, HNSW, metadata pre-filter)
- [x] Hybrid retrieval (RRF with authority weighting)
- [x] Metadata filtering (jurisdiction isolation enforced)
- [x] Cross-encoder reranking (with legal context)
- [x] Evidence selection (MMR with authority + diversity)
- [x] Context building (hierarchical, citation-mapped, token-budgeted)
- [x] Hierarchical/parent-child retrieval (OPTIONAL module)
- [x] Late-interaction/ColBERT (EXPERIMENTAL)
- [x] Context compression (OPTIONAL, structure-preserving only)
- [x] Negative/hard negative mining (EXPERIMENTAL)
- [x] Retrieval confidence & abstention mechanism
- [x] Technique classification matrix (Core/Optional/Experimental/Not Worth It)
- [x] Tunable parameters registry with tuning methodology
- [x] Data structures for all components

**Phase 3 Status: COMPLETE** ✅

---

## Next Phase: Phase 4 - Legal Document Ingestion

**Entry Criteria:** Phase 3 architecture signed off  
**Deliverable:** Complete ingestion pipeline design with structure extraction, chunking, metadata, versioning

**Reference Documents:**
- `/architecture/phase1-requirements.md` - Requirements
- `/architecture/phase2-system-architecture.md` - System architecture
- `/architecture/phase3-rag-architecture.md` - This document
- `/data/corpus/` - Extracted corpus for testing