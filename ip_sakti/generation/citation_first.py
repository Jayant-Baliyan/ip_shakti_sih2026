"""
IP-SAKTI Citation-First Generation
Phase 16: Implements the citation-first generation system.
Ensures all generated answers are grounded in cited sources.
"""

import asyncio
import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import (
    Document,
    DocumentChunk,
    DocumentType,
    Jurisdiction,
    Query,
    QueryIntent,
)

logger = logging.getLogger(__name__)


class CitationStyle(str, Enum):
    """Citation styles."""
    BRACKET = "bracket"      # [1], [2]
    PARENTHETICAL = "parenthetical"  # (Source 1, Source 2)
    FOOTNOTE = "footnote"    # ¹, ²
    INLINE = "inline"        # According to Source 1...
    LEGAL = "legal"          # Bluebook/legal citation format


class CitationRequirement(str, Enum):
    """Citation requirement levels."""
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"
    EVERY_SENTENCE = "every_sentence"
    EVERY_CLAIM = "every_claim"


@dataclass
class CitationConfig:
    """Configuration for citation-first generation."""
    style: CitationStyle = CitationStyle.BRACKET
    requirement: CitationRequirement = CitationRequirement.REQUIRED
    max_citations_per_sentence: int = 3
    max_citations_per_answer: int = 20
    require_authority_citation: bool = True
    require_jurisdiction_citation: bool = True
    citation_format: str = "[{id}]"  # Template for citation
    verify_citations: bool = True
    hallucination_threshold: float = 0.1


@dataclass
class Citation:
    """A single citation."""
    id: int
    chunk_id: str
    document_id: str
    text: str  # The cited text snippet
    source_type: str  # "statute", "case", "patent", "article", etc.
    authority_tier: str
    jurisdiction: Optional[str] = None
    document_type: Optional[str] = None
    section: Optional[str] = None
    page: Optional[str] = None
    confidence: float = 1.0


@dataclass
class CitedAnswer:
    """Answer with embedded citations."""
    answer: str
    citations: List[Citation] = field(default_factory=list)
    citation_map: Dict[int, Citation] = field(default_factory=dict)  # citation_id -> Citation
    unverified_claims: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    generation_metadata: Dict[str, Any] = field(default_factory=dict)


class CitationFormatter:
    """Format citations in various styles."""
    
    def __init__(self, config: CitationConfig):
        self.config = config
    
    def format_citation(self, citation: Citation) -> str:
        """Format a single citation."""
        if self.config.style == CitationStyle.BRACKET:
            return self.config.citation_format.format(id=citation.id)
        elif self.config.style == CitationStyle.PARENTHETICAL:
            return f"({citation.source_type} {citation.id})"
        elif self.config.style == CitationStyle.FOOTNOTE:
            # Unicode superscript numbers
            superscripts = "⁰¹²³⁴⁵⁶⁷⁸⁹"
            if citation.id < len(superscripts):
                return superscripts[citation.id]
            return f"[{citation.id}]"
        elif self.config.style == CitationStyle.INLINE:
            return f"according to {citation.source_type} {citation.id}"
        elif self.config.style == CitationStyle.LEGAL:
            return self._format_legal_citation(citation)
        return f"[{citation.id}]"
    
    def _format_legal_citation(self, citation: Citation) -> str:
        """Format in legal/Bluebook style."""
        parts = []
        if citation.source_type == "statute":
            parts.append(citation.section or "§")
            if citation.jurisdiction:
                parts.append(citation.jurisdiction)
        elif citation.source_type == "case":
            parts.append(citation.text[:50])
            if citation.jurisdiction:
                parts.append(f"({citation.jurisdiction})")
        elif citation.source_type == "patent":
            parts.append(citation.document_id)
        return f"[{citation.id}] {' '.join(parts)}"
    
    def format_citation_list(self, citations: List[Citation]) -> str:
        """Format a list of citations as bibliography."""
        lines = []
        for cite in citations:
            lines.append(f"[{cite.id}] {cite.source_type}: {cite.text[:100]}...")
        return "\n".join(lines)


