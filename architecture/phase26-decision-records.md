# Phase 26: Architecture Decision Records (ADRs)

## Overview

This phase documents all key architectural decisions made across the 26-phase RAG system architecture. Each ADR follows the standard format: Title, Status, Context, Decision, Consequences, and related ADRs.

---

## ADR Index

| ID | Title | Status | Date | Phase |
|----|-------|--------|------|-------|
| ADR-001 | Monorepo with Poetry Workspaces | Accepted | 2026-01-15 | 25 |
| ADR-002 | Python 3.11+ for Services | Accepted | 2026-01-15 | 23 |
| ADR-003 | Kubernetes (EKS) for Orchestration | Accepted | 2026-01-15 | 20, 23 |
| ADR-004 | Istio for Service Mesh | Accepted | 2026-01-15 | 20, 23 |
| ADR-005 | ArgoCD for GitOps | Accepted | 2026-01-15 | 20 |
| ADR-006 | Qdrant for Vector Database | Accepted | 2026-01-15 | 6, 23 |
| ADR-007 | Neo4j for Knowledge Graph | Accepted | 2026-01-15 | 7, 23 |
| ADR-008 | PostgreSQL for Relational Data | Accepted | 2026-01-15 | 15, 23 |
| ADR-009 | Redis for Caching & Pub/Sub | Accepted | 2026-01-15 | 14, 23 |
| ADR-010 | Kafka for Event Streaming | Accepted | 2026-01-15 | 13, 23 |
| ADR-011 | BGE-M3 for Multilingual Embeddings | Accepted | 2026-01-15 | 12, 23 |
| ADR-012 | GPT-4o/Claude for Generation | Accepted | 2026-01-15 | 10, 23 |
| ADR-013 | TGI/vLLM for Model Serving | Accepted | 2026-01-15 | 10, 23 |
| ADR-014 | Deterministic-First Classification | Accepted | 2026-01-15 | 8 |
| ADR-015 | Human Escalation for Low Confidence | Accepted | 2026-01-15 | 8 |
| ADR-016 | Citation Verification Pipeline | Accepted | 2026-01-15 | 10 |
| ADR-017 | Structured JSON Logging with Correlation IDs | Accepted | 2026-01-15 | 21 |
| ADR-018 | Prometheus Metrics with Standard Naming | Accepted | 2026-01-15 | 21 |
| ADR-019 | OpenTelemetry for Distributed Tracing | Accepted | 2026-01-15 | 21 |
| ADR-020 | VictoriaMetrics for Metrics Storage | Accepted | 2026-01-15 | 21, 23 |
| ADR-021 | ClickHouse for Log Storage | Accepted | 2026-01-15 | 21, 23 |
| ADR-022 | Tempo for Trace Storage | Accepted | 2026-01-15 | 21, 23 |
| ADR-023 | Grafana for Visualization | Accepted | 2026-01-15 | 21, 23 |
| ADR-024 | Circuit Breakers for External Dependencies | Accepted | 2026-01-15 | 22 |
| ADR-025 | Graceful Degradation with Fallbacks | Accepted | 2026-01-15 | 22 |
| ADR-026 | Chaos Engineering Program | Accepted | 2026-01-15 | 22 |
| ADR-027 | Immutable Audit Logs with Cryptographic Chaining | Accepted | 2026-01-15 | 21 |
| ADR-028 | PII Redaction in Logs and Traces | Accepted | 2026-01-15 | 21, 19 |
| ADR-029 | Multi-AZ Deployment for HA | Accepted | 2026-01-15 | 20 |
| ADR-030 | Blue/Green Deployments | Accepted | 2026-01-15 | 20 |
| ADR-031 | OPA for Policy Enforcement | Accepted | 2026-01-15 | 19 |
| ADR-032 | Vault for Secrets Management | Accepted | 2026-01-15 | 19 |
| ADR-033 | mTLS via Istio | Accepted | 2026-01-15 | 19, 20 |
| ADR-034 | LangGraph for Agent Orchestration | Accepted | 2026-01-15 | 13 |
| ADR-035 | Dual-Memory Architecture (STM + LTM) | Accepted | 2026-01-15 | 14 |
| ADR-036 | Evaluation-Driven Development | Accepted | 2026-01-15 | 17 |
| ADR-037 | Research Experiment Framework | Accepted | 2026-01-15 | 18 |
| ADR-038 | Source Authority Scoring | Accepted | 2026-01-15 | 11 |
| ADR-039 | Jurisdiction Resolution Engine | Accepted | 2026-01-15 | 9 |
| ADR-040 | Multilingual with Terminology Protection | Accepted | 2026-01-15 | 12 |
| ADR-041 | NLLB-200 for Translation | Accepted | 2026-01-15 | 12, 23 |
| ADR-042 | API Gateway with Kong/Envoy Gateway | Accepted | 2026-01-15 | 16, 23 |
| ADR-043 | gRPC for Service-to-Service Communication | Accepted | 2026-01-15 | 16, 23 |
| ADR-044 | OpenAPI/Swagger for API Contracts | Accepted | 2026-01-15 | 16 |
| ADR-045 | React 18 + TypeScript + Vite for Frontend | Accepted | 2026-01-15 | 23 |
| ADR-046 | Radix UI + Tailwind for Component Library | Accepted | 2026-01-15 | 23 |
| ADR-047 | FinOps with Budgets and Anomaly Detection | Accepted | 2026-01-15 | 23 |
| ADR-048 | Spot Instances for GPU Workloads | Accepted | 2026-01-15 | 23 |
| ADR-049 | Model Quantization (AWQ/GPTQ 4-bit) | Accepted | 2026-01-15 | 23 |
| ADR-050 | ADR Process for Architecture Decisions | Accepted | 2026-01-15 | 26 |

---

## ADR Details

### ADR-001: Monorepo with Poetry Workspaces

**Status**: Accepted

**Context**: 
We need to manage 15+ services, 8 shared libraries, and multiple languages (Python, TypeScript, Go, Rust) while enabling code sharing, consistent tooling, and atomic commits.

**Decision**: 
Use a single monorepo with Poetry workspaces for Python, npm workspaces for TypeScript, Go workspaces, and Cargo workspaces. Shared libraries in `libs/` are published as internal packages with `develop = true` for editable installs.

