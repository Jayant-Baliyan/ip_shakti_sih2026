# Phase 10: Citation-First Generation

## 1. Overview

The Citation-First Generation Engine is the **core answer generation component** that ensures **every substantive legal claim in the output is traceable to specific evidence chunks** from authoritative sources. It implements a strict pipeline: **Question → Evidence Retrieval → Claim Extraction → Claim→Evidence Mapping → Answer Composition → Citation Verification**.

### 1.1 Core Philosophy

| Principle | Implementation |
|-----------|----------------|
| **Evidence-First** | Never generate from parametric knowledge; only from retrieved evidence |
| **Citation Traceability** | Every claim → evidence chunk → section → document → authoritative source URL |
| **Abstention over Hallucination** | "I don't have sufficient authoritative evidence" > fabricated answer |
| **Claim Granularity** | Decompose complex answers into atomic, verifiable claims |
| **Authority-Aware** | Weight claims by source authority tier (Phase 11) |
| **Jurisdiction-Isolated** | Claims segregated by jurisdiction (Phase 9) |

### 1.2 Requirements

| Requirement | Description |
|-------------|-------------|
| **FR-CG-01** | Extract atomic legal claims from retrieved evidence chunks |
| **FR-CG-02** | Map every generated claim to supporting evidence chunk(s) |
| **FR-CG-03** | Compose answer from mapped claims (not from LLM knowledge) |
| **FR-CG-04** | Verify citations before output (citation → chunk match) |
| **FR-CG-05** | Abstain when evidence insufficient for a claim |
| **FR-CG-06** | Support multi-jurisdiction segmented answers (Phase 9) |
| **FR-CG-07** | Generate structured citations with authority metadata |
| **FR-CG-08** | Handle conflicting evidence with explicit attribution |
| **FR-CG-09** | Support multilingual generation with citation preservation (Phase 12) |
| **FR-CG-10** | Provide confidence scores per claim and overall answer |

| Non-Functional | Target |
|----------------|--------|
| **NFR-CG-01** | Citation precision: 100% (every claim has citation) |
| **NFR-CG-02** | Citation recall: > 95% (all relevant evidence cited) |
| **NFR-CG-03** | Hallucination rate: 0% on benchmark |
| **NFR-CG-04** | Abstention accuracy: > 90% (correctly identifies insufficient evidence) |
| **NFR-CG-05** | Generation latency: < 3s p95 |
| **NFR-CG-06** | Citation verification latency: < 500ms |

---

## 2. Pipeline Architecture

### 2.1 End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CITATION-FIRST GENERATION PIPELINE                    │
└─────────────────────────────────────────────────────────────────────────────┘

   USER QUERY
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. EVIDENCE RETRIEVAL (Phase 6 + Phase 9 Jurisdiction Filter)              │
│    Input: Query + JurisdictionContext                                       │
│    Output: Ranked Evidence Chunks (with metadata: jurisdiction, authority,  │
│             section, document, URL, content_hash, retrieval_score)         │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. CLAIM EXTRACTION                                                         │
│    Input: Evidence Chunks                                                   │
│    Process:                                                                 │
│      - LLM extracts atomic legal claims from each chunk                     │
│      - Each claim: {claim_text, claim_type, jurisdiction, authority_tier,   │
│                     source_chunk_id, confidence}                            │
│    Output: Claim Pool (deduplicated, clustered by topic)                    │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. CLAIM-TO-EVIDENCE MAPPING                                               │
│    Input: Claim Pool + Original Chunks                                      │
│    Process:                                                                 │
│      - For each claim, identify ALL supporting chunks (not just one)       │
│      - Score support strength: ENTAILS / SUPPORTS / CONTRADICTS / NEUTRAL │
│      - Resolve conflicts: higher authority tier wins                       │
│    Output: Mapped Claims {claim, supporting_chunks[], contradicting_chunks[],│
│                            net_support_score, authority_weight}            │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. ANSWER COMPOSITION                                                       │
│    Input: Mapped Claims + Query Intent + JurisdictionContext               │
│    Process:                                                                 │
│      - Select claims relevant to query intent                               │
│      - Order logically (definition → requirement → procedure → penalty)    │
│      - Generate natural language from claims ONLY                           │
│      - Insert inline citations [chunk_id] after each claim                 │
│    Output: Draft Answer with Inline Citations                               │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. CITATION VERIFICATION                                                    │
│    Input: Draft Answer + Original Chunks                                    │
│    Process:                                                                 │
│      - For each citation [chunk_id]: verify chunk exists, matches claim    │
│      - Check: chunk text actually supports claim (entailment check)        │
│      - Verify: jurisdiction matches, authority tier recorded               │
│      - Flag: missing, weak, or incorrect citations                         │
│    Output: Verified Answer OR Abstention for specific claims               │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. FINAL OUTPUT                                                             │
│    - Answer text with verified inline citations                            │
│    - Structured citation list with full metadata                           │
│    - Confidence scores (per claim + overall)                               │
│    - Abstention notices for unsupported claims                             │
│    - Jurisdiction segmentation (if multi-jurisdiction)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Models

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal
from enum import Enum
from datetime import datetime
import uuid