class CitationVerifier:
    """Verify citations in generated text."""
    
    def __init__(self, config: CitationConfig):
        self.config = config
    
    def verify(
        self,
        answer: str,
        citations: List[Citation],
        context_chunks: List[DocumentChunk],
    ) -> Tuple[bool, List[str]]:
        """Verify all citations in answer are valid."""
        errors = []
        
        # Extract citation markers from answer
        if self.config.style == CitationStyle.BRACKET:
            pattern = r'\[(\d+)\]'
        elif self.config.style == CitationStyle.PARENTHETICAL:
            pattern = r'\((\d+)\)'
        else:
            pattern = r'\[(\d+)\]'
        
        cited_ids = set(int(m) for m in re.findall(pattern, answer))
        valid_ids = {c.id for c in citations}
        
        # Check for invalid citations
        for cite_id in cited_ids:
            if cite_id not in valid_ids:
                errors.append(f"Citation [{cite_id}] in answer does not exist in sources")
        
        # Check for missing required citations
        if self.config.requirement in (CitationRequirement.REQUIRED, CitationRequirement.EVERY_SENTENCE):
            # Check if every sentence has a citation
            sentences = re.split(r'[.!?]+', answer)
            for i, sent in enumerate(sentences):
                sent = sent.strip()
                if len(sent) > 20:  # Non-trivial sentence
                    sent_citations = re.findall(pattern, sent)
                    if not sent_citations and self.config.requirement == CitationRequirement.EVERY_SENTENCE:
                        errors.append(f"Sentence {i+1} lacks citation: {sent[:50]}...")
        
        # Verify citation content matches source
        for citation in citations:
            if not self._verify_citation_content(citation, context_chunks):
                errors.append(f"Citation [{citation.id}] content doesn't match source")
        
        return len(errors) == 0, errors
    
    def _verify_citation_content(
        self,
        citation: Citation,
        context_chunks: List[DocumentChunk],
    ) -> bool:
        """Verify citation text appears in source chunk."""
        # Find the chunk
        chunk = next((c for c in context_chunks if c.id == citation.chunk_id), None)
        if not chunk:
            return False
        
        # Check if citation text is in chunk (fuzzy match)
        cite_text = citation.text.lower().strip()
        chunk_text = chunk.content.lower()
        
        # Simple containment check (could be more sophisticated)
        return cite_text in chunk_text or self._fuzzy_match(cite_text, chunk_text)
    
    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """Simple fuzzy matching."""
        # Check if significant words from text1 appear in text2
        words1 = set(w for w in text1.split() if len(w) > 3)
        words2 = set(w for w in text2.split() if len(w) > 3)
        
        if not words1:
            return True
        
        overlap = len(words1 & words2) / len(words1)
        return overlap >= threshold


