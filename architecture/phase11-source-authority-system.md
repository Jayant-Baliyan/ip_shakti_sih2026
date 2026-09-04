# Phase 11: Source Authority System

## 1. Overview

The Source Authority System assigns, maintains, and propagates **authority tiers** to every legal source, document, chunk, and claim in the system. It ensures that **hierarchical legal authority** (Constitution > Act > Rules > Guidelines > Commentary) is respected throughout retrieval, generation, and citation.

### 1.1 Core Purpose

| Function | Description |
|----------|-------------|
| **Authority Classification** | Assign Tier 1-6 to every source document and chunk |
| **Authority Propagation** | Propagate authority from document → chunk → claim → citation |
| **Conflict Resolution** | Resolve conflicting provisions using authority hierarchy |
| **Authority Weighting** | Weight retrieval and generation scores by authority |
| **Provenance Tracking** | Track authority lineage for auditability |
| **Dynamic Updates** | Handle amendments, new judgments, regulatory changes |

### 1.2 Authority Tier Definition

| Tier | Category | Examples | Weight | Description |
|------|----------|----------|--------|-------------|
| **TIER_1** | **Primary Legislation** | Acts of Parliament, Constitution, Treaties (ratified) | 1.0 | Highest binding authority |
| **TIER_2** | **Subordinate Legislation** | Rules, Regulations, Notifications, Orders (gazetted) | 0.9 | Binding, derived from Tier 1 |
| **TIER_3** | **Binding Judicial** | Supreme Court judgments, High Court judgments (binding precedent) | 0.95 | Authoritative interpretation |
| **TIER_4** | **Quasi-Judicial/Regulatory** | Tribunal orders (IPAB, NGT), Regulatory decisions, Circulars | 0.7 | Binding on parties, persuasive otherwise |
| **TIER_5** | **Official Guidance** | Guidelines, FAQs, Manuals, Pharmacopoeias, Formularies | 0.5 | Non-binding but official |
| **TIER_6** | **Secondary Sources** | Law review articles, commentaries, blogs, news | 0.2 | Persuasive only, no binding force |

---

## 2. Authority Data Model

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
from datetime import date

class AuthorityTier(int, Enum):
    TIER_1 = 1    # Primary Legislation
    TIER_2 = 2    # Subordinate Legislation
    TIER_3 = 3    # Binding Judicial
    TIER_4 = 4    # Quasi-Judicial/Regulatory
    TIER_5 = 5    # Official Guidance
    TIER_6 = 6    # Secondary Sources

class SourceType(str, Enum):
    ACT = "act"
    AMENDMENT_ACT = "amendment_act"
    ORDINANCE = "ordinance"
    RULE = "rule"
    REGULATION = "regulation"
    NOTIFICATION = "notification"
    ORDER = "order"
    CIRCULAR = "circular"
    GUIDELINE = "guideline"
    FAQ = "faq"
    SUPREME_COURT_JUDGMENT = "supreme_court_judgment"
    HIGH_COURT_JUDGMENT = "high_court_judgment"
    TRIBUNAL_ORDER = "tribunal_order"
    REGULATORY_DECISION = "regulatory_decision"
    PHARMACOPOEIA = "pharmacopoeia"
    FORMULARY = "formulary"
    TREATY = "treaty"
    PROTOCOL = "protocol"
    COP_DECISION = "cop_decision"
    ACADEMIC_ARTICLE = "academic_article"
    COMMENTARY = "commentary"
    BLOG = "blog"
    NEWS = "news"

@dataclass
class AuthorityProfile:
    """Authority metadata for a source document."""
    source_id: str
    source_type: SourceType
    authority_tier: AuthorityTier
    jurisdiction_id: str
    authority_name: str              # e.g., "Parliament of India", "Supreme Court of India"
    enacting_authority: str          # Who enacted/issued
    publication_date: date
    gazette_number: Optional[str] = None
    gazette_date: Optional[date] = None
    is_official_gazette: bool = False
    is_binding: bool = True
    precedence_rank: int = 0         # Within tier (lower = higher precedence)
    parent_source_id: Optional[str] = None  # For Rules → parent Act
    amendment_history: List[str] = field(default_factory=list)  # Source IDs that amended this
    superseded_by: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

@dataclass
class ChunkAuthority:
    """Authority propagated to chunk level."""
    chunk_id: str
    source_id: str
    authority_tier: AuthorityTier
    authority_weight: float          # 0.0-1.0 (tier weight * recency * completeness)
    inheritance_path: List[str]      # [source_id, parent_source_id, ...]
    is_amended_version: bool = False
    amendment_date: Optional[date] = None
    metadata: Dict = field(default_factory=dict)