**Consequences**:
- ✅ Atomic cross-service changes
- ✅ Shared libraries versioned together
- ✅ Simplified dependency management
- ✅ Single CI/CD pipeline
- ⚠️ Requires good tooling for sparse checkouts
- ⚠️ Build times grow with repo size (mitigated by Turborepo/Nx if needed)

**Related**: ADR-025, ADR-026

---

### ADR-002: Python 3.11+ for Services

**Status**: Accepted

**Context**: 
Need a language with strong ML/NLP ecosystem, async support, type hints, and performance for the core RAG pipeline services.

**Decision**: 
Standardize on Python 3.11+ for all backend services. Use FastAPI for APIs, Pydantic v2 for validation, and async/await throughout. Rust for performance-critical components (vector search, embedding serving).

**Consequences**:
- ✅ Rich ecosystem (LangChain, LlamaIndex, HuggingFace, PyTorch)
- ✅ Fast development velocity
- ✅ Strong typing with mypy
- ✅ Good async support for I/O-bound services
- ⚠️ GIL limits CPU parallelism (use multiprocessing/Rust for CPU-bound)
- ⚠️ Slower than Go/Rust for high-throughput services

**Related**: ADR-013, ADR-049

---

### ADR-003: Kubernetes (EKS) for Orchestration

**Status**: Accepted

**Context**: 
Need a container orchestration platform that supports auto-scaling, multi-AZ HA, GPU workloads, and integrates with AWS ecosystem for data residency in India.

**Decision**: 
Use Amazon EKS (Kubernetes 1.28+) with managed node groups, Karpenter for autoscaling, and AWS Load Balancer Controller. Deploy across 3 AZs in Mumbai/Hyderabad regions.

**Consequences**:
- ✅ Industry standard, large talent pool
- ✅ Native GPU support via NVIDIA device plugin
- ✅ Integrates with AWS IAM, VPC, CloudWatch
- ✅ Supports data residency requirements
- ⚠️ Operational complexity (mitigated by managed EKS)
- ⚠️ Cost overhead vs raw EC2

**Related**: ADR-029, ADR-048

---

### ADR-004: Istio for Service Mesh

**Status**: Accepted

**Context**: 
Need mTLS, traffic management (canary, mirroring), observability, and resilience patterns (retry, timeout, circuit breaker) across 15+ services.

**Decision**: 
Deploy Istio 1.20+ with ambient mesh (sidecarless) where possible. Use Envoy Gateway for ingress. Enable mutual TLS in STRICT mode.

**Consequences**:
- ✅ Zero-trust network security
- ✅ Fine-grained traffic control
- ✅ Built-in observability (metrics, traces)
- ✅ Resilience policies without code changes
- ⚠️ Resource overhead (sidecars/ambient agents)
- ⚠️ Operational complexity
- ⚠️ Learning curve for team

**Related**: ADR-033, ADR-019, ADR-024

---

### ADR-005: ArgoCD for GitOps

**Status**: Accepted

**Context**: 
Need declarative, auditable, and automated deployment with drift detection and rollback capabilities.

**Decision**: 
Use ArgoCD for GitOps deployments. All manifests in `infra/helm` and `infra/kustomize`. ArgoCD manages sync, prune, and self-heal. Separate projects per environment (dev, staging, prod).

**Consequences**:
- ✅ Single source of truth in Git
- ✅ Automated drift detection and correction
- ✅ Audit trail of all deployments
- ✅ Easy rollback via Git revert
- ⚠️ Requires discipline (no manual kubectl apply)
- ⚠️ Secrets management via SealedSecrets/Vault

**Related**: ADR-030, ADR-032

---

### ADR-006: Qdrant for Vector Database

**Status**: Accepted

**Context**: 
Need a vector database with metadata filtering, multi-tenancy, high performance, and reasonable cost for 10M+ document embeddings.

**Decision**: 
Use Qdrant (self-hosted on EKS) with binary quantization, HNSW indexing, and payload filtering. Cluster mode with 3+ nodes, replication factor 2.

**Consequences**:
- ✅ Native filtering + vector search in single query
- ✅ Binary quantization (10x memory reduction)
- ✅ Multi-tenancy with sharding
- ✅ Rust-based, high performance, low memory
- ✅ gRPC + REST, good client SDKs
- ⚠️ Self-hosted operational burden
- ⚠️ Younger ecosystem than Pinecone/Weaviate

**Related**: ADR-007, ADR-049

---

### ADR-007: Neo4j for Knowledge Graph

**Status**: Accepted

**Context**: 
Need a graph database for regulatory knowledge with complex relationships, multi-hop reasoning, and graph algorithms.

**Decision**: 
Use Neo4j Enterprise (causal cluster) with Cypher query language, Graph Data Science library, and Bloom for visualization. Deploy on EKS with read replicas for query scaling.

**Consequences**:
- ✅ Native graph storage (index-free adjacency)
- ✅ Cypher - declarative, readable queries
- ✅ ACID transactions
- ✅ Graph Data Science (algorithms, ML)
- ✅ Strong ecosystem and talent pool
- ⚠️ Licensing costs for Enterprise
- ⚠️ Vertical scaling limits (mitigated by read replicas)
- ⚠️ Operational expertise required

**Related**: ADR-006, ADR-034

---

### ADR-008: PostgreSQL for Relational Data

**Status**: Accepted

**Context**: 
Need a reliable relational database for metadata, user data, configuration, and audit logs with JSONB support.

**Decision**: 
Use Amazon RDS PostgreSQL 16 with Multi-AZ, read replicas, and pgvector extension for hybrid search. Enable logical replication for CDC.

**Consequences**:
- ✅ Mature, reliable, well-understood
- ✅ JSONB for flexible metadata
- ✅ Full-text search
- ✅ pgvector for hybrid search fallback
- ✅ Point-in-time recovery
- ⚠️ Connection pooling required (PgBouncer)
- ⚠️ Write scaling limits

**Related**: ADR-009, ADR-027

---

### ADR-009: Redis for Caching & Pub/Sub

**Status**: Accepted

**Context**: 
Need sub-millisecond caching, pub/sub for real-time updates, and distributed locking for coordination.

