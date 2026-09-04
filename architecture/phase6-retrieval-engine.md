# Phase 6: Retrieval Engine Architecture

## Overview

This document designs the complete retrieval engine for IP-SAKTI. The retrieval engine is the backbone of the RAG system, responsible for finding the most relevant legal evidence for a given query while maintaining strict jurisdictional isolation and source authority awareness.

---

## 1. Requirements

### 1.1 Functional Requirements

| Requirement | Description |
|------------|-------------|
| **FR-RET-01** | Hybrid retrieval: sparse (BM25) + dense (embeddings) + metadata filtering |
| **FR-RET-02** | Strict jurisdiction isolation: never mix Indian law, treaties, foreign law |
| **FR-RET-03** | Source authority weighting: Tier 1 > Tier 2 > Tier 3 > Tier 4 |
| **FR-RET-04** | Cross-encoder reranking with hierarchical context |
| **FR-RET-05** | Evidence selection with diversity and deduplication |
| **FR-RET-06** | Retrieval confidence scoring for abstention decisions |
| **FR-RET-07** | Fallback mechanisms for each retrieval stage |
| **FR-RET-08** | Support for multilingual retrieval (English + Indian languages) |
| **FR-RET-09** | Temporal validity filtering (as-of-date queries) |
| **FR-RET-10** | Citation traceability preserved through entire pipeline |

### 1.2 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| **NFR-RET-01** | End-to-end latency: < 2s (p50), < 5s (p95) |
| **NFR-RET-02** | Sparse retrieval: < 200ms |
| **NFR-RET-03** | Dense retrieval: < 300ms |
| **NFR-RET-04** | Reranking: < 500ms (top 50 candidates) |
| **NFR-RET-05** | Recall@10: > 0.85 for legal section lookup |
| **NFR-RET-06** | Jurisdiction purity: 100% (no cross-jurisdiction contamination) |
| **NFR-RET-07** | Authority tier purity: > 90% Tier 1/2 in top 10 |

---

## 2. Retrieval Pipeline Architecture

### 2.1 Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query                                                                      │
│    │                                                                        │
│    ▼                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ QUERY ANALYSIS & PLANNING                                            │  │
│  │ - Classification (Phase 3)                                           │  │
│  │ - Jurisdiction detection (Phase 9)                                   │  │
│  │ - Formulation classification (Phase 8)                               │  │
│  │ - Decomposition into sub-queries (Phase 3)                           │  │
│  │ - Retrieval strategy selection per sub-query                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│    │                                                                        │
│    ▼                                                                        │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ SPARSE RETRIEVAL    │  │ DENSE RETRIEVAL     │  │ METADATA FILTER  │  │
│  │ (BM25)              │  │ (Vector Search)     │  │ (Pre-filter)     │  │
│  │                     │  │                     │  │                  │  │
│  │ - Legal tokenizer   │  │ - Multilingual      │  │ - Jurisdiction   │  │
│  │ - Section boost     │  │   embeddings        │  │ - Doc type       │  │
│  │ - Authority boost   │  │ - HNSW index        │  │ - Authority tier │  │
│  │ - Phrase matching   │  │ - Pre-filter by     │  │ - Temporal       │  │
│  │                     │  │   metadata          │  │ - Language       │  │
│  └──────────┬──────────┘  └──────────┬──────────┘  └────────┬─────────┘  │
│             │                        │                        │           │
│             └────────────┬───────────┴────────────────────────┘           │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │ RECIPROCAL RANK       │                                   │
│              │ FUSION (RRF)          │                                   │
│              │ + Authority Weighting │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                                │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │ CANDIDATE POOL        │                                   │
│              │ (Top K_fused)         │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                                │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │ CROSS-ENCODER         │                                   │
│              │ RERANKING             │                                   │
│              │                       │                                   │
│              │ - bge-reranker-v2-m3  │                                   │
│              │ - Hierarchical input  │                                   │
│              │ - Legal context pairs │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                                │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │ EVIDENCE SELECTION    │                                   │
│              │                       │                                   │
│              │ - MMR + Authority     │                                   │
│              │ - Deduplication       │                                   │
│              │ - Diversity           │                                   │
│              │ - Confidence scoring  │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                                │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │ CONTEXT CONSTRUCTION  │                                   │
│              │                       │                                   │
│              │ - Token budget        │                                   │
│              │ - Citation IDs        │                                   │
│              │ - Hierarchical order  │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                                │
│                          ▼                                                │
│                    Final Evidence Set                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Stage-by-Stage Configuration

| Stage | Input | Output | K-value | Latency Budget |
|-------|-------|--------|---------|----------------|
| Query Analysis | Raw query | Sub-queries + Strategy | 1 | 100ms |
| Metadata Pre-filter | Sub-query | Filtered index view | N/A | 10ms |
| Sparse Retrieval | Sub-query + filters | Top K_sparse chunks | K_sparse=100 | 200ms |
| Dense Retrieval | Sub-query + filters | Top K_dense chunks | K_dense=100 | 300ms |
| RRF Fusion | Two ranked lists | Fused ranking | K_fused=50 | 50ms |
| Cross-Encoder Rerank | Top K_fused | Reranked scores | K_rerank=20 | 500ms |
| Evidence Selection | Reranked list | Final evidence set | K_final=10 | 100ms |
| Context Construction | Evidence set | LLM context | N/A | 50ms |

