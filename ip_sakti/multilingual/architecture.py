"""
IP-SAKTI Multilingual Architecture
Phase 17: Implements the multilingual architecture for cross-language IP analysis.
Supports translation, cross-lingual retrieval, and multilingual generation.
"""

import asyncio
import logging
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
    Language,
)

logger = logging.getLogger(__name__)


class TranslationEngine(str, Enum):
    """Translation engine types."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    DEEPL = "deepl"
    LIBRETRANSLATE = "libretranslate"
    M2M100 = "m2m100"
    NLLB = "nllb"
    MOCK = "mock"


class EmbeddingAlignment(str, Enum):
    """Cross-lingual embedding alignment methods."""
    NONE = "none"
    LINEAR = "linear"
    ORTHOGONAL = "orthogonal"
    ADVERSARIAL = "adversarial"
    LASER = "laser"
    LABSE = "labse"


@dataclass
class MultilingualConfig:
    """Configuration for multilingual processing."""
    supported_languages: List[Language] = field(default_factory=lambda: [
        Language.EN, Language.HI, Language.ZH, Language.JA, Language.KO,
        Language.DE, Language.FR, Language.ES, Language.PT, Language.RU,
        Language.AR, Language.IT, Language.NL, Language.PL, Language.TR,
    ])
    default_language: Language = Language.EN
    translation_engine: TranslationEngine = TranslationEngine.MOCK
    translation_config: Dict[str, Any] = field(default_factory=dict)
    embedding_alignment: EmbeddingAlignment = EmbeddingAlignment.LABSE
    cross_lingual_retrieval: bool = True
    translate_queries: bool = True
    translate_results: bool = True
    max_translation_length: int = 5000
    cache_translations: bool = True
    cache_ttl_hours: int = 168  # 1 week


@dataclass
class TranslationResult:
    """Result of translation."""
    source_text: str
    translated_text: str
    source_language: Language
    target_language: Language
    confidence: float
    engine: TranslationEngine
    translated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultilingualDocument:
    """Document with multilingual content."""
    original_document: Document
    translations: Dict[Language, str] = field(default_factory=dict)  # language -> translated content
    translation_metadata: Dict[Language, Dict[str, Any]] = field(default_factory=dict)
    detected_language: Optional[Language] = None


class LanguageDetector(ABC):
    """Abstract base for language detection."""
    
    @abstractmethod
    async def detect(self, text: str) -> Tuple[Language, float]:
        """Detect language of text. Returns (language, confidence)."""
        pass
    
    @abstractmethod
    async def detect_batch(self, texts: List[str]) -> List[Tuple[Language, float]]:
        pass


class MockLanguageDetector(LanguageDetector):
    """Mock language detector for development."""
    
    # Simple heuristic based on character sets
    LANGUAGE_PATTERNS = {
        Language.ZH: r'[\u4e00-\u9fff]',
        Language.JA: r'[\u3040-\u309f\u30a0-\u30ff]',
        Language.KO: r'[\uac00-\ud7af]',
        Language.AR: r'[\u0600-\u06ff]',
        Language.RU: r'[\u0400-\u04ff]',
        Language.HI: r'[\u0900-\u097f]',
    }
    
    async def detect(self, text: str) -> Tuple[Language, float]:
        # Check for specific scripts
        for lang, pattern in self.LANGUAGE_PATTERNS.items():
            if re.search(pattern, text):
                return lang, 0.9
        
        # Default to English for Latin script
        return Language.EN, 0.7
    
    async def detect_batch(self, texts: List[str]) -> List[Tuple[Language, float]]:
        return [await self.detect(text) for text in texts]


import re


class Translator(ABC):
    """Abstract base for translators."""
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> TranslationResult:
        pass
    
    @abstractmethod
    async def translate_batch(
        self,
        texts: List[str],
        source_language: Language,
        target_language: Language,
    ) -> List[TranslationResult]:
        pass


class MockTranslator(Translator):
    """Mock translator for development."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> TranslationResult:
        # Mock translation - just add a prefix
        if source_language == target_language:
            translated = text
            confidence = 1.0
        else:
            translated = f"[{target_language.value}] {text}"
            confidence = 0.8
        
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_language,
            target_language=target_language,
            confidence=confidence,
            engine=TranslationEngine.MOCK,
        )
    
    async def translate_batch(
        self,
        texts: List[str],
        source_language: Language,
        target_language: Language,
    ) -> List[TranslationResult]:
        return [await self.translate(text, source_language, target_language) for text in texts]


