# Phase 13: Agentic Orchestration

## 1. Overview

The Agentic Orchestration layer handles **complex, multi-step legal research queries** that require planning, tool use, reasoning, and synthesis across multiple retrievals. It transforms the system from a single-turn QA into a **legal research agent** capable of decomposing complex questions, executing multi-hop retrieval, and synthesizing comprehensive answers.

### 1.1 Core Capabilities

| Capability | Description |
|------------|-------------|
| **Query Decomposition** | Break complex queries into sub-questions |
| **Multi-Hop Retrieval** | Chain retrievals (answer to sub-Q1 → informs sub-Q2) |
| **Tool Use** | Retrieval, KG traversal, calculation, comparison, citation verification |
| **Planning** | Create execution plans for multi-step research |
| **Self-Correction** | Detect gaps, re-retrieve, verify citations |
| **Synthesis** | Combine findings into structured legal memos |
| **Human-in-the-Loop** | Escalate ambiguous/novel questions |

### 1.2 Query Types Requiring Agentic Orchestration

| Query Type | Example | Steps Required |
|------------|---------|----------------|
| **Multi-Jurisdictional Comparison** | "Compare patent term extension in India, US, EU" | 3 parallel retrievals → synthesis → comparison table |
| **Regulatory Pathway** | "What's the process to launch Ayurvedic cream in India?" | Formulation class → applicable laws → licensing steps → timeline → fees |
| **Freedom to Operate** | "Can I sell this herbal formulation in India?" | Ingredient analysis → patent search → regulatory classification → ABS check |
| **Compliance Gap Analysis** | "What Section 3(d) cases since 2020 affect my patent?" | Temporal retrieval → case filtering → claim extraction → impact analysis |
| **Cross-Regime Interaction** | "How do CBD and Patents Act interact for TK-based inventions?" | Retrieve both regimes → identify overlap → conflict resolution → synthesis |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC ORCHESTRATION PIPELINE                        │
└─────────────────────────────────────────────────────────────────────────────┘

USER QUERY
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. QUERY ANALYSIS & CLASSIFICATION (Phase 3)                                │
│    - Intent, entities, complexity, jurisdiction                            │
│    - Determine if agentic needed (complexity > threshold)                  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. PLANNER                                                                   │
│    - Decompose query into sub-tasks                                         │
│    - Create execution plan with dependencies                                │
│    - Select tools for each sub-task                                         │
│    - Estimate steps, parallelization                                        │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. EXECUTION ENGINE                                                          │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│    │ RETRIEVAL   │  │ KG TRAVERSAL│  │ CALCULATION │  │ COMPARISON  │      │
│    │ TOOL        │  │ TOOL        │  │ TOOL        │  │ TOOL        │      │
│    └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│    │ CITATION    │  │ FORMULATION │  │ JURISDICTION│  │ SYNTHESIS   │      │
│    │ VERIFICATION│  │ CLASSIFIER  │  │ ENGINE      │  │ TOOL        │      │
│    └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. VERIFICATION & SELF-CORRECTION LOOP                                      │
│    - Check citation coverage                                                │
│    - Identify gaps in evidence                                              │
│    - Re-plan if insufficient                                                │
│    - Max iterations: 3                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. FINAL SYNTHESIS                                                           │
│    - Structure findings as legal memo                                       │
│    - Include: Executive Summary, Analysis, Citations, Confidence, Gaps     │
│    - Multi-jurisdiction segmentation (Phase 9)                             │
│    - Multilingual output (Phase 12)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
STRUCTURED LEGAL MEMO + VERIFIED CITATIONS
```

---

## 3. Data Models

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import uuid

class AgenticQueryType(str, Enum):
    SIMPLE_QA = "simple_qa"                    # Single retrieval sufficient
    MULTI_HOP = "multi_hop"                    # Chain of retrievals
    COMPARATIVE = "comparative"                # Multi-jurisdiction/regime comparison
    PROCEDURAL = "procedural"                  # Step-by-step process
    FTO_ANALYSIS = "fto_analysis"             # Freedom to operate
    GAP_ANALYSIS = "gap_analysis"             # Compliance gaps
    REGULATORY_PATHWAY = "regulatory_pathway" # End-to-end regulatory process

class ToolType(str, Enum):
    RETRIEVAL = "retrieval"
    KG_TRAVERSAL = "kg_traversal"
    CALCULATION = "calculation"
    COMPARISON = "comparison"
    CITATION_VERIFICATION = "citation_verification"
    FORMULATION_CLASSIFICATION = "formulation_classification"
    JURISDICTION_DETERMINATION = "jurisdiction_determination"
    SYNTHESIS = "synthesis"
    TRANSLATION = "translation"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class SubTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    tool: ToolType = ToolType.RETRIEVAL
    input_query: str = ""
    dependencies: List[str] = field(default_factory=list)  # task_ids
    parameters: Dict = field(default_factory=dict)
    expected_output_type: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0

@dataclass
class ExecutionPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str = ""
    query_type: AgenticQueryType = AgenticQueryType.SIMPLE_QA
    tasks: List[SubTask] = field(default_factory=list)
    estimated_steps: int = 0
    parallel_groups: List[List[str]] = field(default_factory=list)  # task_ids that can run in parallel
    max_iterations: int = 3

@dataclass
class AgentState:
    query: str
    plan: ExecutionPlan
    completed_tasks: Dict[str, Any] = field(default_factory=dict)
    evidence_pool: List[EvidenceChunk] = field(default_factory=list)
    claim_pool: List[MappedClaim] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3
    gaps_identified: List[str] = field(default_factory=list)
    final_answer: Optional[GeneratedAnswer] = None
```

