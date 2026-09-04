"""
IP-SAKTI Agentic Orchestration
Phase 18: Implements the agentic orchestration layer for complex multi-step reasoning,
tool use, and workflow management for IP analysis tasks.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set, Tuple, Union

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import (
    Citation,
    Document,
    DocumentChunk,
    DocumentType,
    Jurisdiction,
    Language,
    SourceAuthority,
)

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of agents in the orchestration system."""
    PLANNER = "planner"
    RETRIEVER = "retriever"
    ANALYZER = "analyzer"
    WRITER = "writer"
    CRITIC = "critic"
    VALIDATOR = "validator"
    TRANSLATOR = "translator"
    JURISDICTION_EXPERT = "jurisdiction_expert"
    FORMULATION_EXPERT = "formulation_expert"
    CITATION_MANAGER = "citation_manager"


class TaskStatus(str, Enum):
    """Status of a task in the workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_REVIEW = "needs_review"


class ToolType(str, Enum):
    """Available tools for agents."""
    SEARCH = "search"
    VECTOR_SEARCH = "vector_search"
    KEYWORD_SEARCH = "keyword_search"
    PATENT_SEARCH = "patent_search"
    LEGAL_SEARCH = "legal_search"
    TRANSLATE = "translate"
    SUMMARIZE = "summarize"
    EXTRACT_CLAIMS = "extract_claims"
    EXTRACT_CITATIONS = "extract_citations"
    CLASSIFY_FORMULATION = "classify_formulation"
    CLASSIFY_JURISDICTION = "classify_jurisdiction"
    CHECK_AUTHORITY = "check_authority"
    VALIDATE_CITATION = "validate_citation"
    GENERATE_ANSWER = "generate_answer"
    CRITIQUE_ANSWER = "critique_answer"
    FACT_CHECK = "fact_check"
    CALCULATE = "calculate"
    FORMAT_OUTPUT = "format_output"


@dataclass
class Tool:
    """Tool definition for agents."""
    name: ToolType
    description: str
    parameters: Dict[str, Any]
    returns: str
    requires_auth: bool = False
    timeout_seconds: float = 30.0


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_type: AgentType
    name: str
    description: str
    system_prompt: str
    tools: List[ToolType] = field(default_factory=list)
    max_iterations: int = 5
    temperature: float = 0.1
    model: Optional[str] = None
    memory_enabled: bool = True


@dataclass
class Task:
    """A task in the workflow."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    agent_type: AgentType = AgentType.PLANNER
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    assigned_agent: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """A workflow consisting of multiple tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    tasks: List[Task] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Message between agents or from user."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""  # Empty for broadcast
    content: str = ""
    message_type: str = "user"  # user, agent, system, tool_result
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(
        self,
        config: AgentConfig,
        settings: Optional[Settings] = None,
    ):
        self.config = config
        self.settings = settings or get_settings()
        self.id = f"{config.agent_type.value}_{uuid.uuid4().hex[:8]}"
        self.memory: List[AgentMessage] = []
        self.tools: Dict[ToolType, Callable] = {}
    
    @abstractmethod
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        """Execute a task and return updated task."""
        pass
    
    def add_tool(self, tool_type: ToolType, tool_func: Callable) -> None:
        """Register a tool."""
        self.tools[tool_type] = tool_func
    
    async def call_tool(
        self,
        tool_type: ToolType,
        **kwargs,
    ) -> Any:
        """Call a registered tool."""
        if tool_type not in self.tools:
            raise ValueError(f"Tool {tool_type} not registered")
        
        tool_func = self.tools[tool_type]
        try:
            if asyncio.iscoroutinefunction(tool_func):
                return await tool_func(**kwargs)
            else:
                return tool_func(**kwargs)
        except Exception as e:
            logger.error(f"Tool {tool_type} failed: {e}")
            raise
    
    def add_memory(self, message: AgentMessage) -> None:
        """Add message to agent memory."""
        self.memory.append(message)
    
    def get_memory(self, limit: int = 50) -> List[AgentMessage]:
        """Get recent memory."""
        return self.memory[-limit:]


class PlannerAgent(BaseAgent):
    """Agent responsible for planning multi-step workflows."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        """Plan a workflow for the given task."""
        query = task.input_data.get("query", "")
        task_type = task.input_data.get("task_type", "general")
        
        # Generate plan based on task type
        if task_type == "patent_analysis":
            plan = await self._plan_patent_analysis(query, context)
        elif task_type == "freedom_to_operate":
            plan = await self._plan_fto(query, context)
        elif task_type == "prior_art_search":
            plan = await self._plan_prior_art(query, context)
        elif task_type == "claim_analysis":
            plan = await self._plan_claim_analysis(query, context)
        else:
            plan = await self._plan_general(query, context)
        
        task.output_data = {
            "plan": plan,
            "estimated_steps": len(plan),
        }
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _plan_patent_analysis(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "agent": AgentType.RETRIEVER, "action": "search_patents", "params": {"query": query}},
            {"step": 2, "agent": AgentType.ANALYZER, "action": "analyze_claims", "params": {}},
            {"step": 3, "agent": AgentType.JURISDICTION_EXPERT, "action": "check_jurisdiction", "params": {}},
            {"step": 4, "agent": AgentType.FORMULATION_EXPERT, "action": "classify_formulation", "params": {}},
            {"step": 5, "agent": AgentType.WRITER, "action": "generate_report", "params": {}},
            {"step": 6, "agent": AgentType.CRITIC, "action": "review_report", "params": {}},
        ]
    
    async def _plan_fto(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "agent": AgentType.RETRIEVER, "action": "search_relevant_patents", "params": {"query": query}},
            {"step": 2, "agent": AgentType.ANALYZER, "action": "analyze_claim_scope", "params": {}},
            {"step": 3, "agent": AgentType.JURISDICTION_EXPERT, "action": "check_jurisdiction_coverage", "params": {}},
            {"step": 4, "agent": AgentType.CITATION_MANAGER, "action": "collect_citations", "params": {}},
            {"step": 5, "agent": AgentType.WRITER, "action": "generate_fto_opinion", "params": {}},
            {"step": 6, "agent": AgentType.VALIDATOR, "action": "validate_opinion", "params": {}},
        ]
    
    async def _plan_prior_art(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "agent": AgentType.RETRIEVER, "action": "search_prior_art", "params": {"query": query}},
            {"step": 2, "agent": AgentType.TRANSLATOR, "action": "translate_non_english", "params": {}},
            {"step": 3, "agent": AgentType.ANALYZER, "action": "compare_claims", "params": {}},
            {"step": 4, "agent": AgentType.WRITER, "action": "generate_prior_art_report", "params": {}},
        ]
    
    async def _plan_claim_analysis(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "agent": AgentType.RETRIEVER, "action": "get_patent_document", "params": {"query": query}},
            {"step": 2, "agent": AgentType.ANALYZER, "action": "extract_and_analyze_claims", "params": {}},
            {"step": 3, "agent": AgentType.FORMULATION_EXPERT, "action": "classify_claim_type", "params": {}},
            {"step": 4, "agent": AgentType.WRITER, "action": "generate_claim_analysis", "params": {}},
        ]
    
    async def _plan_general(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "agent": AgentType.RETRIEVER, "action": "search", "params": {"query": query}},
            {"step": 2, "agent": AgentType.ANALYZER, "action": "analyze_results", "params": {}},
            {"step": 3, "agent": AgentType.WRITER, "action": "generate_answer", "params": {}},
            {"step": 4, "agent": AgentType.CRITIC, "action": "critique_answer", "params": {}},
        ]


class RetrieverAgent(BaseAgent):
    """Agent responsible for information retrieval."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        """Execute retrieval task."""
        action = task.input_data.get("action", "search")
        query = task.input_data.get("query", "")
        
        if action == "search_patents":
            results = await self._search_patents(query, context)
        elif action == "search_relevant_patents":
            results = await self._search_relevant_patents(query, context)
        elif action == "search_prior_art":
            results = await self._search_prior_art(query, context)
        elif action == "get_patent_document":
            results = await self._get_patent_document(query, context)
        elif action == "search":
            results = await self._general_search(query, context)
        else:
            results = await self._general_search(query, context)
        
        task.output_data = {"results": results}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _search_patents(self, query: str, context: Dict[str, Any]) -> List[Document]:
        # Would call retrieval engine
        return []
    
    async def _search_relevant_patents(self, query: str, context: Dict[str, Any]) -> List[Document]:
        return []
    
    async def _search_prior_art(self, query: str, context: Dict[str, Any]) -> List[Document]:
        return []
    
    async def _get_patent_document(self, query: str, context: Dict[str, Any]) -> Optional[Document]:
        return None
    
    async def _general_search(self, query: str, context: Dict[str, Any]) -> List[Document]:
        return []


class AnalyzerAgent(BaseAgent):
    """Agent responsible for analyzing documents and claims."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "analyze")
        
        if action == "analyze_claims":
            result = await self._analyze_claims(context)
        elif action == "analyze_claim_scope":
            result = await self._analyze_claim_scope(context)
        elif action == "compare_claims":
            result = await self._compare_claims(context)
        elif action == "extract_and_analyze_claims":
            result = await self._extract_and_analyze_claims(context)
        elif action == "analyze_results":
            result = await self._analyze_results(context)
        else:
            result = await self._analyze_results(context)
        
        task.output_data = {"analysis": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _analyze_claims(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"claim_count": 0, "independent_claims": 0, "dependent_claims": 0}
    
    async def _analyze_claim_scope(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"breadth": "medium", "key_limitations": []}
    
    async def _compare_claims(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"similarity": 0.0, "differences": []}
    
    async def _extract_and_analyze_claims(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"claims": [], "analysis": {}}
    
    async def _analyze_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"summary": "Analysis complete"}