@dataclass
class ClaimAuthority:
    """Authority for a generated claim."""
    claim_id: str
    primary_chunk_authority: ChunkAuthority
    supporting_chunk_authorities: List[ChunkAuthority]
    composite_tier: AuthorityTier
    composite_weight: float
    conflict_resolution: Optional[str] = None  # How conflicts resolved
    metadata: Dict = field(default_factory=dict)
```

---

## 3. Authority Assignment Engine

### 3.1 Document-Level Authority Classification

```python
class AuthorityClassifier:
    """
    Classifies source documents into authority tiers.
    Uses deterministic rules based on source metadata.
    """
    
    # Deterministic classification rules
    CLASSIFICATION_RULES = [
        # TIER 1: Primary Legislation
        (lambda m: m.get("source_type") in ["act", "amendment_act", "ordinance", "constitution", "treaty"] 
                    and m.get("gazette_published", False), AuthorityTier.TIER_1),
        
        # TIER 2: Subordinate Legislation (gazetted)
        (lambda m: m.get("source_type") in ["rule", "regulation", "notification", "order"]
                    and m.get("gazette_published", False), AuthorityTier.TIER_2),
        
        # TIER 3: Binding Judicial
        (lambda m: m.get("source_type") in ["supreme_court_judgment"], AuthorityTier.TIER_3),
        (lambda m: m.get("source_type") in ["high_court_judgment"] 
                    and m.get("is_reported", False), AuthorityTier.TIER_3),
        
        # TIER 4: Quasi-Judicial/Regulatory
        (lambda m: m.get("source_type") in ["tribunal_order", "regulatory_decision"], AuthorityTier.TIER_4),
        (lambda m: m.get("source_type") == "circular" 
                    and m.get("issuing_authority") in ["CDSCO", "FSSAI", "NBA", "IP_INDIA"], AuthorityTier.TIER_4),
        
        # TIER 5: Official Guidance
        (lambda m: m.get("source_type") in ["guideline", "faq", "pharmacopoeia", "formulary", "manual"], AuthorityTier.TIER_5),
        (lambda m: m.get("source_type") == "circular"
                    and m.get("issuing_authority") not in ["CDSCO", "FSSAI", "NBA", "IP_INDIA"], AuthorityTier.TIER_5),
        
        # TIER 6: Secondary Sources
        (lambda m: m.get("source_type") in ["academic_article", "commentary", "blog", "news"], AuthorityTier.TIER_6),
    ]
    
    # Precedence within tier (lower = higher precedence)
    PRECEDENCE_RULES = {
        AuthorityTier.TIER_1: {
            "constitution": 1,
            "treaty": 2,
            "act": 3,
            "amendment_act": 4,
            "ordinance": 5,
        },
        AuthorityTier.TIER_2: {
            "rule": 1,
            "regulation": 2,
            "notification": 3,
            "order": 4,
        },
        AuthorityTier.TIER_3: {
            "supreme_court_judgment": 1,
            "high_court_judgment": 2,
        },
        AuthorityTier.TIER_4: {
            "tribunal_order": 1,
            "regulatory_decision": 2,
            "circular": 3,
        },
    }
    
    def classify(self, metadata: Dict) -> AuthorityProfile:
        # Apply classification rules in order
        for condition, tier in self.CLASSIFICATION_RULES:
            if condition(metadata):
                authority_tier = tier
                break
        else:
            authority_tier = AuthorityTier.TIER_6
        
        # Compute precedence rank
        source_type = metadata.get("source_type", "unknown")
        precedence = self.PRECEDENCE_RULES.get(authority_tier, {}).get(source_type, 999)
        
        return AuthorityProfile(
            source_id=metadata["source_id"],
            source_type=SourceType(source_type),
            authority_tier=authority_tier,
            jurisdiction_id=metadata["jurisdiction_id"],
            authority_name=metadata.get("authority_name", "Unknown"),
            enacting_authority=metadata.get("enacting_authority", "Unknown"),
            publication_date=metadata["publication_date"],
            gazette_number=metadata.get("gazette_number"),
            gazette_date=metadata.get("gazette_date"),
            is_official_gazette=metadata.get("gazette_published", False),
            is_binding=authority_tier.value <= 4,
            precedence_rank=precedence,
            parent_source_id=metadata.get("parent_source_id"),
            metadata=metadata
        )
