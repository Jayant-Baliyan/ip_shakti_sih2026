# Phase 18: Research Experiment Framework

## 1. Overview

This document defines the research experiment framework for IP-SAKTI Sahayak, enabling systematic hypothesis-driven experimentation across all system components. The framework supports the complete experiment lifecycle: hypothesis → design → execution → analysis → decision.

### 1.1 Design Principles

1. **Hypothesis-First**: Every experiment starts with a falsifiable hypothesis
2. **Reproducibility**: Complete configuration snapshots, dataset versioning, environment capture
3. **Automation**: Experiment execution, metric collection, and reporting fully automated
4. **Traceability**: Git commit, data version, config hash linked to every result
5. **Collaboration**: Experiment registry with sharing, review, and comparison
6. **Decision-Oriented**: Clear go/no-go criteria for production deployment

### 1.2 Experiment Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
                    EXPERIMENT LIFECYCLE
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │  IDEATE     │────▶│   DESIGN    │────▶│  EXECUTE    │
    │             │     │             │     │             │
    │ • Hypothesis│     │ • Config    │     │ • Run       │
    │ • Literature│     │ • Dataset   │     │ • Monitor   │
    │ • Feasibility│    │ • Resources │     │ • Collect   │
    └─────────────┘     └─────────────┘     └──────┬──────┘
                                                   │
    ┌─────────────┐     ┌─────────────┐            │
    │  DECIDE     │◀────│  ANALYZE    │◀───────────┘
    │             │     │             │
    │ • Go/No-go  │     │ • Metrics   │
    │ • Document  │     │ • Stats     │
    │ • Deploy    │     │ • Compare   │
    └─────────────┘     └─────────────┘
```

---

## 2. Experiment Template

### 2.1 Experiment Definition

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

class ExperimentStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class ExperimentType(Enum):
    COMPONENT = "component"      # Single component (retriever, reranker)
    PIPELINE = "pipeline"        # End-to-end pipeline variant
    ABLATION = "ablation"        # Component removal study
    HYPERPARAMETER = "hyperparameter"  # Parameter sweep
    ARCHITECTURE = "architecture"      # Major architectural change
    BASELINE = "baseline"        # Reference configuration

@dataclass
class Experiment:
    experiment_id: str = field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    name: str = ""
    type: ExperimentType = ExperimentType.PIPELINE
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Hypothesis
    hypothesis: str = ""
    null_hypothesis: str = ""
    success_criteria: Dict[str, Any] = field(default_factory=dict)  # e.g., {"citation_precision": ">0.85"}
    expected_effect_size: float = 0.05  # Minimum practically significant effect
    
    # Design
    baseline_config: Dict[str, Any] = field(default_factory=dict)
    variant_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> config
    dataset_id: str = ""
    dataset_version: str = ""
    dataset_hash: str = ""
    
    # Resources
    estimated_cost_usd: float = 0
    estimated_duration_hours: float = 0
    required_gpu: bool = False
    max_concurrent_runs: int = 3
    
    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    description: str = ""
    literature_references: List[str] = field(default_factory=list)
    
    # Results (populated after execution)
    runs: List[str] = field(default_factory=list)  # run_ids
    conclusion: str = ""
    decision: str = ""  # adopt, reject, iterate
    deployed: bool = False
```

### 2.2 Experiment Configuration Schema

```yaml
# experiments/exp_retrieval_hybrid_vs_dense.yaml
experiment:
  experiment_id: "exp_retrieval_hybrid_vs_dense"
  name: "Hybrid (BM25 + Dense) vs Dense-only Retrieval"
  type: "pipeline"
  
  hypothesis: |
    Hybrid retrieval (BM25 + bge-m3 with RRF fusion) will achieve higher 
    citation precision and recall than dense-only retrieval for legal queries,
    particularly for exact section/case lookups (QC-01, QC-05).
  
  null_hypothesis: |
    There is no statistically significant difference in citation precision/recall
    between hybrid and dense-only retrieval.
  
  success_criteria:
    citation_precision: ">= 0.85"
    citation_recall: ">= 0.80"
    latency_p95: "<= 3000ms"
    statistical_significance: "p < 0.05"
    effect_size: ">= 0.05"
  
  baseline_config:
    name: "dense_only"
    retrieval:
      sparse:
        enabled: false
      dense:
        enabled: true
        model: "bge-m3"
        top_k: 100
      fusion:
        method: "dense_only"
      reranker:
        enabled: true
        model: "bge-reranker-v2-m3"
        top_k: 20
      selection:
        method: "mmr"
        final_k: 12
  
  variant_configs:
    hybrid_rrf:
      name: "hybrid_rrf"
      retrieval:
        sparse:
          enabled: true
          model: "bm25_legal"
          top_k: 100
        dense:
          enabled: true
          model: "bge-m3"
          top_k: 100
        fusion:
          method: "rrf"
          k: 60
          authority_weights:
            tier1: 1.0
            tier2: 0.8
            tier3: 0.6
            tier4: 0.4
        reranker:
          enabled: true
          model: "bge-reranker-v2-m3"
          top_k: 20
        selection:
          method: "mmr"
          final_k: 12
  
  dataset:
    id: "benchmark_v1"
    version: "1.0.0"
    split: "test"
  
  resources:
    estimated_cost_usd: 50
    estimated_duration_hours: 4
    required_gpu: true
    max_concurrent_runs: 3
```