class CrossLingualEmbedder(ABC):
    """Abstract base for cross-lingual embeddings."""
    
    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        languages: List[Language],
    ) -> List[List[float]]:
        """Generate aligned embeddings for multilingual texts."""
        pass
    
    @abstractmethod
    async def embed_query(
        self,
        query: str,
        language: Language,
    ) -> List[float]:
        pass


class MockCrossLingualEmbedder(CrossLingualEmbedder):
    """Mock cross-lingual embedder."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    async def embed(
        self,
        texts: List[str],
        languages: List[Language],
    ) -> List[List[float]]:
        # Generate deterministic embeddings
        import numpy as np
        embeddings = []
        for text, lang in zip(texts, languages):
            # Include language in hash for alignment
            combined = f"{lang.value}:{text}"
            hash_val = hash(combined)
            np.random.seed(abs(hash_val) % (2**32))
            emb = np.random.randn(self.dimension).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())
        return embeddings
    
    async def embed_query(self, query: str, language: Language) -> List[float]:
        result = await self.embed([query], [language])
        return result[0]


class MultilingualRetriever:
    """Cross-lingual retrieval system."""
    
    def __init__(
        self,
        config: MultilingualConfig,
        embedder: CrossLingualEmbedder,
        translator: Translator,
    ):
        self.config = config
        self.embedder = embedder
        self.translator = translator
        
        # In production, would connect to vector store
        self.vector_store = None
    
    async def search(
        self,
        query: str,
        query_language: Language,
        target_languages: List[Language],
        top_k: int = 10,
    ) -> List[Tuple[DocumentChunk, float, Language]]:
        """Search across languages."""
        
        if not self.config.cross_lingual_retrieval:
            # Single language search
            return await self._search_single_language(query, query_language, top_k)
        
        # Translate query to target languages
        queries = {query_language: query}
        
        if self.config.translate_queries:
            for lang in target_languages:
                if lang != query_language:
                    result = await self.translator.translate(query, query_language, lang)
                    queries[lang] = result.translated_text
        
        # Search in each language
        all_results = []
        for lang, q in queries.items():
            results = await self._search_single_language(q, lang, top_k)
            for chunk, score in results:
                all_results.append((chunk, score, lang))
        
        # Merge and deduplicate
        return self._merge_results(all_results, top_k)
    
    async def _search_single_language(
        self,
        query: str,
        language: Language,
        top_k: int,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search in a single language (placeholder)."""
        # In production, would query vector store with language filter
        return []
    
    def _merge_results(
        self,
        results: List[Tuple[DocumentChunk, float, Language]],
        top_k: int,
    ) -> List[Tuple[DocumentChunk, float, Language]]:
        """Merge results from multiple languages."""
        # Deduplicate by chunk ID, keep highest score
        seen = {}
        for chunk, score, lang in results:
            key = chunk.id
            if key not in seen or score > seen[key][1]:
                seen[key] = (chunk, score, lang)
        
        # Sort by score
        merged = list(seen.values())
        merged.sort(key=lambda x: x[1], reverse=True)
        
        return merged[:top_k]