```

### 3.2 Authority Propagation to Chunks

```python
class AuthorityPropagator:
    """
    Propagates authority from document to chunks with adjustments.
    """
    
    def __init__(self, classifier: AuthorityClassifier):
        self.classifier = classifier
    
    def propagate(self, source_profile: AuthorityProfile, chunks: List[EvidenceChunk]) -> List[ChunkAuthority]:
        """Assign authority to each chunk from its source document."""
        chunk_authorities = []
        
        for chunk in chunks:
            # Base authority from source
            base_tier = source_profile.authority_tier
            base_weight = self._tier_weight(base_tier)
            
            # Adjustments
            adjustments = []
            
            # 1. Recency adjustment (newer = slightly higher for same tier)
            recency_factor = self._recency_factor(source_profile.publication_date)
            adjustments.append(("recency", recency_factor))
            
            # 2. Completeness adjustment (full section vs fragment)
            completeness = self._completeness_factor(chunk)
            adjustments.append(("completeness", completeness))
            
            # 3. Amendment status
            if source_profile.superseded_by:
                adjustments.append(("superseded", 0.3))
            elif source_profile.amendment_history:
                adjustments.append(("amended", 0.9))
            
            # 4. Jurisdiction alignment (from Phase 9)
            # Handled at retrieval filter level
            
            # Compute final weight
            final_weight = base_weight
            for _, factor in adjustments:
                final_weight *= factor
            
            # Determine if this chunk represents amended version
            is_amended = bool(source_profile.amendment_history)
            amendment_date = max(
                (self._get_amendment_date(aid) for aid in source_profile.amendment_history),
                default=None
            ) if is_amended else None
            
            chunk_authorities.append(ChunkAuthority(
                chunk_id=chunk.chunk_id,
                source_id=source_profile.source_id,
                authority_tier=base_tier,
                authority_weight=min(1.0, final_weight),
                inheritance_path=[source_profile.source_id] + 
                                ([source_profile.parent_source_id] if source_profile.parent_source_id else []),
                is_amended_version=is_amended,
                amendment_date=amendment_date,
                metadata={
                    "source_type": source_profile.source_type.value,
                    "adjustments": dict(adjustments)
                }
            ))
        
        return chunk_authorities
    
    def _tier_weight(self, tier: AuthorityTier) -> float:
        return {1: 1.0, 2: 0.9, 3: 0.95, 4: 0.7, 5: 0.5, 6: 0.2}[tier.value]
    
    def _recency_factor(self, pub_date: date) -> float:
        """Slight boost for recent sources (within 5 years)."""
        years_old = (date.today() - pub_date).days / 365
        if years_old <= 1:
            return 1.02
        elif years_old <= 3:
            return 1.01
        elif years_old <= 5:
            return 1.0
        else:
            return 0.99  # Slight decay for very old sources
    
    def _completeness_factor(self, chunk: EvidenceChunk) -> float:
        """Full sections score higher than fragments."""
        if chunk.section_number and chunk.section_title:
            return 1.0
        elif chunk.section_number:
            return 0.95
        else:
            return 0.85
```

---

## 4. Authority-Weighted Retrieval

### 4.1 Retrieval Scoring with Authority

```python
class AuthorityWeightedRetrieval:
    """
    Integrates authority weights into retrieval scoring.
    """
    
    def __init__(self, authority_store: AuthorityStore):
        self.authority_store = authority_store
    
    def compute_authority_score(self, chunk_id: str, query_jurisdiction: str) -> float:
        """Compute authority score for a chunk given query jurisdiction."""
        chunk_auth = self.authority_store.get_chunk_authority(chunk_id)
        if not chunk_auth:
            return 0.5  # Default
        
        # Base authority weight
        score = chunk_auth.authority_weight
        
        # Jurisdiction match bonus
        if chunk_auth.inheritance_path:
            # Check if any authority in path matches query jurisdiction
            # This requires mapping authority_name to jurisdiction
            pass  # Handled by Phase 9 hard filter
        
        # Binding vs non-binding
        if chunk_auth.authority_tier.value <= 4:
            score *= 1.1  # Binding authority boost
        
        return min(1.0, score)
    
    def rerank_by_authority(self, results: List[RetrievalResult], query_jurisdiction: str) -> List[RetrievalResult]:
        """Re-rank retrieval results by authority-weighted score."""
        for result in results:
            auth_score = self.compute_authority_score(result.chunk_id, query_jurisdiction)
            # Combine with retrieval score (e.g., RRF score)
            result.combined_score = 0.7 * result.retrieval_score + 0.3 * auth_score
        
        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results