---

## 3. Experiment Registry

### 3.1 Registry Service

```python
class ExperimentRegistry:
    """Central registry for experiment definitions and runs."""
    
    def __init__(self, storage: ExperimentStorage):
        self.storage = storage
    
    def create_experiment(self, exp: Experiment) -> Experiment:
        """Create new experiment definition."""
        exp.experiment_id = exp.experiment_id or f"exp_{uuid.uuid4().hex[:8]}"
        exp.created_at = datetime.utcnow()
        exp.updated_at = datetime.utcnow()
        return self.storage.save_experiment(exp)
    
    def submit_for_review(self, experiment_id: str) -> Experiment:
        """Submit experiment for peer review."""
        exp = self.storage.get_experiment(experiment_id)
        exp.status = ExperimentStatus.PENDING_REVIEW
        exp.updated_at = datetime.utcnow()
        return self.storage.save_experiment(exp)
    
    def approve_experiment(self, experiment_id: str, reviewer: str) -> Experiment:
        """Approve experiment for execution."""
        exp = self.storage.get_experiment(experiment_id)
        exp.status = ExperimentStatus.APPROVED
        exp.approved_by = reviewer
        exp.approved_at = datetime.utcnow()
        exp.updated_at = datetime.utcnow()
        return self.storage.save_experiment(exp)
    
    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        type: Optional[ExperimentType] = None,
        tags: Optional[List[str]] = None
    ) -> List[Experiment]:
        return self.storage.query_experiments(status, type, tags)
    
    def get_experiment(self, experiment_id: str) -> Experiment:
        return self.storage.get_experiment(experiment_id)
    
    def archive_experiment(self, experiment_id: str) -> Experiment:
        exp = self.storage.get_experiment(experiment_id)
        exp.status = ExperimentStatus.ARCHIVED
        exp.updated_at = datetime.utcnow()
        return self.storage.save_experiment(exp)
```

### 3.2 Experiment Storage Schema

```sql
CREATE TABLE experiments (
    experiment_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    hypothesis TEXT,
    null_hypothesis TEXT,
    success_criteria JSONB DEFAULT '{}',
    expected_effect_size FLOAT DEFAULT 0.05,
    baseline_config JSONB NOT NULL,
    variant_configs JSONB NOT NULL DEFAULT '{}',
    dataset_id VARCHAR(100),
    dataset_version VARCHAR(50),
    dataset_hash CHAR(64),
    estimated_cost_usd FLOAT DEFAULT 0,
    estimated_duration_hours FLOAT DEFAULT 0,
    required_gpu BOOLEAN DEFAULT FALSE,
    max_concurrent_runs INTEGER DEFAULT 3,
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    approved_by UUID REFERENCES users(user_id),
    approved_at TIMESTAMPTZ,
    tags TEXT[],
    description TEXT,
    literature_references TEXT[],
    conclusion TEXT,
    decision VARCHAR(20),  -- adopt, reject, iterate
    deployed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_type ON experiments(type);
CREATE INDEX idx_experiments_created ON experiments(created_at DESC);
CREATE INDEX idx_experiments_tags ON experiments USING GIN (tags);
```

---

## 4. Experiment Execution Engine

### 4.1 Execution Manager