---

## 3. Sparse Retrieval (BM25)

### 3.1 Why BM25 over SPLADE/Other

| Factor | BM25 | SPLADE | Decision |
|--------|------|--------|----------|
| **Exact term matching** | Excellent (section numbers, act names) | Good but learned | BM25 |
| **Legal terminology** | Preserves exact phrases | May expand incorrectly | BM25 |
| **Zero-shot** | Works immediately | Needs training data | BM25 |
| **Interpretability** | Transparent scores | Black box | BM25 |
| **Latency** | < 50ms | > 200ms | BM25 |
| **Maintenance** | No model updates | Retraining needed | BM25 |

**Decision: BM25 is CORE. SPLADE is EXPERIMENTAL.**

### 3.2 Legal BM25 Configuration

```python
class LegalBM25:
    def __init__(self):
        self.k1 = 1.6          # Term frequency saturation (higher for legal)
        self.b = 0.75          # Length normalization
        self.legal_tokenizer = LegalTokenizer()
        self.section_boost = 2.0      # Boost exact section matches
        self.act_boost = 1.5          # Boost act name matches
        self.authority_weights = {
            AuthorityTier.TIER_1: 1.0,
            AuthorityTier.TIER_2: 0.8,
            AuthorityTier.TIER_3: 0.6,
            AuthorityTier.TIER_4: 0.4,
        }
    
    def score(self, query: str, chunk: LegalChunk, filters: MetadataFilters) -> float:
        # 1. Tokenize with legal awareness
        query_terms = self.legal_tokenizer.tokenize(query)
        doc_terms = self.legal_tokenizer.tokenize(chunk.text_normalized)
        
        # 2. Base BM25 score
        base_score = self._bm25_score(query_terms, doc_terms, chunk.token_count)
        
        # 3. Legal entity boosts
        legal_boost = self._compute_legal_boost(query_terms, chunk)
        
        # 4. Authority tier weight
        authority_weight = self.authority_weights[chunk.source_provenance.authority_tier]
        
        # 5. Jurisdiction match (hard filter applied before, but soft boost)
        jurisdiction_boost = 1.0 if self._jurisdiction_matches(query, chunk) else 0.1
        
        # 6. Temporal currency boost
        temporal_boost = self._temporal_boost(chunk, filters.as_of_date)
        
        return base_score * legal_boost * authority_weight * jurisdiction_boost * temporal_boost
    
    def _compute_legal_boost(self, query_terms: List[str], chunk: LegalChunk) -> float:
        boost = 1.0
        text_lower = chunk.text_normalized.lower()
        
        # Section number exact match
        for term in query_terms:
            if re.match(r'section\s+\d+', term.lower()) and term.lower() in text_lower:
                boost *= self.section_boost
            if re.match(r'article\s+\d+', term.lower()) and term.lower() in text_lower:
                boost *= self.section_boost
            if 'act' in term.lower() and chunk.hierarchy.act_short_title.lower() in text_lower:
                boost *= self.act_boost
        
        # Definition chunk boost
        if chunk.chunk_type == ChunkType.DEFINITION:
            boost *= 1.5
        
        return boost
```

### 3.3 Legal Tokenizer

```python
class LegalTokenizer:
    """
    Tokenizer preserving legal citations as single tokens.
    """
    LEGAL_PATTERNS = [
        r'Section\s+\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?(?:\([ivx]+\))?',  # Section 3(d)(i)
        r'Article\s+\d+[A-Z]?',                                            # Article 21
        r'Rule\s+\d+[A-Z]?',                                               # Rule 13
        r'Clause\s+\([a-z]\)',                                             # Clause (d)
        r'Sub[- ]?section\s+\d+',                                          # Sub-section 3
        r'Sub[- ]?clause\s+\([a-z]\)',                                     # Sub-clause (i)
        r'Schedule\s+[IVX]+',                                              # Schedule I
        r'Form\s+[IVX]+',                                                  # Form I
        r'[A-Z]{2,}\s+\d{4}',                                              # PATENTS ACT 1970
        r'Act\s+\d+\s+of\s+\d{4}',                                         # Act 15 of 2005
    ]
    
    def tokenize(self, text: str) -> List[str]:
        # Protect legal citations
        protected = []
        for pattern in self.LEGAL_PATTERNS:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for m in matches:
                protected.append((m.start(), m.end(), m.group().replace(' ', '_')))
        
        # Replace with protected tokens
        # ... implementation
        
        # Standard tokenization on remaining
        tokens = self._standard_tokenize(protected_text)
        
        # Restore protected tokens
        return self._restore_protected(tokens, protected)
```

---

## 4. Dense Retrieval

### 4.1 Embedding Model Requirements

| Requirement | Specification |
|-------------|---------------|
| **Multilingual** | English + Hindi + 10+ Indian languages |
| **Legal domain** | Fine-tuned on legal corpus preferred |
| **Context length** | ≥ 512 tokens (8192 preferred) |
| **Dimension** | 768-1024 (balance quality/speed) |
| **Inference speed** | < 50ms per query on CPU |

