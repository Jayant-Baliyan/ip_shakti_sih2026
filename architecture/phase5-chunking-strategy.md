# Phase 5: Chunking Strategy Architecture

## Overview

This document designs the optimal chunking strategy for legal/regulatory documents in the IP-SAKTI system. Unlike generic RAG, legal documents have strict hierarchical structure that must be preserved for accurate citations and jurisdictional integrity.

---

## 1. Requirements for Legal Chunking

### 1.1 Functional Requirements

| Requirement | Description |
|------------|-------------|
| **FR-CHK-01** | Preserve legal hierarchy: Act → Chapter → Part → Section → Subsection → Clause → Subclause |
| **FR-CHK-02** | Enable citation traceability: embedding → chunk → section → document → authoritative source |
| **FR-CHK-03** | Support cross-reference resolution (e.g., "as per Section 3(d) of the Patents Act") |
| **FR-CHK-04** | Handle amendments: new/amended/repealed sections must be distinguishable |
| **FR-CHK-05** | Support multilingual chunks (English + Indian languages) |
| **FR-CHK-06** | Handle tabular data (schedules, fee tables, classification tables) |
| **FR-CHK-07** | Handle definitions sections specially (high retrieval value) |
| **FR-CHK-08** | Preserve footnotes and marginal notes |

### 1.2 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| **NFR-CHK-01** | Chunk size: 512-2048 tokens (configurable per document type) |
| **NFR-CHK-02** | Overlap: 10-20% for context continuity |
| **NFR-CHK-03** | No section split across chunks unless section > max_tokens |
| **NFR-CHK-04** | Deterministic chunk IDs for versioning |
| **NFR-CHK-05** | Processing latency < 5s per 100-page document |

---

## 2. Chunking Strategy Comparison

### 2.1 Fixed Token Chunking

| Aspect | Assessment |
|--------|------------|
| **Pros** | Simple, predictable size, easy to implement |
| **Cons** | **Breaks legal hierarchy**, splits sections mid-sentence, loses context, citations become ambiguous |
| **Verdict** | ❌ **NOT WORTH IT** for legal documents |

### 2.2 Semantic Chunking (Embedding-based)

| Aspect | Assessment |
|--------|------------|
| **Pros** | Groups semantically similar content |
| **Cons** | Unpredictable boundaries, may split legal sections, no hierarchy preservation |
| **Verdict** | ❌ **NOT WORTH IT** as primary strategy |

### 2.3 Legal-Section Chunking (Primary Strategy)

| Aspect | Assessment |
|--------|------------|
| **Pros** | Preserves legal hierarchy, deterministic boundaries, natural citation units |
| **Cons** | Variable size (some sections very long/short), may exceed token limits |
| **Verdict** | ✅ **CORE STRATEGY** |

### 2.4 Hierarchical Chunking (Enhanced Legal-Section)

| Aspect | Assessment |
|--------|------------|
| **Pros** | Full hierarchy path in metadata, enables hierarchical retrieval |
| **Cons** | More complex, larger metadata |
| **Verdict** | ✅ **CORE ENHANCEMENT** |

### 2.5 Parent-Child Chunking

| Aspect | Assessment |
|--------|------------|
| **Pros** | Small child chunks for retrieval, large parent for context |
| **Cons** | Complexity in mapping, potential duplication |
| **Verdict** | ✅ **OPTIONAL MODULE** for very long sections |

### 2.6 Sentence-Window Chunking

| Aspect | Assessment |
|--------|------------|
| **Pros** | Fine-grained, good for precise quotes |
| **Cons** | Loses legal structure, high chunk count, citation ambiguity |
| **Verdict** | ❌ **NOT WORTH IT** (legal hierarchy superior) |

### 2.7 Overlapping Chunks

| Aspect | Assessment |
|--------|------------|
| **Pros** | Context continuity across boundaries |
| **Cons** | Duplication, retrieval noise |
| **Verdict** | ✅ **CORE** (10-20% overlap at section boundaries) |

