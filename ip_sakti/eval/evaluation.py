"""
IP-SAKTI Evaluation System
Phase 11: Implements the evaluation system for RAG quality assessment.
This must exist before Phase 13 (Knowledge Graph) which requires running experiments.
"""

import asyncio
import json
import logging
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import (
    DocumentChunk,
    DocumentType,
    EvaluationMetric,
    EvaluationResult,
    Jurisdiction,
    Query,
    QueryIntent,
    RetrievalResult,
    RetrievalStrategy,
)
from ip_sakti.rag.pipeline import RAGPipeline, RAGContext
from ip_sakti.retrieval.retrieval_engine import RetrievalEngine, SearchRequest

logger = logging.getLogger(__name__)


class EvaluationType(str, Enum):
    """Types of evaluation."""
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    END_TO_END = "end_to_end"
    CITATION = "citation"
    AUTHORITY = "authority"
    MULTILINGUAL = "multilingual"


@dataclass
class EvaluationConfig:
    """Configuration for evaluation."""
    metrics: List[EvaluationMetric] = field(default_factory=lambda: [
        EvaluationMetric.PRECISION_AT_K,
        EvaluationMetric.RECALL_AT_K,
        EvaluationMetric.MRR,
        EvaluationMetric.NDCG,
        EvaluationMetric.FAITHFULNESS,
        EvaluationMetric.ANSWER_RELEVANCY,
        EvaluationMetric.CITATION_ACCURACY,
        EvaluationMetric.AUTHORITY_WEIGHTED_SCORE,
    ])
    k_values: List[int] = field(default_factory=lambda: [1, 3, 5, 10])
    judge_model: str = "gpt-4"  # For LLM-as-judge
    num_judge_samples: int = 3
    parallel_evaluations: int = 5


@dataclass
class TestCase:
    """Single test case for evaluation."""
    id: str
    query: str
    intent: QueryIntent
    expected_chunks: List[str] = field(default_factory=list)  # chunk_ids
    expected_answer: Optional[str] = None
    expected_citations: List[Dict[str, Any]] = field(default_factory=list)
    jurisdiction: Optional[Jurisdiction] = None
    document_types: List[DocumentType] = field(default_factory=list)
    difficulty: str = "moderate"  # simple, moderate, complex
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationRun:
    """Results of an evaluation run."""
    id: str
    name: str
    evaluation_type: EvaluationType
    config: EvaluationConfig
    test_cases: List[TestCase]
    results: List[EvaluationResult] = field(default_factory=list)
    aggregate_metrics: Dict[str, float] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricCalculator(ABC):
    """Abstract base for metric calculators."""
    
    @abstractmethod
    def calculate(
        self,
        test_case: TestCase,
        prediction: Any,
        ground_truth: Any,
    ) -> float:
        """Calculate metric score."""
        pass