class ClaimType(str, Enum):
    DEFINITION = "definition"                    # "Section 3(d) defines..."
    REQUIREMENT = "requirement"                  # "License requires..."
    PROCEDURE = "procedure"                      # "Application must be filed..."
    PROHIBITION = "prohibition"                  # "No person shall..."
    PENALTY = "penalty"                          # "Punishable with..."
    EXCEPTION = "exception"                      # "This does not apply to..."
    DELEGATION = "delegation"                    # "Central Government may notify..."
    INTERPRETATION = "interpretation"            # "Court held that..."
    TIMELINE = "timeline"                        # "Within 30 days..."
    FEE = "fee"                                  # "Fee of Rs. 5000..."
    CONDITION = "condition"                      # "Subject to..."

class SupportRelation(str, Enum):
    ENTAILS = "entails"           # Chunk text logically entails claim
    SUPPORTS = "supports"         # Chunk text supports but doesn't strictly entail
    CONTRADICTS = "contradicts"   # Chunk text contradicts claim
    NEUTRAL = "neutral"           # Chunk text neither supports nor contradicts
    PARTIAL = "partial"           # Chunk partially supports (some conditions)

class AuthorityTier(int, Enum):
    TIER_1 = 1    # Official gazette: Acts, Rules, Regulations, Notifications
    TIER_2 = 2    # Official guidance: Guidelines, Circulars, FAQs from regulator
    TIER_3 = 3    # Judicial: Supreme Court, High Court judgments
    TIER_4 = 4    # Quasi-judicial: IPAB, NGT, Tribunal orders
    TIER_5 = 5    # Academic/Commentary: Law review articles, treatises
    TIER_6 = 6    # Other: Blog posts, news, unofficial sources

@dataclass
class EvidenceChunk:
    chunk_id: str
    text: str
    document_id: str
    document_title: str
    jurisdiction_id: str
    authority_id: str
    authority_tier: AuthorityTier
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    act_name: Optional[str] = None
    effective_date: Optional[str] = None
    source_url: str = ""
    content_hash: str = ""
    retrieval_score: float = 0.0
    retrieval_rank: int = 0
    metadata: Dict = field(default_factory=dict)

@dataclass
class LegalClaim:
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim_text: str = ""
    claim_type: ClaimType = ClaimType.REQUIREMENT
    jurisdiction_id: str = ""
    authority_tier: AuthorityTier = AuthorityTier.TIER_1
    source_chunk_ids: List[str] = field(default_factory=list)
    extraction_confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

@dataclass
class MappedClaim:
    claim: LegalClaim
    supporting_chunks: List[EvidenceChunk] = field(default_factory=list)
    contradicting_chunks: List[EvidenceChunk] = field(default_factory=list)
    neutral_chunks: List[EvidenceChunk] = field(default_factory=list)
    net_support_score: float = 0.0          # -1.0 to 1.0
    authority_weighted_score: float = 0.0    # Weighted by authority tier
    is_verified: bool = False
    verification_notes: str = ""

@dataclass
class Citation:
    citation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim_id: str = ""
    chunk_ids: List[str] = field(default_factory=list)
    citation_text: str = ""                  # Human-readable: "Section 3(d), Patents Act 1970"
    full_citation: str = ""                  # Full: "Section 3(d), The Patents Act, 1970 (Act 39 of 1970), as amended by the Patents (Amendment) Act, 2005"
    jurisdiction: str = ""
    authority: str = ""
    authority_tier: AuthorityTier = AuthorityTier.TIER_1
    source_url: str = ""
    effective_date: Optional[str] = None
    verification_status: Literal["VERIFIED", "WEAK", "MISSING", "CONTRADICTED"] = "VERIFIED"

@dataclass
class AnswerSegment:
    segment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    jurisdiction_id: str = ""
    content: str = ""                        # Natural language answer text
    claims: List[MappedClaim] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    confidence: float = 0.0
    abstentions: List[str] = field(default_factory=list)  # Claim IDs that couldn't be supported

@dataclass
class GeneratedAnswer:
    query: str
    query_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    segments: List[AnswerSegment] = field(default_factory=list)
    overall_confidence: float = 0.0
    jurisdiction_context: "JurisdictionContext" = None
    generation_timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    
    def get_all_citations(self) -> List[Citation]:
        all_citations = []
        for seg in self.segments:
            all_citations.extend(seg.citations)
        return all_citations
    
    def get_abstention_summary(self) -> str:
        all_abstentions = []
        for seg in self.segments:
            all_abstentions.extend(seg.abstentions)
        if not all_abstentions:
            return ""
        return f"\n\n**Note**: I don't have sufficient authoritative evidence for: {', '.join(all_abstentions)}"
