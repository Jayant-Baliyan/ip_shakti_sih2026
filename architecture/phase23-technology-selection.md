# Phase 23: Technology Selection

## Overview

This phase documents the technology choices for the RAG system, providing rationale, alternatives considered, and integration patterns for each component. The selection prioritizes regulatory compliance, operational excellence, and long-term maintainability.

---

## 1. Selection Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Regulatory Compliance** | 25% | Audit trails, data residency, encryption, access control |
| **Operational Maturity** | 20% | Community, documentation, incident response, talent availability |
| **Performance** | 15% | Latency, throughput, scalability for RAG workloads |
| **Integration** | 15% | Ecosystem compatibility, APIs, SDKs |
| **Cost Efficiency** | 10% | TCO including licensing, infrastructure, engineering time |
| **Vendor Lock-in Risk** | 10% | Portability, open standards, multi-cloud support |
| **Security Posture** | 5% | Defaults, certifications, vulnerability response |

---

## 2. Core Technology Stack

### 2.1 Programming Languages

| Layer | Primary | Rationale | Alternatives |
|-------|---------|-----------|--------------|
| **API/Services** | Python 3.11+ | Rich ML/NLP ecosystem, FastAPI, async support, type hints | Go (performance), Node.js (unified stack) |
| **ML Pipeline** | Python 3.11+ | PyTorch, HuggingFace, LangChain, LlamaIndex | Julia (performance), Rust (candle) |
| **Data Processing** | Python + SQL | Pandas, Polars, DuckDB, dbt | Spark (scale), Rust (polars) |
| **Infrastructure** | Go/Terraform | Kubernetes operators, CLI tools, performance | Rust, Python (Pulumi) |
| **Frontend** | TypeScript/React | Type safety, ecosystem, team familiarity | Vue, Svelte |
| **High-Performance** | Rust | Vector search, embedding serving, zero-cost abstractions | C++, Go |

### 2.2 Language Version Policy

```toml
# pyproject.toml / Cargo.toml versions
[tool.poetry.dependencies]
python = ">=3.11,<3.13"  # 3.11 for performance, 3.12 for typing

[tool.poetry.group.dev.dependencies]
ruff = "^0.3.0"          # Fast linter
mypy = "^1.8.0"          # Type checking
pytest = "^8.0.0"        # Testing
pytest-asyncio = "^0.23.0"
```

---

## 3. Infrastructure & Platform

### 3.1 Container Orchestration

| Component | Choice | Version | Rationale |
|-----------|--------|---------|-----------|
| **Orchestrator** | Kubernetes (EKS/GKE/AKS) | 1.28+ | Industry standard, autoscaling, multi-cloud |
| **Service Mesh** | Istio | 1.20+ | mTLS, traffic management, observability |
| **Ingress** | Envoy Gateway / NGINX | Latest | L7 routing, WAF integration, canary |
| **GitOps** | ArgoCD | 2.9+ | Declarative, drift detection, RBAC |
| **Package Manager** | Helm | 3.13+ | Templating, dependency management |

### 3.2 Compute

| Workload | Instance Type | Sizing | Autoscaling |
|----------|---------------|--------|-------------|
| **API Services** | General purpose (c6i/m6i) | 2-8 vCPU, 4-16GB | HPA: CPU>70%, RPS>100/pod |
| **ML Inference** | GPU (g5/p4) | 1xA10G - 8xH100 | KEDA: queue depth, custom metrics |
| **Vector Search** | Memory optimized (r6i/x2idn) | 32-128 vCPU, 256GB-1TB | Manual + cluster autoscaler |
| **Batch/ETL** | Spot instances | Variable | Karpenter + spot interruption handling |
| **KG Database** | Memory optimized | 16-64 vCPU, 128-512GB | Read replicas for query scaling |

### 3.3 Storage