```

### 4.2 Authority-Aware Fusion (Phase 6 Integration)

```python
# In Phase 6 retrieval fusion:
def authority_aware_rrf(bm25_results, dense_results, authority_scores, k=60):
    """
    RRF with authority weighting.
    Authority acts as a prior that modulates reciprocal rank.
    """
    doc_scores = defaultdict(float)
    
    # BM25 contribution
    for rank, doc_id in enumerate(bm25_results):
        auth_weight = authority_scores.get(doc_id, 0.5)
        doc_scores[doc_id] += auth_weight / (k + rank + 1)
    
    # Dense contribution
    for rank, doc_id in enumerate(dense_results):
        auth_weight = authority_scores.get(doc_id, 0.5)
        doc_scores[doc_id] += auth_weight / (k + rank + 1)
    
    # Sort by combined score
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in sorted_docs]
```

---

## 5. Authority Conflict Resolution

### 5.1 Conflict Detection

```python
class AuthorityConflictDetector:
    """
    Detects conflicts between provisions of different authority tiers.
    """
    
    def detect(self, claims: List[MappedClaim]) -> List[AuthorityConflict]:
        conflicts = []
        
        # Group claims by legal proposition (semantic similarity)
        claim_groups = self._group_by_proposition(claims)
        
        for group in claim_groups:
            if len(group) <= 1:
                continue
            
            # Check for contradictory claims
            for i, claim_a in enumerate(group):
                for claim_b in group[i+1:]:
                    if self._are_contradictory(claim_a, claim_b):
                        conflicts.append(AuthorityConflict(
                            claim_a=claim_a,
                            claim_b=claim_b,
                            tier_a=claim_a.claim.authority_tier,
                            tier_b=claim_b.claim.authority_tier,
                            jurisdiction_a=claim_a.claim.jurisdiction_id,
                            jurisdiction_b=claim_b.claim.jurisdiction_id,
                            conflict_type=self._classify_conflict(claim_a, claim_b)
                        ))
        
        return conflicts
    
    def _classify_conflict(self, claim_a: MappedClaim, claim_b: MappedClaim) -> str:
        # Same jurisdiction, different tiers → Hierarchy conflict
        if claim_a.claim.jurisdiction_id == claim_b.claim.jurisdiction_id:
            if claim_a.claim.authority_tier != claim_b.claim.authority_tier:
                return "HIERARCHY"
            else:
                return "SAME_TIER_CONTRADICTION"
        
        # Different jurisdictions
        if self._is_federal_vs_state(claim_a, claim_b):
            return "FEDERAL_VS_STATE"
        if self._is_treaty_vs_domestic(claim_a, claim_b):
            return "TREATY_VS_DOMESTIC"
        
        return "CROSS_JURISDICTION"
```

### 5.2 Conflict Resolution Rules

```python
class AuthorityConflictResolver:
    """
    Resolves authority conflicts using legal hierarchy principles.
    """
    
    RESOLUTION_RULES = [
        # 1. Constitution > All
        ("CONSTITUTION_SUPREMACY",
         lambda c: c.conflict_type == "HIERARCHY" and 
                   (c.tier_a == AuthorityTier.TIER_1 and c.claim_a.metadata.get("is_constitutional")) 
                   or (c.tier_b == AuthorityTier.TIER_1 and c.claim_b.metadata.get("is_constitutional")),
         "Constitutional provision prevails"),
        
        # 2. Central Act > State Act (Union List)
        ("UNION_LIST_PREVAILS",
         lambda c: c.conflict_type == "FEDERAL_VS_STATE" and c.tier_a == c.tier_b == AuthorityTier.TIER_1
                   and c.claim_a.metadata.get("list_entry") == "UNION",
         "Central legislation on Union List prevails (Art. 246)"),
        
        # 3. Lex posterior (later amendment)
        ("LEX_POSTERIOR",
         lambda c: c.conflict_type in ["HIERARCHY", "SAME_TIER_CONTRADICTION"] 
                   and c.claim_a.metadata.get("effective_date") 
                   and c.claim_b.metadata.get("effective_date")
                   and c.claim_a.metadata["effective_date"] > c.claim_b.metadata["effective_date"],
         "Later enactment prevails"),
        
        # 4. Lex specialis
        ("LEX_SPECIALIS",
         lambda c: c.claim_a.metadata.get("specificity", 0) > c.claim_b.metadata.get("specificity", 0),
         "More specific provision prevails"),
        
        # 5. Binding > Non-binding
        ("BINDING_PREVAILS",
         lambda c: c.tier_a.value <= 4 and c.tier_b.value >= 5,
         "Binding authority prevails over guidance"),
        
        # 6. Higher court > Lower court
        ("COURT_HIERARCHY",
         lambda c: c.tier_a == c.tier_b == AuthorityTier.TIER_3
                   and c.claim_a.metadata.get("court_level") == "SUPREME"
                   and c.claim_b.metadata.get("court_level") == "HIGH",
         "Supreme Court prevails over High Court"),
        
        # 7. Specialized tribunal > General court (on specialized matter)
        ("TRIBUNAL_SPECIALIZATION",
         lambda c: c.tier_a == AuthorityTier.TIER_4 and c.tier_b == AuthorityTier.TIER_3
                   and c.claim_a.metadata.get("subject_matter") == c.claim_a.metadata.get("tribunal_jurisdiction"),
         "Specialized tribunal prevails on its jurisdiction"),
    ]
    
    def resolve(self, conflict: AuthorityConflict) -> ConflictResolution:
        for rule_name, condition, rationale in self.RESOLUTION_RULES:
            if condition(conflict):
                # Determine winner
                if "claim_a" in rationale.lower() or "central" in rationale.lower() or "supreme" in rationale.lower():
                    winner = conflict.claim_a
                    loser = conflict.claim_b
                elif "claim_b" in rationale.lower() or "state" in rationale.lower() or "high" in rationale.lower():
                    winner = conflict.claim_b
                    loser = conflict.claim_a
                else:
                    # Default: higher tier (lower number) wins
                    if conflict.tier_a.value < conflict.tier_b.value:
                        winner, loser = conflict.claim_a, conflict.claim_b
                    else:
                        winner, loser = conflict.claim_b, conflict.claim_a
                
                return ConflictResolution(
                    conflict=conflict,
                    prevailing_claim=winner,
                    overridden_claim=loser,
                    rule_applied=rule_name,
                    rationale=rationale,
                    is_manual_review=False
                )
        
        # No rule matched - escalate
        return ConflictResolution(
            conflict=conflict,
            prevailing_claim=None,
            overridden_claim=None,
            rule_applied="ESCALATE",
            rationale="No deterministic resolution rule matched",
            is_manual_review=True
        )