---

## 4. Query Classification for Agentic Routing

```python
class AgenticQueryClassifier:
    """
    Determines if query needs agentic orchestration and what type.
    """
    
    AGENTIC_TRIGGERS = {
        AgenticQueryType.MULTI_HOP: [
            "multi-hop keywords": ["step by step", "process", "procedure", "how to", "pathway"],
            "dependency indicators": ["first", "then", "after", "before", "prerequisite"],
        ],
        AgenticQueryType.COMPARATIVE: [
            "comparison keywords": ["compare", "versus", "vs", "difference", "similar", "contrast"],
            "multi-jurisdiction": ["india and", "india vs", "us vs eu", "international comparison"],
        ],
        AgenticQueryType.PROCEDURAL: [
            "procedure keywords": ["procedure", "process", "steps", "requirements for", "how do i"],
            "license/approval": ["license", "approval", "registration", "authorization", "permit"],
        ],
        AgenticQueryType.FTO_ANALYSIS: [
            "fto keywords": ["freedom to operate", "fto", "can i sell", "can i manufacture", "infringement risk"],
            "patent search": ["patent landscape", "patent search", "prior art"],
        ],
        AgenticQueryType.GAP_ANALYSIS: [
            "gap keywords": ["gap", "missing", "compliance", "what am i missing", "checklist"],
            "audit": ["audit", "review", "assess"],
        ],
        AgenticQueryType.REGULATORY_PATHWAY: [
            "pathway keywords": ["regulatory pathway", "launch", "market entry", "commercialize", "go to market"],
            "end-to-end": ["end to end", "complete process", "all requirements"],
        ],
    }
    
    def classify(self, query: str, analysis: QueryAnalysis) -> AgenticQueryType:
        query_lower = query.lower()
        
        # Check each type
        scores = {}
        for qtype, triggers in self.AGENTIC_TRIGGERS.items():
            score = 0
            for category, keywords in triggers.items():
                for kw in keywords:
                    if kw in query_lower:
                        score += 1
            scores[qtype] = score
        
        # Also check complexity indicators
        complexity_score = self._compute_complexity(query, analysis)
        
        # If high complexity but no specific type, default to MULTI_HOP
        if complexity_score > 0.7 and max(scores.values()) == 0:
            return AgenticQueryType.MULTI_HOP
        
        # Return highest scoring type above threshold
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type
        
        return AgenticQueryType.SIMPLE_QA
    
    def _compute_complexity(self, query: str, analysis: QueryAnalysis) -> float:
        """Compute query complexity score 0-1."""
        factors = {
            "num_entities": len(analysis.entities) / 10,
            "num_intents": len(analysis.intents) / 5,
            "temporal_complexity": 1.0 if analysis.temporal_markers else 0.0,
            "multi_jurisdiction": 1.0 if len(analysis.jurisdiction_markers) > 1 else 0.0,
            "query_length": min(len(query.split()) / 50, 1.0),
            "has_formulation": 1.0 if analysis.formulation_classification else 0.0,
        }
        
        weights = {
            "num_entities": 0.2,
            "num_intents": 0.2,
            "temporal_complexity": 0.15,
            "multi_jurisdiction": 0.2,
            "query_length": 0.15,
            "has_formulation": 0.1,
        }
        
        return sum(factors[k] * weights[k] for k in factors)
```

---

## 5. Planner

### 5.1 Plan Generation

