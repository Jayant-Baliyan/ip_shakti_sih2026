# Phase 15: Data Model Architecture

## 1. Overview

This document defines the complete data model for IP-SAKTI Sahayak, consolidating all schemas from Phases 1-14. The data model is organized by domain and includes all entities, relationships, indexes, and constraints needed for the full system.

### 1.1 Design Principles

1. **Normalization with Pragmatism**: 3NF for transactional data; denormalized for read-heavy analytical data
2. **Immutability**: Core legal documents and chunks are append-only; versions create new records
3. **Provenance**: Every record tracks source, extraction time, content hash, and transformation lineage
4. **Multi-tenancy Ready**: User-scoped data isolated by user_id; global data shared
5. **Auditability**: All mutations logged with actor, timestamp, and before/after state
6. **Extensibility**: JSONB columns for evolving metadata without schema migrations

### 1.2 Database Technology Selection

| Data Type | Primary Store | Secondary Index | Rationale |
|-----------|---------------|-----------------|-----------|
| Transactional (users, sessions, preferences) | PostgreSQL | B-tree, GIN | ACID, mature, JSONB support |
| Vector embeddings | hnswlib (dev) / Milvus (prod) | HNSW | High-recall ANN search |
| Sparse vectors (BM25) | Custom inverted index / Tantivy | Inverted index | Exact term matching |
| Knowledge graph | FalkorDB (dev) / Neo4j (prod) | Native graph | Cypher/GQL, traversal |
| Analytical (evaluation, metrics) | ClickHouse / TimescaleDB | Columnar | Fast aggregations |
| Object storage (PDFs, exports) | MinIO / S3 | - | Large blobs, versioning |

---

## 2. Core Domain Models

### 2.1 Users & Authentication

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255),  -- Null for SSO users
    auth_provider VARCHAR(50) DEFAULT 'local',  -- local, google, github, oidc
    auth_provider_id VARCHAR(255),
    full_name VARCHAR(255),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_provider ON users(auth_provider, auth_provider_id);

-- User sessions (for JWT refresh tokens)
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    refresh_token_hash CHAR(64) NOT NULL,  -- SHA256 of refresh token
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at) WHERE revoked_at IS NULL;

-- API keys (for programmatic access)
CREATE TABLE api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash CHAR(64) NOT NULL,  -- SHA256 of API key
    key_prefix VARCHAR(20) NOT NULL,  -- First 8 chars for identification
    name VARCHAR(100),
    scopes TEXT[] DEFAULT '{}',  -- e.g., {'query', 'ingestion', 'admin'}
    rate_limit_tier VARCHAR(20) DEFAULT 'standard',
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

### 2.2 User Preferences (from Phase 14)

```sql
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}',
    profile_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Preference learning events
CREATE TABLE preference_learning_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    trigger_context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pref_events_user ON preference_learning_events(user_id, created_at DESC);
```

### 2.3 Conversation Memory (from Phase 14)

```sql
-- Conversation sessions
CREATE TABLE conversation_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT,
    language VARCHAR(10) DEFAULT 'en',
    jurisdiction_context VARCHAR(100),
    formulation_context VARCHAR(100),
    active_branch_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_sessions_user_created ON conversation_sessions(user_id, created_at DESC);
CREATE INDEX idx_sessions_expires ON conversation_sessions(expires_at) WHERE expires_at IS NOT NULL;

-- Conversation messages
CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system, tool
    message_type VARCHAR(20) DEFAULT 'text',  -- text, structured, citation, evidence, error
    content TEXT NOT NULL,
    structured_data JSONB,
    citations JSONB DEFAULT '[]',
    evidence_refs JSONB DEFAULT '[]',
    trace_id UUID,
    parent_message_id UUID REFERENCES conversation_messages(message_id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    token_count INTEGER DEFAULT 0
);

CREATE INDEX idx_messages_session_created ON conversation_messages(session_id, created_at);
CREATE INDEX idx_messages_trace ON conversation_messages(trace_id);
CREATE INDEX idx_messages_parent ON conversation_messages(parent_message_id);

-- Conversation branches
CREATE TABLE conversation_branches (
    branch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    parent_message_id UUID NOT NULL REFERENCES conversation_messages(message_id),
    branch_reason VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_branches_session ON conversation_branches(session_id);
```

### 2.4 Sources & Authority (from Phase 1)

