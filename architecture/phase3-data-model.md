# Phase 3: Data Model

**Status**: ✅ Complete  
**Depends on**: Phase 1 (Requirements), Phase 2 (System Architecture)  
**Consumed by**: Phase 4 (Tech Selection), Phase 7 (Ingestion), Phase 8 (Retrieval/RAG), Phase 9 (Evaluation), Phase 11 (Knowledge Graph), Phase 12 (Formulation Classification), Phase 13 (Jurisdiction Engine), Phase 14 (Citation-First Generation), Phase 15 (Multilingual), Phase 16 (Agentic), Phase 17 (Memory), Phase 18 (API), Phase 21 (Failure Mode), Phase 22 (Roadmap), Phase 23 (Repository), Phase 24 (ADRs)

---

## 1. Overview

This phase defines the canonical data model for the IP-SAKTI Sahayak system. All downstream phases must consume these schemas as their single source of truth. No downstream phase should redefine or extend these schemas without an explicit ADR (Phase 24).

The model is organized into **relational/core tables** (PostgreSQL), **vector tables** (pgvector/FalkorDB), and **graph tables** (FalkorDB/Neo4j). Each entity includes primary keys, foreign keys, indexes, and constraints.

---

## 2. Relational Schema (PostgreSQL)

### 2.1 Core Document Tables

```sql
-- Source registry: every ingested document originates from a source
CREATE TABLE sources (
    source_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(255) NOT NULL,                    -- "India Code", "WIPO", "NBA", "CBD"
    authority_tier    SMALLINT NOT NULL CHECK (authority_tier BETWEEN 1 AND 4),
    jurisdiction      VARCHAR(100) NOT NULL,                    -- "IN", "IN-CA", "INT", "EU", "US", "JP", "PCT"
    source_type       VARCHAR(50) NOT NULL,                     -- "act", "rule", "regulation", "treaty", "guideline", "case", "form", "registry"
    base_url          VARCHAR(500),                             -- Canonical base URL
    metadata          JSONB DEFAULT '{}',                       -- Extensible source-specific metadata
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name, jurisdiction, source_type)
);

-- Document versions: each amendment creates a new version row
CREATE TABLE document_versions (
    version_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id         UUID NOT NULL REFERENCES sources(source_id),
    document_id       UUID NOT NULL,                            -- Stable ID across versions (same act across amendments)
    title             VARCHAR(500) NOT NULL,
    short_title       VARCHAR(200),                             -- "Patents Act, 1970"
    document_number   VARCHAR(100),                             -- "Act No. 39 of 1970"
    enactment_date    DATE,
    effective_date    DATE,
    repeal_date       DATE,
    status            VARCHAR(30) NOT NULL DEFAULT 'in_force',  -- in_force, repealed, amended, draft
    language          VARCHAR(10) NOT NULL DEFAULT 'en',        -- ISO 639-1
    canonical_url     VARCHAR(500),                             -- Authoritative source URL
    content_hash      CHAR(64) NOT NULL,                        -- SHA-256 of full text
    amendment_note    TEXT,                                     -- What changed in this version
    supersedes_version_id UUID REFERENCES document_versions(version_id), -- Previous version
    metadata          JSONB DEFAULT '{}',                       -- Extensible: chapters, schedules, etc.
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, version_id)
);

-- Index for temporal queries
CREATE INDEX idx_doc_versions_temporal ON document_versions (document_id, effective_date DESC);
CREATE INDEX idx_doc_versions_jurisdiction ON document_versions (source_id, status);
```

### 2.2 Chunk Tables