```python
class LegalResearchPlanner:
    """
    Creates execution plans for complex legal queries.
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def create_plan(self, query: str, analysis: QueryAnalysis, 
                    query_type: AgenticQueryType) -> ExecutionPlan:
        
        # Get template for query type
        template = self._get_template(query_type)
        
        # Customize template with query specifics
        prompt = f"""
        Create an execution plan for this legal research query.
        
        QUERY: {query}
        QUERY TYPE: {query_type.value}
        ENTITIES: {analysis.entities}
        INTENTS: {analysis.intents}
        JURISDICTION: {analysis.jurisdiction_context.primary}
        FORMULATION CLASS: {analysis.formulation_classification}
        TEMPORAL: {analysis.temporal_markers}
        
        TEMPLATE STRUCTURE:
        {template}
        
        Create a JSON plan with:
        - tasks: array of subtasks with tool, description, input_query, dependencies, expected_output
        - parallel_groups: array of task_id arrays that can run in parallel
        - estimated_steps: total number of steps
        
        Tools available: RETRIEVAL, KG_TRAVERSAL, CALCULATION, COMPARISON, 
                        CITATION_VERIFICATION, FORMULATION_CLASSIFICATION, 
                        JURISDICTION_DETERMINATION, SYNTHESIS, TRANSLATION
        """
        
        plan_dict = self.llm.extract_structured(prompt, Dict)
        return self._parse_plan(plan_dict)
    
    def _get_template(self, query_type: AgenticQueryType) -> Dict:
        templates = {
            AgenticQueryType.MULTI_HOP: {
                "pattern": "sequential",
                "typical_tasks": [
                    {"tool": "RETRIEVAL", "purpose": "Initial broad retrieval"},
                    {"tool": "KG_TRAVERSAL", "purpose": "Follow relationships"},
                    {"tool": "RETRIEVAL", "purpose": "Targeted retrieval based on KG findings"},
                    {"tool": "SYNTHESIS", "purpose": "Combine findings"},
                ]
            },
            AgenticQueryType.COMPARATIVE: {
                "pattern": "parallel",
                "typical_tasks": [
                    {"tool": "JURISDICTION_DETERMINATION", "purpose": "Identify jurisdictions"},
                    {"tool": "RETRIEVAL", "purpose": "Retrieve per jurisdiction (parallel)"},
                    {"tool": "COMPARISON", "purpose": "Compare provisions"},
                    {"tool": "SYNTHESIS", "purpose": "Generate comparison memo"},
                ]
            },
            AgenticQueryType.PROCEDURAL: {
                "pattern": "sequential",
                "typical_tasks": [
                    {"tool": "FORMULATION_CLASSIFICATION", "purpose": "Classify product"},
                    {"tool": "JURISDICTION_DETERMINATION", "purpose": "Identify authorities"},
                    {"tool": "RETRIEVAL", "purpose": "Get procedural requirements"},
                    {"tool": "KG_TRAVERSAL", "purpose": "Get timelines, fees, forms"},
                    {"tool": "SYNTHESIS", "purpose": "Create step-by-step guide"},
                ]
            },
            AgenticQueryType.FTO_ANALYSIS: {
                "pattern": "parallel_then_sequential",
                "typical_tasks": [
                    {"tool": "FORMULATION_CLASSIFICATION", "purpose": "Classify formulation"},
                    {"tool": "RETRIEVAL", "purpose": "Patent search (parallel)"},
                    {"tool": "RETRIEVAL", "purpose": "Regulatory classification (parallel)"},
                    {"tool": "RETRIEVAL", "purpose": "ABS requirements (parallel)"},
                    {"tool": "COMPARISON", "purpose": "Cross-reference findings"},
                    {"tool": "SYNTHESIS", "purpose": "FTO opinion"},
                ]
            },
            AgenticQueryType.REGULATORY_PATHWAY: {
                "pattern": "sequential_with_branches",
                "typical_tasks": [
                    {"tool": "FORMULATION_CLASSIFICATION", "purpose": "Classify product"},
                    {"tool": "JURISDICTION_DETERMINATION", "purpose": "Map to authorities"},
                    {"tool": "RETRIEVAL", "purpose": "Licensing requirements"},
                    {"tool": "RETRIEVAL", "purpose": "Clinical/non-clinical requirements"},
                    {"tool": "RETRIEVAL", "purpose": "Labeling requirements"},
                    {"tool": "RETRIEVAL", "purpose": "Post-market requirements"},
                    {"tool": "CALCULATION", "purpose": "Timeline and cost estimation"},
                    {"tool": "SYNTHESIS", "purpose": "Regulatory roadmap"},
                ]
            },
        }
        return templates.get(query_type, templates[AgenticQueryType.MULTI_HOP])
```

### 5.2 Plan Execution

