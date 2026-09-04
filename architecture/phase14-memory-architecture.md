# Phase 14: Memory Architecture

## 1. Overview

The Memory Architecture defines how IP-SAKTI Sahayak maintains state across conversations, sessions, and system restarts. It provides persistent, queryable storage for all knowledge artifacts while maintaining strict boundaries between memory types (ephemeral vs permanent, user-specific vs global).

### 1.1 Design Principles

1. **Separation of Concerns**: Distinct memory systems for conversation context, user preferences, retrieval cache, knowledge corpus, knowledge graph, and evaluation history
2. **Persistence Boundaries**: Clear demarcation between ephemeral (session) and persistent (cross-session) data
3. **Queryability**: All memory systems must support efficient search, filtering, and retrieval
4. **Consistency**: ACID guarantees for user data; eventual consistency for knowledge systems
5. **Privacy**: User data isolated by session/user; no cross-contamination
6. **Observability**: All memory operations logged for audit and debugging

### 1.2 Memory Taxonomy

| Memory Type | Persistence | Scope | Access Pattern | TTL |
|-------------|-------------|-------|----------------|-----|
| Conversation Memory | Session + Persistent | Per user/session | Sequential + Random access | 90 days (configurable) |
| User Preferences | Persistent | Per user | Key-value + structured | Indefinite |
| Retrieval Cache | Session + Persistent | Global | Key-value (query hash) | 24 hours (configurable) |
| Knowledge Corpus | Permanent | Global | Full-text + vector + metadata | Indefinite |
| Knowledge Graph | Permanent | Global | Graph traversal + Cypher | Indefinite |
| Evaluation History | Permanent | Global | Time-series + analytical | Indefinite |

---

## 2. Conversation Memory

### 2.1 Requirements

- Store full conversation history (user queries, assistant responses, citations, evidence)
- Support multi-turn context for follow-up questions
- Enable conversation branching (alternative response paths)
- Provide context window management for LLM input
- Support export/import for continuity across sessions
- Maintain audit trail with timestamps and trace IDs

### 2.2 Data Model

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class MessageType(Enum):
    TEXT = "text"
    STRUCTURED = "structured"  # Formulation classification, jurisdiction result
    CITATION = "citation"
    EVIDENCE = "evidence"
    ERROR = "error"

@dataclass
class Citation:
    citation_id: str
    chunk_ids: List[str]
    document_ids: List[str]
    section_path: str  # "Act > Chapter > Section"
    authority_tier: int
    jurisdiction: str
    text_span: str  # Exact text from source
    confidence: float

@dataclass
class EvidenceRef:
    chunk_id: str
    document_id: str
    score: float
    rank: int
    authority_tier: int
    jurisdiction: str
    section_path: str
    text_preview: str

@dataclass
class ConversationMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    user_id: str = ""
    role: MessageRole = MessageRole.USER
    message_type: MessageType = MessageType.TEXT
    content: str = ""
    structured_data: Optional[Dict[str, Any]] = None
    citations: List[Citation] = field(default_factory=list)
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    trace_id: str = ""
    parent_message_id: Optional[str] = None  # For branching
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0

@dataclass
class ConversationSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""  # Auto-generated from first query
    language: str = "en"
    jurisdiction_context: Optional[str] = None
    formulation_context: Optional[str] = None
    messages: List[ConversationMessage] = field(default_factory=list)
    active_branch_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_archived: bool = False
```

### 2.3 Context Window Management

```python
class ConversationContextManager:
    """
    Manages conversation context for LLM input within token budget.
    """
    
    def __init__(
        self,
        max_context_tokens: int = 8192,
        reserved_tokens: int = 2048,  # For system prompt, current query, response
        summary_threshold: int = 0.8  # Summarize when > 80% budget used
    ):
        self.max_context_tokens = max_context_tokens
        self.available_tokens = max_context_tokens - reserved_tokens
        self.summary_threshold = summary_threshold
    
    def build_context(
        self,
        session: ConversationSession,
        current_query: str,
        retrieval_results: List[EvidenceRef]
    ) -> List[ConversationMessage]:
        """
        Build context messages for LLM, including:
        1. System prompt (always included)
        2. Relevant conversation history (prioritized by recency + relevance)
        3. Current query with retrieved evidence
        4. Context summary if history truncated
        """
        messages = []
        
        # 1. System prompt (handled separately)
        
        # 2. Relevant history
        history_messages = self._select_relevant_history(
            session.messages,
            current_query,
            self.available_tokens
        )
        messages.extend(history_messages)
        
        # 3. Check if summarization needed
        used_tokens = sum(m.token_count for m in messages)
        if used_tokens > self.available_tokens * self.summary_threshold:
            summary = self._generate_summary(session.messages[:-len(history_messages)])
            messages.insert(0, ConversationMessage(
                role=MessageRole.SYSTEM,
                message_type=MessageType.TEXT,
                content=f"Previous conversation summary: {summary}",
                token_count=self._count_tokens(summary)
            ))
        
        return messages
    
    def _select_relevant_history(
        self,
        messages: List[ConversationMessage],
        query: str,
        token_budget: int
    ) -> List[ConversationMessage]:
        """
        Select most relevant messages using:
        - Recency weighting (exponential decay)
        - Semantic similarity to query (embedding-based)
        - Citation overlap with current retrieval
        """
        # Implementation: score each message, sort, take top-k within budget
        pass
    
    def _generate_summary(self, messages: List[ConversationMessage]) -> str:
        """Generate concise summary of old conversation turns."""
        # Use LLM to summarize key facts, decisions, classifications
        pass