```sql
-- Chunks: the atomic unit of retrieval and citation
CREATE TABLE chunks (
    chunk_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id        UUID NOT NULL REFERENCES document_versions(version_id),
    chunk_index       INTEGER NOT NULL,                         -- Order within document version
    chunk_type        VARCHAR(30) NOT NULL,                     -- SECTION, DEFINITION, TABLE, SCHEDULE, FOOTNOTE, PREAMBLE, AMENDMENT_NOTE, CLAUSE, SUBSECTION
    hierarchy_path    TEXT[] NOT NULL,                          -- ["Act", "Chapter II", "Section 3", "Subsection (1)", "Clause (a)"]
    hierarchy_level   SMALLINT NOT NULL,                        -- 0=Act, 1=Chapter, 2=Section, 3=Subsection, 4=Clause
    parent_chunk_id   UUID REFERENCES chunks(chunk_id),         -- Parent in hierarchy (for parent-child retrieval)
    title             VARCHAR(500),                             -- "Section 3: Definitions"
    text              TEXT NOT NULL,                            -- Full chunk text
    token_count       INTEGER NOT NULL,                         -- Token count (model-specific, store for bge-m3)
    char_start        INTEGER,                                  -- Character offset in source document
    char_end          INTEGER,
    citation_text     VARCHAR(500),                             -- Human-readable citation: "Section 3(1)(a), Patents Act 1970"
    citation_json     JSONB NOT NULL,                           -- Structured citation for programmatic use
    authority_tier    SMALLINT NOT NULL,                        -- Inherited from source (1-4)
    jurisdiction      VARCHAR(100) NOT NULL,                    -- Inherited from source
    language          VARCHAR(10) NOT NULL DEFAULT 'en',
    is_amendment      BOOLEAN NOT NULL DEFAULT FALSE,           -- True if this chunk is an amendment note
    amended_chunk_ids UUID[],                                   -- Chunks this amendment modifies
    metadata          JSONB DEFAULT '{}',                       -- Extensible: tables, formulas, cross-refs
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (version_id, chunk_index)
);

-- Indexes for retrieval
CREATE INDEX idx_chunks_version ON chunks (version_id);
CREATE INDEX idx_chunks_hierarchy ON chunks USING GIN (hierarchy_path);
CREATE INDEX idx_chunks_type ON chunks (chunk_type);
CREATE INDEX idx_chunks_jurisdiction ON chunks (jurisdiction);
CREATE INDEX idx_chunks_authority ON chunks (authority_tier);
CREATE INDEX idx_chunks_parent ON chunks (parent_chunk_id);
```

### 2.3 Embedding Tables

```sql
-- Embeddings: one row per chunk per embedding model
CREATE TABLE embeddings (
    embedding_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id          UUID NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    model_name        VARCHAR(100) NOT NULL,                    -- "bge-m3", "jina-v3", etc.
    model_version     VARCHAR(50),                              -- Model version/tag
    dimensions        INTEGER NOT NULL,                         -- 1024 for bge-m3
    vector            VECTOR(1024),                             -- pgvector column
    quantization      VARCHAR(20),                              -- "fp32", "int8", "binary"
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chunk_id, model_name, model_version)
);

-- HNSW index (created via pgvector)
-- CREATE INDEX idx_embeddings_hnsw ON embeddings USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 200);
CREATE INDEX idx_embeddings_chunk_model ON embeddings (chunk_id, model_name);
```

### 2.4 Legal Entity Tables

```sql
-- Extracted legal entities from chunks
CREATE TABLE legal_entities (
    entity_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id          UUID NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    entity_type       VARCHAR(50) NOT NULL,                     -- ACT, CHAPTER, SECTION, SUBSECTION, CLAUSE, DEFINITION, TREATY, TREATY_ARTICLE, CASE, PARAGRAPH, GUIDELINE, FORMULATION, INGREDIENT, BIOLOGICAL_RESOURCE, ABS_APPLICATION, PATENT_RECORD, TM_RECORD, GI_RECORD, TK_ENTRY
    entity_name       VARCHAR(500) NOT NULL,                    -- "Section 3(d)", "Novartis v. Union of India"
    entity_identifier VARCHAR(200),                             -- Canonical identifier: "IN-PATENTS-1970-S3-d"
    normalized_text   TEXT,                                     -- Normalized for matching
    confidence        REAL NOT NULL DEFAULT 1.0,                -- Extraction confidence
    metadata          JSONB DEFAULT '{}',                       -- Type-specific attributes
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entities_chunk ON legal_entities (chunk_id);
CREATE INDEX idx_entities_type ON legal_entities (entity_type);
CREATE INDEX idx_entities_identifier ON legal_entities (entity_identifier);
```

### 2.5 Jurisdiction Tables

