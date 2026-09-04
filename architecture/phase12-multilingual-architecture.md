# Phase 12: Multilingual Architecture

## 1. Overview

The Multilingual Architecture enables **query, retrieval, and generation in 13+ Indian languages plus English**, with **legal terminology preservation**, **script-aware processing**, and **citation integrity** across languages. It ensures that a user asking in Hindi, Tamil, or Bengali receives accurate legal answers with citations traceable to authoritative English/Hindi source texts.

### 1.1 Supported Languages

| Language | Code | Script | Speakers (M) | Priority | Legal Corpus Availability |
|----------|------|--------|--------------|----------|---------------------------|
| English | en | Latin | 125 | **CORE** | Full (official) |
| Hindi | hi | Devanagari | 528 | **CORE** | High (official translations) |
| Bengali | bn | Bengali | 97 | **HIGH** | Medium |
| Marathi | mr | Devanagari | 83 | **HIGH** | Medium |
| Tamil | ta | Tamil | 69 | **HIGH** | Medium |
| Telugu | te | Telugu | 81 | **HIGH** | Low |
| Gujarati | gu | Gujarati | 55 | **HIGH** | Low |
| Kannada | kn | Kannada | 44 | **MEDIUM** | Low |
| Malayalam | ml | Malayalam | 34 | **MEDIUM** | Low |
| Punjabi | pa | Gurmukhi | 33 | **MEDIUM** | Low |
| Odia | or | Odia | 37 | **MEDIUM** | Low |
| Assamese | as | Bengali | 15 | **MEDIUM** | Low |
| Urdu | ur | Nastaliq | 70 | **MEDIUM** | Low |

### 1.2 Core Requirements