class WriterAgent(BaseAgent):
    """Agent responsible for generating reports and answers."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "generate")
        
        if action == "generate_report":
            result = await self._generate_report(context)
        elif action == "generate_fto_opinion":
            result = await self._generate_fto_opinion(context)
        elif action == "generate_prior_art_report":
            result = await self._generate_prior_art_report(context)
        elif action == "generate_claim_analysis":
            result = await self._generate_claim_analysis(context)
        elif action == "generate_answer":
            result = await self._generate_answer(context)
        else:
            result = await self._generate_answer(context)
        
        task.output_data = {"output": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _generate_report(self, context: Dict[str, Any]) -> str:
        return "Patent Analysis Report\n\n[Generated content]"
    
    async def _generate_fto_opinion(self, context: Dict[str, Any]) -> str:
        return "Freedom to Operate Opinion\n\n[Generated content]"
    
    async def _generate_prior_art_report(self, context: Dict[str, Any]) -> str:
        return "Prior Art Search Report\n\n[Generated content]"
    
    async def _generate_claim_analysis(self, context: Dict[str, Any]) -> str:
        return "Claim Analysis Report\n\n[Generated content]"
    
    async def _generate_answer(self, context: Dict[str, Any]) -> str:
        return "Answer based on retrieved information."


class CriticAgent(BaseAgent):
    """Agent responsible for reviewing and critiquing outputs."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "critique")
        
        if action == "review_report":
            result = await self._review_report(context)
        elif action == "critique_answer":
            result = await self._critique_answer(context)
        else:
            result = await self._critique_answer(context)
        
        task.output_data = {"critique": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _review_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"issues": [], "suggestions": [], "score": 0.8}
    
    async def _critique_answer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"issues": [], "suggestions": [], "score": 0.85}