### 4.2 Model Candidates (Prioritized)

| Model | Dim | Languages | Legal Fine-tune | Speed | Status |
|-------|-----|-----------|-----------------|-------|--------|
| **bge-m3** | 1024 | 100+ | No | Medium | **CORE** |
| **jina-embeddings-v3** | 1024 | 89 | No | Fast | **CORE** |
| **mxbai-embed-large-v1** | 1024 | English | No | Fast | **CORE** (English only) |
| **legal-xlm-roberta** | 768 | 100+ | Yes | Slow | **OPTIONAL** |
| **indic-bert** | 768 | 12 Indian | No | Medium | **EXPERIMENTAL** |

**Primary: bge-m3** (best multilingual, good legal performance, supports dense+sparse+colbert)

### 4.3 Vector Index: HNSW

```python
class LegalVectorIndex:
    def __init__(self):
        self.index = hnswlib.Index(space='cosine', dim=1024)
        # HNSW parameters optimized for recall
        self.index.init_index(
            max_elements=10_000_000,
            ef_construction=200,    # Higher = better recall, slower build
            M=32,                   # Higher = better recall, more memory
            allow_replace_deleted=True
        )
        self.index.set_ef(100)      # Query-time ef (higher = better recall)
        
        # Metadata store (separate for filtering)
        self.metadata_store = MetadataStore()
    
    def add_chunks(self, chunks: List[LegalChunk], embeddings: np.ndarray):
        """Add chunks with metadata for pre-filtering."""
        ids = np.arange(len(chunks)) + self.current_count
        
        # Add to vector index
        self.index.add_items(embeddings, ids)
        
        # Store metadata for pre-filtering
        for i, chunk in enumerate(chunks):
            self.metadata_store.add(ids[i], {
                'chunk_id': chunk.chunk_id,
                'document_id': chunk.document_id,
                'jurisdiction': chunk.hierarchy.jurisdiction,
                'authority_tier': chunk.source_provenance.authority_tier.value,
                'doc_type': chunk.chunk_type.value,
                'language': chunk.language,
                'effective_date': chunk.effective_date.isoformat() if chunk.effective_date else None,
                'amendment_status': chunk.amendment_status.value,
            })
        
        self.current_count += len(chunks)
    
    def search(self, query_embedding: np.ndarray, 
               filters: MetadataFilters, k: int) -> List[RetrievalResult]:
        """
        Two-stage: metadata pre-filter → vector search.
        """
        # Stage 1: Get allowed IDs from metadata filter
        allowed_ids = self.metadata_store.filter(filters)
        
        if not allowed_ids:
            return []
        
        # Stage 2: Vector search with ID filter
        # HNSW supports filtering via 'ids' parameter in newer versions
        # Fallback: search larger K and filter post-hoc
        search_k = min(k * 10, len(allowed_ids))
        
        labels, distances = self.index.knn_query(
            query_embedding, k=search_k, filter=lambda x: x in allowed_ids
        )
        
        # Convert to results
        results = []
        for idx, dist in zip(labels[0], distances[0]):
            if idx in allowed_ids:
                meta = self.metadata_store.get(idx)
                results.append(RetrievalResult(
                    chunk_id=meta['chunk_id'],
                    score=1.0 - dist,  # Cosine similarity
                    metadata=meta
                ))
                if len(results) >= k:
                    break
        
        return results
```

### 4.4 Metadata Pre-Filtering (Critical for Jurisdiction Isolation)