### 2.8 Recursive Structures (Tables, Schedules)

| Aspect | Assessment |
|--------|------------|
| **Pros** | Handles complex nested structures |
| **Cons** | Specialized parsing needed |
| **Verdict** | ✅ **CORE** (separate table chunker) |

---

## 3. Optimal Legal-RAG Chunk Representation

### 3.1 Chunk Data Structure

```python
@dataclass
class LegalChunk:
    # Identity
    chunk_id: str                    # Deterministic: {doc_id}#{section_path}#{chunk_index}
    document_id: str                 # Source document identifier
    document_version: str            # Version hash/timestamp
    
    # Hierarchy Path (required for all chunks)
    hierarchy: HierarchyPath
    
    # Content
    text: str                        # Main text content
    text_normalized: str             # Normalized for embedding (citations expanded)
    
    # Metadata
    chunk_type: ChunkType            # SECTION, DEFINITION, TABLE, SCHEDULE, FOOTNOTE, PREAMBLE
    token_count: int
    char_start: int                  # Character offset in source document
    char_end: int
    
    # Citations
    citations: List[CitationRef]     # Internal citations within this chunk
    
    # Multilingual
    language: str                    # ISO 639-1 code
    translations: Dict[str, str]     # lang_code -> translated text
    
    # Versioning
    amendment_status: AmendmentStatus # ORIGINAL, AMENDED, INSERTED, REPEALED
    effective_date: Optional[date]
    source_provenance: SourceProvenance
    
    # Embeddings (populated after indexing)
    embedding: Optional[List[float]] = None
    sparse_vector: Optional[Dict[int, float]] = None

@dataclass
class HierarchyPath:
    act_id: str                      # e.g., "A1970-39"
    act_short_title: str             # e.g., "Patents Act, 1970"
    chapter: Optional[str] = None    # e.g., "Chapter II"
    part: Optional[str] = None       # e.g., "Part A"
    section: Optional[str] = None    # e.g., "Section 3"
    subsection: Optional[str] = None # e.g., "Subsection (1)"
    clause: Optional[str] = None     # e.g., "Clause (d)"
    subclause: Optional[str] = None  # e.g., "Subclause (i)"
    
    def to_citation_string(self) -> str:
        """Generate standard legal citation"""
        parts = [self.act_short_title]
        if self.chapter: parts.append(self.chapter)
        if self.part: parts.append(self.part)
        if self.section: parts.append(self.section)
        if self.subsection: parts.append(self.subsection)
        if self.clause: parts.append(self.clause)
        if self.subclause: parts.append(self.subclause)
        return " → ".join(parts)
    
    def to_chunk_id_suffix(self) -> str:
        """Generate deterministic suffix for chunk_id"""
        parts = []
        if self.chapter: parts.append(f"ch{self.chapter}")
        if self.part: parts.append(f"pt{self.part}")
        if self.section: parts.append(f"s{self.section}")
        if self.subsection: parts.append(f"ss{self.subsection}")
        if self.clause: parts.append(f"cl{self.clause}")
        if self.subclause: parts.append(f"scl{self.subclause}")
        return "_".join(parts) or "root"

@dataclass
class CitationRef:
    cited_act: str
    cited_section: str
    cited_text: str                  # The citing text (e.g., "Section 3(d)")
    citation_type: CitationType      # INTERNAL, EXTERNAL, CASE_LAW, TREATY
```

### 3.2 Chunk Type Taxonomy