class MultilingualGenerator:
    """Multilingual answer generation."""
    
    def __init__(
        self,
        config: MultilingualConfig,
        translator: Translator,
    ):
        self.config = config
        self.translator = translator
    
    async def generate(
        self,
        query: str,
        context_chunks: List[DocumentChunk],
        citations: List[Any],  # Citation objects
        target_language: Language,
    ) -> Tuple[str, List[Any]]:
        """Generate answer in target language."""
        
        # For now, generate in English then translate
        # In production, could use multilingual LLM directly
        
        # Generate in English (placeholder)
        english_answer = self._generate_english_answer(query, context_chunks, citations)
        
        # Translate if needed
        if target_language != Language.EN:
            result = await self.translator.translate(english_answer, Language.EN, target_language)
            answer = result.translated_text
            
            # Also translate citations
            translated_citations = await self._translate_citations(citations, target_language)
        else:
            answer = english_answer
            translated_citations = citations
        
        return answer, translated_citations
    
    def _generate_english_answer(
        self,
        query: str,
        context_chunks: List[DocumentChunk],
        citations: List[Any],
    ) -> str:
        """Generate answer in English (placeholder)."""
        if not citations:
            return "I could not find relevant information to answer your query."
        
        return f"Based on {len(citations)} sources, here is the answer to your query about {query[:50]}..."
    
    async def _translate_citations(
        self,
        citations: List[Any],
        target_language: Language,
    ) -> List[Any]:
        """Translate citation metadata."""
        translated = []
        for cite in citations:
            # Create copy with translated text
            new_cite = cite.__class__(**cite.__dict__)
            if hasattr(cite, 'text') and cite.text:
                result = await self.translator.translate(cite.text, Language.EN, target_language)
                new_cite.text = result.translated_text
            translated.append(new_cite)
        return translated


class MultilingualPipeline:
    """Main multilingual processing pipeline."""
    
    def __init__(
        self,
        config: Optional[MultilingualConfig] = None,
        settings: Optional[Settings] = None,
    ):
        self.config = config or MultilingualConfig()
        self.settings = settings or get_settings()
        
        # Components
        self.language_detector = MockLanguageDetector()
        self.translator = self._create_translator()
        self.embedder = MockCrossLingualEmbedder(
            dimension=self.settings.embedding.dimension
        )
        self.retriever = MultilingualRetriever(self.config, self.embedder, self.translator)
        self.generator = MultilingualGenerator(self.config, self.translator)
        
        # Translation cache
        self._translation_cache: Dict[str, TranslationResult] = {}
    
    def _create_translator(self) -> Translator:
        engine = self.config.translation_engine
        config = self.config.translation_config
        
        if engine == TranslationEngine.MOCK:
            return MockTranslator(config)
        # elif engine == TranslationEngine.GOOGLE:
        #     return GoogleTranslator(config)
        # elif engine == TranslationEngine.DEEPL:
        #     return DeepLTranslator(config)
        
        logger.warning(f"Translation engine {engine} not implemented, using mock")
        return MockTranslator(config)
    
    async def process_document(
        self,
        document: Document,
        target_languages: Optional[List[Language]] = None,
    ) -> MultilingualDocument:
        """Process document for multilingual support."""
        target_languages = target_languages or self.config.supported_languages
        
        # Detect source language
        detected_lang, confidence = await self.language_detector.detect(document.content or "")
        
        multilingual_doc = MultilingualDocument(
            original_document=document,
            detected_language=detected_lang,
        )
        
        # Translate to target languages
        for lang in target_languages:
            if lang != detected_lang:
                cache_key = f"{document.id}_{detected_lang.value}_{lang.value}"
                
                if self.config.cache_translations and cache_key in self._translation_cache:
                    result = self._translation_cache[cache_key]
                else:
                    result = await self.translator.translate(
                        document.content or "",
                        detected_lang,
                        lang,
                    )
                    if self.config.cache_translations:
                        self._translation_cache[cache_key] = result
                
                multilingual_doc.translations[lang] = result.translated_text
                multilingual_doc.translation_metadata[lang] = {
                    'confidence': result.confidence,
                    'engine': result.engine.value,
                    'translated_at': result.translated_at.isoformat(),
                }
        
        return multilingual_doc
    
    async def process_chunks(
        self,
        chunks: List[DocumentChunk],
        target_languages: Optional[List[Language]] = None,
    ) -> Dict[str, Dict[Language, str]]:
        """Process chunks for multilingual support.
        
        Returns: chunk_id -> {language -> translated_text}
        """
        target_languages = target_languages or self.config.supported_languages
        results = {}
        
        # Group chunks by detected language for batch translation
        lang_groups: Dict[Language, List[DocumentChunk]] = {}
        for chunk in chunks:
            lang, _ = await self.language_detector.detect(chunk.content)
            if lang not in lang_groups:
                lang_groups[lang] = []
            lang_groups[lang].append(chunk)
        
        # Translate each group
        for source_lang, lang_chunks in lang_groups.items():
            texts = [c.content for c in lang_chunks]
            
            for target_lang in target_languages:
                if target_lang == source_lang:
                    for chunk in lang_chunks:
                        if chunk.id not in results:
                            results[chunk.id] = {}
                        results[chunk.id][target_lang] = chunk.content
                    continue
                
                cache_key = f"batch_{source_lang.value}_{target_lang.value}_{len(texts)}"
                
                if self.config.cache_translations and cache_key in self._translation_cache:
                    translations = self._translation_cache[cache_key].translated_text.split('\n---\n')
                else:
                    batch_results = await self.translator.translate_batch(texts, source_lang, target_lang)
                    translations = [r.translated_text for r in batch_results]
                    if self.config.cache_translations:
                        self._translation_cache[cache_key] = TranslationResult(
                            source_text='\n---\n'.join(texts),
                            translated_text='\n---\n'.join(translations),
                            source_language=source_lang,
                            target_language=target_lang,
                            confidence=sum(r.confidence for r in batch_results) / len(batch_results),
                            engine=self.config.translation_engine,
                        )
                
                for chunk, translated in zip(lang_chunks, translations):
                    if chunk.id not in results:
                        results[chunk.id] = {}
                    results[chunk.id][target_lang] = translated
        
        return results
    
    async def answer_query(
        self,
        query: str,
        target_language: Optional[Language] = None,
        context_chunks: Optional[List[DocumentChunk]] = None,
        citations: Optional[List[Any]] = None,
    ) -> Tuple[str, List[Any], Language]:
        """Answer query in target language."""
        target_language = target_language or self.config.default_language
        
        # Detect query language
        query_lang, _ = await self.language_detector.detect(query)
        
        # If we need to retrieve, do cross-lingual retrieval
        if context_chunks is None:
            # Would retrieve here
            context_chunks = []
            citations = []
        
        # Generate answer
        answer, translated_citations = await self.generator.generate(
            query, context_chunks, citations or [], target_language
        )
        
        return answer, translated_citations, query_lang
    
    async def translate_query(
        self,
        query: str,
        target_language: Language,
    ) -> TranslationResult:
        """Translate a query."""
        source_lang, _ = await self.language_detector.detect(query)
        return await self.translator.translate(query, source_lang, target_language)
    
    def get_supported_languages(self) -> List[Language]:
        """Get supported languages."""
        return self.config.supported_languages
    
    def clear_cache(self) -> None:
        """Clear translation cache."""
        self._translation_cache.clear()