```python
class PlanExecutor:
    """
    Executes the research plan with parallelization and error handling.
    """
    
    def __init__(self, tools: Dict[ToolType, BaseTool], max_parallel: int = 3):
        self.tools = tools
        self.max_parallel = max_parallel
    
    def execute(self, plan: ExecutionPlan, state: AgentState) -> AgentState:
        """Execute plan with topological sort for dependencies."""
        
        # Build dependency graph
        task_map = {t.task_id: t for t in plan.tasks}
        completed = set()
        
        while len(completed) < len(plan.tasks):
            # Find ready tasks (dependencies met, not completed)
            ready = [
                t for t in plan.tasks 
                if t.task_id not in completed and t.status == TaskStatus.PENDING
                and all(dep in completed for dep in t.dependencies)
            ]
            
            if not ready:
                # Check for circular dependency or failed dependencies
                remaining = [t for t in plan.tasks if t.task_id not in completed]
                for t in remaining:
                    if any(dep not in completed for dep in t.dependencies):
                        # Dependency failed - mark as skipped
                        t.status = TaskStatus.SKIPPED
                        t.error = "Dependency failed"
                        completed.add(t.task_id)
                continue
            
            # Execute ready tasks in parallel (up to max_parallel)
            parallel_tasks = ready[:self.max_parallel]
            results = self._execute_parallel(parallel_tasks, state)
            
            # Update state
            for task, result in zip(parallel_tasks, results):
                task.result = result
                task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                task.execution_time_ms = result.execution_time_ms
                if not result.success:
                    task.error = result.error
                
                # Add to evidence/claim pools
                if result.evidence:
                    state.evidence_pool.extend(result.evidence)
                if result.claims:
                    state.claim_pool.extend(result.claims)
                
                state.completed_tasks[task.task_id] = result
                completed.add(task.task_id)
        
        return state
    
    def _execute_parallel(self, tasks: List[SubTask], state: AgentState) -> List[ToolResult]:
        """Execute tasks in parallel using thread pool."""
        from concurrent.futures import ThreadPoolExecutor
        
        def run_task(task: SubTask) -> ToolResult:
            tool = self.tools.get(task.tool)
            if not tool:
                return ToolResult(success=False, error=f"Tool {task.tool} not found")
            
            # Prepare input with state context
            input_data = self._prepare_input(task, state)
            
            start = time.time()
            try:
                result = tool.execute(input_data)
                return ToolResult(
                    success=True, 
                    evidence=result.get("evidence", []),
                    claims=result.get("claims", []),
                    data=result.get("data"),
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            except Exception as e:
                return ToolResult(
                    success=False, 
                    error=str(e),
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = [executor.submit(run_task, task) for task in tasks]
            return [f.result() for f in futures]
```

---

## 6. Tools

### 6.1 Retrieval Tool

```python
class RetrievalTool:
    """
    Retrieval tool for agentic use.
    """
    
    def __init__(self, retrieval_engine, jurisdiction_engine):
        self.retrieval = retrieval_engine
        self.jurisdiction = jurisdiction_engine
    
    def execute(self, input_data: Dict) -> Dict:
        query = input_data["query"]
        jurisdiction_ctx = input_data.get("jurisdiction_context")
        top_k = input_data.get("top_k", 20)
        
        # Get jurisdiction filter if not provided
        if not jurisdiction_ctx:
            jurisdiction_ctx = self.jurisdiction.determine(JurisdictionDeterminationInput(
                query_text=query,
                query_language=input_data.get("language", "en"),
                formulation_classification=input_data.get("formulation_classification"),
                user_location=input_data.get("user_location"),
                target_markets=input_data.get("target_markets", [])
            ))
        
        # Retrieve
        results = self.retrieval.retrieve(
            query=query,
            analysis=QueryAnalysis(jurisdiction_context=jurisdiction_ctx),
            top_k=top_k
        )
        
        return {
            "evidence": results.chunks,
            "jurisdiction_context": jurisdiction_ctx,
            "retrieval_metadata": results.metadata
        }
```

### 6.2 KG Traversal Tool

```python
class KGTraversalTool:
    """
    Knowledge Graph traversal for multi-hop reasoning.
    """
    
    def __init__(self, kg_client):
        self.kg = kg_client
    
    def execute(self, input_data: Dict) -> Dict:
        query_type = input_data.get("traversal_type", "neighbors")
        entity_id = input_data.get("entity_id")
        depth = input_data.get("depth", 2)
        relationship_types = input_data.get("relationship_types", None)
        
        if query_type == "neighbors":
            results = self._get_neighbors(entity_id, depth, relationship_types)
        elif query_type == "path":
            target_id = input_data.get("target_id")
            results = self._find_path(entity_id, target_id, depth)
        elif query_type == "temporal":
            as_of_date = input_data.get("as_of_date")
            results = self._get_temporal_version(entity_id, as_of_date)
        elif query_type == "conflict":
            results = self._find_conflicts(entity_id)
        else:
            return {"error": f"Unknown traversal type: {query_type}"}
        
        return {
            "data": results,
            "evidence": self._convert_to_chunks(results)
        }
    
    def _get_neighbors(self, entity_id: str, depth: int, rel_types: List[str]) -> List[Dict]:
        """Get neighboring entities up to depth hops."""
        query = """
        MATCH (e:Entity {entity_id: $id})
        CALL apoc.path.expandConfig(e, {
            maxLevel: $depth,
            relationshipFilter: $rel_filter,
            labelFilter: "+Entity",
            uniqueness: "NODE_GLOBAL"
        })
        YIELD path
        RETURN path
        """
        rel_filter = "|".join(rel_types) if rel_types else "*"
        return self.kg.query(query, {"id": entity_id, "depth": depth, "rel_filter": rel_filter})
```