| Data Type | Primary | Backup/DR | Rationale |
|-----------|---------|-----------|-----------|
| **Vector Embeddings** | Qdrant Cloud / Self-hosted | S3 snapshots + replication | HNSW, filtering, payload, multi-tenancy |
| **Knowledge Graph** | Neo4j Aura / Self-hosted | Point-in-time recovery | Cypher, ACID, graph algorithms |
| **Documents/Chunks** | S3 (Standard-IA) | Cross-region replication | Cost, durability, versioning |
| **Metadata/Relational** | PostgreSQL (RDS/CloudSQL) | Automated backups + PITR | JSONB, full-text, extensions |
| **Cache** | Redis Cluster (ElastiCache) | Multi-AZ | Sub-ms latency, pub/sub, streams |
| **Time-series/Metrics** | VictoriaMetrics / Thanos | S3 long-term | Prometheus-compatible, compression |
| **Logs** | ClickHouse / Loki | S3 + retention policies | SQL interface, compression, cost |
| **Traces** | Tempo / Jaeger | S3 7-day retention | TraceQL, Grafana integration |

---

## 4. Machine Learning & AI

### 4.1 Models

| Use Case | Primary Model | Fallback | Deployment |
|----------|---------------|----------|------------|
| **Embeddings** | BGE-M3 (multilingual) | E5-large, instructor-xl | TGI/vLLM/Ollama |
| **Generation (Primary)** | GPT-4o / Claude 3.5 Sonnet | Llama-3.1-70B-Instruct | API / Self-hosted |
| **Generation (Fast)** | GPT-4o-mini / Haiku | Llama-3.1-8B-Instruct | API / Self-hosted |
| **Classification** | Fine-tuned DeBERTa-v3 | Rule-based only | TorchServe/Triton |
| **Translation** | NLLB-200 / M2M-100 | Google Translate API | Self-hosted (privacy) |
| **Reranking** | BGE-reranker-v2 | Cohere Rerank | Self-hosted |
| **Entity Extraction** | GLiNER / spaCy | Custom NER | spaCy pipeline |

### 4.2 ML Platform

| Capability | Choice | Rationale |
|------------|--------|-----------|
| **Experiment Tracking** | MLflow + Weights & Biases | Open source + managed UI |
| **Model Registry** | MLflow + HuggingFace Hub | Versioning, staging, lineage |
| **Feature Store** | Feast | Offline/online, point-in-time |
| **Pipeline Orchestration** | Kubeflow Pipelines / Airflow | K8s-native, DAGs, retry |
| **Model Serving** | TGI (text-generation-inference) | Continuous batching, quant |
| **Distributed Training** | PyTorch FSDP / DeepSpeed | Large model fine-tuning |
| **Evaluation** | LangSmith / custom | LLM-specific eval, tracing |

### 4.3 Quantization & Optimization

```yaml
# Model optimization strategy
optimization:
  embeddings:
    - fp16: true           # 2x memory reduction
    - onnx: true           # Cross-platform, faster CPU
    - quantization: int8   # 4x reduction, <1% quality loss
  
  generation:
    - awq_4bit: true       # Activation-aware weight quantization
    - gptq_4bit: true      # Alternative for compatibility
    - flash_attention_2: true  # 2x speed, less memory
    - continuous_batching: true  # TGI/vLLM feature
    - prefix_caching: true  # Shared prefix optimization
  
  reranker:
    - onnx_int8: true      # CPU-friendly
    - batch_size: 32       # Optimal throughput
```

---

## 5. Data & Processing

### 5.1 Data Pipeline

| Stage | Technology | Rationale |
|-------|------------|-----------|
| **Ingestion** | Apache Airflow / Temporal | Reliable, retries, visibility |
| **Stream Processing** | Kafka (MSK/Confluent) + Flink | Exactly-once, event-time, stateful |
| **Batch Processing** | Spark (EMR/Databricks) / Polars | Scale, SQL, DataFrame API |
| **Data Quality** | Great Expectations / Soda | Contracts, profiling, alerting |
| **Catalog** | DataHub / Amundsen | Lineage, discovery, governance |
| **Orchestration** | Dagster / Temporal | Software-defined assets, type-safe |

### 5.2 Vector Database: Qdrant

```yaml
# Qdrant configuration rationale
qdrant:
  why_not_pinecone: "Cost at scale, no metadata filtering flexibility, vendor lock-in"
  why_not_weaviate: "Java-based, higher resource usage, complex ops"
  why_not_milvus: "Operational complexity, separate meta store"
  why_not_pgvector: "Not purpose-built, HNSW limited, no multi-tenancy"
  why_qdrant:
    - "Rust-based, high performance, low memory"
    - "Native filtering + vector search (single query)"
    - "Payload indexing (keyword, range, geo)"
    - "Multi-tenancy with sharding"
    - "Binary quantization (10x smaller)"
    - "gRPC + REST, client SDKs"
    - "Active development, good community"
  
  deployment:
    - mode: "cluster"  # 3+ nodes for HA
    - replication_factor: 2
    - shard_number: 4  # Per collection
    - quantization: "binary"  # For embeddings > 768 dim
    - hnsw_ef: 128
    - hnsw_m: 16
```