```

### 2.4 Storage Backend

| Backend | Use Case | Configuration |
|---------|----------|---------------|
| **Redis** | Active session cache (sub-ms latency) | Cluster mode, TTL = session timeout |
| **PostgreSQL** | Persistent conversation history | Partitioned by user_id, indexed by session_id, created_at |
| **Object Storage (S3/MinIO)** | Full conversation exports, backups | Parquet format, partitioned by date |

```sql
-- PostgreSQL schema for conversation memory
CREATE TABLE conversation_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
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

CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES conversation_sessions(session_id),
    role VARCHAR(20) NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
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
```

### 2.5 Conversation Branching

Support for exploring alternative responses:

```python
@dataclass
class ConversationBranch:
    branch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    parent_message_id: str = ""  # Message where branch diverged
    branch_reason: str = ""  # "alternative_interpretation", "different_jurisdiction", "user_request"
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = False
```

---

## 3. User Preferences Memory

### 3.1 Requirements

- Store user-specific settings (language, jurisdiction, expertise level, citation style)
- Support profile-based defaults (attorney, researcher, student, regulator)
- Enable preference learning from interaction patterns
- Provide privacy controls (delete, export, anonymize)

### 3.2 Data Model

```python
@dataclass
class UserPreferences:
    user_id: str = ""
    
    # Language & Localization
    preferred_language: str = "en"
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    citation_language: str = "en"  # Language for citation display
    
    # Jurisdiction
    default_jurisdiction: str = "IN"  # ISO country code
    allowed_jurisdictions: List[str] = field(default_factory=lambda: ["IN"])
    jurisdiction_priority: List[str] = field(default_factory=list)  # Ordered preference
    
    # User Profile
    expertise_level: str = "general"  # "student", "general", "practitioner", "expert", "regulator"
    professional_role: str = ""  # "attorney", "researcher", "startup", "regulator", "student"
    organization: str = ""
    
    # Response Preferences
    citation_style: str = "detailed"  # "minimal", "standard", "detailed", "academic"
    response_length: str = "balanced"  # "concise", "balanced", "comprehensive"
    include_reasoning: bool = True
    include_confidence: bool = True
    include_alternatives: bool = False
    
    # Technical
    max_tokens_per_response: int = 4096
    enable_streaming: bool = True
    enable_caching: bool = True
    
    # Privacy
    data_retention_days: int = 90
    allow_analytics: bool = True
    allow_improvement: bool = True  # Use conversations for model improvement
    
    # Formulation Context
    default_formulation_class: Optional[str] = None
    preferred_regulatory_regime: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
```

### 3.3 Preference Profiles (Defaults by Role)

| Role | Expertise | Citation Style | Response Length | Default Jurisdiction |
|------|-----------|----------------|-----------------|---------------------|
| **Attorney** | Expert | Academic | Comprehensive | IN (with multi-jurisdiction) |
| **Researcher** | Expert | Academic | Comprehensive | IN + International |
| **Startup Founder** | Practitioner | Standard | Balanced | IN |
| **Regulator** | Expert | Detailed | Comprehensive | IN (all states) |
| **Student** | Student | Minimal | Concise | IN |
| **General** | General | Standard | Balanced | IN |

### 3.4 Storage

```sql
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY,
    preferences JSONB NOT NULL DEFAULT '{}',
    profile_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Preference learning log
CREATE TABLE preference_learning_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- "language_switch", "jurisdiction_change", "citation_style_change"
    old_value JSONB,
    new_value JSONB,
    trigger_context JSONB,  -- What caused the change
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Retrieval Cache

### 4.1 Requirements

- Cache query embeddings, sparse vectors, retrieval results, reranked results
- Multi-layer cache (L1: in-memory, L2: Redis, L3: persistent)
- Cache invalidation on corpus updates
- Cache warming for common queries
- Cost tracking (token savings, latency reduction)

### 4.2 Cache Layers