### 6.3 Calculation Tool

```python
class CalculationTool:
    """
    Performs calculations: timelines, fees, deadlines, term calculations.
    """
    
    def execute(self, input_data: Dict) -> Dict:
        calc_type = input_data.get("calculation_type")
        
        if calc_type == "patent_term":
            return self._calc_patent_term(input_data)
        elif calc_type == "deadline":
            return self._calc_deadline(input_data)
        elif calc_type == "fee_schedule":
            return self._calc_fees(input_data)
        elif calc_type == "timeline":
            return self._calc_timeline(input_data)
        elif calc_type == "royalty":
            return self._calc_royalty(input_data)
        else:
            return {"error": f"Unknown calculation type: {calc_type}"}
    
    def _calc_patent_term(self, input_data: Dict) -> Dict:
        """Calculate patent term based on filing date, jurisdiction, adjustments."""
        filing_date = input_data["filing_date"]
        jurisdiction = input_data["jurisdiction"]
        pta_days = input_data.get("pta_days", 0)  # Patent Term Adjustment
        
        if jurisdiction == "INDIA_CENTRAL":
            # India: 20 years from filing, no PTA
            expiry = filing_date + timedelta(days=20*365)
        elif jurisdiction == "USA":
            # US: 20 years from filing + PTA - PTE
            expiry = filing_date + timedelta(days=20*365 + pta_days)
        elif jurisdiction == "EU":
            # EU: 20 years from filing + SPC (up to 5 years)
            spc_years = input_data.get("spc_years", 0)
            expiry = filing_date + timedelta(days=20*365 + spc_years*365)
        else:
            expiry = filing_date + timedelta(days=20*365)
        
        return {
            "data": {
                "filing_date": filing_date.isoformat(),
                "expiry_date": expiry.isoformat(),
                "term_years": 20,
                "adjustments": {"pta_days": pta_days}
            },
            "evidence": []  # Would cite relevant patent act sections
        }
```

### 6.4 Comparison Tool

```python
class ComparisonTool:
    """
    Compares legal provisions across jurisdictions or regimes.
    """
    
    def execute(self, input_data: Dict) -> Dict:
        comparison_type = input_data.get("comparison_type", "provision")
        jurisdictions = input_data.get("jurisdictions", [])
        subject = input_data.get("subject", "")
        provisions = input_data.get("provisions", [])  # Pre-retrieved
        
        if comparison_type == "provision":
            return self._compare_provisions(jurisdictions, subject, provisions)
        elif comparison_type == "regime":
            return self._compare_regimes(jurisdictions, subject)
        elif comparison_type == "timeline":
            return self._compare_timelines(jurisdictions, subject)
        else:
            return {"error": f"Unknown comparison type: {comparison_type}"}
    
    def _compare_provisions(self, jurisdictions: List[str], subject: str, 
                           provisions: List[Dict]) -> Dict:
        """Compare specific legal provisions across jurisdictions."""
        
        # Build comparison matrix
        matrix = {}
        for jur in jurisdictions:
            jur_provisions = [p for p in provisions if p.get("jurisdiction") == jur]
            matrix[jur] = self._extract_key_elements(jur_provisions, subject)
        
        # Identify similarities and differences
        differences = self._identify_differences(matrix)
        harmonized = self._identify_harmonized(matrix)
        
        return {
            "data": {
                "comparison_matrix": matrix,
                "key_differences": differences,
                "harmonized_elements": harmonized,
                "subject": subject,
                "jurisdictions": jurisdictions
            },
            "evidence": provisions
        }
```

### 6.5 Synthesis Tool