**Decision**: 
Use Amazon ElastiCache Redis 7 in cluster mode with Multi-AZ. Enable Redis Streams for event processing. Use Valkey as potential future alternative.

**Consequences**:
- ✅ Sub-ms latency
- ✅ Pub/sub, streams, Lua scripting
- ✅ Cluster mode for horizontal scaling
- ✅ Multi-AZ with automatic failover
- ⚠️ Memory costs at scale
- ⚠️ Persistence not durable (use for cache only)

**Related**: ADR-014, ADR-024

---

### ADR-010: Kafka for Event Streaming

**Status**: Accepted

**Context**: 
Need durable, ordered event streaming for audit trails, async processing, and inter-service communication with replay capability.

**Decision**: 
Use Amazon MSK (Kafka 3.6+) with 3 AZ brokers. Topics per domain: `query.events`, `classification.events`, `ingestion.events`, `audit.events`. Retention: 7 days hot, 1 year cold (S3).

**Consequences**:
- ✅ Durability and ordering guarantees
- ✅ Replay for debugging and reprocessing
- ✅ Multiple consumer groups
- ✅ Exactly-once semantics
- ⚠️ Operational complexity (MSK helps)
- ⚠️ Latency higher than direct RPC

**Related**: ADR-013, ADR-027

---

### ADR-011: BGE-M3 for Multilingual Embeddings

**Status**: Accepted

**Context**: 
Need high-quality embeddings for 13 Indian languages + English with strong cross-lingual retrieval performance.

**Decision**: 
Use BGE-M3 (BAAI) as primary embedding model. Supports 100+ languages, dense + sparse + multi-vector representations. Fine-tune on domain data if needed.

**Consequences**:
- ✅ State-of-the-art multilingual performance
- ✅ Single model for all languages
- ✅ Supports hybrid retrieval (dense + sparse)
- ✅ Open weights, self-hostable
- ⚠️ 1024 dimensions (larger than 768)
- ⚠️ Fine-tuning requires GPU resources

**Related**: ADR-012, ADR-041

---

### ADR-012: GPT-4o/Claude for Generation

**Status**: Accepted

**Context**: 
Need highest-quality generation for regulatory citations with strict grounding requirements.

**Decision**: 
Primary: GPT-4o (OpenAI) and Claude 3.5 Sonnet (Anthropic) via API. Fallback: Self-hosted Llama-3.1-70B-Instruct on TGI. Route simple queries to smaller models (GPT-4o-mini, Haiku).

**Consequences**:
- ✅ Best-in-class reasoning and instruction following
- ✅ Strong citation adherence with prompting
- ✅ Multi-provider redundancy
- ⚠️ API costs at scale
- ⚠️ Vendor dependency
- ⚠️ Data privacy concerns (mitigate with self-hosted fallback)

**Related**: ADR-013, ADR-016, ADR-048

---

### ADR-013: TGI/vLLM for Model Serving

**Status**: Accepted

**Context**: 
Need high-throughput, low-latency model serving with continuous batching, quantization, and prefix caching for self-hosted models.

**Decision**: 
Use Text Generation Inference (TGI) as primary, vLLM as alternative. Enable continuous batching, flash-attention-2, AWQ 4-bit quantization, and prefix caching.

**Consequences**:
- ✅ Continuous batching (2-10x throughput)
- ✅ Quantization support (4-bit)
- ✅ Prefix caching for RAG prompts
- ✅ OpenAI-compatible API
- ⚠️ GPU memory management complexity
- ⚠️ Model-specific optimization needed

**Related**: ADR-012, ADR-049

---

### ADR-014: Deterministic-First Classification

**Status**: Accepted

**Context**: 
Regulatory classification must be accurate, auditable, and consistent. LLM-based classification is non-deterministic and can hallucinate.

**Decision**: 
Implement deterministic rule engine as primary classifier (25+ rules covering D&C Act, D&C Rules, FSSAI, Cosmetics Rules). LLM reasoning only for borderline cases (confidence < 0.6). LLM can never override deterministic rules.

**Consequences**:
- ✅ 100% reproducible classifications
- ✅ Auditable decision logic
- ✅ Regulatory compliance
- ✅ LLM only for genuine ambiguity
- ⚠️ Rule maintenance overhead
- ⚠️ Requires domain expert involvement

**Related**: ADR-015, ADR-016

---

### ADR-015: Human Escalation for Low Confidence

**Status**: Accepted

**Context**: 
Some queries cannot be reliably classified automatically. Need human-in-the-loop for regulatory safety.

**Decision**: 
Escalate to human review when: confidence < 0.6, rule conflicts, scheduled ingredients, therapeutic claims on non-drugs, novel formulations, multi-class ambiguity. Target SLA: 4 hours for SEV-1, 24 hours for SEV-2.

**Consequences**:
- ✅ Safety net for edge cases
- ✅ Feedback loop for rule improvement
- ✅ Regulatory defensibility
- ⚠️ Operational cost of review team
- ⚠️ Latency for escalated queries
- ⚠️ Need escalation queue management

**Related**: ADR-014, ADR-024

---

### ADR-016: Citation Verification Pipeline

**Status**: Accepted

**Context**: 
Hallucinated citations in regulatory advice are unacceptable. Must verify every citation against retrieved documents.

**Decision**: 
Post-generation verification step: extract citation spans → match against retrieved document chunks → compute grounding score → reject/regenerate if score < 0.8. Log all verification results for audit.

**Consequences**:
- ✅ Prevents hallucinated citations
- ✅ Quantifiable grounding metric
- ✅ Audit trail for compliance
- ⚠️ Additional latency (~500ms)
- ⚠️ May reject valid but paraphrased citations

**Related**: ADR-012, ADR-027

---

### ADR-017: Structured JSON Logging with Correlation IDs

**Status**: Accepted

**Context**: 
Need unified logging across 15+ services with request tracing, searchability, and PII protection.

**Decision**: 
All services emit structured JSON logs with: timestamp, level, service, version, trace_id, span_id, correlation_id, user_id, message, fields. Use structlog with contextvars for automatic injection. Redact PII via regex patterns.