### 5.3 Knowledge Graph: Neo4j

```yaml
neo4j:
  why_not_amazon_neptune: "Vendor lock-in, Gremlin only, cost"
  why_not_janusgraph: "Operational complexity, Titan-based"
  why_not_arangodb: "Multi-model compromise, smaller community"
  why_neo4j:
    - "Native graph storage (index-free adjacency)"
    - "Cypher query language (declarative, readable)"
    - "ACID transactions"
    - "Graph Data Science library (algorithms, ML)"
    - "Bloom (visualization), Aura (managed)"
    - "Strong ecosystem, talent pool"
  
  deployment:
    - edition: "Enterprise"  # For clustering, security
    - topology: "causal cluster"  # 3+ core, read replicas
    - page_cache: "50% RAM"
    - heap: "25% RAM"
```

---

## 6. Observability & Operations

### 6.1 Observability Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Metrics** | VictoriaMetrics (single-node) / Thanos (HA) | PromQL, compression, cost |
| **Logs** | ClickHouse (self-hosted) / Loki (Grafana Cloud) | SQL, compression, retention |
| **Traces** | Tempo (Grafana) / Jaeger | TraceQL, object storage backend |
| **Visualization** | Grafana | Unified, provisioning, alerting |
| **Alerting** | Alertmanager + PagerDuty | Routing, inhibition, on-call |
| **Synthetics** | Grafana k6 / Checkly | API + browser, CI integration |
| **Profiling** | Pyroscope / Grafana Profiler | Continuous profiling, flame graphs |

### 6.2 CI/CD & Developer Experience

| Capability | Choice | Rationale |
|------------|--------|-----------|
| **Source Control** | GitHub Enterprise | Org, security, Actions |
| **CI/CD** | GitHub Actions + ArgoCD | Native GH integration, GitOps |
| **Testing** | pytest, Playwright, k6 | Unit, E2E, load |
| **Code Quality** | Ruff, mypy, bandit, semgrep | Fast, secure, comprehensive |
| **Dependency Mgmt** | Dependabot + Renovate | Auto-updates, security |
| **Secrets** | 1Password / Vault / SealedSecrets | Rotation, audit, GitOps |
| **Documentation** | MkDocs / Notion | Versioned, searchable |
| **API Docs** | OpenAPI/Swagger + Redoc | Contract-first, generated |

---

## 7. Security & Compliance

### 7.1 Security Tools

| Capability | Choice | Rationale |
|------------|--------|-----------|
| **Secrets Management** | HashiCorp Vault / AWS Secrets Manager | Dynamic secrets, rotation, audit |
| **Certificate Mgmt** | cert-manager + Let's Encrypt / Venafi | Automated TLS, mTLS |
| **Policy Engine** | OPA/Gatekeeper / Kyverno | Admission control, validation |
| **Image Security** | Cosign + Syft + Grype / Trivy | SBOM, signing, vulnerability scan |
| **Runtime Security** | Falco / Tetragon | eBPF, syscall monitoring |
| **Network Policy** | Cilium / Calico | L3/L4/L7, Hubble observability |
| **Compliance** | OpenPolicyAgent + Regula | Policy as code, CI integration |
| **Audit Logging** | CloudTrail / Falco + Loki | Immutable, queryable |

### 7.2 Compliance Frameworks

```yaml
compliance:
  standards:
    - SOC2_Type_II
    - ISO_27001
    - HIPAA (if PHI)
    - GDPR (if EU users)
    - Indian IT Act / DPDP Act (primary jurisdiction)
  
  controls:
    encryption_at_rest: "AES-256 (KMS-managed)"
    encryption_in_transit: "TLS 1.3, mTLS via Istio"
    access_control: "RBAC + ABAC (OPA)"
    data_residency: "Region-locked deployments"
    retention: "Configurable per data class"
    right_to_erasure: "API + automated workflow"
  
  auditing:
    - immutable_audit_logs (S3 Object Lock)
    - access_logs (7 years)
    - change_logs (GitOps + K8s audit)
    - model_decisions (MLflow + custom)
```

