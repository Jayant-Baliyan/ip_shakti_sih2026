# Phase 16: API Architecture

## 1. Overview

This document defines the complete API architecture for IP-SAKTI Sahayak, covering all external and internal APIs. The architecture follows REST principles for synchronous operations, gRPC for high-performance internal communication, and Server-Sent Events (SSE) for streaming responses.

### 1.1 Design Principles

1. **API-First**: All functionality exposed via well-defined APIs
2. **Versioning**: URL-based versioning (`/v1/`, `/v2/`) with semantic versioning
3. **Consistency**: Uniform request/response formats, error handling, pagination
4. **Security**: Authentication, authorization, rate limiting on all endpoints
5. **Observability**: Request tracing, structured logging, metrics on every endpoint
6. **Backward Compatibility**: No breaking changes within major version
7. **Idempotency**: Safe retries for mutating operations via idempotency keys

### 1.2 API Surface Summary

| API Group | Protocol | Base Path | Description |
|-----------|----------|-----------|-------------|
| **Query API** | REST + SSE | `/v1/query` | Main user-facing query interface |
| **Retrieval API** | REST | `/v1/retrieval` | Direct retrieval for debugging/analysis |
| **Evidence API** | REST | `/v1/evidence` | Evidence inspection and verification |
| **Citation API** | REST | `/v1/citations` | Citation verification and formatting |
| **Formulation API** | REST | `/v1/formulation` | Formulation classification |
| **Jurisdiction API** | REST | `/v1/jurisdiction` | Jurisdiction detection and mapping |
| **Document API** | REST | `/v1/documents` | Document ingestion and management |
| **Evaluation API** | REST | `/v1/evaluation` | Benchmark and experiment management |
| **Admin API** | REST | `/v1/admin` | System administration |
| **Audit API** | REST | `/v1/audit` | Audit log access |
| **Internal gRPC** | gRPC | `grpc://internal` | Inter-service communication |

---

## 2. Common Patterns

### 2.1 Request/Response Envelope

```json
// Success Response
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-09-03T10:00:00Z",
    "version": "1.0.0",
    "trace_id": "uuid"
  }
}

// Error Response
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { ... },
    "retryable": false
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-09-03T10:00:00Z",
    "version": "1.0.0",
    "trace_id": "uuid"
  }
}
```

### 2.2 Standard Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <jwt>` or `ApiKey <key>` |
| `Idempotency-Key` | For mutations | UUID for safe retries |
| `X-Request-ID` | Auto-generated | Client-provided or generated |
| `X-Trace-ID` | Auto-generated | Distributed tracing |
| `Accept-Language` | Optional | Preferred response language |
| `Accept` | Yes | `application/json`, `text/event-stream` |

### 2.3 Pagination

```json
// Request
GET /v1/documents?page=1&page_size=20&sort=created_at:desc

// Response
{
  "success": true,
  "data": [...],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 2.4 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHENTICATED` | 401 | Missing or invalid auth |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate) |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Dependency unavailable |
| `UPSTREAM_TIMEOUT` | 504 | Upstream service timeout |

---

## 3. Query API

### 3.1 Submit Query (Streaming)

```http
POST /v1/query/stream
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer <token>
Idempotency-Key: <uuid>
```

**Request:**
```json
{
  "query": "What are the patentability requirements for pharmaceutical formulations in India?",
  "session_id": "uuid",  // Optional, for conversation continuity
  "language": "en",       // Optional, defaults to user preference
  "jurisdiction": "IN",   // Optional, auto-detected if omitted
  "formulation_class": null,  // Optional, auto-classified if omitted
  "options": {
    "include_reasoning": true,
    "include_citations": true,
    "include_confidence": true,
    "include_alternatives": false,
    "max_tokens": 4096,
    "stream": true
  },
  "context": {
    "user_role": "attorney",
    "previous_classifications": []
  }
}
```