```

---

## 3. Claim Extraction

### 3.1 Extraction Prompt Design

```python
CLAIM_EXTRACTION_PROMPT = """
You are a legal claim extraction specialist. Extract ATOMIC legal claims from the provided legal text chunk.

**INSTRUCTIONS:**
1. Extract ONLY claims explicitly stated in the text. Do NOT infer, generalize, or use external knowledge.
2. Each claim must be ATOMIC - a single legal proposition that can be independently verified.
3. Classify each claim by type: DEFINITION, REQUIREMENT, PROCEDURE, PROHIBITION, PENALTY, EXCEPTION, DELEGATION, INTERPRETATION, TIMELINE, FEE, CONDITION.
4. Include the exact text span from the chunk that supports the claim.
5. Note the jurisdiction and authority tier from the chunk metadata.

**CHUNK METADATA:**
- Chunk ID: {chunk_id}
- Jurisdiction: {jurisdiction_id}
- Authority: {authority_id} (Tier {authority_tier})
- Section: {section_number} - {section_title}
- Act: {act_name}
- Source URL: {source_url}

**CHUNK TEXT:**
{chunk_text}

**OUTPUT FORMAT (JSON array):**
[
  {{
    "claim_text": "Exact claim as stated in text",
    "claim_type": "REQUIREMENT",
    "supporting_span": "Exact text span from chunk that supports this claim",
    "claim_confidence": 0.95
  }}
]

**EXAMPLES:**

Input: "Section 3(d) of the Patents Act 1970 provides that the mere discovery of a new form of a known substance which does not result in the enhancement of the known efficacy of that substance is not patentable."

Output:
[
  {{
    "claim_text": "Mere discovery of a new form of a known substance is not patentable",
    "claim_type": "PROHIBITION",
    "supporting_span": "the mere discovery of a new form of a known substance which does not result in the enhancement of the known efficacy of that substance is not patentable",
    "claim_confidence": 0.98
  }},
  {{
    "claim_text": "New form must result in enhancement of known efficacy to be patentable",
    "claim_type": "CONDITION",
    "supporting_span": "which does not result in the enhancement of the known efficacy of that substance",
    "claim_confidence": 0.95
  }}
]
"""

class ClaimExtractor:
    def __init__(self, llm_client, max_claims_per_chunk: int = 10):
        self.llm = llm_client
        self.max_claims = max_claims_per_chunk
    
    def extract(self, chunk: EvidenceChunk) -> List[LegalClaim]:
        prompt = CLAIM_EXTRACTION_PROMPT.format(
            chunk_id=chunk.chunk_id,
            jurisdiction_id=chunk.jurisdiction_id,
            authority_id=chunk.authority_id,
            authority_tier=chunk.authority_tier.value,
            section_number=chunk.section_number or "N/A",
            section_title=chunk.section_title or "N/A",
            act_name=chunk.act_name or "N/A",
            source_url=chunk.source_url,
            chunk_text=chunk.text
        )
        
        response = self.llm.extract_structured(prompt, List[Dict])
        
        claims = []
        for item in response:
            claim = LegalClaim(
                claim_text=item["claim_text"],
                claim_type=ClaimType(item["claim_type"]),
                jurisdiction_id=chunk.jurisdiction_id,
                authority_tier=chunk.authority_tier,
                source_chunk_ids=[chunk.chunk_id],
                extraction_confidence=item["claim_confidence"],
                metadata={
                    "supporting_span": item["supporting_span"],
                    "source_chunk_id": chunk.chunk_id,
                    "section_number": chunk.section_number,
                    "act_name": chunk.act_name
                }
            )
            claims.append(claim)
        
        return claims
    
    def extract_batch(self, chunks: List[EvidenceChunk]) -> List[LegalClaim]:
        all_claims = []
        for chunk in chunks:
            claims = self.extract(chunk)
            all_claims.extend(claims)
        
        # Deduplicate similar claims (same text, same jurisdiction)
        deduplicated = self._deduplicate_claims(all_claims)
        return deduplicated
    
    def _deduplicate_claims(self, claims: List[LegalClaim]) -> List[LegalClaim]:
        # Group by normalized claim text + jurisdiction
        groups = {}
        for claim in claims:
            key = (claim.claim_text.lower().strip(), claim.jurisdiction_id)
            if key not in groups:
                groups[key] = claim
            else:
                # Merge chunk IDs, keep higher confidence
                existing = groups[key]
                existing.source_chunk_ids.extend(claim.source_chunk_ids)
                existing.extraction_confidence = max(existing.extraction_confidence, claim.extraction_confidence)
        
        return list(groups.values())