| ChunkType | Description | Retrieval Priority | Example |
|-----------|-------------|-------------------|---------|
| **SECTION** | Standard section/subsection | High | Section 3(d) Patents Act |
| **DEFINITION** | Definitions clause | **Highest** | "invention" definition |
| **TABLE** | Fee tables, classification tables | Medium | Schedule I fees |
| **SCHEDULE** | Full schedule | Medium | Schedule of GIs |
| **FOOTNOTE** | Footnotes/marginal notes | Low | "Inserted by Act 15 of 2005" |
| **PREAMBLE** | Preamble/Statement of Objects | Low | Preamble to Act |
| **AMENDMENT_NOTE** | Amendment history note | Medium | "Section 3 substituted by..." |

---

## 4. Chunking Algorithm

### 4.1 Primary Algorithm: Hierarchical Section Chunking

```python
def chunk_legal_document(document: LegalDocument) -> List[LegalChunk]:
    """
    Main chunking pipeline for legal documents.
    Preserves hierarchy, handles oversized sections, generates citations.
    """
    chunks = []
    
    # Step 1: Parse document structure
    structure = parse_legal_hierarchy(document)
    
    # Step 2: Extract definitions separately (high value)
    def_chunks = extract_definitions(structure, document)
    chunks.extend(def_chunks)
    
    # Step 3: Extract tables/schedules separately
    table_chunks = extract_tables_and_schedules(structure, document)
    chunks.extend(table_chunks)
    
    # Step 4: Chunk regular sections hierarchically
    section_chunks = chunk_sections_hierarchically(structure, document)
    chunks.extend(section_chunks)
    
    # Step 5: Handle footnotes/amendment notes
    footnote_chunks = extract_footnotes_and_amendments(structure, document)
    chunks.extend(footnote_chunks)
    
    # Step 6: Apply overlap at boundaries
    chunks = apply_boundary_overlap(chunks, overlap_ratio=0.15)
    
    # Step 7: Validate and assign deterministic IDs
    chunks = assign_deterministic_ids(chunks, document)
    
    # Step 8: Generate citation metadata
    chunks = enrich_citation_metadata(chunks)
    
    return chunks
```

### 4.2 Section Chunking with Size Management

```python
def chunk_sections_hierarchically(structure: LegalStructure, 
                                   document: LegalDocument,
                                   max_tokens: int = 1536,
                                   min_tokens: int = 128) -> List[LegalChunk]:
    """
    Chunk sections respecting hierarchy. Split oversized sections.
    """
    chunks = []
    
    for section_node in structure.sections:
        # Build hierarchy path
        hierarchy = build_hierarchy_path(section_node)
        
        # Get section text
        section_text = section_node.get_text()
        token_count = count_tokens(section_text)
        
        if token_count <= max_tokens:
            # Section fits in one chunk
            chunk = create_chunk(
                hierarchy=hierarchy,
                text=section_text,
                chunk_type=ChunkType.SECTION,
                document=document,
                section_node=section_node
            )
            chunks.append(chunk)
        else:
            # Oversized section: split by subsections/clauses
            sub_chunks = split_oversized_section(
                section_node, hierarchy, document, max_tokens, min_tokens
            )
            chunks.extend(sub_chunks)
    
    return chunks

def split_oversized_section(section_node, hierarchy, document, 
                            max_tokens, min_tokens) -> List[LegalChunk]:
    """
    Split large section by subsections → clauses → paragraphs → sentences.
    Always prefer legal boundaries over arbitrary splits.
    """
    chunks = []
    
    # Try subsections first
    if section_node.subsections:
        for subsection in section_node.subsections:
            sub_hierarchy = hierarchy.with_subsection(subsection.number)
            sub_text = subsection.get_text()
            if count_tokens(sub_text) <= max_tokens:
                chunks.append(create_chunk(sub_hierarchy, sub_text, ...))
            else:
                # Recurse to clauses
                chunks.extend(split_by_clauses(subsection, sub_hierarchy, ...))
    elif section_node.clauses:
        chunks.extend(split_by_clauses(section_node, hierarchy, ...))
    else:
        # Fallback: split by paragraphs with overlap
        chunks.extend(split_by_paragraphs_with_overlap(section_node, hierarchy, ...))
    
    return chunks
```