```python
class ExperimentExecutor:
    """Executes experiments with full reproducibility."""
    
    def __init__(
        self,
        registry: ExperimentRegistry,
        evaluation_engine: EvaluationEngine,
        resource_manager: ResourceManager
    ):
        self.registry = registry
        self.evaluation_engine = evaluation_engine
        self.resource_manager = resource_manager
    
    async def execute_experiment(
        self,
        experiment_id: str,
        variant_names: Optional[List[str]] = None,
        sample_size: Optional[int] = None
    ) -> List[ExperimentRun]:
        """Execute all variants of an experiment."""
        
        experiment = self.registry.get_experiment(experiment_id)
        
        if experiment.status not in [ExperimentStatus.APPROVED, ExperimentStatus.RUNNING]:
            raise ValueError(f"Experiment not approved: {experiment.status}")
        
        # Update status
        experiment.status = ExperimentStatus.RUNNING
        experiment.updated_at = datetime.utcnow()
        self.registry.storage.save_experiment(experiment)
        
        # Determine variants to run
        variants = variant_names or list(experiment.variant_configs.keys())
        if "baseline" not in variants:
            variants = ["baseline"] + variants
        
        runs = []
        for variant_name in variants:
            run = await self._execute_variant(experiment, variant_name, sample_size)
            runs.append(run)
            experiment.runs.append(run.run_id)
            self.registry.storage.save_experiment(experiment)
        
        # Finalize
        experiment.status = ExperimentStatus.COMPLETED
        experiment.updated_at = datetime.utcnow()
        self.registry.storage.save_experiment(experiment)
        
        return runs
    
    async def _execute_variant(
        self,
        experiment: Experiment,
        variant_name: str,
        sample_size: Optional[int]
    ) -> ExperimentRun:
        """Execute a single variant."""
        
        # Get config
        if variant_name == "baseline":
            config = experiment.baseline_config
        else:
            config = experiment.variant_configs.get(variant_name)
            if not config:
                raise ValueError(f"Variant not found: {variant_name}")
        
        # Create run record
        run = ExperimentRun(
            experiment_id=experiment.experiment_id,
            variant_name=variant_name,
            config_snapshot=config,
            dataset_version=experiment.dataset_version,
            dataset_hash=experiment.dataset_hash,
            status="running",
            git_commit=self._get_git_commit(),
            environment=self._get_environment()
        )
        
        # Save initial run
        run = await self.evaluation_engine.results_store.save_run(run)
        
        try:
            # Load dataset
            dataset = await self._load_dataset(experiment.dataset_id, experiment.dataset_version)
            
            # Execute evaluation
            result_run = await self.evaluation_engine.run_evaluation(
                dataset=dataset,
                split="test",
                config=PipelineConfig(**config),
                sample_size=sample_size
            )
            
            # Update run with results
            run.status = "completed"
            run.metrics = result_run.metrics
            run.per_case_metrics = result_run.per_case_metrics
            run.aggregate_metrics = result_run.aggregate_metrics
            run.total_latency_ms = result_run.total_latency_ms
            run.avg_latency_ms = result_run.avg_latency_ms
            run.p50_latency_ms = result_run.p50_latency_ms
            run.p95_latency_ms = result_run.p95_latency_ms
            run.p99_latency_ms = result_run.p99_latency_ms
            run.total_tokens = result_run.total_tokens
            run.total_cost_usd = result_run.total_cost_usd
            run.failure_cases = result_run.failure_cases
            run.error_summary = result_run.error_summary
            run.completed_at = datetime.utcnow()
            
        except Exception as e:
            run.status = "failed"
            run.error_summary = {"error": str(e), "traceback": traceback.format_exc()}
            run.completed_at = datetime.utcnow()
            logger.error(f"Experiment run failed: {e}")
        
        await self.evaluation_engine.results_store.save_run(run)
        return run
    
    def _get_git_commit(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip()
        except:
            return "unknown"
    
    def _get_environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development")
```

### 4.2 Resource Management

```python
class ResourceManager:
    """Manages compute resources for experiments."""
    
    def __init__(self, config: ResourceConfig):
        self.config = config
        self.active_runs: Dict[str, RunResources] = {}
    
    async def allocate(self, run_id: str, requirements: ResourceRequirements) -> Allocation:
        """Allocate resources for a run."""
        
        # Check quota
        if not self._check_quota(requirements):
            raise ResourceExhaustedError("Insufficient quota")
        
        # Reserve resources
        allocation = Allocation(
            run_id=run_id,
            gpu_type=requirements.gpu_type,
            gpu_count=requirements.gpu_count,
            cpu_cores=requirements.cpu_cores,
            memory_gb=requirements.memory_gb,
            allocated_at=datetime.utcnow()
        )
        
        self.active_runs[run_id] = RunResources(
            allocation=allocation,
            requirements=requirements
        )
        
        return allocation
    
    async def deallocate(self, run_id: str):
        """Release resources after run completion."""
        if run_id in self.active_runs:
            del self.active_runs[run_id]
    
    def get_utilization(self) -> ResourceUtilization:
        return ResourceUtilization(
            active_runs=len(self.active_runs),
            gpu_utilization=self._compute_gpu_utilization(),
            cpu_utilization=self._compute_cpu_utilization(),
            memory_utilization=self._compute_memory_utilization()
        )
```

---

## 5. Hypothesis Management

### 5.1 Hypothesis Template

```python
@dataclass
class Hypothesis:
    hypothesis_id: str = field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    statement: str = ""
    null_hypothesis: str = ""
    independent_variables: List[str] = field(default_factory=list)
    dependent_variables: List[str] = field(default_factory=list)
    expected_direction: Dict[str, str] = field(default_factory=dict)  # var -> increase/decrease
    minimum_effect_size: Dict[str, float] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    related_hypotheses: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    def to_experiment(self) -> Experiment:
        """Convert hypothesis to experiment design."""
        return Experiment(
            name=f"Test: {self.statement[:80]}",
            hypothesis=self.statement,
            null_hypothesis=self.null_hypothesis,
            success_criteria={
                var: f"{dir} {size}"
                for var, (dir, size) in zip(
                    self.dependent_variables,
                    zip(
                        [self.expected_direction.get(v, "increase") for v in self.dependent_variables],
                        [self.minimum_effect_size.get(v, 0.05) for v in self.dependent_variables]
                    )
                )
            }
        )
```

