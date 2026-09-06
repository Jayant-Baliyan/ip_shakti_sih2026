"""
IP-SAKTI Ingestion Pipeline
Phase 7: Implements the ingestion architecture for processing IP documents.
Consumes Source Authority tiers (Phase 5) and Security constraints (Phase 6).
"""

import asyncio
import hashlib
import json
import logging
import mimetypes
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import urllib.request

from pydantic import BaseModel, Field, validator

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import (
    AuthorityTier,
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentSource,
    DocumentType,
    IngestionJob,
    IngestionStatus,
    Jurisdiction,
    JurisdictionCode,
)
SourceAuthorityTier = AuthorityTier
from ip_sakti.authority.authority_system import SourceAuthoritySystem
from ip_sakti.security.security_system import SecuritySystem
from ip_sakti.embedding.embedder import SentenceTransformerEmbedder
from ip_sakti.embedding.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class IngestionStage(str, Enum):
    """Stages in the ingestion pipeline."""
    FETCH = "fetch"
    VALIDATE = "validate"
    EXTRACT = "extract"
    CHUNK = "chunk"
    ENRICH = "enrich"
    INDEX = "index"
    COMPLETE = "complete"
    FAILED = "failed"


class DocumentValidator(ABC):
    """Abstract base for document validators."""
    
    @abstractmethod
    async def validate(self, content: bytes, metadata: DocumentMetadata) -> Tuple[bool, List[str]]:
        """Validate document. Returns (is_valid, errors)."""
        pass


class MaliciousDocumentDetector(DocumentValidator):
    """Detects potentially malicious documents using security system."""
    
    def __init__(self, security_system: SecuritySystem):
        self.security_system = security_system
    
    async def validate(self, content: bytes, metadata: DocumentMetadata) -> Tuple[bool, List[str]]:
        errors = []
        
        # Check file size
        max_size = self.security_system.settings.max_document_size_mb * 1024 * 1024
        if len(content) > max_size:
            errors.append(f"Document size {len(content)} exceeds maximum {max_size}")
        
        # Check for executable content
        if self._has_executable_signature(content):
            errors.append("Document contains executable signatures")
        
        # Check for embedded scripts (skip for HTML files)
        mime_type = metadata.mime_type or ""
        if "text/html" not in mime_type and "application/xhtml" not in mime_type:
            # Also check detected type
            if "text/html" not in (metadata.mime_type or ""):
                if self._has_embedded_scripts(content):
                    errors.append("Document contains embedded scripts")
        
        # Check for polyglot files
        if self._is_polyglot(content):
            errors.append("Document appears to be a polyglot file")
        
        # Run security scan
        scan_result = await self.security_system.scan_document(content, metadata)
        if not scan_result.safe:
            errors.extend(scan_result.threats)
        
        return len(errors) == 0, errors
    
    def _has_executable_signature(self, content: bytes) -> bool:
        """Check for executable file signatures."""
        signatures = [
            b'\x7fELF',  # ELF
            b'MZ',       # PE/EXE
            b'\xca\xfe\xba\xbe',  # Mach-O
            b'PK\x03\x04',  # ZIP (could contain executables)
        ]
        return any(content.startswith(sig) for sig in signatures)
    
    def _has_embedded_scripts(self, content: bytes) -> bool:
        """Check for embedded JavaScript/VBScript/PowerShell."""
        script_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'powershell',
            b'eval(',
            b'Function(',
        ]
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in script_patterns)
    
    def _is_polyglot(self, content: bytes) -> bool:
        """Check if file is a polyglot (multiple valid formats)."""
        # Simple heuristic: multiple format signatures
        format_count = 0
        if content.startswith(b'%PDF'): format_count += 1
        if content.startswith(b'PK\x03\x04'): format_count += 1
        if content.startswith(b'\xff\xd8\xff'): format_count += 1
        if content.startswith(b'GIF8'): format_count += 1
        if content.startswith(b'\x89PNG'): format_count += 1
        return format_count > 1