```

### 3.2 Claim Type Definitions

| Claim Type | Legal Function | Example |
|------------|----------------|---------|
| **DEFINITION** | Defines a term | "Patented article means..." |
| **REQUIREMENT** | Mandates action/condition | "Application shall be accompanied by..." |
| **PROCEDURE** | Describes process steps | "The Controller shall examine..." |
| **PROHIBITION** | Forbids action | "No person shall manufacture..." |
| **PENALTY** | Specifies punishment | "Punishable with imprisonment..." |
| **EXCEPTION** | Carves out exclusion | "This section does not apply to..." |
| **DELEGATION** | Grants rulemaking power | "Central Government may by notification..." |
| **INTERPRETATION** | Judicial construction | "Court held that Section 3(d)..." |
| **TIMELINE** | Specifies deadline | "Within 30 days from..." |
| **FEE** | Specifies fee amount | "Fee of Rs. 10,000 shall be paid..." |
| **CONDITION** | Conditional requirement | "Subject to the provisions of..." |

---

## 4. Claim-to-Evidence Mapping

### 4.1 Support Scoring

```python
class ClaimEvidenceMapper:
    """
    Maps claims to ALL supporting evidence chunks and scores support strength.
    """
    
    def __init__(self, llm_client, entailment_model=None):
        self.llm = llm_client
        self.entailment_model = entailment_model  # Optional: cross-encoder for entailment
    
    def map(self, claims: List[LegalClaim], chunks: List[EvidenceChunk]) -> List[MappedClaim]:
        mapped = []
        
        for claim in claims:
            # 1. Find all chunks that could relate (same jurisdiction, similar topics)
            candidate_chunks = self._find_candidate_chunks(claim, chunks)
            
            # 2. Score each candidate for support relation
            supporting = []
            contradicting = []
            neutral = []
            
            for chunk in candidate_chunks:
                relation, score = self._score_support(claim, chunk)
                
                if relation == SupportRelation.ENTAILS or relation == SupportRelation.SUPPORTS:
                    supporting.append((chunk, score, relation))
                elif relation == SupportRelation.CONTRADICTS:
                    contradicting.append((chunk, score))
                else:
                    neutral.append(chunk)
            
            # 3. Compute net support score
            net_score = self._compute_net_score(supporting, contradicting)
            
            # 4. Compute authority-weighted score
            auth_score = self._compute_authority_score(supporting, contradicting)
            
            mapped.append(MappedClaim(
                claim=claim,
                supporting_chunks=[c for c, s, r in supporting],
                contradicting_chunks=[c for c, s in contradicting],
                neutral_chunks=neutral,
                net_support_score=net_score,
                authority_weighted_score=auth_score,
                is_verified=False
            ))
        
        return mapped
    
    def _score_support(self, claim: LegalClaim, chunk: EvidenceChunk) -> Tuple[SupportRelation, float]:
        """Score how well chunk supports claim."""
        
        # Quick check: same chunk that extracted claim
        if chunk.chunk_id in claim.source_chunk_ids:
            return SupportRelation.ENTAILS, 1.0
        
        # Use LLM for entailment check
        prompt = f"""
        Determine the relationship between this CLAIM and CHUNK:
        
        CLAIM: {claim.claim_text}
        CLAIM TYPE: {claim.claim_type.value}
        
        CHUNK (from {chunk.jurisdiction_id}, {chunk.authority_id} Tier {chunk.authority_tier.value}):
        {chunk.text}
        
        CLASSIFY as one of:
        - ENTAILS: Chunk text logically entails the claim (claim necessarily true if chunk true)
        - SUPPORTS: Chunk text supports the claim but doesn't strictly entail it
        - CONTRADICTS: Chunk text contradicts the claim
        - NEUTRAL: Chunk text neither supports nor contradicts
        - PARTIAL: Chunk partially supports (some conditions match, others don't)
        
        Also provide confidence 0.0-1.0.
        
        Return JSON: {{"relation": "...", "confidence": 0.0}}
        """
        
        result = self.llm.extract_structured(prompt, Dict)
        return SupportRelation(result["relation"]), result["confidence"]
    
    def _compute_net_score(self, supporting, contradicting) -> float:
        if not supporting and not contradicting:
            return 0.0
        
        support_weight = sum(s for _, s, _ in supporting)
        contradict_weight = sum(s for _, s in contradicting)
        
        total = support_weight + contradict_weight
        if total == 0:
            return 0.0
        
        return (support_weight - contradict_weight) / total
    
    def _compute_authority_score(self, supporting, contradicting) -> float:
        """Weight by authority tier (Tier 1 = highest weight)."""
        tier_weights = {1: 1.0, 2: 0.8, 3: 0.9, 4: 0.7, 5: 0.4, 6: 0.2}
        
        support_score = 0.0
        for chunk, conf, rel in supporting:
            weight = tier_weights.get(chunk.authority_tier.value, 0.5)
            support_score += conf * weight
        
        contradict_score = 0.0
        for chunk, conf in contradicting:
            weight = tier_weights.get(chunk.authority_tier.value, 0.5)
            contradict_score += conf * weight
        
        total = support_score + contradict_score
        if total == 0:
            return 0.0
        
        return (support_score - contradict_score) / total
```

### 4.2 Conflict Resolution in Mapping

```python
class ClaimConflictResolver:
    """
    Resolves conflicts between claims from different sources/jurisdictions.
    """
    
    def resolve(self, mapped_claims: List[MappedClaim]) -> List[MappedClaim]:
        # Group claims by semantic similarity (same legal proposition)
        claim_groups = self._group_similar_claims(mapped_claims)
        
        resolved = []
        for group in claim_groups:
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Multiple claims on same proposition - resolve
                resolved_claim = self._resolve_claim_group(group)
                resolved.append(resolved_claim)
        
        return resolved
    
    def _resolve_claim_group(self, group: List[MappedClaim]) -> MappedClaim:
        """
        Resolution priority:
        1. Higher authority tier wins
        2. More recent version wins (temporal)
        3. More specific provision wins (lex specialis)
        4. Primary jurisdiction wins (Phase 9)
        5. If still tied: mark as CONFLICTED, present both views
        """
        # Sort by resolution criteria
        sorted_claims = sorted(group, key=lambda mc: (
            mc.claim.authority_tier.value,           # Lower tier = higher authority
            -self._get_effective_date(mc).toordinal() if self._get_effective_date(mc) else 0,
            -mc.claim.metadata.get("specificity", 0),
            -mc.authority_weighted_score
        ))
        
        winner = sorted_claims[0]
        
        # Check if significant conflict remains
        for other in sorted_claims[1:]:
            if other.authority_weighted_score > 0.7 * winner.authority_weighted_score:
                # Significant competing view - mark as conflicted
                winner.verification_notes = f"CONFLICT: Competing view from {other.claim.jurisdiction_id} (score: {other.authority_weighted_score:.2f})"
                winner.contradicting_chunks.extend(other.supporting_chunks)
        
        return winner