**Response (SSE Stream):**
```
event: metadata
data: {"trace_id": "uuid", "stage": "understanding", "progress": 0.1}

event: stage
data: {"stage": "jurisdiction_detection", "result": {"jurisdiction": "IN", "confidence": 0.98}}

event: stage
data: {"stage": "formulation_classification", "result": {"class": "patent_proprietary", "confidence": 0.92}}

event: stage
data: {"stage": "retrieval", "result": {"candidates": 150, "selected": 12, "confidence": 0.87}}

event: stage
data: {"stage": "generation", "delta": "Based on Section 3(d) of the Patents Act..."}

event: stage
data: {"stage": "generation", "delta": " the patentability requirements include..."}

event: citations
data: {"citations": [{"citation_id": "uuid", "text": "Section 3(d)...", "authority_tier": 1, "jurisdiction": "IN"}]}

event: complete
data: {"answer": "Based on Section 3(d)...", "confidence": 0.89, "abstained": false}

event: done
data: {"trace_id": "uuid", "total_latency_ms": 2340, "token_usage": {"prompt": 1200, "completion": 800}}
```

### 3.2 Submit Query (Non-Streaming)

```http
POST /v1/query
Content-Type: application/json
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "trace_id": "uuid",
    "answer": "Based on Section 3(d) of the Patents Act 1970...",
    "confidence": 0.89,
    "abstained": false,
    "abstention_reason": null,
    "citations": [
      {
        "citation_id": "uuid",
        "text": "Section 3(d) states...",
        "document_id": "uuid",
        "section": "Section 3(d)",
        "act": "Patents Act 1970",
        "authority_tier": 1,
        "jurisdiction": "IN",
        "url": "https://indiacode.nic.in/.../section-3"
      }
    ],
    "reasoning": "The query asks about patentability...",
    "alternatives": [],
    "metadata": {
      "jurisdiction": "IN",
      "formulation_class": "patent_proprietary",
      "retrieval_stats": {"candidates": 150, "selected": 12, "confidence": 0.87},
      "latency_ms": 2340,
      "token_usage": {"embedding": 500, "llm_prompt": 1200, "llm_completion": 800}
    }
  }
}
```

### 3.3 Get Query History

```http
GET /v1/query/history?session_id=uuid&page=1&page_size=20
```

### 3.4 Get Query Trace (Debugging)

```http
GET /v1/query/trace/{trace_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "trace_id": "uuid",
    "query": "What are the patentability requirements...",
    "stages": [
      {"name": "understanding", "latency_ms": 45, "status": "completed", "output": {...}},
      {"name": "jurisdiction_detection", "latency_ms": 120, "status": "completed", "output": {...}},
      {"name": "formulation_classification", "latency_ms": 340, "status": "completed", "output": {...}},
      {"name": "retrieval", "latency_ms": 890, "status": "completed", "output": {...}},
      {"name": "reranking", "latency_ms": 450, "status": "completed", "output": {...}},
      {"name": "evidence_selection", "latency_ms": 120, "status": "completed", "output": {...}},
      {"name": "generation", "latency_ms": 680, "status": "completed", "output": {...}},
      {"name": "verification", "latency_ms": 210, "status": "completed", "output": {...}}
    ],
    "total_latency_ms": 2340,
    "final_confidence": 0.89
  }
}
```

---

## 4. Retrieval API

### 4.1 Direct Retrieval

```http
POST /v1/retrieval/search
Content-Type: application/json
Authorization: Bearer <token>
```

**Request:**
```json
{
  "query": "Section 3(d) patentability pharmaceutical",
  "filters": {
    "jurisdiction": ["IN"],
    "authority_tier": [1, 2],
    "document_type": ["LEGISLATION", "RULE"],
    "effective_date_range": {"from": "2000-01-01", "to": "2026-12-31"},
    "languages": ["en", "hi"]
  },
  "options": {
    "sparse_weight": 1.0,
    "dense_weight": 1.0,
    "rrf_k": 60,
    "top_k": 50,
    "rerank": true,
    "rerank_top_k": 20,
    "mmr_lambda": 0.7,
    "include_vectors": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "chunk_id": "uuid",
        "document_id": "uuid",
        "rank": 1,
        "score": 0.92,
        "sparse_score": 0.85,
        "dense_score": 0.88,
        "rerank_score": 0.92,
        "authority_tier": 1,
        "jurisdiction": "IN",
        "hierarchy_path": "Patents Act 1970 > Chapter II > Section 3 > Section 3(d)",
        "section_number": "Section 3(d)",
        "section_title": "What are not inventions",
        "text_preview": "The mere discovery of a new form of a known substance...",
        "token_count": 450,
        "metadata": {"citations": [], "definitions": []}
      }
    ],
    "stats": {
      "sparse_candidates": 200,
      "dense_candidates": 200,
      "fused_candidates": 150,
      "reranked": 20,
      "selected": 12,
      "latency_ms": {"sparse": 15, "dense": 45, "fusion": 5, "rerank": 450, "mmr": 10}
    }
  }
}
```

