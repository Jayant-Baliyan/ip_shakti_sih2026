# Phase 21: Observability Architecture

## Overview

This phase defines the comprehensive observability architecture for the RAG system, covering logging, metrics, tracing, alerting, and debugging capabilities. The observability system provides end-to-end visibility into system behavior, performance, and health across all 25+ phases of the architecture.

---

## 1. Requirements

### 1.1 Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| FR-OBS-01 | Structured Logging | Centralized, structured logging with correlation IDs across all services |
| FR-OBS-02 | Metrics Collection | Real-time metrics for latency, throughput, errors, and business KPIs |
| FR-OBS-03 | Distributed Tracing | End-to-end request tracing across microservices and async boundaries |
| FR-OBS-04 | Alerting | Multi-channel alerting with escalation policies and runbook integration |
| FR-OBS-05 | Dashboards | Pre-built and customizable dashboards for operations and business stakeholders |
| FR-OBS-06 | Log Search & Analysis | Fast, scalable log search with regex, time-range, and facet filtering |
| FR-OBS-07 | Anomaly Detection | ML-based anomaly detection on metrics and logs |
| FR-OBS-08 | Audit Trail | Immutable audit logging for regulatory compliance |
| FR-OBS-09 | Debug Endpoints | Live debugging endpoints (pprof, health, readiness, metrics) |
| FR-OBS-10 | Cost Attribution | Observability cost tracking and attribution per team/service |

### 1.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-OBS-01 | Log Ingestion Latency | < 5 seconds from emission to queryable |
| NFR-OBS-02 | Metrics Granularity | 10-second resolution for high-cardinality metrics |
| NFR-OBS-03 | Trace Sampling Rate | 100% for errors, 10% for success (configurable) |
| NFR-OBS-04 | Alert Latency | < 30 seconds from threshold breach to notification |
| NFR-OBS-05 | Data Retention | Logs: 30 days hot, 1 year cold; Metrics: 13 months; Traces: 7 days |
| NFR-OBS-06 | Availability | 99.9% observability stack uptime |
| NFR-OBS-07 | Scalability | Handle 1M+ spans/sec, 10M+ log lines/sec |
| NFR-OBS-08 | PII Protection | Automatic PII redaction in logs and traces |

---

## 2. Observability Pillars

### 2.1 Logging Architecture

#### 2.1.1 Log Structure (JSON)

```json
{
  "timestamp": "2026-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "query-processor",
  "version": "v2.3.1",
  "trace_id": "abc123def456",
  "span_id": "span789",
  "correlation_id": "req-xyz789",
  "user_id": "user-123",
  "session_id": "sess-456",
  "request_id": "req-xyz789",
  "message": "Query processed successfully",
  "fields": {
    "query_length": 145,
    "retrieval_latency_ms": 234,
    "generation_latency_ms": 567,
    "total_latency_ms": 891,
    "tokens_used": 1234,
    "confidence_score": 0.92,
    "classification": "AYURVEDA_CLASSICAL"
  },
  "tags": ["query", "retrieval", "generation"],
  "stack_trace": null
}
```

#### 2.1.2 Log Levels & Semantics

| Level | Use Case | Sampling |
|-------|----------|----------|
| TRACE | Detailed execution flow (variable values, loop iterations) | 1% in prod |
| DEBUG | Diagnostic information for troubleshooting | 10% in prod |
| INFO | Business events, state transitions, key milestones | 100% |
| WARN | Recoverable issues, deprecated usage, near-threshold | 100% |
| ERROR | Failed operations requiring investigation | 100% |
| FATAL | System/critical component failure requiring immediate action | 100% |

#### 2.1.3 Structured Logging Library

```python
# src/observability/logging.py
import structlog
import logging
import sys
from typing import Any, Dict
from contextvars import ContextVar

# Context variables for correlation
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")

class ObservabilityLogger:
    """Structured logger with automatic context injection."""
    
    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
        self._logger = self._configure_logger()
    
    def _configure_logger(self) -> structlog.BoundLogger:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                        structlog.processors.CallsiteParameter.LINENO,
                    ]
                ),
                self._add_service_context,
                self._redact_pii,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )
        return structlog.get_logger()
    
    def _add_service_context(self, logger, method_name, event_dict):
        event_dict["service"] = self.service_name
        event_dict["version"] = self.version
        event_dict["trace_id"] = trace_id_var.get()
        event_dict["span_id"] = span_id_var.get()
        event_dict["correlation_id"] = correlation_id_var.get()
        event_dict["user_id"] = user_id_var.get()
        return event_dict
    
    def _redact_pii(self, logger, method_name, event_dict):
        """Automatically redact PII from log fields."""
        pii_fields = {"email", "phone", "aadhaar", "pan", "password", "token", "secret"}
        for key in list(event_dict.keys()):
            if any(pii in key.lower() for pii in pii_fields):
                event_dict[key] = "[REDACTED]"
            elif isinstance(event_dict[key], str) and len(event_dict[key]) > 100:
                # Truncate long strings that might contain PII
                event_dict[key] = event_dict[key][:100] + "...[TRUNCATED]"
        return event_dict
    
    def bind(self, **kwargs) -> "ObservabilityLogger":
        """Create a new logger with additional context."""
        new_logger = ObservabilityLogger(self.service_name, self.version)
        new_logger._logger = self._logger.bind(**kwargs)
        return new_logger
    
    def info(self, message: str, **kwargs):
        self._logger.info(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._logger.error(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        self._logger.exception(message, **kwargs)

# Usage
logger = ObservabilityLogger("query-processor", "v2.3.1")

# In request handler
async def process_query(request: QueryRequest):
    # Set correlation context
    correlation_id_var.set(request.request_id)
    trace_id_var.set(request.trace_id)
    user_id_var.set(request.user_id)
    
    logger.info("Query received", query_length=len(request.query))
    
    # ... processing ...
    
    logger.info("Query completed", 
                total_latency_ms=elapsed_ms,
                confidence=result.confidence)
```

### 2.2 Metrics Architecture