```python
from enum import Enum
from dataclasses import dataclass
from typing import Generic, TypeVar
import hashlib
import json

T = TypeVar('T')

class CacheLayer(Enum):
    L1_MEMORY = "memory"      # In-process, <1ms
    L2_REDIS = "redis"        # Distributed, <5ms
    L3_PERSISTENT = "disk"    # Persistent, <50ms

@dataclass
class CacheEntry(Generic[T]):
    key: str
    value: T
    layer: CacheLayer
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: Optional[int] = None

class RetrievalCache:
    """
    Multi-layer cache for retrieval pipeline.
    """
    
    def __init__(
        self,
        l1_max_size: int = 10000,      # In-memory entries
        l2_redis_url: str = "redis://localhost:6379",
        l3_path: str = "/data/cache/retrieval",
        default_ttl: int = 86400  # 24 hours
    ):
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l1_max_size = l1_max_size
        self.l2_client = redis.from_url(l2_redis_url)
        self.l3_path = Path(l3_path)
        self.default_ttl = default_ttl
        self.stats = CacheStats()
    
    def _make_key(self, *components: Any) -> str:
        """Generate deterministic cache key from components."""
        content = json.dumps(components, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    # Cache keys for each pipeline stage
    def get_query_embedding(self, query: str, model: str) -> Optional[np.ndarray]:
        key = self._make_key("embedding", model, query)
        return self._get(key, deserializer=np_from_bytes)
    
    def set_query_embedding(self, query: str, model: str, embedding: np.ndarray):
        key = self._make_key("embedding", model, query)
        self._set(key, embedding, serializer=np_to_bytes)
    
    def get_sparse_vector(self, query: str, config_hash: str) -> Optional[Dict]:
        key = self._make_key("sparse", config_hash, query)
        return self._get(key)
    
    def get_dense_results(self, query_embedding_hash: str, filters_hash: str, top_k: int) -> Optional[List]:
        key = self._make_key("dense", query_embedding_hash, filters_hash, top_k)
        return self._get(key)
    
    def get_reranked_results(self, query: str, candidate_hashes: List[str], reranker: str) -> Optional[List]:
        key = self._make_key("rerank", reranker, query, *candidate_hashes)
        return self._get(key)
    
    def get_final_results(self, query_hash: str, pipeline_config_hash: str) -> Optional[List]:
        key = self._make_key("final", pipeline_config_hash, query_hash)
        return self._get(key)
    
    def invalidate_corpus(self, document_ids: List[str]):
        """Invalidate all cache entries related to updated documents."""
        # Pattern-based invalidation in Redis
        # Full clear for L1/L3 (simpler, acceptable for corpus updates)
        pass
    
    def warm_cache(self, common_queries: List[str], pipeline_config: Dict):
        """Pre-populate cache for known frequent queries."""
        pass
```

### 4.3 Cache Invalidation Strategy

| Trigger | Invalidation Scope | Mechanism |
|---------|-------------------|-----------|
| Document added/updated | All entries involving document | Tag-based invalidation (document_id tags) |
| Corpus re-indexed | Full cache clear | Version prefix in all keys |
| Authority tier changed | Entries with affected chunks | Tier tag invalidation |
| Jurisdiction rules changed | Entries for affected jurisdiction | Jurisdiction tag invalidation |
| Embedding model changed | All embedding-dependent entries | Model version in key |

---

## 5. Knowledge Corpus Memory

### 5.1 Requirements

- Permanent storage of all ingested legal documents
- Full-text search + vector search + metadata filtering
- Version control with amendment chains
- Provenance tracking (source, extraction date, content hash)
- Support for 50M+ chunks at scale
- Efficient bulk operations (ingestion, re-indexing, deletion)

### 5.2 Data Model (from Phase 15)

```sql
-- Documents table (Phase 15)
CREATE TABLE documents (
    document_id UUID PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,  -- e.g., "ip_india", "nba", "cbd"
    authority_tier INTEGER NOT NULL,  -- 1-4
    jurisdiction VARCHAR(50) NOT NULL,  -- ISO code or "INTERNATIONAL"
    document_type VARCHAR(50) NOT NULL,  -- LEGISLATION, RULE, TREATY, etc.
    title TEXT NOT NULL,
    canonical_url TEXT,
    content_hash CHAR(64) NOT NULL,  -- SHA256
    version VARCHAR(50),  -- e.g., "2024-01-15", "Amendment 2023"
    effective_date DATE,
    supersedes_document_id UUID REFERENCES documents(document_id),
    superseded_by_document_id UUID REFERENCES documents(document_id),
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    ingestion_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    ingestion_started_at TIMESTAMPTZ,
    ingestion_completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks table (Phase 15)
CREATE TABLE chunks (
    chunk_id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(document_id),
    chunk_index INTEGER NOT NULL,  -- Order within document
    chunk_type VARCHAR(20) NOT NULL,  -- SECTION, DEFINITION, TABLE, etc.
    hierarchy_path TEXT NOT NULL,  -- "Act > Chapter > Section > Subsection"
    section_number VARCHAR(50),  -- e.g., "Section 3(b)", "Article 8"
    section_title TEXT,
    text_content TEXT NOT NULL,
    text_hash CHAR(64) NOT NULL,
    token_count INTEGER NOT NULL,
    char_start INTEGER,
    char_end INTEGER,
    parent_chunk_id UUID REFERENCES chunks(chunk_id),  -- For parent-child
    child_chunk_ids UUID[],
    metadata JSONB DEFAULT '{}',  -- Citations, cross-refs, definitions
    embedding_model VARCHAR(50),  -- e.g., "bge-m3"
    embedding_vector_id UUID,  -- Reference to vector store
    sparse_vector_id UUID,  -- Reference to BM25 index
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_hierarchy ON chunks USING GIN (hierarchy_path gin_trgm_ops);
CREATE INDEX idx_chunks_section ON chunks(section_number);
CREATE INDEX idx_chunks_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_text_hash ON chunks(text_hash);
```