```sql
-- Source registry
CREATE TABLE sources (
    source_id VARCHAR(100) PRIMARY KEY,  -- e.g., 'india_code', 'ip_india', 'nba', 'cbd', 'wipo'
    name TEXT NOT NULL,
    description TEXT,
    authority_tier INTEGER NOT NULL CHECK (authority_tier BETWEEN 1 AND 5),
    jurisdiction VARCHAR(50) NOT NULL,  -- ISO country code or 'INTERNATIONAL'
    base_url TEXT,
    robots_txt_url TEXT,
    access_method VARCHAR(20) NOT NULL,  -- 'api', 'scrape', 'manual', 'bulk_download'
    access_config JSONB DEFAULT '{}',  -- API keys, selectors, auth details
    crawl_frequency INTERVAL,  -- e.g., '1 day', '1 week'
    last_crawled_at TIMESTAMPTZ,
    last_successful_crawl_at TIMESTAMPTZ,
    crawl_status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    crawl_error TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Source documents (ingested documents)
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id VARCHAR(100) NOT NULL REFERENCES sources(source_id),
    authority_tier INTEGER NOT NULL CHECK (authority_tier BETWEEN 1 AND 5),
    jurisdiction VARCHAR(50) NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- LEGISLATION, RULE, REGULATION, NOTIFICATION, GUIDELINE, TREATY, REGISTRY_RECORD, CASE_LAW, ACADEMIC, SECONDARY
    title TEXT NOT NULL,
    canonical_url TEXT,
    content_hash CHAR(64) NOT NULL,  -- SHA256 of full text
    version VARCHAR(50),  -- e.g., '2024-01-15', 'Amendment 2023', 'v1.2'
    effective_date DATE,
    publication_date DATE,
    supersedes_document_id UUID REFERENCES documents(document_id),
    superseded_by_document_id UUID REFERENCES documents(document_id),
    language VARCHAR(10) DEFAULT 'en',
    original_format VARCHAR(20),  -- pdf, html, docx, txt
    file_size_bytes BIGINT,
    page_count INTEGER,
    metadata JSONB DEFAULT '{}',  -- Extracted metadata: ministry, act_number, year, etc.
    ingestion_status VARCHAR(20) DEFAULT 'pending',  -- pending, downloading, parsing, chunking, embedding, indexing, completed, failed
    ingestion_started_at TIMESTAMPTZ,
    ingestion_completed_at TIMESTAMPTZ,
    ingestion_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_source ON documents(source_id);
CREATE INDEX idx_documents_jurisdiction ON documents(jurisdiction);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_authority ON documents(authority_tier);
CREATE INDEX idx_documents_effective ON documents(effective_date);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_supersedes ON documents(supersedes_document_id);
CREATE INDEX idx_documents_status ON documents(ingestion_status);

-- Document versions (amendment chain)
CREATE TABLE document_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    version_label VARCHAR(100),  -- e.g., 'Original', 'Amendment 2023', 'Corrigendum'
    amendment_act VARCHAR(200),  -- e.g., 'Patents (Amendment) Act, 2024'
    amendment_date DATE,
    effective_date DATE,
    changes_summary TEXT,  -- Human-readable summary of changes
    changed_sections TEXT[],  -- Section numbers that changed
    content_hash CHAR(64) NOT NULL,
    pdf_url TEXT,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_doc_versions_doc_num ON document_versions(document_id, version_number);
CREATE INDEX idx_doc_versions_current ON document_versions(document_id) WHERE is_current = TRUE;
```

### 2.5 Legal Structure & Chunks (from Phases 4, 5)