class RetrievalMetrics:
    """Retrieval evaluation metrics."""
    
    @staticmethod
    def precision_at_k(
        retrieved: List[str],
        relevant: List[str],
        k: int,
    ) -> float:
        """Precision@K."""
        if not retrieved or k == 0:
            return 0.0
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for r in retrieved_k if r in relevant_set)
        return hits / min(k, len(retrieved_k))
    
    @staticmethod
    def recall_at_k(
        retrieved: List[str],
        relevant: List[str],
        k: int,
    ) -> float:
        """Recall@K."""
        if not relevant:
            return 1.0
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for r in retrieved_k if r in relevant_set)
        return hits / len(relevant)
    
    @staticmethod
    def mrr(retrieved: List[str], relevant: List[str]) -> float:
        """Mean Reciprocal Rank."""
        relevant_set = set(relevant)
        for i, r in enumerate(retrieved, 1):
            if r in relevant_set:
                return 1.0 / i
        return 0.0
    
    @staticmethod
    def ndcg_at_k(
        retrieved: List[str],
        relevant: List[str],
        k: int,
        relevance_scores: Optional[Dict[str, float]] = None,
    ) -> float:
        """Normalized Discounted Cumulative Gain @K."""
        if not relevant:
            return 1.0
        
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        
        # Default binary relevance
        if relevance_scores is None:
            relevance_scores = {r: 1.0 for r in relevant}
        
        # DCG
        dcg = 0.0
        for i, r in enumerate(retrieved_k, 1):
            if r in relevant_set:
                rel = relevance_scores.get(r, 1.0)
                dcg += rel / np.log2(i + 1)
        
        # IDCG (ideal)
        ideal_relevances = sorted(relevance_scores.values(), reverse=True)
        idcg = 0.0
        for i, rel in enumerate(ideal_relevances[:k], 1):
            idcg += rel / np.log2(i + 1)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def authority_weighted_precision(
        retrieved: List[Tuple[str, float]],  # (chunk_id, authority_score)
        relevant: List[str],
        k: int,
    ) -> float:
        """Precision weighted by authority scores."""
        if not retrieved or k == 0:
            return 0.0
        
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        
        total_weight = 0.0
        hit_weight = 0.0
        
        for chunk_id, authority in retrieved_k:
            total_weight += authority
            if chunk_id in relevant_set:
                hit_weight += authority
        
        return hit_weight / total_weight if total_weight > 0 else 0.0


class GenerationMetrics:
    """Generation evaluation metrics."""
    
    def __init__(self, judge_model: str = "gpt-4"):
        self.judge_model = judge_model
    
    async def faithfulness(
        self,
        answer: str,
        context: str,
    ) -> float:
        """Evaluate faithfulness of answer to context (LLM-as-judge)."""
        # Placeholder - in production would call LLM
        # Returns score 0-1
        return 0.85  # Mock
    
    async def answer_relevancy(
        self,
        question: str,
        answer: str,
    ) -> float:
        """Evaluate answer relevancy to question (LLM-as-judge)."""
        # Placeholder
        return 0.88  # Mock
    
    async def citation_accuracy(
        self,
        answer: str,
        citations: List[Dict[str, Any]],
        context_chunks: List[DocumentChunk],
    ) -> float:
        """Evaluate citation accuracy."""
        # Check if citations in answer match provided sources
        import re
        cited_ids = set(int(m) for m in re.findall(r'\[(\d+)\]', answer))
        valid_ids = {c['id'] for c in citations}
        
        if not cited_ids:
            return 0.0 if citations else 1.0
        
        correct = cited_ids & valid_ids
        return len(correct) / len(cited_ids) if cited_ids else 0.0
    
    async def hallucination_rate(
        self,
        answer: str,
        context: str,
    ) -> float:
        """Estimate hallucination rate (lower is better)."""
        # Placeholder - would use LLM to detect unsupported claims
        return 0.05  # Mock