class FormatValidator(DocumentValidator):
    """Validates document format matches expected type."""
    
    SUPPORTED_TYPES = {
        DocumentType.PATENT: ['application/pdf', 'application/xml', 'text/xml', 'text/plain', 'text/html'],
        DocumentType.TRADEMARK: ['application/pdf', 'application/xml', 'text/xml', 'text/plain', 'text/html'],
        DocumentType.COPYRIGHT: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.DESIGN: ['application/pdf', 'image/jpeg', 'image/png'],
        DocumentType.LEGAL_OPINION: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.CASE_LAW: ['application/pdf', 'text/plain', 'application/xml', 'text/html'],
        DocumentType.STATUTE: ['application/pdf', 'text/xml', 'application/xml', 'text/plain', 'text/html'],
        DocumentType.REGULATION: ['application/pdf', 'text/xml', 'application/xml', 'text/plain', 'text/html'],
        DocumentType.TREATY: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.SCHOLARLY_ARTICLE: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.ACT: ['application/pdf', 'text/plain', 'text/xml', 'application/xml', 'text/html'],
        DocumentType.RULE: ['application/pdf', 'text/plain', 'text/xml', 'application/xml', 'text/html'],
        DocumentType.NOTIFICATION: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.ORDER: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.CIRCULAR: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.GUIDELINE: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.PROTOCOL: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.REGISTRY_RECORD: ['application/pdf', 'text/plain', 'application/xml', 'text/html'],
        DocumentType.PHARMACOPOEIA: ['application/pdf', 'text/plain', 'text/html'],
        DocumentType.FORMULARY: ['application/pdf', 'text/plain', 'text/html'],
    }
    
    async def validate(self, content: bytes, metadata: DocumentMetadata) -> Tuple[bool, List[str]]:
        errors = []
        expected_types = self.SUPPORTED_TYPES.get(metadata.document_type, [])
        mime_type = metadata.mime_type or mimetypes.guess_type(metadata.source_path or "")[0]
        
        # Detect actual type from content
        from ip_sakti.security.security_system import DocumentValidator as SecurityDocValidator
        sec_validator = SecurityDocValidator()
        detected_mime = sec_validator._detect_mime_type(content)
        
        # Use detected mime type if available
        effective_mime = detected_mime if detected_mime != "text/plain" else mime_type
        
        if effective_mime and effective_mime not in expected_types:
            errors.append(f"MIME type {effective_mime} not supported for {metadata.document_type}")
        
        # Validate PDF structure if PDF (lenient for HTML-in-PDF)
        if effective_mime == 'application/pdf' and not content.startswith(b'%PDF'):
            # Check if it's HTML content (common for mislabeled PDFs)
            if content.strip().startswith(b'<!DOCTYPE') or content.strip().startswith(b'<html'):
                logger.warning("File has .pdf extension but contains HTML content - treating as HTML")
                # This will be handled by the HTML loader
            else:
                errors.append("Invalid PDF structure")
        
        return len(errors) == 0, errors


class ContentExtractor(ABC):
    """Abstract base for content extractors."""
    
    @abstractmethod
    async def extract(self, content: bytes, metadata: DocumentMetadata) -> str:
        """Extract text content from document."""
        pass


class PDFExtractor(ContentExtractor):
    """Extract text from PDF documents."""
    
    async def extract(self, content: bytes, metadata: DocumentMetadata) -> str:
        try:
            import pdfplumber
            import io
            
            text_parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("pdfplumber not installed, falling back to basic extraction")
            return self._basic_pdf_extract(content)
    
    def _basic_pdf_extract(self, content: bytes) -> str:
        """Basic PDF text extraction without pdfplumber."""
        # Very basic extraction - in production use pdfplumber or PyMuPDF
        text = content.decode('latin-1', errors='ignore')
        # Extract text between stream/endstream
        import re
        streams = re.findall(b'stream(.*?)endstream', content, re.DOTALL)
        extracted = []
        for stream in streams:
            try:
                # Try to decode
                decoded = stream.decode('latin-1', errors='ignore')
                # Filter printable
                printable = ''.join(c for c in decoded if c.isprintable() or c in '\n\r\t')
                if len(printable) > 50:
                    extracted.append(printable)
            except:
                pass
        return "\n".join(extracted[:10])  # Limit for basic extraction


class XMLExtractor(ContentExtractor):
    """Extract text from XML documents."""
    
    async def extract(self, content: bytes, metadata: DocumentMetadata) -> str:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            return self._extract_text(root)
        except Exception as e:
            logger.error(f"XML extraction failed: {e}")
            return content.decode('utf-8', errors='ignore')
    
    def _extract_text(self, element, depth=0) -> str:
        texts = []
        if element.text and element.text.strip():
            texts.append(element.text.strip())
        for child in element:
            texts.append(self._extract_text(child, depth + 1))
        if element.tail and element.tail.strip():
            texts.append(element.tail.strip())
        return " ".join(texts)