**Consequences**:
- ✅ Queryable logs in ClickHouse
- ✅ End-to-end request tracing
- ✅ PII protection by default
- ✅ Consistent format across services
- ⚠️ Slightly larger log volume
- ⚠️ Requires discipline to use structured fields

**Related**: ADR-018, ADR-019, ADR-028

---

### ADR-018: Prometheus Metrics with Standard Naming

**Status**: Accepted

**Context**: 
Need consistent metrics across services for dashboards, alerting, and SLO tracking.

**Decision**: 
Use Prometheus client libraries. Naming convention: `<subsystem>_<component>_<operation>_<unit>`. Key metrics: `rag_query_latency_seconds`, `rag_retrieval_documents_retrieved`, `rag_classification_confidence`, `rag_escalation_total`. Histograms for latency, counters for rates.

**Consequences**:
- ✅ Consistent dashboards and alerts
- ✅ Interoperable with Prometheus ecosystem
- ✅ Standard naming aids discoverability
- ⚠️ Cardinality management required
- ⚠️ Need to avoid high-cardinality labels

**Related**: ADR-017, ADR-020

---

### ADR-019: OpenTelemetry for Distributed Tracing

**Status**: Accepted

**Context**: 
Need end-to-end request tracing across service boundaries, async queues, and external APIs.

**Decision**: 
Use OpenTelemetry SDK with auto-instrumentation (FastAPI, httpx, Redis, SQLAlchemy). Export via OTLP to Tempo. Adaptive sampling: 100% errors, 10% success, 100% priority operations.

**Consequences**:
- ✅ Vendor-neutral, wide ecosystem
- ✅ Auto-instrumentation reduces boilerplate
- ✅ Context propagation across async boundaries
- ✅ Adaptive sampling controls cost
- ⚠️ Instrumentation overhead (~1-2ms)
- ⚠️ Trace ID propagation must be maintained

**Related**: ADR-017, ADR-022

---

### ADR-020: VictoriaMetrics for Metrics Storage

**Status**: Accepted

**Context**: 
Need cost-effective, Prometheus-compatible long-term metrics storage with high compression.

**Decision**: 
Use VictoriaMetrics (single-node for dev, cluster for prod) with 30-day retention. PromQL compatible. 10x compression vs Prometheus.

**Consequences**:
- ✅ 10x storage cost reduction
- ✅ PromQL compatible
- ✅ Single binary, easy operations
- ✅ Downsampling for long-term retention
- ⚠️ Less features than Thanos/Cortex
- ⚠️ Single-node not HA (use cluster mode for prod)

**Related**: ADR-018, ADR-023

---

### ADR-021: ClickHouse for Log Storage

**Status**: Accepted

**Context**: 
Need fast log search with SQL interface, high compression, and cost-effective retention.

**Decision**: 
Use ClickHouse for log storage. Ingest via Fluent Bit → Kafka → ClickHouse. Partition by day, TTL 30 days hot / 1 year cold (S3). SQL interface for complex queries.

**Consequences**:
- ✅ 5-10x compression
- ✅ SQL queries (familiar to analysts)
- ✅ Sub-second log search
- ✅ Materialized views for common queries
- ⚠️ Operational expertise needed
- ⚠️ Not a drop-in Loki replacement

**Related**: ADR-017, ADR-028

---

### ADR-022: Tempo for Trace Storage

**Status**: Accepted

**Context**: 
Need trace storage integrated with Grafana, object storage backend, and TraceQL query language.

**Decision**: 
Use Grafana Tempo with S3 backend. 7-day retention. TraceQL for query. Integrates natively with Grafana dashboards and logs/metrics correlation.

**Consequences**:
- ✅ Native Grafana integration
- ✅ Object storage backend (cheap)
- ✅ TraceQL for structured queries
- ✅ No indexing cost (columnar)
- ⚠️ No built-in sampling (done at collector)
- ⚠️ Query performance depends on trace volume

**Related**: ADR-019, ADR-023

---

### ADR-023: Grafana for Visualization

**Status**: Accepted

**Context**: 
Need unified visualization for metrics, logs, traces with provisioning-as-code.

**Decision**: 
Use Grafana as single pane of glass. Provision dashboards, datasources, and alerts via ConfigMaps/ArgoCD. Use Grafana Alerting (unified) with Alertmanager for routing.

**Consequences**:
- ✅ Single tool for all observability
- ✅ Provisioning as code
- ✅ Excellent Tempo/Loki/Prometheus integration
- ✅ Rich ecosystem of panels and plugins
- ⚠️ Dashboard sprawl without governance

**Related**: ADR-020, ADR-021, ADR-022

---

### ADR-024: Circuit Breakers for External Dependencies

**Status**: Accepted

**Context**: 
External dependencies (LLM APIs, vector DB, KG) can fail or become slow, causing cascade failures.

**Decision**: 
Implement circuit breakers (closed/open/half-open) for all external calls. Configuration: failure_threshold=5, timeout=30s, success_threshold=2. Fallback implementations for each dependency.

**Consequences**:
- ✅ Prevents cascade failures
- ✅ Fast failure instead of timeout waiting
- ✅ Automatic recovery when dependency recovers
- ✅ Fallback maintains partial functionality
- ⚠️ Added complexity in call paths
- ⚠️ Need to tune thresholds per dependency

**Related**: ADR-009, ADR-025, ADR-026

---

### ADR-025: Graceful Degradation with Fallbacks

**Status**: Accepted

**Context**: 
System should remain partially functional even when components fail.

**Decision**: 
Define fallback for each critical path:
- Vector search → keyword search (BM25)
- LLM generation → template responses
- KG query → skip KG context
- Translation → return English with note
- Cache miss → compute on demand

**Consequences**:
- ✅ Maintains core functionality during incidents
- ✅ Better UX than hard errors
- ✅ Buys time for recovery
- ⚠️ Degraded quality (documented)
- ⚠️ Fallback logic maintenance burden

**Related**: ADR-024, ADR-026

---

### ADR-026: Chaos Engineering Program

**Status**: Accepted

**Context**: 
Need to validate resilience assumptions and discover unknown failure modes before production incidents.

**Decision**: 
Run automated chaos experiments weekly: pod kills, latency injection, network partitions, cache stampede, config corruption. Define steady-state hypotheses. Auto-rollback on violation. Integrate with CI/CD for pre-deploy validation.