class Evaluator:
    """Main evaluator for running evaluations."""
    
    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        settings: Optional[Settings] = None,
    ):
        self.config = config or EvaluationConfig()
        self.settings = settings or get_settings()
        self.retrieval_metrics = RetrievalMetrics()
        self.generation_metrics = GenerationMetrics(self.config.judge_model)
    
    async def evaluate_retrieval(
        self,
        test_cases: List[TestCase],
        retrieval_engine: RetrievalEngine,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
    ) -> List[EvaluationResult]:
        """Evaluate retrieval quality."""
        results = []
        
        for test_case in test_cases:
            # Search
            request = SearchRequest(
                query=test_case.query,
                strategy=strategy,
                filters={
                    'jurisdiction': test_case.jurisdiction.value if test_case.jurisdiction else None,
                    'document_type': test_case.document_types[0].value if test_case.document_types else None,
                },
                top_k=max(self.config.k_values),
            )
            
            response = await retrieval_engine.search(request)
            retrieved_ids = [r.chunk.id for r in response.results]
            relevant_ids = test_case.expected_chunks
            
            # Calculate metrics for each k
            for k in self.config.k_values:
                if EvaluationMetric.PRECISION_AT_K in self.config.metrics:
                    p_at_k = self.retrieval_metrics.precision_at_k(
                        retrieved_ids, relevant_ids, k
                    )
                    results.append(EvaluationResult(
                        test_case_id=test_case.id,
                        metric=EvaluationMetric.PRECISION_AT_K,
                        value=p_at_k,
                        parameters={'k': k, 'strategy': strategy.value},
                    ))
                
                if EvaluationMetric.RECALL_AT_K in self.config.metrics:
                    r_at_k = self.retrieval_metrics.recall_at_k(
                        retrieved_ids, relevant_ids, k
                    )
                    results.append(EvaluationResult(
                        test_case_id=test_case.id,
                        metric=EvaluationMetric.RECALL_AT_K,
                        value=r_at_k,
                        parameters={'k': k, 'strategy': strategy.value},
                    ))
                
                if EvaluationMetric.NDCG in self.config.metrics:
                    ndcg = self.retrieval_metrics.ndcg_at_k(
                        retrieved_ids, relevant_ids, k
                    )
                    results.append(EvaluationResult(
                        test_case_id=test_case.id,
                        metric=EvaluationMetric.NDCG,
                        value=ndcg,
                        parameters={'k': k, 'strategy': strategy.value},
                    ))
            
            # MRR
            if EvaluationMetric.MRR in self.config.metrics:
                mrr = self.retrieval_metrics.mrr(retrieved_ids, relevant_ids)
                results.append(EvaluationResult(
                    test_case_id=test_case.id,
                    metric=EvaluationMetric.MRR,
                    value=mrr,
                    parameters={'strategy': strategy.value},
                ))
            
            # Authority-weighted
            if EvaluationMetric.AUTHORITY_WEIGHTED_SCORE in self.config.metrics:
                auth_results = [(r.chunk.id, r.chunk.metadata.get('authority_score', 0.5)) for r in response.results]
                auth_prec = self.retrieval_metrics.authority_weighted_precision(
                    auth_results, relevant_ids, self.config.k_values[-1]
                )
                results.append(EvaluationResult(
                    test_case_id=test_case.id,
                    metric=EvaluationMetric.AUTHORITY_WEIGHTED_SCORE,
                    value=auth_prec,
                    parameters={'k': self.config.k_values[-1]},
                ))
        
        return results
    
    async def evaluate_generation(
        self,
        test_cases: List[TestCase],
        rag_pipeline: RAGPipeline,
    ) -> List[EvaluationResult]:
        """Evaluate generation quality."""
        results = []
        
        for test_case in test_cases:
            query = Query(
                text=test_case.query,
                intent=test_case.intent,
                jurisdiction=test_case.jurisdiction,
            )
            
            # Run RAG pipeline
            rag_context = await rag_pipeline.run(query)
            
            if not rag_context.generated_answer:
                # No answer generated
                for metric in [EvaluationMetric.FAITHFULNESS, EvaluationMetric.ANSWER_RELEVANCY, EvaluationMetric.CITATION_ACCURACY]:
                    if metric in self.config.metrics:
                        results.append(EvaluationResult(
                            test_case_id=test_case.id,
                            metric=metric,
                            value=0.0,
                            parameters={'error': 'no_answer'},
                        ))
                continue
            
            # Faithfulness
            if EvaluationMetric.FAITHFULNESS in self.config.metrics:
                context_str = rag_context.metadata.get('context_string', '')
                faithfulness = await self.generation_metrics.faithfulness(
                    rag_context.generated_answer,
                    context_str,
                )
                results.append(EvaluationResult(
                    test_case_id=test_case.id,
                    metric=EvaluationMetric.FAITHFULNESS,
                    value=faithfulness,
                ))
            
            # Answer Relevancy
            if EvaluationMetric.ANSWER_RELEVANCY in self.config.metrics:
                relevancy = await self.generation_metrics.answer_relevancy(
                    test_case.query,
                    rag_context.generated_answer,
                )
                results.append(EvaluationResult(
                    test_case_id=test_case.id,
                    metric=EvaluationMetric.ANSWER_RELEVANCY,
                    value=relevancy,
                ))
            
            # Citation Accuracy
            if EvaluationMetric.CITATION_ACCURACY in self.config.metrics:
                citation_acc = await self.generation_metrics.citation_accuracy(
                    rag_context.generated_answer,
                    rag_context.citations,
                    rag_context.context_chunks,
                )
                results.append(EvaluationResult(
                    test_case_id=test_case.id,
                    metric=EvaluationMetric.CITATION_ACCURACY,
                    value=citation_acc,
                ))
            
            # Hallucination Rate
            if EvaluationMetric.HALLUCINATION_RATE in self.config.metrics:
                context_str = rag_context.metadata.get('context_string', '')
                hallucination = await self.generation_metrics.hallucination_rate(
                    rag_context.generated_answer,
                    context_str,
                )
                results.append(EvaluationResult(
                    test_case_id=test_case.id,
                    metric=EvaluationMetric.HALLUCINATION_RATE,
                    value=hallucination,
                ))
        
        return results
    
    async def evaluate_end_to_end(
        self,
        test_cases: List[TestCase],
        rag_pipeline: RAGPipeline,
        retrieval_engine: RetrievalEngine,
    ) -> List[EvaluationResult]:
        """Run full end-to-end evaluation."""
        all_results = []
        
        # Run retrieval evaluation
        retrieval_results = await self.evaluate_retrieval(test_cases, retrieval_engine)
        all_results.extend(retrieval_results)
        
        # Run generation evaluation
        generation_results = await self.evaluate_generation(test_cases, rag_pipeline)
        all_results.extend(generation_results)
        
        return all_results