class PlainTextExtractor(ContentExtractor):
    """Extract text from plain text documents."""
    
    async def extract(self, content: bytes, metadata: DocumentMetadata) -> str:
        return content.decode('utf-8', errors='ignore')


class ImageExtractor(ContentExtractor):
    """Extract text from images using OCR."""
    
    async def extract(self, content: bytes, metadata: DocumentMetadata) -> str:
        try:
            import pytesseract
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(image)
        except ImportError:
            logger.warning("pytesseract/PIL not installed, returning empty")
            return ""


class ExtractorFactory:
    """Factory for creating content extractors."""
    
    _extractors = {
        'application/pdf': PDFExtractor,
        'application/xml': XMLExtractor,
        'text/xml': XMLExtractor,
        'text/plain': PlainTextExtractor,
        'image/jpeg': ImageExtractor,
        'image/png': ImageExtractor,
        'image/tiff': ImageExtractor,
    }
    
    @classmethod
    def get_extractor(cls, mime_type: str) -> ContentExtractor:
        extractor_class = cls._extractors.get(mime_type, PlainTextExtractor)
        return extractor_class()


@dataclass
class IngestionContext:
    """Context passed through ingestion pipeline stages."""
    job: IngestionJob
    document: Optional[Document] = None
    raw_content: Optional[bytes] = None
    extracted_text: Optional[str] = None
    chunks: List[DocumentChunk] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    current_stage: IngestionStage = IngestionStage.FETCH
    stage_start_time: datetime = field(default_factory=datetime.utcnow)
    metrics: Dict[str, Any] = field(default_factory=dict)