```sql
-- Jurisdiction hierarchy
CREATE TABLE jurisdictions (
    jurisdiction_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code              VARCHAR(10) NOT NULL UNIQUE,              -- "IN", "IN-MH", "INT-CBD", "INT-TRIPS", "US", "EP"
    name              VARCHAR(200) NOT NULL,
    jurisdiction_type VARCHAR(30) NOT NULL,                     -- NATIONAL, STATE_PROVINCE, INTERNATIONAL_TREATY, REGIONAL, INTERNATIONAL_ORG
    parent_jurisdiction_id UUID REFERENCES jurisdictions(jurisdiction_id),
    iso_code          VARCHAR(10),                              -- ISO 3166-1 alpha-2 for countries
    metadata          JSONB DEFAULT '{}',                       -- Courts, regulators, official gazettes
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jurisdictions_parent ON jurisdictions (parent_jurisdiction_id);
CREATE INDEX idx_jurisdictions_type ON jurisdictions (jurisdiction_type);
```

### 2.6 Claims & Citations Tables

```sql
-- Legal claims extracted from chunks
CREATE TABLE claims (
    claim_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id          UUID NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    claim_text        TEXT NOT NULL,                            -- The legal proposition
    claim_type        VARCHAR(50) NOT NULL,                     -- DEFINITION, REQUIREMENT, PROHIBITION, PROCEDURE, PENALTY, EXEMPTION, POWER, DUTY, RIGHT
    authority_tier    SMALLINT NOT NULL,
    jurisdiction      VARCHAR(100) NOT NULL,
    effective_from    DATE,
    effective_to      DATE,
    is_current        BOOLEAN NOT NULL DEFAULT TRUE,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claims_chunk ON claims (chunk_id);
CREATE INDEX idx_claims_type ON claims (claim_type);
CREATE INDEX idx_claims_jurisdiction ON claims (jurisdiction);
CREATE INDEX idx_claims_temporal ON claims (effective_from, effective_to);

-- Citations: explicit link from answer claims to evidence chunks
CREATE TABLE citations (
    citation_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id          UUID NOT NULL,                            -- FK to queries table (later)
    chunk_id          UUID NOT NULL REFERENCES chunks(chunk_id),
    claim_id          UUID REFERENCES claims(claim_id),         -- Optional: which claim this supports
    answer_span_start INTEGER,                                  -- Character offset in generated answer
    answer_span_end   INTEGER,
    citation_text     VARCHAR(500) NOT NULL,                    -- Formatted citation
    authority_tier    SMALLINT NOT NULL,
    relevance_score   REAL,                                     -- Retrieval/rerank score
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_citations_query ON citations (query_id);
CREATE INDEX idx_citations_chunk ON citations (chunk_id);
```

### 2.7 Query & Retrieval Tables

```sql
-- User queries and their analysis
CREATE TABLE queries (
    query_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID,
    user_id           UUID,
    query_text        TEXT NOT NULL,
    language          VARCHAR(10) NOT NULL DEFAULT 'en',
    intent            VARCHAR(50),                              -- CLASSIFICATION, INTERPRETATION, PROCEDURE, COMPLIANCE, COMPARISON, PRECEDENT, STATUS, STRATEGY, CALCULATION, DRAFTING
    formulation_class VARCHAR(50),                              -- CLASSICAL_MEDICINE, GENERIC_MEDICINE, PATENT_PROPRIETARY, NEW_DRUG, PHYTOPHARMACEUTICAL, AYURVEDA_AAHAR, NUTRACEUTICAL, COSMETIC
    jurisdiction_codes VARCHAR(100)[],                          -- Determined applicable jurisdictions
    analysis_json     JSONB,                                    -- Full query analysis output
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_queries_session ON queries (session_id);
CREATE INDEX idx_queries_user ON queries (user_id);
CREATE INDEX idx_queries_intent ON queries (intent);
CREATE INDEX idx_queries_formulation ON queries (formulation_class);

-- Retrieval results per query
CREATE TABLE retrieval_results (
    result_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id          UUID NOT NULL REFERENCES queries(query_id) ON DELETE CASCADE,
    chunk_id          UUID NOT NULL REFERENCES chunks(chunk_id),
    stage             VARCHAR(30) NOT NULL,                     -- SPARSE, DENSE, FUSED, RERANKED, SELECTED
    score             REAL NOT NULL,
    rank              INTEGER NOT NULL,
    fusion_method     VARCHAR(30),                              -- RRF, WEIGHTED, etc.
    authority_weight  REAL,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (query_id, chunk_id, stage)
);

CREATE INDEX idx_retrieval_query_stage ON retrieval_results (query_id, stage);
CREATE INDEX idx_retrieval_chunk ON retrieval_results (chunk_id);
```