```

---

## 6. Authority in Generation (Phase 10 Integration)

### 6.1 Claim Authority Composition

```python
class ClaimAuthorityComposer:
    """
    Composes authority for generated claims from supporting evidence.
    """
    
    def compose(self, mapped_claim: MappedClaim) -> ClaimAuthority:
        primary = mapped_claim.claim
        supporting = mapped_claim.supporting_chunks
        
        # Get chunk authorities
        chunk_authorities = [self.authority_store.get_chunk_authority(c.chunk_id) for c in supporting]
        chunk_authorities = [ca for ca in chunk_authorities if ca]
        
        if not chunk_authorities:
            # No authority info - use claim's declared tier
            return ClaimAuthority(
                claim_id=primary.claim_id,
                primary_chunk_authority=None,
                supporting_chunk_authorities=[],
                composite_tier=primary.authority_tier,
                composite_weight=0.5
            )
        
        # Primary = highest authority tier (lowest number)
        primary_auth = min(chunk_authorities, key=lambda ca: ca.authority_tier.value)
        
        # Composite tier = primary tier
        composite_tier = primary_auth.authority_tier
        
        # Composite weight = authority-weighted average
        total_weight = sum(ca.authority_weight for ca in chunk_authorities)
        weighted_sum = sum(ca.authority_weight * self._tier_weight(ca.authority_tier) for ca in chunk_authorities)
        composite_weight = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        return ClaimAuthority(
            claim_id=primary.claim_id,
            primary_chunk_authority=primary_auth,
            supporting_chunk_authorities=chunk_authorities,
            composite_tier=composite_tier,
            composite_weight=composite_weight,
            metadata={
                "supporting_tiers": [ca.authority_tier.value for ca in chunk_authorities],
                "num_sources": len(chunk_authorities)
            }
        )
    
    def _tier_weight(self, tier: AuthorityTier) -> float:
        return {1: 1.0, 2: 0.9, 3: 0.95, 4: 0.7, 5: 0.5, 6: 0.2}[tier.value]
```

### 6.2 Authority-Aware Citation Generation

```python
class AuthorityAwareCitationGenerator:
    """
    Generates citations with full authority metadata.
    """
    
    def generate(self, claim_authority: ClaimAuthority, chunk: EvidenceChunk) -> Citation:
        # Build citation text with authority indicators
        tier_labels = {1: "Act", 2: "Rule/Reg", 3: "Judgment", 4: "Order", 5: "Guideline", 6: "Commentary"}
        
        citation_text = f"{tier_labels.get(claim_authority.composite_tier.value, 'Source')}: "
        
        if chunk.section_number:
            citation_text += f"Section {chunk.section_number}"
        if chunk.act_name:
            citation_text += f", {chunk.act_name}"
        if chunk.effective_date:
            citation_text += f" (eff. {chunk.effective_date})"
        
        # Full citation
        full_citation = self._build_full_citation(chunk, claim_authority)
        
        return Citation(
            claim_id=claim_authority.claim_id,
            chunk_ids=[chunk.chunk_id],
            citation_text=citation_text,
            full_citation=full_citation,
            jurisdiction=chunk.jurisdiction_id,
            authority=chunk.authority_id,
            authority_tier=claim_authority.composite_tier,
            source_url=chunk.source_url,
            effective_date=chunk.effective_date,
            verification_status="VERIFIED"
        )
    
    def _build_full_citation(self, chunk: EvidenceChunk, auth: ClaimAuthority) -> str:
        parts = []
        
        if chunk.section_number:
            parts.append(f"Section {chunk.section_number}")
        if chunk.section_title:
            parts.append(f"({chunk.section_title})")
        if chunk.act_name:
            parts.append(chunk.act_name)
        if chunk.document_title and chunk.document_title != chunk.act_name:
            parts.append(f"[{chunk.document_title}]")
        if chunk.gazette_number:
            parts.append(f"Gazette No. {chunk.gazette_number}")
        if chunk.gazette_date:
            parts.append(f"dated {chunk.gazette_date}")
        if chunk.effective_date:
            parts.append(f"effective {chunk.effective_date}")
        if chunk.source_url:
            parts.append(f"Available at: {chunk.source_url}")
        
        tier_desc = {1: "Primary Legislation", 2: "Subordinate Legislation", 
                     3: "Binding Judicial Precedent", 4: "Quasi-Judicial Order",
                     5: "Official Guidance", 6: "Secondary Source"}[auth.composite_tier.value]
        parts.append(f"[Authority Tier {auth.composite_tier.value}: {tier_desc}]")
        
        return "; ".join(parts)