```python
@dataclass
class MetadataFilters:
    # Jurisdiction (MANDATORY - hard filter)
    jurisdictions: List[Jurisdiction] = field(default_factory=list)
    exclude_jurisdictions: List[Jurisdiction] = field(default_factory=list)
    
    # Document type
    doc_types: Optional[List[DocType]] = None
    exclude_doc_types: Optional[List[DocType]] = None
    
    # Authority tier (minimum)
    min_authority_tier: AuthorityTier = AuthorityTier.TIER_4
    
    # Temporal
    as_of_date: Optional[date] = None
    effective_after: Optional[date] = None
    effective_before: Optional[date] = None
    
    # Language
    languages: Optional[List[str]] = None
    
    # Amendment status
    amendment_statuses: Optional[List[AmendmentStatus]] = None
    
    # Source IDs
    source_ids: Optional[List[str]] = None

class MetadataStore:
    """In-memory / Redis-backed metadata index for fast filtering."""
    
    def __init__(self):
        # Inverted indexes for each filterable field
        self.by_jurisdiction: Dict[Jurisdiction, Set[int]] = defaultdict(set)
        self.by_doc_type: Dict[DocType, Set[int]] = defaultdict(set)
        self.by_authority_tier: Dict[int, Set[int]] = defaultdict(set)
        self.by_language: Dict[str, Set[int]] = defaultdict(set)
        self.by_source: Dict[str, Set[int]] = defaultdict(set)
        # B-tree for temporal
        self.by_effective_date: SortedList = SortedList(key=lambda x: x[0])
        
        self.chunk_metadata: Dict[int, Dict] = {}
    
    def add(self, chunk_id: int, metadata: Dict):
        self.chunk_metadata[chunk_id] = metadata
        self.by_jurisdiction[metadata['jurisdiction']].add(chunk_id)
        self.by_doc_type[metadata['doc_type']].add(chunk_id)
        self.by_authority_tier[metadata['authority_tier']].add(chunk_id)
        self.by_language[metadata['language']].add(chunk_id)
        self.by_source[metadata['source_id']].add(chunk_id)
        if metadata['effective_date']:
            self.by_effective_date.add((metadata['effective_date'], chunk_id))
    
    def filter(self, filters: MetadataFilters) -> Set[int]:
        """Apply all filters as set intersections."""
        candidate_sets = []
        
        # Jurisdiction (MANDATORY - start with this)
        if filters.jurisdictions:
            jur_set = set()
            for jur in filters.jurisdictions:
                jur_set.update(self.by_jurisdiction.get(jur, set()))
            candidate_sets.append(jur_set)
        else:
            # No jurisdiction specified = all jurisdictions (but this should be rare)
            candidate_sets.append(set(self.chunk_metadata.keys()))
        
        # Exclude jurisdictions
        if filters.exclude_jurisdictions:
            exclude_set = set()
            for jur in filters.exclude_jurisdictions:
                exclude_set.update(self.by_jurisdiction.get(jur, set()))
            candidate_sets[0] -= exclude_set
        
        # Document type
        if filters.doc_types:
            dt_set = set()
            for dt in filters.doc_types:
                dt_set.update(self.by_doc_type.get(dt, set()))
            candidate_sets.append(dt_set)
        
        # Authority tier (minimum)
        if filters.min_authority_tier != AuthorityTier.TIER_4:
            at_set = set()
            for tier_val in range(filters.min_authority_tier.value, 5):
                at_set.update(self.by_authority_tier.get(tier_val, set()))
            candidate_sets.append(at_set)
        
        # Language
        if filters.languages:
            lang_set = set()
            for lang in filters.languages:
                lang_set.update(self.by_language.get(lang, set()))
            candidate_sets.append(lang_set)
        
        # Temporal: as_of_date
        if filters.as_of_date:
            # Binary search in sorted list
            temporal_set = set(
                cid for eff_date, cid in self.by_effective_date 
                if eff_date <= filters.as_of_date
            )
            candidate_sets.append(temporal_set)
        
        # Intersection of all filters
        if not candidate_sets:
            return set()
        
        result = candidate_sets[0]
        for s in candidate_sets[1:]:
            result &= s
            if not result:
                break
        
        return result
```

---

## 5. Hybrid Fusion: Reciprocal Rank Fusion (RRF)

### 5.1 Why RRF

| Method | Pros | Cons | Decision |
|--------|------|------|----------|
| **RRF** | Parameter-free, robust, no score normalization | Less tunable | **CORE** |
| **Weighted Score Fusion** | Tunable weights | Needs score calibration | Optional |
| **Learned Fusion** | Optimal | Needs training data, brittle | Experimental |
| **Concatenation** | Simple | No ranking logic | Not recommended |

### 5.2 RRF with Authority Weighting

```python
def reciprocal_rank_fusion(
    sparse_results: List[RetrievalResult],
    dense_results: List[RetrievalResult],
    k: int = 60,                    # RRF constant (standard)
    authority_weights: Dict[AuthorityTier, float] = None
) -> List[FusedResult]:
    """
    RRF with authority-aware weighting.
    
    Score = Σ (weight / (k + rank))
    """
    if authority_weights is None:
        authority_weights = {
            AuthorityTier.TIER_1: 1.0,
            AuthorityTier.TIER_2: 0.8,
            AuthorityTier.TIER_3: 0.6,
            AuthorityTier.TIER_4: 0.4,
        }
    
    # Build rank maps
    sparse_ranks = {r.chunk_id: i+1 for i, r in enumerate(sparse_results)}
    dense_ranks = {r.chunk_id: i+1 for i, r in enumerate(dense_results)}
    
    # All unique chunk IDs
    all_chunk_ids = set(sparse_ranks.keys()) | set(dense_ranks.keys())
    
    # Get authority tier for each chunk (from metadata)
    chunk_authority = get_authority_tiers(all_chunk_ids)
    
    # Compute RRF scores
    fused_scores = {}
    for chunk_id in all_chunk_ids:
        score = 0.0
        
        # Sparse contribution
        if chunk_id in sparse_ranks:
            weight = authority_weights.get(chunk_authority[chunk_id], 0.5)
            score += weight / (k + sparse_ranks[chunk_id])
        
        # Dense contribution
        if chunk_id in dense_ranks:
            weight = authority_weights.get(chunk_authority[chunk_id], 0.5)
            score += weight / (k + dense_ranks[chunk_id])
        
        fused_scores[chunk_id] = score
    
    # Sort and return top K
    sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    
    return [FusedResult(chunk_id=cid, fused_score=score) for cid, score in sorted_chunks]
```

### 5.3 Fusion Variants for Experimentation

