"""
IP-SAKTI Chunking Strategy
Phase 8: Implements the chunking strategy for document processing.
Consumes the ingestion pipeline output and prepares chunks for RAG/retrieval.
"""

import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import Document, DocumentChunk, DocumentType


class ChunkingStrategyType(str, Enum):
    """Types of chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    HYBRID = "hybrid"
    LEGAL_STRUCTURAL = "legal_structural"
    PATENT_CLAIMS = "patent_claims"


@dataclass
class ChunkingConfig:
    """Configuration for chunking."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    strategy: ChunkingStrategyType = ChunkingStrategyType.HYBRID
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    preserve_structure: bool = True
    legal_document: bool = False


class BaseChunker(ABC):
    """Abstract base class for chunkers."""
    
    def __init__(self, config: ChunkingConfig):
        self.config = config
    
    @abstractmethod
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk text into DocumentChunks."""
        pass
    
    def _create_chunk(
        self,
        text: str,
        index: int,
        document_id: str,
        start_char: int,
        end_char: int,
        metadata: Dict[str, Any],
    ) -> DocumentChunk:
        """Create a DocumentChunk with standard fields."""
        return DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=text,
            chunk_index=index,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata.copy(),
        )


class FixedSizeChunker(BaseChunker):
    """Fixed-size chunking with overlap."""
    
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        chunks = []
        document_id = metadata.get('document_id', '')
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        start = 0
        index = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within last 100 chars
                search_start = max(start + chunk_size - 100, start)
                sentence_end = self._find_sentence_boundary(text, search_start, end)
                if sentence_end > start:
                    end = sentence_end
            
            chunk_text = text[start:end].strip()
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = self._create_chunk(
                    text=chunk_text,
                    index=index,
                    document_id=document_id,
                    start_char=start,
                    end_char=end,
                    metadata=metadata,
                )
                chunks.append(chunk)
                index += 1
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Find the last sentence boundary in range."""
        # Look for .!? followed by space or newline
        for i in range(end - 1, start - 1, -1):
            if text[i] in '.!?':
                # Check if followed by space/newline or end of text
                if i + 1 >= len(text) or text[i + 1] in ' \n\r\t':
                    return i + 1
        return end


class StructuralChunker(BaseChunker):
    """Structure-aware chunking based on document structure."""
    
    # Patterns for common structural elements
    HEADING_PATTERNS = [
        r'^#{1,6}\s+.*$',  # Markdown headings
        r'^\d+(\.\d+)*\s+[A-Z].*$',  # Numbered sections
        r'^[A-Z][A-Z\s]{2,}:$',  # ALL CAPS headings
        r'^Article\s+\d+',  # Legal articles
        r'^Section\s+\d+',  # Legal sections
        r'^Chapter\s+\d+',  # Chapters
        r'^Rule\s+\d+',     # Rules
        r'^Regulation\s+\d+',  # Regulations
    ]
    
    PARAGRAPH_BREAK = r'\n\s*\n'
    
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        chunks = []
        document_id = metadata.get('document_id', '')
        doc_type = metadata.get('document_type', DocumentType.PATENT)
        
        # Split by structural boundaries
        sections = self._split_by_structure(text, doc_type)
        
        index = 0
        char_offset = 0
        
        for section_title, section_text, level in sections:
            # If section is small, keep as one chunk
            if len(section_text) <= self.config.chunk_size:
                chunk = self._create_chunk(
                    text=section_text,
                    index=index,
                    document_id=document_id,
                    start_char=char_offset,
                    end_char=char_offset + len(section_text),
                    metadata={**metadata, 'section_title': section_title, 'section_level': level},
                )
                chunks.append(chunk)
                index += 1
                char_offset += len(section_text) + 2  # +2 for newlines
            else:
                # Sub-chunk large sections
                sub_chunks = await self._chunk_large_section(
                    section_text, section_title, level, document_id, char_offset, metadata, index
                )
                chunks.extend(sub_chunks)
                index += len(sub_chunks)
                char_offset += len(section_text) + 2
        
        return chunks
    
    def _split_by_structure(self, text: str, doc_type: DocumentType) -> List[Tuple[str, str, int]]:
        """Split text by structural elements. Returns (title, content, level)."""
        sections = []
        lines = text.split('\n')
        
        current_title = "Document Start"
        current_content = []
        current_level = 0
        
        for line in lines:
            heading_match = self._match_heading(line)
            if heading_match:
                # Save previous section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content).strip(), current_level))
                
                # Start new section
                current_title = heading_match['title']
                current_level = heading_match['level']
                current_content = []
            else:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections.append((current_title, '\n'.join(current_content).strip(), current_level))
        
        return sections if sections else [("Full Document", text.strip(), 0)]
    
    def _match_heading(self, line: str) -> Optional[Dict[str, Any]]:
        """Match line against heading patterns."""
        for i, pattern in enumerate(self.HEADING_PATTERNS):
            match = re.match(pattern, line.strip())
            if match:
                title = line.strip()
                # Clean up markdown heading markers
                title = re.sub(r'^#{1,6}\s+', '', title)
                return {'title': title, 'level': i + 1}
        return None
    
    async def _chunk_large_section(
        self,
        text: str,
        section_title: str,
        level: int,
        document_id: str,
        char_offset: int,
        metadata: Dict[str, Any],
        start_index: int,
    ) -> List[DocumentChunk]:
        """Chunk a large section using fixed-size with overlap."""
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        start = 0
        index = start_index
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            if end < len(text):
                search_start = max(start + chunk_size - 100, start)
                sentence_end = self._find_sentence_boundary(text, search_start, end)
                if sentence_end > start:
                    end = sentence_end
            
            chunk_text = text[start:end].strip()
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = self._create_chunk(
                    text=chunk_text,
                    index=index,
                    document_id=document_id,
                    start_char=char_offset + start,
                    end_char=char_offset + end,
                    metadata={**metadata, 'section_title': section_title, 'section_level': level},
                )
                chunks.append(chunk)
                index += 1
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        for i in range(end - 1, start - 1, -1):
            if text[i] in '.!?':
                if i + 1 >= len(text) or text[i + 1] in ' \n\r\t':
                    return i + 1
        return end