```python
class SynthesisTool:
    """
    Synthesizes findings into structured legal memos.
    """
    
    def __init__(self, llm_client, citation_generator):
        self.llm = llm_client
        self.citations = citation_generator
    
    def execute(self, input_data: Dict) -> Dict:
        synthesis_type = input_data.get("synthesis_type", "memo")
        query = input_data["query"]
        evidence = input_data.get("evidence", [])
        claims = input_data.get("claims", [])
        jurisdiction_ctx = input_data.get("jurisdiction_context")
        
        if synthesis_type == "memo":
            return self._generate_memo(query, evidence, claims, jurisdiction_ctx)
        elif synthesis_type == "comparison":
            return self._generate_comparison(query, input_data.get("comparison_data"))
        elif synthesis_type == "checklist":
            return self._generate_checklist(query, evidence, claims)
        elif synthesis_type == "timeline":
            return self._generate_timeline(query, evidence)
        else:
            return {"error": f"Unknown synthesis type: {synthesis_type}"}
    
    def _generate_memo(self, query: str, evidence: List, claims: List, 
                       jurisdiction_ctx) -> Dict:
        """Generate structured legal memo."""
        
        # Format evidence for prompt
        evidence_text = self._format_evidence(evidence)
        
        prompt = f"""
        Generate a structured legal research memo for the following query.
        
        QUERY: {query}
        JURISDICTION: {jurisdiction_ctx.primary if jurisdiction_ctx else 'Unknown'}
        
        EVIDENCE:
        {evidence_text}
        
        STRUCTURE:
        1. EXECUTIVE SUMMARY (2-3 sentences)
        2. APPLICABLE LAW & JURISDICTION
        3. DETAILED ANALYSIS
           - For each key finding: claim + citation
        4. PRACTICAL IMPLICATIONS
        5. RISKS & UNCERTAINTIES
        6. RECOMMENDATIONS
        7. CITATIONS (full)
        8. CONFIDENCE ASSESSMENT
        9. KNOWLEDGE GAPS (what couldn't be determined)
        
        Requirements:
        - Every legal assertion must have inline citation [CHUNK_ID]
        - Use professional legal tone
        - Flag any conflicting authorities
        - Note temporal limitations
        - Include abstentions for insufficient evidence
        
        Return JSON with: content, citations, confidence, gaps
        """
        
        result = self.llm.extract_structured(prompt, Dict)
        
        # Verify citations
        verified = self.citations.verify_citations(result, evidence)
        
        return {
            "data": verified,
            "evidence": evidence
        }
```

---

## 7. Self-Correction & Verification Loop

```python
class VerificationLoop:
    """
    Verifies answer completeness and triggers re-planning if gaps found.
    """
    
    def __init__(self, planner: LegalResearchPlanner, executor: PlanExecutor):
        self.planner = planner
        self.executor = executor
    
    def verify_and_correct(self, state: AgentState) -> AgentState:
        """Run verification loop up to max_iterations."""
        
        for iteration in range(state.max_iterations):
            state.iteration = iteration
            
            # 1. Check citation coverage
            coverage = self._check_citation_coverage(state)
            
            # 2. Identify gaps
            gaps = self._identify_gaps(state, coverage)
            state.gaps_identified = gaps
            
            # 3. If no gaps or max iterations, break
            if not gaps or iteration == state.max_iterations - 1:
                break
            
            # 4. Create gap-filling plan
            gap_plan = self._create_gap_plan(gaps, state)
            
            # 5. Execute gap plan
            state = self.executor.execute(gap_plan, state)
        
        return state
    
    def _check_citation_coverage(self, state: AgentState) -> Dict:
        """Check what aspects of query are covered by citations."""
        # Analyze claims vs query intents
        covered_intents = set()
        for claim in state.claim_pool:
            for intent in claim.claim.metadata.get("addresses_intents", []):
                covered_intents.add(intent)
        
        all_intents = set(state.query_analysis.intents)
        
        return {
            "covered": covered_intents,
            "missing": all_intents - covered_intents,
            "coverage_ratio": len(covered_intents) / len(all_intents) if all_intents else 1.0
        }
    
    def _identify_gaps(self, state: AgentState, coverage: Dict) -> List[str]:
        """Identify specific evidence gaps."""
        gaps = []
        
        # Missing intents
        for intent in coverage["missing"]:
            gaps.append(f"No evidence found for intent: {intent}")
        
        # Low confidence claims
        for claim in state.claim_pool:
            if claim.authority_weighted_score < 0.5:
                gaps.append(f"Low authority support for: {claim.claim.claim_text[:100]}")
        
        # Contradictions unresolved
        for claim in state.claim_pool:
            if claim.verification_notes and "CONFLICT" in claim.verification_notes:
                gaps.append(f"Unresolved conflict: {claim.claim.claim_text[:100]}")
        
        # Missing jurisdictions (if comparative)
        if state.query_analysis.jurisdiction_context.requires_multi_jurisdiction_answer():
            covered_jurs = {c.claim.jurisdiction_id for c in state.claim_pool}
            required_jurs = set(state.query_analysis.jurisdiction_context.get_generation_jurisdictions())
            for jur in required_jurs - covered_jurs:
                gaps.append(f"No evidence from jurisdiction: {jur}")
        
        return gaps
    
    def _create_gap_plan(self, gaps: List[str], state: AgentState) -> ExecutionPlan:
        """Create plan to fill identified gaps."""
        tasks = []
        
        for i, gap in enumerate(gaps):
            if "No evidence found for intent" in gap:
                intent = gap.split(": ")[1]
                tasks.append(SubTask(
                    description=f"Retrieve evidence for {intent}",
                    tool=ToolType.RETRIEVAL,
                    input_query=f"Legal provisions for {intent}",
                    expected_output_type="evidence"
                ))
            elif "Low authority support" in gap:
                claim_text = gap.split(": ")[1]
                tasks.append(SubTask(
                    description=f"Find higher authority source for claim",
                    tool=ToolType.RETRIEVAL,
                    input_query=f"Binding authority for: {claim_text}",
                    expected_output_type="evidence"
                ))
            elif "Unresolved conflict" in gap:
                tasks.append(SubTask(
                    description="Resolve conflicting authorities",
                    tool=ToolType.KG_TRAVERSAL,
                    input_query="conflict_resolution",
                    parameters={"claim_text": gap.split(": ")[1]},
                    expected_output_type="resolution"
                ))
            elif "No evidence from jurisdiction" in gap:
                jur = gap.split(": ")[1]
                tasks.append(SubTask(
                    description=f"Retrieve from {jur}",
                    tool=ToolType.RETRIEVAL,
                    input_query=state.query,
                    parameters={"jurisdiction": jur},
                    expected_output_type="evidence"
                ))
        
        return ExecutionPlan(
            query=state.query,
            query_type=AgenticQueryType.MULTI_HOP,
            tasks=tasks,
            estimated_steps=len(tasks)
        )
```