**Consequences**:
- ✅ Proactive resilience validation
- ✅ Discovers real failure modes
- ✅ Builds team confidence
- ✅ Documents system behavior
- ⚠️ Requires investment in tooling
- ⚠️ Risk of production impact (mitigate with blast radius control)

**Related**: ADR-024, ADR-025

---

### ADR-027: Immutable Audit Logs with Cryptographic Chaining

**Status**: Accepted

**Context**: 
Regulatory requirements demand tamper-evident audit trails for all classification and generation decisions.

**Decision**: 
Write audit events to S3 with Object Lock (COMPLIANCE mode, 1-year retention). Each event includes: hash of previous event, digital signature (RSA-PSS). Chain verification validates integrity.

**Consequences**:
- ✅ Tamper-evident audit trail
- ✅ Meets regulatory requirements
- ✅ Cryptographic proof of integrity
- ✅ Long-term retention with legal hold
- ⚠️ S3 Object Lock costs
- ⚠️ Key management for signing
- ⚠️ Write latency (~100ms)

**Related**: ADR-010, ADR-016

---

### ADR-028: PII Redaction in Logs and Traces

**Status**: Accepted

**Context**: 
Logs and traces may contain user queries with personal information (Aadhaar, PAN, phone, email).

**Decision**: 
Automatic PII redaction at log emission (structlog processor) and trace export (OTel processor). Patterns: email, phone, Aadhaar, PAN, credit card, tokens. Also truncate long strings (>100 chars).

**Consequences**:
- ✅ Privacy by default
- ✅ Reduces compliance scope
- ✅ Consistent across all services
- ⚠️ May redact legitimate technical identifiers
- ⚠️ Regex-based, not perfect
- ⚠️ Slight processing overhead

**Related**: ADR-017, ADR-019, ADR-021, ADR-022

---

### ADR-029: Multi-AZ Deployment for HA

**Status**: Accepted

**Context**: 
Production system must tolerate AZ failures without downtime.

**Decision**: 
Deploy all stateful services (PostgreSQL, Redis, Qdrant, Neo4j, Kafka) in Multi-AZ configuration. Stateless services: minimum 3 replicas spread across 3 AZs. Use topology spread constraints.

**Consequences**:
- ✅ Survives single AZ outage
- ✅ Meets 99.9% availability target
- ✅ Automatic failover for managed services
- ⚠️ 2x infrastructure cost for stateful
- ⚠️ Cross-AZ latency (1-2ms)
- ⚠️ Complexity in stateful failover

**Related**: ADR-003, ADR-008, ADR-009

---

### ADR-030: Blue/Green Deployments

**Status**: Accepted

**Context**: 
Need zero-downtime deployments with instant rollback capability.

**Decision**: 
Use blue/green deployments via ArgoCD for stateless services. New version deployed to inactive color, health checks pass, traffic switched via Istio/Envoy. Rollback = switch back. For stateful: rolling updates with PDBs.

**Consequences**:
- ✅ Zero-downtime deployments
- ✅ Instant rollback (< 30s)
- ✅ Pre-deployment validation in staging color
- ⚠️ 2x compute during deployment
- ⚠️ Database migrations need backward compatibility
- ⚠️ Session affinity considerations

**Related**: ADR-005, ADR-004

---

### ADR-031: OPA for Policy Enforcement

**Status**: Accepted

**Context**: 
Need fine-grained, centralized authorization across API gateway, services, and Kubernetes admission control.

**Decision**: 
Use Open Policy Agent (OPA) with Rego policies. Deploy as sidecar for low-latency decisions. Policies in Git, versioned, tested. Use Gatekeeper for K8s admission control.

**Consequences**:
- ✅ Centralized policy management
- ✅ Decoupled from application code
- ✅ GitOps for policies
- ✅ High performance (Rego compiled)
- ⚠️ Rego learning curve
- ⚠️ Policy distribution latency

**Related**: ADR-004, ADR-032, ADR-033

---

### ADR-032: Vault for Secrets Management

**Status**: Accepted

**Context**: 
Need dynamic secrets, rotation, audit, and Kubernetes integration.

**Decision**: 
Use HashiCorp Vault (HA mode on EKS) with Kubernetes auth method. Dynamic database credentials, AWS IAM roles, PKI certificates. Inject via Vault Agent Injector or CSI driver. External Secrets Operator for K8s secrets sync.

**Consequences**:
- ✅ Dynamic secrets with TTL
- ✅ Automatic rotation
- ✅ Audit trail of all access
- ✅ Lease-based revocation
- ⚠️ Operational complexity (unseal, backup)
- ⚠️ Single point of failure (mitigate with HA)
- ⚠️ Latency for secret retrieval

**Related**: ADR-005, ADR-031, ADR-033

---

### ADR-033: mTLS via Istio

**Status**: Accepted

**Context**: 
Need encryption-in-transit and service identity for zero-trust network.

**Decision**: 
Enable Istio mTLS in STRICT mode. All service-to-service traffic encrypted with mutual TLS. Certificates auto-rotated every 24h. Use PeerAuthentication and DestinationRules.

**Consequences**:
- ✅ Encryption without code changes
- ✅ Service identity for authorization
- ✅ Automatic certificate rotation
- ✅ Compliance with encryption requirements
- ⚠️ Debugging complexity (encrypted traffic)
- ⚠️ Certificate renewal edge cases
- ⚠️ External service integration complexity

**Related**: ADR-004, ADR-031, ADR-032

---

### ADR-034: LangGraph for Agent Orchestration

**Status**: Accepted

**Context**: 
Need a framework for building controllable, observable, stateful agent workflows with human-in-the-loop.

**Decision**: 
Use LangGraph (LangChain) for agent orchestration. Define agents as nodes, edges as transitions. State persisted in PostgreSQL. Built-in streaming, checkpointing, and human intervention points.

**Consequences**:
- ✅ Graph-based workflow (natural for agents)
- ✅ Persistent state with checkpoints
- ✅ Human-in-the-loop support
- ✅ Streaming token output
- ✅ Visualization and debugging
- ⚠️ Tied to LangChain ecosystem
- ⚠️ Learning curve for graph concepts
- ⚠️ Less mature than core LangChain