```

---

## 5. Answer Composition

### 5.1 Composition Strategy

```python
class AnswerComposer:
    """
    Composes natural language answer from mapped claims.
    ONLY uses claims - never parametric knowledge.
    """
    
    CLAIM_ORDERING = [
        ClaimType.DEFINITION,      # First: define terms
        ClaimType.REQUIREMENT,     # Then: what is required
        ClaimType.CONDITION,       # Conditions on requirements
        ClaimType.EXCEPTION,       # Exceptions
        ClaimType.PROCEDURE,       # Procedures
        ClaimType.TIMELINE,        # Deadlines
        ClaimType.FEE,             # Fees
        ClaimType.DELEGATION,      # Delegated powers
        ClaimType.PROHIBITION,     # Prohibitions
        ClaimType.PENALTY,         # Penalties
        ClaimType.INTERPRETATION,  # Judicial interpretations
    ]
    
    def compose(self, mapped_claims: List[MappedClaim], query: str, 
                jurisdiction_ctx: JurisdictionContext) -> List[AnswerSegment]:
        
        # Group by jurisdiction
        claims_by_jur = self._group_by_jurisdiction(mapped_claims)
        
        segments = []
        for jur_id, claims in claims_by_jur.items():
            # Filter claims relevant to query intent
            relevant_claims = self._filter_relevant_claims(claims, query)
            
            # Order claims logically
            ordered_claims = self._order_claims(relevant_claims)
            
            # Generate segment
            segment = self._generate_segment(query, ordered_claims, jur_id)
            segments.append(segment)
        
        return segments
    
    def _generate_segment(self, query: str, claims: List[MappedClaim], 
                          jurisdiction: str) -> AnswerSegment:
        # Build prompt with ONLY the claims as source material
        claims_text = self._format_claims_for_prompt(claims)
        
        prompt = f"""
        You are a legal assistant. Generate an answer to the query using ONLY the provided claims.
        DO NOT use any external knowledge. If a claim is not in the list, do not include it.
        
        QUERY: {query}
        JURISDICTION: {jurisdiction}
        
        AVAILABLE CLAIMS (each with supporting evidence):
        {claims_text}
        
        INSTRUCTIONS:
        1. Write a clear, well-structured answer addressing the query.
        2. After EVERY substantive legal statement, insert inline citation [CLAIM_ID].
        3. Use claim IDs exactly as provided (e.g., [C1], [C2]).
        4. If claims contradict, present both views with citations.
        5. If insufficient claims to answer, state what is missing.
        6. Use professional legal language appropriate for the jurisdiction.
        
        OUTPUT FORMAT:
        {{
            "content": "Answer text with [CLAIM_ID] citations",
            "claim_ids_used": ["C1", "C2", ...],
            "confidence": 0.85
        }}
        """
        
        result = self.llm.extract_structured(prompt, Dict)
        
        # Map claim IDs to actual claims and citations
        used_claims = [c for c in claims if c.claim.claim_id in result["claim_ids_used"]]
        citations = self._build_citations(used_claims)
        
        # Identify abstentions (query aspects not covered)
        abstentions = self._identify_abstentions(query, used_claims)
        
        return AnswerSegment(
            jurisdiction_id=jurisdiction,
            content=result["content"],
            claims=used_claims,
            citations=citations,
            confidence=result["confidence"],
            abstentions=abstentions
        )
    
    def _format_claims_for_prompt(self, claims: List[MappedClaim]) -> str:
        lines = []
        for i, mc in enumerate(claims):
            claim = mc.claim
            lines.append(f"[C{i+1}] ({claim.claim_type.value}, Tier {claim.authority_tier.value}, "
                        f"Support: {mc.net_support_score:.2f}): {claim.claim_text}")
            # Show supporting chunk references
            chunk_refs = ", ".join(mc.claim.source_chunk_ids)
            lines.append(f"     Source chunks: {chunk_refs}")
        return "\n".join(lines)
```

### 5.2 Jurisdiction-Segmented Composition

```python
class MultiJurisdictionComposer(AnswerComposer):
    """
    Handles multi-jurisdiction queries with explicit segmentation.
    """
    
    def compose(self, mapped_claims: List[MappedClaim], query: str,
                jurisdiction_ctx: JurisdictionContext) -> List[AnswerSegment]:
        
        segments = super().compose(mapped_claims, query, jurisdiction_ctx)
        
        # If multi-jurisdiction, add comparison segment
        if jurisdiction_ctx.requires_multi_jurisdiction_answer():
            comparison_segment = self._generate_comparison_segment(
                segments, query, jurisdiction_ctx
            )
            segments.append(comparison_segment)
        
        return segments
    
    def _generate_comparison_segment(self, segments: List[AnswerSegment], 
                                     query: str, ctx: JurisdictionContext) -> AnswerSegment:
        # Build comparison from segments
        comparison_prompt = f"""
        Generate a comparative analysis of the following jurisdiction-specific answers.
        
        QUERY: {query}
        
        JURISDICTION ANSWERS:
        """
        for seg in segments:
            comparison_prompt += f"\n--- {seg.jurisdiction_id} ---\n{seg.content}\n"
        
        comparison_prompt += """
        
        INSTRUCTIONS:
        1. Create a structured comparison highlighting key similarities and differences.
        2. Focus on: requirements, procedures, timelines, penalties, exceptions.
        3. Use a table format for easy comparison.
        4. Cite specific claims from each jurisdiction using their claim IDs.
        5. Note any harmonization or conflict between regimes.
        
        OUTPUT: {{"content": "...", "confidence": 0.8}}
        """
        
        result = self.llm.extract_structured(comparison_prompt, Dict)
        
        return AnswerSegment(
            jurisdiction_id="MULTI_JURISDICTION_COMPARISON",
            content=result["content"],
            claims=[],
            citations=[],
            confidence=result["confidence"],
            abstentions=[]
        )