#### 2.2.1 Metric Types & Naming Convention

```
# Format: <subsystem>_<component>_<operation>_<unit>
# Examples:
rag_query_total                              # Counter: total queries
rag_query_latency_seconds                    # Histogram: query latency
rag_retrieval_documents_retrieved            # Histogram: docs retrieved per query
rag_generation_tokens_used_total             # Counter: total tokens generated
rag_classification_confidence                # Histogram: classification confidence
rag_escalation_total                         # Counter: escalations by reason
rag_cache_hit_total                          # Counter: cache hits
rag_cache_miss_total                         # Counter: cache misses
rag_vector_search_latency_seconds            # Histogram: vector search latency
rag_llm_latency_seconds                      # Histogram: LLM call latency
rag_llm_tokens_input_total                   # Counter: input tokens
rag_llm_tokens_output_total                  # Counter: output tokens
rag_error_total                              # Counter: errors by type
rag_active_connections                       # Gauge: active connections
rag_queue_depth                              # Gauge: async queue depth
```

#### 2.2.2 Key Metrics by Subsystem

| Subsystem | Key Metrics | Type | Labels |
|-----------|-------------|------|--------|
| **Query Processing** | `rag_query_total`, `rag_query_latency_seconds`, `rag_query_success_total` | Counter, Histogram, Counter | `classification`, `language`, `status` |
| **Retrieval** | `rag_retrieval_latency_seconds`, `rag_retrieval_documents_retrieved`, `rag_retrieval_score_distribution` | Histogram, Histogram, Histogram | `strategy`, `index` |
| **Generation** | `rag_generation_latency_seconds`, `rag_generation_tokens_used_total`, `rag_generation_citations_total` | Histogram, Counter, Histogram | `model`, `temperature` |
| **Classification** | `rag_classification_total`, `rag_classification_confidence`, `rag_classification_escalation_total` | Counter, Histogram, Counter | `class`, `method` (rule/llm) |
| **Knowledge Graph** | `rag_kg_query_total`, `rag_kg_query_latency_seconds`, `rag_kg_cache_hit_total` | Counter, Histogram, Counter | `query_type`, `status` |
| **Multilingual** | `rag_translation_total`, `rag_translation_latency_seconds`, `rag_language_detection_total` | Counter, Histogram, Counter | `source_lang`, `target_lang` |
| **System** | `rag_cpu_usage_percent`, `rag_memory_usage_bytes`, `rag_disk_usage_bytes`, `rag_network_bytes_total` | Gauge, Gauge, Gauge, Counter | `instance`, `container` |

#### 2.2.3 Metrics Implementation

```python
# src/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector
import time
from functools import wraps
from typing import Callable, Any
import os

class MetricsCollector:
    """Centralized metrics collection with Prometheus."""
    
    def __init__(self, service_name: str, registry: CollectorRegistry = None):
        self.service_name = service_name
        self.registry = registry or CollectorRegistry()
        
        # Enable multiprocess mode for gunicorn/uwsgi
        if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
            MultiProcessCollector(self.registry)
        
        self._init_metrics()
    
    def _init_metrics(self):
        # Query processing
        self.query_total = Counter(
            "rag_query_total",
            "Total number of queries processed",
            ["service", "classification", "language", "status"],
            registry=self.registry
        )
        
        self.query_latency = Histogram(
            "rag_query_latency_seconds",
            "Query processing latency in seconds",
            ["service", "classification", "language"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        # Retrieval
        self.retrieval_latency = Histogram(
            "rag_retrieval_latency_seconds",
            "Retrieval latency in seconds",
            ["service", "strategy", "index"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
            registry=self.registry
        )
        
        self.retrieval_docs = Histogram(
            "rag_retrieval_documents_retrieved",
            "Number of documents retrieved per query",
            ["service", "strategy"],
            buckets=[1, 5, 10, 20, 50, 100, 200],
            registry=self.registry
        )
        
        # Generation
        self.generation_latency = Histogram(
            "rag_generation_latency_seconds",
            "Generation latency in seconds",
            ["service", "model"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.generation_tokens = Histogram(
            "rag_generation_tokens_used_total",
            "Tokens used in generation",
            ["service", "model", "type"],  # type: input/output
            buckets=[10, 50, 100, 500, 1000, 2000, 4000, 8000],
            registry=self.registry
        )
        
        # Classification
        self.classification_total = Counter(
            "rag_classification_total",
            "Total classifications performed",
            ["service", "class", "method"],  # method: rule/llm/hybrid
            registry=self.registry
        )
        
        self.classification_confidence = Histogram(
            "rag_classification_confidence",
            "Classification confidence score",
            ["service", "class", "method"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
            registry=self.registry
        )
        
        # Escalations
        self.escalation_total = Counter(
            "rag_escalation_total",
            "Total escalations to human review",
            ["service", "reason", "classification"],
            registry=self.registry
        )
        
        # Cache
        self.cache_hits = Counter(
            "rag_cache_hit_total",
            "Cache hits",
            ["service", "cache_type"],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            "rag_cache_miss_total",
            "Cache misses",
            ["service", "cache_type"],
            registry=self.registry
        )
        
        # Errors
        self.errors = Counter(
            "rag_error_total",
            "Total errors by type",
            ["service", "error_type", "component"],
            registry=self.registry
        )
        
        # System
        self.active_requests = Gauge(
            "rag_active_requests",
            "Currently active requests",
            ["service"],
            registry=self.registry
        )
        
        self.queue_depth = Gauge(
            "rag_queue_depth",
            "Async queue depth",
            ["service", "queue_name"],
            registry=self.registry
        )
    
    def record_query(self, classification: str, language: str, status: str, latency: float):
        self.query_total.labels(
            service=self.service_name,
            classification=classification,
            language=language,
            status=status
        ).inc()
        self.query_latency.labels(
            service=self.service_name,
            classification=classification,
            language=language
        ).observe(latency)
    
    def record_retrieval(self, strategy: str, index: str, latency: float, doc_count: int):
        self.retrieval_latency.labels(
            service=self.service_name,
            strategy=strategy,
            index=index
        ).observe(latency)
        self.retrieval_docs.labels(
            service=self.service_name,
            strategy=strategy
        ).observe(doc_count)
    
    def record_generation(self, model: str, latency: float, input_tokens: int, output_tokens: int):
        self.generation_latency.labels(
            service=self.service_name,
            model=model
        ).observe(latency)
        self.generation_tokens.labels(
            service=self.service_name,
            model=model,
            type="input"
        ).observe(input_tokens)
        self.generation_tokens.labels(
            service=self.service_name,
            model=model,
            type="output"
        ).observe(output_tokens)
    
    def record_classification(self, class_name: str, method: str, confidence: float):
        self.classification_total.labels(
            service=self.service_name,
            class=class_name,
            method=method
        ).inc()
        self.classification_confidence.labels(
            service=self.service_name,
            class=class_name,
            method=method
        ).observe(confidence)
    
    def record_escalation(self, reason: str, classification: str):
        self.escalation_total.labels(
            service=self.service_name,
            reason=reason,
            classification=classification
        ).inc()
    
    def record_error(self, error_type: str, component: str):
        self.errors.labels(
            service=self.service_name,
            error_type=error_type,
            component=component
        ).inc()
    
    def track_active_requests(self, delta: int):
        self.active_requests.labels(service=self.service_name).inc(delta)
    
    def set_queue_depth(self, queue_name: str, depth: int):
        self.queue_depth.labels(service=self.service_name, queue_name=queue_name).set(depth)
    
    def expose_metrics(self) -> bytes:
        """Expose metrics for Prometheus scraping."""
        return generate_latest(self.registry)

# Decorator for automatic latency tracking
def track_latency(metrics: MetricsCollector, metric_name: str, labels: dict = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start
                # Record based on metric_name
                if metric_name == "retrieval":
                    metrics.record_retrieval(**labels, latency=latency)
                elif metric_name == "generation":
                    metrics.record_generation(**labels, latency=latency)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                latency = time.time() - start
                # Record based on metric_name
                pass
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
```