### 4.2 Retrieve by Chunk IDs

```http
POST /v1/retrieval/chunks
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "chunk_ids": ["uuid1", "uuid2", "uuid3"],
  "include_context": true,
  "context_window": 1  // Parent + child chunks
}
```

### 4.3 Retrieve by Document

```http
GET /v1/retrieval/documents/{document_id}/chunks?section=3(d)&include_children=true
```

---

## 5. Evidence API

### 5.1 Get Evidence for Trace

```http
GET /v1/evidence/trace/{trace_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "trace_id": "uuid",
    "evidence": [
      {
        "evidence_id": "uuid",
        "chunk_id": "uuid",
        "document_id": "uuid",
        "retrieval_stage": "reranked",
        "rank": 1,
        "score": 0.92,
        "authority_tier": 1,
        "jurisdiction": "IN",
        "hierarchy_path": "Patents Act 1970 > Chapter II > Section 3 > Section 3(d)",
        "text": "Full chunk text...",
        "is_selected": true,
        "used_in_answer": true,
        "citation_ids": ["uuid1", "uuid2"]
      }
    ],
    "stats": {
      "total_retrieved": 150,
      "after_rerank": 20,
      "selected_for_context": 12,
      "cited_in_answer": 5
    }
  }
}
```

### 5.2 Verify Evidence Claim

```http
POST /v1/evidence/verify
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "claim": "Section 3(d) prevents evergreening of pharmaceutical patents",
  "evidence_chunk_ids": ["uuid1", "uuid2"],
  "verification_type": "entailment"  // entailment, groundedness, citation_accuracy
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "claim": "Section 3(d) prevents evergreening...",
    "verification": {
      "entailment_score": 0.91,
      "groundedness_score": 0.94,
      "citation_accuracy": 0.98,
      "overall": "verified",
      "details": {
        "supporting_chunks": ["uuid1"],
        "contradicting_chunks": [],
        "missing_evidence": []
      }
    }
  }
}
```

---

## 6. Citation API

### 6.1 Format Citation

```http
POST /v1/citations/format
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "citation_ids": ["uuid1", "uuid2"],
  "style": "academic",  // minimal, standard, detailed, academic, bluebook
  "language": "en"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "formatted": [
      "Patents Act 1970, § 3(d) (India).",
      "Novartis AG v. Union of India, (2013) 6 SCC 1 (Supreme Court of India)."
    ],
    "citations": [
      {
        "citation_id": "uuid1",
        "formatted": "Patents Act 1970, § 3(d) (India).",
        "components": {
          "act": "Patents Act 1970",
          "section": "3(d)",
          "jurisdiction": "India",
          "url": "https://indiacode.nic.in/..."
        }
      }
    ]
  }
}
```

### 6.2 Verify Citation

```http
POST /v1/citations/verify
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "citation_id": "uuid",
  "claimed_text": "The mere discovery of a new form...",
  "claimed_section": "Section 3(d)",
  "claimed_act": "Patents Act 1970"
}
```

---

## 7. Formulation Classification API

### 7.1 Classify Formulation

```http
POST /v1/formulation/classify
Content-Type: application/json
Authorization: Bearer <token>
```