### 2.8 Evaluation Tables

```sql
-- Golden dataset for evaluation
CREATE TABLE evaluation_cases (
    case_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text        TEXT NOT NULL,
    language          VARCHAR(10) NOT NULL DEFAULT 'en',
    intent            VARCHAR(50) NOT NULL,
    formulation_class VARCHAR(50),
    jurisdiction_codes VARCHAR(100)[],
    expected_answer   TEXT,                                     -- Reference answer
    expected_citations UUID[],                                  -- Expected chunk_ids
    expected_entities UUID[],                                   -- Expected legal_entities
    difficulty        VARCHAR(20),                              -- EASY, MEDIUM, HARD, ADVERSARIAL
    tags              VARCHAR(100)[],
    source            VARCHAR(100),                             -- "expert", "synthetic", "historical"
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Experiment runs
CREATE TABLE experiments (
    experiment_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(200) NOT NULL,
    hypothesis        TEXT NOT NULL,
    config_json       JSONB NOT NULL,                           -- Full config: models, params, prompts
    dataset_id        UUID REFERENCES evaluation_cases(case_id), -- Or separate dataset table
    status            VARCHAR(30) NOT NULL DEFAULT 'pending',   -- pending, running, completed, failed
    metrics_json      JSONB,                                    -- Results: precision, recall, latency, cost
    conclusion        TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ
);

CREATE INDEX idx_experiments_status ON experiments (status);
```

### 2.9 User & Session Tables

```sql
CREATE TABLE users (
    user_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             VARCHAR(255) UNIQUE,
    role              VARCHAR(30) NOT NULL DEFAULT 'researcher', -- attorney, researcher, founder, regulator, student, admin
    default_jurisdiction VARCHAR(100) DEFAULT 'IN',
    preferred_language VARCHAR(10) DEFAULT 'en',
    preferences       JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sessions (
    session_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users(user_id),
    context_json      JSONB DEFAULT '{}',                       -- Active jurisdiction, formulation context, etc.
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions (user_id);
```

### 2.10 Audit Tables

```sql
-- Immutable audit log of all system decisions
CREATE TABLE audit_events (
    event_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type        VARCHAR(50) NOT NULL,                     -- QUERY, RETRIEVAL, RERANK, GENERATION, CITATION_VERIFICATION, GROUNDEDNESS_CHECK, ESCALATION, FORMULATION_CLASSIFICATION, JURISDICTION_DETERMINATION
    query_id          UUID REFERENCES queries(query_id),
    session_id        UUID REFERENCES sessions(session_id),
    user_id           UUID REFERENCES users(user_id),
    input_json        JSONB,                                    -- Input to the decision
    output_json       JSONB,                                    -- Output from the decision
    confidence        REAL,
    latency_ms        INTEGER,
    model_versions    JSONB,                                    -- Versions of all models used
    error             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_query ON audit_events (query_id);
CREATE INDEX idx_audit_session ON audit_events (session_id);
CREATE INDEX idx_audit_type_time ON audit_events (event_type, created_at);
```

---

## 3. Vector Schema (pgvector / FalkorDB)

### 3.1 Vector Index Configuration

```sql
-- HNSW index for cosine similarity (bge-m3)
-- Parameters from Phase 4 Technology Selection
CREATE INDEX idx_embeddings_hnsw_cosine 
ON embeddings USING hnsw (vector vector_cosine_ops) 
WITH (m = 16, ef_construction = 200);

-- For inner product (if using normalized vectors)
CREATE INDEX idx_embeddings_hnsw_ip 
ON embeddings USING hnsw (vector vector_ip_ops) 
WITH (m = 16, ef_construction = 200);
```

### 3.2 Multi-Model Embedding Strategy

| Model | Dimensions | Use Case | Table |
|-------|------------|----------|-------|
| bge-m3 | 1024 | Primary dense retrieval | embeddings (model_name='bge-m3') |
| jina-v3 | 1024 | Fallback/ensemble | embeddings (model_name='jina-v3') |
| bge-reranker-v2-m3 | N/A | Cross-encoder (no vector storage) | N/A |

---

## 4. Graph Schema (FalkorDB / Neo4j)

### 4.1 Node Labels