| Requirement | Description |
|-------------|-------------|
| **FR-ML-01** | Accept queries in any supported language |
| **FR-ML-02** | Retrieve relevant evidence across languages (cross-lingual retrieval) |
| **FR-ML-03** | Generate answers in query language |
| **FR-ML-04** | Preserve legal terminology (don't translate "Section 3(d)", "prior informed consent") |
| **FR-ML-05** | Maintain citation integrity: citations point to original source language chunks |
| **FR-ML-06** | Handle script conversion (Devanagari ↔ Latin transliteration) |
| **FR-ML-07** | Support code-switching (mixed English + Indian language queries) |
| **FR-ML-08** | Legal term glossary per language (authoritative translations) |

| Non-Functional | Target |
|----------------|--------|
| **NFR-ML-01** | Cross-lingual retrieval recall: > 85% vs monolingual |
| **NFR-ML-02** | Translation quality (BLEU): > 35 for legal domain |
| **NFR-ML-03** | Terminology preservation accuracy: 100% for protected terms |
| **NFR-ML-04** | Generation latency overhead: < 500ms vs English-only |
| **NFR-ML-05** | Script handling: zero data loss |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTILINGUAL PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

USER QUERY (any language)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. LANGUAGE IDENTIFICATION & SCRIPT NORMALIZATION                           │
│    - Detect language (fastText / CLD3)                                      │
│    - Normalize script (NFC, indic normalization)                            │
│    - Extract protected terms (legal terminology)                            │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. QUERY TRANSLATION / EXPANSION                                            │
│    - Option A: Translate query → English for retrieval                     │
│    - Option B: Multi-vector query (original + translated)                  │
│    - Option C: bge-m3 multilingual embedding (preferred)                   │
│    - Expand with legal synonyms from glossary                              │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. MULTILINGUAL RETRIEVAL (Phase 6 + Phase 9)                               │
│    - Dense: bge-m3 (100+ languages, single model)                          │
│    - Sparse: Language-specific BM25 (IndicBERT tokenizer)                  │
│    - Cross-lingual: English chunks retrieved for non-English queries       │
│    - Jurisdiction filter applied (Phase 9)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. EVIDENCE PROCESSING                                                      │
│    - Chunks have: original_text, language, translation (if available)      │
│    - Protected terms marked with metadata                                   │
│    - Authority tier preserved                                               │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. CITATION-FIRST GENERATION (Phase 10)                                     │
│    - Claims extracted in source language                                    │
│    - Answer composed in query language                                      │
│    - Citations reference original chunks (with translation if needed)      │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. ANSWER TRANSLATION / LOCALIZATION                                        │
│    - If generation in English: translate to query language                 │
│    - Protected terms kept in original (English/legal)                      │
│    - Citations formatted for target language                               │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
FINAL ANSWER (query language) + CITATIONS (with original source refs)
```

---

## 3. Language Identification & Script Handling

### 3.1 Language Detection

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum
import fasttext
import langdetect

class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    MARATHI = "mr"
    TAMIL = "ta"
    TELUGU = "te"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    ODIA = "or"
    ASSAMESE = "as"
    URDU = "ur"

class Script(str, Enum):
    LATIN = "latn"
    DEVANAGARI = "deva"
    BENGALI = "beng"
    TAMIL = "taml"
    TELUGU = "telu"
    GUJARATI = "gujr"
    KANNADA = "knda"
    MALAYALAM = "mlym"
    GURMUKHI = "guru"
    ODIA = "orya"
    NASTALIQ = "arab"

LANGUAGE_SCRIPT_MAP = {
    SupportedLanguage.ENGLISH: Script.LATIN,
    SupportedLanguage.HINDI: Script.DEVANAGARI,
    SupportedLanguage.MARATHI: Script.DEVANAGARI,
    SupportedLanguage.BENGALI: Script.BENGALI,
    SupportedLanguage.ASSAMESE: Script.BENGALI,
    SupportedLanguage.TAMIL: Script.TAMIL,
    SupportedLanguage.TELUGU: Script.TELUGU,
    SupportedLanguage.GUJARATI: Script.GUJARATI,
    SupportedLanguage.KANNADA: Script.KANNADA,
    SupportedLanguage.MALAYALAM: Script.MALAYALAM,
    SupportedLanguage.PUNJABI: Script.GURMUKHI,
    SupportedLanguage.ODIA: Script.ODIA,
    SupportedLanguage.URDU: Script.NASTALIQ,
}

@dataclass
class LanguageDetectionResult:
    language: SupportedLanguage
    confidence: float
    script: Script
    is_code_switched: bool = False
    english_segments: List[str] = field(default_factory=list)
    indic_segments: List[str] = field(default_factory=list)

class LanguageIdentifier:
    """
    Identifies query language and handles code-switching.
    """
    
    def __init__(self):
        self.fasttext_model = fasttext.load_model("lid.176.ftz")
        self.indic_tokenizer = IndicTokenizer()  # For script-level detection
    
    def identify(self, text: str) -> LanguageDetectionResult:
        # Normalize unicode
        text = self._normalize_unicode(text)
        
        # FastText detection
        predictions = self.fasttext_model.predict(text, k=3)
        lang_code = predictions[0][0].replace("__label__", "")
        confidence = predictions[1][0]
        
        # Map to supported language
        language = self._map_to_supported(lang_code)
        
        # Check for code-switching (English + Indic)
        is_cs, en_segs, indic_segs = self._detect_code_switching(text)
        
        script = LANGUAGE_SCRIPT_MAP.get(language, Script.LATIN)
        
        return LanguageDetectionResult(
            language=language,
            confidence=confidence,
            script=script,
            is_code_switched=is_cs,
            english_segments=en_segs,
            indic_segments=indic_segs
        )
    
    def _detect_code_switching(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """Detect English-Indic code switching using script detection."""
        # Split by script runs
        script_runs = self._split_by_script(text)
        
        english_segments = []
        indic_segments = []
        
        for run_text, script in script_runs:
            if script == Script.LATIN:
                # Check if actually English (not transliteration)
                if self._is_english(run_text):
                    english_segments.append(run_text)
            else:
                indic_segments.append(run_text)
        
        is_cs = len(english_segments) > 0 and len(indic_segments) > 0
        return is_cs, english_segments, indic_segments
    
    def _normalize_unicode(self, text: str) -> str:
        """NFC normalization + Indic-specific normalization."""
        import unicodedata
        text = unicodedata.normalize('NFC', text)
        
        # Indic normalization (virama handling, etc.)
        # Use indic-nlp-library or similar
        return text
```

### 3.2 Script Transliteration

```python
class ScriptTransliterator:
    """
    Transliteration between scripts for Indic languages.
    Uses indic-trans library or custom mappings.
    """
    
    # Devanagari ↔ ITRANS (ASCII) mappings for Hindi/Marathi/Sanskrit
    DEVANAGARI_TO_ITRANS = {
        'अ': 'a', 'आ': 'A', 'इ': 'i', 'ई': 'I', 'उ': 'u', 'ऊ': 'U',
        'ऋ': 'RRi', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'N',
        'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'JN',
        'ट': 'T', 'ठ': 'Th', 'ड': 'D', 'ढ': 'Dh', 'ण': 'N',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
        'ष': 'Sh', 'स': 's', 'ह': 'h', 'ळ': 'L',
        'ा': 'A', 'ि': 'i', 'ी': 'I', 'ु': 'u', 'ू': 'U',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', '्': '',
        'ं': 'M', 'ः': 'H', 'ँ': '.N', 'ऽ': '.a',
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    }
    
    def transliterate(self, text: str, source_script: Script, target_script: Script) -> str:
        if source_script == target_script:
            return text
        
        # Devanagari → Latin (ITRANS)
        if source_script == Script.DEVANAGARI and target_script == Script.LATIN:
            return self._devanagari_to_itrans(text)
        
        # Latin (ITRANS) → Devanagari
        if source_script == Script.LATIN and target_script == Script.DEVANAGARI:
            return self._itrans_to_devanagari(text)
        
        # Other scripts: use indic-trans library
        return self._indic_trans(text, source_script, target_script)
    
    def _devanagari_to_itrans(self, text: str) -> str:
        result = []
        i = 0
        while i < len(text):
            char = text[i]
            # Handle conjuncts (virama)
            if i + 1 < len(text) and text[i+1] == '्':
                result.append(self.DEVANAGARI_TO_ITRANS.get(char, char))
                i += 2
            else:
                result.append(self.DEVANAGARI_TO_ITRANS.get(char, char))
                i += 1
        return ''.join(result)
```

---

## 4. Multilingual Retrieval

### 4.1 Dense Retrieval with bge-m3

```python
class MultilingualDenseRetriever:
    """
    Uses bge-m3 for multilingual dense retrieval.
    Single model handles 100+ languages.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model = SentenceTransformer(model_name)
        self.dim = 1024
    
    def encode_query(self, query: str, language: SupportedLanguage) -> np.ndarray:
        """Encode query in its native language."""
        # bge-m3 handles multilingual natively
        # Add language instruction for better performance
        instruction = self._get_instruction(language)
        embedding = self.model.encode(
            [f"{instruction}{query}"],
            normalize_embeddings=True
        )[0]
        return embedding
    
    def encode_chunks(self, chunks: List[EvidenceChunk]) -> np.ndarray:
        """Encode chunks - use original language text."""
        texts = []
        for chunk in chunks:
            # Use original text, not translation
            texts.append(chunk.text)
        
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings
    
    def _get_instruction(self, language: SupportedLanguage) -> str:
        """Language-specific instruction for bge-m3."""
        instructions = {
            SupportedLanguage.ENGLISH: "Represent this legal query for retrieval: ",
            SupportedLanguage.HINDI: "इस कानूनी प्रश्न को पुनर्प्राप्ति के लिए प्रस्तुत करें: ",
            SupportedLanguage.BENGALI: "এই আইনি প্রশ্নটি পুনরুদ্ধারের জন্য উপস্থাপন করুন: ",
            SupportedLanguage.TAMIL: "இந்த சட்ட வினவை மீட்டெடுப்பதற்காக வெளிப்படுத்தவும்: ",
            # ... other languages
        }
        return instructions.get(language, "Represent this query for retrieval: ")
```

### 4.2 Sparse Retrieval with Language-Specific BM25

```python
class MultilingualSparseRetriever:
    """
    BM25 with language-specific tokenization.
    Uses IndicBERT tokenizer for Indian languages.
    """
    
    def __init__(self):
        self.tokenizers = {
            SupportedLanguage.ENGLISH: EnglishLegalTokenizer(),
            SupportedLanguage.HINDI: IndicBERTTokenizer("hi"),
            SupportedLanguage.BENGALI: IndicBERTTokenizer("bn"),
            SupportedLanguage.MARATHI: IndicBERTTokenizer("mr"),
            SupportedLanguage.TAMIL: IndicBERTTokenizer("ta"),
            SupportedLanguage.TELUGU: IndicBERTTokenizer("te"),
            SupportedLanguage.GUJARATI: IndicBERTTokenizer("gu"),
            SupportedLanguage.KANNADA: IndicBERTTokenizer("kn"),
            SupportedLanguage.MALAYALAM: IndicBERTTokenizer("ml"),
            SupportedLanguage.PUNJABI: IndicBERTTokenizer("pa"),
            SupportedLanguage.ODIA: IndicBERTTokenizer("or"),
            SupportedLanguage.ASSAMESE: IndicBERTTokenizer("as"),
            SupportedLanguage.URDU: IndicBERTTokenizer("ur"),
        }
        self.indices = {}  # Per-language BM25 indices
    
    def build_index(self, chunks: List[EvidenceChunk]):
        """Build separate BM25 index per language."""
        chunks_by_lang = defaultdict(list)
        for chunk in chunks:
            lang = SupportedLanguage(chunk.language)
            chunks_by_lang[lang].append(chunk)
        
        for lang, lang_chunks in chunks_by_lang.items():
            tokenizer = self.tokenizers[lang]
            corpus = [tokenizer.tokenize(c.text) for c in lang_chunks]
            self.indices[lang] = BM25Okapi(corpus)
    
    def search(self, query: str, language: SupportedLanguage, top_k: int = 50) -> List[Tuple[str, float]]:
        """Search in query language index."""
        if language not in self.indices:
            # Fallback to English index for cross-lingual
            language = SupportedLanguage.ENGLISH
        
        tokenizer = self.tokenizers[language]
        tokenized_query = tokenizer.tokenize(query)
        scores = self.indices[language].get_scores(tokenized_query)
        
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.chunk_ids[language][i], scores[i]) for i in top_indices]
```

### 4.3 Cross-Lingual Retrieval Strategy

```python
class CrossLingualRetrieval:
    """
    Orchestrates multilingual retrieval combining dense + sparse.
    """
    
    def __init__(self, dense: MultilingualDenseRetriever, sparse: MultilingualSparseRetriever):
        self.dense = dense
        self.sparse = sparse
    
    def retrieve(self, query: str, language: SupportedLanguage, 
                 jurisdiction_filter: MetadataFilter, top_k: int = 100) -> List[RetrievalResult]:
        
        # Strategy 1: Native language retrieval (primary)
        native_results = self._retrieve_native(query, language, jurisdiction_filter, top_k)
        
        # Strategy 2: Cross-lingual (English) retrieval for low-resource languages
        cross_lingual_results = []
        if language != SupportedLanguage.ENGLISH and language in LOW_RESOURCE_LANGUAGES:
            en_query = self._translate_query(query, language, SupportedLanguage.ENGLISH)
            cross_lingual_results = self._retrieve_native(en_query, SupportedLanguage.ENGLISH, 
                                                           jurisdiction_filter, top_k)
        
        # Strategy 3: Transliterated query for script variants
        translit_results = []
        if language in {SupportedLanguage.HINDI, SupportedLanguage.MARATHI}:
            # Try ITRANS transliteration for better sparse matching
            translit_query = self.transliterator.transliterate(query, Script.DEVANAGARI, Script.LATIN)
            translit_results = self._retrieve_sparse(translit_query, SupportedLanguage.ENGLISH, top_k)
        
        # Fuse results with RRF
        fused = self._rrf_fuse([native_results, cross_lingual_results, translit_results])
        
        return fused[:top_k]
    
    def _retrieve_native(self, query: str, language: SupportedLanguage, 
                         jurisdiction_filter: MetadataFilter, top_k: int) -> List[RetrievalResult]:
        # Dense
        query_emb = self.dense.encode_query(query, language)
        dense_results = self.vector_store.search(query_emb, jurisdiction_filter, top_k*2)
        
        # Sparse
        sparse_results = self.sparse.search(query, language, top_k*2)
        
        # Fuse
        return self._rrf_fuse([dense_results, sparse_results])
```

---

## 5. Legal Terminology Preservation

### 5.1 Protected Term Glossary

```python
@dataclass
class LegalTerm:
    term_id: str
    canonical_english: str           # "Section 3(d)"
    canonical_hindi: str             # "धारा 3(घ)"
    translations: Dict[SupportedLanguage, str]  # Per-language translations
    do_not_translate: bool = True    # Keep in original script
    context: List[str] = field(default_factory=list)  # Legal contexts
    authority_source: str = ""       # Source of translation (official gazette)

# Core protected terms (sample)
PROTECTED_TERMS = {
    "section_3d": LegalTerm(
        term_id="section_3d",
        canonical_english="Section 3(d)",
        canonical_hindi="धारा 3(घ)",
        translations={
            SupportedLanguage.BENGALI: "ধারা ৩(ঘ)",
            SupportedLanguage.TAMIL: "பிரிவு 3(घ)",
            SupportedLanguage.TELUGU: "విధി 3(ఘ)",
        },
        do_not_translate=True,
        context=["patent", "patentability", "efficacy"],
        authority_source="Patents Act 1970 (Official Hindi Translation)"
    ),
    "prior_informed_consent": LegalTerm(
        term_id="prior_informed_consent",
        canonical_english="prior informed consent",
        canonical_hindi="पूर्व सूचित सहमति",
        translations={
            SupportedLanguage.BENGALI: "পূর্বে सूচিত সম্মতি",
            SupportedLanguage.TAMIL: "முன்பு தெரிவிக்கப்பட்ட ஒப்புதல்",
        },
        do_not_translate=True,
        context=["abs", "nagoya", "biodiversity"],
        authority_source="Nagoya Protocol (Official Hindi Translation)"
    ),
    "mutually_agreed_terms": LegalTerm(
        term_id="mutually_agreed_terms",
        canonical_english="mutually agreed terms",
        canonical_hindi="पारस्परिक सहमत शर्तें",
        do_not_translate=True,
        context=["abs", "nagoya"],
        authority_source="Nagoya Protocol"
    ),
    "biological_resource": LegalTerm(
        term_id="biological_resource",
        canonical_english="biological resource",
        canonical_hindi="जैविक संसाधन",
        translations={...},
        do_not_translate=True,
        context=["biodiversity", "abs", "bda"],
        authority_source="Biological Diversity Act 2002"
    ),
    "traditional_knowledge": LegalTerm(
        term_id="traditional_knowledge",
        canonical_english="traditional knowledge",
        canonical_hindi="पारंपरिक ज्ञान",
        do_not_translate=True,
        context=["tk", "biodiversity", "abs", "cbd"],
        authority_source="CBD / BDA 2002"
    ),
    "ayurveda_aahar": LegalTerm(
        term_id="ayurveda_aahar",
        canonical_english="Ayurveda Aahar",
        canonical_hindi="आयुर्वेद आहार",
        do_not_translate=True,
        context=["food", "fssai", "ayush"],
        authority_source="FSSAI Ayurveda Aahar Regulations 2022"
    ),
    # ... 200+ terms
}

class TerminologyProtector:
    """
    Protects legal terminology during translation/generation.
    """
    
    def __init__(self):
        self.glossary = PROTECTED_TERMS
        self._build_lookup()
    
    def _build_lookup(self):
        self.term_patterns = {}
        for term_id, term in self.glossary.items():
            # Build regex for each language variant
            for lang, translation in term.translations.items():
                pattern = re.escape(translation)
                self.term_patterns[pattern] = term_id
            # Also add canonical English
            self.term_patterns[re.escape(term.canonical_english)] = term_id
            if term.canonical_hindi:
                self.term_patterns[re.escape(term.canonical_hindi)] = term_id
    
    def protect(self, text: str, target_language: SupportedLanguage) -> ProtectedText:
        """
        Mark protected terms in text before translation.
        Returns text with placeholders + mapping.
        """
        protected_text = text
        placeholders = {}
        
        for pattern, term_id in self.term_patterns.items():
            matches = list(re.finditer(pattern, protected_text, re.IGNORECASE))
            for i, match in enumerate(matches):
                placeholder = f"__TERM_{term_id}_{i}__"
                protected_text = protected_text[:match.start()] + placeholder + protected_text[match.end():]
                placeholders[placeholder] = {
                    "term_id": term_id,
                    "original": match.group(),
                    "target_form": self.glossary[term_id].translations.get(target_language, 
                                                                           self.glossary[term_id].canonical_english)
                }
        
        return ProtectedText(
            original_text=text,
            protected_text=protected_text,
            placeholders=placeholders
        )
    
    def restore(self, protected_text: ProtectedText) -> str:
        """Restore protected terms after translation."""
        result = protected_text.protected_text
        for placeholder, info in protected_text.placeholders.items():
            result = result.replace(placeholder, info["target_form"])
        return result
    
    def verify_preservation(self, source: str, target: str, language: SupportedLanguage) -> VerificationResult:
        """Verify all protected terms preserved in translation."""
        missing = []
        for term_id, term in self.glossary.items():
            target_form = term.translations.get(language, term.canonical_english)
            if target_form in source and target_form not in target:
                missing.append(term_id)
        
        return VerificationResult(
            all_preserved=len(missing) == 0,
            missing_terms=missing
        )
```

---

## 6. Multilingual Generation

### 6.1 Generation Strategies

```python
class MultilingualGenerationStrategy(str, Enum):
    NATIVE_GENERATION = "native_generation"      # Generate directly in target language
    TRANSLATE_AFTER = "translate_after"          # Generate in English, translate
    HYBRID = "hybrid"                            # Native for claims, translate for fluency

class MultilingualGenerator:
    """
    Generates answers in target language with citation preservation.
    """
    
    def __init__(self, llm_client, terminology_protector: TerminologyProtector):
        self.llm = llm_client
        self.terminology = terminology_protector
    
    def generate(self, mapped_claims: List[MappedClaim], query: str,
                 target_language: SupportedLanguage,
                 jurisdiction_ctx: JurisdictionContext,
                 strategy: MultilingualGenerationStrategy = MultilingualGenerationStrategy.HYBRID) -> GeneratedAnswer:
        
        if strategy == MultilingualGenerationStrategy.NATIVE_GENERATION:
            return self._generate_native(mapped_claims, query, target_language, jurisdiction_ctx)
        elif strategy == MultilingualGenerationStrategy.TRANSLATE_AFTER:
            return self._generate_translate_after(mapped_claims, query, target_language, jurisdiction_ctx)
        else:
            return self._generate_hybrid(mapped_claims, query, target_language, jurisdiction_ctx)
    
    def _generate_native(self, mapped_claims: List[MappedClaim], query: str,
                         target_language: SupportedLanguage,
                         jurisdiction_ctx: JurisdictionContext) -> GeneratedAnswer:
        """Generate directly in target language using multilingual LLM."""
        
        # Format claims in target language (translate claim text, keep citations)
        claims_text = self._format_claims_multilingual(mapped_claims, target_language)
        
        prompt = self._get_native_prompt(target_language, query, claims_text, jurisdiction_ctx)
        result = self.llm.extract_structured(prompt, Dict)
        
        # Verify terminology preservation
        protected = self.terminology.protect(result["content"], target_language)
        # ... rest of pipeline
        
        return self._build_answer(result, mapped_claims, target_language)
    
    def _generate_translate_after(self, mapped_claims: List[MappedClaim], query: str,
                                   target_language: SupportedLanguage,
                                   jurisdiction_ctx: JurisdictionContext) -> GeneratedAnswer:
        """Generate in English, then translate with terminology protection."""
        
        # Generate in English (Phase 10 pipeline)
        en_answer = self.english_generator.generate(mapped_claims, query, jurisdiction_ctx)
        
        # Translate each segment with terminology protection
        translated_segments = []
        for segment in en_answer.segments:
            protected = self.terminology.protect(segment.content, target_language)
            translated = self._translate_text(protected.protected_text, SupportedLanguage.ENGLISH, target_language)
            restored = self.terminology.restore(ProtectedText(
                original_text=segment.content,
                protected_text=translated,
                placeholders=protected.placeholders
            ))
            
            # Translate citations
            translated_citations = self._translate_citations(segment.citations, target_language)
            
            translated_segments.append(AnswerSegment(
                jurisdiction_id=segment.jurisdiction_id,
                content=restored,
                claims=segment.claims,
                citations=translated_citations,
                confidence=segment.confidence,
                abstentions=segment.abstentions
            ))
        
        return GeneratedAnswer(
            query=query,
            segments=translated_segments,
            overall_confidence=en_answer.overall_confidence,
            jurisdiction_context=jurisdiction_ctx
        )
    
    def _generate_hybrid(self, mapped_claims: List[MappedClaim], query: str,
                         target_language: SupportedLanguage,
                         jurisdiction_ctx: JurisdictionContext) -> GeneratedAnswer:
        """
        Hybrid: Extract claims in source languages, compose in target language.
        Best of both worlds - citation accuracy + target language fluency.
        """
        # Group claims by source language
        claims_by_lang = defaultdict(list)
        for mc in mapped_claims:
            lang = SupportedLanguage(mc.claim.metadata.get("source_language", "en"))
            claims_by_lang[lang].append(mc)
        
        # Generate segment per source language jurisdiction
        segments = []
        for jur_id, claims in self._group_by_jurisdiction(mapped_claims).items():
            # Determine dominant source language for this jurisdiction
            source_lang = self._dominant_language(claims)
            
            if source_lang == target_language:
                # Native generation
                segment = self._generate_native_segment(claims, query, target_language, jur_id)
            else:
                # Translate after generation in source language
                segment = self._generate_crosslingual_segment(claims, query, source_lang, target_language, jur_id)
            
            segments.append(segment)
        
        return GeneratedAnswer(
            query=query,
            segments=segments,
            overall_confidence=self._compute_confidence(segments),
            jurisdiction_context=jurisdiction_ctx
        )
```

### 6.2 Citation Translation

```python
class CitationTranslator:
    """
    Translates citations while preserving source references.
    """
    
    def translate_citation(self, citation: Citation, target_language: SupportedLanguage) -> Citation:
        """Translate citation text, keep chunk references intact."""
        
        # Translate human-readable citation text
        protected = self.terminology.protect(citation.citation_text, target_language)
        translated_text = self._translate_text(protected.protected_text, SupportedLanguage.ENGLISH, target_language)
        restored_text = self.terminology.restore(ProtectedText(
            original_text=citation.citation_text,
            protected_text=translated_text,
            placeholders=protected.placeholders
        ))
        
        # Full citation: translate descriptive parts, keep identifiers
        full_citation = self._translate_full_citation(citation.full_citation, target_language)
        
        return Citation(
            citation_id=citation.citation_id,
            claim_id=citation.claim_id,
            chunk_ids=citation.chunk_ids,  # UNCHANGED - points to original chunks
            citation_text=restored_text,
            full_citation=full_citation,
            jurisdiction=citation.jurisdiction,
            authority=citation.authority,
            authority_tier=citation.authority_tier,
            source_url=citation.source_url,
            effective_date=citation.effective_date,
            verification_status=citation.verification_status
        )
    
    def _translate_full_citation(self, full_citation: str, target_language: SupportedLanguage) -> str:
        """Translate full citation preserving legal identifiers."""
        # Protect section numbers, act names, dates, URLs
        protected = self.terminology.protect(full_citation, target_language)
        # Also protect: Section numbers, Act names, Years, URLs
        protected = self._protect_legal_identifiers(protected)
        
        translated = self._translate_text(protected.protected_text, SupportedLanguage.ENGLISH, target_language)
        restored = self.terminology.restore(protected)
        return self._restore_legal_identifiers(restored)
```

---

## 7. Multilingual Corpus Preparation

### 7.1 Corpus Language Distribution

```python
CORPUS_LANGUAGE_DISTRIBUTION = {
    # Primary sources (official)
    "en": 15,    # Acts, Rules, Notifications, Judgments (original English)
    "hi": 12,    # Official Hindi translations (gazetted)
    
    # Secondary (limited)
    "bn": 2,     # Some WB state notifications
    "mr": 2,     # Some MH state notifications  
    "ta": 1,     # TN notifications
    "te": 1,     # AP/TS notifications
    "gu": 1,     # GJ notifications
    "kn": 1,     # KA notifications
    "ml": 1,     # KL notifications
    "pa": 1,     # PB notifications
    "or": 1,     # OD notifications
    "as": 1,     # AS notifications
    "ur": 1,     # Limited
}

# Translation pipeline for corpus expansion
class CorpusTranslationPipeline:
    """
    Translates English corpus to Indic languages for retrieval augmentation.
    """
    
    def translate_corpus(self, chunks: List[EvidenceChunk], 
                         target_languages: List[SupportedLanguage]) -> List[EvidenceChunk]:
        """Create translated versions of chunks for cross-lingual retrieval."""
        translated_chunks = []
        
        for chunk in chunks:
            if chunk.language == "en":  # Only translate English originals
                for lang in target_languages:
                    if lang in HIGH_PRIORITY_LANGUAGES:
                        translated = self._translate_chunk(chunk, lang)
                        if translated:
                            translated_chunks.append(translated)
        
        return translated_chunks
    
    def _translate_chunk(self, chunk: EvidenceChunk, target_lang: SupportedLanguage) -> Optional[EvidenceChunk]:
        """Translate chunk with terminology protection."""
        protected = self.terminology.protect(chunk.text, target_lang)
        translated_text = self.translator.translate(protected.protected_text, "en", target_lang.value)
        restored_text = self.terminology.restore(ProtectedText(
            original_text=chunk.text,
            protected_text=translated_text,
            placeholders=protected.placeholders
        ))
        
        # Verify quality
        if not self._verify_translation_quality(chunk.text, restored_text, target_lang):
            return None
        
        return EvidenceChunk(
            chunk_id=f"{chunk.chunk_id}_{target_lang.value}",
            text=restored_text,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            jurisdiction_id=chunk.jurisdiction_id,
            authority_id=chunk.authority_id,
            authority_tier=chunk.authority_tier,
            section_number=chunk.section_number,
            section_title=chunk.section_title,
            act_name=chunk.act_name,
            effective_date=chunk.effective_date,
            source_url=chunk.source_url,
            content_hash=hashlib.sha256(restored_text.encode()).hexdigest()[:16],
            retrieval_score=0.0,
            retrieval_rank=0,
            metadata={
                **chunk.metadata,
                "translated_from": chunk.chunk_id,
                "source_language": "en",
                "target_language": target_lang.value,
                "translation_model": "nllb-200-3.3B",
                "terminology_verified": True
            }
        )
```

---

## 8. Evaluation Framework

### 8.1 Multilingual Test Sets

```python
MULTILINGUAL_TEST_CASES = [
    MultilingualTestCase(
        case_id="ML-001",
        query="धारा 3(घ) के तहत पेटेंटेबिलिटी क्या है?",
        language=SupportedLanguage.HINDI,
        expected_answer_language=SupportedLanguage.HINDI,
        must_cite=["Section 3(d)", "Patents Act 1970"],
        must_preserve_terms=["Section 3(d)", "enhancement of known efficacy"],
        jurisdiction="INDIA_CENTRAL"
    ),
    MultilingualTestCase(
        case_id="ML-002",
        query="নাগোয়া প্রোটোকল অনুযায়ী PIC এবং MAT কি?",
        language=SupportedLanguage.BENGALI,
        expected_answer_language=SupportedLanguage.BENGALI,
        must_cite=["Article 6", "Article 7", "Nagoya Protocol"],
        must_preserve_terms=["prior informed consent", "mutually agreed terms"],
        jurisdiction="NAGOYA"
    ),
    MultilingualTestCase(
        case_id="ML-003",
        query="What are the ABS requirements for exporting neem extract?",
        language=SupportedLanguage.ENGLISH,
        expected_answer_language=SupportedLanguage.ENGLISH,
        # Cross-lingual: answer should cite Hindi/English sources
        must_cite=["Biological Diversity Act 2002", "ABS Rules 2014"],
        jurisdiction="INDIA_CENTRAL"
    ),
    MultilingualTestCase(
        case_id="ML-004",
        query="ஆயுர்வேத ಆஹார் लाइसेंस के लिए क्या आवश्यक है?",
        language=SupportedLanguage.TAMIL,  # Code-switched: Tamil + Hindi + English
        expected_answer_language=SupportedLanguage.TAMIL,
        must_cite=["FSSAI", "Ayurveda Aahar Regulations 2022"],
        must_preserve_terms=["Ayurveda Aahar", "FSSAI", "license"],
        jurisdiction="INDIA_CENTRAL"
    ),
]

MULTILINGUAL_METRICS = {
    "retrieval_recall_crosslingual": {
        "target": 0.85,
        "description": "Recall of relevant chunks when query language ≠ chunk language"
    },
    "translation_bleu": {
        "target": 35,
        "description": "BLEU score for legal translation (EN→HI)"
    },
    "terminology_preservation": {
        "target": 1.0,
        "description": "100% protected terms preserved in translation"
    },
    "citation_integrity": {
        "target": 1.0,
        "description": "Citations point to correct original chunks after translation"
    },
    "generation_quality_native": {
        "target": 0.9,
        "description": "Native generation quality vs translate-after (human eval)"
    },
    "code_switching_handling": {
        "target": 0.95,
        "description": "Accuracy on mixed-language queries"
    }
}
```

---

## 9. Integration Points

| Phase | Integration |
|-------|-------------|
| **Phase 3** | Language detection → query analysis |
| **Phase 4** | Corpus translation pipeline at ingestion |
| **Phase 5** | Chunk metadata includes language, translation links |
| **Phase 6** | Multilingual dense (bge-m3) + sparse (IndicBERT) retrieval |
| **Phase 7** | KG stores multilingual term mappings |
| **Phase 8** | Formulation terms in glossary |
| **Phase 9** | Jurisdiction detection works cross-lingually |
| **Phase 10** | Claims extracted in source lang, answer in target lang |
| **Phase 11** | Authority tier preserved across translation |
| **Phase 13** | Agentic orchestration uses language detection |

---

## 10. Open Research Questions

| ID | Question |
|----|----------|
| **ORQ-66** | Optimal cross-lingual retrieval: translate query vs. multilingual embedding vs. both? |
| **ORQ-67** | How to handle legal terms with no official translation (e.g., "evergreening")? |
| **ORQ-68** | Script mixing in generation (Devanagari + Latin in same answer)? |
| **ORQ-69** | Low-resource languages (Odia, Assamese): translation vs. zero-shot? |
| **ORQ-70** | Legal transliteration standards (ITRANS vs IAST vs ISO 15919)? |
| **ORQ-71** | Evaluating multilingual legal QA without native speaker annotators? |
| **ORQ-72** | Handling Urdu (Nastaliq script) with RTL rendering? |

---

## 11. Implementation Checklist

- [ ] Language detection (fastText + script detection)
- [ ] Script normalization (NFC, Indic normalization)
- [ ] Code-switching detection
- [ ] Transliteration (Devanagari ↔ ITRANS, other scripts)
- [ ] bge-m3 dense retrieval integration
- [ ] Language-specific BM25 (IndicBERT tokenizers)
- [ ] Cross-lingual retrieval fusion
- [ ] Protected terminology glossary (200+ terms)
- [ ] Terminology protector (placeholder-based)
- [ ] Native generation (multilingual LLM)
- [ ] Translate-after generation with protection
- [ ] Hybrid generation strategy
- [ ] Citation translation with reference preservation
- [ ] Corpus translation pipeline (NLLB-200)
- [ ] Multilingual evaluation dataset
- [ ] Terminology preservation verification
- [ ] Integration tests across pipeline

---

## 12. Summary

| Aspect | Decision |
|--------|----------|
| **Languages** | 13 Indian languages + English (prioritized by corpus availability) |
| **Dense Retrieval** | bge-m3 (single model, 100+ langs) |
| **Sparse Retrieval** | Language-specific BM25 with IndicBERT tokenizers |
| **Cross-Lingual** | Query translation + multilingual embedding + transliteration |
| **Terminology** | 200+ protected terms with official translations |
| **Generation** | Hybrid: native where possible, translate-after with protection |
| **Citations** | Translate citation text, preserve chunk references |
| **Scripts** | Unicode NFC + indic-normalize + transliteration utilities |
| **Evaluation** | Cross-lingual recall, BLEU, terminology preservation, citation integrity |

---

## 13. Next Phase: Phase 13 - Agentic Orchestration

Phase 13 will design the **Agentic Orchestration** layer for:
- Multi-step legal research queries
- Tool use: retrieval, KG traversal, calculation, comparison
- Planning and decomposition of complex queries
- Self-correction and verification loops
- Integration with all previous phases