**Request:**
```json
{
  "ingredients": [
    {
      "name": "Curcuma longa",
      "quantity": "500mg",
      "unit": "mg",
      "role": "active",
      "part_used": "rhizome",
      "preparation": "powder"
    },
    {
      "name": "Piper nigrum",
      "quantity": "50mg",
      "unit": "mg",
      "role": "bioenhancer",
      "part_used": "fruit",
      "preparation": "powder"
    }
  ],
  "dosage_form": "tablet",
  "preparation_method": "Classical Ayurvedic preparation per Ayurvedic Formulary",
  "intended_use": "Anti-inflammatory, digestive aid",
  "claims": ["Reduces inflammation", "Improves digestion"],
  "classical_reference": {
    "text": "Ayurvedic Formulary of India",
    "formula_name": "Haridra Khanda",
    "chapter": "Khanda",
    "verse": "12"
  },
  "manufacturer_info": {
    "name": "ABC Ayurveda Ltd",
    "license_number": "AYU/MP/2024/001",
    "state": "Madhya Pradesh"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "classification_id": "uuid",
    "determined_class": "classical_medicine",
    "confidence": 0.96,
    "method": "deterministic",
    "rule_matches": [
      {
        "rule_id": "CLASSICAL_001",
        "name": "Classical Text Reference",
        "matched": true,
        "legal_basis": "D&C Act Schedule E(1), Rule 158"
      },
      {
        "rule_id": "CLASSICAL_002",
        "name": "Classical Preparation Method",
        "matched": true,
        "legal_basis": "D&C Rules Rule 158"
      }
    ],
    "llm_reasoning": null,
    "conflicts": [],
    "escalation_triggers": [],
    "regulatory_output": {
      "applicable_regimes": [
        {"regime": "D&C Act 1940", "authority": "Central Drugs Standard Control Organization"},
        {"regime": "ASU Drugs Rules 2016", "authority": "State Licensing Authority"},
        {"regime": "Ayurvedic Pharmacopoeia", "authority": "Pharmacopoeia Commission for Indian Medicine"}
      ],
      "licensing_requirements": [
        {"requirement": "Manufacturing License (Form 25-D)", "authority": "State Licensing Authority"},
        {"requirement": "GMP Certification", "authority": "CDSCO"},
        {"requirement": "Label Approval", "authority": "State Licensing Authority"}
      ],
      "abs_requirements": {
        "required": false,
        "reason": "Classical formulation with ingredients from cultivated sources",
        "form_type": null
      },
      "labeling_requirements": [
        "Name of formulation",
        "List of ingredients with quantities",
        "Classical reference",
        "Manufacturer details",
        "Batch number",
        "Expiry date",
        "License number",
        "Ayurvedic logo"
      ]
    }
  }
}
```

### 7.2 Get Formulation Classes

```http
GET /v1/formulation/classes
```

### 7.3 Get Classification Rules

```http
GET /v1/formulation/rules?class=classical_medicine
```

---

## 8. Jurisdiction API

### 8.1 Detect Jurisdiction

```http
POST /v1/jurisdiction/detect
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "query": "Patent filing requirements for AI inventions",
  "user_context": {
    "user_jurisdiction": "IN",
    "allowed_jurisdictions": ["IN", "US", "EP", "WO"]
  },
  "formulation_class": null
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "determination_id": "uuid",
    "applicable_jurisdictions": [
      {"jurisdiction_id": "IN", "confidence": 0.95, "reason": "User context + Indian patent law query"},
      {"jurisdiction_id": "US", "confidence": 0.30, "reason": "Comparative reference possible"},
      {"jurisdiction_id": "EP", "confidence": 0.25, "reason": "EPO guidelines relevant"}
    ],
    "primary_jurisdiction": "IN",
    "applicable_authorities": [
      {"authority_id": "in_ip_india", "name": "Intellectual Property India", "type": "PATENT_OFFICE"}
    ],
    "applicable_regimes": [
      {"jurisdiction": "IN", "legislation": ["Patents Act 1970", "Patents Rules 2003"], "guidelines": ["CRI Guidelines 2017"]}
    ],
    "temporal_context": {"as_of": "2026-09-03", "prospective_only": false},
    "conflicts": [],
    "confidence": 0.92
  }
}
```

### 8.2 Get Jurisdiction Hierarchy