### 5.3 Vector Storage

```python
class VectorStore:
    """
    Abstraction over vector database (hnswlib, FAISS, Milvus, pgvector).
    """
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.index = self._init_index()
        self.id_mapping: Dict[str, int] = {}  # chunk_id -> internal_id
    
    def _init_index(self):
        if self.config.backend == "hnswlib":
            import hnswlib
            index = hnswlib.Index(space='cosine', dim=self.config.dimension)
            index.init_index(
                max_elements=self.config.max_elements,
                ef_construction=self.config.ef_construction,
                M=self.config.M
            )
            return index
        # ... other backends
    
    def add(self, chunk_ids: List[str], vectors: np.ndarray):
        """Add vectors to index."""
        internal_ids = []
        for chunk_id in chunk_ids:
            if chunk_id not in self.id_mapping:
                self.id_mapping[chunk_id] = len(self.id_mapping)
            internal_ids.append(self.id_mapping[chunk_id])
        
        self.index.add_items(vectors, internal_ids)
    
    def search(self, query_vector: np.ndarray, k: int, filter_fn=None) -> List[Tuple[str, float]]:
        """Search with optional metadata filter."""
        # Apply filter by checking metadata in chunks table
        # For hnswlib: search large k, then filter
        pass
    
    def delete(self, chunk_ids: List[str]):
        """Mark vectors as deleted (hnswlib doesn't support true delete)."""
        # Use tombstone approach or rebuild
        pass
    
    def save(self, path: str):
        self.index.save_index(path)
        # Save id_mapping
    
    def load(self, path: str):
        self.index.load_index(path)
        # Load id_mapping
```

### 5.4 Sparse Vector Storage (BM25)

```python
class SparseVectorStore:
    """
    BM25 index using rank-bm25 or custom inverted index.
    """
    
    def __init__(self, config: SparseStoreConfig):
        self.config = config
        self.corpus: List[Dict] = []  # tokenized documents
        self.chunk_ids: List[str] = []
        self.doc_freq: Dict[str, int] = {}
        self.doc_len: List[int] = []
        self.avgdl: float = 0
    
    def build(self, chunks: List[Chunk]):
        """Build BM25 index from chunks."""
        for chunk in chunks:
            tokens = self._tokenize_legal(chunk.text_content)
            self.corpus.append(tokens)
            self.chunk_ids.append(chunk.chunk_id)
            self.doc_len.append(len(tokens))
            for token in set(tokens):
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0
    
    def search(self, query: str, k: int, filter_fn=None) -> List[Tuple[str, float]]:
        """BM25 search with optional filter."""
        query_tokens = self._tokenize_legal(query)
        scores = []
        for i, doc_tokens in enumerate(self.corpus):
            if filter_fn and not filter_fn(self.chunk_ids[i]):
                continue
            score = self._bm25_score(query_tokens, doc_tokens, self.doc_len[i])
            scores.append((self.chunk_ids[i], score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
```

---

## 6. Knowledge Graph Memory

### 6.1 Requirements (from Phase 7)

- Store entities and relationships as property graph
- Support temporal queries (version chains, amendment history)
- Enable graph traversal for multi-hop reasoning
- Support Cypher/GQL query language
- Scale to 10M+ nodes, 50M+ relationships

### 6.2 Graph Schema (Recap from Phase 7)