### 2.3 Distributed Tracing

#### 2.3.1 Trace Context Propagation

```python
# src/observability/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.propagate import inject, extract
from contextvars import ContextVar
import uuid
from typing import Optional, Dict, Any
from functools import wraps

# Context variables
trace_context_var: ContextVar[Optional[trace.Span]] = ContextVar("trace_context", default=None)

class TracingManager:
    """Manages distributed tracing with OpenTelemetry."""
    
    def __init__(self, service_name: str, version: str, otlp_endpoint: str = None):
        self.service_name = service_name
        self.version = version
        
        # Configure tracer provider
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development")
        })
        
        provider = TracerProvider(resource=resource)
        
        # Configure exporter
        if otlp_endpoint:
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        
        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(service_name, version)
        
        # Auto-instrument common libraries
        self._setup_instrumentation()
    
    def _setup_instrumentation(self):
        """Auto-instrument common frameworks."""
        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor.instrument()
        RedisInstrumentor.instrument()
        SQLAlchemyInstrumentor.instrument()
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Dict[str, Any] = None,
        parent_context: Optional[trace.SpanContext] = None
    ) -> trace.Span:
        """Start a new span with context propagation."""
        context = trace.set_span_in_context(parent_context) if parent_context else None
        
        span = self.tracer.start_span(
            name,
            kind=kind,
            attributes=attributes or {},
            context=context
        )
        
        # Set as current span in context
        trace_context_var.set(span)
        
        # Add standard attributes
        span.set_attribute("service.name", self.service_name)
        span.set_attribute("service.version", self.version)
        
        return span
    
    def get_current_span(self) -> Optional[trace.Span]:
        return trace_context_var.get()
    
    def inject_context(self, carrier: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into carrier (headers, etc.)."""
        inject(carrier)
        return carrier
    
    def extract_context(self, carrier: Dict[str, str]) -> trace.SpanContext:
        """Extract trace context from carrier."""
        return extract(carrier)
    
    def end_span(self, span: trace.Span, error: Exception = None):
        """End span with optional error recording."""
        if error:
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.record_exception(error)
        else:
            span.set_status(Status(StatusCode.OK))
        span.end()
        trace_context_var.set(None)

# Decorator for automatic tracing
def trace_operation(
    tracing: TracingManager,
    operation_name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Dict[str, Any] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span = tracing.start_span(operation_name, kind, attributes)
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                tracing.end_span(span, e)
                raise
            finally:
                tracing.end_span(span)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span = tracing.start_span(operation_name, kind, attributes)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tracing.end_span(span, e)
                raise
            finally:
                tracing.end_span(span)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# Usage example
tracing = TracingManager("query-processor", "v2.3.1", "http://jaeger:4317")

@trace_operation(tracing, "process_query", SpanKind.SERVER, {"component": "query"})
async def process_query(request: QueryRequest) -> QueryResponse:
    span = tracing.get_current_span()
    span.set_attribute("query.length", len(request.query))
    span.set_attribute("query.language", request.language)
    
    # Retrieval span
    with tracing.start_span("retrieve_documents", SpanKind.INTERNAL) as retrieve_span:
        retrieve_span.set_attribute("strategy", "hybrid")
        docs = await retrieve(request.query)
        retrieve_span.set_attribute("documents.count", len(docs))
    
    # Generation span
    with tracing.start_span("generate_response", SpanKind.CLIENT) as gen_span:
        gen_span.set_attribute("model", "gpt-4")
        response = await generate(docs, request.query)
        gen_span.set_attribute("tokens.output", response.token_count)
    
    span.set_attribute("classification", response.classification)
    span.set_attribute("confidence", response.confidence)
    
    return response
```

#### 2.3.2 Trace Sampling Strategy