```http
GET /v1/jurisdiction/hierarchy?jurisdiction=IN
```

### 8.3 Get Applicable Regimes

```http
GET /v1/jurisdiction/regimes?jurisdiction=IN&formulation_class=patent_proprietary
```

---

## 9. Document Ingestion API

### 9.1 Ingest Document

```http
POST /v1/documents/ingest
Content-Type: multipart/form-data
Authorization: Bearer <admin_token>
```

**Form Data:**
- `file`: PDF/HTML/DOCX file
- `metadata`: JSON string with:
```json
{
  "source_id": "ip_india",
  "document_type": "LEGISLATION",
  "jurisdiction": "IN",
  "authority_tier": 1,
  "title": "Patents (Amendment) Act 2024",
  "canonical_url": "https://ipindia.gov.in/...",
  "effective_date": "2024-03-15",
  "version": "Amendment 2024",
  "language": "en",
  "supersedes_document_id": "uuid"
}
```

### 9.2 Get Ingestion Status

```http
GET /v1/documents/{document_id}/status
```

### 9.3 Trigger Re-ingestion

```http
POST /v1/documents/{document_id}/reingest
Authorization: Bearer <admin_token>
```

### 9.4 List Documents

```http
GET /v1/documents?source_id=ip_india&status=completed&page=1&page_size=50
```

---

## 10. Evaluation API

### 10.1 Run Evaluation

```http
POST /v1/evaluation/run
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "experiment_id": "exp_patent_retrieval_v2",
  "variant": "hybrid_rerank_mmr",
  "dataset_id": "benchmark_v1",
  "config_overrides": {
    "rrf_k": 50,
    "mmr_lambda": 0.6
  }
}
```

### 10.2 Get Evaluation Results

```http
GET /v1/evaluation/runs/{run_id}
```

### 10.3 Compare Runs

```http
POST /v1/evaluation/compare
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "run_ids": ["uuid1", "uuid2", "uuid3"],
  "metrics": ["citation_precision", "latency_p95", "hallucination_rate"]
}
```

### 10.4 List Benchmarks

```http
GET /v1/evaluation/benchmarks
```

---

## 11. Admin API

### 11.1 System Health

```http
GET /v1/admin/health
Authorization: Bearer <admin_token>
```

### 11.2 System Metrics

```http
GET /v1/admin/metrics?since=1h
Authorization: Bearer <admin_token>
```

### 11.3 Cache Management

```http
POST /v1/admin/cache/invalidate
Authorization: Bearer <admin_token>
```

```json
{
  "pattern": "retrieval:*",
  "layer": "all"  // l1, l2, l3, all
}
```

### 11.4 Corpus Management

```http
POST /v1/admin/corpus/reindex
Authorization: Bearer <admin_token>
```

```json
{
  "source_ids": ["ip_india", "nba"],
  "document_types": ["LEGISLATION"],
  "force": false
}
```

### 11.5 User Management

```http
GET /v1/admin/users?page=1&page_size=50
POST /v1/admin/users/{user_id}/suspend
POST /v1/admin/users/{user_id}/unsuspend
GET /v1/admin/users/{user_id}/usage
```

---

## 12. Audit API

### 12.1 Query Audit Logs

```http
GET /v1/audit/logs?actor_id=uuid&event_type=query&from=2026-09-01&to=2026-09-03&page=1&page_size=100
Authorization: Bearer <admin_token>
```

### 12.2 Get Audit Event

```http
GET /v1/audit/events/{event_id}
Authorization: Bearer <admin_token>
```

### 12.3 Export Audit Logs

```http
POST /v1/audit/export
Authorization: Bearer <admin_token>
```

```json
{
  "format": "csv",  // csv, json, parquet
  "filters": {...},
  "date_range": {"from": "2026-09-01", "to": "2026-09-03"}
}
```

---

## 13. Internal gRPC APIs

### 13.1 Service Definitions

