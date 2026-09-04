"""
IP-SAKTI Research Experiment Framework
Phase 12: Implements the research experiment framework for systematic experimentation.
This must exist before Phase 13 (Knowledge Graph) which requires running experiments.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import (
    DocumentType,
    EvaluationMetric,
    EvaluationResult,
    Jurisdiction,
    QueryIntent,
)
from ip_sakti.eval.evaluation import (
    EvaluationHarness,
    EvaluationConfig,
    EvaluationType,
    TestCase,
    EvaluationRun,
)

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """Experiment status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExperimentType(str, Enum):
    """Types of experiments."""
    AB_TEST = "ab_test"
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    COMPARATIVE = "comparative"
    ABLATION = "ablation"
    SCALING = "scaling"


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    experiment_type: ExperimentType = ExperimentType.COMPARATIVE
    name: str = ""
    description: str = ""
    hypothesis: str = ""
    success_criteria: Dict[str, float] = field(default_factory=dict)
    max_runs: int = 10
    parallel_runs: int = 3
    timeout_minutes: int = 60
    random_seed: int = 42


@dataclass
class ExperimentParameter:
    """Parameter for experiment search space."""
    name: str
    param_type: str  # "categorical", "float", "int", "bool"
    values: List[Any] = field(default_factory=list)  # For categorical
    min_value: Optional[float] = None  # For numeric
    max_value: Optional[float] = None
    log_scale: bool = False


@dataclass
class ExperimentCondition:
    """A single experimental condition (parameter combination)."""
    id: str
    parameters: Dict[str, Any]
    label: str = ""