```

---

## 7. Authority Registry & Knowledge Graph Integration

### 7.1 Authority Registry

```python
class AuthorityRegistry:
    """
    Central registry of all authority profiles.
    Backed by Knowledge Graph (Phase 7).
    """
    
    def __init__(self, kg_client: GraphDatabase):
        self.kg = kg_client
        self.cache = {}
    
    def register_source(self, profile: AuthorityProfile) -> str:
        """Register a new source in the authority registry."""
        # Store in KG
        self.kg.create_node("Source", {
            "source_id": profile.source_id,
            "source_type": profile.source_type.value,
            "authority_tier": profile.authority_tier.value,
            "jurisdiction_id": profile.jurisdiction_id,
            "authority_name": profile.authority_name,
            "enacting_authority": profile.enacting_authority,
            "publication_date": profile.publication_date.isoformat(),
            "gazette_number": profile.gazette_number,
            "gazette_date": profile.gazette_date.isoformat() if profile.gazette_date else None,
            "is_official_gazette": profile.is_official_gazette,
            "is_binding": profile.is_binding,
            "precedence_rank": profile.precedence_rank,
            "parent_source_id": profile.parent_source_id,
            "superseded_by": profile.superseded_by,
        })
        
        # Create relationships
        if profile.parent_source_id:
            self.kg.create_relationship(
                profile.source_id, profile.parent_source_id, "DERIVED_FROM"
            )
        
        for amend_id in profile.amendment_history:
            self.kg.create_relationship(
                amend_id, profile.source_id, "AMENDS"
            )
        
        if profile.superseded_by:
            self.kg.create_relationship(
                profile.source_id, profile.superseded_by, "SUPERSEDED_BY"
            )
        
        self.cache[profile.source_id] = profile
        return profile.source_id
    
    def get_source_authority(self, source_id: str) -> Optional[AuthorityProfile]:
        if source_id in self.cache:
            return self.cache[source_id]
        
        result = self.kg.query("""
            MATCH (s:Source {source_id: $id})
            RETURN s
        """, {"id": source_id})
        
        if result:
            profile = self._deserialize(result[0]["s"])
            self.cache[source_id] = profile
            return profile
        
        return None
    
    def get_chunk_authority(self, chunk_id: str) -> Optional[ChunkAuthority]:
        # Chunks inherit from source
        result = self.kg.query("""
            MATCH (c:Chunk {chunk_id: $id})-[:FROM_SOURCE]->(s:Source)
            RETURN s, c
        """, {"id": chunk_id})
        
        if result:
            source = self._deserialize(result[0]["s"])
            chunk = result[0]["c"]
            return ChunkAuthority(
                chunk_id=chunk_id,
                source_id=source["source_id"],
                authority_tier=AuthorityTier(source["authority_tier"]),
                authority_weight=chunk.get("authority_weight", 0.5),
                inheritance_path=self._get_inheritance_path(source["source_id"])
            )
        
        return None
    
    def _get_inheritance_path(self, source_id: str) -> List[str]:
        """Walk DERIVED_FROM chain to get full authority lineage."""
        path = [source_id]
        current = source_id
        
        while True:
            result = self.kg.query("""
                MATCH (s:Source {source_id: $id})-[:DERIVED_FROM]->(parent:Source)
                RETURN parent.source_id as parent_id
            """, {"id": current})
            
            if result:
                parent_id = result[0]["parent_id"]
                path.append(parent_id)
                current = parent_id
            else:
                break
        
        return path