### 4.3 Boundary Overlap Strategy

```python
def apply_boundary_overlap(chunks: List[LegalChunk], 
                           overlap_ratio: float = 0.15) -> List[LegalChunk]:
    """
    Add overlap between adjacent chunks in same hierarchy branch.
    Overlap is added to the END of previous chunk and START of next chunk.
    """
    # Group chunks by hierarchy prefix (same parent)
    groups = group_by_hierarchy_prefix(chunks)
    
    for group in groups:
        # Sort by hierarchy order
        sorted_chunks = sort_by_hierarchy_order(group)
        
        for i in range(len(sorted_chunks) - 1):
            curr = sorted_chunks[i]
            next_chunk = sorted_chunks[i + 1]
            
            # Calculate overlap size
            overlap_tokens = int(min(curr.token_count, next_chunk.token_count) * overlap_ratio)
            overlap_tokens = max(overlap_tokens, 50)  # Minimum overlap
            overlap_tokens = min(overlap_tokens, 200)  # Maximum overlap
            
            # Extract overlap text from end of current
            overlap_text = extract_tail_tokens(curr.text, overlap_tokens)
            
            # Prepend to next chunk (with marker)
            next_chunk.text = f"[...continued from {curr.hierarchy.to_citation_string()}]\n{overlap_text}\n{next_chunk.text}"
            next_chunk.text_normalized = normalize_for_embedding(next_chunk.text)
            next_chunk.token_count = count_tokens(next_chunk.text_normalized)
            
            # Also append to current (for bidirectional context)
            curr.text = f"{curr.text}\n[...continues to {next_chunk.hierarchy.to_citation_string()}]\n{extract_head_tokens(next_chunk.text, overlap_tokens)}"
            curr.text_normalized = normalize_for_embedding(curr.text)
            curr.token_count = count_tokens(curr.text_normalized)
    
    return chunks
```

---

## 5. Citation Mapping: Embedding → Source

### 5.1 Complete Traceability Chain

```
User Query
    ↓
Retrieved Chunk (chunk_id)
    ↓
chunk.hierarchy → "Patents Act, 1970 → Chapter II → Section 3 → Subsection (d)"
    ↓
chunk.document_id → "A1970-39"
    ↓
chunk.document_version → "v2024-03-15" (with amendment history)
    ↓
chunk.source_provenance → SourceProvenance(
    source_id="india_code",
    source_name="India Code",
    source_url="https://www.indiacode.nic.in/handle/123456789/2039",
    authority_tier=1,
    retrieved_at="2025-01-15T10:30:00Z",
    content_hash="sha256:..."
)
    ↓
Authoritative Source: "The Patents Act, 1970 (Act 39 of 1970), Section 3(d), 
as amended by the Patents (Amendment) Act, 2005 (Act 15 of 2005), 
effective 1 January 2005. 
Source: India Code (indiacode.nic.in), retrieved 2025-01-15."
```

### 5.2 Citation Generation at Answer Time

```python
def generate_citation(chunk: LegalChunk, claim_text: str) -> Citation:
    """Generate a complete, verifiable citation from chunk metadata."""
    
    # Build legal citation string
    legal_citation = chunk.hierarchy.to_citation_string()
    
    # Add amendment info if applicable
    if chunk.amendment_status != AmendmentStatus.ORIGINAL:
        legal_citation += f" ({chunk.amendment_status.value}"
        if chunk.effective_date:
            legal_citation += f", effective {chunk.effective_date}"
        legal_citation += ")"
    
    # Build source reference
    source_ref = SourceReference(
        source_id=chunk.source_provenance.source_id,
        source_name=chunk.source_provenance.source_name,
        canonical_url=chunk.source_provenance.source_url,
        authority_tier=chunk.source_provenance.authority_tier,
        retrieved_at=chunk.source_provenance.retrieved_at,
        content_hash=chunk.source_provenance.content_hash
    )
    
    # Exact text span for verification
    text_span = find_claim_span(chunk.text, claim_text)
    
    return Citation(
        legal_citation=legal_citation,
        source_reference=source_ref,
        chunk_id=chunk.chunk_id,
        text_span=text_span,
        confidence=chunk.retrieval_confidence
    )
```