```cypher
// Core Entities
(:Act {act_id, title, jurisdiction, year, authority_tier, status})
(:Chapter {chapter_id, title, number, act_id})
(:Section {section_id, number, text, act_id, chapter_id, version, effective_date})
(:Subsection {subsection_id, number, text, section_id})
(:Clause {clause_id, number, text, subsection_id})
(:Definition {term, defined_text, section_id, scope})
(:Treaty {treaty_id, title, year, status, parties})
(:TreatyArticle {article_id, number, text, treaty_id})
(:Case {case_id, citation, court, date, jurisdiction, url})
(:Paragraph {paragraph_id, text, case_id, section_refs})
(:Guideline {guideline_id, title, authority, jurisdiction, effective_date})
(:Formulation {formulation_id, name, class, ingredients_json, preparation_method})
(:Ingredient {ingredient_id, name, scientific_name, synonyms, regulatory_status})
(:BiologicalResource {resource_id, scientific_name, common_name, geography, endangered_status})
(:ABSApplication {application_id, form_type, applicant, resource_ids, status, filed_date})
(:PatentRecord {patent_id, application_number, title, ipc_codes, status, filing_date})
(:TrademarkRecord {tm_id, mark, classes, status, proprietor, filing_date})
(:GIRecord {gi_id, name, goods, state, registration_number, registration_date})
(:TKEntry {tk_id, community, knowledge_domain, resource_ids, access_level})

// Core Relationships
(:Act)-[:HAS_CHAPTER]->(:Chapter)
(:Chapter)-[:HAS_SECTION]->(:Section)
(:Section)-[:HAS_SUBSECTION]->(:Subsection)
(:Subsection)-[:HAS_CLAUSE]->(:Clause)
(:Section)-[:HAS_DEFINITION]->(:Definition)

(:Act)-[:AMENDS]->(:Act)  // With properties: amendment_date, amendment_type, sections_affected
(:Section)-[:SUPERSEDES]->(:Section)  // Version chain
(:Act)-[:IMPLEMENTS]->(:Treaty)
(:Act)-[:DELEGATES_TO]->(:Guideline)

(:Case)-[:INTERPRETS]->(:Section)
(:Case)-[:CITES]->(:Case)
(:Case)-[:OVERRULES]->(:Case)
(:Case)-[:DISTINGUISHES]->(:Case)
(:Case)-[:FOLLOWS]->(:Case)

(:Formulation)-[:CLASSIFIED_AS]->(:FormulationClass)
(:Formulation)-[:CONTAINS]->(:Ingredient)
(:Ingredient)-[:DERIVED_FROM]->(:BiologicalResource)
(:Formulation)-[:REQUIRES_ABS]->(:BiologicalResource)
(:Formulation)-[:EXEMPT_FROM]->(:Requirement)

(:ABSApplication)-[:ACCESSES]->(:BiologicalResource)
(:ABSApplication)-[:FILED_UNDER]->(:Act)
```

### 6.3 Graph Database Selection

| Environment | Database | Rationale |
|-------------|----------|-----------|
| **Development/Hackathon** | FalkorDB | Redis-based, fast, Docker-native, Cypher support |
| **Production** | Neo4j Aura / Self-hosted | Mature, clustering, enterprise features, GQL standard |
| **Embedded/Edge** | Kuzu | Columnar, fast OLAP, Python-native, zero-copy |

### 6.4 Graph Operations

```python
class KnowledgeGraph:
    def __init__(self, config: GraphConfig):
        self.driver = self._connect(config)
    
    # Temporal queries
    def get_section_version_chain(self, section_id: str) -> List[SectionVersion]:
        """Get all versions of a section via SUPERSEDES chain."""
        query = """
        MATCH (s:Section {section_id: $section_id})
        OPTIONAL MATCH path = (s)-[:SUPERSEDES*]->(newer:Section)
        RETURN s, collect(newer) as versions
        ORDER BY newer.effective_date
        """
        return self.driver.execute(query, {"section_id": section_id})
    
    def get_applicable_version(self, section_id: str, as_of_date: date) -> Section:
        """Get section version effective on a specific date."""
        query = """
        MATCH (s:Section {section_id: $section_id})
        WHERE s.effective_date <= $as_of_date
        OPTIONAL MATCH (s)-[:SUPERSEDES]->(newer:Section)
        WHERE newer.effective_date <= $as_of_date
        WITH s, collect(newer) as newer_versions
        RETURN s, newer_versions
        ORDER BY s.effective_date DESC
        LIMIT 1
        """
        return self.driver.execute(query, {"section_id": section_id, "as_of_date": as_of_date})
    
    # Treaty implementation
    def get_implementing_legislation(self, treaty_id: str) -> List[Act]:
        query = """
        MATCH (a:Act)-[:IMPLEMENTS]->(t:Treaty {treaty_id: $treaty_id})
        RETURN a
        """
        return self.driver.execute(query, {"treaty_id": treaty_id})
    
    # Case law hierarchy
    def get_interpretation_chain(self, section_id: str) -> List[CaseInterpretation]:
        query = """
        MATCH (c:Case)-[:INTERPRETS]->(s:Section {section_id: $section_id})
        OPTIONAL MATCH (c)-[:CITES|OVERRULES|DISTINGUISHES|FOLLOWS*]->(related:Case)
        RETURN c, collect(related) as related_cases
        ORDER BY c.date DESC
        """
        return self.driver.execute(query, {"section_id": section_id})
    
    # Formulation classification
    def get_formulation_requirements(self, formulation_class: str) -> FormulationRequirements:
        query = """
        MATCH (fc:FormulationClass {name: $class})
        OPTIONAL MATCH (fc)-[:REQUIRES]->(req:Requirement)
        OPTIONAL MATCH (fc)-[:EXEMPT_FROM]->(exempt:Requirement)
        RETURN fc, collect(req) as requirements, collect(exempt) as exemptions
        """
        return self.driver.execute(query, {"class": formulation_class})
```

### 6.5 Graph Construction Pipeline

