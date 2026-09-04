"""
IP-SAKTI Memory Architecture
Phase 19: Implements the memory architecture for conversation history,
context management, and long-term knowledge retention.
"""

import asyncio
import logging
import uuid
import json
import pickle
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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


class MemoryType(str, Enum):
    """Types of memory stores."""
    SHORT_TERM = "short_term"      # Conversation context
    LONG_TERM = "long_term"        # Persistent knowledge
    EPISODIC = "episodic"          # Task/execution history
    SEMANTIC = "semantic"          # Learned facts/patterns
    WORKING = "working"            # Active task state


class MemoryPriority(str, Enum):
    """Priority levels for memory retention."""
    CRITICAL = "critical"    # Never evict
    HIGH = "high"            # Evict last
    MEDIUM = "medium"        # Normal eviction
    LOW = "low"              # Evict first
    TEMPORARY = "temporary"  # Auto-expire


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.SHORT_TERM
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    expires_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    embedding: Optional[List[float]] = None
    
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def touch(self) -> None:
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_message: str = ""
    assistant_message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    citations: List[Citation] = field(default_factory=list)
    context_used: List[str] = field(default_factory=list)  # Memory entry IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryConfig:
    """Configuration for memory system."""
    # Capacity limits
    max_short_term_entries: int = 100
    max_long_term_entries: int = 10000
    max_episodic_entries: int = 1000
    max_working_entries: int = 50
    
    # TTL settings
    short_term_ttl_hours: int = 24
    episodic_ttl_days: int = 30
    working_ttl_hours: int = 4
    
    # Eviction policies
    eviction_policy: str = "lru"  # lru, lfu, priority, hybrid
    
    # Consolidation
    enable_consolidation: bool = True
    consolidation_interval_hours: int = 6
    min_access_for_consolidation: int = 3
    
    # Embedding
    enable_embeddings: bool = True
    embedding_dimension: int = 384
    
    # Persistence
    persist_to_disk: bool = True
    persistence_path: str = "./memory_store"
    auto_save_interval_seconds: int = 300