```

### 7.2 KG Schema for Authority

```cypher
// Source nodes
(:Source {
    source_id: String,
    source_type: String,           // "act", "rule", "judgment", "guideline", etc.
    authority_tier: Integer,       // 1-6
    jurisdiction_id: String,
    authority_name: String,        // "Parliament of India", "Supreme Court"
    enacting_authority: String,    // "Central Government", "CDSCO"
    publication_date: Date,
    gazette_number: String,
    gazette_date: Date,
    is_official_gazette: Boolean,
    is_binding: Boolean,
    precedence_rank: Integer,
    superseded_by: String,
    content_hash: String
})

// Relationships
(:Source)-[:DERIVED_FROM]->(:Source)           // Rules derived from Act
(:Source)-[:AMENDS]->(:Source)                 // Amendment Act amends original
(:Source)-[:SUPERSEDED_BY]->(:Source)          // Version chain
(:Source)-[:IMPLEMENTS]->(:Source)             // Domestic law implements treaty
(:Chunk)-[:FROM_SOURCE]->(:Source)             // Chunk belongs to source
(:Chunk)-[:CITES_SECTION]->(:Section)          // Chunk cites specific section
(:Section)-[:PART_OF]->(:Source)               // Section hierarchy
```

---

## 8. Dynamic Authority Updates

### 8.1 Amendment Processing

```python
class AuthorityUpdateProcessor:
    """
    Processes amendments, new judgments, regulatory updates.
    """
    
    def process_amendment(self, amendment_source_id: str, amended_source_id: str):
        """Update authority registry when amendment occurs."""
        # 1. Register amendment source
        amendment_profile = self.classifier.classify(amendment_metadata)
        self.registry.register_source(amendment_profile)
        
        # 2. Update amended source
        amended_profile = self.registry.get_source_authority(amended_source_id)
        if amended_profile:
            amended_profile.amendment_history.append(amendment_source_id)
            amended_profile.superseded_by = amendment_source_id
            self.registry.register_source(amended_profile)  # Update
        
        # 3. Invalidate cached chunk authorities for amended source
        self._invalidate_chunk_cache(amended_source_id)
        
        # 4. Trigger re-indexing of affected chunks
        self._reindex_affected_chunks(amended_source_id)
    
    def process_new_judgment(self, judgment_metadata: Dict):
        """Register new court judgment."""
        # Determine binding vs persuasive
        court = judgment_metadata.get("court")
        is_reported = judgment_metadata.get("is_reported", False)
        
        if court == "Supreme Court":
            tier = AuthorityTier.TIER_3
        elif court.startswith("High Court") and is_reported:
            tier = AuthorityTier.TIER_3
        elif court.startswith("High Court"):
            tier = AuthorityTier.TIER_4  # Unreported HC judgment
        else:
            tier = AuthorityTier.TIER_4  # Tribunal
        
        profile = AuthorityProfile(
            source_id=judgment_metadata["source_id"],
            source_type=SourceType.SUPREME_COURT_JUDGMENT if court == "Supreme Court" 
                       else SourceType.HIGH_COURT_JUDGMENT,
            authority_tier=tier,
            jurisdiction_id=judgment_metadata["jurisdiction_id"],
            authority_name=court,
            enacting_authority=court,
            publication_date=judgment_metadata["date"],
            is_binding=tier.value <= 3,
            metadata=judgment_metadata
        )
        
        self.registry.register_source(profile)
        
        # Link to interpreted provisions
        for provision in judgment_metadata.get("interpreted_provisions", []):
            self.kg.create_relationship(
                judgment_metadata["source_id"], 
                provision, 
                "INTERPRETS"
            )
    
    def _invalidate_chunk_cache(self, source_id: str):
        """Invalidate chunk authority cache for a source."""
        # Find all chunks from this source
        chunks = self.kg.query("""
            MATCH (c:Chunk)-[:FROM_SOURCE]->(s:Source {source_id: $id})
            RETURN c.chunk_id
        """, {"id": source_id})
        
        for record in chunks:
            chunk_id = record["c.chunk_id"]
            if chunk_id in self.chunk_auth_cache:
                del self.chunk_auth_cache[chunk_id]