```protobuf
// query_service.proto
service QueryService {
  rpc ProcessQuery(QueryRequest) returns (stream QueryResponse);
  rpc GetTrace(TraceRequest) returns (TraceResponse);
}

// retrieval_service.proto
service RetrievalService {
  rpc Search(SearchRequest) returns (SearchResponse);
  rpc GetChunks(ChunksRequest) returns (ChunksResponse);
  rpc WarmCache(WarmCacheRequest) returns (WarmCacheResponse);
}

// formulation_service.proto
service FormulationService {
  rpc Classify(ClassifyRequest) returns (ClassifyResponse);
  rpc GetRules(GetRulesRequest) returns (RulesResponse);
}

// jurisdiction_service.proto
service JurisdictionService {
  rpc Detect(DetectRequest) returns (DetectResponse);
  rpc GetRegimes(GetRegimesRequest) returns (RegimesResponse);
}

// ingestion_service.proto
service IngestionService {
  rpc Ingest(IngestRequest) returns (IngestResponse);
  rpc GetStatus(StatusRequest) returns (StatusResponse);
}

// evaluation_service.proto
service EvaluationService {
  rpc RunExperiment(RunRequest) returns (RunResponse);
  rpc GetResults(ResultsRequest) returns (ResultsResponse);
}
```

---

## 14. Authentication & Authorization

### 14.1 Authentication Methods

| Method | Use Case | Token Format |
|--------|----------|--------------|
| **JWT (Access Token)** | User sessions | `Bearer eyJhbGciOiJIUzI1NiIs...` |
| **API Key** | Programmatic access | `ApiKey sk_live_abc123...` |
| **Service Token** | Internal service-to-service | `Bearer <service_jwt>` |

### 14.2 JWT Claims

```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "role": "attorney",
  "permissions": ["query", "formulation:classify", "retrieval:search"],
  "rate_limit_tier": "professional",
  "iat": 1693700000,
  "exp": 1693703600,
  "jti": "token_uuid"
}
```

### 14.3 Role-Based Access Control

| Role | Query | Formulation | Retrieval | Documents | Evaluation | Admin |
|------|-------|-------------|-----------|-----------|------------|-------|
| **Student** | ✅ | ❌ | ✅ (limited) | ❌ | ✅ (view) | ❌ |
| **General** | ✅ | ✅ | ✅ | ❌ | ✅ (view) | ❌ |
| **Practitioner** | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Researcher** | ✅ | ✅ | ✅ | ✅ (view) | ✅ | ❌ |
| **Regulator** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 14.4 Rate Limiting

| Tier | Requests/min | Queries/hour | Tokens/day | Burst |
|------|--------------|--------------|------------|-------|
| **Free** | 10 | 50 | 10,000 | 20 |
| **Standard** | 30 | 200 | 100,000 | 50 |
| **Professional** | 100 | 1,000 | 1,000,000 | 200 |
| **Enterprise** | 500 | 10,000 | Unlimited | 1000 |

---

## 15. API Versioning Strategy

### 15.1 Version Header

```
Accept: application/vnd.ip-sakti.v1+json
```

### 15.2 URL Versioning (Primary)

```
/v1/query
/v2/query
```

### 15.3 Deprecation Policy

1. **Announce**: 6 months before deprecation
2. **Deprecate**: Mark in docs, add `Deprecation` header
3. **Remove**: After 12 months minimum

### 15.4 Version Compatibility Matrix

| Client Version | Server v1 | Server v2 |
|----------------|-----------|-----------|
| Client v1 | ✅ | ✅ (with warnings) |
| Client v2 | ❌ | ✅ |

---

## 16. Request/Response Examples

### 16.1 Complex Query with All Options

```http
POST /v1/query
Content-Type: application/json
Authorization: Bearer <token>
Accept-Language: hi
```

```json
{
  "query": "पेटेंट अधिनियम की धारा 3(घ) के तहत फार्मास्यूटिकल पेटेंट की क्या आवश्यकताएं हैं?",
  "session_id": "uuid",
  "language": "hi",
  "jurisdiction": "IN",
  "options": {
    "include_reasoning": true,
    "include_citations": true,
    "include_confidence": true,
    "include_alternatives": true,
    "max_tokens": 4096,
    "citation_style": "academic"
  },
  "context": {
    "user_role": "attorney",
    "case_reference": "Novartis v. Union of India"
  }
}
```