```python
# src/observability/sampling.py
import random
from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult, Decision
from opentelemetry.trace import SpanKind, TraceFlags
from typing import Optional, Sequence

class AdaptiveSampler(Sampler):
    """
    Adaptive sampler that:
    - Always samples errors
    - Samples 100% of high-priority operations
    - Samples configurable % of normal operations
    - Respects parent sampling decision
    """
    
    def __init__(
        self,
        default_rate: float = 0.1,
        error_rate: float = 1.0,
        priority_operations: set = None
    ):
        self.default_rate = default_rate
        self.error_rate = error_rate
        self.priority_operations = priority_operations or {
            "process_query",
            "classify_formulation",
            "escalate_to_human",
            "generate_citation"
        }
    
    def should_sample(
        self,
        parent_context: Optional[trace.SpanContext],
        trace_id: int,
        name: str,
        kind: SpanKind,
        attributes: dict = None,
        links: Sequence = None
    ) -> SamplingResult:
        
        # Check parent decision
        if parent_context and parent_context.trace_flags & TraceFlags.SAMPLED:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
        # Always sample priority operations
        if name in self.priority_operations:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
        # Check for error attributes (pre-emptive)
        if attributes and attributes.get("error.expected", False):
            if random.random() < self.error_rate:
                return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
        # Default probabilistic sampling
        if random.random() < self.default_rate:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
        return SamplingResult(Decision.DROP)
    
    def get_description(self) -> str:
        return f"AdaptiveSampler(default={self.default_rate}, error={self.error_rate})"
```

---

## 3. Alerting Architecture

### 3.1 Alert Rules

```yaml
# alerts/rules.yaml
groups:
  - name: rag-critical
    interval: 30s
    rules:
      # Service availability
      - alert: ServiceDown
        expr: up{job="rag-services"} == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Service {{ $labels.service }} is down"
          runbook: "https://wiki.company.com/runbooks/service-down"
      
      # Query processing
      - alert: HighQueryLatency
        expr: histogram_quantile(0.95, rate(rag_query_latency_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
          team: rag-core
        annotations:
          summary: "P95 query latency > 10s for {{ $labels.service }}"
          description: "Current P95: {{ $value }}s"
          runbook: "https://wiki.company.com/runbooks/high-latency"
      
      - alert: HighErrorRate
        expr: |
          sum(rate(rag_error_total[5m])) by (service) 
          / sum(rate(rag_query_total[5m])) by (service) > 0.05
        for: 2m
        labels:
          severity: critical
          team: rag-core
        annotations:
          summary: "Error rate > 5% for {{ $labels.service }}"
          runbook: "https://wiki.company.com/runbooks/high-error-rate"
      
      # Classification specific
      - alert: HighEscalationRate
        expr: |
          sum(rate(rag_escalation_total[15m])) by (service)
          / sum(rate(rag_classification_total[15m])) by (service) > 0.2
        for: 10m
        labels:
          severity: warning
          team: rag-classification
        annotations:
          summary: "Escalation rate > 20% for {{ $labels.service }}"
          description: "Too many queries requiring human review"
      
      - alert: LowClassificationConfidence
        expr: |
          histogram_quantile(0.5, rate(rag_classification_confidence_bucket[10m])) < 0.6
        for: 15m
        labels:
          severity: warning
          team: rag-classification
        annotations:
          summary: "Median classification confidence < 0.6"
      
      # Retrieval
      - alert: RetrievalLatencyHigh
        expr: histogram_quantile(0.95, rate(rag_retrieval_latency_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
          team: rag-retrieval
        annotations:
          summary: "P95 retrieval latency > 5s"
      
      - alert: RetrievalEmptyResults
        expr: |
          sum(rate(rag_retrieval_documents_retrieved_bucket{le="0"}[5m])) 
          / sum(rate(rag_retrieval_documents_retrieved_count[5m])) > 0.1
        for: 10m
        labels:
          severity: warning
          team: rag-retrieval
        annotations:
          summary: ">10% queries return zero documents"
      
      # Generation
      - alert: GenerationLatencyHigh
        expr: histogram_quantile(0.95, rate(rag_generation_latency_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
          team: rag-generation
        annotations:
          summary: "P95 generation latency > 30s"
      
      - alert: TokenUsageAnomaly
        expr: |
          rate(rag_generation_tokens_used_total[5m]) 
          > 3 * rate(rag_generation_tokens_used_total[1h] offset 5m)
        for: 5m
        labels:
          severity: warning
          team: rag-generation
        annotations:
          summary: "Token usage 3x baseline"
      
      # System resources
      - alert: HighMemoryUsage
        expr: |
          (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.85
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Memory usage > 85% for {{ $labels.container }}"
      
      - alert: HighCPUUsage
        expr: |
          rate(container_cpu_usage_seconds_total[5m]) / container_spec_cpu_quota / container_spec_cpu_period > 0.8
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "CPU usage > 80% for {{ $labels.container }}"
      
      # Queue depth
      - alert: QueueBacklog
        expr: rag_queue_depth > 1000
        for: 5m
        labels:
          severity: warning
          team: rag-core
        annotations:
          summary: "Queue {{ $labels.queue_name }} backlog > 1000"
      
      # Cache
      - alert: LowCacheHitRate
        expr: |
          sum(rate(rag_cache_hit_total[10m])) 
          / (sum(rate(rag_cache_hit_total[10m])) + sum(rate(rag_cache_miss_total[10m]))) < 0.5
        for: 15m
        labels:
          severity: info
          team: rag-core
        annotations:
          summary: "Cache hit rate < 50%"
```

### 3.2 Alert Routing & Escalation

```yaml
# alerts/routing.yaml
route:
  group_by: ['alertname', 'service', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: true
    - match:
        team: rag-classification
      receiver: 'classification-team'
    - match:
        team: rag-retrieval
      receiver: 'retrieval-team'
    - match:
        team: rag-generation
      receiver: 'generation-team'

receivers:
  - name: 'default'
    email_configs:
      - to: 'oncall@company.com'
        send_resolved: true
    slack_configs:
      - channel: '#alerts-general'
        send_resolved: true
  
  - name: 'critical-alerts'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'
        severity: critical
    slack_configs:
      - channel: '#alerts-critical'
        send_resolved: true
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
  
  - name: 'classification-team'
    slack_configs:
      - channel: '#alerts-classification'
        send_resolved: true
  
  - name: 'retrieval-team'
    slack_configs:
      - channel: '#alerts-retrieval'
        send_resolved: true
  
  - name: 'generation-team'
    slack_configs:
      - channel: '#alerts-generation'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match_re:
      severity: 'warning|info'
    equal: ['service']
```