### 5.2 Hypothesis Tracking

```python
class HypothesisTracker:
    """Tracks hypotheses from ideation to decision."""
    
    def __init__(self, storage: HypothesisStorage):
        self.storage = storage
    
    def create_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        return self.storage.save(hypothesis)
    
    def link_experiment(self, hypothesis_id: str, experiment_id: str):
        """Link experiment to hypothesis."""
        hyp = self.storage.get(hypothesis_id)
        hyp.related_experiments = hyp.related_experiments or []
        hyp.related_experiments.append(experiment_id)
        self.storage.save(hyp)
    
    def get_hypothesis_status(self, hypothesis_id: str) -> HypothesisStatus:
        """Get aggregated status of hypothesis based on experiments."""
        hyp = self.storage.get(hypothesis_id)
        experiments = [
            self.registry.get_experiment(eid) 
            for eid in hyp.related_experiments
        ]
        
        if not experiments:
            return HypothesisStatus.UNTESTED
        
        decisions = [e.decision for e in experiments if e.decision]
        
        if "adopt" in decisions:
            return HypothesisStatus.SUPPORTED
        elif "reject" in decisions:
            return HypothesisStatus.REJECTED
        elif "iterate" in decisions:
            return HypothesisStatus.NEEDS_ITERATION
        else:
            return HypothesisStatus.IN_PROGRESS
```

---

## 6. Configuration Management

### 6.1 Configuration Versioning

```python
class ConfigManager:
    """Manages pipeline configurations with versioning."""
    
    def __init__(self, storage: ConfigStorage):
        self.storage = storage
    
    def save_config(self, config: PipelineConfig, name: str, version: str) -> ConfigVersion:
        """Save configuration with semantic versioning."""
        
        config_hash = self._compute_hash(config)
        
        # Check if identical config exists
        existing = self.storage.get_by_hash(config_hash)
        if existing:
            return existing
        
        version_obj = ConfigVersion(
            config_id=f"cfg_{uuid.uuid4().hex[:8]}",
            name=name,
            version=version,
            config=config.to_dict(),
            hash=config_hash,
            created_at=datetime.utcnow(),
            created_by=get_current_user(),
            parent_config_id=self._get_latest_version(name)
        )
        
        return self.storage.save(version_obj)
    
    def get_config(self, name: str, version: str = "latest") -> PipelineConfig:
        """Get configuration by name and version."""
        version_obj = self.storage.get(name, version)
        return PipelineConfig(**version_obj.config)
    
    def diff_configs(self, config_a: str, config_b: str) -> ConfigDiff:
        """Compare two configurations."""
        a = self.get_config(*config_a.split(":"))
        b = self.get_config(*config_b.split(":"))
        return self._compute_diff(a, b)
```

### 6.2 Configuration Schema (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any

class SparseRetrievalConfig(BaseModel):
    enabled: bool = True
    model: str = "bm25_legal"
    top_k: int = 100
    tokenizer: str = "legal"
    k1: float = 1.2
    b: float = 0.75

class DenseRetrievalConfig(BaseModel):
    enabled: bool = True
    model: str = "bge-m3"
    top_k: int = 100
    ef_search: int = 100

class FusionConfig(BaseModel):
    method: str = "rrf"  # rrf, weighted, learned
    k: int = 60
    authority_weights: Dict[str, float] = Field(default_factory=lambda: {
        "tier1": 1.0, "tier2": 0.8, "tier3": 0.6, "tier4": 0.4
    })

class RerankerConfig(BaseModel):
    enabled: bool = True
    model: str = "bge-reranker-v2-m3"
    top_k: int = 20
    batch_size: int = 32

class SelectionConfig(BaseModel):
    method: str = "mmr"  # mmr, top_k, diversity
    lambda_param: float = 0.7
    final_k: int = 12
    dedup_threshold: float = 0.95