```python
# EXPERIMENTAL: Weighted fusion with calibrated scores
def weighted_fusion(sparse_results, dense_results, 
                    sparse_weight=0.5, dense_weight=0.5):
    # Requires score calibration (e.g., min-max per query)
    pass

# EXPERIMENTAL: Learned fusion (logistic regression on features)
def learned_fusion(sparse_results, dense_results, query_features):
    # Features: sparse_score, dense_score, authority_tier, jurisdiction_match, etc.
    pass
```

---

## 6. Cross-Encoder Reranking

### 6.1 Model Selection

| Model | Params | Languages | Legal Performance | Speed | Status |
|-------|--------|-----------|-------------------|-------|--------|
| **bge-reranker-v2-m3** | 600M | 100+ | Excellent | ~100ms/query | **CORE** |
| **jina-reranker-v2-base** | 135M | 89 | Good | ~50ms/query | **OPTIONAL** |
| **cross-encoder/ms-marco-MiniLM-L6** | 22M | English | Good | ~20ms/query | **FALLBACK** |
| **Legal-BERT reranker** | 110M | English | Best legal | ~150ms/query | **EXPERIMENTAL** |

**Primary: bge-reranker-v2-m3** (multilingual, strong legal performance, reasonable speed)

### 6.2 Hierarchical Reranking Input Construction

```python
class HierarchicalReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model = CrossEncoder(model_name, max_length=512)
    
    def rerank(self, query: str, candidates: List[LegalChunk], 
               top_k: int = 20) -> List[RerankedResult]:
        """
        Construct input pairs with hierarchical context.
        """
        pairs = []
        for chunk in candidates:
            # Build hierarchical context string
            context = self._build_hierarchical_context(chunk)
            
            # Input format: [QUERY] [SEP] [HIERARCHY] [SEP] [CHUNK_TEXT]
            pair = f"{query} [SEP] {context} [SEP] {chunk.text_normalized[:1000]}"
            pairs.append(pair)
        
        # Batch inference
        scores = self.model.predict(pairs, batch_size=16)
        
        # Combine with original metadata
        results = []
        for chunk, score in zip(candidates, scores):
            results.append(RerankedResult(
                chunk=chunk,
                rerank_score=float(score),
                original_score=chunk.score
            ))
        
        # Sort by rerank score
        results.sort(key=lambda x: x.rerank_score, reverse=True)
        
        return results[:top_k]
    
    def _build_hierarchical_context(self, chunk: LegalChunk) -> str:
        """Build context showing legal hierarchy for the cross-encoder."""
        parts = []
        
        # Act level
        parts.append(f"Act: {chunk.hierarchy.act_short_title}")
        
        # Chapter/Part
        if chunk.hierarchy.chapter:
            parts.append(f"Chapter: {chunk.hierarchy.chapter}")
        if chunk.hierarchy.part:
            parts.append(f"Part: {chunk.hierarchy.part}")
        
        # Section hierarchy
        if chunk.hierarchy.section:
            parts.append(f"Section: {chunk.hierarchy.section}")
        if chunk.hierarchy.subsection:
            parts.append(f"Subsection: {chunk.hierarchy.subsection}")
        if chunk.hierarchy.clause:
            parts.append(f"Clause: {chunk.hierarchy.clause}")
        
        # Chunk type
        parts.append(f"Type: {chunk.chunk_type.value}")
        
        # Authority
        parts.append(f"Authority: Tier {chunk.source_provenance.authority_tier.value}")
        
        return " | ".join(parts)
```

### 6.3 Reranking with Legal Reasoning Prompts

```python
# EXPERIMENTAL: LLM-based reranking for complex queries
class LLMReranker:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def rerank(self, query: str, candidates: List[LegalChunk], top_k: int = 10):
        """Use LLM to score relevance with legal reasoning."""
        # Only for complex queries (multi-hop, interpretation)
        # Too expensive for every query
        pass
```

---

## 7. Evidence Selection

### 7.1 Maximal Marginal Relevance (MMR) with Authority