---

## 6. Document-Type Specific Chunking

### 6.1 Acts/Statutes (Primary)

| Parameter | Value |
|-----------|-------|
| **Strategy** | Hierarchical section chunking |
| **Max tokens** | 1536 |
| **Min tokens** | 128 |
| **Overlap** | 15% |
| **Special handling** | Definitions → separate chunks; Schedules → table chunks |

### 6.2 Rules/Regulations

| Parameter | Value |
|-----------|-------|
| **Strategy** | Hierarchical rule chunking |
| **Max tokens** | 1024 |
| **Min tokens** | 64 |
| **Overlap** | 10% |
| **Special handling** | Forms → separate chunks; Fee tables → table chunks |

### 6.3 Treaties (CBD, Nagoya, TRIPS, PCT, etc.)

| Parameter | Value |
|-----------|-------|
| **Strategy** | Article-based chunking |
| **Max tokens** | 1024 |
| **Min tokens** | 128 |
| **Overlap** | 10% |
| **Special handling** | Annexes → separate chunks; Reservations → separate chunks |

### 6.4 Registry Records (Patents, Trademarks, GI, Designs)

| Parameter | Value |
|-----------|-------|
| **Strategy** | Field-based chunking |
| **Max tokens** | 512 |
| **Min tokens** | 64 |
| **Overlap** | 0% |
| **Special handling** | Each record = 1 chunk; Claims → separate sub-chunks |

### 6.5 Case Law

| Parameter | Value |
|-----------|-------|
| **Strategy** | Paragraph-based with hierarchy |
| **Max tokens** | 1024 |
| **Min tokens** | 128 |
| **Overlap** | 15% |
| **Special handling** | Headnotes → separate high-priority chunks; Judgment paragraphs → hierarchical |

### 6.6 Guidelines/Notifications

| Parameter | Value |
|-----------|-------|
| **Strategy** | Section/paragraph chunking |
| **Max tokens** | 1024 |
| **Min tokens** | 128 |
| **Overlap** | 10% |
| **Special handling** | Annexures → separate chunks |

---

## 7. Multilingual Chunking

### 7.1 Strategy

1. **Primary language**: Chunk in original language (English for Indian laws)
2. **Translation chunks**: Create parallel chunks for target languages
3. **Shared chunk_id**: Translations share base chunk_id with lang suffix
4. **Embedding**: Use multilingual embedder (bge-m3, jina-v3) for all

```python
@dataclass
class MultilingualChunkGroup:
    base_chunk_id: str
    primary_chunk: LegalChunk      # English/original
    translations: Dict[str, LegalChunk]  # hi, ta, bn, etc.
    
    def get_all_chunks(self) -> List[LegalChunk]:
        return [self.primary_chunk] + list(self.translations.values())
```

### 7.2 Language-Specific Considerations

| Language | Script | Tokenizer | Notes |
|----------|--------|-----------|-------|
| Hindi | Devanagari | IndicBERT / mBERT | Compound words, sandhi |
| Tamil | Tamil | mBERT / XLM-R | Agglutinative |
| Bengali | Bengali | mBERT / XLM-R | Compound verbs |
| English | Latin | Standard | Baseline |

---

## 8. Amendment & Version Handling

### 8.1 Amendment Representation

When a law is amended, we create **new chunk versions** rather than overwriting:

```
Original Section 3(d) [v2005-01-01]
    ↓ Amended by Patents (Amendment) Act 2005
New Section 3(d) [v2005-01-01]  -- AMENDED status
    ↓ Further amended
New Section 3(d) [v2021-09-15]  -- AMENDED status
```