**Related**: ADR-008, ADR-035

---

### ADR-035: Dual-Memory Architecture (STM + LTM)

**Status**: Accepted

**Context**: 
Conversations need short-term context (current session) and long-term memory (user preferences, past interactions, learned facts).

**Decision**: 
Short-term Memory (STM): In-memory per session, sliding window (last 10 turns), token budget management. Long-term Memory (LTM): Vector store (Qdrant) with user-scoped collections, consolidation from STM via background worker, TTL-based decay.

**Consequences**:
- ✅ Handles both immediate context and persistent knowledge
- ✅ Token budget control for LLM context window
- ✅ Personalization across sessions
- ✅ Privacy via user-scoped isolation
- ⚠️ Consistency between STM/LTM
- ⚠️ Consolidation quality depends on LLM
- ⚠️ Storage growth over time

**Related**: ADR-006, ADR-034

---

### ADR-036: Evaluation-Driven Development

**Status**: Accepted

**Context**: 
RAG quality must be measured continuously to prevent regressions and guide improvements.

**Decision**: 
Implement evaluation harness running on every PR and nightly. Golden dataset: 500+ queries covering all formulation classes, languages, complexity levels. Metrics: accuracy, citation precision/recall, latency, cost. Block merge on regression > 2%.

**Consequences**:
- ✅ Prevents quality regressions
- ✅ Quantifies improvement impact
- ✅ Guides prompt/model tuning
- ✅ Shared quality language across team
- ⚠️ Golden set maintenance burden
- ⚠️ Evaluation latency in CI
- ⚠️ Metric gaming risk

**Related**: ADR-016, ADR-037

---

### ADR-037: Research Experiment Framework

**Status**: Accepted

**Context**: 
Need systematic A/B testing and hypothesis validation for model, prompt, and retrieval strategy changes.

**Decision**: 
Build experiment framework with: hypothesis registry, traffic splitting (consistent hashing), metric tracking, statistical significance testing, automated reporting. Integrate with feature flags for gradual rollout.

**Consequences**:
- ✅ Data-driven model/prompt decisions
- ✅ Controlled rollout of changes
- ✅ Statistical rigor
- ✅ Knowledge capture
- ⚠️ Infrastructure investment
- ⚠️ Sample size requirements
- ⚠️ Experiment lifecycle management

**Related**: ADR-036, ADR-047

---

### ADR-038: Source Authority Scoring

**Status**: Accepted

**Context**: 
Not all regulatory sources are equal. Need to weight retrieval by source credibility.

**Decision**: 
Assign authority scores (0-1) to each source: Gazette notifications (1.0), Acts/Rules (0.95), Official pharmacopeias (0.9), Case law (0.85), Guidelines (0.8), Industry publications (0.6), General web (0.3). Score used in retrieval ranking and citation selection.

**Consequences**:
- ✅ Prefer authoritative sources
- ✅ Reduces hallucination from low-quality sources
- ✅ Auditable source hierarchy
- ⚠️ Authority assignment requires domain expertise
- ⚠️ Scores may become stale
- ⚠️ Bias toward established sources

**Related**: ADR-006, ADR-016

---

### ADR-039: Jurisdiction Resolution Engine

**Status**: Accepted

**Context**: 
Indian regulatory framework has complex Central/State jurisdiction with overlapping authorities.

**Decision**: 
Implement hierarchical jurisdiction resolver: Central Acts → State Rules → Local notifications. Input: user location (explicit or IP), formulation class, claim type. Output: applicable regulations, licensing authority, enforcement agency. Cache resolutions with TTL.

**Consequences**:
- ✅ Correct regulatory context per query
- ✅ Handles Central/State complexity
- ✅ Extensible for new jurisdictions
- ⚠️ Jurisdiction data maintenance
- ⚠️ Edge cases (inter-state, online sales)

**Related**: ADR-014, ADR-007

---

### ADR-040: Multilingual with Terminology Protection

**Status**: Accepted

**Context**: 
13 Indian languages needed, but regulatory terminology (Sanskrit terms, Latin names, legal phrases) must not be translated.

**Decision**: 
Pipeline: Language detection → Terminology extraction (protected terms) → Translation (NLLB-200) → Terminology re-insertion → Quality estimation. Glossary of 5000+ protected terms maintained by domain experts.

**Consequences**:
- ✅ Preserves regulatory precision
- ✅ Supports all 13 scheduled languages
- ✅ Quality gates for low-resource languages
- ⚠️ Glossary maintenance overhead
- ⚠️ Translation quality varies by language
- ⚠️ Code-mixed queries challenging

**Related**: ADR-011, ADR-041

---

### ADR-041: NLLB-200 for Translation

**Status**: Accepted

**Context**: 
Need open-weight translation model supporting all 13 Indian languages with reasonable quality.

**Decision**: 
Use NLLB-200 (Meta) 3.3B parameter model, self-hosted on TGI. Supports 200 languages including all scheduled Indian languages. Fine-tune on regulatory domain data. Fallback to Google Translate API for unsupported pairs.

**Consequences**:
- ✅ Open weights, self-hosted (privacy)
- ✅ Covers all target languages
- ✅ Single model for all directions
- ⚠️ Quality lower than commercial APIs for low-resource
- ⚠️ GPU memory for 3.3B model
- ⚠️ Fine-tuning needed for domain quality

**Related**: ADR-011, ADR-040, ADR-013

---

### ADR-042: API Gateway with Kong/Envoy Gateway

**Status**: Accepted

**Context**: 
Need centralized API management: auth, rate limiting, request/response transformation, analytics.

**Decision**: 
Use Envoy Gateway (Kubernetes Gateway API) for native K8s integration, with Kong as alternative for advanced plugin ecosystem. Handle: JWT validation, API key auth, rate limiting (token bucket), request validation, response caching, analytics export.

**Consequences**:
- ✅ Centralized cross-cutting concerns
- ✅ Kubernetes-native (Gateway API)
- ✅ Extensible with plugins/WASM
- ✅ Observability built-in
- ⚠️ Additional hop latency
- ⚠️ Configuration complexity

