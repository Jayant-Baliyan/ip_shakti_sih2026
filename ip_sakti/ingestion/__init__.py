"""
IP-SAKTI Ingestion Package
"""

from ip_sakti.ingestion.pipeline import (
    IngestionPipeline,
    IngestionStage,
    IngestionContext,
    BatchIngestionManager,
    DocumentValidator,
    MaliciousDocumentDetector,
    FormatValidator,
    ContentExtractor,
    PDFExtractor,
    XMLExtractor,
    PlainTextExtractor,
    ImageExtractor,
    ExtractorFactory,
)

from ip_sakti.ingestion.chunking import (
    ChunkingStrategy,
    ChunkingConfig,
    ChunkingStrategyType,
    BaseChunker,
    FixedSizeChunker,
    StructuralChunker,
    SemanticChunker,
    LegalStructuralChunker,
    PatentClaimsChunker,
    HybridChunker,
    create_chunker,
)

__all__ = [
    # Pipeline
    "IngestionPipeline",
    "IngestionStage",
    "IngestionContext",
    "BatchIngestionManager",
    # Validators
    "DocumentValidator",
    "MaliciousDocumentDetector",
    "FormatValidator",
    # Extractors
    "ContentExtractor",
    "PDFExtractor",
    "XMLExtractor",
    "PlainTextExtractor",
    "ImageExtractor",
    "ExtractorFactory",
    # Chunking
    "ChunkingStrategy",
    "ChunkingConfig",
    "ChunkingStrategyType",
    "BaseChunker",
    "FixedSizeChunker",
    "StructuralChunker",
    "SemanticChunker",
    "LegalStructuralChunker",
    "PatentClaimsChunker",
    "HybridChunker",
    "create_chunker",
]