```python
class EvidenceSelector:
    def __init__(self):
        self.lambda_mmr = 0.7          # Relevance vs diversity tradeoff
        self.dedup_threshold = 0.95    # Cosine similarity for deduplication
        self.max_evidence = 10         # Final evidence count
        self.min_authority_tier = AuthorityTier.TIER_2
    
    def select(self, 
               reranked: List[RerankedResult], 
               query_embedding: np.ndarray,
               chunk_embeddings: Dict[str, np.ndarray]) -> List[SelectedEvidence]:
        
        # 1. Deduplication (exact/near-duplicate removal)
        unique = self._deduplicate(reranked, chunk_embeddings)
        
        # 2. MMR selection with authority bias
        selected = []
        candidate_embeddings = {r.chunk.chunk_id: chunk_embeddings[r.chunk.chunk_id] 
                               for r in unique}
        
        for _ in range(min(self.max_evidence, len(unique))):
            best_score = -1
            best_candidate = None
            
            for candidate in unique:
                if candidate.chunk.chunk_id in [s.chunk_id for s in selected]:
                    continue
                
                # Relevance score (rerank score)
                relevance = candidate.rerank_score
                
                # Authority bonus
                authority_bonus = self._authority_bonus(candidate.chunk)
                
                # Diversity penalty (max similarity to already selected)
                diversity_penalty = 0
                if selected:
                    cand_emb = candidate_embeddings[candidate.chunk.chunk_id]
                    max_sim = max(
                        cosine_similarity(cand_emb, candidate_embeddings[s.chunk_id])
                        for s in selected
                    )
                    diversity_penalty = max_sim
                
                # MMR score
                mmr_score = (self.lambda_mmr * relevance + 
                            (1 - self.lambda_mmr) * (1 - diversity_penalty) +
                            0.1 * authority_bonus)
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(SelectedEvidence(
                    chunk=best_candidate.chunk,
                    relevance_score=best_candidate.rerank_score,
                    mmr_score=best_score,
                    citation_id=len(selected) + 1  # Sequential citation IDs
                ))
        
        return selected
    
    def _deduplicate(self, reranked: List[RerankedResult], 
                     embeddings: Dict[str, np.ndarray]) -> List[RerankedResult]:
        """Remove near-duplicate chunks (cosine > 0.95)."""
        unique = []
        seen_embeddings = []
        
        for result in reranked:
            emb = embeddings[result.chunk.chunk_id]
            
            is_duplicate = False
            for seen_emb in seen_embeddings:
                if cosine_similarity(emb, seen_emb) > self.dedup_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(result)
                seen_embeddings.append(emb)
        
        return unique
    
    def _authority_bonus(self, chunk: LegalChunk) -> float:
        tier = chunk.source_provenance.authority_tier
        return {1: 0.3, 2: 0.2, 3: 0.1, 4: 0.0}[tier.value]
```

---

## 8. Retrieval Confidence & Abstention

### 8.1 Confidence Scoring

```python
@dataclass
class RetrievalConfidence:
    overall: float              # 0.0 - 1.0
    signals: ConfidenceSignals
    abstain: bool               # True if overall < threshold
    abstention_reason: Optional[str]

@dataclass
class ConfidenceSignals:
    candidate_count: int              # Total candidates after fusion
    top_rerank_score: float           # Best rerank score
    score_distribution: Dict[str, float]  # Mean, std, gap between top-1 and top-2
    authority_purity: float           # Fraction of Tier 1/2 in top 10
    jurisdiction_purity: float        # Fraction matching target jurisdiction
    temporal_currency: float          # Fraction of chunks currently effective
    coverage_breadth: float           # Number of distinct acts/sections covered
    query_coverage: float             # Fraction of query terms matched

def compute_retrieval_confidence(
    fused_results: List[FusedResult],
    reranked_results: List[RerankedResult],
    selected_evidence: List[SelectedEvidence],
    query_analysis: QueryAnalysis,
    filters: MetadataFilters
) -> RetrievalConfidence:
    
    signals = ConfidenceSignals(
        candidate_count=len(fused_results),
        top_rerank_score=reranked_results[0].rerank_score if reranked_results else 0.0,
        score_distribution=compute_score_stats([r.rerank_score for r in reranked_results]),
        authority_purity=compute_authority_purity(reranked_results[:10]),
        jurisdiction_purity=compute_jurisdiction_purity(reranked_results[:10], filters.jurisdictions),
        temporal_currency=compute_temporal_currency(reranked_results[:10], filters.as_of_date),
        coverage_breadth=compute_coverage_breadth(selected_evidence),
        query_coverage=compute_query_coverage(query_analysis, selected_evidence)
    )
    
    # Weighted combination (tunable)
    weights = {
        'top_rerank_score': 0.30,
        'authority_purity': 0.20,
        'jurisdiction_purity': 0.20,
        'temporal_currency': 0.10,
        'coverage_breadth': 0.10,
        'query_coverage': 0.10,
    }
    
    overall = (
        weights['top_rerank_score'] * signals.top_rerank_score +
        weights['authority_purity'] * signals.authority_purity +
        weights['jurisdiction_purity'] * signals.jurisdiction_purity +
        weights['temporal_currency'] * signals.temporal_currency +
        weights['coverage_breadth'] * signals.coverage_breadth +
        weights['query_coverage'] * signals.query_coverage
    )
    
    # Abstention threshold
    ABSTENTION_THRESHOLD = 0.4
    abstain = overall < ABSTENTION_THRESHOLD
    
    reason = None
    if abstain:
        if signals.top_rerank_score < 0.3:
            reason = "No highly relevant evidence found"
        elif signals.jurisdiction_purity < 0.5:
            reason = "Insufficient evidence from target jurisdiction"
        elif signals.authority_purity < 0.3:
            reason = "Insufficient authoritative sources"
        elif signals.candidate_count < 5:
            reason = "Too few candidate documents retrieved"
        else:
            reason = "Overall retrieval confidence below threshold"
    
    return RetrievalConfidence(
        overall=overall,
        signals=signals,
        abstain=abstain,
        abstention_reason=reason
    )
```

---

## 9. Retrieval Fallbacks

### 9.1 Fallback Chain