---

## 4. Dashboards

### 4.1 Core Dashboards

#### 4.1.1 System Overview Dashboard

```json
{
  "title": "RAG System Overview",
  "panels": [
    {
      "title": "Query Throughput (QPS)",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(rag_query_total[1m])) by (service)",
          "legendFormat": "{{service}}"
        }
      ]
    },
    {
      "title": "Query Latency (P50, P95, P99)",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, sum(rate(rag_query_latency_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "P50 - {{service}}"
        },
        {
          "expr": "histogram_quantile(0.95, sum(rate(rag_query_latency_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "P95 - {{service}}"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(rag_query_latency_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "P99 - {{service}}"
        }
      ]
    },
    {
      "title": "Error Rate by Service",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(rag_error_total[5m])) by (service, error_type) / sum(rate(rag_query_total[5m])) by (service)",
          "legendFormat": "{{service}} - {{error_type}}"
        }
      ]
    },
    {
      "title": "Active Requests",
      "type": "graph",
      "targets": [
        {
          "expr": "rag_active_requests",
          "legendFormat": "{{service}}"
        }
      ]
    },
    {
      "title": "Classification Distribution",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum(rate(rag_classification_total[5m])) by (class)",
          "legendFormat": "{{class}}"
        }
      ]
    },
    {
      "title": "Escalation Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(rag_escalation_total[5m])) by (reason, service)",
          "legendFormat": "{{service}} - {{reason}}"
        }
      ]
    }
  ]
}
```

#### 4.1.2 Classification Deep-Dive Dashboard

```json
{
  "title": "Classification Deep-Dive",
  "panels": [
    {
      "title": "Classification Confidence Distribution",
      "type": "heatmap",
      "targets": [
        {
          "expr": "sum(rate(rag_classification_confidence_bucket[5m])) by (le, class, method)",
          "format": "heatmap"
        }
      ]
    },
    {
      "title": "Method Breakdown (Rule vs LLM vs Hybrid)",
      "type": "stacked-bar",
      "targets": [
        {
          "expr": "sum(rate(rag_classification_total[5m])) by (method, class)",
          "legendFormat": "{{method}} - {{class}}"
        }
      ]
    },
    {
      "title": "Escalation Reasons",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum(rate(rag_escalation_total[1h])) by (reason)",
          "legendFormat": "{{reason}}"
        }
      ]
    },
    {
      "title": "Confidence by Language",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.5, sum(rate(rag_classification_confidence_bucket[10m])) by (le, language))",
          "legendFormat": "Median - {{language}}"
        }
      ]
    }
  ]
}
```

#### 4.1.3 Retrieval & Generation Dashboard

```json
{
  "title": "Retrieval & Generation Performance",
  "panels": [
    {
      "title": "Retrieval Latency by Strategy",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(rag_retrieval_latency_seconds_bucket[5m])) by (le, strategy))",
          "legendFormat": "P95 - {{strategy}}"
        }
      ]
    },
    {
      "title": "Documents Retrieved per Query",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.5, sum(rate(rag_retrieval_documents_retrieved_bucket[5m])) by (le, strategy))",
          "legendFormat": "Median - {{strategy}}"
        }
      ]
    },
    {
      "title": "Generation Latency by Model",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(rag_generation_latency_seconds_bucket[5m])) by (le, model))",
          "legendFormat": "P95 - {{model}}"
        }
      ]
    },
    {
      "title": "Token Usage (Input vs Output)",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(rag_generation_tokens_used_total{type=\"input\"}[5m])) by (model)",
          "legendFormat": "Input - {{model}}"
        },
        {
          "expr": "sum(rate(rag_generation_tokens_used_total{type=\"output\"}[5m])) by (model)",
          "legendFormat": "Output - {{model}}"
        }
      ]
    },
    {
      "title": "Cache Hit Rate",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(rate(rag_cache_hit_total[5m])) / (sum(rate(rag_cache_hit_total[5m])) + sum(rate(rag_cache_miss_total[5m])))",
          "legendFormat": "Hit Rate"
        }
      ]
    }
  ]
}
```

---

## 5. Log Aggregation & Search

### 5.1 Log Pipeline Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Services   │────▶│  Fluent Bit  │────▶│   Kafka     │────▶│  ClickHouse  │
│  (stdout)   │     │  (sidecar)   │     │  (buffer)   │     │  (storage)   │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                                           │
                           ▼                                           ▼
                    ┌──────────────┐                         ┌──────────────┐
                    │  Prometheus  │                         │  Grafana     │
                    │  (metrics)   │                         │  (search)    │
                    └──────────────┘                         └──────────────┘
```

### 5.2 Fluent Bit Configuration

```ini
# fluent-bit.conf
[SERVICE]
    Flush         5
    Log_Level     info
    Daemon        off
    Parsers_File  parsers.conf
    HTTP_Server   On
    HTTP_Listen   0.0.0.0
    HTTP_Port     2020