---

## 8. Communication & Messaging

### 8.1 Event Streaming

| Pattern | Technology | Use Case |
|---------|------------|----------|
| **Event Sourcing** | Kafka (Confluent Cloud) | Audit trail, replay, multi-consumer |
| **Async Processing** | Kafka + Kafka Streams / Flink | ETL, enrichment, aggregation |
| **Task Queue** | Celery + Redis / Temporal | Long-running, retries, scheduling |
| **Pub/Sub** | NATS / Redis Streams | Low-latency, fire-and-forget |
| **Webhooks** | Svix / custom | External integrations, retries |

### 8.2 Service Communication

| Pattern | Protocol | Library |
|---------|----------|---------|
| **Sync RPC** | gRPC (protobuf) | grpcio, tonic, connect-go |
| **Async Messaging** | Kafka (Avro/Protobuf) | aiokafka, kafka-python |
| **Service Discovery** | Consul / Cloud Map / K8s DNS | Built-in |
| **Load Balancing** | Envoy (sidecar) | Istio |
| **API Gateway** | Kong / Envoy Gateway / AWS ALB | Rate limiting, auth, transform |

---

## 9. Frontend & User Experience

### 9.1 Frontend Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Framework** | React 18 + TypeScript | Ecosystem, concurrent features |
| **Build** | Vite | Fast HMR, optimized builds |
| **State** | TanStack Query + Zustand | Server state + client state |
| **UI Components** | Radix UI + Tailwind CSS | Accessible, unstyled, customizable |
| **Forms** | React Hook Form + Zod | Performant, validation |
| **Charts** | Recharts / Tremor | Declarative, responsive |
| **Real-time** | Socket.io / Server-Sent Events | Live updates, fallback |
| **Testing** | Vitest + Playwright | Unit + E2E |
| **Storybook** | Storybook 8 | Component documentation |

### 9.2 Mobile

| Approach | Choice | Rationale |
|----------|--------|-----------|
| **Primary** | Responsive Web (PWA) | Single codebase, instant updates |
| **Native** | React Native (Expo) | If app store presence needed |
| **Offline** | Service Workers + IndexedDB | Cache-first, background sync |

---

## 10. Cost Optimization

### 10.1 Strategies by Component

| Component | Strategy | Estimated Savings |
|-----------|----------|-------------------|
| **GPU Inference** | Spot instances + fallback to on-demand | 60-70% |
| **Vector DB** | Binary quantization + tiered storage | 50-80% |
| **LLM API** | Route simple queries to smaller models | 40-60% |
| **Storage** | S3 Intelligent Tiering + lifecycle | 30-50% |
| **Compute** | Right-sizing + Karpenter consolidation | 20-40% |
| **Data Transfer** | VPC endpoints, regional deployment | 10-20% |
| **Observability** | Sampling, retention policies, compression | 30-50% |

### 10.2 FinOps Practices

```yaml
finops:
  tagging:
    mandatory: [environment, team, project, cost_center]
    recommended: [owner, compliance, data_classification]
  
  budgets:
    - scope: "project/rag-core"
      monthly_limit: 50000
      alerts: [50%, 80%, 100%]
    - scope: "team/ml-platform"
      monthly_limit: 30000
      alerts: [50%, 80%, 100%]
  
  anomaly_detection:
    - enabled: true
    - lookback_days: 14
    - threshold: 2.0  # std deviations
  
  rightsizing:
    - frequency: weekly
    - cpu_threshold: 20%  # Underutilized
    - memory_threshold: 30%
  
  commit_savings:
    - compute_savings_plans: "50% of baseline"
    - reserved_instances: "RDS, ElastiCache"
```

---

## 11. Vendor Evaluation Matrix

### 11.1 Managed vs Self-Hosted Decision Framework

| Component | Managed Preferred When | Self-Hosted Preferred When |
|-----------|------------------------|---------------------------|
| **Kubernetes** | Team < 5, no platform team | Scale > 50 nodes, custom needs |
| **Vector DB** | Quick start, < 10M vectors | > 100M vectors, data residency |
| **LLM** | No GPU expertise, variable load | Consistent high volume, privacy |
| **Kafka** | Team < 3, no streaming expertise | High throughput, custom logic |
| **PostgreSQL** | Standard workloads, < 1TB | Extensions, tuning, compliance |
| **Redis** | Cache only, < 50GB | Pub/sub, streams, clustering |
| **Observability** | Team < 10, limited SRE | Data sovereignty, cost at scale |