```python
class RetrievalOrchestrator:
    def __init__(self):
        self.stages = [
            self._hybrid_retrieval,       # Primary: BM25 + Dense + RRF + Rerank
            self._sparse_only_retrieval,  # Fallback 1: BM25 only
            self._dense_only_retrieval,   # Fallback 2: Dense only
            self._broadened_filters,      # Fallback 3: Relax metadata filters
            self._cross_jurisdiction,     # Fallback 4: Allow other jurisdictions (with warning)
        ]
    
    def retrieve(self, query: str, analysis: QueryAnalysis) -> RetrievalOutput:
        filters = self._build_filters(analysis)
        
        for i, stage in enumerate(self.stages):
            try:
                result = stage(query, analysis, filters)
                if result.confidence.overall >= 0.3:  # Minimum viable
                    result.fallback_stage = i
                    return result
            except Exception as e:
                logger.warning(f"Retrieval stage {i} failed: {e}")
                continue
        
        # All failed - return empty with abstention
        return RetrievalOutput(
            evidence=[],
            confidence=RetrievalConfidence(overall=0.0, signals=..., abstain=True, 
                                           abstention_reason="All retrieval stages failed"),
            fallback_stage=len(self.stages)
        )
```

### 9.2 Fallback Details

| Fallback Stage | Trigger | Modification | Warning to User |
|----------------|---------|--------------|-----------------|
| 0: Hybrid | - | Full pipeline | None |
| 1: Sparse only | Dense index down | BM25 only | "Using keyword search only" |
| 2: Dense only | BM25 index down | Vector only | "Using semantic search only" |
| 3: Broadened filters | Low candidate count | Relax authority/temporal | "Expanded search to secondary sources" |
| 4: Cross-jurisdiction | No results | Allow other jurisdictions | ⚠️ "Showing results from other jurisdictions - verify applicability" |

---

## 10. Multilingual Retrieval

### 10.1 Strategy: Translate Query + Multilingual Embeddings

```python
class MultilingualRetriever:
    def __init__(self):
        self.embedder = MultilingualEmbedder("bge-m3")  # Supports 100+ langs
        self.translator = TranslationService()          # For query translation
    
    def retrieve(self, query: str, analysis: QueryAnalysis) -> RetrievalOutput:
        detected_lang = analysis.detected_language
        
        if detected_lang == 'en':
            # Native English retrieval
            return self._retrieve_monolingual(query, 'en', analysis)
        
        # Strategy A: Translate query to English, retrieve in English corpus
        en_query = self.translator.translate(query, detected_lang, 'en')
        en_results = self._retrieve_monolingual(en_query, 'en', analysis)
        
        # Strategy B: Retrieve directly in multilingual space
        multi_results = self._retrieve_monolingual(query, detected_lang, analysis)
        
        # Strategy C: Both + merge (CORE for Phase 3+)
        return self._merge_multilingual_results(en_results, multi_results, analysis)
```

### 10.2 Cross-Lingual Considerations

| Aspect | Approach |
|--------|----------|
| **Legal terminology** | Preserve English legal terms in translation (Section, Act, Rule) |
| **Query expansion** | Add English synonyms for Indian language queries |
| **Embedding space** | bge-m3 aligns languages well; no separate indices needed |
| **Citation preservation** | Citations remain in original language (English) |

---

## 11. Caching Strategy

### 11.1 Cache Layers

| Layer | What | TTL | Invalidation |
|-------|------|-----|--------------|
| **Query Embedding** | Query → embedding | 24h | Model version change |
| **Sparse Results** | Query terms → BM25 top-K | 1h | Corpus update |
| **Dense Results** | Query embedding → vector top-K | 1h | Corpus update / index rebuild |
| **Reranked Results** | Query + candidate IDs → rerank scores | 30min | Model version change |
| **Final Evidence** | Full pipeline output | 15min | Any upstream change |

### 11.2 Cache Keys

```
cache_key = hash(f"{query}:{jurisdictions}:{doc_types}:{authority_tier}:{as_of_date}:{lang}")
```

---

## 12. Tunable Parameters Summary

| Parameter | Default | Range | Tuning Method |
|-----------|---------|-------|---------------|
| `k_sparse` | 100 | 50-200 | Recall@100 on benchmark |
| `k_dense` | 100 | 50-200 | Recall@100 on benchmark |
| `k_fused` | 50 | 20-100 | Reranker input quality |
| `k_rerank` | 20 | 10-50 | Precision@K vs latency |
| `k_final` | 10 | 5-20 | Context window / answer quality |
| `bm25_k1` | 1.6 | 1.2-2.0 | Legal term frequency |
| `bm25_b` | 0.75 | 0.5-0.9 | Length normalization |
| `rrf_k` | 60 | 30-100 | Fusion quality |
| `authority_weight_t1` | 1.0 | 0.8-1.2 | Authority influence |
| `authority_weight_t2` | 0.8 | 0.6-1.0 | Authority influence |
| `mmr_lambda` | 0.7 | 0.5-0.9 | Diversity vs relevance |
| `dedup_threshold` | 0.95 | 0.90-0.98 | Duplicate removal |
| `confidence_threshold` | 0.4 | 0.3-0.5 | Abstention rate vs accuracy |
| `hnsw_ef` | 100 | 50-200 | Recall vs latency |
| `rerank_batch_size` | 16 | 8-32 | GPU memory / latency |