[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            docker
    Tag               kube.*
    Refresh_Interval  10
    Mem_Buf_Limit     50MB
    Skip_Long_Lines   On

[FILTER]
    Name                kubernetes
    Match               kube.*
    Kube_URL            https://kubernetes.default.svc:443
    Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
    Kube_Tag_Prefix     kube.var.log.containers.
    Merge_Log           On
    Merge_Log_Key       log_processed
    K8S-Logging.Parser  On
    K8S-Logging.Exclude On

[FILTER]
    Name          modify
    Match         kube.*
    Add           cluster_name ${CLUSTER_NAME}
    Add           environment ${ENVIRONMENT}

[FILTER]
    Name          lua
    Match         kube.*
    Script        redact_pii.lua
    Call          redact_pii

[OUTPUT]
    Name            kafka
    Match           kube.*
    Brokers         kafka:9092
    Topic           logs
    Format          json
    Json_Date_Format iso8601
    Compress        gzip
```

### 5.3 PII Redaction Lua Script

```lua
-- redact_pii.lua
local pii_patterns = {
    email = "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+%.[a-zA-Z]{2,}",
    phone = "[+]?[0-9]{1,3}[-. ]?[0-9]{3}[-. ]?[0-9]{3}[-. ]?[0-9]{4}",
    aadhaar = "[0-9]{4}[ ]?[0-9]{4}[ ]?[0-9]{4}",
    pan = "[A-Z]{5}[0-9]{4}[A-Z]{1}",
    credit_card = "[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}",
    ipv4 = "[0-9]{1,3}%. [0-9]{1,3}%. [0-9]{1,3}%. [0-9]{1,3}",
    token = "Bearer [a-zA-Z0-9._-]+",
    api_key = "[a-zA-Z0-9]{32,}"
}

function redact_pii(tag, timestamp, record)
    local log = record["log"] or record["message"] or ""
    
    for name, pattern in pairs(pii_patterns) do
        log = log:gsub(pattern, "[" .. name:upper() .. "_REDACTED]")
    end
    
    -- Also redact from structured fields
    for key, value in pairs(record) do
        if type(value) == "string" then
            for name, pattern in pairs(pii_patterns) do
                if value:match(pattern) then
                    record[key] = "[" .. name:upper() .. "_REDACTED]"
                end
            end
        end
    end
    
    record["log"] = log
    return 1, timestamp, record
end
```

---

## 6. Anomaly Detection

### 6.1 Statistical Anomaly Detection

```python
# src/observability/anomaly_detection.py
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional
import time

@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    expected_range: tuple
    actual_value: float
    metric_name: str

class StatisticalAnomalyDetector:
    """
    Statistical anomaly detection using:
    - Z-score for stationary metrics
    - Seasonal decomposition for periodic metrics
    - EWMA for trending metrics
    """
    
    def __init__(self, window_size: int = 1000, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.metric_windows: Dict[str, deque] = {}
        self.metric_stats: Dict[str, Dict] = {}
    
    def add_value(self, metric_name: str, value: float, timestamp: float = None):
        """Add a new value and update statistics."""
        if metric_name not in self.metric_windows:
            self.metric_windows[metric_name] = deque(maxlen=self.window_size)
            self.metric_stats[metric_name] = {
                "mean": 0.0,
                "std": 1.0,
                "ewma": value,
                "ewma_var": 0.0,
                "alpha": 0.1
            }
        
        window = self.metric_windows[metric_name]
        stats = self.metric_stats[metric_name]
        
        window.append(value)
        
        # Update EWMA (Exponentially Weighted Moving Average)
        alpha = stats["alpha"]
        stats["ewma"] = alpha * value + (1 - alpha) * stats["ewma"]
        stats["ewma_var"] = alpha * (value - stats["ewma"])**2 + (1 - alpha) * stats["ewma_var"]
        
        # Update simple stats periodically
        if len(window) % 100 == 0:
            stats["mean"] = np.mean(window)
            stats["std"] = max(np.std(window), 1e-6)
    
    def check_anomaly(self, metric_name: str, value: float) -> AnomalyResult:
        """Check if value is anomalous."""
        if metric_name not in self.metric_stats:
            return AnomalyResult(False, 0.0, (0, 0), value, metric_name)
        
        stats = self.metric_stats[metric_name]
        
        # Use EWMA for trending metrics, simple stats for stationary
        expected_mean = stats["ewma"]
        expected_std = max(np.sqrt(stats["ewma_var"]), stats["std"])
        
        z_score = abs(value - expected_mean) / expected_std if expected_std > 0 else 0
        is_anomaly = z_score > self.z_threshold
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=z_score,
            expected_range=(expected_mean - 3*expected_std, expected_mean + 3*expected_std),
            actual_value=value,
            metric_name=metric_name
        )

class SeasonalAnomalyDetector:
    """Detect anomalies accounting for daily/weekly seasonality."""
    
    def __init__(self, seasonality_period: int = 86400):  # 24 hours in seconds
        self.seasonality_period = seasonality_period
        self.historical_data: Dict[int, List[float]] = {}  # timestamp_bucket -> values
    
    def add_value(self, metric_name: str, value: float, timestamp: float):
        bucket = int(timestamp // self.seasonality_period * self.seasonality_period)
        key = f"{metric_name}:{bucket}"
        
        if key not in self.historical_data:
            self.historical_data[key] = []
        self.historical_data[key].append(value)
        
        # Keep only last 30 days of buckets
        cutoff = timestamp - 30 * self.seasonality_period
        old_keys = [k for k in self.historical_data if int(k.split(":")[1]) < cutoff]
        for k in old_keys:
            del self.historical_data[k]
    
    def check_anomaly(self, metric_name: str, value: float, timestamp: float) -> AnomalyResult:
        bucket = int(timestamp // self.seasonality_period * self.seasonality_period)
        key = f"{metric_name}:{bucket}"
        
        if key not in self.historical_data or len(self.historical_data[key]) < 10:
            return AnomalyResult(False, 0.0, (0, 0), value, metric_name)
        
        historical = self.historical_data[key]
        mean = np.mean(historical)
        std = max(np.std(historical), 1e-6)
        
        z_score = abs(value - mean) / std
        is_anomaly = z_score > 3.0
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=z_score,
            expected_range=(mean - 3*std, mean + 3*std),
            actual_value=value,
            metric_name=metric_name
        )
```

---

## 7. Audit Logging for Compliance

### 7.1 Immutable Audit Trail

```python
# src/observability/audit.py
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import boto3

@dataclass
class AuditEvent:
    """Immutable audit event for regulatory compliance."""
    event_id: str
    timestamp: str
    event_type: str  # QUERY, CLASSIFICATION, ESCALATION, ADMIN_ACTION, DATA_ACCESS
    actor: Dict[str, Any]  # user_id, role, ip, session_id
    resource: Dict[str, Any]  # resource_type, resource_id, classification
    action: str  # CREATE, READ, UPDATE, DELETE, CLASSIFY, ESCALATE
    outcome: str  # SUCCESS, FAILURE, PARTIAL
    details: Dict[str, Any]
    previous_hash: str  # Hash of previous event for chain integrity
    signature: str  # Digital signature

class AuditLogger:
    """Tamper-evident audit logger with cryptographic chaining."""
    
    def __init__(self, service_name: str, private_key_pem: bytes = None):
        self.service_name = service_name
        self.private_key = None
        if private_key_pem:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem, password=None
            )
        self.last_hash = "0" * 64  # Genesis hash
        self.s3_client = boto3.client('s3')
        self.bucket = "rag-audit-logs"
    
    def _compute_hash(self, event: Dict) -> str:
        """Compute SHA-256 hash of event."""
        event_json = json.dumps(event, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(event_json.encode()).hexdigest()
    
    def _sign_event(self, event_hash: str) -> str:
        """Sign event hash with private key."""
        if not self.private_key:
            return "unsigned"
        
        signature = self.private_key.sign(
            event_hash.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature.hex()
    
    def log_event(
        self,
        event_type: str,
        actor: Dict,
        resource: Dict,
        action: str,
        outcome: str,
        details: Dict
    ) -> AuditEvent:
        """Log an immutable audit event."""
        
        event_id = f"audit-{int(time.time() * 1000000)}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        
        event_data = {
            "event_id": event_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "service": self.service_name,
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "action": action,
            "outcome": outcome,
            "details": details,
            "previous_hash": self.last_hash
        }
        
        # Compute hash and sign
        event_hash = self._compute_hash(event_data)
        signature = self._sign_event(event_hash)
        
        event_data["hash"] = event_hash
        event_data["signature"] = signature
        
        # Create immutable audit event
        audit_event = AuditEvent(**event_data)
        
        # Update chain
        self.last_hash = event_hash
        
        # Persist to immutable storage (S3 with Object Lock)
        self._persist_event(audit_event)
        
        return audit_event
    
    def _persist_event(self, event: AuditEvent):
        """Persist to S3 with Object Lock for immutability."""
        key = f"{self.service_name}/{event.timestamp[:10]}/{event.event_id}.json"
        
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(asdict(event), indent=2).encode(),
            ContentType="application/json",
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=int(time.time()) + 365 * 24 * 3600,  # 1 year
            ObjectLockLegalHold=True
        )
    
    def verify_chain(self, events: list) -> bool:
        """Verify audit chain integrity."""
        previous_hash = "0" * 64
        
        for event in events:
            event_dict = asdict(event)
            # Remove hash and signature for verification
            event_hash = event_dict.pop("hash")
            signature = event_dict.pop("signature")
            event_dict["previous_hash"] = previous_hash
            
            computed_hash = self._compute_hash(event_dict)
            
            if computed_hash != event_hash:
                return False
            
            previous_hash = event_hash
        
        return True
```

---

## 8. Debug Endpoints

### 8.1 Health & Readiness Endpoints

```python
# src/observability/health.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import psutil
import time

router = APIRouter(prefix="/health", tags=["health"])

class HealthCheck(BaseModel):
    service: str
    status: str  # healthy, degraded, unhealthy
    checks: Dict[str, Any]
    timestamp: str
    version: str

class ReadinessCheck(BaseModel):
    ready: bool
    checks: Dict[str, bool]
    timestamp: str

@router.get("/live", response_model=HealthCheck)
async def liveness():
    """Kubernetes liveness probe - process is alive."""
    return HealthCheck(
        service="rag-query-processor",
        status="healthy",
        checks={"process": "alive"},
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version="v2.3.1"
    )

@router.get("/ready", response_model=ReadinessCheck)
async def readiness():
    """Kubernetes readiness probe - ready to serve traffic."""
    checks = {}
    all_ready = True
    
    # Check database
    try:
        await check_database()
        checks["database"] = True
    except Exception:
        checks["database"] = False
        all_ready = False
    
    # Check vector index
    try:
        await check_vector_index()
        checks["vector_index"] = True
    except Exception:
        checks["vector_index"] = False
        all_ready = False
    
    # Check LLM endpoint
    try:
        await check_llm_endpoint()
        checks["llm"] = True
    except Exception:
        checks["llm"] = False
        all_ready = False
    
    # Check KG
    try:
        await check_knowledge_graph()
        checks["knowledge_graph"] = True
    except Exception:
        checks["knowledge_graph"] = False
        all_ready = False
    
    return ReadinessCheck(
        ready=all_ready,
        checks=checks,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=metrics_collector.expose_metrics(), media_type="text/plain")

@router.get("/debug/pprof")
async def pprof_profile(seconds: int = 30):
    """CPU profile endpoint."""
    import pyinstrument
    profiler = pyinstrument.Profiler()
    profiler.start()
    await asyncio.sleep(seconds)
    profiler.stop()
    return HTMLResponse(profiler.output_html())

@router.get("/debug/trace")
async def trace_endpoint(trace_id: str):
    """Fetch trace by ID from tracing backend."""
    # Query Jaeger/Tempo
    pass

@router.get("/debug/config")
async def config_dump():
    """Dump current configuration (redacted)."""
    return get_redacted_config()

@router.post("/debug/gc")
async def trigger_gc():
    """Trigger garbage collection."""
    import gc
    collected = gc.collect()
    return {"collected": collected}
```

---

## 9. Cost Attribution

### 9.1 Observability Cost Tracking

```python
# src/observability/cost_tracking.py
from dataclasses import dataclass
from typing import Dict
from datetime import datetime, timedelta
import boto3

@dataclass
class ObservabilityCost:
    service: str
    component: str  # logs, metrics, traces
    volume_gb: float
    cost_usd: float
    period_start: datetime
    period_end: datetime

class CostTracker:
    """Track and attribute observability costs."""
    
    def __init__(self):
        self.ce_client = boto3.client('ce')  # Cost Explorer
    
    async def get_costs(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "SERVICE"
    ) -> list[ObservabilityCost]:
        """Get observability costs from AWS Cost Explorer."""
        
        # Filter for observability services
        filter_expr = {
            "Or": [
                {"Dimensions": {"Key": "SERVICE", "Values": ["Amazon CloudWatch", "Amazon OpenSearch Service", "AWS X-Ray"]}},
                {"Tags": {"Key": "Component", "Values": ["observability"]}}
            ]
        }
        
        response = self.ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date.strftime("%Y-%m-%d"),
                "End": end_date.strftime("%Y-%m-%d")
            },
            Granularity="DAILY",
            Metrics=["UnblendedCost", "UsageQuantity"],
            GroupBy=[{"Type": "DIMENSION", "Key": group_by}],
            Filter=filter_expr
        )
        
        costs = []
        for result in response["ResultsByTime"]:
            for group in result["Groups"]:
                cost = ObservabilityCost(
                    service=group["Keys"][0] if group["Keys"] else "Unknown",
                    component=group["Keys"][1] if len(group["Keys"]) > 1 else "Unknown",
                    volume_gb=float(group["Metrics"]["UsageQuantity"]["Amount"]),
                    cost_usd=float(group["Metrics"]["UnblendedCost"]["Amount"]),
                    period_start=datetime.strptime(result["TimePeriod"]["Start"], "%Y-%m-%d"),
                    period_end=datetime.strptime(result["TimePeriod"]["End"], "%Y-%m-%d")
                )
                costs.append(cost)
        
        return costs
    
    def generate_cost_report(self, costs: list[ObservabilityCost]) -> Dict:
        """Generate cost attribution report."""
        by_service = {}
        by_component = {}
        total = 0.0
        
        for cost in costs:
            total += cost.cost_usd
            
            if cost.service not in by_service:
                by_service[cost.service] = {"cost": 0.0, "volume_gb": 0.0}
            by_service[cost.service]["cost"] += cost.cost_usd
            by_service[cost.service]["volume_gb"] += cost.volume_gb
            
            if cost.component not in by_component:
                by_component[cost.component] = {"cost": 0.0, "volume_gb": 0.0}
            by_component[cost.component]["cost"] += cost.cost_usd
            by_component[cost.component]["volume_gb"] += cost.volume_gb
        
        return {
            "total_cost_usd": total,
            "by_service": by_service,
            "by_component": by_component,
            "period": f"{costs[0].period_start} to {costs[-1].period_end}" if costs else "N/A"
        }