class IngestionPipeline:
    """Main ingestion pipeline orchestrator."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        authority_system: Optional[SourceAuthoritySystem] = None,
        security_system: Optional[SecuritySystem] = None,
        embedder: Optional[SentenceTransformerEmbedder] = None,
        vector_store: Optional[ChromaVectorStore] = None,
    ):
        self.settings = settings or get_settings()
        self.authority_system = authority_system or SourceAuthoritySystem(self.settings)
        self.security_system = security_system or SecuritySystem(self.settings)
        self.embedder = embedder or SentenceTransformerEmbedder()
        self.vector_store = vector_store or ChromaVectorStore()
        
        # Validators
        self.validators: List[DocumentValidator] = [
            MaliciousDocumentDetector(self.security_system),
            FormatValidator(),
        ]
        
        # Stage handlers
        self.stage_handlers = {
            IngestionStage.FETCH: self._stage_fetch,
            IngestionStage.VALIDATE: self._stage_validate,
            IngestionStage.EXTRACT: self._stage_extract,
            IngestionStage.CHUNK: self._stage_chunk,
            IngestionStage.ENRICH: self._stage_enrich,
            IngestionStage.INDEX: self._stage_index,
        }
    
    async def ingest(self, job: IngestionJob) -> IngestionJob:
        """Run the full ingestion pipeline for a job."""
        context = IngestionContext(job=job)
        job.status = IngestionStatus.PROCESSING
        job.started_at = datetime.utcnow()
        
        try:
            for stage in IngestionStage:
                if stage == IngestionStage.COMPLETE or stage == IngestionStage.FAILED:
                    break
                
                context.current_stage = stage
                context.stage_start_time = datetime.utcnow()
                
                handler = self.stage_handlers.get(stage)
                if handler:
                    await handler(context)
                
                # Check for errors
                if context.errors:
                    job.status = IngestionStatus.FAILED
                    job.error_message = "; ".join(context.errors)
                    break
            
            if job.status != IngestionStatus.FAILED:
                job.status = IngestionStatus.COMPLETED
                job.document_id = context.document.id if context.document else None
                job.chunks = context.chunks  # Store chunks in job for access
            
        except Exception as e:
            logger.exception(f"Ingestion failed for job {job.id}")
            job.status = IngestionStatus.FAILED
            job.error_message = str(e)
        
        job.completed_at = datetime.utcnow()
        if job.started_at:
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        
        return job
    
    async def _stage_fetch(self, context: IngestionContext) -> None:
        """Fetch document from source."""
        job = context.job
        
        # Determine jurisdiction based on path/source or explicit setting
        source_str = str(job.source_path or job.source_url or "")
        path_norm = source_str.lower().replace("\\", "/")
        if "cbd" in path_norm or "wipo" in path_norm or "intl" in path_norm:
            inferred_jur = JurisdictionCode.INTERNATIONAL
        else:
            inferred_jur = JurisdictionCode.INDIA

        doc_jurisdiction = job.jurisdiction or inferred_jur
        meta_dict = dict(job.metadata or {})
        meta_dict.pop("jurisdiction", None)
        meta_dict.pop("title", None)
        meta_dict.pop("document_type", None)

        if job.source_url:
            context.raw_content = await self._fetch_from_url(job.source_url)
            context.document = Document(
                id=str(uuid.uuid4()),
                source=DocumentSource(
                    url=job.source_url,
                    authority_tier=job.authority_tier or AuthorityTier.TIER_1,
                ),
                metadata=DocumentMetadata(
                    **meta_dict,
                    title=job.title or "Untitled",
                    document_type=job.document_type or DocumentType.PATENT,
                    jurisdiction=doc_jurisdiction,
                ),
            )
        elif job.source_path:
            context.raw_content = await self._fetch_from_file(job.source_path)
            context.document = Document(
                id=str(uuid.uuid4()),
                source=DocumentSource(
                    path=job.source_path,
                    authority_tier=job.authority_tier or AuthorityTier.TIER_1,
                ),
                metadata=DocumentMetadata(
                    **meta_dict,
                    title=job.title or Path(job.source_path).stem,
                    document_type=job.document_type or DocumentType.PATENT,
                    jurisdiction=doc_jurisdiction,
                ),
            )
        elif job.raw_content:
            context.raw_content = job.raw_content
            context.document = Document(
                id=str(uuid.uuid4()),
                source=DocumentSource(
                    authority_tier=job.authority_tier or AuthorityTier.TIER_1,
                ),
                metadata=DocumentMetadata(
                    **meta_dict,
                    title=job.title or "Untitled",
                    document_type=job.document_type or DocumentType.PATENT,
                    jurisdiction=doc_jurisdiction,
                ),
            )
        else:
            context.errors.append("No source specified for ingestion")
        
        if context.raw_content:
            context.document.content_hash = hashlib.sha256(context.raw_content).hexdigest()
            context.document.size_bytes = len(context.raw_content)
        
        context.metrics['fetch_time_ms'] = (
            datetime.utcnow() - context.stage_start_time
        ).total_seconds() * 1000
    
    async def _fetch_from_url(self, url: str) -> bytes:
        """Fetch document from URL with security checks."""
        parsed = urlparse(url)
        if not self.security_system.is_allowed_domain(parsed.netloc):
            raise ValueError(f"Domain {parsed.netloc} not in allowed list")
        
        def _get():
            req = urllib.request.Request(url, headers={"User-Agent": "IP-Sakti-Ingestion/1.0"})
            with urllib.request.urlopen(req, timeout=self.settings.fetch_timeout_seconds) as response:
                return response.read()

        content = await asyncio.to_thread(_get)
        if len(content) > self.settings.max_document_size_mb * 1024 * 1024:
            raise ValueError("Document too large")
        return content
    
    async def _fetch_from_file(self, path: str) -> bytes:
        """Fetch document from local file."""
        file_path = Path(path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return await asyncio.to_thread(file_path.read_bytes)
    
    async def _stage_validate(self, context: IngestionContext) -> None:
        """Validate document against security and format rules."""
        if not context.document or not context.raw_content:
            context.errors.append("No document or content to validate")
            return
        
        # Detect actual MIME type from content bytes (more reliable than extension)
        from ip_sakti.security.security_system import DocumentValidator as SecurityDocValidator
        sec_validator = SecurityDocValidator()
        detected_mime = sec_validator._detect_mime_type(context.raw_content)
        
        # Use detected MIME type as the authoritative type
        # If detection fails (text/plain), fall back to extension guess
        if detected_mime != "text/plain":
            context.document.metadata.mime_type = detected_mime
        else:
            context.document.metadata.mime_type = mimetypes.guess_type(context.document.source.path or "")[0] or "text/plain"
        
        logger.info(f"Detected MIME type: {context.document.metadata.mime_type}")
        
        # Run all validators
        for validator in self.validators:
            is_valid, errors = await validator.validate(context.raw_content, context.document.metadata)
            if not is_valid:
                context.errors.extend(errors)
                break
        
        # Verify authority tier
        if context.document.source.authority_tier:
            try:
                tier_valid = self.authority_system.verify_tier(
                    context.document.source.authority_tier,
                    context.document.metadata
                )
                if not tier_valid:
                    logger.warning(f"Authority tier verification warning for {context.job.source_path}")
            except Exception as e:
                logger.warning(f"Authority tier verification skipped: {e}")
        
        context.metrics['validate_time_ms'] = (
            datetime.utcnow() - context.stage_start_time
        ).total_seconds() * 1000
    
    async def _stage_extract(self, context: IngestionContext) -> None:
        """Extract text content from document using LangChain loaders."""
        if not context.document or not context.job.source_path:
            context.errors.append("No document or source path to extract")
            return
        
        source_path = str(context.job.source_path)
        p = Path(source_path)
        if p.suffix.lower() == ".pdf":
            txt_alt = p.with_suffix(".txt")
            if txt_alt.exists():
                source_path = str(txt_alt)

        # Use the new document loaders
        from ip_sakti.ingestion.loaders import load_document
        
        try:
            loaded_docs = await load_document(source_path)
            
            if not loaded_docs:
                context.errors.append("No content extracted from document")
                return
            
            # Combine all loaded documents
            text_parts = []
            for doc in loaded_docs:
                if doc.content and doc.content.strip():
                    text_parts.append(doc.content.strip())
            
            context.extracted_text = "\n\n".join(text_parts)
            
            if not context.extracted_text or len(context.extracted_text.strip()) < 10:
                context.errors.append("Extracted text too short or empty")
            
            context.document.content = context.extracted_text
            
        except Exception as e:
            logger.error(f"Document loading failed: {e}")
            context.errors.append(f"Document loading failed: {e}")
        
        context.metrics['extract_time_ms'] = (
            datetime.utcnow() - context.stage_start_time
        ).total_seconds() * 1000
        context.metrics['extracted_chars'] = len(context.extracted_text) if context.extracted_text else 0
    
    async def _stage_chunk(self, context: IngestionContext) -> None:
        """Chunk document using chunking strategy (Phase 8)."""
        from ip_sakti.ingestion.chunking import ChunkingStrategy, ChunkingConfig, ChunkingStrategyType
        
        if not context.document or not context.extracted_text:
            context.errors.append("No document or text to chunk")
            return
        
        config = ChunkingConfig(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            strategy=ChunkingStrategyType(self.settings.chunking_strategy),
        )
        
        chunker = ChunkingStrategy(config)
        context.chunks = await chunker.chunk_document(context.document, context.extracted_text)
        
        context.metrics['chunk_time_ms'] = (
            datetime.utcnow() - context.stage_start_time
        ).total_seconds() * 1000
        context.metrics['num_chunks'] = len(context.chunks)
    
    async def _stage_enrich(self, context: IngestionContext) -> None:
        """Enrich chunks with metadata, embeddings, authority scores."""
        if not context.document or not context.chunks:
            return
        
        # Assign authority scores based on source tier
        authority_score = self.authority_system.get_tier_score(
            context.document.source.authority_tier
        )
        
        jur_val = context.document.metadata.jurisdiction
        jur_str = str(jur_val.value if hasattr(jur_val, "value") else jur_val or "INDIA").upper()
        jur_tag = "INDIA" if ("INDIA" in jur_str or "IN-" in jur_str) else "INTL"
        
        tier_val = context.document.source.authority_tier
        tier_str = tier_val.value if hasattr(tier_val, "value") else str(tier_val or "tier1")

        for chunk in context.chunks:
            chunk.document_id = context.document.id
            chunk.authority_score = authority_score
            chunk.jurisdiction = jur_tag
            chunk.document_type = context.document.metadata.document_type
            
            # Add source metadata
            chunk.metadata.update({
                'source_authority_tier': tier_str,
                'source_url': context.document.source.url,
                'source_path': context.document.source.path,
                'ingestion_job_id': context.job.id,
                'jurisdiction': jur_tag,
            })
        
        context.metrics['enrich_time_ms'] = (
            datetime.utcnow() - context.stage_start_time
        ).total_seconds() * 1000
    
    async def _stage_index(self, context: IngestionContext) -> None:
        """Index chunks into Chroma vector store."""
        if not context.chunks:
            return
        
        texts = [c.content for c in context.chunks]
        vectors = await self.embedder.embed(texts)
        await self.vector_store.upsert(context.chunks, vectors)

        if context.document:
            context.document.chunks = context.chunks
        
        context.metrics['index_time_ms'] = (
            datetime.utcnow() - context.stage_start_time
        ).total_seconds() * 1000


class BatchIngestionManager:
    """Manages batch ingestion jobs."""
    
    def __init__(self, pipeline: IngestionPipeline, max_concurrent: int = 5):
        self.pipeline = pipeline
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_jobs: Dict[str, IngestionJob] = {}
    
    async def ingest_batch(self, jobs: List[IngestionJob]) -> List[IngestionJob]:
        """Ingest multiple jobs concurrently."""
        async def ingest_one(job: IngestionJob) -> IngestionJob:
            async with self.semaphore:
                self.active_jobs[job.id] = job
                try:
                    return await self.pipeline.ingest(job)
                finally:
                    self.active_jobs.pop(job.id, None)
        
        return await asyncio.gather(*[ingest_one(job) for job in jobs])
    
    def get_active_jobs(self) -> List[IngestionJob]:
        """Get currently active ingestion jobs."""
        return list(self.active_jobs.values())


def create_ingestion_pipeline(
    settings: Optional[Settings] = None,
    authority_system: Optional[SourceAuthoritySystem] = None,
    security_system: Optional[SecuritySystem] = None,
) -> IngestionPipeline:
    """Factory to create ingestion pipeline."""
    return IngestionPipeline(settings, authority_system, security_system)


async def run_corpus_ingestion(corpus_dir: str = "data/corpus") -> Dict[str, Any]:
    """Ingest all documents from data/corpus/ into ChromaDB."""
    pipeline = create_ingestion_pipeline()
    await pipeline.vector_store.initialize()

    corpus_path = Path(corpus_dir).resolve()
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_path}")

    # Gather text files (each PDF has a corresponding .txt)
    txt_files = sorted(list(corpus_path.rglob("*.txt")))
    logger.info(f"Found {len(txt_files)} text files to ingest from {corpus_path}")

    total_chunks = 0
    success_count = 0

    for file_path in txt_files:
        if file_path.stat().st_size == 0:
            print(f"Skipping empty file: {file_path.name}")
            continue

        path_str = str(file_path).replace("\\", "/")
        path_lower = path_str.lower()

        # Tag jurisdiction: INDIA for Indian laws, INTL for international
        if "cbd" in path_lower or "wipo" in path_lower or "intl" in path_lower:
            jur = JurisdictionCode.INTERNATIONAL
            jur_tag = "INTL"
        else:
            jur = JurisdictionCode.INDIA
            jur_tag = "INDIA"

        # Authority & type
        if "act" in path_lower:
            doc_type = DocumentType.ACT
            tier = AuthorityTier.TIER_1
        elif "rule" in path_lower:
            doc_type = DocumentType.RULE
            tier = AuthorityTier.TIER_2
        elif "guideline" in path_lower or "form" in path_lower:
            doc_type = DocumentType.GUIDELINE
            tier = AuthorityTier.TIER_5
        elif "treaty" in path_lower or "protocol" in path_lower or "agreement" in path_lower or "pct" in path_lower:
            doc_type = DocumentType.TREATY
            tier = AuthorityTier.TIER_1
        else:
            doc_type = DocumentType.PATENT
            tier = AuthorityTier.TIER_1

        job = IngestionJob(
            id=str(uuid.uuid4()),
            source_path=str(file_path),
            title=file_path.stem.replace("_", " ").title(),
            document_type=doc_type,
            jurisdiction=jur,
            authority_tier=tier,
            metadata={"jurisdiction": jur_tag},
        )

        print(f"Ingesting [{jur_tag}] {file_path.name}...")
        result = await pipeline.ingest(job)
        if result.status == IngestionStatus.COMPLETED:
            success_count += 1
            num_ch = len(result.chunks or [])
            total_chunks += num_ch
            print(f"  -> Ingested {num_ch} chunks.")
        else:
            print(f"  -> FAILED: {result.error_message}")

    stats = await pipeline.vector_store.get_stats()
    print(f"\nIngestion Complete: {success_count}/{len(txt_files)} files processed, {total_chunks} chunks embedded.")
    print(f"Vector Store Stats: {stats}")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_corpus_ingestion())