```

---

## 6. Citation Verification

### 6.1 Verification Process

```python
class CitationVerifier:
    """
    Verifies every citation in the generated answer before output.
    This is the FINAL GATE - no answer passes without verification.
    """
    
    def __init__(self, chunk_store: ChunkStore, entailment_model=None):
        self.chunk_store = chunk_store
        self.entailment_model = entailment_model
    
    def verify(self, answer: GeneratedAnswer, chunks: List[EvidenceChunk]) -> GeneratedAnswer:
        chunk_map = {c.chunk_id: c for c in chunks}
        
        all_verified = True
        for segment in answer.segments:
            for citation in segment.citations:
                verification = self._verify_citation(citation, chunk_map)
                citation.verification_status = verification.status
                citation.verification_notes = verification.notes
                
                if verification.status != "VERIFIED":
                    all_verified = False
                    # Mark associated claims as unverified
                    for claim in segment.claims:
                        if claim.claim.claim_id == citation.claim_id:
                            claim.is_verified = False
                            claim.verification_notes = verification.notes
        
        # Recompute confidence based on verification
        answer.overall_confidence = self._compute_overall_confidence(answer)
        
        # Add abstentions for failed verifications
        self._add_verification_abstentions(answer)
        
        return answer
    
    def _verify_citation(self, citation: Citation, chunk_map: Dict[str, EvidenceChunk]) -> VerificationResult:
        # 1. Check all chunk IDs exist
        missing_chunks = [cid for cid in citation.chunk_ids if cid not in chunk_map]
        if missing_chunks:
            return VerificationResult("MISSING", f"Chunks not found: {missing_chunks}")
        
        # 2. Check jurisdiction match
        chunk_jurisdictions = {chunk_map[cid].jurisdiction_id for cid in citation.chunk_ids}
        if len(chunk_jurisdictions) > 1:
            return VerificationResult("WEAK", f"Multiple jurisdictions in citation: {chunk_jurisdictions}")
        if citation.jurisdiction not in chunk_jurisdictions:
            return VerificationResult("WEAK", f"Jurisdiction mismatch: citation={citation.jurisdiction}, chunks={chunk_jurisdictions}")
        
        # 3. Entailment check: does chunk text actually support claim?
        claim_text = self._get_claim_text(citation.claim_id)
        for chunk_id in citation.chunk_ids:
            chunk = chunk_map[chunk_id]
            entails = self._check_entailment(claim_text, chunk.text)
            if not entails:
                return VerificationResult("WEAK", f"Chunk {chunk_id} does not entail claim")
        
        # 4. Authority tier consistency
        tiers = {chunk_map[cid].authority_tier for cid in citation.chunk_ids}
        if len(tiers) > 1:
            return VerificationResult("WEAK", f"Mixed authority tiers: {tiers}")
        
        return VerificationResult("VERIFIED", "All checks passed")
    
    def _check_entailment(self, claim: str, chunk_text: str) -> bool:
        if self.entailment_model:
            score = self.entailment_model.predict(claim, chunk_text)
            return score > 0.7
        
        # Fallback: LLM-based check
        prompt = f"""
        Does the CHUNK text ENTAIL the CLAIM? (Claim must be necessarily true if chunk is true)
        
        CLAIM: {claim}
        CHUNK: {chunk_text}
        
        Answer YES or NO only.
        """
        result = self.llm.generate(prompt).strip().upper()
        return result == "YES"
