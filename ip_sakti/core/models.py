"""
IP-SAKTI Sahayak - Core Data Models
Phase 3: Data Model Implementation (from phase15-data-model)

All core entities, enums, and data structures for the legal RAG system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID, uuid4
import hashlib
import json


# ============================================================
# ENUMS
# ============================================================

class AuthorityTier(int, Enum):
    """Legal authority hierarchy tiers (1=highest)."""
    TIER_1 = 1      # Primary Legislation (Constitution, Acts, Treaties)
    TIER_2 = 2      # Subordinate Legislation (Rules, Regulations, Notifications)
    TIER_3 = 3      # Binding Judicial (Supreme Court, High Court judgments)
    TIER_4 = 4      # Quasi-Judicial/Regulatory (Tribunals, Regulatory decisions)
    TIER_5 = 5      # Official Guidance (Guidelines, FAQs, Pharmacopoeias)
    TIER_6 = 6      # Secondary Sources (Commentary, Academic, News)
    
    @property
    def weight(self) -> float:
        """Retrieval weight for this tier."""
        return {1: 1.0, 2: 0.9, 3: 0.95, 4: 0.7, 5: 0.5, 6: 0.2}[self.value]
    
    @property
    def is_binding(self) -> bool:
        return self.value <= 4
    
    @property
    def label(self) -> str:
        return {
            1: "Primary Legislation",
            2: "Subordinate Legislation", 
            3: "Binding Judicial Precedent",
            4: "Quasi-Judicial/Regulatory",
            5: "Official Guidance",
            6: "Secondary Sources"
        }[self.value]


class SourceType(str, Enum):
    """Source document types."""
    # Primary legislation
    ACT = "act"
    AMENDMENT_ACT = "amendment_act"
    ORDINANCE = "ordinance"
    CONSTITUTION = "constitution"
    TREATY = "treaty"
    PROTOCOL = "protocol"
    COP_DECISION = "cop_decision"
    
    # Subordinate legislation
    RULE = "rule"
    REGULATION = "regulation"
    NOTIFICATION = "notification"
    ORDER = "order"
    CIRCULAR = "circular"
    
    # Judicial
    SUPREME_COURT_JUDGMENT = "supreme_court_judgment"
    HIGH_COURT_JUDGMENT = "high_court_judgment"
    TRIBUNAL_ORDER = "tribunal_order"
    REGULATORY_DECISION = "regulatory_decision"
    
    # Official guidance
    GUIDELINE = "guideline"
    FAQ = "faq"
    MANUAL = "manual"
    PHARMACOPOEIA = "pharmacopoeia"
    FORMULARY = "formulary"
    
    # Registry records
    PATENT_RECORD = "patent_record"
    TRADEMARK_RECORD = "trademark_record"
    DESIGN_RECORD = "design_record"
    GI_RECORD = "gi_record"
    REGISTRY_RECORD = "registry_record"
    
    # Secondary
    ACADEMIC_ARTICLE = "academic_article"
    COMMENTARY = "commentary"
    BLOG = "blog"
    NEWS = "news"
    JOURNAL = "journal"


class JurisdictionCode(str, Enum):
    """Jurisdiction identifiers."""
    INDIA = "INDIA"
    IN = "INDIA"
    US = "US"
    EP = "EP"
    WO = "WO"
    UK = "UK"
    CN = "CN"
    JP = "JP"
    DE = "DE"
    FR = "FR"
    KR = "KR"
    INTERNATIONAL = "INTERNATIONAL"
    # Indian states/UTs
    ANDHRA_PRADESH = "IN-AP"
    ARUNACHAL_PRADESH = "IN-AR"
    ASSAM = "IN-AS"
    BIHAR = "IN-BR"
    CHHATTISGARH = "IN-CG"
    GOA = "IN-GA"
    GUJARAT = "IN-GJ"
    HARYANA = "IN-HR"
    HIMACHAL_PRADESH = "IN-HP"
    JHARKHAND = "IN-JH"
    KARNATAKA = "IN-KA"
    KERALA = "IN-KL"
    MADHYA_PRADESH = "IN-MP"
    MAHARASHTRA = "IN-MH"
    MANIPUR = "IN-MN"
    MEGHALAYA = "IN-ML"
    MIZORAM = "IN-MZ"
    NAGALAND = "IN-NL"
    ODISHA = "IN-OD"
    PUNJAB = "IN-PB"
    RAJASTHAN = "IN-RJ"
    SIKKIM = "IN-SK"
    TAMIL_NADU = "IN-TN"
    TELANGANA = "IN-TG"
    TRIPURA = "IN-TR"
    UTTAR_PRADESH = "IN-UP"
    UTTARAKHAND = "IN-UT"
    WEST_BENGAL = "IN-WB"
    DELHI = "IN-DL"
    JAMMU_KASHMIR = "IN-JK"
    LADAKH = "IN-LA"
    CHANDIGARH = "IN-CH"
    DADRA_NAGAR_HAVELI = "IN-DN"
    DAMAN_DIU = "IN-DD"
    LAKSHADWEEP = "IN-LD"
    PUDUCHERRY = "IN-PY"


class ChunkType(str, Enum):
    """Types of legal chunks."""
    SECTION = "section"
    SUBSECTION = "subsection"
    CLAUSE = "clause"
    SUBCLAUSE = "subclause"
    DEFINITION = "definition"
    TABLE = "table"
    SCHEDULE = "schedule"
    FOOTNOTE = "footnote"
    PREAMBLE = "preamble"
    AMENDMENT_NOTE = "amendment_note"
    ACT_METADATA = "act_metadata"
    REGISTRY_RECORD = "registry_record"
    CASE_HEADNOTE = "case_headnote"
    CASE_PARAGRAPH = "case_paragraph"
    TREATY_ARTICLE = "treaty_article"
    ANNEX = "annex"


class AmendmentStatus(str, Enum):
    """Amendment status of a provision."""
    ORIGINAL = "original"
    AMENDED = "amended"
    INSERTED = "inserted"
    REPEALED = "repealed"
    SUBSTITUTED = "substituted"
    MODIFIED = "modified"


class CitationType(str, Enum):
    """Types of citations within chunks."""
    INTERNAL = "internal"           # Within same document
    EXTERNAL = "external"           # Other legislation
    CASE_LAW = "case_law"           # Court judgment
    TREATY = "treaty"               # International treaty
    REGULATORY = "regulatory"       # Regulation/rule


class QueryIntent(str, Enum):
    """User query intent classification."""
    PROVISION_LOOKUP = "provision_lookup"         # "What does Section 3(d) say?"
    DEFINITION_QUERY = "definition_query"         # "Define 'invention'"
    PROCEDURE_QUERY = "procedure_query"           # "How to file a patent?"
    COMPLIANCE_CHECK = "compliance_check"         # "Is this formulation compliant?"
    CASE_LAW_SEARCH = "case_law_search"           # "Cases on Section 3(d)"
    CROSS_REFERENCE = "cross_reference"           # "What does Rule 13 refer to?"
    AMENDMENT_HISTORY = "amendment_history"       # "How has Section 3 changed?"
    JURISDICTION_COMPARE = "jurisdiction_compare" # "Patent law India vs US"
    FORMULATION_CLASSIFY = "formulation_classify" # "Classify this formulation"
    GENERAL_LEGAL = "general_legal"               # General legal question
    # Additional intents for pipeline
    PATENT_SEARCH = "patent_search"
    TRADEMARK_SEARCH = "trademark_search"
    COPYRIGHT_SEARCH = "copyright_search"
    DESIGN_SEARCH = "design_search"
    LEGAL_RESEARCH = "legal_research"
    FREEDOM_TO_OPERATE = "freedom_to_operate"
    VALIDITY_CHALLENGE = "validity_challenge"
    LICENSING = "licensing"


class UserRole(str, Enum):
    """User roles for RBAC."""
    STUDENT = "student"
    GENERAL = "general"
    PRACTITIONER = "practitioner"
    RESEARCHER = "researcher"
    REGULATOR = "regulator"
    ADMIN = "admin"


class LanguageCode(str, Enum):
    """Supported languages (ISO 639-1)."""
    EN = "en"
    HI = "hi"
    TA = "ta"
    BN = "bn"
    TE = "te"
    MR = "mr"
    GU = "gu"
    KN = "kn"
    ML = "ml"
    PA = "pa"
    OR = "or"
    AS = "as"
    UR = "ur"


# ============================================================
# CORE ENTITIES
# ============================================================

@dataclass
class HierarchyPath:
    """Legal hierarchy path for a chunk."""
    act_id: str                      # e.g., "A1970-39"
    act_short_title: str             # e.g., "Patents Act, 1970"
    act_year: Optional[int] = None
    act_number: Optional[int] = None
    chapter: Optional[str] = None
    chapter_number: Optional[str] = None
    part: Optional[str] = None
    part_number: Optional[str] = None
    section: Optional[str] = None    # e.g., "3(d)"
    subsection: Optional[str] = None # e.g., "(1)"
    clause: Optional[str] = None     # e.g., "(a)"
    subclause: Optional[str] = None  # e.g., "(i)"
    
    def to_citation_string(self) -> str:
        """Generate standard legal citation."""
        parts = [self.act_short_title]
        if self.chapter: parts.append(self.chapter)
        if self.part: parts.append(self.part)
        if self.section: parts.append(f"Section {self.section}")
        if self.subsection: parts.append(f"Subsection {self.subsection}")
        if self.clause: parts.append(f"Clause {self.clause}")
        if self.subclause: parts.append(f"Subclause {self.subclause}")
        return " → ".join(parts)
    
    def to_chunk_id_suffix(self) -> str:
        """Deterministic suffix for chunk_id."""
        parts = []
        if self.chapter: parts.append(f"ch{self.chapter_number or self.chapter}")
        if self.part: parts.append(f"pt{self.part_number or self.part}")
        if self.section: parts.append(f"s{self.section}")
        if self.subsection: parts.append(f"ss{self.subsection}")
        if self.clause: parts.append(f"cl{self.clause}")
        if self.subclause: parts.append(f"scl{self.subclause}")
        return "_".join(parts) or "root"
    
    def get_level(self) -> int:
        """Hierarchy level: 0=act, 1=chapter, 2=part, 3=section, 4=subsection, 5=clause, 6=subclause"""
        if self.subclause: return 6
        if self.clause: return 5
        if self.subsection: return 4
        if self.section: return 3
        if self.part: return 2
        if self.chapter: return 1
        return 0
    
    def is_parent_of(self, other: HierarchyPath) -> bool:
        """Check if this path is a parent of another."""
        return (self.act_id == other.act_id and
                (self.chapter is None or self.chapter == other.chapter) and
                (self.part is None or self.part == other.part) and
                (self.section is None or self.section == other.section) and
                (self.subsection is None or self.subsection == other.subsection) and
                (self.clause is None or self.clause == other.clause) and
                self.get_level() < other.get_level())


@dataclass
class SourceProvenance:
    """Provenance tracking for source documents."""
    source_id: str                   # e.g., "india_code", "ip_india"
    source_name: str                 # e.g., "India Code", "IP India"
    source_type: SourceType
    authority_tier: AuthorityTier
    jurisdiction: JurisdictionCode
    canonical_url: str
    acquired_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    parser_version: str = ""
    extraction_confidence: float = 1.0
    is_official_gazette: bool = False
    gazette_number: Optional[str] = None
    gazette_date: Optional[date] = None


@dataclass
class CitationRef:
    """Internal citation reference within a chunk."""
    cited_act: str
    cited_section: str
    cited_text: str                  # The citing text as it appears
    citation_type: CitationType
    hierarchy_path: Optional[HierarchyPath] = None
    confidence: float = 1.0


@dataclass
class LegalChunk:
    """Core chunk entity with full legal metadata."""
    # Identity
    chunk_id: str
    document_id: str
    document_version: str
    
    # Hierarchy
    hierarchy: HierarchyPath
    
    # Content
    text: str
    text_normalized: str             # For embedding (citations expanded)
    language: LanguageCode = LanguageCode.EN
    translations: Dict[LanguageCode, str] = field(default_factory=dict)
    
    # Metadata
    chunk_type: ChunkType = ChunkType.SECTION
    token_count: int = 0
    char_start: int = 0
    char_end: int = 0
    
    # Citations
    citations: List[CitationRef] = field(default_factory=list)
    
    # Versioning
    amendment_status: AmendmentStatus = AmendmentStatus.ORIGINAL
    effective_date: Optional[date] = None
    amendment_act: Optional[str] = None  # Source ID of amendment act
    
    # Provenance
    source_provenance: SourceProvenance = field(default_factory=SourceProvenance)
    
    # Embeddings (populated after indexing)
    embedding: Optional[List[float]] = None
    sparse_vector: Optional[Dict[int, float]] = None
    
    # Quality
    extraction_confidence: float = 1.0
    has_tables: bool = False
    has_footnotes: bool = False
    
    # Relationships
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = f"{self.document_id}#{self.hierarchy.to_chunk_id_suffix()}"
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.text_normalized.encode()).hexdigest()[:16]
    
    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text_normalized.encode()).hexdigest()[:16]
    
    def to_citation(self, claim_text: str = "") -> Citation:
        """Generate a complete citation from this chunk."""
        return Citation(
            legal_citation=self.hierarchy.to_citation_string(),
            source_reference=SourceReference(
                source_id=self.source_provenance.source_id,
                source_name=self.source_provenance.source_name,
                canonical_url=self.source_provenance.canonical_url,
                authority_tier=self.source_provenance.authority_tier,
                retrieved_at=self.source_provenance.acquired_at,
                content_hash=self.content_hash
            ),
            chunk_id=self.chunk_id,
            text_span=self._find_span(claim_text) if claim_text else None,
            amendment_status=self.amendment_status,
            effective_date=self.effective_date,
            amendment_act=self.amendment_act
        )
    
    def _find_span(self, claim_text: str) -> Optional[TextSpan]:
        """Find claim text span within chunk."""
        idx = self.text.find(claim_text)
        if idx >= 0:
            return TextSpan(start=idx, end=idx + len(claim_text), text=claim_text)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for indexing/storage."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_version": self.document_version,
            "hierarchy": self.hierarchy.__dict__,
            "text": self.text,
            "text_normalized": self.text_normalized,
            "language": self.language.value,
            "translations": {k.value: v for k, v in self.translations.items()},
            "chunk_type": self.chunk_type.value,
            "token_count": self.token_count,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "citations": [c.__dict__ for c in self.citations],
            "amendment_status": self.amendment_status.value,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "amendment_act": self.amendment_act,
            "source_provenance": self.source_provenance.__dict__,
            "extraction_confidence": self.extraction_confidence,
            "has_tables": self.has_tables,
            "has_footnotes": self.has_footnotes,
            "parent_chunk_id": self.parent_chunk_id,
            "child_chunk_ids": self.child_chunk_ids,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LegalChunk:
        """Deserialize from storage."""
        hierarchy = HierarchyPath(**data["hierarchy"])
        provenance = SourceProvenance(**data["source_provenance"])
        citations = [CitationRef(**c) for c in data.get("citations", [])]
        translations = {LanguageCode(k): v for k, v in data.get("translations", {}).items()}
        
        return cls(
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            document_version=data["document_version"],
            hierarchy=hierarchy,
            text=data["text"],
            text_normalized=data["text_normalized"],
            language=LanguageCode(data.get("language", "en")),
            translations=translations,
            chunk_type=ChunkType(data.get("chunk_type", "section")),
            token_count=data.get("token_count", 0),
            char_start=data.get("char_start", 0),
            char_end=data.get("char_end", 0),
            citations=citations,
            amendment_status=AmendmentStatus(data.get("amendment_status", "original")),
            effective_date=date.fromisoformat(data["effective_date"]) if data.get("effective_date") else None,
            amendment_act=data.get("amendment_act"),
            source_provenance=provenance,
            extraction_confidence=data.get("extraction_confidence", 1.0),
            has_tables=data.get("has_tables", False),
            has_footnotes=data.get("has_footnotes", False),
            parent_chunk_id=data.get("parent_chunk_id"),
            child_chunk_ids=data.get("child_chunk_ids", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


@dataclass
class DocumentVersion:
    """Document version tracking."""
    document_id: str
    version_id: str                  # Hash or timestamp
    version_label: str               # e.g., "2024 Amendment"
    effective_date: date
    amendment_act: Optional[str] = None
    amendment_type: Optional[str] = None
    changes: List[ChangeDetail] = field(default_factory=list)
    previous_version_id: Optional[str] = None
    superseded: bool = False
    source_provenance: Optional[SourceProvenance] = None


@dataclass
class ChangeDetail:
    """Detail of a specific change in an amendment."""
    hierarchy_path: HierarchyPath
    change_type: str                 # INSERTION, DELETION, SUBSTITUTION, MODIFICATION
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    change_summary: str = ""


@dataclass
class Citation:
    """Complete citation for generated answers."""
    legal_citation: str              # e.g., "Patents Act, 1970 → Section 3(d)"
    source_reference: SourceReference
    chunk_id: str
    text_span: Optional[TextSpan] = None
    amendment_status: AmendmentStatus = AmendmentStatus.ORIGINAL
    effective_date: Optional[date] = None
    amendment_act: Optional[str] = None
    
    def format_legal(self) -> str:
        """Format as legal citation."""
        parts = [self.legal_citation]
        if self.amendment_status != AmendmentStatus.ORIGINAL:
            parts.append(f"({self.amendment_status.value}")
            if self.effective_date:
                parts.append(f"effective {self.effective_date}")
            if self.amendment_act:
                parts.append(f"by {self.amendment_act}")
            parts.append(")")
        parts.append(f"Source: {self.source_reference.source_name} ({self.source_reference.canonical_url})")
        return " ".join(parts)
    
    def format_inline(self) -> str:
        """Format as inline citation [1]."""
        return f"[{self.legal_citation}]"


@dataclass
class SourceReference:
    """Source reference for citations."""
    source_id: str
    source_name: str
    canonical_url: str
    authority_tier: AuthorityTier
    retrieved_at: datetime
    content_hash: str


@dataclass
class TextSpan:
    """Text span within a chunk."""
    start: int
    end: int
    text: str


@dataclass
class AuthorityProfile:
    """Authority metadata for a source document."""
    source_id: str
    source_type: SourceType
    authority_tier: AuthorityTier
    jurisdiction_id: str
    authority_name: str
    enacting_authority: str
    publication_date: date
    gazette_number: Optional[str] = None
    gazette_date: Optional[date] = None
    is_official_gazette: bool = False
    is_binding: bool = True
    precedence_rank: int = 0
    parent_source_id: Optional[str] = None
    amendment_history: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkAuthority:
    """Authority propagated to chunk level."""
    chunk_id: str
    source_id: str
    authority_tier: AuthorityTier
    authority_weight: float
    inheritance_path: List[str]
    is_amended_version: bool = False
    amendment_date: Optional[date] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaimAuthority:
    """Authority for a generated claim."""
    claim_id: str
    primary_chunk_authority: ChunkAuthority
    supporting_chunk_authorities: List[ChunkAuthority]
    composite_tier: AuthorityTier
    composite_weight: float
    conflict_resolution: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# QUERY/RESPONSE MODELS
# ============================================================

@dataclass
class QueryRequest:
    """Incoming query request."""
    query: str
    user_id: str
    session_id: Optional[str] = None
    jurisdiction: Optional[JurisdictionCode] = None
    language: LanguageCode = LanguageCode.EN
    max_results: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)
    intent: Optional[QueryIntent] = None
    require_citations: bool = True
    stream: bool = False


@dataclass
class RetrievedChunk:
    """Retrieved chunk with scores."""
    chunk: LegalChunk
    retrieval_score: float
    authority_score: float
    combined_score: float
    rank: int
    matched_terms: List[str] = field(default_factory=list)


@dataclass
class EvidenceChunk:
    """Evidence chunk for generation."""
    chunk: LegalChunk
    relevance_score: float
    authority_score: float
    citation: Citation
    claim_support: str = ""  # What claim this supports


@dataclass
class GeneratedSegment:
    """A segment of generated answer."""
    text: str
    claims: List[Claim] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)


@dataclass
class Claim:
    """A verifiable claim in generated answer."""
    claim_id: str
    text: str
    claim_type: str
    confidence: float
    supporting_chunks: List[EvidenceChunk] = field(default_factory=list)
    authority: Optional[ClaimAuthority] = None


@dataclass
class GeneratedAnswer:
    """Complete generated answer."""
    answer_id: str
    query: str
    segments: List[GeneratedSegment]
    citations: List[Citation]
    overall_confidence: float
    jurisdiction: JurisdictionCode
    language: LanguageCode
    processing_time_ms: int
    retrieval_stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResponse:
    """Complete query response."""
    query_id: str
    answer: GeneratedAnswer
    retrieved_chunks: List[RetrievedChunk]
    intent: QueryIntent
    jurisdiction: JurisdictionCode
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# FORMULATION MODELS (Phase 14)
# ============================================================

class FormulationCategory(str, Enum):
    """Formulation classification categories."""
    HERBAL = "herbal"
    HERBO_MINERAL = "herbo_mineral"
    MINERAL = "mineral"
    ANIMAL_DERIVED = "animal_derived"
    SYNTHETIC = "synthetic"
    BIOTECH = "biotech"
    COMBINATION = "combination"


class FormulationStatus(str, Enum):
    """Regulatory status of formulation."""
    CLASSICAL = "classical"           # Classical Ayurvedic formulation
    PATENTED = "patented"             # Patented formulation
    PROPRIETARY = "proprietary"       # Proprietary/branded
    GENERIC = "generic"               # Generic
    NOTIFIED = "notified"             # Notified under Drugs & Cosmetics
    TRADITIONAL = "traditional"       # Traditional knowledge


@dataclass
class FormulationIngredient:
    """Ingredient in a formulation."""
    name: str
    botanical_name: Optional[str] = None
    part_used: Optional[str] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    percentage: Optional[float] = None
    is_active: bool = True
    source_category: Optional[str] = None  # Plant, mineral, animal


@dataclass
class Formulation:
    """Formulation entity."""
    formulation_id: str
    name: str
    category: FormulationCategory
    status: FormulationStatus
    ingredients: List[FormulationIngredient]
    indications: List[str] = field(default_factory=list)
    dosage_form: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None
    license_number: Optional[str] = None
    classical_reference: Optional[str] = None  # e.g., "Charaka Samhita, Chikitsa Sthana 5/12"
    proprietary: bool = False
    jurisdiction: JurisdictionCode = JurisdictionCode.INDIA
    authority_tier: AuthorityTier = AuthorityTier.TIER_5
    source_provenance: Optional[SourceProvenance] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================
# EXPERIMENT/EVAL MODELS (Phase 12, 11)
# ============================================================

@dataclass
class ExperimentConfig:
    """Experiment configuration."""
    experiment_id: str
    name: str
    description: str
    hypothesis: str
    variables: Dict[str, Any]  # Config variables to test
    metrics: List[str]
    dataset: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class ExperimentResult:
    """Experiment result."""
    experiment_id: str
    run_id: str
    config: ExperimentConfig
    metrics: Dict[str, float]
    artifacts: Dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """Evaluation result for a query."""
    query_id: str
    query: str
    expected_answer: Optional[str] = None
    generated_answer: Optional[GeneratedAnswer] = None
    retrieval_metrics: Dict[str, float] = field(default_factory=dict)
    generation_metrics: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_chunk_id(document_id: str, hierarchy: HierarchyPath, index: int = 0) -> str:
    """Create deterministic chunk ID."""
    suffix = hierarchy.to_chunk_id_suffix()
    if index > 0:
        suffix += f"_{index}"
    return f"{document_id}#{suffix}"


def normalize_text_for_embedding(text: str) -> str:
    """Normalize text for embedding generation."""
    # Expand common legal abbreviations
    expansions = {
        r"\bSec\.\s*": "Section ",
        r"\bS\.?\s*(\d+)": r"Section \1",
        r"\bArt\.\s*": "Article ",
        r"\bCl\.\s*": "Clause ",
        r"\bR\.\s*(\d+)": r"Rule \1",
        r"\bSch\.\s*": "Schedule ",
        r"\bPara\.\s*": "Paragraph ",
        r"\bSub-?s?ec\.\s*": "Subsection ",
        r"\bv\.\s*": "versus ",
        r"\bet seq\.": "and following",
        r"\bi\.e\.": "that is",
        r"\be\.g\.": "for example",
    }
    import re
    normalized = text
    for pattern, replacement in expansions.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Approximate token count."""
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: ~4 chars per token
        return len(text) // 4