```python
class GraphBuilder:
    """
    Builds knowledge graph from Phase 5 chunks + separate ingestions.
    """
    
    def build_from_chunks(self, chunks: List[Chunk]):
        """Extract entities and relationships from legal chunks."""
        for chunk in chunks:
            # 1. Create hierarchy nodes
            self._create_hierarchy_nodes(chunk)
            
            # 2. Extract definitions
            self._extract_definitions(chunk)
            
            # 3. Extract cross-references
            self._extract_cross_references(chunk)
            
            # 4. Extract amendment relationships
            self._extract_amendments(chunk)
    
    def build_from_cases(self, cases: List[CaseDocument]):
        """Build case law graph from judgments."""
        pass
    
    def build_from_treaties(self, treaties: List[TreatyDocument]):
        """Build treaty implementation graph."""
        pass
    
    def build_formulation_kg(self, formulations: List[Formulation]):
        """Build formulation-ingredient-resource graph."""
        pass
```

---

## 7. Evaluation History Memory

### 7.1 Requirements

- Store all experiment runs with full configuration
- Track metrics over time for regression detection
- Enable comparison across experiments
- Support A/B test analysis
- Store failure cases for root cause analysis

### 7.2 Data Model

```python
@dataclass
class ExperimentRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""  # Links to experiment definition
    name: str = ""
    hypothesis: str = ""
    
    # Configuration (immutable snapshot)
    config: Dict[str, Any] = field(default_factory=dict)  # Full pipeline config
    dataset_version: str = ""
    dataset_hash: str = ""
    
    # Results
    status: str = "running"  # running, completed, failed, cancelled
    metrics: Dict[str, float] = field(default_factory=dict)
    per_query_metrics: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance
    total_latency_ms: int = 0
    avg_latency_ms: float = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    
    # Cost
    total_tokens: int = 0
    total_cost_usd: float = 0
    embedding_tokens: int = 0
    llm_tokens: int = 0
    
    # Quality
    citation_precision: float = 0
    citation_recall: float = 0
    groundedness: float = 0
    hallucination_rate: float = 0
    abstention_rate: float = 0
    
    # Failure Analysis
    failure_cases: List[FailureCase] = field(default_factory=list)
    error_summary: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    git_commit: str = ""
    environment: str = ""  # dev, staging, prod
    tags: List[str] = field(default_factory=list)
    notes: str = ""

@dataclass
class FailureCase:
    query: str
    expected: str
    actual: str
    error_type: str  # "hallucination", "missing_citation", "wrong_jurisdiction", "low_confidence"
    retrieval_results: List[Dict]
    trace_id: str
```

### 7.3 Storage Schema

```sql
CREATE TABLE experiment_runs (
    run_id UUID PRIMARY KEY,
    experiment_id VARCHAR(100) NOT NULL,
    name TEXT,
    hypothesis TEXT,
    config JSONB NOT NULL,
    dataset_version VARCHAR(100),
    dataset_hash CHAR(64),
    status VARCHAR(20) DEFAULT 'running',
    metrics JSONB DEFAULT '{}',
    per_query_metrics JSONB DEFAULT '[]',
    total_latency_ms INTEGER,
    avg_latency_ms FLOAT,
    p50_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0,
    embedding_tokens BIGINT DEFAULT 0,
    llm_tokens BIGINT DEFAULT 0,
    citation_precision FLOAT,
    citation_recall FLOAT,
    groundedness FLOAT,
    hallucination_rate FLOAT,
    abstention_rate FLOAT,
    failure_cases JSONB DEFAULT '[]',
    error_summary JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    git_commit VARCHAR(40),
    environment VARCHAR(20),
    tags TEXT[],
    notes TEXT
);

CREATE INDEX idx_experiment_runs_experiment ON experiment_runs(experiment_id, started_at DESC);
CREATE INDEX idx_experiment_runs_env ON experiment_runs(environment, started_at DESC);
CREATE INDEX idx_experiment_runs_status ON experiment_runs(status);
```

### 7.4 Experiment Comparison

```python
class ExperimentComparator:
    def compare_runs(self, run_ids: List[str]) -> ComparisonReport:
        """Compare multiple experiment runs."""
        runs = self._load_runs(run_ids)
        
        return ComparisonReport(
            baseline=run_ids[0] if run_ids else None,
            runs=runs,
            metric_comparison=self._compare_metrics(runs),
            latency_comparison=self._compare_latency(runs),
            cost_comparison=self._compare_cost(runs),
            quality_comparison=self._compare_quality(runs),
            regression_alerts=self._detect_regressions(runs),
            recommendations=self._generate_recommendations(runs)
        )
    
    def _detect_regressions(self, runs: List[ExperimentRun]) -> List[RegressionAlert]:
        """Detect statistically significant regressions."""
        # Compare each metric against baseline with confidence intervals
        pass
```

---

## 8. Persistence Boundaries & Data Flow

### 8.1 Memory Access Patterns