class ClaimExtractor:
    """Extract verifiable claims from generated text."""
    
    CLAIM_PATTERNS = [
        r'[^.!?]*\b(?:is|are|was|were|has|have|had|can|could|will|would|shall|should|must|may|might)\b[^.!?]*[.!?]',
        r'[^.!?]*\b(?:patent|trademark|copyright|infringe|valid|invalid|novel|obvious|claim)\b[^.!?]*[.!?]',
        r'[^.!?]*\b(?:court|held|ruled|decided|found|determined)\b[^.!?]*[.!?]',
    ]
    
    def extract_claims(self, text: str) -> List[str]:
        """Extract verifiable claims from text."""
        claims = []
        
        for pattern in self.CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            claims.extend([m.strip() for m in matches if len(m.strip()) > 20])
        
        # Also split by sentences and filter
        sentences = re.split(r'[.!?]+', text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 30 and any(kw in sent.lower() for kw in 
                ['patent', 'trademark', 'copyright', 'court', 'held', 'ruled', 'section', 'article', 'claim']):
                claims.append(sent)
        
        return list(set(claims))  # Deduplicate


class CitationFirstGenerator:
    """Generator that produces citation-first answers."""
    
    def __init__(
        self,
        config: CitationConfig,
        settings: Optional[Settings] = None,
    ):
        self.config = config
        self.settings = settings or get_settings()
        self.formatter = CitationFormatter(config)
        self.verifier = CitationVerifier(config)
        self.claim_extractor = ClaimExtractor()
        
        # LLM placeholder
        self.llm_model = None
    
    async def generate(
        self,
        query: str,
        context_chunks: List[DocumentChunk],
        citations: List[Citation],
    ) -> CitedAnswer:
        """Generate answer with citations."""
        
        # Build context with citation markers
        context_with_citations = self._build_context(context_chunks, citations)
        
        # Generate answer
        answer = await self._generate_answer(query, context_with_citations, citations)
        
        # Post-process to ensure citations
        answer = self._ensure_citations(answer, citations, context_chunks)
        
        # Verify citations
        is_valid, errors = self.verifier.verify(answer, citations, context_chunks)
        
        # Extract unverified claims
        unverified = []
        if self.config.verify_citations:
            claims = self.claim_extractor.extract_claims(answer)
            for claim in claims:
                if not self._is_claim_supported(claim, citations, context_chunks):
                    unverified.append(claim)
        
        # Calculate confidence
        confidence = self._calculate_confidence(answer, citations, unverified)
        
        return CitedAnswer(
            answer=answer,
            citations=citations,
            citation_map={c.id: c for c in citations},
            unverified_claims=unverified,
            confidence_score=confidence,
            generation_metadata={
                'query': query,
                'num_context_chunks': len(context_chunks),
                'num_citations': len(citations),
                'verification_passed': is_valid,
                'verification_errors': errors,
            },
        )
    
    def _build_context(
        self,
        context_chunks: List[DocumentChunk],
        citations: List[Citation],
    ) -> str:
        """Build context string with citation markers."""
        parts = []
        
        for citation in citations:
            chunk = next((c for c in context_chunks if c.id == citation.chunk_id), None)
            if not chunk:
                continue
            
            marker = self.formatter.format_citation(citation)
            parts.append(f"{marker} {chunk.content[:500]}")
        
        return "\n\n".join(parts)
    
    async def _generate_answer(
        self,
        query: str,
        context: str,
        citations: List[Citation],
    ) -> str:
        """Generate answer using LLM (placeholder)."""
        # In production, this would call an actual LLM
        # For now, return a structured template answer
        
        if not citations:
            return "I could not find relevant sources to answer your query."
        
        citation_list = ", ".join([self.formatter.format_citation(c) for c in citations[:5]])
        
        # Template-based answer
        answer = (
            f"Based on the retrieved sources ({citation_list}), "
            f"the answer to your query involves several key points. "
        )
        
        # Add citations to each major point
        for i, cite in enumerate(citations[:3]):
            answer += f"Source {self.formatter.format_citation(cite)} indicates that {cite.text[:100]}. "
        
        return answer
    
    def _ensure_citations(
        self,
        answer: str,
        citations: List[Citation],
        context_chunks: List[DocumentChunk],
    ) -> str:
        """Ensure answer has proper citations."""
        
        # If no citations in answer, add them
        if not re.search(r'\[\d+\]', answer):
            # Add citation to first sentence
            sentences = re.split(r'([.!?]+)', answer)
            if len(sentences) >= 2:
                first_sent = sentences[0] + sentences[1]
                rest = "".join(sentences[2:])
                citation_marker = self.formatter.format_citation(citations[0])
                answer = f"{first_sent} {citation_marker}{rest}"
        
        return answer
    
    def _is_claim_supported(
        self,
        claim: str,
        citations: List[Citation],
        context_chunks: List[DocumentChunk],
    ) -> bool:
        """Check if a claim is supported by citations."""
        # Simple check: does claim share key terms with cited sources?
        claim_words = set(w.lower() for w in claim.split() if len(w) > 4)
        
        for citation in citations:
            chunk = next((c for c in context_chunks if c.id == citation.chunk_id), None)
            if chunk:
                chunk_words = set(w.lower() for w in chunk.content.split() if len(w) > 4)
                overlap = len(claim_words & chunk_words) / max(len(claim_words), 1)
                if overlap > 0.3:
                    return True
        
        return False
    
    def _calculate_confidence(
        self,
        answer: str,
        citations: List[Citation],
        unverified_claims: List[str],
    ) -> float:
        """Calculate confidence score for answer."""
        confidence = 0.5
        
        # More citations = higher confidence (up to a point)
        confidence += min(len(citations) * 0.05, 0.3)
        
        # Authority of sources
        authority_scores = [c.confidence for c in citations]
        if authority_scores:
            confidence += (sum(authority_scores) / len(authority_scores)) * 0.2
        
        # Penalty for unverified claims
        if unverified_claims:
            confidence -= min(len(unverified_claims) * 0.1, 0.3)
        
        return max(0.0, min(1.0, confidence))


class LegalCitationGenerator(CitationFirstGenerator):
    """Specialized generator for legal citations (Bluebook style)."""
    
    def __init__(self, config: CitationConfig, settings: Optional[Settings] = None):
        super().__init__(config, settings)
        self.config.style = CitationStyle.LEGAL
    
    async def generate(
        self,
        query: str,
        context_chunks: List[DocumentChunk],
        citations: List[Citation],
    ) -> CitedAnswer:
        """Generate legally-formatted answer."""
        # Enhance citations with legal metadata
        enhanced_citations = self._enhance_legal_citations(citations, context_chunks)
        
        return await super().generate(query, context_chunks, enhanced_citations)
    
    def _enhance_legal_citations(
        self,
        citations: List[Citation],
        context_chunks: List[DocumentChunk],
    ) -> List[Citation]:
        """Enhance citations with legal formatting."""
        for citation in citations:
            chunk = next((c for c in context_chunks if c.id == citation.chunk_id), None)
            if chunk:
                # Add legal-specific metadata
                if citation.source_type == "statute":
                    citation.section = chunk.metadata.get('statute_section') or chunk.metadata.get('section_title')
                elif citation.source_type == "case":
                    citation.page = chunk.metadata.get('page')
                elif citation.source_type == "patent":
                    citation.section = chunk.metadata.get('patent_section')
                    citation.page = chunk.metadata.get('claim_number')
        
        return citations


class PatentCitationGenerator(CitationFirstGenerator):
    """Specialized generator for patent citations."""
    
    def __init__(self, config: CitationConfig, settings: Optional[Settings] = None):
        super().__init__(config, settings)
    
    async def generate(
        self,
        query: str,
        context_chunks: List[DocumentChunk],
        citations: List[Citation],
    ) -> CitedAnswer:
        """Generate patent-specific answer with claim citations."""
        # Enhance with claim-level citations
        enhanced = self._enhance_patent_citations(citations, context_chunks)
        return await super().generate(query, context_chunks, enhanced)
    
    def _enhance_patent_citations(
        self,
        citations: List[Citation],
        context_chunks: List[DocumentChunk],
    ) -> List[Citation]:
        """Add claim numbers and patent sections to citations."""
        for citation in citations:
            chunk = next((c for c in context_chunks if c.id == citation.chunk_id), None)
            if chunk:
                if 'claim_number' in chunk.metadata:
                    citation.page = f"Claim {chunk.metadata['claim_number']}"
                if 'patent_section' in chunk.metadata:
                    citation.section = chunk.metadata['patent_section']
        return citations


class StreamingCitationGenerator(CitationFirstGenerator):
    """Generator with streaming output support."""
    
    async def generate_streaming(
        self,
        query: str,
        context_chunks: List[DocumentChunk],
        citations: List[Citation],
    ):
        """Generate answer in streaming fashion."""
        # Build context
        context = self._build_context(context_chunks, citations)
        
        # Simulate streaming (in production, use actual streaming LLM)
        answer = await self._generate_answer(query, context, citations)
        
        # Yield in chunks
        words = answer.split()
        for i in range(0, len(words), 5):
            chunk = " ".join(words[i:i+5])
            yield {
                'token': chunk + " ",
                'is_complete': i + 5 >= len(words),
                'citations': [
                    {'id': c.id, 'text': self.formatter.format_citation(c)}
                    for c in citations
                ] if i == 0 else None,
            }
        
        # Final verification
        final_answer = answer
        is_valid, errors = self.verifier.verify(final_answer, citations, context_chunks)
        
        yield {
            'token': '',
            'is_complete': True,
            'final_answer': final_answer,
            'citations': [c.__dict__ for c in citations],
            'verification': {'passed': is_valid, 'errors': errors},
        }


def create_citation_generator(
    style: CitationStyle = CitationStyle.BRACKET,
    requirement: CitationRequirement = CitationRequirement.REQUIRED,
    legal_mode: bool = False,
    patent_mode: bool = False,
    streaming: bool = False,
    **kwargs
) -> CitationFirstGenerator:
    """Factory to create citation generator."""
    config = CitationConfig(
        style=style,
        requirement=requirement,
        **kwargs
    )
    
    if legal_mode:
        return LegalCitationGenerator(config)
    elif patent_mode:
        return PatentCitationGenerator(config)
    elif streaming:
        return StreamingCitationGenerator(config)
    else:
        return CitationFirstGenerator(config)