**Related**: ADR-004, ADR-043, ADR-044

---

### ADR-043: gRPC for Service-to-Service Communication

**Status**: Accepted

**Context**: 
Need high-performance, typed communication between internal services.

**Decision**: 
Use gRPC with Protocol Buffers for all service-to-service communication. Define proto files in `api/proto/` shared across services. Use connect-go for HTTP/JSON compatibility where needed. Unary for requests, streaming for long-running operations.

**Consequences**:
- ✅ Type-safe contracts
- ✅ High performance (HTTP/2, binary)
- ✅ Streaming support
- ✅ Code generation for multiple languages
- ⚠️ Browser compatibility (need grpc-web/connect)
- ⚠️ Debugging harder than REST
- ⚠️ Schema evolution discipline required

**Related**: ADR-044, ADR-010

---

### ADR-044: OpenAPI/Swagger for API Contracts

**Status**: Accepted

**Context**: 
Need machine-readable API contracts for client generation, testing, and documentation.

**Decision**: 
All external APIs defined via OpenAPI 3.1 specs. Generated from FastAPI decorators. Published to developer portal. Contract tests (Pact) verify compliance. Versioning via URL path (`/v1/`, `/v2/`).

**Consequences**:
- ✅ Single source of truth for API
- ✅ Auto-generated SDKs (Python, TypeScript)
- ✅ Interactive documentation (Swagger UI)
- ✅ Contract testing in CI
- ⚠️ Spec maintenance discipline
- ⚠️ Breaking change detection needed

**Related**: ADR-042, ADR-043

---

### ADR-045: React 18 + TypeScript + Vite for Frontend

**Status**: Accepted

**Context**: 
Need modern, type-safe frontend framework with fast development experience.

**Decision**: 
React 18 with TypeScript, Vite for build, TanStack Query for server state, Zustand for client state. Component library: Radix UI + Tailwind CSS. Testing: Vitest + Playwright.

**Consequences**:
- ✅ Excellent TypeScript support
- ✅ Fast HMR and builds
- ✅ Concurrent features (useTransition)
- ✅ Rich ecosystem
- ⚠️ Bundle size management needed
- ⚠️ Frequent ecosystem changes

**Related**: ADR-046

---

### ADR-046: Radix UI + Tailwind for Component Library

**Status**: Accepted

**Context**: 
Need accessible, customizable component library without design system lock-in.

**Decision**: 
Radix UI primitives (headless, accessible) + Tailwind CSS for styling. No opinionated component library (MUI, Chakra). Build own composed components in `frontend/shared`.

**Consequences**:
- ✅ Full design control
- ✅ Accessibility by default (Radix)
- ✅ No theme overriding battles
- ✅ Tree-shakable, small bundle
- ⚠️ More development effort
- ⚠️ Consistency requires discipline

**Related**: ADR-045

---

### ADR-047: FinOps with Budgets and Anomaly Detection

**Status**: Accepted

**Context**: 
Cloud costs can grow unbounded with GPU workloads, vector databases, and LLM APIs.

**Decision**: 
Implement FinOps: mandatory cost allocation tags, per-team budgets with alerts at 50/80/100%, anomaly detection (2σ), weekly rightsizing, Savings Plans for 50% baseline compute, Reserved Instances for databases.

**Consequences**:
- ✅ Cost visibility and accountability
- ✅ Proactive anomaly detection
- ✅ Optimized committed spend
- ⚠️ Tagging discipline required
- ⚠️ Savings Plans reduce flexibility
- ⚠️ Requires FinOps culture

**Related**: ADR-048, ADR-049

---

### ADR-048: Spot Instances for GPU Workloads

**Status**: Accepted

**Context**: 
GPU instances are expensive. Model inference can tolerate interruption with proper queuing.

**Decision**: 
Use EC2 Spot instances for GPU inference workers (g5, p4). Implement graceful degradation: spot interruption notice → drain queue → reschedule on on-demand. Target 70% spot, 30% on-demand baseline.

**Consequences**:
- ✅ 60-70% cost reduction
- ✅ Automatic diversification across pools
- ⚠️ Interruption handling complexity
- ⚠️ Queue latency during replacement
- ⚠️ Not suitable for real-time serving

**Related**: ADR-012, ADR-013, ADR-047

---

### ADR-049: Model Quantization (AWQ/GPTQ 4-bit)

**Status**: Accepted

**Context**: 
Self-hosted LLMs (Llama-3.1-70B) require significant GPU memory. Quantization reduces requirements with minimal quality loss.

**Decision**: 
Use AWQ 4-bit quantization for self-hosted models. Calibrate on domain data. Fallback to GPTQ if AWQ unavailable. Target: 70B model on 2×A10G (48GB VRAM) instead of 4×A100.

**Consequences**:
- ✅ 4x memory reduction
- ✅ <1% quality degradation (per literature)
- ✅ Enables larger models on cheaper GPUs
- ⚠️ Calibration data required
- ⚠️ Not all models support AWQ
- ⚠️ Quality validation needed per model

**Related**: ADR-012, ADR-013, ADR-048

---

### ADR-050: ADR Process for Architecture Decisions

**Status**: Accepted

**Context**: 
Need a lightweight, durable process for recording architectural decisions.

**Decision**: 
Adopt ADR format (Markdown in `docs/architecture/adrs/`). Each ADR: number, title, status, date, context, decision, consequences, related. New ADRs for significant decisions. Superseded ADRs marked, not deleted. Review quarterly.

**Consequences**:
- ✅ Institutional memory preserved
- ✅ Onboarding aid for new team members
- ✅ Decision rationale documented
- ✅ Prevents re-litigation
- ⚠️ Maintenance discipline required
- ⚠️ Can become stale

**Related**: All ADRs

---

## ADR Template

```markdown
# ADR-XXX: [Title]

**Status**: [Proposed | Accepted | Superseded | Deprecated]

**Date**: YYYY-MM-DD

**Decision Makers**: [@handles]

**Related**: ADR-XXX, ADR-YYY

## Context

[Describe the problem, constraints, and forces at play. What is the decision to be made?]

## Decision

[State the decision clearly and concisely. Include enough detail for implementation.]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Drawback 1]
- [Drawback 2]

### Neutral
- [Trade-off 1]
- [Trade-off 2]

## Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Alt 1 | ... | ... | ... |
| Alt 2 | ... | ... | ... |

## Implementation Notes

[Any implementation details, migration steps, or follow-up tasks]

## Review Date

[Date for next review, typically 6-12 months]
```