```cypher
// Core legal hierarchy
(:Act {act_id, short_title, full_title, year, jurisdiction, authority_tier, status})
(:Chapter {chapter_id, number, title, act_id})
(:Part {part_id, number, title, chapter_id})
(:Section {section_id, number, title, text, part_id, version_id})
(:Subsection {subsection_id, number, text, section_id})
(:Clause {clause_id, number, text, subsection_id})
(:Definition {definition_id, term, defined_text, section_id})

// Treaties & International
(:Treaty {treaty_id, name, year, status, parties})
(:TreatyArticle {article_id, number, text, treaty_id})

// Case Law
(:Case {case_id, citation, court, date, jurisdiction, url})
(:Paragraph {paragraph_id, number, text, case_id})

// Guidelines & Forms
(:Guideline {guideline_id, title, issuer, date, jurisdiction})
(:Form {form_id, number, title, jurisdiction, purpose})

// Formulation & AYUSH
(:Formulation {formulation_id, name, class, classical_text_ref})
(:Ingredient {ingredient_id, name, synonyms[], botanical_name, cas_number})
(:BiologicalResource {resource_id, scientific_name, common_name, geography})
(:ABSApplication {application_id, applicant, resource_id, status, date})

// Registry Records
(:PatentRecord {patent_id, number, title, applicant, status, filing_date, grant_date})
(:TMRecord {tm_id, number, mark, class, proprietor, status})
(:GIRecord {gi_id, name, goods, geography, proprietor})
(:TKEntry {tk_id, formulation, community, source_text})
```

### 4.2 Relationship Types

```cypher
// Hierarchy (HIGH VALUE - mandatory)
(:Act)-[:HAS_CHAPTER]->(:Chapter)
(:Chapter)-[:HAS_PART]->(:Part)
(:Part)-[:HAS_SECTION]->(:Section)
(:Section)-[:HAS_SUBSECTION]->(:Subsection)
(:Subsection)-[:HAS_CLAUSE]->(:Clause)
(:Section)-[:HAS_DEFINITION]->(:Definition)

// Amendments (HIGH VALUE - mandatory)
(:Act)-[:AMENDS]->(:Act)                           // Act-level amendment
(:Section)-[:AMENDS_SECTION]->(:Section)           // Section-level amendment
(:Act)-[:INSERTS]->(:Section)                      // New section inserted
(:Act)-[:DELETES]->(:Section)                      // Section deleted
(:Act)-[:SUBSTITUTES]->(:Section)                  // Section substituted
(:Act)-[:MODIFIES]->(:Section)                     // Section modified
(:Act)-[:SUPERSEDES]->(:Act)                       // Version supersession
(:Section)-[:HAS_VERSION]->(:SectionVersion)       // Version chain per section

// Treaty Implementation (HIGH VALUE)
(:Act)-[:IMPLEMENTS]->(:Treaty)
(:Treaty)-[:IMPLEMENTED_BY]->(:Act)
(:Section)-[:IMPLEMENTS_TREATY]->(:TreatyArticle)

// Case Law (HIGH VALUE)
(:Case)-[:INTERPRETS]->(:Section)
(:Section)-[:INTERPRETED_BY]->(:Case)
(:Case)-[:CITES]->(:Case)
(:Case)-[:OVERRULES]->(:Case)
(:Case)-[:DISTINGUISHES]->(:Case)
(:Case)-[:FOLLOWS]->(:Case)

// Delegation (HIGH VALUE)
(:Act)-[:DELEGATES_TO]->(:Act)                     // e.g., D&C Act delegates to Rules
(:Rule)-[:MADE_UNDER]->(:Act)

// Cross-References (MEDIUM VALUE)
(:Section)-[:REFERENCES]->(:Section)
(:Section)-[:DEFINES_TERM]->(:Definition)
(:Section)-[:SUBJECT_TO]->(:Section)
(:Section)-[:OVERRIDES]->(:Section)
(:Section)-[:CONFLICTS_WITH]->(:Section)

// Formulation (MEDIUM VALUE)
(:Formulation)-[:CLASSIFIED_AS]->(:FormulationClass)
(:Formulation)-[:CONTAINS]->(:Ingredient)
(:Formulation)-[:DERIVED_FROM]->(:BiologicalResource)
(:Formulation)-[:REQUIRES_ABS]->(:ABSApplication)
(:Ingredient)-[:EXEMPT_FROM]->(:Regulation)

// Registry (LOW VALUE - optional)
(:PatentRecord)-[:CLAIMS]->(:Section)
(:TMRecord)-[:REGISTERED_UNDER]->(:Act)
```