```

### 6.2 Verification Outcomes

| Status | Meaning | Action |
|--------|---------|--------|
| **VERIFIED** | Chunk exists, jurisdiction matches, entails claim | Include in final answer |
| **WEAK** | Chunk exists but support is partial/indirect | Include with reduced confidence, flag |
| **MISSING** | Referenced chunk not found | Remove citation, mark claim as unsupported |
| **CONTRADICTED** | Chunk contradicts claim | Remove claim, add abstention notice |

---

## 7. Confidence Calculation

### 7.1 Multi-Signal Confidence Model

```python
class ConfidenceCalculator:
    """
    Computes confidence scores at claim, segment, and answer level.
    """
    
    def compute_claim_confidence(self, claim: MappedClaim) -> float:
        signals = {
            "extraction": claim.claim.extraction_confidence,           # LLM extraction confidence
            "net_support": max(0, claim.net_support_score),            # Evidence support (-1 to 1)
            "authority_weight": claim.authority_weighted_score,        # Authority-weighted support
            "chunk_count": min(1.0, len(claim.supporting_chunks) / 3), # More chunks = more confidence
            "tier_bonus": self._tier_bonus(claim.claim.authority_tier),# Tier 1 bonus
            "verification": 1.0 if claim.is_verified else 0.5,         # Verification status
        }
        
        # Weighted combination
        weights = {
            "extraction": 0.15,
            "net_support": 0.30,
            "authority_weight": 0.25,
            "chunk_count": 0.10,
            "tier_bonus": 0.10,
            "verification": 0.10,
        }
        
        confidence = sum(signals[k] * weights[k] for k in weights)
        return min(1.0, max(0.0, confidence))
    
    def _tier_bonus(self, tier: AuthorityTier) -> float:
        return {1: 1.0, 2: 0.9, 3: 0.85, 4: 0.7, 5: 0.5, 6: 0.3}.get(tier.value, 0.5)
    
    def compute_segment_confidence(self, segment: AnswerSegment) -> float:
        if not segment.claims:
            return 0.0
        
        claim_confidences = [self.compute_claim_confidence(c) for c in segment.claims]
        
        # Penalize abstentions
        abstention_penalty = len(segment.abstentions) * 0.1
        
        return max(0.0, sum(claim_confidences) / len(claim_confidences) - abstention_penalty)
    
    def compute_overall_confidence(self, answer: GeneratedAnswer) -> float:
        if not answer.segments:
            return 0.0
        
        segment_confidences = [self.compute_segment_confidence(s) for s in answer.segments]
        
        # Weight by segment relevance (primary jurisdiction higher)
        weights = []
        for seg in answer.segments:
            if seg.jurisdiction_id == answer.jurisdiction_context.primary[0]:
                weights.append(1.0)
            elif seg.jurisdiction_id == "MULTI_JURISDICTION_COMPARISON":
                weights.append(0.5)
            else:
                weights.append(0.7)
        
        weighted_sum = sum(c * w for c, w in zip(segment_confidences, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
```

### 7.2 Abstention Thresholds

```python
class AbstentionPolicy:
    """
    Determines when to abstain vs. answer with low confidence.
    """
    
    THRESHOLDS = {
        "claim_min_confidence": 0.4,       # Individual claim below this → abstain
        "segment_min_confidence": 0.5,     # Segment below this → abstain
        "answer_min_confidence": 0.5,      # Overall below this → full abstention
        "insufficient_evidence_chunks": 1,  # Min chunks per claim
    }
    
    def should_abstain_claim(self, claim: MappedClaim) -> bool:
        if len(claim.supporting_chunks) < self.THRESHOLDS["insufficient_evidence_chunks"]:
            return True
        if claim.net_support_score < 0:
            return True
        if self.compute_claim_confidence(claim) < self.THRESHOLDS["claim_min_confidence"]:
            return True
        return False
    
    def should_abstain_segment(self, segment: AnswerSegment) -> bool:
        if not segment.claims:
            return True
        if self.compute_segment_confidence(segment) < self.THRESHOLDS["segment_min_confidence"]:
            return True
        return False
    
    def should_abstain_answer(self, answer: GeneratedAnswer) -> bool:
        return answer.overall_confidence < self.THRESHOLDS["answer_min_confidence"]
    
    def generate_abstention_message(self, answer: GeneratedAnswer) -> str:
        if self.should_abstain_answer(answer):
            return ("I don't have sufficient authoritative evidence to answer this question. "
                   "The available legal sources do not provide clear guidance on this specific matter.")
        
        # Per-segment abstentions
        messages = []
        for seg in answer.segments:
            if self.should_abstain_segment(seg):
                messages.append(f"For {seg.jurisdiction_id}: insufficient evidence")
        
        if messages:
            return "Note: " + "; ".join(messages)
        
        return ""
```

---

## 8. Citation Formatting

### 8.1 Citation Styles

```python
class CitationFormatter:
    """
    Formats citations in multiple styles for different use cases.
    """
    
    @staticmethod
    def format_legal_citation(citation: Citation, style: str = "standard") -> str:
        """
        Styles:
        - "inline": [Section 3(d), Patents Act 1970]
        - "full": Section 3(d), The Patents Act, 1970 (Act 39 of 1970), as amended
        - "academic": (Patents Act 1970, s 3(d))
        - "json": structured object
        """
        if style == "inline":
            return f"[{citation.citation_text}]"
        
        elif style == "full":
            parts = []
            if citation.citation_text:
                parts.append(citation.citation_text)
            if citation.authority:
                parts.append(f"({citation.authority})")
            if citation.effective_date:
                parts.append(f"effective {citation.effective_date}")
            if citation.source_url:
                parts.append(f"Available at: {citation.source_url}")
            return ". ".join(parts) + "."
        
        elif style == "academic":
            # (Act Year, section)
            return f"({citation.citation_text})"
        
        elif style == "json":
            return json.dumps({
                "citation_id": citation.citation_id,
                "claim_id": citation.claim_id,
                "text": citation.citation_text,
                "full": citation.full_citation,
                "jurisdiction": citation.jurisdiction,
                "authority": citation.authority,
                "authority_tier": citation.authority_tier.value,
                "url": citation.source_url,
                "effective_date": citation.effective_date,
                "verification": citation.verification_status
            })
        
        return citation.citation_text
    
    @staticmethod
    def build_citation_text(claim: LegalClaim, chunk: EvidenceChunk) -> str:
        """Build human-readable citation from claim + chunk."""
        parts = []
        
        if chunk.section_number:
            parts.append(f"Section {chunk.section_number}")
        elif chunk.section_title:
            parts.append(chunk.section_title)
        
        if chunk.act_name:
            parts.append(chunk.act_name)
        elif chunk.document_title:
            parts.append(chunk.document_title)
        
        if chunk.effective_date:
            parts.append(f"(effective {chunk.effective_date})")
        
        return ", ".join(parts)
```

---

## 9. Integration Points

### 9.1 Upstream Dependencies

| Phase | Input | Usage |
|-------|-------|-------|
| **Phase 3** | QueryAnalysis (intent, entities) | Guides claim selection & ordering |
| **Phase 6** | Retrieved EvidenceChunks | Source material for claim extraction |
| **Phase 7** | Knowledge Graph relationships | Resolves cross-references, definitions |
| **Phase 8** | FormulationClassification | Domain-specific claim templates |
| **Phase 9** | JurisdictionContext | Segregates claims by jurisdiction |
| **Phase 11** | SourceAuthority scores | Weights evidence in claim mapping |

### 9.2 Downstream Consumers

| Phase | Output | Usage |
|-------|--------|-------|
| **Phase 11** | Verified claims with authority metadata | Authority-weighted ranking |
| **Phase 12** | Multilingual citations | Translation with citation preservation |
| **Phase 13** | Structured answer with claims | Agentic orchestration for complex queries |
| **Phase 17** | Citations + confidence | Evaluation metrics (citation precision/recall) |

---

## 10. Evaluation Framework

### 10.1 Citation Quality Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Citation Precision** | % of generated claims with valid citation | 100% |
| **Citation Recall** | % of relevant evidence chunks cited | > 95% |
| **Citation Accuracy** | % of citations where chunk actually supports claim | > 98% |
| **Hallucination Rate** | % of claims not supported by any evidence | 0% |
| **Abstention Precision** | % of correct abstentions (evidence truly insufficient) | > 90% |
| **Abstention Recall** | % of insufficient-evidence cases correctly abstained | > 85% |

### 10.2 Test Cases

```python
CITATION_TEST_CASES = [
    CitationTestCase(
        case_id="CIT-001",
        query="What is the patentability criteria under Section 3(d)?",
        expected_claims=[
            "Mere discovery of new form not patentable",
            "Enhancement of known efficacy required",
            "Explanation: salts, esters, polymorphs considered same substance"
        ],
        must_cite_sections=["Section 3(d)", "Explanation to Section 3(d)"],
        must_cite_act="Patents Act 1970",
        jurisdiction="INDIA_CENTRAL"
    ),
    CitationTestCase(
        case_id="CIT-002",
        query="What are ABS requirements under Nagoya Protocol?",
        expected_claims=[
            "Prior informed consent required",
            "Mutually agreed terms required",
            "Compliance with domestic ABS legislation"
        ],
        must_cite_articles=["Article 6", "Article 7", "Article 15"],
        must_cite_treaty="Nagoya Protocol",
        jurisdiction="NAGOYA"
    ),
    CitationTestCase(
        case_id="CIT-003",
        query="Cosmetic labeling requirements in India",
        expected_claims=[
            "Label must contain name of product",
            "Label must contain name/address of manufacturer",
            "Label must contain batch number",
            "Label must contain manufacturing date",
            "Label must contain expiry date"
        ],
        must_cite_rules=["Cosmetics Rules 2020, Rule 145"],
        jurisdiction="INDIA_CENTRAL"
    ),
    CitationTestCase(
        case_id="CIT-004",
        query="Compare patent term in India and USA",
        expected_claims=[
            "India: 20 years from filing date",
            "USA: 20 years from filing date",
            "India: no patent term extension",
            "USA: patent term adjustment available"
        ],
        jurisdictions=["INDIA_CENTRAL", "USA"],
        comparative=True
    ),
]
```

---

## 11. Open Research Questions

| ID | Question |
|----|----------|
| **ORQ-52** | Optimal claim granularity: atomic vs. compound claims for retrieval? |
| **ORQ-53** | LLM-based entailment vs. cross-encoder: accuracy vs. latency tradeoff? |
| **ORQ-54** | How to handle "negative claims" (what the law does NOT require)? |
| **ORQ-55** | Citation format for non-text sources (tables, schedules, forms)? |
| **ORQ-56** | Real-time citation verification vs. pre-computed claim index? |
| **ORQ-57** | Handling of "silent amendments" where text unchanged but interpretation shifted? |
| **ORQ-58** | Multi-document claim synthesis (combining Act + Rules + Notification)? |

---

## 12. Implementation Checklist

- [ ] Claim extraction prompt + LLM integration
- [ ] Claim deduplication (cross-chunk)
- [ ] Claim-to-evidence mapping with entailment scoring
- [ ] Authority-weighted conflict resolution
- [ ] Answer composition from claims only
- [ ] Inline citation insertion
- [ ] Citation verification pipeline (entailment + metadata checks)
- [ ] Multi-jurisdiction segmented generation
- [ ] Comparative answer generation
- [ ] Confidence calculation (multi-signal)
- [ ] Abstention logic and messaging
- [ ] Citation formatting (multiple styles)
- [ ] Integration tests with Phase 6 retrieval
- [ ] Evaluation dataset (CIT-001 to CIT-004+)
- [ ] Benchmark: citation precision/recall, hallucination rate

---

## 13. Summary

| Aspect | Decision |
|--------|----------|
| **Core Pipeline** | Evidence → Claims → Mapping → Composition → Verification |
| **Claim Granularity** | Atomic legal propositions (11 types) |
| **Evidence Mapping** | All supporting chunks, entailment scoring, authority weighting |
| **Composition** | Claims-only generation, logical ordering, inline citations |
| **Verification** | Mandatory gate: chunk existence, jurisdiction, entailment, authority |
| **Abstention** | Multi-level thresholds (claim/segment/answer) |
| **Multi-Jurisdiction** | Explicit segments + comparison segment |
| **Confidence** | 6-signal weighted model |
| **Output** | Answer + structured citations + confidence + abstentions |

---

## 14. Next Phase: Phase 11 - Source Authority System

Phase 11 will design the **Source Authority System** that:
- Assigns authority tiers to all sources (Tier 1-6)
- Computes authority-weighted retrieval and generation scores
- Handles authority conflicts (court vs. regulator, central vs. state)
- Provides authority provenance for every chunk and claim
- Integrates with KG for dynamic authority updates