```

---

## 9. Authority Metrics & Monitoring

### 9.1 Authority Distribution Metrics

```python
class AuthorityMetrics:
    """
    Tracks authority distribution across corpus, retrieval, generation.
    """
    
    def compute_corpus_distribution(self) -> Dict:
        """Authority tier distribution in corpus."""
        query = """
            MATCH (s:Source)
            RETURN s.authority_tier as tier, count(s) as count
        """
        results = self.kg.query(query)
        return {r["tier"]: r["count"] for r in results}
    
    def compute_retrieval_authority(self, query_logs: List[QueryLog]) -> Dict:
        """Average authority tier of retrieved chunks."""
        tiers = []
        for log in query_logs:
            for chunk_id in log.retrieved_chunk_ids:
                auth = self.registry.get_chunk_authority(chunk_id)
                if auth:
                    tiers.append(auth.authority_tier.value)
        
        return {
            "mean_tier": sum(tiers) / len(tiers) if tiers else 0,
            "tier_distribution": Counter(tiers),
            "binding_ratio": sum(1 for t in tiers if t <= 4) / len(tiers) if tiers else 0
        }
    
    def compute_generation_authority(self, answers: List[GeneratedAnswer]) -> Dict:
        """Authority tier of claims in generated answers."""
        tiers = []
        for answer in answers:
            for seg in answer.segments:
                for claim in seg.claims:
                    auth = self.authority_store.get_claim_authority(claim.claim.claim_id)
                    if auth:
                        tiers.append(auth.composite_tier.value)
        
        return {
            "mean_tier": sum(tiers) / len(tiers) if tiers else 0,
            "tier_distribution": Counter(tiers),
            "binding_ratio": sum(1 for t in tiers if t <= 4) / len(tiers) if tiers else 0
        }
```

### 9.2 Quality Gates

| Gate | Threshold | Action |
|------|-----------|--------|
| Corpus Tier 1+2 coverage | > 60% | Alert if below |
| Retrieval binding ratio | > 80% | Alert if below |
| Generation binding ratio | > 90% | Alert if below |
| Tier 6 in top-10 retrieval | < 10% | Alert if above |
| Unresolved conflicts | 0 | Alert if > 0 |

---

## 10. Integration Points

| Phase | Integration |
|-------|-------------|
| **Phase 4** | Authority classification at ingestion |
| **Phase 5** | Chunk authority propagation |
| **Phase 6** | Authority-weighted retrieval scoring |
| **Phase 7** | KG stores authority hierarchy & relationships |
| **Phase 8** | Formulation class → typical authority sources |
| **Phase 9** | Jurisdiction → authority mapping |
| **Phase 10** | Claim authority composition, citation authority |
| **Phase 13** | Agentic decisions use authority for tool selection |
| **Phase 17** | Authority metrics in evaluation |

---

## 11. Open Research Questions

| ID | Question |
|----|----------|
| **ORQ-59** | How to handle "soft law" that becomes binding through judicial adoption? |
| **ORQ-60** | Authority tier for regulatory "circulars" that are binding in practice but not law? |
| **ORQ-61** | International tribunal decisions (WTO DSB, ICJ) - what tier? |
| **ORQ-62** | Pre-constitutional legislation authority (e.g., 1940 Act under Constitution)? |
| **ORQ-63** | State High Court vs. Central Tribunal on concurrent list matters? |
| **ORQ-64** | Dynamic authority updates: how to propagate to already-generated answers? |
| **ORQ-65** | Authority for "notified bodies" (e.g., BIS certified labs)? |

---

## 12. Implementation Checklist

- [ ] Authority tier enum and data models
- [ ] Deterministic document classifier (metadata-based)
- [ ] Authority propagation to chunks
- [ ] Authority-weighted retrieval scoring
- [ ] Conflict detection (semantic + authority)
- [ ] Conflict resolution rules (constitutional hierarchy)
- [ ] Claim authority composition
- [ ] Authority-aware citation formatting
- [ ] Authority registry (KG-backed)
- [ ] Amendment/judgment update processor
- [ ] Authority metrics computation
- [ ] Quality gates and monitoring
- [ ] Integration tests with Phases 6, 7, 10

---

## 13. Summary

| Aspect | Decision |
|--------|----------|
| **Tier System** | 6 tiers: Constitution/Act (1) → Rules (2) → SC/HC Judgments (3) → Tribunals/Regulatory (4) → Guidelines (5) → Commentary (6) |
| **Classification** | Deterministic, metadata-driven at ingestion |
| **Propagation** | Document → Chunk → Claim → Citation |
| **Retrieval** | Authority weight modulates RRF fusion (30% weight) |
| **Conflict Resolution** | Constitutional hierarchy > Lex posterior > Lex specialis > Binding > Tier |
| **Updates** | Amendment processor invalidates cache, re-indexes |
| **Monitoring** | Corpus/retrieval/generation authority distribution |

---

## 14. Next Phase: Phase 12 - Multilingual Architecture

Phase 12 will design the **Multilingual Architecture** for:
- 13+ Indian languages + English query/answer support
- Legal terminology preservation across translation
- Multilingual retrieval (bge-m3 dense + language-specific sparse)
- Citation translation with authority preservation
- Script handling (Devanagari, Tamil, Bengali, etc.)
- Evaluation across languages