### 4.3 Graph Indexes

```cypher
// FalkorDB/Redis indexes
CREATE INDEX ON :Act(act_id)
CREATE INDEX ON :Section(section_id)
CREATE INDEX ON :Section(number)
CREATE INDEX ON :Case(case_id)
CREATE INDEX ON :Formulation(formulation_id)
CREATE INDEX ON :Ingredient(ingredient_id)
CREATE FULLTEXT INDEX ON :Section(text)
CREATE FULLTEXT INDEX ON :Case(text)
```

---

## 5. Schema Relationships (ER Diagram)

```
sources (1) ─────< (N) document_versions
document_versions (1) ─────< (N) chunks
chunks (1) ─────< (N) embeddings (per model)
chunks (1) ─────< (N) legal_entities
chunks (1) ─────< (N) claims
chunks (1) ─────< (1) parent_chunk (self-ref)
chunks (N) ─────< (N) amended_chunk_ids (self-ref array)

queries (1) ─────< (N) retrieval_results
retrieval_results (N) ─────> (1) chunks

citations (N) ─────> (1) queries
citations (N) ─────> (1) chunks
citations (N) ─────> (1) claims (optional)

evaluation_cases (1) ─────< (N) experiments (via dataset)
```

---

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **document_id + version_id** | Stable document identity across amendments; version_id for point-in-time queries |
| **hierarchy_path as TEXT[]** | Efficient GIN indexing for prefix queries ("all chunks under Section 3") |
| **authority_tier on chunks** | Denormalized for fast retrieval filtering without joins |
| **citation_json structured** | Enables programmatic citation formatting (Bluebook, Indian, custom) |
| **claims separate from chunks** | Claims are the atomic legal propositions; chunks are retrieval units |
| **audit_events immutable** | Append-only; partitioned by month for retention |
| **Graph separate from relational** | Graph for multi-hop/temporal; relational for primary retrieval & metadata |
| **entity_identifier canonical** | Enables cross-document entity resolution (e.g., "Section 3(d)" across versions) |

---

## 7. Migration & Versioning Strategy

1. **Schema version** stored in `schema_migrations` table (Flyway/Liquibase)
2. **Backward compatibility**: New columns always nullable with defaults
3. **Data migrations** for schema changes affecting existing data
4. **Graph schema** versioned via separate migration scripts
5. **Vector index rebuild** triggered on model change (embedding model version column)

---

## 8. Data Quality Constraints

```sql
-- Every chunk must have valid hierarchy_path
ALTER TABLE chunks ADD CONSTRAINT chk_hierarchy_not_empty 
    CHECK (array_length(hierarchy_path, 1) > 0);

-- Authority tier must be 1-4
ALTER TABLE chunks ADD CONSTRAINT chk_authority_tier 
    CHECK (authority_tier BETWEEN 1 AND 4);

-- Content hash must be valid SHA-256
ALTER TABLE document_versions ADD CONSTRAINT chk_content_hash 
    CHECK (content_hash ~ '^[a-f0-9]{64}$');

-- Effective dates logical
ALTER TABLE document_versions ADD CONSTRAINT chk_dates 
    CHECK (repeal_date IS NULL OR repeal_date >= effective_date);
```

---

## 9. Open Research Questions (for Phase 24 ADR)

| ID | Question |
|----|----------|
| ORQ-63 | Should `chunks` table be partitioned by `jurisdiction` for query performance? |
| ORQ-64 | Optimal `token_count` threshold for chunk splitting per document type? |
| ORQ-65 | Store sparse (BM25) vectors in `embeddings` table or separate? |
| ORQ-66 | Graph node properties: store full text or only references to chunk_ids? |
| ORQ-67 | Temporal queries: materialized view for point-in-time or runtime joins? |
| ORQ-68 | Multi-lingual chunks: single table with `language` column or separate tables? |

---

## 10. Deliverables

1. ✅ This document (`architecture/phase3-data-model.md`)
2. SQL migration scripts (to be created in Phase 22/23 implementation)
3. Graph schema Cypher scripts
4. Entity-relationship diagram (Mermaid/PlantUML)
5. Data dictionary (Markdown/CSV for stakeholders)