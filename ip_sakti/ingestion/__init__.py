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
    RecursiveChunker,
    SemanticChunker,
    create_chunker,
)

from ip_sakti.ingestion.loaders import (
    DocumentLoaderRegistry,
    LoadedDocument,
    DocumentFormat,
    BaseDocumentLoader,
    TextLoaderWrapper,
    PDFLoaderWrapper,
    DocxLoaderWrapper,
    HTMLLoaderWrapper,
    MarkdownLoaderWrapper,
    XMLLoaderWrapper,
    FallbackLoaderWrapper,
    get_loader_registry,
    load_document,
    detect_format,
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
    "RecursiveChunker",
    "SemanticChunker",
    "create_chunker",
    # Loaders
    "DocumentLoaderRegistry",
    "LoadedDocument",
    "DocumentFormat",
    "BaseDocumentLoader",
    "TextLoaderWrapper",
    "PDFLoaderWrapper",
    "DocxLoaderWrapper",
    "HTMLLoaderWrapper",
    "MarkdownLoaderWrapper",
    "XMLLoaderWrapper",
    "FallbackLoaderWrapper",
    "get_loader_registry",
    "load_document",
    "detect_format",
]