### 11.2 Cloud Provider Selection

| Factor | AWS | GCP | Azure | Multi-Cloud |
|--------|-----|-----|-------|-------------|
| **Kubernetes** | EKS (mature) | GKE (best autoscaling) | AKS (integration) | Complexity |
| **GPU Availability** | Best (P4, P5) | Good (A3) | Good (NDv5) | Fragmented |
| **AI Services** | Bedrock, SageMaker | Vertex AI | Azure AI | Best-of-breed |
| **Data Residency (India)** | Mumbai, Hyderabad | Delhi, Mumbai | Pune, Chennai | All support |
| **Cost** | Complex pricing | Sustained use discounts | Enterprise agreements | Negotiation |
| **Talent Pool** | Largest | Growing | Enterprise-focused | Split |

**Recommendation**: **Primary: AWS (Mumbai/Hyderabad)** for India data residency, GPU availability, and ecosystem maturity. **Secondary: GCP** for Vertex AI and BigQuery analytics. Multi-cloud only for DR.

---

## 12. Technology Radar

### 12.1 Adopt (Proven, Standardize)

- Python 3.11+, FastAPI, Pydantic v2
- Kubernetes, Istio, ArgoCD, Helm
- Qdrant, Neo4j, PostgreSQL, Redis
- VictoriaMetrics, ClickHouse, Tempo, Grafana
- TGI/vLLM for model serving
- MLflow, Feast, Kubeflow
- OPA, Vault, cert-manager, Falco

### 12.2 Trial (Evaluating for Specific Use Cases)

- **DuckDB** - Embedded analytics, local development
- **Polars** - Faster DataFrame alternative to Pandas
- **Temporal** - Durable execution for complex workflows
- **LangGraph** - Agent orchestration (Phase 13)
- **Weaviate** - If hybrid search needs grow
- **ParadeDB** - PostgreSQL-based search alternative
- **Unsloth** - Faster fine-tuning
- **Mojo** - Python superset for performance critical paths

### 12.3 Assess (Monitoring, Not Yet Adopting)

- **Rust for Python extensions** (PyO3) - For hot paths
- **Apache Arrow / DataFusion** - In-memory analytics
- **Substrait** - Cross-engine query plans
- **WebAssembly (Wasm)** - Plugin sandboxing
- **Apache Iceberg** - Table format for data lake
- **Trino** - Federated query engine

### 12.4 Hold (Deprecating/Avoiding)

- **Elasticsearch** for vectors (use Qdrant)
- **Plain Kafka Streams** (prefer Flink/Temporal)
- **Custom model serving** (use TGI/vLLM)
- **Monolithic deployments** (decompose to services)
- **Manual infrastructure** (GitOps only)

---

## 13. Integration Patterns

### 13.1 Service Communication Matrix

```
                    ┌─────────────────┐
                    │   API Gateway   │  (Kong/Envoy Gateway)
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Query API      │ │  Admin API      │ │  Webhook API    │
│  (FastAPI)      │ │  (FastAPI)      │ │  (FastAPI)      │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Mesh (Istio)                      │
│  mTLS │ Traffic Split │ Retry │ Timeout │ Circuit Breaker   │
└─────────────────────────────────────────────────────────────┘
         │                   │                   │
    ┌────┴────┐       ┌─────┴─────┐       ┌────┴────┐
    ▼         ▼       ▼           ▼       ▼         ▼
┌───────┐ ┌───────┐ ┌────────┐ ┌────────┐ ┌───────┐ ┌───────┐
│Classif│ │Retri- │ │Genera- │ │  KG    │ │Juris- │ │Multi- │
│ication│ │eval   │ │tion    │ │Service │ │dict.  │ │lingual│
└───┬───┘ └───┬───┘ └────┬───┘ └────┬───┘ └───┬───┘ └───┬───┘
    │         │          │         │         │         │
    ▼         ▼          ▼         ▼         ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Message Bus (Kafka)                     │
│  Events: query.received, classification.done, generation.done│
└─────────────────────────────────────────────────────────────┘
```