class SemanticChunker(BaseChunker):
    """Semantic chunking using embeddings similarity (placeholder for embedding-based)."""
    
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        # For now, fall back to structural chunking
        # In production, this would use sentence embeddings to find semantic boundaries
        structural_chunker = StructuralChunker(self.config)
        return await structural_chunker.chunk(text, metadata)


class LegalStructuralChunker(BaseChunker):
    """Specialized chunker for legal documents (patents, statutes, cases)."""
    
    # Legal document patterns
    PATENT_SECTIONS = [
        r'^Title\s*:',
        r'^Abstract\s*:',
        r'^Background\s+of\s+the\s+Invention',
        r'^Summary\s+of\s+the\s+Invention',
        r'^Brief\s+Description\s+of\s+Drawings',
        r'^Detailed\s+Description',
        r'^Claims?\s*:',
        r'^Claim\s+\d+',
    ]
    
    STATUTE_SECTIONS = [
        r'^Section\s+\d+[A-Z]?',
        r'^Article\s+\d+[A-Z]?',
        r'^Chapter\s+\d+',
        r'^Part\s+[IVX]+',
        r'^Schedule\s+\d+',
    ]
    
    CASE_LAW_SECTIONS = [
        r'^Judgment',
        r'^Order',
        r'^Opinion',
        r'^Facts?',
        r'^Issues?',
        r'^Holding',
        r'^Analysis',
        r'^Conclusion',
        r'^Dissent',
        r'^Concurrence',
    ]
    
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        doc_type = metadata.get('document_type', DocumentType.PATENT)
        
        if doc_type == DocumentType.PATENT:
            return await self._chunk_patent(text, metadata)
        elif doc_type in (DocumentType.STATUTE, DocumentType.REGULATION):
            return await self._chunk_statute(text, metadata)
        elif doc_type == DocumentType.CASE_LAW:
            return await self._chunk_case_law(text, metadata)
        else:
            # Fall back to structural
            structural = StructuralChunker(self.config)
            return await structural.chunk(text, metadata)
    
    async def _chunk_patent(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk patent document preserving claims structure."""
        chunks = []
        document_id = metadata.get('document_id', '')
        
        # Split into major sections
        sections = self._split_patent_sections(text)
        
        index = 0
        char_offset = 0
        
        for section_name, section_text in sections:
            if section_name == 'claims':
                # Special handling for claims - each claim is a chunk
                claim_chunks = self._chunk_claims(section_text, document_id, char_offset, metadata, index)
                chunks.extend(claim_chunks)
                index += len(claim_chunks)
            elif len(section_text) <= self.config.chunk_size:
                chunk = self._create_chunk(
                    text=section_text,
                    index=index,
                    document_id=document_id,
                    start_char=char_offset,
                    end_char=char_offset + len(section_text),
                    metadata={**metadata, 'patent_section': section_name},
                )
                chunks.append(chunk)
                index += 1
            else:
                # Sub-chunk large sections
                structural = StructuralChunker(self.config)
                sub_chunks = await structural.chunk(section_text, {**metadata, 'patent_section': section_name})
                for sc in sub_chunks:
                    sc.chunk_index = index
                    sc.start_char += char_offset
                    sc.end_char += char_offset
                    index += 1
                chunks.extend(sub_chunks)
            
            char_offset += len(section_text) + 2
        
        return chunks
    
    def _split_patent_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split patent into major sections."""
        sections = []
        current_section = 'header'
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            # Check for section headers
            matched_section = None
            for pattern in self.PATENT_SECTIONS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    # Normalize section name
                    if 'claim' in line.lower():
                        matched_section = 'claims'
                    elif 'abstract' in line.lower():
                        matched_section = 'abstract'
                    elif 'background' in line.lower():
                        matched_section = 'background'
                    elif 'summary' in line.lower():
                        matched_section = 'summary'
                    elif 'description' in line.lower() and 'detailed' not in line.lower():
                        matched_section = 'description'
                    elif 'detailed description' in line.lower():
                        matched_section = 'detailed_description'
                    elif 'drawing' in line.lower():
                        matched_section = 'drawings'
                    elif 'title' in line.lower():
                        matched_section = 'title'
                    break
            
            if matched_section:
                if current_content:
                    sections.append((current_section, '\n'.join(current_content).strip()))
                current_section = matched_section
                current_content = [line]
            else:
                current_content.append(line)
        
        if current_content:
            sections.append((current_section, '\n'.join(current_content).strip()))
        
        return sections if sections else [('full_text', text.strip())]
    
    def _chunk_claims(
        self,
        text: str,
        document_id: str,
        char_offset: int,
        metadata: Dict[str, Any],
        start_index: int,
    ) -> List[DocumentChunk]:
        """Split claims into individual claim chunks."""
        chunks = []
        
        # Split by claim numbers
        claim_pattern = r'(Claim\s+\d+[\.:])'
        parts = re.split(claim_pattern, text, flags=re.IGNORECASE)
        
        index = start_index
        current_offset = char_offset
        
        # parts will be: [before_first_claim, "Claim 1:", claim1_text, "Claim 2:", claim2_text, ...]
        current_claim_num = None
        current_claim_text = []
        
        for part in parts:
            claim_match = re.match(r'Claim\s+(\d+)', part, re.IGNORECASE)
            if claim_match:
                # Save previous claim
                if current_claim_num is not None and current_claim_text:
                    claim_text = ''.join(current_claim_text).strip()
                    if claim_text:
                        chunk = self._create_chunk(
                            text=claim_text,
                            index=index,
                            document_id=document_id,
                            start_char=current_offset,
                            end_char=current_offset + len(claim_text),
                            metadata={**metadata, 'patent_section': 'claims', 'claim_number': current_claim_num},
                        )
                        chunks.append(chunk)
                        index += 1
                        current_offset += len(claim_text) + 2
                
                current_claim_num = claim_match.group(1)
                current_claim_text = [part]
            else:
                current_claim_text.append(part)
        
        # Save last claim
        if current_claim_num is not None and current_claim_text:
            claim_text = ''.join(current_claim_text).strip()
            if claim_text:
                chunk = self._create_chunk(
                    text=claim_text,
                    index=index,
                    document_id=document_id,
                    start_char=current_offset,
                    end_char=current_offset + len(claim_text),
                    metadata={**metadata, 'patent_section': 'claims', 'claim_number': current_claim_num},
                )
                chunks.append(chunk)
        
        return chunks
    
    async def _chunk_statute(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk statute/regulation by sections."""
        chunks = []
        document_id = metadata.get('document_id', '')
        
        # Split by section/article
        section_pattern = r'(^(?:Section|Article|Chapter|Part|Schedule)\s+[\dIVX]+[A-Z]?\.?\s*)'
        parts = re.split(section_pattern, text, flags=re.MULTILINE | re.IGNORECASE)
        
        index = 0
        char_offset = 0
        current_section = "Preamble"
        current_content = []
        
        for part in parts:
            section_match = re.match(r'^(?:Section|Article|Chapter|Part|Schedule)\s+([\dIVX]+[A-Z]?)', part, re.IGNORECASE)
            if section_match:
                # Save previous
                if current_content:
                    section_text = ''.join(current_content).strip()
                    if section_text:
                        await self._add_section_chunks(
                            section_text, current_section, document_id, char_offset, metadata, index, chunks
                        )
                        index += len([c for c in chunks if c.metadata.get('statute_section') == current_section])
                        char_offset += len(section_text) + 2
                
                current_section = f"{section_match.group(0)}"
                current_content = [part]
            else:
                current_content.append(part)
        
        # Save last
        if current_content:
            section_text = ''.join(current_content).strip()
            if section_text:
                await self._add_section_chunks(
                    section_text, current_section, document_id, char_offset, metadata, index, chunks
                )
        
        return chunks
    
    async def _add_section_chunks(
        self,
        text: str,
        section: str,
        document_id: str,
        char_offset: int,
        metadata: Dict[str, Any],
        start_index: int,
        chunks: List[DocumentChunk],
    ) -> None:
        """Add chunks for a statute section."""
        if len(text) <= self.config.chunk_size:
            chunk = self._create_chunk(
                text=text,
                index=start_index,
                document_id=document_id,
                start_char=char_offset,
                end_char=char_offset + len(text),
                metadata={**metadata, 'statute_section': section},
            )
            chunks.append(chunk)
        else:
            structural = StructuralChunker(self.config)
            sub_chunks = await structural.chunk(text, {**metadata, 'statute_section': section})
            for i, sc in enumerate(sub_chunks):
                sc.chunk_index = start_index + i
                sc.start_char += char_offset
                sc.end_char += char_offset
                chunks.append(sc)
    
    async def _chunk_case_law(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk case law by structural sections."""
        chunks = []
        document_id = metadata.get('document_id', '')
        
        # Try to identify major sections
        sections = self._split_case_law_sections(text)
        
        index = 0
        char_offset = 0
        
        for section_name, section_text in sections:
            if len(section_text) <= self.config.chunk_size:
                chunk = self._create_chunk(
                    text=section_text,
                    index=index,
                    document_id=document_id,
                    start_char=char_offset,
                    end_char=char_offset + len(section_text),
                    metadata={**metadata, 'case_section': section_name},
                )
                chunks.append(chunk)
                index += 1
            else:
                structural = StructuralChunker(self.config)
                sub_chunks = await structural.chunk(section_text, {**metadata, 'case_section': section_name})
                for sc in sub_chunks:
                    sc.chunk_index = index
                    sc.start_char += char_offset
                    sc.end_char += char_offset
                    index += 1
                chunks.extend(sub_chunks)
            
            char_offset += len(section_text) + 2
        
        return chunks
    
    def _split_case_law_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split case law into sections."""
        sections = []
        current_section = 'header'
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            matched = None
            for pattern in self.CASE_LAW_SECTIONS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    matched = line.strip()
                    break
            
            if matched:
                if current_content:
                    sections.append((current_section, '\n'.join(current_content).strip()))
                current_section = matched.lower().replace(' ', '_')
                current_content = [line]
            else:
                current_content.append(line)
        
        if current_content:
            sections.append((current_section, '\n'.join(current_content).strip()))
        
        return sections if sections else [('full_text', text.strip())]


class PatentClaimsChunker(BaseChunker):
    """Specialized chunker for patent claims with dependency analysis."""
    
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Extract and chunk patent claims with dependency metadata."""
        chunks = []
        document_id = metadata.get('document_id', '')
        
        # Find claims section
        claims_text = self._extract_claims_section(text)
        if not claims_text:
            return chunks
        
        # Parse individual claims
        claims = self._parse_claims(claims_text)
        
        # Build dependency graph
        dependencies = self._analyze_dependencies(claims)
        
        # Create chunks for each claim
        for i, (claim_num, claim_text) in enumerate(claims):
            dep_info = dependencies.get(claim_num, {})
            
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                content=claim_text,
                chunk_index=i,
                start_char=0,  # Would need actual positions
                end_char=len(claim_text),
                metadata={
                    **metadata,
                    'patent_section': 'claims',
                    'claim_number': claim_num,
                    'claim_type': dep_info.get('type', 'independent'),
                    'depends_on': dep_info.get('depends_on', []),
                    'dependent_claims': dep_info.get('dependent_claims', []),
                },
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_claims_section(self, text: str) -> Optional[str]:
        """Extract the claims section from patent text."""
        # Look for claims section start
        claims_start = re.search(r'\bClaims?\s*:', text, re.IGNORECASE)
        if not claims_start:
            return None
        
        # Return text from claims start to end
        return text[claims_start.start():]
    
    def _parse_claims(self, text: str) -> List[Tuple[str, str]]:
        """Parse individual claims from claims text."""
        claims = []
        
        # Split by claim numbers
        pattern = r'(Claim\s+(\d+)[\.:]\s*)'
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        
        current_num = None
        current_text = []
        
        for part in parts:
            match = re.match(r'Claim\s+(\d+)', part, re.IGNORECASE)
            if match:
                if current_num is not None and current_text:
                    claims.append((current_num, ''.join(current_text).strip()))
                current_num = match.group(1)
                current_text = [part]
            else:
                current_text.append(part)
        
        if current_num is not None and current_text:
            claims.append((current_num, ''.join(current_text).strip()))
        
        return claims
    
    def _analyze_dependencies(self, claims: List[Tuple[str, str]]) -> Dict[str, Dict]:
        """Analyze claim dependencies."""
        dependencies = {}
        
        for claim_num, claim_text in claims:
            # Check if independent (no reference to other claims)
            dep_match = re.search(r'claim\s+(\d+)', claim_text, re.IGNORECASE)
            
            if dep_match:
                # Dependent claim
                depends_on = [dep_match.group(1)]
                # Find all referenced claims
                all_refs = re.findall(r'claim\s+(\d+)', claim_text, re.IGNORECASE)
                depends_on = list(set(all_refs))
                
                dependencies[claim_num] = {
                    'type': 'dependent',
                    'depends_on': depends_on,
                    'dependent_claims': [],
                }
                
                # Update parent claims
                for parent in depends_on:
                    if parent not in dependencies:
                        dependencies[parent] = {'type': 'independent', 'depends_on': [], 'dependent_claims': []}
                    dependencies[parent]['dependent_claims'].append(claim_num)
            else:
                # Independent claim
                dependencies[claim_num] = {
                    'type': 'independent',
                    'depends_on': [],
                    'dependent_claims': [],
                }
        
        return dependencies


class HybridChunker(BaseChunker):
    """Hybrid chunking combining multiple strategies."""
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.structural = StructuralChunker(config)
        self.legal = LegalStructuralChunker(config)
        self.fixed = FixedSizeChunker(config)
    
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        doc_type = metadata.get('document_type', DocumentType.PATENT)
        legal_doc = metadata.get('legal_document', self.config.legal_document)
        
        # Use legal structural for legal documents
        if legal_doc or doc_type in (
            DocumentType.PATENT, DocumentType.STATUTE, 
            DocumentType.REGULATION, DocumentType.CASE_LAW,
            DocumentType.LEGAL_OPINION, DocumentType.TREATY
        ):
            return await self.legal.chunk(text, metadata)
        
        # Use structural for structured documents
        if self.config.preserve_structure:
            return await self.structural.chunk(text, metadata)
        
        # Fall back to fixed size
        return await self.fixed.chunk(text, metadata)


class ChunkingStrategy:
    """Main chunking strategy orchestrator."""
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self._chunker = self._create_chunker()
    
    def _create_chunker(self) -> BaseChunker:
        """Create appropriate chunker based on strategy."""
        strategy_map = {
            ChunkingStrategyType.FIXED_SIZE: FixedSizeChunker,
            ChunkingStrategyType.SEMANTIC: SemanticChunker,
            ChunkingStrategyType.STRUCTURAL: StructuralChunker,
            ChunkingStrategyType.HYBRID: HybridChunker,
            ChunkingStrategyType.LEGAL_STRUCTURAL: LegalStructuralChunker,
            ChunkingStrategyType.PATENT_CLAIMS: PatentClaimsChunker,
        }
        
        chunker_class = strategy_map.get(self.config.strategy, HybridChunker)
        return chunker_class(self.config)
    
    async def chunk_document(
        self,
        document: Document,
        text: str,
    ) -> List[DocumentChunk]:
        """Chunk a document's text content."""
        metadata = {
            'document_id': document.id,
            'document_type': document.metadata.document_type,
            'jurisdiction': document.metadata.jurisdiction,
            'legal_document': True,  # IP documents are legal
        }
        
        # Add source authority info
        if document.source.authority_tier:
            metadata['authority_tier'] = document.source.authority_tier.value
        
        return await self._chunker.chunk(text, metadata)
    
    async def chunk_text(
        self,
        text: str,
        document_id: str,
        document_type: DocumentType = DocumentType.PATENT,
        jurisdiction = None,
    ) -> List[DocumentChunk]:
        """Chunk arbitrary text with metadata."""
        metadata = {
            'document_id': document_id,
            'document_type': document_type,
            'jurisdiction': jurisdiction,
            'legal_document': True,
        }
        return await self._chunker.chunk(text, metadata)


def create_chunker(
    strategy: ChunkingStrategyType = ChunkingStrategyType.HYBRID,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs
) -> ChunkingStrategy:
    """Factory function to create a chunking strategy."""
    config = ChunkingConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    return ChunkingStrategy(config)