### 16.2 Error Response Example

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Query validation failed",
    "details": {
      "field": "query",
      "issue": "Query too short (minimum 10 characters)",
      "value": "patent"
    },
    "retryable": false
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-09-03T10:00:00Z",
    "version": "1.0.0",
    "trace_id": "uuid"
  }
}
```

---

## 17. WebSocket API (Real-time)

### 17.1 Connection

```
GET /v1/ws?token=<jwt>
```

### 17.2 Messages

```json
// Client -> Server
{"type": "query", "payload": {...}, "request_id": "uuid"}

// Server -> Client
{"type": "stage_update", "request_id": "uuid", "payload": {...}}
{"type": "token", "request_id": "uuid", "payload": {"delta": "..."}}
{"type": "complete", "request_id": "uuid", "payload": {...}}
{"type": "error", "request_id": "uuid", "payload": {...}}
```

---

## 18. SDKs & Client Libraries

### 18.1 Python SDK

```python
from ip_sakti import Client

client = Client(api_key="sk_live_...", base_url="https://api.ip-sakti.in")

# Simple query
result = client.query("What is Section 3(d)?")

# Streaming query
for event in client.query_stream("Patent requirements for AI inventions"):
    if event.type == "token":
        print(event.delta, end="", flush=True)
    elif event.type == "citations":
        print("\nCitations:", event.citations)

# Formulation classification
classification = client.formulation.classify(
    ingredients=[{"name": "Curcuma longa", "quantity": "500mg"}],
    dosage_form="tablet",
    intended_use="Anti-inflammatory"
)

# Direct retrieval
results = client.retrieval.search(
    query="Section 3(d) pharmaceutical",
    filters={"jurisdiction": ["IN"], "authority_tier": [1, 2]},
    top_k=20
)
```

### 18.2 JavaScript/TypeScript SDK

```typescript
import { IpSaktiClient } from '@ip-sakti/sdk';

const client = new IpSaktiClient({
  apiKey: 'sk_live_...',
  baseUrl: 'https://api.ip-sakti.in'
});

// Query with streaming
for await (const event of client.query.stream({
  query: 'Patentability of AI inventions',
  language: 'en'
})) {
  if (event.type === 'token') process.stdout.write(event.delta);
  if (event.type === 'complete') console.log('\nDone:', event.confidence);
}
```

---

## 19. OpenAPI Specification

Full OpenAPI 3.1 specification available at:
- `/openapi.json` (machine-readable)
- `/docs` (Swagger UI)
- `/redoc` (ReDoc)

---

## 20. Open Research Questions

| ID | Question | Priority |
|----|----------|----------|
| ORQ-65 | Optimal streaming chunk size for legal text generation? | Medium |
| ORQ-66 | API rate limiting strategy for bursty legal research workloads? | High |
| ORQ-67 | WebSocket vs SSE for production streaming reliability? | Medium |
| ORQ-68 | GraphQL API for flexible evidence/citation queries? | Low |
| ORQ-69 | API gateway selection (Kong, Traefik, AWS API Gateway)? | High |
| ORQ-70 | Request/response compression for large legal documents? | Medium |

---

## 21. Implementation Checklist

- [ ] OpenAPI 3.1 specification (complete)
- [ ] FastAPI/Express.js implementation with all endpoints
- [ ] JWT authentication middleware
- [ ] API key management
- [ ] Rate limiting (Redis-backed)
- [ ] Request validation (Pydantic/Zod)
- [ ] SSE streaming for query endpoint
- [ ] gRPC service definitions and implementations
- [ ] Python SDK (pip package)
- [ ] TypeScript SDK (npm package)
- [ ] API documentation (Swagger/ReDoc)
- [ ] Integration tests for all endpoints
- [ ] Load testing (locust/k6)
- [ ] API gateway configuration
- [ ] CORS policy
- [ ] Request/response logging middleware
- [ ] Error handling middleware
- [ ] Idempotency key middleware
- [ ] Trace context propagation
- [ ] Deprecation header middleware