```
┌─────────────────────────────────────────────────────────────────────┐
                        QUERY REQUEST
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
                    QUERY UNDERSTANDING (Phase 3)
         ├─ Conversation Memory: Get session context, history
         ├─ User Preferences: Get language, jurisdiction, style prefs
         └─ Retrieval Cache: Check query embedding cache
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
                    JURISDICTION ENGINE (Phase 9)
         ├─ Knowledge Graph: Get jurisdiction hierarchy, treaties
         └─ User Preferences: Get allowed jurisdictions
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
                    FORMULATION CLASSIFIER (Phase 8)
         ├─ Knowledge Graph: Get formulation class hierarchy, ingredients
         └─ Knowledge Corpus: Get schedule/classification references
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
                    RETRIEVAL ENGINE (Phase 6)
         ├─ Retrieval Cache: Check all cache layers
         ├─ Knowledge Corpus: Vector + sparse search
         ├─ Knowledge Graph: Graph retrieval (if triggered)
         └─ User Preferences: Apply jurisdiction filters
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
                    GENERATION & VERIFICATION (Phase 10)
         ├─ Conversation Memory: Store response, citations, evidence
         ├─ Retrieval Cache: Cache final results
         └─ Evaluation History: Log if evaluation mode
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 Write Paths

| Operation | Memory Systems Written | Consistency |
|-----------|------------------------|-------------|
| New conversation message | Conversation (Redis + PG), Retrieval Cache (if cacheable) | Session: eventual; User: strong |
| User preference update | User Preferences (PG) | Strong |
| Document ingestion | Knowledge Corpus (PG + Vector + Sparse), Knowledge Graph | Eventual (async pipeline) |
| Graph update | Knowledge Graph | Strong (transactional) |
| Experiment run | Evaluation History (PG) | Strong |
| Cache population | Retrieval Cache (all layers) | Eventual |

### 8.3 Read Paths & Latency Budgets

| Memory System | Read Pattern | Latency Budget (p99) | Cache Strategy |
|---------------|--------------|---------------------|----------------|
| Conversation Memory | Session load, history fetch | 50ms | Redis L1 + PG |
| User Preferences | Key lookup | 10ms | Redis L1 (long TTL) |
| Retrieval Cache | Multi-layer lookup | 5ms (L1), 20ms (L2) | Tiered |
| Knowledge Corpus | Vector/sparse search | 100ms | Vector index in memory |
| Knowledge Graph | Cypher queries | 200ms | Query result cache |
| Evaluation History | Analytical queries | 500ms | Columnar (ClickHouse) |

---

## 9. Cross-Memory Operations

### 9.1 Conversation → Evaluation Linkage

```python
@dataclass
class EvaluationTrace:
    """Links conversation turn to evaluation ground truth."""
    trace_id: str
    session_id: str
    message_id: str
    evaluation_dataset: str  # e.g., "benchmark_v1"
    question_id: str
    expected_answer: str
    expected_citations: List[str]
    is_golden: bool = False  # Human-verified ground truth
```

### 9.2 Corpus Update Propagation

```python
class CorpusUpdatePropagator:
    """
    Handles cascade of corpus updates to all dependent memory systems.
    """
    
    def on_document_ingested(self, document: Document):
        # 1. Invalidate retrieval cache for affected chunks
        self.retrieval_cache.invalidate_document(document.document_id)
        
        # 2. Update knowledge graph (async)
        self.graph_builder.queue_document(document)
        
        # 3. Invalidate formulation classifier cache (if schedules changed)
        if self._affects_formulation_rules(document):
            self.formulation_classifier.invalidate_cache()
        
        # 4. Update jurisdiction engine (if new jurisdiction/regime)
        if self._affects_jurisdiction_mapping(document):
            self.jurisdiction_engine.invalidate_cache()
        
        # 5. Log for evaluation regression testing
        self.evaluation_history.log_corpus_change(document)