---

## 13. Evaluation Methodology

### 13.1 Retrieval Benchmark Dataset

```
Benchmark queries with:
- query_id
- query_text
- language
- jurisdiction
- intent_category
- relevant_chunk_ids (ground truth)
- relevant_sections (ground truth)
- answerability (ANSWERABLE / UNSURE / UNANSWERABLE)
- required_authority_tier (min tier needed)
```

### 13.2 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Recall@10** | > 0.85 | Fraction of relevant chunks in top 10 |
| **Recall@20** | > 0.95 | Fraction of relevant chunks in top 20 |
| **MRR@10** | > 0.65 | Mean Reciprocal Rank |
| **nDCG@10** | > 0.70 | Normalized Discounted Cumulative Gain |
| **Hit Rate@1** | > 0.40 | Top-1 is relevant |
| **Jurisdiction Purity@10** | 1.0 | No wrong-jurisdiction in top 10 |
| **Authority Purity@10** | > 0.90 | Tier 1/2 fraction in top 10 |
| **Latency p50** | < 2s | End-to-end |
| **Latency p95** | < 5s | End-to-end |

---

## 14. Failure Modes & Mitigations

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| **Empty candidate pool** | K_fused = 0 | Fallback to broadened filters |
| **All low rerank scores** | top_rerank_score < 0.2 | Abstain, suggest reformulation |
| **Jurisdiction contamination** | jurisdiction_purity < 1.0 | Hard filter bug - block deployment |
| **Stale embeddings** | Version mismatch | Re-index on corpus update |
| **Cross-encoder timeout** | > 2s | Fallback to fused scores only |
| **Memory OOM** | HNSW index too large | Shard index, use disk-backed |

---

## 15. Open Research Questions

| ID | Question | Status |
|----|----------|--------|
| ORQ-27 | Optimal RRF k for legal (60 vs 30 vs 100)? | Benchmark needed |
| ORQ-28 | Cross-encoder vs LLM reranker for complex legal queries? | Experiment planned |
| ORQ-29 | Does query decomposition improve multi-hop retrieval? | Phase 3 design |
| ORQ-30 | Best multilingual strategy: translate-query vs multilingual-embed? | Experiment planned |
| ORQ-31 | Optimal MMR lambda for legal diversity? | 0.5 vs 0.7 vs 0.9 |
| ORQ-32 | Should we use separate indices per jurisdiction? | Architecture decision |
| ORQ-33 | Late interaction (ColBERT) vs cross-encoder for reranking? | Experimental |

---

## 16. Integration Points

### 16.1 Input from Previous Phases

| Phase | Input |
|-------|-------|
| Phase 3 | QueryAnalysis (classification, decomposition, jurisdiction, formulation) |
| Phase 4 | LegalChunk objects with full metadata |
| Phase 5 | Chunking strategy determines retrieval units |

### 16.2 Output to Next Phases

| Phase | Output |
|-------|--------|
| Phase 7 | Retrieved chunks with scores for graph enhancement |
| Phase 10 | Evidence set with citation IDs for grounded generation |
| Phase 11 | Authority tier distribution for source weighting |
| Phase 17 | Retrieval metrics for evaluation |

---

## 17. Summary: Retrieval Architecture Decision

| Component | Role | Implementation Priority |
|-----------|------|------------------------|
| **Legal BM25** | **CORE** | Phase 1 (MVP) |
| **Multilingual Dense (bge-m3)** | **CORE** | Phase 1 (MVP) |
| **Metadata Pre-filtering (Jurisdiction)** | **CORE** | Phase 1 (MVP) |
| **RRF Fusion + Authority Weight** | **CORE** | Phase 1 (MVP) |
| **Cross-Encoder Reranker (bge-reranker-v2-m3)** | **CORE** | Phase 1 (MVP) |
| **MMR Evidence Selection** | **CORE** | Phase 1 (MVP) |
| **Retrieval Confidence + Abstention** | **CORE** | Phase 1 (MVP) |
| **Fallback Chain** | **CORE** | Phase 1 (MVP) |
| **Caching Layer** | **OPTIONAL** | Phase 2 |
| **Learned Fusion** | **EXPERIMENTAL** | Phase 3+ |
| **ColBERT/Late Interaction** | **EXPERIMENTAL** | Phase 3+ |
| **LLM Reranker** | **EXPERIMENTAL** | Phase 3+ |

---

## 18. Next Phase: Phase 7 - Knowledge Graph Architecture

The retrieval engine outputs **evidence chunks with full metadata**. Phase 7 will design how a knowledge graph can enhance retrieval by:
- Entity linking from chunks to graph nodes
- Graph traversal for multi-hop reasoning
- Relationship-aware retrieval (AMENDS, IMPLEMENTS, SUPERSEDES)
- Conflict detection between legal provisions

**Key interface**: Retrieval engine can optionally call Graph Retrieval as an additional evidence source, merged via RRF.