class MemoryStore(ABC):
    """Abstract base for memory stores."""
    
    @abstractmethod
    async def put(self, entry: MemoryEntry) -> str:
        """Store a memory entry. Returns entry ID."""
        pass
    
    @abstractmethod
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        pass
    
    @abstractmethod
    async def query(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Query memory by content."""
        pass
    
    @abstractmethod
    async def list_entries(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """List memory entries."""
        pass
    
    @abstractmethod
    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        """Clear memory entries."""
        pass


class InMemoryStore(MemoryStore):
    """In-memory implementation of memory store."""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self._stores: Dict[MemoryType, Dict[str, MemoryEntry]] = defaultdict(dict)
        self._access_order: Dict[MemoryType, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def put(self, entry: MemoryEntry) -> str:
        async with self._lock:
            # Check capacity
            store = self._stores[entry.memory_type]
            max_entries = self._get_max_entries(entry.memory_type)
            
            if len(store) >= max_entries:
                await self._evict(entry.memory_type)
            
            store[entry.id] = entry
            self._access_order[entry.memory_type].append(entry.id)
            
            # Set expiry
            if entry.expires_at is None:
                entry.expires_at = self._calculate_expiry(entry.memory_type)
            
            return entry.id
    
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        async with self._lock:
            for store in self._stores.values():
                if entry_id in store:
                    entry = store[entry_id]
                    if entry.is_expired():
                        del store[entry_id]
                        return None
                    entry.touch()
                    return entry
            return None
    
    async def delete(self, entry_id: str) -> bool:
        async with self._lock:
            for store in self._stores.values():
                if entry_id in store:
                    del store[entry_id]
                    return True
            return False
    
    async def query(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        async with self._lock:
            results = []
            types = memory_types or list(MemoryType)
            
            for mem_type in types:
                store = self._stores[mem_type]
                for entry in store.values():
                    if entry.is_expired():
                        continue
                    if tags and not tags.intersection(entry.tags):
                        continue
                    
                    # Simple text search (in production, use embeddings)
                    content_str = str(entry.content).lower()
                    if query.lower() in content_str:
                        results.append(entry)
            
            # Sort by priority and recency
            priority_order = {
                MemoryPriority.CRITICAL: 0,
                MemoryPriority.HIGH: 1,
                MemoryPriority.MEDIUM: 2,
                MemoryPriority.LOW: 3,
                MemoryPriority.TEMPORARY: 4,
            }
            results.sort(key=lambda e: (priority_order.get(e.priority, 2), -e.last_accessed.timestamp()))
            
            return results[:limit]
    
    async def list_entries(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        async with self._lock:
            results = []
            types = [memory_type] if memory_type else list(MemoryType)
            
            for mem_type in types:
                store = self._stores[mem_type]
                for entry in store.values():
                    if entry.is_expired():
                        continue
                    if tags and not tags.intersection(entry.tags):
                        continue
                    results.append(entry)
            
            results.sort(key=lambda e: e.last_accessed, reverse=True)
            return results[:limit]
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        async with self._lock:
            count = 0
            types = [memory_type] if memory_type else list(MemoryType)
            
            for mem_type in types:
                count += len(self._stores[mem_type])
                self._stores[mem_type].clear()
                self._access_order[mem_type].clear()
            
            return count
    
    def _get_max_entries(self, memory_type: MemoryType) -> int:
        limits = {
            MemoryType.SHORT_TERM: self.config.max_short_term_entries,
            MemoryType.LONG_TERM: self.config.max_long_term_entries,
            MemoryType.EPISODIC: self.config.max_episodic_entries,
            MemoryType.WORKING: self.config.max_working_entries,
            MemoryType.SEMANTIC: self.config.max_long_term_entries,
        }
        return limits.get(memory_type, 1000)
    
    def _calculate_expiry(self, memory_type: MemoryType) -> Optional[datetime]:
        now = datetime.utcnow()
        if memory_type == MemoryType.SHORT_TERM:
            return now + timedelta(hours=self.config.short_term_ttl_hours)
        elif memory_type == MemoryType.EPISODIC:
            return now + timedelta(days=self.config.episodic_ttl_days)
        elif memory_type == MemoryType.WORKING:
            return now + timedelta(hours=self.config.working_ttl_hours)
        return None  # Long-term and semantic don't expire by default
    
    async def _evict(self, memory_type: MemoryType) -> None:
        store = self._stores[memory_type]
        access_order = self._access_order[memory_type]
        
        if not store:
            return
        
        if self.config.eviction_policy == "lru":
            # Remove oldest accessed
            while access_order and access_order[0] not in store:
                access_order.popleft()
            if access_order:
                oldest = access_order.popleft()
                if oldest in store:
                    del store[oldest]
        
        elif self.config.eviction_policy == "lfu":
            # Remove least frequently used
            if store:
                lfu = min(store.values(), key=lambda e: e.access_count)
                del store[lfu.id]
        
        elif self.config.eviction_policy == "priority":
            # Remove lowest priority
            priority_order = {
                MemoryPriority.CRITICAL: 0,
                MemoryPriority.HIGH: 1,
                MemoryPriority.MEDIUM: 2,
                MemoryPriority.LOW: 3,
                MemoryPriority.TEMPORARY: 4,
            }
            if store:
                lowest = max(store.values(), key=lambda e: priority_order.get(e.priority, 2))
                del store[lowest.id]
        
        else:  # hybrid
            # Combine priority and recency
            if store:
                def eviction_score(e):
                    priority_score = {
                        MemoryPriority.CRITICAL: 0,
                        MemoryPriority.HIGH: 1,
                        MemoryPriority.MEDIUM: 2,
                        MemoryPriority.LOW: 3,
                        MemoryPriority.TEMPORARY: 4,
                    }.get(e.priority, 2)
                    recency_score = (datetime.utcnow() - e.last_accessed).total_seconds() / 3600
                    return priority_score * 10 + recency_score
                
                worst = max(store.values(), key=eviction_score)
                del store[worst.id]


class ConversationMemory:
    """Manages conversation history and context."""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore):
        self.config = config
        self.store = store
        self.current_session_id: Optional[str] = None
        self.turns: List[ConversationTurn] = []
        self._max_turns = config.max_short_term_entries
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new conversation session."""
        self.current_session_id = session_id or str(uuid.uuid4())
        self.turns = []
        return self.current_session_id
    
    def add_turn(
        self,
        user_message: str,
        assistant_message: str,
        citations: Optional[List[Citation]] = None,
        context_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """Add a conversation turn."""
        turn = ConversationTurn(
            user_message=user_message,
            assistant_message=assistant_message,
            citations=citations or [],
            context_used=context_used or [],
            metadata=metadata or {},
        )
        self.turns.append(turn)
        
        # Trim if needed
        if len(self.turns) > self._max_turns:
            self.turns = self.turns[-self._max_turns:]
        
        # Also store in memory store
        asyncio.create_task(self._persist_turn(turn))
        
        return turn
    
    async def _persist_turn(self, turn: ConversationTurn) -> None:
        entry = MemoryEntry(
            memory_type=MemoryType.SHORT_TERM,
            content={
                "type": "conversation_turn",
                "session_id": self.current_session_id,
                "turn": {
                    "user_message": turn.user_message,
                    "assistant_message": turn.assistant_message,
                    "citations": [c.__dict__ for c in turn.citations],
                    "metadata": turn.metadata,
                },
            },
            tags={"conversation", self.current_session_id or "unknown"},
            priority=MemoryPriority.HIGH,
        )
        await self.store.put(entry)
    
    def get_recent_turns(self, n: int = 10) -> List[ConversationTurn]:
        """Get recent conversation turns."""
        return self.turns[-n:]
    
    def get_context_window(self, max_tokens: int = 4000) -> List[ConversationTurn]:
        """Get conversation context within token limit."""
        # Rough estimate: 1 token ≈ 4 chars
        max_chars = max_tokens * 4
        total_chars = 0
        context = []
        
        for turn in reversed(self.turns):
            turn_chars = len(turn.user_message) + len(turn.assistant_message)
            if total_chars + turn_chars > max_chars:
                break
            context.insert(0, turn)
            total_chars += turn_chars
        
        return context
    
    def get_formatted_history(self, n: int = 5) -> str:
        """Get formatted conversation history for LLM context."""
        turns = self.get_recent_turns(n)
        lines = []
        for turn in turns:
            lines.append(f"User: {turn.user_message}")
            lines.append(f"Assistant: {turn.assistant_message}")
        return "\n".join(lines)
    
    async def search_history(self, query: str, limit: int = 5) -> List[ConversationTurn]:
        """Search conversation history."""
        results = await self.store.query(
            query=query,
            memory_types=[MemoryType.SHORT_TERM],
            tags={"conversation"},
            limit=limit,
        )
        
        turns = []
        for entry in results:
            if isinstance(entry.content, dict) and entry.content.get("type") == "conversation_turn":
                turn_data = entry.content.get("turn", {})
                turn = ConversationTurn(
                    user_message=turn_data.get("user_message", ""),
                    assistant_message=turn_data.get("assistant_message", ""),
                    metadata=turn_data.get("metadata", {}),
                )
                turns.append(turn)
        
        return turns


class WorkingMemory:
    """Working memory for active task state."""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore):
        self.config = config
        self.store = store
        self.active_task_id: Optional[str] = None
        self.task_state: Dict[str, Any] = {}
    
    def start_task(self, task_id: str, initial_state: Optional[Dict[str, Any]] = None) -> None:
        """Start a new task in working memory."""
        self.active_task_id = task_id
        self.task_state = initial_state or {}
        self.task_state["task_id"] = task_id
        self.task_state["started_at"] = datetime.utcnow().isoformat()
    
    def update_state(self, key: str, value: Any) -> None:
        """Update working memory state."""
        self.task_state[key] = value
        self.task_state["last_updated"] = datetime.utcnow().isoformat()
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from working memory."""
        return self.task_state.get(key, default)
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get full working memory state."""
        return self.task_state.copy()
    
    async def persist(self) -> None:
        """Persist working memory to store."""
        if not self.active_task_id:
            return
        
        entry = MemoryEntry(
            memory_type=MemoryType.WORKING,
            content={
                "type": "working_memory",
                "task_id": self.active_task_id,
                "state": self.task_state,
            },
            tags={"working", "task", self.active_task_id},
            priority=MemoryPriority.HIGH,
        )
        await self.store.put(entry)
    
    async def load(self, task_id: str) -> bool:
        """Load working memory for a task."""
        entries = await self.store.query(
            query=task_id,
            memory_types=[MemoryType.WORKING],
            tags={"working", "task", task_id},
            limit=1,
        )
        
        if entries:
            content = entries[0].content
            if isinstance(content, dict) and content.get("type") == "working_memory":
                self.active_task_id = task_id
                self.task_state = content.get("state", {})
                return True
        return False
    
    def clear(self) -> None:
        """Clear working memory."""
        self.active_task_id = None
        self.task_state = {}


class LongTermMemory:
    """Long-term memory for persistent knowledge."""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore):
        self.config = config
        self.store = store
    
    async def remember(
        self,
        content: Any,
        tags: Optional[Set[str]] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a long-term memory."""
        entry = MemoryEntry(
            memory_type=MemoryType.LONG_TERM,
            content=content,
            tags=tags or set(),
            priority=priority,
            metadata=metadata or {},
        )
        return await self.store.put(entry)
    
    async def recall(
        self,
        query: str,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Recall memories matching query."""
        return await self.store.query(
            query=query,
            memory_types=[MemoryType.LONG_TERM, MemoryType.SEMANTIC],
            tags=tags,
            limit=limit,
        )
    
    async def get_by_tags(
        self,
        tags: Set[str],
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Get memories by tags."""
        return await self.store.list_entries(
            memory_type=MemoryType.LONG_TERM,
            tags=tags,
            limit=limit,
        )
    
    async def forget(self, entry_id: str) -> bool:
        """Forget a specific memory."""
        return await self.store.delete(entry_id)
    
    async def consolidate_from_short_term(
        self,
        short_term_entries: List[MemoryEntry],
    ) -> int:
        """Consolidate important short-term memories to long-term."""
        consolidated = 0
        for entry in short_term_entries:
            if (entry.access_count >= self.config.min_access_for_consolidation and
                entry.priority in [MemoryPriority.CRITICAL, MemoryPriority.HIGH]):
                
                # Create long-term copy
                ltm_entry = MemoryEntry(
                    memory_type=MemoryType.LONG_TERM,
                    content=entry.content,
                    metadata={**entry.metadata, "consolidated_from": entry.id},
                    priority=entry.priority,
                    tags=entry.tags.union({"consolidated"}),
                )
                await self.store.put(ltm_entry)
                consolidated += 1
        
        return consolidated


class EpisodicMemory:
    """Episodic memory for task execution history."""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore):
        self.config = config
        self.store = store
    
    async def record_episode(
        self,
        task_name: str,
        task_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a task execution episode."""
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            content={
                "type": "episode",
                "task_name": task_name,
                "task_type": task_type,
                "input": input_data,
                "output": output_data,
                "success": success,
                "duration_seconds": duration_seconds,
            },
            tags={"episode", task_type},
            priority=MemoryPriority.MEDIUM,
            metadata=metadata or {},
        )
        return await self.store.put(entry)
    
    async def get_episodes(
        self,
        task_type: Optional[str] = None,
        success_only: bool = False,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Get episodes matching criteria."""
        tags = {"episode"}
        if task_type:
            tags.add(task_type)
        
        entries = await self.store.list_entries(
            memory_type=MemoryType.EPISODIC,
            tags=tags,
            limit=limit,
        )
        
        if success_only:
            entries = [e for e in entries if e.content.get("success", False)]
        
        return entries
    
    async def get_similar_episodes(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """Find similar past episodes."""
        # Simple similarity based on task type and input keys
        episodes = await self.get_episodes(task_type=task_type, limit=limit * 2)
        
        # Score by input similarity
        scored = []
        for ep in episodes:
            ep_input = ep.content.get("input", {})
            # Simple key overlap score
            common_keys = set(input_data.keys()) & set(ep_input.keys())
            score = len(common_keys) / max(len(input_data), 1)
            scored.append((ep, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [ep for ep, score in scored[:limit]]


class SemanticMemory:
    """Semantic memory for learned facts and patterns."""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore):
        self.config = config
        self.store = store
    
    async def learn(
        self,
        fact: str,
        category: str,
        confidence: float = 1.0,
        source: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> str:
        """Learn a new fact."""
        entry = MemoryEntry(
            memory_type=MemoryType.SEMANTIC,
            content={
                "type": "fact",
                "fact": fact,
                "category": category,
                "confidence": confidence,
                "source": source,
            },
            tags=tags or {category, "fact"},
            priority=MemoryPriority.HIGH if confidence > 0.8 else MemoryPriority.MEDIUM,
        )
        return await self.store.put(entry)
    
    async def recall_facts(
        self,
        category: Optional[str] = None,
        query: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> List[MemoryEntry]:
        """Recall learned facts."""
        tags = {"fact"}
        if category:
            tags.add(category)
        
        entries = await self.store.list_entries(
            memory_type=MemoryType.SEMANTIC,
            tags=tags,
            limit=limit * 2,
        )
        
        results = []
        for entry in entries:
            content = entry.content
            if isinstance(content, dict) and content.get("type") == "fact":
                if content.get("confidence", 0) >= min_confidence:
                    if query is None or query.lower() in content.get("fact", "").lower():
                        results.append(entry)
        
        return results[:limit]
    
    async def update_confidence(self, entry_id: str, new_confidence: float) -> bool:
        """Update confidence of a learned fact."""
        entry = await self.store.get(entry_id)
        if entry and isinstance(entry.content, dict):
            entry.content["confidence"] = new_confidence
            entry.priority = MemoryPriority.HIGH if new_confidence > 0.8 else MemoryPriority.MEDIUM
            await self.store.put(entry)  # Re-put to update
            return True
        return False


class MemoryManager:
    """Unified memory manager coordinating all memory types."""
    
    def __init__(self, config: Optional[MemoryConfig] = None, settings: Optional[Settings] = None):
        self.config = config or MemoryConfig()
        self.settings = settings or get_settings()
        
        # Core store
        self.store = InMemoryStore(self.config)
        
        # Memory subsystems
        self.conversation = ConversationMemory(self.config, self.store)
        self.working = WorkingMemory(self.config, self.store)
        self.long_term = LongTermMemory(self.config, self.store)
        self.episodic = EpisodicMemory(self.config, self.store)
        self.semantic = SemanticMemory(self.config, self.config, self.store)
        
        # Background tasks
        self._consolidation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start background memory tasks."""
        if self._running:
            return
        
        self._running = True
        
        if self.config.enable_consolidation:
            self._consolidation_task = asyncio.create_task(self._consolidation_loop())
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Memory manager started")
    
    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        
        if self._consolidation_task:
            self._consolidation_task.cancel()
            try:
                await self._consolidation_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Memory manager stopped")
    
    async def _consolidation_loop(self) -> None:
        """Periodically consolidate short-term to long-term memory."""
        while self._running:
            try:
                await asyncio.sleep(self.config.consolidation_interval_hours * 3600)
                await self._consolidate()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consolidation error: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired entries."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Every hour
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def _consolidate(self) -> None:
        """Consolidate short-term memories to long-term."""
        short_term_entries = await self.store.list_entries(
            memory_type=MemoryType.SHORT_TERM,
            limit=self.config.max_short_term_entries,
        )
        
        count = await self.long_term.consolidate_from_short_term(short_term_entries)
        if count > 0:
            logger.info(f"Consolidated {count} memories to long-term")
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries from all stores."""
        for mem_type in MemoryType:
            entries = await self.store.list_entries(memory_type=mem_type, limit=10000)
            expired = [e for e in entries if e.is_expired()]
            for entry in expired:
                await self.store.delete(entry.id)
            
            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired {mem_type} entries")
    
    def start_conversation(self, session_id: Optional[str] = None) -> str:
        """Start a new conversation."""
        return self.conversation.start_session(session_id)
    
    def add_conversation_turn(
        self,
        user_message: str,
        assistant_message: str,
        citations: Optional[List[Citation]] = None,
        context_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """Add a conversation turn."""
        return self.conversation.add_turn(
            user_message, assistant_message, citations, context_used, metadata
        )
    
    def get_conversation_context(self, max_tokens: int = 4000) -> List[ConversationTurn]:
        """Get conversation context for LLM."""
        return self.conversation.get_context_window(max_tokens)
    
    def get_conversation_history(self, n: int = 5) -> str:
        """Get formatted conversation history."""
        return self.conversation.get_formatted_history(n)
    
    async def search_conversation(self, query: str, limit: int = 5) -> List[ConversationTurn]:
        """Search conversation history."""
        return await self.conversation.search_history(query, limit)
    
    def start_working_task(self, task_id: str, initial_state: Optional[Dict[str, Any]] = None) -> None:
        """Start a working memory task."""
        self.working.start_task(task_id, initial_state)
    
    def update_working_memory(self, key: str, value: Any) -> None:
        """Update working memory."""
        self.working.update_state(key, value)
    
    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """Get working memory value."""
        return self.working.get_state(key, default)
    
    async def persist_working_memory(self) -> None:
        """Persist working memory."""
        await self.working.persist()
    
    async def load_working_memory(self, task_id: str) -> bool:
        """Load working memory for task."""
        return await self.working.load(task_id)
    
    async def remember(
        self,
        content: Any,
        tags: Optional[Set[str]] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store in long-term memory."""
        return await self.long_term.remember(content, tags, priority, metadata)
    
    async def recall(
        self,
        query: str,
        tags: Optional[Set[str]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Recall from long-term memory."""
        return await self.long_term.recall(query, tags, limit)
    
    async def record_episode(
        self,
        task_name: str,
        task_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an episodic memory."""
        return await self.episodic.record_episode(
            task_name, task_type, input_data, output_data, success, duration_seconds, metadata
        )
    
    async def get_similar_episodes(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """Get similar past episodes."""
        return await self.episodic.get_similar_episodes(task_type, input_data, limit)
    
    async def learn_fact(
        self,
        fact: str,
        category: str,
        confidence: float = 1.0,
        source: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> str:
        """Learn a fact in semantic memory."""
        return await self.semantic.learn(fact, category, confidence, source, tags)
    
    async def recall_facts(
        self,
        category: Optional[str] = None,
        query: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> List[MemoryEntry]:
        """Recall facts from semantic memory."""
        return await self.semantic.recall_facts(category, query, min_confidence, limit)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = {}
        for mem_type in MemoryType:
            entries = await self.store.list_entries(memory_type=mem_type, limit=10000)
            stats[mem_type.value] = {
                "count": len(entries),
                "expired": sum(1 for e in entries if e.is_expired()),
            }
        return stats


def create_memory_manager(
    config: Optional[MemoryConfig] = None,
    settings: Optional[Settings] = None,
) -> MemoryManager:
    """Factory to create memory manager."""
    return MemoryManager(config, settings)