```

### 9.3 User Data Lifecycle

```python
class UserDataLifecycleManager:
    """
    Handles GDPR/privacy compliance for user data.
    """
    
    def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data (conversations, preferences, analytics)."""
        return UserDataExport(
            conversations=self.conversation_store.get_by_user(user_id),
            preferences=self.preference_store.get(user_id),
            analytics=self.analytics_store.get_by_user(user_id)
        )
    
    def delete_user_data(self, user_id: str, hard_delete: bool = False):
        """Delete or anonymize user data."""
        if hard_delete:
            self.conversation_store.hard_delete_user(user_id)
            self.preference_store.delete(user_id)
            self.analytics_store.delete_user(user_id)
        else:
            # Soft delete: anonymize, keep for aggregate analytics
            self.conversation_store.anonymize_user(user_id)
            self.preference_store.anonymize(user_id)
    
    def enforce_retention(self):
        """Enforce retention policies (cron job)."""
        expired_sessions = self.conversation_store.get_expired()
        for session in expired_sessions:
            if session.user_preferences.data_retention_days > 0:
                self.conversation_store.soft_delete(session.session_id)
```

---

## 10. Memory System APIs

### 10.1 Conversation Memory API

```python
class ConversationMemoryService:
    """gRPC service for conversation memory."""
    
    async def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        pass
    
    async def get_session(self, request: GetSessionRequest) -> SessionResponse:
        pass
    
    async def add_message(self, request: AddMessageRequest) -> MessageResponse:
        pass
    
    async def get_messages(self, request: GetMessagesRequest) -> MessagesResponse:
        pass
    
    async def create_branch(self, request: CreateBranchRequest) -> BranchResponse:
        pass
    
    async def switch_branch(self, request: SwitchBranchRequest) -> BranchResponse:
        pass
    
    async def archive_session(self, request: ArchiveSessionRequest) -> Empty:
        pass
    
    async def export_session(self, request: ExportSessionRequest) -> ExportResponse:
        pass
```

### 10.2 User Preferences API

```python
class UserPreferencesService:
    async def get_preferences(self, request: GetPreferencesRequest) -> PreferencesResponse:
        pass
    
    async def update_preferences(self, request: UpdatePreferencesRequest) -> PreferencesResponse:
        pass
    
    async def reset_to_defaults(self, request: ResetPreferencesRequest) -> PreferencesResponse:
        pass
    
    async def export_preferences(self, request: ExportPreferencesRequest) -> ExportResponse:
        pass
```

### 10.3 Retrieval Cache API (Internal)

```python
class RetrievalCacheService:
    async def get_embedding(self, request: GetEmbeddingRequest) -> EmbeddingResponse:
        pass
    
    async def set_embedding(self, request: SetEmbeddingRequest) -> Empty:
        pass
    
    async def get_retrieval_results(self, request: GetResultsRequest) -> ResultsResponse:
        pass
    
    async def set_retrieval_results(self, request: SetResultsRequest) -> Empty:
        pass
    
    async def invalidate(self, request: InvalidateRequest) -> InvalidateResponse:
        pass
    
    async def get_stats(self, request: StatsRequest) -> CacheStatsResponse:
        pass
```

---

## 11. Monitoring & Observability

### 11.1 Key Metrics

| Metric | Memory System | Alert Threshold |
|--------|---------------|-----------------|
| Session load latency | Conversation | > 100ms |
| Cache hit rate | Retrieval Cache | < 70% |
| Cache memory usage | Retrieval Cache (L1) | > 80% capacity |
| Vector index size | Knowledge Corpus | > 90% capacity |
| Graph query latency | Knowledge Graph | > 500ms |
| Experiment run duration | Evaluation History | > 2x baseline |
| User data export time | All user data | > 30s |
| Retention policy compliance | All | Any violation |

### 11.2 Health Checks

```python
class MemoryHealthCheck:
    async def check_all(self) -> HealthReport:
        checks = await asyncio.gather(
            self._check_conversation_memory(),
            self._check_user_preferences(),
            self._check_retrieval_cache(),
            self._check_knowledge_corpus(),
            self._check_knowledge_graph(),
            self._check_evaluation_history(),
            return_exceptions=True
        )
        return HealthReport(
            conversation=checks[0],
            preferences=checks[1],
            retrieval_cache=checks[2],
            corpus=checks[3],
            graph=checks[4],
            evaluation=checks[5],
            overall=all(c.status == "healthy" for c in checks if not isinstance(c, Exception))
        )
```

---

## 12. Open Research Questions

| ID | Question | Priority |
|----|----------|----------|
| ORQ-52 | Optimal conversation summarization strategy for legal context preservation? | High |
| ORQ-53 | Cache warming strategies for legal query distributions? | Medium |
| ORQ-54 | Graph database sharding strategy for 10M+ nodes? | Medium |
| ORQ-55 | Optimal TTL for retrieval cache given legal corpus update frequency? | Medium |
| ORQ-56 | Privacy-preserving preference learning without centralizing user data? | High |
| ORQ-57 | Cross-session context transfer for continuing research tasks? | Low |
| ORQ-58 | Vector index rebuild strategy for zero-downtime corpus updates? | High |

---

## 13. Implementation Checklist

- [ ] Conversation memory: Redis + PostgreSQL implementation
- [ ] Context window manager with summarization
- [ ] Conversation branching support
- [ ] User preferences service with profile defaults
- [ ] Preference learning event log
- [ ] Multi-layer retrieval cache (L1/L2/L3)
- [ ] Cache invalidation framework
- [ ] Knowledge corpus: PostgreSQL + hnswlib + BM25
- [ ] Vector store abstraction with multiple backends
- [ ] Knowledge graph: FalkorDB/Neo4j driver
- [ ] Graph construction pipeline from chunks
- [ ] Evaluation history store with comparison tools
- [ ] User data lifecycle manager (export, delete, retention)
- [ ] Cross-memory propagation for corpus updates
- [ ] Memory health checks and monitoring
- [ ] Integration tests for all memory systems
- [ ] Performance benchmarks for each memory system