---

## ADR Governance

### Creation Process

1. **Identify Need**: Significant architectural choice with long-term impact
2. **Draft ADR**: Use template, gather input from stakeholders
3. **Review**: Async review in PR (minimum 2 approvers from relevant domains)
4. **Decide**: Architecture owner merges → Accepted
5. **Implement**: Reference ADR in implementation tickets
6. **Review**: Quarterly review of active ADRs

### Status Lifecycle

```
Proposed → Accepted → (Superseded by ADR-XXX) → Deprecated
                ↘ (Rejected) → Rejected
```

### Supersession

When a decision is overturned:
1. Create new ADR with `Supersedes: ADR-XXX`
2. Mark old ADR as `Superseded by ADR-YYY`
3. Update related ADRs
4. Communicate to affected teams

---

## Open Research Questions (Consolidated)

| ID | Question | Origin Phase |
|----|----------|--------------|
| ORQ-01 | Optimal chunking strategy for regulatory documents? | 6 |
| ORQ-02 | How to handle amendment tracking in KG? | 7 |
| ORQ-03 | Rule conflict resolution for overlapping regulations? | 8 |
| ORQ-04 | LLM reasoning transparency for audit? | 8 |
| ORQ-05 | Jurisdiction precedence for conflicting Central/State rules? | 9 |
| ORQ-06 | Citation style standardization across sources? | 10 |
| ORQ-07 | Authority score calibration methodology? | 11 |
| ORQ-08 | Cross-lingual retrieval vs translate-then-retrieve? | 12 |
| ORQ-09 | Agent communication protocol standardization? | 13 |
| ORQ-10 | Memory consolidation trigger optimization? | 14 |
| ORQ-11 | Schema evolution for regulatory data models? | 15 |
| ORQ-12 | API versioning strategy for breaking changes? | 16 |
| ORQ-13 | Evaluation metric correlation with user satisfaction? | 17 |
| ORQ-14 | Experiment statistical power for low-traffic features? | 18 |
| ORQ-15 | Threat model for prompt injection in classification? | 19 |
| ORQ-16 | Canary analysis automation for ML model deployments? | 20 |
| ORQ-17 | Optimal trace sampling rate for cost vs debuggability? | 21 |
| ORQ-18 | Business metric correlation with system metrics? | 21 |
| ORQ-19 | eBPF for zero-instrumentation system metrics? | 21 |
| ORQ-20 | Cross-cluster trace correlation? | 21 |
| ORQ-21 | Privacy-preserving log aggregation? | 21 |
| ORQ-22 | Optimal circuit breaker timeout for LLM providers? | 22 |
| ORQ-23 | ML-based failure prediction from metric patterns? | 22 |
| ORQ-24 | Cascading failure handling in agent orchestration? | 22 |
| ORQ-25 | Blast radius of single document corruption? | 22 |
| ORQ-26 | Automated rollback for ML model degradation? | 22 |
| ORQ-27 | WebAssembly for plugin sandboxing? | 23 |
| ORQ-28 | DuckDB vs ClickHouse for log analytics? | 23 |
| ORQ-29 | Temporal vs Airflow for ML pipelines? | 23 |
| ORQ-30 | Arrow/Parquet for inter-service data? | 23 |
| ORQ-31 | Iceberg table format for data lake? | 23 |
| ORQ-32 | Optimal team structure for agent development? | 24 |
| ORQ-33 | LLM-as-judge reliability for evaluation? | 24 |
| ORQ-34 | Measuring "regulatory correctness" vs generic accuracy? | 24 |
| ORQ-35 | Multi-tenant RAG abstraction? | 24 |
| ORQ-36 | Build vs buy developer portal? | 24 |
| ORQ-37 | Model deprecation handling (GPT-4o → GPT-5)? | 24 |
| ORQ-38 | Synthetic data for low-resource languages? | 24 |
| ORQ-39 | Nx/Turborepo for build orchestration? | 25 |
| ORQ-40 | Shared library versioning across services? | 25 |
| ORQ-41 | Frontend separate repo vs monorepo? | 25 |
| ORQ-42 | Database migration management across services? | 25 |
| ORQ-43 | Bazel for hermetic builds? | 25 |

**Total: 43 Open Research Questions across 26 phases**

---

## Summary

Phase 26 captures 50 Architecture Decision Records documenting the key choices across all 26 phases:

1. **Platform Decisions** (ADR-001 to ADR-005): Monorepo, Python, Kubernetes, Istio, GitOps
2. **Data Layer Decisions** (ADR-006 to ADR-010): Qdrant, Neo4j, PostgreSQL, Redis, Kafka
3. **ML/AI Decisions** (ADR-011 to ADR-013): BGE-M3, GPT-4o/Claude, TGI/vLLM
4. **Core RAG Decisions** (ADR-014 to ADR-016): Deterministic classification, escalation, citation verification
5. **Observability Decisions** (ADR-017 to ADR-023): Structured logging, Prometheus metrics, OpenTelemetry, VictoriaMetrics, ClickHouse, Tempo, Grafana
6. **Resilience Decisions** (ADR-024 to ADR-026): Circuit breakers, graceful degradation, chaos engineering
7. **Security/Compliance Decisions** (ADR-027 to ADR-033): Audit logs, PII redaction, Multi-AZ, blue/green, OPA, Vault, mTLS
8. **Advanced Capability Decisions** (ADR-034 to ADR-041): LangGraph, dual memory, evaluation-driven, experiments, authority scoring, jurisdiction, multilingual, NLLB-200
9. **API/Frontend Decisions** (ADR-042 to ADR-046): API Gateway, gRPC, OpenAPI, React/TypeScript/Vite, Radix+Tailwind
10. **Cost/Ops Decisions** (ADR-047 to ADR-049): FinOps, Spot GPUs, quantization
11. **Process Decision** (ADR-050): ADR process itself

Plus **43 Open Research Questions** identifying areas for future investigation and improvement.