### 8.2 Version Data Model

```python
@dataclass
class DocumentVersion:
    document_id: str
    version_id: str              # Hash or timestamp
    version_label: str           # e.g., "2024 Amendment"
    effective_date: date
    amendment_act: Optional[str] # e.g., "Act 15 of 2005"
    amendment_type: AmendmentType # INSERTION, DELETION, SUBSTITUTION, MODIFICATION
    changes: List[ChangeDetail]
    previous_version_id: Optional[str]
    superseded: bool

@dataclass
class ChangeDetail:
    hierarchy_path: HierarchyPath
    change_type: ChangeType
    old_text: Optional[str]
    new_text: Optional[str]
    change_summary: str
```

### 8.3 Retrieval with Versions

- **Default**: Retrieve latest effective version
- **Historical**: Query with `as_of_date` parameter
- **Comparison**: Retrieve multiple versions for diff

---

## 9. Deduplication Strategy

### 9.1 Content-Based Deduplication

```python
def deduplicate_chunks(chunks: List[LegalChunk]) -> List[LegalChunk]:
    """
    Remove exact/near-duplicate chunks within same document.
    Preserve first occurrence (earliest in hierarchy).
    """
    seen_hashes = {}
    unique_chunks = []
    
    for chunk in chunks:
        # Content hash (normalized text)
        content_hash = hashlib.sha256(chunk.text_normalized.encode()).hexdigest()[:16]
        
        if content_hash not in seen_hashes:
            seen_hashes[content_hash] = chunk.chunk_id
            unique_chunks.append(chunk)
        else:
            # Log duplicate for audit
            log_duplicate(chunk.chunk_id, seen_hashes[content_hash], content_hash)
    
    return unique_chunks
```

### 9.2 Cross-Document Deduplication

- **Across versions**: Same section in different versions → keep all (versioned)
- **Across sources**: Same act from India Code vs WIPO → keep both, tag source
- **Identical text, different hierarchy**: Keep both (different legal context)

---

## 10. Validation & Quality Checks

### 10.1 Automated Validation Rules

| Check | Description | Failure Action |
|-------|-------------|----------------|
| **Hierarchy completeness** | Every chunk has act_id + section | Reject |
| **Token limits** | min_tokens ≤ tokens ≤ max_tokens | Split/merge |
| **Citation consistency** | Internal citations resolve to existing chunks | Flag for review |
| **Coverage** | All source text assigned to chunks | Flag gaps |
| **Deterministic IDs** | Same input → same chunk_ids | Verify |
| **Amendment traceability** | Amended chunks link to amendment act | Verify |

### 10.2 Quality Metrics

| Metric | Target |
|--------|--------|
| **Hierarchy preservation rate** | 100% |
| **Citation resolution rate** | > 95% |
| **Coverage** | > 99.5% of source text chunked |
| **Duplicate rate** | < 1% |
| **Amendment linkage** | 100% for amended sections |

---

## 11. Integration with Ingestion Pipeline (Phase 4)

### 11.1 Chunking Stage in Pipeline

```
Raw Document
    ↓
[Acquisition] → [Parsing/OCR] → [Structure Extraction] 
    ↓
[Legal Hierarchy Parser] → [Chunking Engine] ← Uses Phase 5 logic
    ↓
[Metadata Enrichment] → [Deduplication] → [Validation]
    ↓
[Embedding Generation] → [Indexing] → [Vector Store + Metadata Store]
```

### 11.2 Chunking Configuration per Source

| Source | Document Types | Chunk Config |
|--------|----------------|--------------|
| India Code | Acts, Rules | Hierarchical section, max 1536 tokens |
| IP India | Registry records | Field-based, max 512 tokens |
| NBA | Act, Rules, Guidelines | Hierarchical, max 1024 tokens |
| CBD/WIPO | Treaties | Article-based, max 1024 tokens |
| FSSAI | Regulations | Section-based, max 1024 tokens |
| AYUSH | Pharmacopoeia, Formulary | Monograph-based, max 1024 tokens |