class ValidatorAgent(BaseAgent):
    """Agent responsible for validating outputs."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "validate")
        
        if action == "validate_opinion":
            result = await self._validate_opinion(context)
        else:
            result = await self._validate_opinion(context)
        
        task.output_data = {"validation": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _validate_opinion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "confidence": 0.9, "checks_passed": []}


class JurisdictionExpertAgent(BaseAgent):
    """Agent with jurisdiction-specific expertise."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "check_jurisdiction")
        
        if action == "check_jurisdiction":
            result = await self._check_jurisdiction(context)
        elif action == "check_jurisdiction_coverage":
            result = await self._check_jurisdiction_coverage(context)
        else:
            result = await self._check_jurisdiction(context)
        
        task.output_data = {"jurisdiction_analysis": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _check_jurisdiction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"jurisdictions": [], "applicable_laws": []}
    
    async def _check_jurisdiction_coverage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"covered": [], "gaps": []}


class FormulationExpertAgent(BaseAgent):
    """Agent with formulation classification expertise."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "classify")
        
        if action == "classify_formulation":
            result = await self._classify_formulation(context)
        elif action == "classify_claim_type":
            result = await self._classify_claim_type(context)
        else:
            result = await self._classify_formulation(context)
        
        task.output_data = {"formulation_analysis": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _classify_formulation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"formulation_type": "unknown", "confidence": 0.0}
    
    async def _classify_claim_type(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"claim_type": "unknown", "confidence": 0.0}


class CitationManagerAgent(BaseAgent):
    """Agent responsible for managing citations."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "collect_citations")
        
        if action == "collect_citations":
            result = await self._collect_citations(context)
        else:
            result = await self._collect_citations(context)
        
        task.output_data = {"citations": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _collect_citations(self, context: Dict[str, Any]) -> List[Citation]:
        return []


class TranslatorAgent(BaseAgent):
    """Agent for translation tasks."""
    
    async def execute(self, task: Task, context: Dict[str, Any]) -> Task:
        action = task.input_data.get("action", "translate")
        
        if action == "translate_non_english":
            result = await self._translate_non_english(context)
        else:
            result = await self._translate_non_english(context)
        
        task.output_data = {"translations": result}
        task.status = TaskStatus.COMPLETED
        return task
    
    async def _translate_non_english(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"translated": [], "languages": []}


# Agent registry
AGENT_REGISTRY: Dict[AgentType, type] = {
    AgentType.PLANNER: PlannerAgent,
    AgentType.RETRIEVER: RetrieverAgent,
    AgentType.ANALYZER: AnalyzerAgent,
    AgentType.WRITER: WriterAgent,
    AgentType.CRITIC: CriticAgent,
    AgentType.VALIDATOR: ValidatorAgent,
    AgentType.JURISDICTION_EXPERT: JurisdictionExpertAgent,
    AgentType.FORMULATION_EXPERT: FormulationExpertAgent,
    AgentType.CITATION_MANAGER: CitationManagerAgent,
    AgentType.TRANSLATOR: TranslatorAgent,
}


DEFAULT_AGENT_CONFIGS = {
    AgentType.PLANNER: AgentConfig(
        agent_type=AgentType.PLANNER,
        name="Planner",
        description="Plans multi-step workflows for IP analysis tasks",
        system_prompt="You are a planning agent for IP analysis. Break down complex tasks into executable steps.",
        tools=[ToolType.SEARCH, ToolType.VECTOR_SEARCH],
    ),
    AgentType.RETRIEVER: AgentConfig(
        agent_type=AgentType.RETRIEVER,
        name="Retriever",
        description="Retrieves relevant patent and legal documents",
        system_prompt="You are a retrieval agent. Find the most relevant documents for the query.",
        tools=[ToolType.VECTOR_SEARCH, ToolType.KEYWORD_SEARCH, ToolType.PATENT_SEARCH, ToolType.LEGAL_SEARCH],
    ),
    AgentType.ANALYZER: AgentConfig(
        agent_type=AgentType.ANALYZER,
        name="Analyzer",
        description="Analyzes patent claims, documents, and search results",
        system_prompt="You are an analysis agent. Extract key information and perform comparative analysis.",
        tools=[ToolType.EXTRACT_CLAIMS, ToolType.EXTRACT_CITATIONS, ToolType.CLASSIFY_FORMULATION],
    ),
    AgentType.WRITER: AgentConfig(
        agent_type=AgentType.WRITER,
        name="Writer",
        description="Generates reports, opinions, and answers",
        system_prompt="You are a writing agent. Generate clear, well-cited IP analysis reports.",
        tools=[ToolType.GENERATE_ANSWER, ToolType.FORMAT_OUTPUT],
    ),
    AgentType.CRITIC: AgentConfig(
        agent_type=AgentType.CRITIC,
        name="Critic",
        description="Reviews and critiques generated outputs",
        system_prompt="You are a critic agent. Identify issues, gaps, and suggest improvements.",
        tools=[ToolType.CRITIQUE_ANSWER, ToolType.FACT_CHECK],
    ),
    AgentType.VALIDATOR: AgentConfig(
        agent_type=AgentType.VALIDATOR,
        name="Validator",
        description="Validates outputs for correctness and completeness",
        system_prompt="You are a validation agent. Verify citations, facts, and legal reasoning.",
        tools=[ToolType.VALIDATE_CITATION, ToolType.FACT_CHECK],
    ),
    AgentType.JURISDICTION_EXPERT: AgentConfig(
        agent_type=AgentType.JURISDICTION_EXPERT,
        name="Jurisdiction Expert",
        description="Provides jurisdiction-specific legal expertise",
        system_prompt="You are a jurisdiction expert. Apply relevant patent laws and procedures.",
        tools=[ToolType.CLASSIFY_JURISDICTION, ToolType.CHECK_AUTHORITY],
    ),
    AgentType.FORMULATION_EXPERT: AgentConfig(
        agent_type=AgentType.FORMULATION_EXPERT,
        name="Formulation Expert",
        description="Classifies and analyzes patent formulations",
        system_prompt="You are a formulation expert. Classify claim types and formulation strategies.",
        tools=[ToolType.CLASSIFY_FORMULATION],
    ),
    AgentType.CITATION_MANAGER: AgentConfig(
        agent_type=AgentType.CITATION_MANAGER,
        name="Citation Manager",
        description="Manages and validates citations",
        system_prompt="You are a citation manager. Ensure all claims are properly cited.",
        tools=[ToolType.EXTRACT_CITATIONS, ToolType.VALIDATE_CITATION],
    ),
    AgentType.TRANSLATOR: AgentConfig(
        agent_type=AgentType.TRANSLATOR,
        name="Translator",
        description="Handles translation of non-English documents",
        system_prompt="You are a translation agent. Translate patent documents accurately.",
        tools=[ToolType.TRANSLATE],
    ),
}


class OrchestrationEngine:
    """Main orchestration engine for managing agent workflows."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        agent_configs: Optional[Dict[AgentType, AgentConfig]] = None,
    ):
        self.settings = settings or get_settings()
        self.agent_configs = agent_configs or DEFAULT_AGENT_CONFIGS
        self.agents: Dict[str, BaseAgent] = {}
        self.workflows: Dict[str, Workflow] = {}
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """Create agent instances from configs."""
        for agent_type, config in self.agent_configs.items():
            agent_class = AGENT_REGISTRY.get(agent_type)
            if agent_class:
                agent = agent_class(config, self.settings)
                self.agents[agent.id] = agent
                logger.info(f"Initialized agent: {agent.id}")
    
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type."""
        for agent in self.agents.values():
            if agent.config.agent_type == agent_type:
                return agent
        return None
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        query: str,
        task_type: str = "general",
        context: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """Create a new workflow from a query."""
        # Use planner to create plan
        planner = self.get_agent(AgentType.PLANNER)
        if not planner:
            raise ValueError("Planner agent not available")
        
        plan_task = Task(
            name="Create Plan",
            description=f"Plan workflow for: {query}",
            agent_type=AgentType.PLANNER,
            input_data={"query": query, "task_type": task_type},
        )
        
        plan_task = await planner.execute(plan_task, context or {})
        
        plan = plan_task.output_data.get("plan", [])
        
        # Create tasks from plan
        tasks = []
        task_id_map = {}
        
        for step in plan:
            task = Task(
                name=step.get("action", "unknown"),
                description=f"Step {step['step']}: {step.get('action', 'unknown')}",
                agent_type=step.get("agent", AgentType.RETRIEVER),
                input_data={"action": step.get("action", ""), "query": query, **step.get("params", {})},
                dependencies=[task_id_map.get(dep) for dep in step.get("dependencies", []) if dep in task_id_map],
            )
            tasks.append(task)
            task_id_map[step.get("action", "")] = task.id
        
        workflow = Workflow(
            name=name,
            description=description,
            tasks=tasks,
            context=context or {},
        )
        
        self.workflows[workflow.id] = workflow
        return workflow
    
    async def execute_workflow(
        self,
        workflow_id: str,
        stream: bool = False,
    ) -> AsyncGenerator[Tuple[str, Task], None] | Workflow:
        """Execute a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow.status = TaskStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        
        completed_tasks: Set[str] = set()
        task_map = {t.id: t for t in workflow.tasks}
        
        while True:
            # Find runnable tasks
            runnable = []
            for task in workflow.tasks:
                if task.status == TaskStatus.PENDING:
                    deps_met = all(dep in completed_tasks for dep in task.dependencies)
                    if deps_met:
                        runnable.append(task)
            
            if not runnable:
                break
            
            # Execute runnable tasks (can parallelize independent tasks)
            for task in runnable:
                agent = self.get_agent(task.agent_type)
                if not agent:
                    task.status = TaskStatus.FAILED
                    task.error = f"No agent for type {task.agent_type}"
                    continue
                
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                task.assigned_agent = agent.id
                
                try:
                    # Prepare context with previous task outputs
                    task_context = {**workflow.context}
                    for dep_id in task.dependencies:
                        if dep_id in task_map:
                            task_context[f"task_{dep_id}_output"] = task_map[dep_id].output_data
                    
                    task = await agent.execute(task, task_context)
                    task.completed_at = datetime.utcnow()
                    completed_tasks.add(task.id)
                    
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.utcnow()
                    logger.error(f"Task {task.id} failed: {e}")
                
                if stream:
                    yield task.id, task
            
            if stream:
                # Yield control for streaming
                await asyncio.sleep(0)
        
        # Check final status
        failed = any(t.status == TaskStatus.FAILED for t in workflow.tasks)
        workflow.status = TaskStatus.FAILED if failed else TaskStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()
        
        if not stream:
            return workflow
    
    async def execute_single_task(
        self,
        agent_type: AgentType,
        action: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Execute a single task with specified agent."""
        agent = self.get_agent(agent_type)
        if not agent:
            raise ValueError(f"Agent {agent_type} not available")
        
        task = Task(
            name=action,
            agent_type=agent_type,
            input_data={"action": action, **input_data},
        )
        
        task = await agent.execute(task, context or {})
        return task
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow status."""
        return self.workflows.get(workflow_id)
    
    def register_tool(self, agent_type: AgentType, tool_type: ToolType, tool_func: Callable) -> None:
        """Register a tool for an agent type."""
        agent = self.get_agent(agent_type)
        if agent:
            agent.add_tool(tool_type, tool_func)
    
    def register_tool_for_all(self, tool_type: ToolType, tool_func: Callable) -> None:
        """Register a tool for all agents."""
        for agent in self.agents.values():
            agent.add_tool(tool_type, tool_func)


def create_orchestration_engine(
    settings: Optional[Settings] = None,
    agent_configs: Optional[Dict[AgentType, AgentConfig]] = None,
) -> OrchestrationEngine:
    """Factory to create orchestration engine."""
    return OrchestrationEngine(settings, agent_configs)