class EvaluationHarness:
    """Harness for running and managing evaluations."""
    
    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        settings: Optional[Settings] = None,
    ):
        self.config = config or EvaluationConfig()
        self.settings = settings or get_settings()
        self.evaluator = Evaluator(self.config, self.settings)
        self.runs: Dict[str, EvaluationRun] = {}
    
    async def run_evaluation(
        self,
        name: str,
        evaluation_type: EvaluationType,
        test_cases: List[TestCase],
        rag_pipeline: Optional[RAGPipeline] = None,
        retrieval_engine: Optional[RetrievalEngine] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationRun:
        """Run a complete evaluation."""
        run = EvaluationRun(
            id=str(uuid.uuid4()),
            name=name,
            evaluation_type=evaluation_type,
            config=self.config,
            test_cases=test_cases,
            metadata=metadata or {},
        )
        
        self.runs[run.id] = run
        
        try:
            if evaluation_type == EvaluationType.RETRIEVAL:
                if not retrieval_engine:
                    raise ValueError("Retrieval engine required for retrieval evaluation")
                run.results = await self.evaluator.evaluate_retrieval(
                    test_cases, retrieval_engine
                )
            elif evaluation_type == EvaluationType.GENERATION:
                if not rag_pipeline:
                    raise ValueError("RAG pipeline required for generation evaluation")
                run.results = await self.evaluator.evaluate_generation(
                    test_cases, rag_pipeline
                )
            elif evaluation_type == EvaluationType.END_TO_END:
                if not rag_pipeline or not retrieval_engine:
                    raise ValueError("Both RAG pipeline and retrieval engine required for end-to-end evaluation")
                run.results = await self.evaluator.evaluate_end_to_end(
                    test_cases, rag_pipeline, retrieval_engine
                )
            
            # Calculate aggregate metrics
            run.aggregate_metrics = self._calculate_aggregates(run.results)
            
        finally:
            run.completed_at = datetime.utcnow()
        
        return run
    
    def _calculate_aggregates(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Calculate aggregate metrics across test cases."""
        aggregates = {}
        
        # Group by metric
        metric_values: Dict[EvaluationMetric, List[float]] = {}
        for result in results:
            if result.metric not in metric_values:
                metric_values[result.metric] = []
            metric_values[result.metric].append(result.value)
        
        # Calculate statistics
        for metric, values in metric_values.items():
            if values:
                aggregates[f"{metric.value}_mean"] = statistics.mean(values)
                aggregates[f"{metric.value}_median"] = statistics.median(values)
                aggregates[f"{metric.value}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
                aggregates[f"{metric.value}_min"] = min(values)
                aggregates[f"{metric.value}_max"] = max(values)
        
        return aggregates
    
    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        """Get evaluation run by ID."""
        return self.runs.get(run_id)
    
    def list_runs(self) -> List[EvaluationRun]:
        """List all evaluation runs."""
        return list(self.runs.values())
    
    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple evaluation runs."""
        runs = [self.runs[rid] for rid in run_ids if rid in self.runs]
        
        if not runs:
            return {}
        
        comparison = {
            'runs': {},
            'metric_comparison': {},
        }
        
        for run in runs:
            comparison['runs'][run.id] = {
                'name': run.name,
                'type': run.evaluation_type.value,
                'metrics': run.aggregate_metrics,
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
            }
        
        # Compare metrics across runs
        all_metrics = set()
        for run in runs:
            all_metrics.update(run.aggregate_metrics.keys())
        
        for metric in all_metrics:
            comparison['metric_comparison'][metric] = {
                run.id: run.aggregate_metrics.get(metric)
                for run in runs
            }
        
        return comparison


# Test case builders for common IP scenarios
class IPTestCaseBuilder:
    """Builder for IP-specific test cases."""
    
    @staticmethod
    def patent_novelty_query(
        query: str,
        relevant_patent_ids: List[str],
        jurisdiction: Jurisdiction = Jurisdiction.US,
    ) -> TestCase:
        return TestCase(
            id=str(uuid.uuid4()),
            query=query,
            intent=QueryIntent.PATENT_SEARCH,
            expected_chunks=relevant_patent_ids,
            jurisdiction=jurisdiction,
            document_types=[DocumentType.PATENT],
            difficulty="moderate",
        )
    
    @staticmethod
    def trademark_confusion_query(
        query: str,
        relevant_mark_ids: List[str],
        jurisdiction: Jurisdiction = Jurisdiction.US,
    ) -> TestCase:
        return TestCase(
            id=str(uuid.uuid4()),
            query=query,
            intent=QueryIntent.TRADEMARK_SEARCH,
            expected_chunks=relevant_mark_ids,
            jurisdiction=jurisdiction,
            document_types=[DocumentType.TRADEMARK],
            difficulty="moderate",
        )
    
    @staticmethod
    def fto_analysis_query(
        query: str,
        relevant_patent_ids: List[str],
        jurisdiction: Jurisdiction = Jurisdiction.US,
    ) -> TestCase:
        return TestCase(
            id=str(uuid.uuid4()),
            query=query,
            intent=QueryIntent.FREEDOM_TO_OPERATE,
            expected_chunks=relevant_patent_ids,
            jurisdiction=jurisdiction,
            document_types=[DocumentType.PATENT],
            difficulty="complex",
        )
    
    @staticmethod
    def validity_challenge_query(
        query: str,
        relevant_patent_ids: List[str],
        jurisdiction: Jurisdiction = Jurisdiction.US,
    ) -> TestCase:
        return TestCase(
            id=str(uuid.uuid4()),
            query=query,
            intent=QueryIntent.VALIDITY_CHALLENGE,
            expected_chunks=relevant_patent_ids,
            jurisdiction=jurisdiction,
            document_types=[DocumentType.PATENT, DocumentType.CASE_LAW],
            difficulty="complex",
        )


def create_evaluation_harness(
    config: Optional[EvaluationConfig] = None,
) -> EvaluationHarness:
    """Factory to create evaluation harness."""
    return EvaluationHarness(config)