# ============================================================
# SERIALIZATION HELPERS
# ============================================================

class DataModelEncoder(json.JSONEncoder):
    """JSON encoder for data models."""
    def default(self, obj):
        if isinstance(obj, (UUID, date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


def to_json(obj: Any) -> str:
    """Serialize to JSON."""
    return json.dumps(obj, cls=DataModelEncoder, ensure_ascii=False, indent=2)


# ============================================================
# INGESTION MODELS (for backward compatibility)
# ============================================================

class DocumentType(str, Enum):
    """Document types for ingestion."""
    PATENT = "patent"
    TRADEMARK = "trademark"
    COPYRIGHT = "copyright"
    DESIGN = "design"
    LEGAL_OPINION = "legal_opinion"
    CASE_LAW = "case_law"
    STATUTE = "statute"
    REGULATION = "regulation"
    TREATY = "treaty"
    SCHOLARLY_ARTICLE = "scholarly_article"
    ACT = "act"
    RULE = "rule"
    NOTIFICATION = "notification"
    ORDER = "order"
    CIRCULAR = "circular"
    GUIDELINE = "guideline"
    PROTOCOL = "protocol"
    REGISTRY_RECORD = "registry_record"
    PHARMACOPOEIA = "pharmacopoeia"
    FORMULARY = "formulary"


@dataclass
class DocumentMetadata:
    """Document metadata for ingestion."""
    title: str = ""
    document_type: DocumentType = DocumentType.PATENT
    jurisdiction: JurisdictionCode = JurisdictionCode.INDIA
    language: LanguageCode = LanguageCode.EN
    mime_type: Optional[str] = None
    source_path: Optional[str] = None
    version: str = "1.0"
    effective_date: Optional[date] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSource:
    """Document source information."""
    url: Optional[str] = None
    path: Optional[str] = None
    authority_tier: AuthorityTier = AuthorityTier.TIER_1
    acquired_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    size_bytes: int = 0


@dataclass
class Document:
    """Document entity for ingestion pipeline."""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    source: DocumentSource = field(default_factory=DocumentSource)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    chunks: List[Any] = field(default_factory=list)  # DocumentChunk from chunking
    content_hash: str = ""
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DocumentChunk:
    """Document chunk from ingestion/chunking."""
    id: str = field(default_factory=lambda: str(uuid4()))
    document_id: str = ""
    content: str = ""
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    authority_score: float = 0.0
    jurisdiction: Optional[JurisdictionCode] = None
    document_type: Optional[DocumentType] = None
    embedding: Optional[List[float]] = None


class IngestionStatus(str, Enum):
    """Ingestion job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class IngestionJob:
    """Ingestion job."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_url: Optional[str] = None
    source_path: Optional[str] = None
    raw_content: Optional[bytes] = None
    title: Optional[str] = None
    document_type: Optional[DocumentType] = None
    authority_tier: Optional[AuthorityTier] = None
    jurisdiction: Optional[JurisdictionCode] = None
    metadata: Optional[DocumentMetadata] = None
    options: Dict[str, Any] = field(default_factory=dict)
    status: IngestionStatus = IngestionStatus.PENDING
    error_message: Optional[str] = None
    document_id: Optional[str] = None
    chunks: List[Any] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    priority: int = 0


# Aliases for backward compatibility
Jurisdiction = JurisdictionCode
SourceAuthorityTier = AuthorityTier


class FormulationType(str, Enum):
    """Formulation type and section classification."""
    CLAIM = "claim"
    ABSTRACT = "abstract"
    DESCRIPTION = "description"
    DRAWINGS = "drawings"
    BACKGROUND = "background"
    SUMMARY = "summary"
    CLASSICAL = "classical"
    NEW_DRUG = "new_drug"
    COSMETIC = "cosmetic"
    OTHER = "other"


class TechnicalDomain(str, Enum):
    """Technical domain classification."""
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    CHEMICAL = "chemical"
    BIOTECHNOLOGY = "biotechnology"
    COMPUTER_SOFTWARE = "computer_software"
    PHARMACEUTICAL = "pharmaceutical"
    MATERIALS = "materials"
    TELECOMMUNICATIONS = "telecommunications"
    AUTOMOTIVE = "automotive"
    AEROSPACE = "aerospace"
    ENERGY = "energy"
    ENVIRONMENTAL = "environmental"


FormulationCategory = FormulationType


class RetrievalStrategy(str, Enum):
    """Retrieval strategy."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    GRAPH = "graph"


@dataclass
class Query:
    """Query model for RAG pipeline."""
    text: str
    user_id: str
    session_id: Optional[str] = None
    intent: Optional[QueryIntent] = None
    jurisdiction: JurisdictionCode = JurisdictionCode.INDIA
    language: LanguageCode = LanguageCode.EN
    max_results: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)
    require_citations: bool = True
    stream: bool = False
    query_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetrievalResult:
    """Retrieval result with chunk and scores."""
    chunk: Any  # DocumentChunk or LegalChunk
    score: float
    strategy: RetrievalStrategy
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


def from_json(json_str: str, cls: type) -> Any:
    """Deserialize from JSON."""
    data = json.loads(json_str)
    return cls.from_dict(data) if hasattr(cls, 'from_dict') else data