@dataclass
class ExperimentRun:
    """A single run of an experiment condition."""
    id: str
    experiment_id: str
    condition_id: str
    evaluation_run_id: Optional[str] = None
    status: ExperimentStatus = ExperimentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class Experiment:
    """An experiment with multiple conditions and runs."""
    id: str
    config: ExperimentConfig
    search_space: List[ExperimentParameter] = field(default_factory=list)
    conditions: List[ExperimentCondition] = field(default_factory=list)
    runs: List[ExperimentRun] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    best_condition_id: Optional[str] = None
    best_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExperimentRunner(ABC):
    """Abstract base for experiment runners."""
    
    @abstractmethod
    async def run(
        self,
        experiment: Experiment,
        harness: EvaluationHarness,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run the experiment."""
        pass


class ComparativeExperimentRunner(ExperimentRunner):
    """Run comparative experiments (A/B test style)."""
    
    async def run(
        self,
        experiment: Experiment,
        harness: EvaluationHarness,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run comparative experiment comparing conditions."""
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        
        # Create runs for each condition
        semaphore = asyncio.Semaphore(experiment.config.parallel_runs)
        
        async def run_condition(condition: ExperimentCondition) -> ExperimentRun:
            async with semaphore:
                run = ExperimentRun(
                    id=str(uuid.uuid4()),
                    experiment_id=experiment.id,
                    condition_id=condition.id,
                    status=ExperimentStatus.RUNNING,
                    started_at=datetime.utcnow(),
                )
                experiment.runs.append(run)
                
                try:
                    # Create system with condition parameters
                    system = system_factory(condition.parameters)
                    
                    # Run evaluation
                    eval_run = await harness.run_evaluation(
                        name=f"{experiment.config.name} - {condition.label}",
                        evaluation_type=EvaluationType.END_TO_END,
                        test_cases=experiment.test_cases,
                        rag_pipeline=system.get('rag_pipeline'),
                        retrieval_engine=system.get('retrieval_engine'),
                        metadata={
                            'experiment_id': experiment.id,
                            'condition_id': condition.id,
                            'condition_parameters': condition.parameters,
                        },
                    )
                    
                    run.evaluation_run_id = eval_run.id
                    run.metrics = eval_run.aggregate_metrics
                    run.status = ExperimentStatus.COMPLETED
                    
                except Exception as e:
                    logger.exception(f"Experiment run failed for condition {condition.id}")
                    run.status = ExperimentStatus.FAILED
                    run.error = str(e)
                
                run.completed_at = datetime.utcnow()
                return run
        
        # Run all conditions
        await asyncio.gather(*[run_condition(c) for c in experiment.conditions])
        
        # Determine best condition
        experiment.best_condition_id = self._find_best_condition(experiment)
        if experiment.best_condition_id:
            best_run = next(r for r in experiment.runs if r.condition_id == experiment.best_condition_id)
            experiment.best_metrics = best_run.metrics
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.utcnow()
        
        return experiment
    
    def _find_best_condition(self, experiment: Experiment) -> Optional[str]:
        """Find the best condition based on success criteria."""
        completed_runs = [r for r in experiment.runs if r.status == ExperimentStatus.COMPLETED]
        if not completed_runs:
            return None
        
        # If success criteria defined, use primary metric
        primary_metric = experiment.config.success_criteria.get('primary_metric')
        if primary_metric:
            # Find run with best primary metric
            best_run = max(
                completed_runs,
                key=lambda r: r.metrics.get(primary_metric, 0)
            )
            return best_run.condition_id
        
        # Default: use first success criterion or mean of all metrics
        if experiment.config.success_criteria:
            metric_name = list(experiment.config.success_criteria.keys())[0]
            best_run = max(
                completed_runs,
                key=lambda r: r.metrics.get(metric_name, 0)
            )
            return best_run.condition_id
        
        # Average all metrics
        best_run = max(
            completed_runs,
            key=lambda r: sum(r.metrics.values()) / len(r.metrics) if r.metrics else 0
        )
        return best_run.condition_id


class GridSearchExperimentRunner(ExperimentRunner):
    """Run grid search over parameter space."""
    
    async def run(
        self,
        experiment: Experiment,
        harness: EvaluationHarness,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run grid search experiment."""
        # Generate all parameter combinations
        experiment.conditions = self._generate_grid(experiment.search_space)
        experiment.config.experiment_type = ExperimentType.GRID_SEARCH
        
        # Run comparative
        runner = ComparativeExperimentRunner()
        return await runner.run(experiment, harness, system_factory)
    
    def _generate_grid(self, search_space: List[ExperimentParameter]) -> List[ExperimentCondition]:
        """Generate all combinations from grid."""
        import itertools
        
        param_names = [p.name for p in search_space]
        param_values = []
        
        for param in search_space:
            if param.param_type == "categorical":
                param_values.append(param.values)
            elif param.param_type in ("float", "int"):
                # Generate steps (simplified - would be configurable)
                steps = 5
                if param.min_value is not None and param.max_value is not None:
                    if param.log_scale:
                        import numpy as np
                        vals = np.logspace(
                            np.log10(param.min_value),
                            np.log10(param.max_value),
                            steps
                        )
                    else:
                        import numpy as np
                        vals = np.linspace(param.min_value, param.max_value, steps)
                    if param.param_type == "int":
                        vals = [int(v) for v in vals]
                    param_values.append(list(vals))
                else:
                    param_values.append([param.min_value or 0])
            elif param.param_type == "bool":
                param_values.append([True, False])
            else:
                param_values.append([None])
        
        conditions = []
        for i, combo in enumerate(itertools.product(*param_values)):
            params = dict(zip(param_names, combo))
            conditions.append(ExperimentCondition(
                id=str(uuid.uuid4()),
                parameters=params,
                label=f"grid_{i}",
            ))
        
        return conditions


class RandomSearchExperimentRunner(ExperimentRunner):
    """Run random search over parameter space."""
    
    def __init__(self, num_samples: int = 20):
        self.num_samples = num_samples
    
    async def run(
        self,
        experiment: Experiment,
        harness: EvaluationHarness,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run random search experiment."""
        # Generate random parameter combinations
        experiment.conditions = self._generate_random(experiment.search_space)
        experiment.config.experiment_type = ExperimentType.RANDOM_SEARCH
        
        # Run comparative
        runner = ComparativeExperimentRunner()
        return await runner.run(experiment, harness, system_factory)
    
    def _generate_random(self, search_space: List[ExperimentParameter]) -> List[ExperimentCondition]:
        """Generate random combinations."""
        import random
        
        random.seed(42)  # Reproducible
        
        conditions = []
        for i in range(self.num_samples):
            params = {}
            for param in search_space:
                if param.param_type == "categorical":
                    params[param.name] = random.choice(param.values)
                elif param.param_type == "float":
                    if param.min_value is not None and param.max_value is not None:
                        if param.log_scale:
                            import numpy as np
                            val = 10 ** random.uniform(
                                np.log10(param.min_value),
                                np.log10(param.max_value)
                            )
                        else:
                            val = random.uniform(param.min_value, param.max_value)
                        params[param.name] = val
                elif param.param_type == "int":
                    if param.min_value is not None and param.max_value is not None:
                        params[param.name] = random.randint(int(param.min_value), int(param.max_value))
                elif param.param_type == "bool":
                    params[param.name] = random.choice([True, False])
            
            conditions.append(ExperimentCondition(
                id=str(uuid.uuid4()),
                parameters=params,
                label=f"random_{i}",
            ))
        
        return conditions


class AblationExperimentRunner(ExperimentRunner):
    """Run ablation experiments (remove one component at a time)."""
    
    def __init__(self, base_config: Dict[str, Any], components_to_ablate: List[str]):
        self.base_config = base_config
        self.components_to_ablate = components_to_ablate
    
    async def run(
        self,
        experiment: Experiment,
        harness: EvaluationHarness,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run ablation experiment."""
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        
        # Base condition (full system)
        base_condition = ExperimentCondition(
            id=str(uuid.uuid4()),
            parameters=self.base_config.copy(),
            label="full_system",
        )
        experiment.conditions.append(base_condition)
        
        # Ablation conditions
        for component in self.components_to_ablate:
            ablated_config = self.base_config.copy()
            ablated_config[component] = False  # or None, or "disabled"
            
            condition = ExperimentCondition(
                id=str(uuid.uuid4()),
                parameters=ablated_config,
                label=f"without_{component}",
            )
            experiment.conditions.append(condition)
        
        # Run comparative
        runner = ComparativeExperimentRunner()
        result = await runner.run(experiment, harness, system_factory)
        
        # Add ablation analysis
        result.metadata['ablation_analysis'] = self._analyze_ablation(result)
        
        return result
    
    def _analyze_ablation(self, experiment: Experiment) -> Dict[str, Any]:
        """Analyze ablation results."""
        base_run = next((r for r in experiment.runs if r.condition_id == experiment.conditions[0].id), None)
        if not base_run:
            return {}
        
        analysis = {}
        for condition in experiment.conditions[1:]:  # Skip base
            run = next((r for r in experiment.runs if r.condition_id == condition.id), None)
            if not run or run.status != ExperimentStatus.COMPLETED:
                continue
            
            component = condition.label.replace("without_", "")
            analysis[component] = {}
            
            for metric, base_value in base_run.metrics.items():
                ablated_value = run.metrics.get(metric)
                if ablated_value is not None:
                    diff = ablated_value - base_value
                    pct_change = (diff / base_value * 100) if base_value != 0 else 0
                    analysis[component][metric] = {
                        'base': base_value,
                        'ablated': ablated_value,
                        'difference': diff,
                        'percent_change': pct_change,
                    }
        
        return analysis


class ScalingExperimentRunner(ExperimentRunner):
    """Run scaling experiments (vary data/compute scale)."""
    
    def __init__(self, scale_factors: List[float] = None):
        self.scale_factors = scale_factors or [0.1, 0.25, 0.5, 0.75, 1.0]
    
    async def run(
        self,
        experiment: Experiment,
        harness: EvaluationHarness,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run scaling experiment."""
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        
        # Create conditions for each scale factor
        for factor in self.scale_factors:
            condition = ExperimentCondition(
                id=str(uuid.uuid4()),
                parameters={'scale_factor': factor},
                label=f"scale_{factor}",
            )
            experiment.conditions.append(condition)
        
        # Run comparative
        runner = ComparativeExperimentRunner()
        result = await runner.run(experiment, harness, system_factory)
        
        # Add scaling analysis
        result.metadata['scaling_analysis'] = self._analyze_scaling(result)
        
        return result
    
    def _analyze_scaling(self, experiment: Experiment) -> Dict[str, Any]:
        """Analyze scaling behavior."""
        completed = [(r, c) for r in experiment.runs 
                     for c in experiment.conditions 
                     if r.condition_id == c.id and r.status == ExperimentStatus.COMPLETED]
        
        if len(completed) < 2:
            return {}
        
        # Sort by scale factor
        completed.sort(key=lambda x: x[1].parameters.get('scale_factor', 0))
        
        analysis = {
            'scale_factors': [c.parameters['scale_factor'] for _, c in completed],
            'metrics': {},
        }
        
        # Track each metric across scales
        all_metrics = set()
        for run, _ in completed:
            all_metrics.update(run.metrics.keys())
        
        for metric in all_metrics:
            values = []
            for run, _ in completed:
                values.append(run.metrics.get(metric))
            analysis['metrics'][metric] = values
        
        return analysis


class ExperimentManager:
    """Manages experiments lifecycle."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.experiments: Dict[str, Experiment] = {}
        self.runners: Dict[ExperimentType, ExperimentRunner] = {
            ExperimentType.COMPARATIVE: ComparativeExperimentRunner(),
            ExperimentType.GRID_SEARCH: GridSearchExperimentRunner(),
            ExperimentType.RANDOM_SEARCH: RandomSearchExperimentRunner(),
            ExperimentType.ABLATION: None,  # Requires special init
            ExperimentType.SCALING: ScalingExperimentRunner(),
        }
        self.harness = EvaluationHarness()
    
    def register_runner(self, exp_type: ExperimentType, runner: ExperimentRunner) -> None:
        """Register a custom experiment runner."""
        self.runners[exp_type] = runner
    
    def create_experiment(
        self,
        config: ExperimentConfig,
        search_space: Optional[List[ExperimentParameter]] = None,
        conditions: Optional[List[ExperimentCondition]] = None,
        test_cases: Optional[List[TestCase]] = None,
    ) -> Experiment:
        """Create a new experiment."""
        experiment = Experiment(
            id=str(uuid.uuid4()),
            config=config,
            search_space=search_space or [],
            conditions=conditions or [],
            test_cases=test_cases or [],
        )
        
        self.experiments[experiment.id] = experiment
        return experiment
    
    async def run_experiment(
        self,
        experiment_id: str,
        system_factory: Callable[[Dict[str, Any]], Any],
    ) -> Experiment:
        """Run an experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        runner = self.runners.get(experiment.config.experiment_type)
        if not runner:
            raise ValueError(f"No runner for experiment type {experiment.config.experiment_type}")
        
        # For ablation, create runner dynamically
        if experiment.config.experiment_type == ExperimentType.ABLATION:
            base_config = experiment.metadata.get('base_config', {})
            components = experiment.metadata.get('components_to_ablate', [])
            runner = AblationExperimentRunner(base_config, components)
        
        return await runner.run(experiment, self.harness, system_factory)
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return self.experiments.get(experiment_id)
    
    def list_experiments(self) -> List[Experiment]:
        """List all experiments."""
        return list(self.experiments.values())
    
    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Get formatted experiment results."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return {}
        
        return {
            'experiment': {
                'id': experiment.id,
                'name': experiment.config.name,
                'type': experiment.config.experiment_type.value,
                'status': experiment.status.value,
                'hypothesis': experiment.config.hypothesis,
            },
            'conditions': [
                {
                    'id': c.id,
                    'label': c.label,
                    'parameters': c.parameters,
                }
                for c in experiment.conditions
            ],
            'runs': [
                {
                    'id': r.id,
                    'condition_id': r.condition_id,
                    'status': r.status.value,
                    'metrics': r.metrics,
                    'error': r.error,
                }
                for r in experiment.runs
            ],
            'best_condition': experiment.best_condition_id,
            'best_metrics': experiment.best_metrics,
            'metadata': experiment.metadata,
        }
    
    def compare_experiments(self, experiment_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple experiments."""
        experiments = [self.experiments[eid] for eid in experiment_ids if eid in self.experiments]
        
        if not experiments:
            return {}
        
        comparison = {
            'experiments': {},
            'best_conditions': {},
        }
        
        for exp in experiments:
            comparison['experiments'][exp.id] = {
                'name': exp.config.name,
                'type': exp.config.experiment_type.value,
                'status': exp.status.value,
                'num_conditions': len(exp.conditions),
                'num_runs': len(exp.runs),
                'best_metrics': exp.best_metrics,
            }
            
            if exp.best_condition_id:
                best_cond = next((c for c in exp.conditions if c.id == exp.best_condition_id), None)
                if best_cond:
                    comparison['best_conditions'][exp.id] = {
                        'condition_id': exp.best_condition_id,
                        'label': best_cond.label,
                        'parameters': best_cond.parameters,
                        'metrics': exp.best_metrics,
                    }
        
        return comparison


# Predefined experiment templates for IP domain
class IPExperimentTemplates:
    """Predefined experiment templates for IP-SAKTI."""
    
    @staticmethod
    def retrieval_strategy_comparison() -> Tuple[ExperimentConfig, List[ExperimentParameter]]:
        """Compare retrieval strategies."""
        config = ExperimentConfig(
            name="Retrieval Strategy Comparison",
            description="Compare semantic, keyword, hybrid, and graph retrieval",
            experiment_type=ExperimentType.COMPARATIVE,
            hypothesis="Hybrid retrieval with authority weighting outperforms single strategies",
            success_criteria={'precision_at_k_10_mean': 0.7, 'mrr_mean': 0.6},
        )
        
        search_space = [
            ExperimentParameter(
                name="retrieval_strategy",
                param_type="categorical",
                values=["semantic", "keyword", "hybrid", "graph"],
            ),
            ExperimentParameter(
                name="hybrid_alpha",
                param_type="float",
                min_value=0.0,
                max_value=1.0,
            ),
        ]
        
        return config, search_space
    
    @staticmethod
    def chunking_strategy_comparison() -> Tuple[ExperimentConfig, List[ExperimentParameter]]:
        """Compare chunking strategies."""
        config = ExperimentConfig(
            name="Chunking Strategy Comparison",
            description="Compare fixed, structural, semantic, and legal chunking",
            experiment_type=ExperimentType.COMPARATIVE,
            hypothesis="Legal structural chunking outperforms generic chunking for IP documents",
            success_criteria={'precision_at_k_5_mean': 0.75, 'faithfulness_mean': 0.85},
        )
        
        search_space = [
            ExperimentParameter(
                name="chunking_strategy",
                param_type="categorical",
                values=["fixed_size", "structural", "semantic", "legal_structural", "patent_claims"],
            ),
            ExperimentParameter(
                name="chunk_size",
                param_type="int",
                min_value=500,
                max_value=2000,
            ),
            ExperimentParameter(
                name="chunk_overlap",
                param_type="int",
                min_value=50,
                max_value=500,
            ),
        ]
        
        return config, search_space
    
    @staticmethod
    def authority_weight_ablation() -> Tuple[ExperimentConfig, Dict[str, Any], List[str]]:
        """Ablation study on authority weighting."""
        config = ExperimentConfig(
            name="Authority Weight Ablation",
            description="Measure impact of authority-weighted reranking",
            experiment_type=ExperimentType.ABLATION,
            hypothesis="Authority weighting improves retrieval precision for IP queries",
            success_criteria={'authority_weighted_score_mean': 0.8},
        )
        
        base_config = {
            'authority_weighted_reranking': True,
            'cross_encoder_reranking': True,
            'query_rewriting': True,
            'multi_query_retrieval': True,
        }
        
        components_to_ablate = [
            'authority_weighted_reranking',
            'cross_encoder_reranking',
            'query_rewriting',
            'multi_query_retrieval',
        ]
        
        return config, base_config, components_to_ablate
    
    @staticmethod
    def embedding_model_comparison() -> Tuple[ExperimentConfig, List[ExperimentParameter]]:
        """Compare embedding models."""
        config = ExperimentConfig(
            name="Embedding Model Comparison",
            description="Compare different embedding models for IP retrieval",
            experiment_type=ExperimentType.COMPARATIVE,
            hypothesis="Domain-specific embeddings outperform general embeddings for IP",
            success_criteria={'ndcg_10_mean': 0.7, 'mrr_mean': 0.65},
        )
        
        search_space = [
            ExperimentParameter(
                name="embedding_model",
                param_type="categorical",
                values=[
                    "text-embedding-3-small",
                    "text-embedding-3-large",
                    "sentence-transformers/all-MiniLM-L6-v2",
                    "sentence-transformers/all-mpnet-base-v2",
                    "domain-specific-ip-embeddings",
                ],
            ),
        ]
        
        return config, search_space
    
    @staticmethod
    def jurisdiction_scaling() -> Tuple[ExperimentConfig, List[float]]:
        """Scaling experiment across jurisdictions."""
        config = ExperimentConfig(
            name="Jurisdiction Scaling",
            description="Evaluate performance as jurisdiction corpus scales",
            experiment_type=ExperimentType.SCALING,
            hypothesis="Performance scales sub-linearly with corpus size",
        )
        
        scale_factors = [0.1, 0.25, 0.5, 0.75, 1.0]
        
        return config, scale_factors


def create_experiment_manager(settings: Optional[Settings] = None) -> ExperimentManager:
    """Factory to create experiment manager."""
    return ExperimentManager(settings)