### 13.2 Data Flow Patterns

```python
# src/patterns/data_flow.py
from enum import Enum
from dataclasses import dataclass
from typing import Generic, TypeVar, AsyncGenerator

T = TypeVar('T')
R = TypeVar('R')

class ProcessingPattern(Enum):
    """Data flow patterns for different workloads."""
    REQUEST_RESPONSE = "request_response"      # Synchronous API
    STREAM_PROCESSING = "stream_processing"    # Kafka -> Flink -> Sink
    BATCH_PIPELINE = "batch_pipeline"          # Airflow -> Spark -> Warehouse
    EVENT_SOURCING = "event_sourcing"          # Commands -> Events -> Projections
    CQRS = "cqrs"                              # Separate read/write models
    SAGA = "saga"                              # Distributed transactions
    PIPELINE = "pipeline"                      # Linear stages with checkpoints

@dataclass
class PipelineStage(Generic[T, R]):
    name: str
    process: Callable[[T], AsyncGenerator[R, None]]
    checkpoint: bool = True
    parallelism: int = 1
    timeout_seconds: float = 300
    retry_policy: RetryPolicy = None
```

---

## 14. Decision Log

| Decision | Date | Status | Context |
|----------|------|--------|---------|
| Python 3.11+ for services | 2026-01 | ✅ Adopted | Performance, typing, ecosystem |
| Qdrant for vectors | 2026-01 | ✅ Adopted | Filtering, multi-tenancy, cost |
| Neo4j for KG | 2026-01 | ✅ Adopted | Native graph, Cypher, GDS |
| Istio for service mesh | 2026-01 | ✅ Adopted | mTLS, traffic management |
| VictoriaMetrics for metrics | 2026-01 | ✅ Adopted | Cost, PromQL, single binary |
| ClickHouse for logs | 2026-01 | ✅ Adopted | SQL, compression, retention |
| TGI for model serving | 2026-01 | ✅ Adopted | Continuous batching, quantization |
| GitHub Actions + ArgoCD | 2026-01 | ✅ Adopted | Native GH, GitOps |
| BGE-M3 embeddings | 2026-01 | ✅ Adopted | Multilingual, strong benchmarks |
| NLLB-200 translation | 2026-01 | ✅ Adopted | 200 languages, open weights |

---

## 15. Open Research Questions

| ID | Question | Context |
|----|----------|---------|
| ORQ-56 | Should we adopt WebAssembly for plugin sandboxing? | User-defined rules, custom extractors |
| ORQ-57 | Can DuckDB replace ClickHouse for log analytics? | Simpler ops, embedded, but less scale |
| ORQ-58 | Is Temporal better than Airflow for ML pipelines? | Durable execution, but learning curve |
| ORQ-59 | Should we use Arrow/Parquet for inter-service data? | Zero-copy, but schema evolution complexity |
| ORQ-60 | When to migrate from PGVector to Qdrant? | Threshold: >10M vectors or complex filtering |
| ORQ-61 | Can we use SQLite (Turso/LibSQL) for edge caching? | Embedded replicas, but consistency model |

---

## 16. Summary

Phase 23 establishes the technology foundation with:

1. **Language Strategy**: Python (services/ML), Rust (performance), TypeScript (frontend), Go (infra)
2. **Platform**: Kubernetes (EKS) + Istio + ArgoCD for GitOps
3. **Storage**: Qdrant (vectors), Neo4j (KG), PostgreSQL (relational), S3 (objects), Redis (cache)
4. **ML Stack**: BGE-M3, GPT-4o/Claude, Llama-3.1, TGI/vLLM, MLflow, Feast, Kubeflow
5. **Observability**: VictoriaMetrics, ClickHouse, Tempo, Grafana, k6
6. **Security**: Vault, OPA, Falco, Cosign, cert-manager
7. **Messaging**: Kafka (events), gRPC (sync), NATS (pub/sub)
8. **Frontend**: React 18, TypeScript, Vite, TanStack Query, Radix UI
9. **Cost Optimization**: Spot GPUs, quantization, tiered storage, Savings Plans
10. **11 Open Research Questions** for emerging technology evaluation

All choices are documented with rationale, alternatives, and integration patterns to enable consistent architectural decisions across the 26 phases.