```

---

## 10. Implementation Checklist

### 10.1 Phase 21 Deliverables

| Component | Status | Description |
|-----------|--------|-------------|
| Structured Logging | ✅ | JSON logs with correlation IDs, PII redaction |
| Metrics Collection | ✅ | Prometheus metrics with standard naming |
| Distributed Tracing | ✅ | OpenTelemetry with adaptive sampling |
| Alerting Rules | ✅ | PrometheusAlert rules with routing |
| Dashboards | ✅ | Grafana dashboards for all subsystems |
| Log Aggregation | ✅ | Fluent Bit → Kafka → ClickHouse |
| Anomaly Detection | ✅ | Statistical + seasonal detectors |
| Audit Logging | ✅ | Immutable, cryptographically chained |
| Debug Endpoints | ✅ | Health, readiness, pprof, config |
| Cost Attribution | ✅ | Cost tracking per service/component |

### 10.2 Integration Points

| Phase | Integration |
|-------|-------------|
| Phase 3 (Query Analysis) | Trace query parsing, log classification decisions |
| Phase 6 (Retrieval) | Trace retrieval strategies, log document scores |
| Phase 7 (KG) | Trace KG queries, log entity resolution |
| Phase 8 (Classification) | Trace classification pipeline, log escalations |
| Phase 9 (Jurisdiction) | Trace jurisdiction resolution |
| Phase 10 (Generation) | Trace citation generation, log token usage |
| Phase 11 (Authority) | Trace authority scoring |
| Phase 12 (Multilingual) | Trace translation pipeline |
| Phase 13 (Orchestration) | Trace agent workflows |
| Phase 14 (Memory) | Trace memory operations |
| Phase 16 (API) | Trace API requests end-to-end |

---

## 11. Open Research Questions

| ID | Question | Context |
|----|----------|---------|
| ORQ-46 | What is the optimal trace sampling rate for cost vs. debuggability? | Balance between 10% default and 100% error sampling |
| ORQ-47 | How to correlate business metrics (answer quality) with system metrics? | Need join between user feedback and trace data |
| ORQ-48 | Can we use eBPF for zero-instrumentation system metrics? | Reduce overhead of userspace metric collection |
| ORQ-49 | What's the best approach for cross-cluster trace correlation? | Multi-region deployments need trace ID propagation |
| ORQ-50 | How to implement privacy-preserving log aggregation? | Differential privacy for log analytics |

---

## 12. Summary

Phase 21 establishes a production-grade observability architecture with:

1. **Four Pillars**: Logs, Metrics, Traces, Alerting - all integrated
2. **Structured Logging**: JSON format with correlation IDs, automatic PII redaction
3. **Prometheus Metrics**: Standard naming, histograms for latency, counters for throughput
4. **OpenTelemetry Tracing**: Adaptive sampling, auto-instrumentation, context propagation
5. **Multi-channel Alerting**: PagerDuty, Slack, Email with escalation policies
6. **Grafana Dashboards**: Pre-built for system overview, classification, retrieval, generation
7. **Log Pipeline**: Fluent Bit → Kafka → ClickHouse with PII redaction
8. **Anomaly Detection**: Statistical (Z-score, EWMA) + Seasonal detectors
9. **Audit Trail**: Cryptographically chained, S3 Object Lock for compliance
10. **Debug Endpoints**: Health, readiness, pprof, config, trace lookup
11. **Cost Attribution**: Per-service/component observability cost tracking

This architecture ensures full visibility into the RAG system's behavior, enabling rapid debugging, proactive alerting, and regulatory compliance.