class RetrievalConfig(BaseModel):
    sparse: SparseRetrievalConfig = Field(default_factory=SparseRetrievalConfig)
    dense: DenseRetrievalConfig = Field(default_factory=DenseRetrievalConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    selection: SelectionConfig = Field(default_factory=SelectionConfig)

class GenerationConfig(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4096
    citation_style: str = "detailed"
    system_prompt_version: str = "v1"

class VerificationConfig(BaseModel):
    citation_check: bool = True
    groundedness_check: bool = True
    entailment_check: bool = True
    jurisdiction_check: bool = True
    authority_check: bool = True
    hallucination_check: bool = True

class PipelineConfig(BaseModel):
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## 7. Dataset Versioning

### 7.1 Dataset Version Control

```python
class DatasetVersionManager:
    """Manages dataset versions with DVC-like semantics."""
    
    def __init__(self, storage: DatasetStorage):
        self.storage = storage
    
    def create_version(
        self,
        dataset_id: str,
        source_path: str,
        version: str,
        description: str,
        created_by: str
    ) -> DatasetVersion:
        """Create new dataset version."""
        
        # Compute hash of dataset
        dataset_hash = self._compute_dataset_hash(source_path)
        
        # Check for duplicates
        existing = self.storage.get_by_hash(dataset_hash)
        if existing:
            raise ValueError(f"Dataset with hash {dataset_hash} already exists as {existing.version}")
        
        # Load and validate
        dataset = self._load_dataset(source_path)
        validation = self._validate_dataset(dataset)
        
        version_obj = DatasetVersion(
            dataset_id=dataset_id,
            version=version,
            hash=dataset_hash,
            description=description,
            query_count=len(dataset.queries),
            category_distribution=self._category_distribution(dataset),
            language_distribution=self._language_distribution(dataset),
            jurisdiction_distribution=self._jurisdiction_distribution(dataset),
            validation=validation,
            source_path=source_path,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        
        # Store dataset files
        self.storage.store_dataset_files(dataset_id, version, source_path)
        self.storage.save_version(version_obj)
        
        return version_obj
    
    def get_version(self, dataset_id: str, version: str) -> DatasetVersion:
        return self.storage.get_version(dataset_id, version)
    
    def list_versions(self, dataset_id: str) -> List[DatasetVersion]:
        return self.storage.list_versions(dataset_id)
    
    def _compute_dataset_hash(self, path: str) -> str:
        """Compute deterministic hash of dataset."""
        hasher = hashlib.sha256()
        for root, dirs, files in sorted(os.walk(path)):
            for file in sorted(files):
                filepath = os.path.join(root, file)
                with open(filepath, 'rb') as f:
                    hasher.update(f.read())
        return hasher.hexdigest()
```

---

## 8. Metrics Collection & Storage

### 8.1 Metrics Collector

```python
class MetricsCollector:
    """Collects and aggregates metrics during experiment runs."""
    
    def __init__(self, storage: MetricsStorage):
        self.storage = storage
        self.buffers: Dict[str, List[MetricPoint]] = defaultdict(list)
    
    def record(self, run_id: str, metric: MetricPoint):
        """Record a single metric point."""
        self.buffers[run_id].append(metric)
    
    def flush(self, run_id: str):
        """Flush buffered metrics to storage."""
        if run_id in self.buffers:
            self.storage.save_metrics(run_id, self.buffers[run_id])
            del self.buffers[run_id]
    
    def get_run_metrics(self, run_id: str) -> List[MetricPoint]:
        return self.storage.get_metrics(run_id)
    
    def get_aggregated(
        self,
        experiment_id: str,
        metric_names: List[str],
        aggregation: str = "mean"  # mean, median, p95, min, max
    ) -> Dict[str, float]:
        return self.storage.get_aggregated(experiment_id, metric_names, aggregation)

@dataclass
class MetricPoint:
    timestamp: datetime
    run_id: str
    variant_name: str
    query_id: str
    metric_name: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 8.2 Real-time Metrics Streaming

```python
class MetricsStreamer:
    """Streams metrics to monitoring systems (Prometheus, DataDog)."""
    
    def __init__(self, exporters: List[MetricsExporter]):
        self.exporters = exporters
    
    async def stream_run_metrics(self, run_id: str):
        """Stream metrics for a running experiment."""
        async for metric in self._tail_metrics(run_id):
            for exporter in self.exporters:
                await exporter.export(metric)
    
    def _tail_metrics(self, run_id: str) -> AsyncGenerator[MetricPoint, None]:
        """Tail metrics as they're written."""
        last_position = 0
        while True:
            metrics = self.storage.get_metrics_since(run_id, last_position)
            for m in metrics:
                yield m
                last_position = m.timestamp
            await asyncio.sleep(1)
```

---

## 9. Experiment Comparison & Analysis

### 9.1 Comparison Engine

```python
class ExperimentComparator:
    """Compares experiment runs with statistical rigor."""
    
    def __init__(self, results_store: EvaluationResultsStore):
        self.results_store = results_store
        self.analyzer = StatisticalAnalyzer()
    
    def compare_variants(
        self,
        experiment_id: str,
        baseline_variant: str = "baseline",
        metric_names: Optional[List[str]] = None
    ) -> ComparisonReport:
        """Compare all variants against baseline."""
        
        experiment = self.registry.get_experiment(experiment_id)
        runs = {r.variant_name: r for r in experiment.runs}
        
        baseline_run = runs.get(baseline_variant)
        if not baseline_run:
            raise ValueError(f"Baseline variant not found: {baseline_variant}")
        
        variant_runs = {k: v for k, v in runs.items() if k != baseline_variant}
        
        comparisons = {}
        for variant_name, variant_run in variant_runs.items():
            comparison = self.analyzer.compare_runs(
                baseline=baseline_run,
                variant=variant_run,
                metrics=metric_names or list(baseline_run.metrics.keys())
            )
            comparisons[variant_name] = comparison
        
        return ComparisonReport(
            experiment_id=experiment_id,
            baseline_variant=baseline_variant,
            variant_comparisons=comparisons,
            summary=self._generate_summary(comparisons)
        )
    
    def _generate_summary(self, comparisons: Dict) -> ComparisonSummary:
        """Generate human-readable summary."""
        significant_improvements = []
        significant_regressions = []
        
        for variant, comp in comparisons.items():
            for metric, result in comp.metric_comparisons.items():
                if result.significant:
                    if result.direction == "improved":
                        significant_improvements.append(f"{variant}: {metric} ({result.effect_size:.3f})")
                    else:
                        significant_regressions.append(f"{variant}: {metric} ({result.effect_size:.3f})")
        
        return ComparisonSummary(
            n_variants=len(comparisons),
            n_significant_improvements=len(significant_improvements),
            n_significant_regressions=len(significant_regressions),
            improvements=significant_improvements,
            regressions=significant_regressions
        )
```

### 9.2 Visualization Data Export

```python
class ExperimentVisualizer:
    """Exports data for visualization (Grafana, notebooks, reports)."""
    
    def export_for_grafana(self, experiment_id: str) -> GrafanaDashboard:
        """Generate Grafana dashboard JSON."""
        experiment = self.registry.get_experiment(experiment_id)
        runs = [self.results_store.get_run(rid) for rid in experiment.runs]
        
        return GrafanaDashboard(
            title=f"Experiment: {experiment.name}",
            panels=[
                self._create_metric_panel(runs, "citation_precision"),
                self._create_metric_panel(runs, "citation_recall"),
                self._create_latency_panel(runs),
                self._create_cost_panel(runs),
                self._create_breakdown_panel(runs, "category"),
                self._create_breakdown_panel(runs, "language"),
                self._create_breakdown_panel(runs, "jurisdiction"),
            ]
        )
    
    def export_for_notebook(self, experiment_id: str) -> Dict[str, pd.DataFrame]:
        """Export DataFrames for Jupyter analysis."""
        experiment = self.registry.get_experiment(experiment_id)
        runs = [self.results_store.get_run(rid) for rid in experiment.runs]
        
        return {
            "summary": self._summary_df(runs),
            "per_query": self._per_query_df(runs),
            "latency": self._latency_df(runs),
            "cost": self._cost_df(runs),
            "failures": self._failures_df(runs)
        }
```

---

## 10. Automated Experiment Generation

### 10.1 Hyperparameter Sweep Generator

```python
class SweepGenerator:
    """Generates experiment configurations for hyperparameter sweeps."""
    
    def generate_sweep(
        self,
        base_config: PipelineConfig,
        param_grid: Dict[str, List[Any]],
        experiment_name: str,
        hypothesis: str
    ) -> List[Experiment]:
        """Generate experiments for all parameter combinations."""
        
        # Generate all combinations
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        
        experiments = []
        for i, combo in enumerate(combinations):
            variant_config = base_config.model_copy(deep=True)
            for key, value in zip(keys, combo):
                self._set_nested_attr(variant_config, key, value)
            
            exp = Experiment(
                name=f"{experiment_name}_trial_{i}",
                type=ExperimentType.HYPERPARAMETER,
                hypothesis=hypothesis,
                baseline_config=base_config.to_dict(),
                variant_configs={f"trial_{i}": variant_config.to_dict()},
                dataset_id="benchmark_v1",
                dataset_version="1.0.0",
                tags=["sweep", experiment_name],
                description=f"Trial {i}: {dict(zip(keys, combo))}"
            )
            experiments.append(exp)
        
        return experiments
    
    def _set_nested_attr(self, obj: BaseModel, path: str, value: Any):
        """Set nested attribute by dot path."""
        parts = path.split(".")
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
```

### 10.2 Ablation Study Generator

```python
class AblationGenerator:
    """Generates ablation study experiments."""
    
    ABLATION_COMPONENTS = [
        "sparse_retrieval",
        "dense_retrieval",
        "reranker",
        "mmr_selection",
        "authority_weighting",
        "jurisdiction_filter",
        "query_rewriting",
        "query_decomposition",
        "citation_verification",
        "groundedness_check",
        "entailment_check",
        "hallucination_check"
    ]
    
    def generate_ablation(
        self,
        full_config: PipelineConfig,
        experiment_name: str,
        hypothesis: str
    ) -> List[Experiment]:
        """Generate experiments removing each component."""
        
        experiments = []
        
        for component in self.ABLATION_COMPONENTS:
            ablated_config = self._remove_component(full_config, component)
            
            exp = Experiment(
                name=f"{experiment_name}_ablate_{component}",
                type=ExperimentType.ABLATION,
                hypothesis=f"{hypothesis} - Testing necessity of {component}",
                baseline_config=full_config.to_dict(),
                variant_configs={f"without_{component}": ablated_config.to_dict()},
                dataset_id="benchmark_v1",
                dataset_version="1.0.0",
                tags=["ablation", experiment_name, component],
                description=f"Ablation: {component} removed"
            )
            experiments.append(exp)
        
        return experiments
    
    def _remove_component(self, config: PipelineConfig, component: str) -> PipelineConfig:
        """Remove a component from config."""
        ablated = config.model_copy(deep=True)
        
        if component == "sparse_retrieval":
            ablated.retrieval.sparse.enabled = False
        elif component == "dense_retrieval":
            ablated.retrieval.dense.enabled = False
        elif component == "reranker":
            ablated.retrieval.reranker.enabled = False
        elif component == "mmr_selection":
            ablated.retrieval.selection.method = "top_k"
        elif component == "authority_weighting":
            ablated.retrieval.fusion.authority_weights = {"tier1": 1.0, "tier2": 1.0, "tier3": 1.0, "tier4": 1.0}
        # ... etc
        
        return ablated
```

---

## 11. Experiment Reporting

### 11.1 Report Template

```markdown
# Experiment Report: {{experiment.name}}

## Executive Summary
- **Experiment ID**: {{experiment.experiment_id}}
- **Status**: {{experiment.status}}
- **Decision**: {{experiment.decision}}
- **Conclusion**: {{experiment.conclusion}}

## Hypothesis
- **Statement**: {{experiment.hypothesis}}
- **Null Hypothesis**: {{experiment.null_hypothesis}}
- **Success Criteria**: {{experiment.success_criteria}}

## Design
- **Baseline**: {{experiment.baseline_config.name}}
- **Variants**: {{experiment.variant_configs.keys()}}
- **Dataset**: {{experiment.dataset_id}} v{{experiment.dataset_version}}
- **Estimated Cost**: ${{experiment.estimated_cost_usd}}
- **Estimated Duration**: {{experiment.estimated_duration_hours}}h

## Results Summary
| Variant | Citation Precision | Citation Recall | Latency (p95) | Cost | Status |
|---------|-------------------|-----------------|---------------|------|--------|
{% for variant, run in results %}
| {{variant}} | {{run.metrics.citation_precision}} | {{run.metrics.citation_recall}} | {{run.p95_latency_ms}}ms | ${{run.total_cost_usd}} | {{run.status}} |
{% endfor %}

## Statistical Analysis
{% for variant, comparison in statistical_comparisons.items() %}
### {{variant}} vs Baseline
{% for metric, result in comparison.metric_comparisons.items() %}
- **{{metric}}**: {{result.direction}} (p={{result.p_value:.4f}}, d={{result.effect_size:.3f}}) {% if result.significant %}✅{% else %}❌{% endif %}
{% endfor %}
{% endfor %}

## Failure Analysis
- **Total Failures**: {{failure_analysis.total_failures}}
- **Top Failure Types**: {{failure_analysis.by_type.top(5)}}
- **Key Root Causes**: {{failure_analysis.top_root_causes}}
- **Action Items**: {{failure_analysis.action_items}}

## Cost Analysis
- **Total Cost**: ${{total_cost}}
- **Cost per Query**: ${{cost_per_query}}
- **Cost Breakdown**: {{cost_breakdown}}

## Recommendations
{{experiment.conclusion}}

## Reproducibility
- **Git Commit**: {{git_commit}}
- **Dataset Hash**: {{dataset_hash}}
- **Config Hashes**: {{config_hashes}}
- **Environment**: {{environment}}
```

### 11.2 Report Generator

```python
class ReportGenerator:
    def generate_report(self, experiment_id: str) -> ExperimentReport:
        experiment = self.registry.get_experiment(experiment_id)
        runs = [self.results_store.get_run(rid) for rid in experiment.runs]
        
        # Statistical comparisons
        comparisons = self.comparator.compare_variants(experiment_id)
        
        # Failure analysis
        failure_analysis = self.failure_analyzer.analyze_experiment(runs)
        
        # Cost analysis
        cost_analysis = self.cost_analyzer.analyze(runs)
        
        return ExperimentReport(
            experiment=experiment,
            runs=runs,
            comparisons=comparisons,
            failure_analysis=failure_analysis,
            cost_analysis=cost_analysis,
            generated_at=datetime.utcnow()
        )
    
    def render_markdown(self, report: ExperimentReport) -> str:
        """Render report as Markdown."""
        template = self._load_template("experiment_report.md")
        return template.render(**report.to_dict())
    
    def render_html(self, report: ExperimentReport) -> str:
        """Render report as HTML."""
        markdown = self.render_markdown(report)
        return markdown_to_html(markdown)
    
    def render_pdf(self, report: ExperimentReport) -> bytes:
        """Render report as PDF."""
        html = self.render_html(report)
        return html_to_pdf(html)
```

---

## 12. Integration with CI/CD

### 12.1 Automated Experiment Triggers

```yaml
# .github/workflows/experiments.yml
name: Research Experiments

on:
  workflow_dispatch:
    inputs:
      experiment_id:
        description: 'Experiment ID to run'
        required: true
      variants:
        description: 'Comma-separated variant names (default: all)'
        required: false

  schedule:
    - cron: '0 3 * * 0'  # Weekly on Sunday

jobs:
  run-experiment:
    runs-on: [self-hosted, gpu]
    timeout-minutes: 240
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup environment
        run: |
          pip install -e .[experiments]
          
      - name: Run experiment
        id: experiment
        run: |
          python -m experiments.run \
            --experiment-id ${{ github.event.inputs.experiment_id }} \
            --variants ${{ github.event.inputs.variants }} \
            --output results.json
          
      - name: Check regressions
        run: |
          python -m experiments.check_regression \
            --experiment-id ${{ github.event.inputs.experiment_id }} \
            --baseline main
          
      - name: Generate report
        if: always()
        run: |
          python -m experiments.report \
            --experiment-id ${{ github.event.inputs.experiment_id }} \
            --format html \
            --output report.html
          
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: experiment-report
          path: report.html
          
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('report.html', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Experiment Results\n${report}`
            })
```

---

## 13. Experiment Catalog (Pre-defined)

### 13.1 Core Experiments

| Experiment ID | Name | Type | Hypothesis | Status |
|---------------|------|------|------------|--------|
| exp_001 | Dense vs Hybrid Retrieval | Pipeline | Hybrid > Dense for legal exact-match | Planned |
| exp_002 | Reranker Impact | Ablation | Cross-encoder improves precision@10 by >10% | Planned |
| exp_003 | Authority Weighting | Component | Authority-weighted RRF > Uniform RRF | Planned |
| exp_004 | Query Decomposition | Pipeline | Multi-hop queries need decomposition | Planned |
| exp_005 | Graph Retrieval Value | Pipeline | Graph helps temporal/treaty queries | Planned |
| exp_006 | LLM vs Cross-encoder Reranker | Component | LLM reranker better but slower | Planned |
| exp_007 | Multilingual Strategy | Pipeline | Translate-query > Multilingual embeddings | Planned |
| exp_008 | Chunk Size Optimization | Hyperparameter | 1024 tokens optimal for legal sections | Planned |
| exp_009 | MMR Lambda Tuning | Hyperparameter | λ=0.7 optimal for legal diversity | Planned |
| exp_010 | Citation Verification Impact | Ablation | Verification layer reduces hallucination >50% | Planned |

### 13.2 Experiment Prioritization Matrix

| Experiment | Impact | Effort | Priority | Dependencies |
|------------|--------|--------|----------|--------------|
| exp_001 | High | Medium | P0 | Retrieval engine ready |
| exp_002 | High | Low | P0 | Reranker integrated |
| exp_003 | High | Low | P0 | Authority tiers defined |
| exp_004 | Medium | High | P1 | Query decomposition done |
| exp_005 | Medium | High | P2 | Knowledge graph ready |
| exp_006 | Medium | Medium | P1 | LLM reranker available |
| exp_007 | High | Medium | P1 | Multilingual embeddings |
| exp_008 | Low | Low | P2 | Chunking implemented |
| exp_009 | Low | Low | P2 | MMR implemented |
| exp_010 | High | Medium | P0 | Verification layer ready |

---

## 14. Open Research Questions

| ID | Question | Priority |
|----|----------|----------|
| ORQ-78 | Optimal experiment sample size for legal domain statistical power? | High |
| ORQ-79 | How to handle non-determinism in LLM-based components? | High |
| ORQ-80 | Experiment randomization strategy for A/B testing in production? | Medium |
| ORQ-81 | Meta-experimentation: learning which experiments to run? | Low |
| ORQ-82 | Transfer learning from experiment results across domains? | Low |
| ORQ-83 | Experiment result reproducibility across hardware/platforms? | Medium |

---

## 15. Implementation Checklist

- [ ] Experiment definition schema (YAML/JSON)
- [ ] Experiment registry service (CRUD, review workflow)
- [ ] Experiment executor (parallel variant execution)
- [ ] Resource manager (GPU/CPU quota, scheduling)
- [ ] Hypothesis tracker (ideation → decision)
- [ ] Configuration manager (versioning, diffing)
- [ ] Dataset version manager (DVC-like)
- [ ] Metrics collector (buffered, streaming)
- [ ] Statistical analyzer (Wilcoxon, bootstrap, effect sizes)
- [ ] Regression detector (thresholds, alerts)
- [ ] Experiment comparator (variant vs baseline)
- [ ] Visualization exporter (Grafana, notebooks)
- [ ] Report generator (Markdown, HTML, PDF)
- [ ] Sweep generator (hyperparameter, ablation)
- [ ] CI/CD integration (GitHub Actions)
- [ ] Experiment catalog (pre-defined core experiments)
- [ ] Dashboard for experiment tracking
- [ ] Notification system (Slack, email on completion)