---

## 8. Human-in-the-Loop Escalation

```python
class EscalationManager:
    """
    Manages escalation to human experts for novel/ambiguous queries.
    """
    
    ESCALATION_TRIGGERS = [
        "NO_AUTHORITATIVE_SOURCE",      # No Tier 1-3 sources found
        "CONFLICTING_SUPREME_COURT",    # SC judgments conflict
        "NOVEL_LEGAL_QUESTION",         # No precedent found
        "CONSTITUTIONAL_QUESTION",      # Constitutional interpretation needed
        "CROSS_BORDER_ENFORCEMENT",     # International enforcement
        "REGULATORY_UNCERTAINTY",       # Regulator hasn't issued guidance
        "HIGH_STAKES",                  # Significant commercial/legal impact
    ]
    
    def should_escalate(self, state: AgentState) -> Optional[EscalationRequest]:
        # Check triggers
        for trigger in self.ESCALATION_TRIGGERS:
            if self._check_trigger(trigger, state):
                return EscalationRequest(
                    trigger=trigger,
                    query=state.query,
                    context=self._build_escalation_context(state),
                    urgency=self._assess_urgency(state)
                )
        
        # Check confidence threshold
        if state.final_answer and state.final_answer.overall_confidence < 0.4:
            return EscalationRequest(
                trigger="LOW_CONFIDENCE",
                query=state.query,
                context=self._build_escalation_context(state),
                urgency="NORMAL"
            )
        
        return None
    
    def _check_trigger(self, trigger: str, state: AgentState) -> bool:
        if trigger == "NO_AUTHORITATIVE_SOURCE":
            binding_claims = [c for c in state.claim_pool if c.claim.authority_tier.value <= 3]
            return len(binding_claims) == 0
        
        elif trigger == "CONFLICTING_SUPREME_COURT":
            sc_claims = [c for c in state.claim_pool 
                        if c.claim.authority_tier == AuthorityTier.TIER_3 
                        and c.claim.metadata.get("court") == "Supreme Court"]
            # Check for contradictory SC claims
            return self._has_contradictions(sc_claims)
        
        elif trigger == "NOVEL_LEGAL_QUESTION":
            # No claims found at all
            return len(state.claim_pool) == 0
        
        return False
```

---

## 9. Integration Points

| Phase | Integration |
|-------|-------------|
| **Phase 3** | Query classification → agentic routing decision |
| **Phase 6** | Retrieval tool for evidence gathering |
| **Phase 7** | KG traversal tool for multi-hop reasoning |
| **Phase 8** | Formulation classification tool |
| **Phase 9** | Jurisdiction determination tool |
| **Phase 10** | Citation verification tool |
| **Phase 11** | Authority-weighted tool selection |
| **Phase 12** | Translation tool for multilingual queries |
| **Phase 14** | Memory for conversation context, learned procedures |
| **Phase 17** | Evaluation of agentic vs non-agentic performance |