```sql
-- Legal hierarchy nodes (Act, Chapter, Part, Section, Subsection, Clause)
CREATE TABLE legal_hierarchy_nodes (
    node_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    parent_node_id UUID REFERENCES legal_hierarchy_nodes(node_id),
    node_type VARCHAR(20) NOT NULL,  -- ACT, CHAPTER, PART, SECTION, SUBSECTION, CLAUSE, SCHEDULE, APPENDIX, DEFINITION
    number VARCHAR(50),  -- e.g., '3', '3(b)', '3(b)(i)', 'Chapter II', 'Schedule I'
    title TEXT,
    full_path TEXT NOT NULL,  -- e.g., 'Patents Act 1970 > Chapter II > Section 3 > Section 3(b)'
    level INTEGER NOT NULL,  -- 0=Act, 1=Chapter, 2=Part, 3=Section, 4=Subsection, 5=Clause
    start_char INTEGER,
    end_char INTEGER,
    metadata JSONB DEFAULT '{}',  -- cross_refs, definitions, amendments, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hierarchy_doc ON legal_hierarchy_nodes(document_id);
CREATE INDEX idx_hierarchy_parent ON legal_hierarchy_nodes(parent_node_id);
CREATE INDEX idx_hierarchy_type ON legal_hierarchy_nodes(node_type);
CREATE INDEX idx_hierarchy_number ON legal_hierarchy_nodes(number);
CREATE INDEX idx_hierarchy_path ON legal_hierarchy_nodes USING GIN (full_path gin_trgm_ops);

-- Chunks (from Phase 5)
CREATE TABLE chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    hierarchy_node_id UUID REFERENCES legal_hierarchy_nodes(node_id),
    chunk_index INTEGER NOT NULL,  -- Sequential order within document
    chunk_type VARCHAR(20) NOT NULL,  -- SECTION, DEFINITION, TABLE, SCHEDULE, FOOTNOTE, PREAMBLE, AMENDMENT_NOTE, CLAUSE, PARAGRAPH
    hierarchy_path TEXT NOT NULL,  -- Denormalized for fast filtering: "Act > Chapter > Section > Subsection"
    section_number VARCHAR(50),  -- e.g., 'Section 3(b)', 'Article 8'
    section_title TEXT,
    text_content TEXT NOT NULL,
    text_hash CHAR(64) NOT NULL,  -- SHA256 of text_content
    token_count INTEGER NOT NULL,
    char_start INTEGER,
    char_end INTEGER,
    parent_chunk_id UUID REFERENCES chunks(chunk_id),  -- For parent-child chunking
    child_chunk_ids UUID[],
    metadata JSONB DEFAULT '{}',  -- citations, cross_refs, definitions, tables, footnotes
    embedding_model VARCHAR(50),
    embedding_version INTEGER DEFAULT 1,
    sparse_vector_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_hierarchy_node ON chunks(hierarchy_node_id);
CREATE INDEX idx_chunks_hierarchy_path ON chunks USING GIN (hierarchy_path gin_trgm_ops);
CREATE INDEX idx_chunks_section ON chunks(section_number);
CREATE INDEX idx_chunks_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_text_hash ON chunks(text_hash);
CREATE INDEX idx_chunks_parent ON chunks(parent_chunk_id);
CREATE INDEX idx_chunks_doc_idx ON chunks(document_id, chunk_index);

-- Chunk embeddings (stored in vector DB, but metadata here)
CREATE TABLE chunk_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    model VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    vector_id VARCHAR(100),  -- Internal ID in vector store
    dimension INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_model ON chunk_embeddings(model, version);

-- Chunk sparse vectors (BM25)
CREATE TABLE chunk_sparse_vectors (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    config_hash CHAR(64) NOT NULL,  -- Hash of BM25 config (tokenizer, stopwords, etc.)
    vector_data BYTEA,  -- Serialized sparse vector
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.6 Citations & Evidence (from Phase 10)

```sql
-- Citations (generated during answer generation)
CREATE TABLE citations (
    citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL,  -- Links to query trace
    message_id UUID REFERENCES conversation_messages(message_id),
    chunk_ids UUID[] NOT NULL,
    document_ids UUID[] NOT NULL,
    hierarchy_path TEXT NOT NULL,
    section_numbers TEXT[],
    authority_tier INTEGER NOT NULL,
    jurisdiction VARCHAR(50) NOT NULL,
    text_span TEXT,  -- Exact quoted text from source
    citation_text TEXT,  -- Formatted citation for display
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    verification_status VARCHAR(20) DEFAULT 'pending',  -- pending, verified, failed, disputed
    verification_details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_citations_trace ON citations(trace_id);
CREATE INDEX idx_citations_message ON citations(message_id);
CREATE INDEX idx_citations_chunk ON citations USING GIN (chunk_ids);
CREATE INDEX idx_citations_doc ON citations USING GIN (document_ids);

-- Evidence references (retrieval results linked to queries)
CREATE TABLE evidence_refs (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL,
    query_id UUID,  -- If part of evaluation
    chunk_id UUID NOT NULL REFERENCES chunks(chunk_id),
    document_id UUID NOT NULL REFERENCES documents(document_id),
    retrieval_stage VARCHAR(20) NOT NULL,  -- sparse, dense, hybrid, reranked, selected
    rank INTEGER,
    score FLOAT,
    authority_tier INTEGER,
    jurisdiction VARCHAR(50),
    hierarchy_path TEXT,
    text_preview TEXT,
    is_selected BOOLEAN DEFAULT FALSE,  -- Whether used in final answer
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evidence_trace ON evidence_refs(trace_id);
CREATE INDEX idx_evidence_query ON evidence_refs(query_id);
CREATE INDEX idx_evidence_chunk ON evidence_refs(chunk_id);
CREATE INDEX idx_evidence_stage ON evidence_refs(retrieval_stage);
CREATE INDEX idx_evidence_selected ON evidence_refs(trace_id, is_selected) WHERE is_selected = TRUE;
```

### 2.7 Queries & Traces (from Phases 3, 6, 10, 21)

```sql
-- Queries (canonical query records)
CREATE TABLE queries (
    query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES conversation_sessions(session_id),
    user_id UUID REFERENCES users(user_id),
    trace_id UUID NOT NULL UNIQUE,
    raw_query TEXT NOT NULL,
    normalized_query TEXT,
    detected_language VARCHAR(10),
    query_category VARCHAR(50),  -- From Phase 3 classification
    intent_category VARCHAR(50),
    jurisdiction_detected VARCHAR(50),
    formulation_class VARCHAR(50),
    retrieval_strategy_hints JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_queries_session ON queries(session_id, created_at DESC);
CREATE INDEX idx_queries_user ON queries(user_id, created_at DESC);
CREATE INDEX idx_queries_trace ON queries(trace_id);
CREATE INDEX idx_queries_category ON queries(query_category);

-- Query traces (full pipeline execution trace)
CREATE TABLE query_traces (
    trace_id UUID PRIMARY KEY,
    query_id UUID NOT NULL REFERENCES queries(query_id),
    status VARCHAR(20) NOT NULL,  -- started, understanding, jurisdiction, formulation, planning, retrieving, reranking, selecting, generating, verifying, completed, failed
    current_stage VARCHAR(50),
    error_message TEXT,
    error_stage VARCHAR(50),
    stages JSONB DEFAULT '[]',  -- Array of stage executions with timings
    total_latency_ms INTEGER,
    retrieval_latency_ms INTEGER,
    rerank_latency_ms INTEGER,
    generation_latency_ms INTEGER,
    verification_latency_ms INTEGER,
    token_usage JSONB,  -- {embedding: X, llm_prompt: Y, llm_completion: Z}
    cost_usd FLOAT,
    retrieval_confidence FLOAT,
    generation_confidence FLOAT,
    final_confidence FLOAT,
    abstained BOOLEAN DEFAULT FALSE,
    abstention_reason VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_traces_query ON query_traces(query_id);
CREATE INDEX idx_traces_status ON query_traces(status);
CREATE INDEX idx_traces_created ON query_traces(created_at DESC);

-- Stage executions (detailed per-stage timing)
CREATE TABLE stage_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES query_traces(trace_id) ON DELETE CASCADE,
    stage_name VARCHAR(50) NOT NULL,
    stage_order INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,  -- started, completed, failed, skipped
    input_summary JSONB,
    output_summary JSONB,
    latency_ms INTEGER,
    token_usage JSONB,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_stage_trace ON stage_executions(trace_id, stage_order);
```

### 2.8 Formulation Classification (from Phase 8)

```sql
-- Formulation classes (reference data)
CREATE TABLE formulation_classes (
    class_id VARCHAR(50) PRIMARY KEY,  -- e.g., 'classical_medicine', 'generic_medicine'
    name TEXT NOT NULL,
    description TEXT,
    legal_basis TEXT,  -- e.g., 'D&C Act Schedule E(1), Rule 158'
    applicable_acts TEXT[],
    applicable_rules TEXT[],
    regulatory_authority VARCHAR(100),
    licensing_requirements JSONB DEFAULT '[]',
    labeling_requirements JSONB DEFAULT '[]',
    abs_requirements JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Formulation classification results
CREATE TABLE formulation_classifications (
    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL,
    input_data JSONB NOT NULL,  -- Full input: ingredients, dosage_form, preparation_method, etc.
    determined_class VARCHAR(50) NOT NULL REFERENCES formulation_classes(class_id),
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    method VARCHAR(20) NOT NULL,  -- deterministic, llm_reasoning, escalated
    rule_matches JSONB DEFAULT '[]',  -- Which deterministic rules matched
    llm_reasoning TEXT,
    conflicts JSONB DEFAULT '[]',
    escalation_triggers JSONB DEFAULT '[]',
    regulatory_output JSONB,  -- Applicable regimes, licensing, ABS, labeling
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_formulation_trace ON formulation_classifications(trace_id);
CREATE INDEX idx_formulation_class ON formulation_classifications(determined_class);

-- Formulation classification rules (deterministic engine)
CREATE TABLE formulation_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    target_class VARCHAR(50) REFERENCES formulation_classes(class_id),
    priority INTEGER NOT NULL,  -- Higher = evaluated first
    conditions JSONB NOT NULL,  -- Structured conditions (ingredient schedules, dosage forms, etc.)
    legal_basis TEXT,  -- Specific section/rule reference
    authority_tier INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    supersedes_rule_id VARCHAR(50) REFERENCES formulation_rules(rule_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_formulation_rules_class ON formulation_rules(target_class);
CREATE INDEX idx_formulation_rules_priority ON formulation_rules(priority DESC);
```

### 2.9 Jurisdiction Engine (from Phase 9)

```sql
-- Jurisdictions
CREATE TABLE jurisdictions (
    jurisdiction_id VARCHAR(50) PRIMARY KEY,  -- ISO code or custom (e.g., 'IN', 'IN-MH', 'EP', 'WO')
    name TEXT NOT NULL,
    jurisdiction_type VARCHAR(20) NOT NULL,  -- NATIONAL, STATE_PROVINCIAL, INTERNATIONAL_TREATY, REGIONAL, INTERNATIONAL_ORG
    parent_jurisdiction_id VARCHAR(50) REFERENCES jurisdictions(jurisdiction_id),
    iso_code VARCHAR(10),
    iso_subdivision_code VARCHAR(10),
    level INTEGER DEFAULT 0,  -- 0=root, 1=national, 2=state, etc.
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jurisdictions_parent ON jurisdictions(parent_jurisdiction_id);
CREATE INDEX idx_jurisdictions_type ON jurisdictions(jurisdiction_type);

-- Regulatory authorities
CREATE TABLE regulatory_authorities (
    authority_id VARCHAR(50) PRIMARY KEY,
    jurisdiction_id VARCHAR(50) NOT NULL REFERENCES jurisdictions(jurisdiction_id),
    name TEXT NOT NULL,
    authority_type VARCHAR(50),  -- PATENT_OFFICE, TM_REGISTRY, DRUG_CONTROLLER, BIODIVERSITY_AUTHORITY, etc.
    website_url TEXT,
    contact_info JSONB,
    powers TEXT[],  -- e.g., ['grant_patents', 'register_trademarks', 'approve_drugs']
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_authorities_jurisdiction ON regulatory_authorities(jurisdiction_id);
CREATE INDEX idx_authorities_type ON regulatory_authorities(authority_type);

-- Jurisdiction determination results
CREATE TABLE jurisdiction_determinations (
    determination_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL,
    applicable_jurisdictions JSONB NOT NULL,  -- Array of {jurisdiction_id, confidence, reason}
    primary_jurisdiction VARCHAR(50) REFERENCES jurisdictions(jurisdiction_id),
    applicable_authorities JSONB DEFAULT '[]',
    applicable_regimes JSONB DEFAULT '[]',  -- Legislation, rules, guidelines per jurisdiction
    temporal_context JSONB,  -- As-of date, prospective/retrospective
    conflicts JSONB DEFAULT '[]',
    resolution_notes TEXT,
    method VARCHAR(20) NOT NULL,  -- deterministic, llm_disambiguation, user_context
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jurisdiction_trace ON jurisdiction_determinations(trace_id);
CREATE INDEX idx_jurisdiction_primary ON jurisdiction_determinations(primary_jurisdiction);
```

### 2.10 Knowledge Graph (from Phase 7)

```sql
-- Graph entities (mirrored from graph DB for SQL querying)
CREATE TABLE graph_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_node_id VARCHAR(100) NOT NULL UNIQUE,  -- Node ID in graph DB
    entity_type VARCHAR(50) NOT NULL,  -- Act, Section, Case, Treaty, Formulation, etc.
    name TEXT NOT NULL,
    jurisdiction VARCHAR(50),
    authority_tier INTEGER,
    properties JSONB DEFAULT '{}',
    source_document_id UUID REFERENCES documents(document_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_graph_entities_type ON graph_entities(entity_type);
CREATE INDEX idx_graph_entities_jurisdiction ON graph_entities(jurisdiction);
CREATE INDEX idx_graph_entities_source ON graph_entities(source_document_id);
CREATE INDEX idx_graph_entities_name ON graph_entities USING GIN (name gin_trgm_ops);

-- Graph relationships (mirrored from graph DB)
CREATE TABLE graph_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_rel_id VARCHAR(100) NOT NULL UNIQUE,
    source_entity_id UUID NOT NULL REFERENCES graph_entities(entity_id),
    target_entity_id UUID NOT NULL REFERENCES graph_entities(entity_id),
    relationship_type VARCHAR(50) NOT NULL,  -- HAS_CHAPTER, AMENDS, INTERPRETS, IMPLEMENTS, etc.
    properties JSONB DEFAULT '{}',  -- e.g., {amendment_date: '2024-01-15', sections: ['3', '5']}
    confidence FLOAT DEFAULT 1.0,
    source_trace_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_graph_rels_source ON graph_relationships(source_entity_id);
CREATE INDEX idx_graph_rels_target ON graph_relationships(target_entity_id);
CREATE INDEX idx_graph_rels_type ON graph_relationships(relationship_type);
```

### 2.11 Evaluation System (from Phase 17)

```sql
-- Benchmark datasets
CREATE TABLE benchmark_datasets (
    dataset_id VARCHAR(100) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    query_count INTEGER NOT NULL,
    queries JSONB NOT NULL,  -- Array of {query_id, query, expected_answer, expected_citations, category, difficulty}
    ground_truth_source VARCHAR(50),  -- expert_annotated, synthetic, historical
    languages TEXT[] DEFAULT '{en}',
    jurisdictions TEXT[] DEFAULT '{IN}',
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluation cases (individual test cases)
CREATE TABLE evaluation_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(100) REFERENCES benchmark_datasets(dataset_id),
    query_id VARCHAR(100) NOT NULL,  -- Stable ID within dataset
    query TEXT NOT NULL,
    expected_answer TEXT,
    expected_citations JSONB DEFAULT '[]',  -- Array of {document_id, section, text_span}
    category VARCHAR(50),
    difficulty VARCHAR(20),  -- easy, medium, hard
    jurisdiction VARCHAR(50),
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_eval_cases_dataset ON evaluation_cases(dataset_id);
CREATE INDEX idx_eval_cases_category ON evaluation_cases(category);
CREATE INDEX idx_eval_cases_jurisdiction ON evaluation_cases(jurisdiction);

-- Experiment definitions
CREATE TABLE experiments (
    experiment_id VARCHAR(100) PRIMARY KEY,
    name TEXT NOT NULL,
    hypothesis TEXT,
    description TEXT,
    baseline_config JSONB NOT NULL,
    variant_configs JSONB NOT NULL,  -- Array of named configs
    dataset_id VARCHAR(100) REFERENCES benchmark_datasets(dataset_id),
    metrics_to_track TEXT[] NOT NULL,
    success_criteria JSONB,  -- e.g., {citation_precision: ">0.85", latency_p95: "<2000"}
    tags TEXT[],
    status VARCHAR(20) DEFAULT 'draft',  -- draft, running, completed, archived
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Experiment runs (from Phase 14)
CREATE TABLE experiment_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(100) NOT NULL REFERENCES experiments(experiment_id),
    variant_name VARCHAR(100) NOT NULL,  -- 'baseline' or variant name
    config_snapshot JSONB NOT NULL,
    dataset_version VARCHAR(50),
    dataset_hash CHAR(64),
    status VARCHAR(20) DEFAULT 'running',
    metrics JSONB DEFAULT '{}',
    per_case_metrics JSONB DEFAULT '[]',
    aggregate_metrics JSONB DEFAULT '{}',
    total_latency_ms BIGINT,
    avg_latency_ms FLOAT,
    p50_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0,
    failure_cases JSONB DEFAULT '[]',
    error_summary JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    git_commit VARCHAR(40),
    environment VARCHAR(20),
    notes TEXT
);

CREATE INDEX idx_exp_runs_experiment ON experiment_runs(experiment_id, started_at DESC);
CREATE INDEX idx_exp_runs_status ON experiment_runs(status);
CREATE INDEX idx_exp_runs_env ON experiment_runs(environment, started_at DESC);
```

### 2.12 Audit & Compliance (from Phase 19)

```sql
-- Audit log (immutable)
CREATE TABLE audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,  -- query, ingestion, admin, auth, data_export, data_delete
    actor_type VARCHAR(20) NOT NULL,  -- user, system, api_key, anonymous
    actor_id UUID,  -- user_id or api_key_id
    session_id UUID,
    trace_id UUID,
    resource_type VARCHAR(50),  -- document, query, user, session, etc.
    resource_id UUID,
    action VARCHAR(50) NOT NULL,  -- create, read, update, delete, export, classify, retrieve
    before_state JSONB,
    after_state JSONB,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Partition by month for performance
CREATE INDEX idx_audit_actor ON audit_events(actor_type, actor_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_events(resource_type, resource_id, created_at DESC);
CREATE INDEX idx_audit_trace ON audit_events(trace_id);
CREATE INDEX idx_audit_type ON audit_events(event_type, created_at DESC);

-- Data retention policies
CREATE TABLE retention_policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,  -- conversation_messages, audit_events, query_traces, etc.
    retention_days INTEGER NOT NULL,
    archive_after_days INTEGER,
    archive_storage_class VARCHAR(20),  -- standard, infrequent, glacier
    delete_after_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. Cross-Cutting Concerns

### 3.1 Soft Deletes Pattern

```sql
-- Add to all mutable tables
ALTER TABLE documents ADD COLUMN deleted_at TIMESTAMPTZ;
ALTER TABLE chunks ADD COLUMN deleted_at TIMESTAMPTZ;
ALTER TABLE conversation_sessions ADD COLUMN deleted_at TIMESTAMPTZ;
-- ... etc

-- Partial indexes for active records
CREATE INDEX idx_documents_active ON documents(document_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_chunks_active ON chunks(chunk_id) WHERE deleted_at IS NULL;
```

### 3.2 Optimistic Locking

```sql
-- Add version column to frequently updated tables
ALTER TABLE user_preferences ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE formulation_rules ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN version INTEGER DEFAULT 1;

-- Update trigger
CREATE OR REPLACE FUNCTION update_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_preferences_version
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_version();
```

### 3.3 Full-Text Search

```sql
-- Add tsvector column for full-text search on chunks
ALTER TABLE chunks ADD COLUMN search_vector TSVECTOR 
    GENERATED ALWAYS AS (to_tsvector('english', text_content)) STORED;

CREATE INDEX idx_chunks_fts ON chunks USING GIN (search_vector);

-- For multilingual: use pg_trgm for fuzzy search across languages
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_chunks_trgm ON chunks USING GIN (text_content gin_trgm_ops);
```

---

## 4. Relationship Diagram (ERD Summary)

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│   users     │───────│ user_sessions│       │  api_keys   │
└─────────────┘       └──────────────┘       └─────────────┘
      │                                               │
      │                    ┌────────────────────┐     │
      └───────────────────│  conversation_     │─────┘
                           │  sessions          │
                           └────────┬───────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
           ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
           │conversation_│ │conversation_ │ │  preference_ │
           │  messages   │ │  branches    │ │ learning_evt │
           └─────────────┘ └──────────────┘ └──────────────┘
                    │
                    │ (trace_id)
                    ▼
           ┌─────────────────────┐
           │      queries        │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │    query_traces     │
           └──────────┬──────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ formulation_ │ │jurisdic- │ │   evidence_  │
│classification│ │ tion_    │ │    refs      │
└──────────────┘ └──────────┘ └──────────────┘
         │            │            │
         ▼            ▼            ▼
┌─────────────────────────────────────────────┐
│           KNOWLEDGE CORPUS                  │
│  ┌─────────┐ ┌────────┐ ┌───────────────┐  │
│  │documents│ │ chunks │ │ legal_hierarchy│  │
│  └────┬────┘ └────┬───┘ └───────┬───────┘  │
│       │           │             │           │
│       ▼           ▼             ▼           │
│  ┌─────────────────────────────────────┐   │
│  │      chunk_embeddings (vector DB)   │   │
│  │      chunk_sparse_vectors (BM25)    │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│ Knowledge Graph │  │  Evaluation     │
│  (FalkorDB/     │  │  History        │
│   Neo4j)        │  │ (ClickHouse)    │
└─────────────────┘  └─────────────────┘
```

---

## 5. Migration Strategy

### 5.1 Versioning

```sql
-- Schema version tracking
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    checksum CHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    applied_by VARCHAR(100),
    execution_time_ms INTEGER
);
```

### 5.2 Migration Order (Dependencies)

1. **Core**: `users`, `sources`, `jurisdictions`, `regulatory_authorities`
2. **Documents**: `documents`, `document_versions`, `legal_hierarchy_nodes`
3. **Chunks**: `chunks`, `chunk_embeddings`, `chunk_sparse_vectors`
4. **Conversation**: `conversation_sessions`, `conversation_messages`, `conversation_branches`
5. **Preferences**: `user_preferences`, `preference_learning_events`
6. **Classification**: `formulation_classes`, `formulation_rules`, `formulation_classifications`
7. **Jurisdiction**: `jurisdiction_determinations`
8. **Citations**: `citations`, `evidence_refs`
9. **Queries**: `queries`, `query_traces`, `stage_executions`
10. **Graph Mirror**: `graph_entities`, `graph_relationships`
11. **Evaluation**: `benchmark_datasets`, `evaluation_cases`, `experiments`, `experiment_runs`
12. **Audit**: `audit_events` (partitioned), `retention_policies`

---

## 6. Indexing Strategy Summary

| Table | Primary Indexes | Secondary Indexes | Special Indexes |
|-------|-----------------|-------------------|-----------------|
| documents | PK, source_id | jurisdiction, type, authority, effective_date, content_hash, supersedes | GIN on metadata |
| chunks | PK, document_id | hierarchy_node, hierarchy_path (GIN), section, type, text_hash, parent | FTS (tsvector), trigram |
| conversation_sessions | PK | user_id+created_at, expires_at | - |
| conversation_messages | PK | session_id+created_at, trace_id, parent_message_id | - |
| queries | PK | session_id, user_id, trace_id, category | - |
| query_traces | PK | query_id, status, created_at | - |
| citations | PK | trace_id, message_id, chunk_ids (GIN), doc_ids (GIN) | - |
| evidence_refs | PK | trace_id, query_id, chunk_id, stage, selected | - |
| experiment_runs | PK | experiment_id+started_at, status, environment | - |
| audit_events | PK (partitioned) | actor, resource, trace_id, type+created_at | - |

---

## 7. Data Retention & Archival

| Table | Retention | Archive Strategy | Delete Strategy |
|-------|-----------|------------------|-----------------|
| documents | Permanent | Never | Never (legal record) |
| chunks | Permanent | Never | Never |
| conversation_sessions | 90 days (configurable) | Compress to Parquet in S3 | Hard delete after archive |
| conversation_messages | 90 days | Compress to Parquet in S3 | Hard delete after archive |
| user_preferences | Indefinite | - | On user deletion (GDPR) |
| queries | 1 year | Aggregate to ClickHouse | Delete raw, keep aggregates |
| query_traces | 90 days | Sample 10% for analysis | Delete |
| experiment_runs | Permanent | - | Never |
| audit_events | 7 years (compliance) | Compress to Parquet in S3 | Delete after 7 years |
| graph_entities/rels | Permanent | - | Never |

---

## 8. Open Research Questions

| ID | Question | Priority |
|----|----------|----------|
| ORQ-59 | Optimal chunk embedding dimension for legal multilingual retrieval? | High |
| ORQ-60 | PostgreSQL vs TimescaleDB for time-series evaluation metrics? | Medium |
| ORQ-61 | Graph entity mirror sync strategy (CDC vs batch)? | High |
| ORQ-62 | Partitioning strategy for audit_events at 1B+ rows/year? | Medium |
| ORQ-63 | Chunk deduplication across document versions (amendment handling)? | High |
| ORQ-64 | Optimal BM25 config hash granularity for cache invalidation? | Medium |

---

## 9. Implementation Checklist

- [ ] PostgreSQL schema with all tables, indexes, constraints
- [ ] Partitioning for audit_events (monthly)
- [ ] Migration system (golang-migrate or similar)
- [ ] Vector store abstraction (hnswlib + Milvus interface)
- [ ] Sparse vector store (BM25 index)
- [ ] Graph DB driver (FalkorDB/Neo4j)
- [ ] Analytics store (ClickHouse)
- [ ] Object storage integration (MinIO/S3)
- [ ] Soft delete implementation
- [ ] Optimistic locking triggers
- [ ] Full-text search setup (tsvector + trigram)
- [ ] Data retention cron jobs
- [ ] GDPR export/delete procedures
- [ ] Schema documentation (dbdocs or similar)
- [ ] Integration tests for all repositories
- [ ] Performance benchmarks for key queries