---

## 12. Tunable Parameters

| Parameter | Default | Range | Tuning Method |
|-----------|---------|-------|---------------|
| `max_tokens` | 1536 | 512-4096 | Retrieval recall@K on benchmark |
| `min_tokens` | 128 | 64-512 | Avoid too-small chunks |
| `overlap_ratio` | 0.15 | 0.05-0.30 | Boundary retrieval quality |
| `definition_boost` | 2.0x | 1.5-3.0 | Definition query recall |
| `table_chunk_separately` | true | bool | Table query accuracy |
| `multilingual_enabled` | false | bool | Multilingual eval |

---

## 13. Failure Modes & Fallbacks

| Failure Mode | Detection | Fallback |
|--------------|-----------|----------|
| **Structure parse failure** | No hierarchy detected | Fall back to paragraph chunking with warnings |
| **Section > 4096 tokens** | Token count exceeded | Recursive split: subsection → clause → paragraph → sentence |
| **OCR garbage text** | Low dictionary word ratio | Flag for manual review, exclude from retrieval |
| **Missing section numbers** | Regex pattern not found | Use heading-based hierarchy |
| **Circular references** | Citation graph cycle | Break cycle, log warning |

---

## 14. Open Research Questions

| ID | Question | Status |
|----|----------|--------|
| ORQ-21 | Optimal max_tokens for Indian legal acts (1536 vs 2048)? | Benchmark needed |
| ORQ-22 | Does parent-child retrieval improve section-lookup queries? | Experiment planned |
| ORQ-23 | Best overlap ratio for cross-section legal reasoning? | 10% vs 15% vs 20% |
| ORQ-24 | How to chunk "Schedule" with 100+ entries efficiently? | Table-aware chunking |
| ORQ-25 | Should definitions be separate chunks or inline? | Current: separate (high priority) |
| ORQ-26 | Chunking for patent claims (highly structured)? | Special handler needed |

---

## 15. Implementation Dependencies

| Dependency | Purpose |
|------------|---------|
| **Legal Hierarchy Parser** | Extract Act→Chapter→Section structure |
| **Token Counter** | Accurate token counting (tiktoken) |
| **Multilingual Embedder** | bge-m3 / jina-v3 for embeddings |
| **PDF/HTML Parser** | pdfplumber, BeautifulSoup |
| **Table Extractor** | camelot, tabula-py for schedules |

---

## 16. Summary: Chunking Architecture Decision

| Strategy | Role | Implementation Priority |
|----------|------|------------------------|
| **Hierarchical Section Chunking** | **CORE** | Phase 1 (MVP) |
| **Definition Extraction** | **CORE** | Phase 1 (MVP) |
| **Table/Schedule Chunking** | **CORE** | Phase 1 (MVP) |
| **Boundary Overlap (15%)** | **CORE** | Phase 1 (MVP) |
| **Parent-Child for Large Sections** | **OPTIONAL** | Phase 2 |
| **Multilingual Parallel Chunks** | **OPTIONAL** | Phase 3 |
| **Amendment Version Chunks** | **CORE** | Phase 1 (MVP) |
| **Deterministic Chunk IDs** | **CORE** | Phase 1 (MVP) |
| **Citation Traceability Metadata** | **CORE** | Phase 1 (MVP) |

---

## 17. Next Phase: Phase 6 - Retrieval Engine

The chunking strategy defines the **units of retrieval**. Phase 6 will design:
- How these chunks are indexed (vector + sparse)
- How queries match to chunks
- How hierarchy metadata enables filtering
- How citation metadata enables verification

**Key interface**: Retrieval engine receives `LegalChunk` objects and must preserve all metadata through the retrieval → rerank → evidence selection pipeline.