---

## 10. Evaluation Framework

```python
AGENTIC_TEST_CASES = [
    AgenticTestCase(
        case_id="AG-001",
        query="What is the complete regulatory pathway to launch a phytopharmaceutical in India?",
        query_type=AgenticQueryType.REGULATORY_PATHWAY,
        expected_steps=["classification", "jurisdiction", "licensing", "clinical", "labeling", "post-market"],
        must_cite=["D&C Act", "Phytopharmaceutical Guidelines 2015", "NDCT Rules 2019"],
        min_confidence=0.7
    ),
    AgenticTestCase(
        case_id="AG-002",
        query="Compare compulsory licensing provisions in India, US, and EU for pharmaceuticals",
        query_type=AgenticQueryType.COMPARATIVE,
        expected_jurisdictions=["INDIA_CENTRAL", "USA", "EU"],
        must_cite=["Section 84 Patents Act", "28 USC 1498", "EU Directive 2001/83"],
        min_confidence=0.8
    ),
    AgenticTestCase(
        case_id="AG-003",
        query="Can I export Ashwagandha extract to US without FDA approval if it's a dietary supplement?",
        query_type=AgenticQueryType.FTO_ANALYSIS,
        expected_steps=["classification", "india_export", "us_import", "abs_check", "fda_analysis"],
        must_cite=["BDA 2002", "FD&C Act", "DSHEA 1994"],
        min_confidence=0.75
    ),
]

AGENTIC_METRICS = {
    "plan_quality": "Human eval: plan completeness, correctness, efficiency",
    "tool_selection_accuracy": "% correct tool chosen for sub-task",
    "parallelization_efficiency": "Actual parallel speedup vs theoretical",
    "gap_detection_recall": "% of actual gaps identified",
    "self_correction_success": "% gaps resolved in verification loop",
    "escalation_precision": "% escalations that were truly needed",
    "end_to_end_accuracy": "Final answer quality vs baseline",
}
```

---

## 11. Open Research Questions

| ID | Question |
|----|----------|
| **ORQ-73** | Optimal planning horizon: fixed template vs LLM-generated plans? |
| **ORQ-74** | How to handle tool failures gracefully (fallback tools)? |
| **ORQ-75** | Memory-augmented planning: learn from past successful plans? |
| **ORQ-76** | Cost/latency tradeoff: when to use agentic vs simple RAG? |
| **ORQ-77** | Evaluating multi-step reasoning without ground truth plans? |
| **ORQ-78** | Agentic orchestration for real-time regulatory monitoring? |

---

## 12. Implementation Checklist

- [ ] Query classifier for agentic routing
- [ ] Planner with templates per query type
- [ ] Plan executor with parallelization
- [ ] Tool registry (retrieval, KG, calculation, comparison, synthesis, etc.)
- [ ] Retrieval tool with jurisdiction context
- [ ] KG traversal tool (neighbors, paths, temporal, conflicts)
- [ ] Calculation tool (patent term, deadlines, fees, timelines)
- [ ] Comparison tool (provisions, regimes, timelines)
- [ ] Synthesis tool (memos, comparisons, checklists, timelines)
- [ ] Verification loop (citation coverage, gap detection, re-planning)
- [ ] Escalation manager (triggers, context building, urgency)
- [ ] Integration tests with Phases 3, 6, 7, 8, 9, 10, 11, 12
- [ ] Agentic evaluation dataset
- [ ] Cost/latency monitoring

---

## 13. Summary

| Aspect | Decision |
|--------|----------|
| **Trigger** | Query complexity > threshold OR specific query types |
| **Query Types** | 6 types: multi-hop, comparative, procedural, FTO, gap, regulatory pathway |
| **Planning** | Template-based + LLM customization |
| **Execution** | Topological sort + parallel execution (max 3) |
| **Tools** | 9 tools: retrieval, KG, calculation, comparison, citation, formulation, jurisdiction, synthesis, translation |
| **Verification** | 3-iteration loop: coverage check → gap detection → re-plan → execute |
| **Escalation** | 7 triggers + confidence threshold |
| **Output** | Structured legal memo with citations, confidence, gaps |

---

## 14. Next Phase: Phase 14 - Memory Architecture

Phase 14 will design the **Memory Architecture** for:
- Conversation memory (short-term context)
- Long-term procedural memory (learned pathways)
- Episodic memory (past queries, answers, corrections)
- Semantic memory (legal concepts, relationships)
- Memory retrieval and consolidation
- Privacy and data retention policies