# Jurisdiction-specific language mappings
JURISDICTION_LANGUAGES = {
    Jurisdiction.US: [Language.EN, Language.ES],
    Jurisdiction.EP: [Language.EN, Language.DE, Language.FR],
    Jurisdiction.WO: [Language.EN, Language.FR, Language.ES, Language.ZH, Language.AR, Language.RU],
    Jurisdiction.IN: [Language.EN, Language.HI],
    Jurisdiction.CN: [Language.ZH, Language.EN],
    Jurisdiction.JP: [Language.JA, Language.EN],
    Jurisdiction.KR: [Language.KO, Language.EN],
    Jurisdiction.DE: [Language.DE, Language.EN],
    Jurisdiction.FR: [Language.FR, Language.EN],
    Jurisdiction.UK: [Language.EN],
    Jurisdiction.CA: [Language.EN, Language.FR],
    Jurisdiction.AU: [Language.EN],
    Jurisdiction.BR: [Language.PT, Language.EN],
    Jurisdiction.MX: [Language.ES, Language.EN],
}


def get_jurisdiction_languages(jurisdiction: Jurisdiction) -> List[Language]:
    """Get official languages for a jurisdiction."""
    return JURISDICTION_LANGUAGES.get(jurisdiction, [Language.EN])


def create_multilingual_pipeline(
    config: Optional[MultilingualConfig] = None,
    settings: Optional[Settings] = None,
) -> MultilingualPipeline:
    """Factory to create multilingual pipeline."""
    return MultilingualPipeline(config, settings)