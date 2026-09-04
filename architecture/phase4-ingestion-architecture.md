# Phase 4: Legal Document Ingestion Architecture
## IP-SAKTI Sahayak - Complete Ingestion Pipeline Specification

**Status:** COMPLETE  
**Version:** 1.0  
**Date:** 2026-09-02

---

## 1. Ingestion Architecture Overview

### 1.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Hierarchy Preservation** | Act → Chapter → Part → Section → Subsection → Clause → Subclause |
| **Full Provenance** | Every chunk traceable to: source → document → version → section → authoritative URL |
| **Version Immutability** | Never overwrite; new version = new document with supersession links |
| **Source-Type Awareness** | LEGISLATION, RULE, REGULATION, TREATY, REGISTRY_RECORD, GUIDELINE, CASE_LAW each have distinct parsing |
| **Authority Tier Embedding** | Tier baked into metadata at ingestion time |
| **Change Detection** | Content hashing + structural diffing for amendment detection |
| **Idempotency** | Re-ingestion safe; deduplication by content_hash + source_id + version |

### 1.2 High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LEGAL DOCUMENT INGESTION PIPELINE                             │
│                                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  ACQUISITION │───▶│   PARSING    │───▶│ STRUCTURE    │───▶│  CHUNKING    │      │
│  │              │    │              │    │  EXTRACTION  │    │              │      │
│  │ • HTTP/Play  │    │ • PDF/HTML   │    │ • Hierarchy  │    │ • Legal-     │      │
│  │ • Auth/API   │    │ • OCR        │    │ • Numbering  │    │   aware      │      │
│  │ • Scheduling │    │ • Tables     │    │ • Definitions│    │ • Parent-    │      │
│  └──────────────┘    │ • Footnotes  │    │ • Cross-refs │    │   child      │      │
│                      └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                                       │             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │             │
│  │  VALIDATION  │◀───│  METADATA    │◀───│  DEDUP/      │           │             │
│  │              │    │  GENERATION  │    │  VERSIONING  │           │             │
│  │ • Schema     │    │              │    │              │           │             │
│  │ • Hierarchy  │    │ • Provenance │    │ • Content    │           │             │
│  │ • Citations  │    │ • Authority  │    │   hash       │           │             │
│  │ • Completeness│   │ • Jurisdiction│   │ • Version    │           │             │
│  └──────┬───────┘    │ • Temporal   │    │   links      │           │             │
│         │            │ • Source URL │    │ • Amendment  │           │             │
│         ▼            └──────────────┘    │   detection  │           │             │
│  ┌──────────────┐                         └──────────────┘           │             │
│  │   INDEXING   │                                                  │             │
│  │              │                                                  │             │
│  │ • Vector DB  │                                                  │             │
│  │ • Lexical IDX│                                                  │             │
│  │ • Graph DB   │                                                  │             │
│  │ • Metadata   │                                                  │             │
│  └──────────────┘                                                  │             │
│                                                                    │             │
└────────────────────────────────────────────────────────────────────┼─────────────┘
                                                                     │
                                                         ┌───────────┴───────────┐
                                                         ▼                       ▼
                                                ┌───────────────┐         ┌───────────────┐
                                                │  CHANGE       │         │  NOTIFICATION │
                                                │  DETECTION    │         │  & AUDIT      │
                                                │               │         │               │
                                                │ • Hash compare│         │ • Ingest log  │
                                                │ • Struct diff │         │ • Version     │
                                                │ • Alert       │         │   history     │
                                                └───────────────┘         └───────────────┘
```

---

## 2. Acquisition Layer

### 2.1 Source-Specific Acquisition Strategies

| Source | Method | Frequency | Auth | Challenges |
|--------|--------|-----------|------|------------|
| **India Code** | Official bulk API request + manual PDF fallback | On-demand + quarterly check | Govt credentials | robots.txt blocks crawlers |
| **IP India** | Direct PDF download + Playwright for registry | Monthly + on amendment | None (public) | JS-rendered registry search |
| **NBA** | Direct PDF/HTML + Playwright for forms | Monthly | None (public) | Drupal CMS, JS navigation |
| **CBD/Nagoya** | Direct PDF from cbd.int | Quarterly | None | Treaty COP decisions updates |
| **WIPO** | Direct PDF from wipo.int | Quarterly | None | Signed URLs expire |
| **FSSAI** | Playwright rendering | Monthly | None | Heavy JS, dynamic content |
| **AYUSH** | Direct PDF + Playwright | Quarterly | None | Mixed access |

### 2.2 Acquisition Implementation

```python
class DocumentAcquirer:
    def __init__(self):
        self.sources = {
            "india_code": IndiaCodeAcquirer(),
            "ip_india": IPAcquirer(),
            "nba": NBAAcquirer(),
            "cbd": CBDacquirer(),
            "wipo": WIPOAcquirer(),
            "fssai": FSSAIAcquirer(),
            "ayush": AYUSHAcquirer(),
        }
    
    def acquire_all(self, mode: str = "incremental") -> List[AcquiredDocument]:
        """Mode: 'full' | 'incremental' | 'single_source'"""
        results = []
        for source_id, acquirer in self.sources.items():
            try:
                docs = acquirer.acquire(mode=mode)
                results.extend(docs)
            except Exception as e:
                self.logger.error(f"Acquisition failed for {source_id}: {e}")
                # Continue with other sources
        return results

class BaseAcquirer(ABC):
    @abstractmethod
    def discover_documents(self) -> List[DocumentRef]:
        """Return list of document references (URL, metadata hints)"""
        pass
    
    @abstractmethod
    def download(self, ref: DocumentRef) -> RawDocument:
        """Download raw content (PDF, HTML, etc.)"""
        pass
    
    def acquire(self, mode: str) -> List[AcquiredDocument]:
        refs = self.discover_documents()
        acquired = []
        for ref in refs:
            # Check if already ingested (by content_hash)
            if mode == "incremental" and self._already_ingested(ref):
                continue
            raw = self.download(ref)
            acquired.append(AcquiredDocument(
                source_id=self.source_id,
                raw_content=raw,
                metadata=ref.metadata,
                acquired_at=datetime.utcnow()
            ))
        return acquired
```

### 2.3 Playwright-Based Acquisition (for JS-heavy sources)

```python
class PlaywrightAcquirer(BaseAcquirer):
    async def download(self, ref: DocumentRef) -> RawDocument:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; IP-SAKTI Bot/1.0)",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            # Navigate and wait for content
            await page.goto(ref.url, wait_until="networkidle", timeout=60000)
            
            # Handle dynamic content (click "Download PDF", expand sections, etc.)
            if ref.selectors:
                for selector, action in ref.selectors:
                    await self._perform_action(page, selector, action)
            
            # Get content
            if ref.output_format == "pdf":
                content = await page.pdf(format="A4", print_background=True)
                mime_type = "application/pdf"
            else:
                content = await page.content()
                mime_type = "text/html"
            
            await browser.close()
            return RawDocument(content=content, mime_type=mime_type, url=ref.url)
```

### 2.4 Scheduled Acquisition & Change Detection

```python
class AcquisitionScheduler:
    def __init__(self):
        self.schedule = {
            "india_code": "0 2 1 * *",      # Monthly 1st at 2 AM
            "ip_india": "0 3 * * 0",        # Weekly Sunday 3 AM
            "nba": "0 3 * * 1",             # Weekly Monday 3 AM
            "cbd": "0 4 1 */3 *",           # Quarterly 1st at 4 AM
            "wipo": "0 4 1 */3 *",
            "fssai": "0 5 1 * *",
            "ayush": "0 5 1 */3 *",
        }
    
    async def run_scheduled(self):
        for source_id, cron_expr in self.schedule.items():
            if croniter.match(cron_expr, datetime.utcnow()):
                await self.trigger_acquisition(source_id)
```

---

## 3. Parsing Layer

### 3.1 Parser Selection by MIME Type

```python
class ParserRegistry:
    def __init__(self):
        self.parsers = {
            "application/pdf": PDFParser(),
            "text/html": HTMLParser(),
            "application/msword": DocxParser(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser(),
            "text/plain": PlainTextParser(),
        }
    
    def parse(self, raw: RawDocument) -> ParsedDocument:
        parser = self.parsers.get(raw.mime_type)
        if not parser:
            raise UnsupportedFormatError(raw.mime_type)
        return parser.parse(raw)
```

### 3.2 PDF Parsing (Primary for Indian Legislation)

```python
class PDFParser:
    def __init__(self):
        self.ocr_engine = OCREngine()  # Tesseract + layout analysis
    
    def parse(self, raw: RawDocument) -> ParsedDocument:
        # Try text extraction first
        text_content = self._extract_text(raw.content)
        
        if self._needs_ocr(text_content):
            # Fallback to OCR for scanned PDFs
            text_content = self._ocr_pdf(raw.content)
        
        # Extract structure using layout analysis
        structure = self._extract_structure(raw.content)
        
        # Extract tables
        tables = self._extract_tables(raw.content)
        
        # Extract footnotes/endnotes
        footnotes = self._extract_footnotes(text_content, structure)
        
        return ParsedDocument(
            text=text_content,
            structure=structure,
            tables=tables,
            footnotes=footnotes,
            page_count=self._count_pages(raw.content),
            parser_version="pdfplumber+ocr_v1"
        )
    
    def _extract_structure(self, pdf_bytes: bytes) -> DocumentStructure:
        """Extract hierarchical structure from PDF layout"""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            structure = DocumentStructure()
            current_act = None
            current_chapter = None
            current_part = None
            
            for page_num, page in enumerate(pdf.pages):
                # Extract text with position info
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False
                )
                
                # Detect headings by font size, bold, position
                lines = self._group_words_into_lines(words)
                for line in lines:
                    level, number, title = self._classify_heading(line)
                    if level == "act":
                        current_act = ActNode(number=number, title=title, page=page_num)
                        structure.acts.append(current_act)
                    elif level == "chapter" and current_act:
                        current_chapter = ChapterNode(number=number, title=title, page=page_num)
                        current_act.chapters.append(current_chapter)
                    elif level == "part" and current_chapter:
                        current_part = PartNode(number=number, title=title, page=page_num)
                        current_chapter.parts.append(current_part)
                    elif level == "section" and (current_part or current_chapter or current_act):
                        parent = current_part or current_chapter or current_act
                        section = SectionNode(
                            number=number, title=title, page=page_num,
                            parent_id=parent.id
                        )
                        parent.sections.append(section)
                    # ... subsection, clause, subclause
            
            return structure
```

### 3.3 HTML Parsing (for Web-Based Sources)

```python
class HTMLParser:
    def parse(self, raw: RawDocument) -> ParsedDocument:
        soup = BeautifulSoup(raw.content, 'lxml')
        
        # Remove navigation, headers, footers, scripts
        for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'aside', 'noscript']):
            tag.decompose()
        
        # Extract main content area
        main = soup.find('main') or soup.find('div', id='content') or soup.find('div', class_='document')
        if not main:
            main = soup.body
        
        # Extract structure from HTML headings
        structure = self._extract_html_structure(main)
        
        # Extract tables
        tables = []
        for table in main.find_all('table'):
            tables.append(self._parse_table(table))
        
        # Get clean text
        text = main.get_text(separator='\n', strip=True)
        
        return ParsedDocument(
            text=text,
            structure=structure,
            tables=tables,
            footnotes=[],
            parser_version="bs4_v1"
        )
    
    def _extract_html_structure(self, element) -> DocumentStructure:
        """Extract Act→Chapter→Section from HTML headings h1-h6"""
        structure = DocumentStructure()
        stack = []  # (level, node)
        
        for tag in element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div']):
            if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag.name[1])
                text = tag.get_text(strip=True)
                node_type, number, title = self._classify_legal_heading(text, level)
                
                if node_type:
                    node = self._create_node(node_type, number, title)
                    # Maintain hierarchy
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    if stack:
                        stack[-1][1].children.append(node)
                    else:
                        structure.acts.append(node)  # Top level
                    stack.append((level, node))
        
        return structure
```

### 3.4 OCR Engine (for Scanned PDFs)

```python
class OCREngine:
    def __init__(self):
        self.tesseract_config = '--oem 3 --psm 6 -l eng+hin'  # English + Hindi
    
    def _ocr_pdf(self, pdf_bytes: bytes) -> str:
        """OCR each page of PDF"""
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page to image at 300 DPI
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Run Tesseract
            text = pytesseract.image_to_string(img, config=self.tesseract_config)
            full_text.append(f"--- PAGE {page_num+1} ---\n{text}")
        
        return "\n".join(full_text)
```

---

## 4. Structure Extraction

### 4.1 Legal Hierarchy Model

```python
@dataclass
class DocumentStructure:
    acts: List[ActNode] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

@dataclass
class Node:
    id: str  # UUID
    type: str  # act, chapter, part, section, subsection, clause, subclause
    number: str  # e.g., "3", "3(d)", "13(2)(a)"
    title: str
    page: int
    parent_id: Optional[str] = None
    children: List['Node'] = field(default_factory=list)
    content_start: int = 0  # Character offset in full text
    content_end: int = 0
    metadata: Dict = field(default_factory=dict)

# Specific node types
@dataclass
class ActNode(Node):
    type: str = "act"
    act_year: Optional[int] = None
    act_number: Optional[int] = None
    short_title: Optional[str] = None
    long_title: Optional[str] = None
    commencement_date: Optional[str] = None
    extent: Optional[str] = None  # "Whole of India"

@dataclass
class ChapterNode(Node):
    type: str = "chapter"
    chapter_number: Optional[str] = None  # Roman or Arabic

@dataclass
class SectionNode(Node):
    type: str = "section"
    section_number: str  # e.g., "3", "3(d)", "13(2)"
    marginal_note: Optional[str] = None  # Section heading
    is_amended: bool = False
    amendment_acts: List[str] = field(default_factory=list)
    effective_date: Optional[str] = None
    repealed: bool = False

@dataclass
class ClauseNode(Node):
    type: str = "clause"
    clause_letter: str  # e.g., "a", "b", "(i)", "(ii)"
```

### 4.2 Structure Extraction Rules (Indian Legislation)

```python
class LegalStructureExtractor:
    """
    Extracts hierarchy from Indian legislative texts.
    Pattern based on India Code / Legislative Department formatting.
    """
    
    # Heading patterns for Indian Acts
    PATTERNS = {
        "act": [
            r'^(?:THE\s+)?([A-Z\s]+(?:ACT|ORDINANCE))\s*,?\s*(\d{4})$',
            r'^ACT\s+NO\.?\s*(\d+)\s+OF\s+(\d{4})$',
            r'^An Act\s+(?:further\s+to\s+)?(?:amend\s+)?(.+)$',
        ],
        "chapter": [
            r'^CHAPTER\s+([IVXLC]+|\d+)\s*[:\-]?\s*(.*)$',
            r'^CHAP\.?\s*([IVXLC]+|\d+)\s*[:\-]?\s*(.*)$',
        ],
        "part": [
            r'^PART\s+([IVXLC]+|\d+)\s*[:\-]?\s*(.*)$',
        ],
        "section": [
            r'^(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\)?)*)\.\s*(.+)$',  # "3. Short title" or "3(d). ..."
            r'^Section\s+(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\)?)*)\s*[:\-]\s*(.+)$',
            r'^Sec\.?\s+(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\)?)*)\s*[:\-]\s*(.+)$',
        ],
        "subsection": [
            r'^\((\d+)\)\s*(.+)$',  # "(1) ..."
            r'^Sub[-\s]section\s+\((\d+)\)\s*(.+)$',
        ],
        "clause": [
            r'^\(([a-z])\)\s*(.+)$',  # "(a) ..."
            r'^Clause\s+\(([a-z])\)\s*(.+)$',
            r'^\(([ivx]+)\)\s*(.+)$',  # Roman numerals
        ],
        "subclause": [
            r'^\(([ivx]+)\)\s*(.+)$',
            r'^\(([a-z])\)\s*(.+)$',  # Nested
        ],
    }
    
    def extract(self, text: str, source_metadata: Dict) -> DocumentStructure:
        lines = text.split('\n')
        structure = DocumentStructure()
        structure.metadata = source_metadata
        
        current_path = []  # Stack of (level, node)
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Try each pattern in hierarchy order
            matched = False
            for node_type in ["act", "chapter", "part", "section", "subsection", "clause", "subclause"]:
                for pattern in self.PATTERNS[node_type]:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        node = self._create_node(node_type, match, i, line)
                        self._insert_into_hierarchy(structure, current_path, node, node_type)
                        matched = True
                        break
                if matched:
                    break
            
            # If no heading matched, it's content - associate with current deepest node
            if not matched and current_path:
                current_path[-1][1].content_end = i
        
        # Post-process: set content ranges, handle definitions, schedules
        self._post_process(structure)
        return structure
    
    def _insert_into_hierarchy(self, structure, path, node, node_type):
        # Level order: act=0, chapter=1, part=2, section=3, subsection=4, clause=5, subclause=6
        level_map = {"act": 0, "chapter": 1, "part": 2, "section": 3, "subsection": 4, "clause": 5, "subclause": 6}
        level = level_map[node_type]
        
        # Pop to correct parent level
        while path and path[-1][0] >= level:
            path.pop()
        
        if path:
            path[-1][1].children.append(node)
            node.parent_id = path[-1][1].id
        else:
            structure.acts.append(node)
        
        path.append((level, node))
```

### 4.3 Special Elements Extraction

```python
class SpecialElementsExtractor:
    def extract_definitions(self, text: str, structure: DocumentStructure) -> List[Definition]:
        """Extract definition clauses (typically in Section 2)"""
        definitions = []
        # Find "Definitions" section
        def_section = self._find_section(structure, "definitions")
        if def_section:
            for clause in def_section.children:
                if clause.type == "clause":
                    term, meaning = self._parse_definition_clause(clause.text)
                    if term:
                        definitions.append(Definition(
                            term=term,
                            meaning=meaning,
                            source_section=def_section.number,
                            source_clause=clause.number
                        ))
        return definitions
    
    def extract_schedules(self, text: str, structure: DocumentStructure) -> List[Schedule]:
        """Extract Schedules (typically at end of Act)"""
        schedules = []
        schedule_pattern = r'^SCHEDULE\s+([IVXLC]+|\d+)\s*[:\-]?\s*(.*)$'
        # ... extract schedule content
        return schedules
    
    def extract_cross_references(self, text: str) -> List[CrossReference]:
        """Extract internal and external cross-references"""
        refs = []
        # Patterns: "Section 3(d)", "Rule 13(2)", "Article 21 of the Constitution"
        patterns = [
            r'Section\s+(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\)?)*)',
            r'Rule\s+(\d+(?:\(\d+\))?(?:\([a-z]\)?)*)',
            r'Article\s+(\d+[A-Z]?)',
            r'Clause\s+\(([a-z])\)',
            r'Sub[-\s]section\s+\((\d+)\)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                refs.append(CrossReference(
                    raw_text=match.group(0),
                    reference_type=self._classify_ref(match.group(0)),
                    target=match.group(1),
                    position=match.start()
                ))
        return refs
    
    def extract_footnotes(self, text: str) -> List[Footnote]:
        """Extract footnotes from text"""
        # Pattern: superscript numbers or [1], †, ‡
        footnotes = []
        # ... implementation
        return footnotes
```

---

## 5. Chunking Strategy

### 5.1 Legal-Hierarchy-Aware Chunking (CORE)

**Design Principle:** Chunks align with legal hierarchy boundaries, not fixed tokens.

```python
class LegalChunker:
    """
    Chunks at section/clause level with parent context.
    Each chunk = one semantic legal unit (section, subsection, or clause group).
    """
    
    def __init__(self, max_chunk_tokens: int = 512, overlap_tokens: int = 50):
        self.max_tokens = max_chunk_tokens
        self.overlap = overlap_tokens
        self.tokenizer = LegalTokenizer()  # Preserves legal citations
    
    def chunk(self, structure: DocumentStructure, full_text: str) -> List[LegalChunk]:
        chunks = []
        
        for act in structure.acts:
            act_chunks = self._chunk_act(act, full_text)
            chunks.extend(act_chunks)
        
        return chunks
    
    def _chunk_act(self, act: ActNode, full_text: str) -> List[LegalChunk]:
        chunks = []
        
        # Act-level chunk (title, preamble, extent, commencement)
        act_text = self._extract_node_text(act, full_text)
        if self._token_count(act_text) > 0:
            chunks.append(LegalChunk(
                content=act_text,
                hierarchy_path=[act],
                chunk_type="act_metadata",
                metadata=self._build_chunk_metadata(act, "act_metadata")
            ))
        
        for chapter in act.chapters:
            chapter_chunks = self._chunk_chapter(chapter, full_text)
            chunks.extend(chapter_chunks)
        
        return chunks
    
    def _chunk_chapter(self, chapter: ChapterNode, full_text: str) -> List[LegalChunk]:
        chunks = []
        
        for section in chapter.sections:
            section_chunks = self._chunk_section(section, full_text)
            chunks.extend(section_chunks)
        
        return chunks
    
    def _chunk_section(self, section: SectionNode, full_text: str) -> List[LegalChunk]:
        """Chunk a section - may split into multiple chunks if large"""
        section_text = self._extract_node_text(section, full_text)
        tokens = self._token_count(section_text)
        
        if tokens <= self.max_tokens:
            # Single chunk for entire section
            return [LegalChunk(
                content=section_text,
                hierarchy_path=self._get_path(section),
                chunk_type="section",
                metadata=self._build_chunk_metadata(section, "section")
            )]
        
        # Large section: chunk at subsection level
        chunks = []
        if section.children:  # Has subsections
            for subsection in section.children:
                sub_chunks = self._chunk_subsection(subsection, full_text)
                chunks.extend(sub_chunks)
        else:
            # No subsections - split by clauses with overlap
            chunks = self._split_by_clauses_with_overlap(section, full_text)
        
        return chunks
    
    def _chunk_subsection(self, subsection: Node, full_text: str) -> List[LegalChunk]:
        """Chunk subsection - split by clauses if needed"""
        sub_text = self._extract_node_text(subsection, full_text)
        tokens = self._token_count(sub_text)
        
        if tokens <= self.max_tokens:
            return [LegalChunk(
                content=sub_text,
                hierarchy_path=self._get_path(subsection),
                chunk_type="subsection",
                metadata=self._build_chunk_metadata(subsection, "subsection")
            )]
        
        # Split by clauses
        return self._split_by_clauses_with_overlap(subsection, full_text)
    
    def _split_by_clauses_with_overlap(self, node: Node, full_text: str) -> List[LegalChunk]:
        """Group clauses into chunks respecting token limit with overlap"""
        clause_texts = []
        for clause in node.children:
            if clause.type in ["clause", "subclause"]:
                clause_texts.append((clause, self._extract_node_text(clause, full_text)))
        
        chunks = []
        current_chunk_clauses = []
        current_tokens = 0
        
        for clause, text in clause_texts:
            clause_tokens = self._token_count(text)
            
            if current_tokens + clause_tokens > self.max_tokens and current_chunk_clauses:
                # Emit current chunk
                chunks.append(self._create_chunk_from_clauses(
                    node, current_chunk_clauses, full_text
                ))
                # Start new chunk with overlap (last clause from previous)
                overlap_clauses = current_chunk_clauses[-1:] if self.overlap > 0 else []
                current_chunk_clauses = overlap_clauses + [clause]
                current_tokens = sum(self._token_count(c[1]) for c in current_chunk_clauses)
            else:
                current_chunk_clauses.append((clause, text))
                current_tokens += clause_tokens
        
        if current_chunk_clauses:
            chunks.append(self._create_chunk_from_clauses(node, current_chunk_clauses, full_text))
        
        return chunks
```

### 5.2 Chunk Metadata (Full Provenance)

```python
@dataclass
class LegalChunk:
    chunk_id: str  # UUID
    content: str
    hierarchy_path: List[Node]  # [Act, Chapter, Section, ...]
    chunk_type: str  # act_metadata, section, subsection, clause_group
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None
    content_hash: str = ""  # SHA256 of content
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ChunkMetadata:
    # Source provenance
    source_id: str  # e.g., "india_code", "ip_india", "nba"
    source_name: str  # e.g., "India Code", "IP India", "National Biodiversity Authority"
    source_type: SourceType  # LEGISLATION, RULE, TREATY, etc.
    authority_tier: int  # 1-5
    jurisdiction: str  # INDIA, INTERNATIONAL, etc.
    
    # Document identification
    document_id: str  # e.g., "PATENTS_ACT_1970"
    document_title: str  # Full title
    version: str  # e.g., "2024-03-15" (amendment date)
    effective_date: str
    superseded_date: Optional[str] = None
    is_superseded: bool = False
    supersedes_document_id: Optional[str] = None
    superseded_by_document_id: Optional[str] = None
    
    # Hierarchy
    act_title: str
    act_year: Optional[int] = None
    act_number: Optional[int] = None
    chapter: Optional[str] = None
    chapter_number: Optional[str] = None
    part: Optional[str] = None
    section: Optional[str] = None  # e.g., "3(d)"
    subsection: Optional[str] = None
    clause: Optional[str] = None
    hierarchy_level: int = 0  # 0=act, 1=chapter, 2=part, 3=section, 4=subsection, 5=clause
    
    # Citations
    canonical_citation: str  # e.g., "Section 3(d), The Patents Act, 1970"
    canonical_url: str  # Official source URL
    marginal_note: Optional[str] = None  # Section heading
    
    # Quality
    parser_version: str
    extraction_confidence: float  # 0-1
    has_tables: bool = False
    has_footnotes: bool = False
    
    # For chunking
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    token_count: int = 0
```

### 5.3 Citation Mapping: Embedding → Chunk → Section → Document → Source

```
Answer Claim
    │
    ▼
Citation ID "[1]"
    │
    ▼
ChunkMetadata (chunk_id: "chunk_abc123")
    │
    ├── section: "3(d)"
    ├── act_title: "The Patents Act, 1970"
    ├── document_id: "PATENTS_ACT_1970"
    ├── version: "2024-03-15"
    ├── source_id: "india_code"
    ├── authority_tier: 1
    ├── jurisdiction: "INDIA"
    ├── canonical_url: "https://indiacode.nic.in/.../A1970-39.pdf"
    │
    ▼
Authoritative Source Document
```

---

## 6. Metadata Generation

### 6.1 Complete Metadata Pipeline

```python
class MetadataGenerator:
    def __init__(self):
        self.authority_map = self._load_authority_map()
        self.jurisdiction_map = self._load_jurisdiction_map()
        self.source_type_map = self._load_source_type_map()
    
    def generate(self, acquired: AcquiredDocument, parsed: ParsedDocument, 
                 structure: DocumentStructure, chunks: List[LegalChunk]) -> IngestionMetadata:
        
        # Determine source type from acquisition metadata + content
        source_type = self._determine_source_type(acquired, parsed, structure)
        
        # Determine authority tier
        authority_tier = self._determine_authority_tier(acquired.source_id, source_type)
        
        # Determine jurisdiction
        jurisdiction = self._determine_jurisdiction(acquired, parsed, structure)
        
        # Extract document-level metadata
        doc_metadata = self._extract_document_metadata(parsed, structure)
        
        # Build version info
        version_info = self._build_version_info(acquired, doc_metadata)
        
        # Generate metadata for each chunk
        for chunk in chunks:
            chunk.metadata = ChunkMetadata(
                source_id=acquired.source_id,
                source_name=self._get_source_name(acquired.source_id),
                source_type=source_type,
                authority_tier=authority_tier,
                jurisdiction=jurisdiction,
                document_id=doc_metadata.document_id,
                document_title=doc_metadata.title,
                version=version_info.version,
                effective_date=version_info.effective_date,
                superseded_date=version_info.superseded_date,
                is_superseded=version_info.is_superseded,
                supersedes_document_id=version_info.supersedes_id,
                superseded_by_document_id=version_info.superseded_by_id,
                act_title=doc_metadata.act_title,
                act_year=doc_metadata.act_year,
                act_number=doc_metadata.act_number,
                chapter=chunk.hierarchy_path[1].title if len(chunk.hierarchy_path) > 1 else None,
                chapter_number=chunk.hierarchy_path[1].number if len(chunk.hierarchy_path) > 1 else None,
                part=chunk.hierarchy_path[2].title if len(chunk.hierarchy_path) > 2 and chunk.hierarchy_path[2].type == "part" else None,
                section=self._get_section_number(chunk.hierarchy_path),
                subsection=self._get_subsection_number(chunk.hierarchy_path),
                clause=self._get_clause_number(chunk.hierarchy_path),
                hierarchy_level=self._get_hierarchy_level(chunk.hierarchy_path),
                canonical_citation=self._build_canonical_citation(chunk),
                canonical_url=acquired.metadata.canonical_url,
                marginal_note=self._get_marginal_note(chunk.hierarchy_path),
                parser_version=parsed.parser_version,
                extraction_confidence=self._compute_extraction_confidence(chunk, parsed),
                has_tables=any(t for t in parsed.tables if t.overlaps_chunk(chunk)),
                has_footnotes=any(f for f in parsed.footnotes if f.overlaps_chunk(chunk)),
                parent_chunk_id=chunk.metadata.parent_chunk_id,
                child_chunk_ids=chunk.metadata.child_chunk_ids,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
            )
        
        return IngestionMetadata(
            document_id=doc_metadata.document_id,
            source_id=acquired.source_id,
            source_type=source_type,
            authority_tier=authority_tier,
            jurisdiction=jurisdiction,
            version=version_info.version,
            effective_date=version_info.effective_date,
            chunks=chunks,
            definitions=self._extract_all_definitions(structure),
            schedules=self._extract_all_schedules(structure),
            cross_references=self._extract_all_cross_refs(parsed.text),
        )
```

### 6.2 Authority Tier Assignment

```python
AUTHORITY_TIER_RULES = {
    # Tier 1: Official primary law
    ("india_code", "LEGISLATION"): 1,
    ("india_code", "RULE"): 1,
    ("ip_india", "LEGISLATION"): 1,
    ("ip_india", "RULE"): 1,
    ("nba", "LEGISLATION"): 1,
    ("nba", "RULE"): 1,
    ("cbd", "TREATY"): 1,
    ("wipo", "TREATY"): 1,
    ("fssai", "LEGISLATION"): 1,
    ("ayush", "LEGISLATION"): 1,
    
    # Tier 2: Official secondary
    ("ip_india", "GUIDELINE"): 2,
    ("ip_india", "MANUAL"): 2,
    ("nba", "GUIDELINE"): 2,
    ("nba", "NOTIFICATION"): 2,
    ("fssai", "REGULATION"): 2,
    ("fssai", "NOTIFICATION"): 2,
    ("ayush", "GUIDELINE"): 2,
    
    # Tier 3: Registry records (factual, high authority)
    ("ip_india", "REGISTRY_RECORD"): 3,
    ("ip_india", "PATENT_RECORD"): 3,
    ("ip_india", "TRADEMARK_RECORD"): 3,
    ("ip_india", "DESIGN_RECORD"): 3,
    ("ip_india", "GI_RECORD"): 3,
    ("nba", "REGISTRY_RECORD"): 3,
    
    # Tier 4: Traditional Knowledge (limited access)
    ("tkdl", "TK_RESOURCE"): 4,
    
    # Tier 5: Academic/Secondary
    ("academic", "ACADEMIC"): 5,
    ("secondary", "SECONDARY"): 5,
}
```

---

## 7. Deduplication & Versioning

### 7.1 Content-Based Deduplication

```python
class Deduplicator:
    def __init__(self, vector_db, metadata_db):
        self.vector_db = vector_db
        self.metadata_db = metadata_db
    
    def deduplicate(self, chunks: List[LegalChunk]) -> DeduplicationResult:
        """Remove duplicate chunks across versions and sources"""
        unique_chunks = []
        duplicates = []
        
        # Group by content_hash
        hash_groups = defaultdict(list)
        for chunk in chunks:
            hash_groups[chunk.content_hash].append(chunk)
        
        for hash_val, chunk_group in hash_groups.items():
            if len(chunk_group) == 1:
                unique_chunks.append(chunk_group[0])
            else:
                # Multiple chunks with same content - keep highest authority
                chunk_group.sort(key=lambda c: c.metadata.authority_tier)
                primary = chunk_group[0]
                unique_chunks.append(primary)
                
                # Record duplicates with link to primary
                for dup in chunk_group[1:]:
                    duplicates.append(DuplicateRecord(
                        primary_chunk_id=primary.chunk_id,
                        duplicate_chunk_id=dup.chunk_id,
                        duplicate_source=dup.metadata.source_id,
                        duplicate_version=dup.metadata.version,
                        reason="identical_content"
                    ))
        
        # Also check near-duplicates (cosine > 0.98)
        near_dupes = self._find_near_duplicates(unique_chunks)
        for primary_id, dupe_id, similarity in near_dupes:
            duplicates.append(DuplicateRecord(
                primary_chunk_id=primary_id,
                duplicate_chunk_id=dupe_id,
                reason=f"near_duplicate_similarity_{similarity:.3f}"
            ))
        
        return DeduplicationResult(
            unique_chunks=unique_chunks,
            duplicates=duplicates,
            stats=DeduplicationStats(
                input_count=len(chunks),
                unique_count=len(unique_chunks),
                exact_duplicates=len([d for d in duplicates if d.reason == "identical_content"]),
                near_duplicates=len([d for d in duplicates if d.reason.startswith("near_duplicate")])
            )
        )
```

### 7.2 Versioning & Amendment Handling

```python
class VersionManager:
    """
    Handles legislative versioning:
    - Each amendment creates NEW document version
    - Old versions preserved with supersession links
    - Section-level versioning for granular tracking
    """
    
    def process_new_version(self, new_doc: IngestionMetadata) -> VersionResult:
        """Process a newly ingested document version"""
        
        # 1. Check if this document_id exists
        existing = self.metadata_db.get_document(new_doc.document_id)
        
        if not existing:
            # First version
            return self._create_initial_version(new_doc)
        
        # 2. Compare with latest version
        latest_version = existing.latest_version
        changes = self._compare_versions(latest_version, new_doc)
        
        if not changes.has_changes:
            return VersionResult(
                action="no_change",
                document_id=new_doc.document_id,
                version=latest_version.version
            )
        
        # 3. Create new version
        new_version = self._create_new_version(existing, new_doc, changes)
        
        # 4. Update supersession links
        self._update_supersession_links(existing.document_id, new_version)
        
        # 5. Detect affected citations (for audit)
        affected_citations = self._find_affected_citations(changes)
        
        return VersionResult(
            action="new_version",
            document_id=new_doc.document_id,
            version=new_version.version,
            changes=changes,
            affected_citations=affected_citations
        )
    
    def _compare_versions(self, old: DocumentVersion, new: IngestionMetadata) -> VersionChanges:
        """Structural diff between versions"""
        changes = VersionChanges()
        
        # Compare at section level
        old_sections = {s.section: s for s in old.sections}
        new_sections = {s.section: s for s in new.sections}
        
        # Added sections
        for section_num in set(new_sections) - set(old_sections):
            changes.added_sections.append(new_sections[section_num])
        
        # Removed sections
        for section_num in set(old_sections) - set(new_sections):
            changes.removed_sections.append(old_sections[section_num])
        
        # Modified sections (content hash changed)
        for section_num in set(old_sections) & set(new_sections):
            if old_sections[section_num].content_hash != new_sections[section_num].content_hash:
                changes.modified_sections.append(SectionChange(
                    section=section_num,
                    old_hash=old_sections[section_num].content_hash,
                    new_hash=new_sections[section_num].content_hash,
                    old_text=old_sections[section_num].text,
                    new_text=new_sections[section_num].text
                ))
        
        changes.has_changes = bool(changes.added_sections or changes.removed_sections or changes.modified_sections)
        return changes
    
    def _find_affected_citations(self, changes: VersionChanges) -> List[AffectedCitation]:
        """Find which citations in the system reference changed sections"""
        affected = []
        for change in changes.modified_sections:
            # Query vector DB for chunks citing this section
            citing_chunks = self.vector_db.find_citing_chunks(
                section=change.section,
                document_id=changes.document_id
            )
            for chunk in citing_chunks:
                affected.append(AffectedCitation(
                    chunk_id=chunk.chunk_id,
                    section=change.section,
                    change_type="modified",
                    old_text_preview=change.old_text[:200],
                    new_text_preview=change.new_text[:200]
                ))
        return affected
```

---

## 8. Change Detection & Monitoring

### 8.1 Source Monitoring

```python
class SourceMonitor:
    def __init__(self):
        self.checkers = {
            "india_code": IndiaCodeChecker(),
            "ip_india": IPIndiaChecker(),
            "nba": NBAChecker(),
            "cbd": CBDChecker(),
            "wipo": WIPOChecker(),
            "fssai": FSSAIChecker(),
            "ayush": AYUSHChecker(),
        }
    
    async def check_all(self) -> List[ChangeEvent]:
        events = []
        for source_id, checker in self.checkers.items():
            try:
                source_events = await checker.check()
                events.extend(source_events)
            except Exception as e:
                self.logger.error(f"Monitor failed for {source_id}: {e}")
        return events

class BaseSourceChecker(ABC):
    @abstractmethod
    async def check(self) -> List[ChangeEvent]:
        pass

class IPIndiaChecker(BaseSourceChecker):
    async def check(self) -> List[ChangeEvent]:
        events = []
        # Check "What's New" / "Notifications" page
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://ipindia.gov.in/notifications.htm", wait_until="networkidle")
            
            # Extract notification links
            notifications = await page.query_selector_all('.notification-item a')
            for notif in notifications:
                url = await notif.get_attribute('href')
                title = await notif.inner_text()
                if self._is_new_notification(url):
                    events.append(ChangeEvent(
                        source_id="ip_india",
                        change_type="new_notification",
                        url=url,
                        title=title,
                        detected_at=datetime.utcnow()
                    ))
            await browser.close()
        return events
```

### 8.2 Change Event Processing

```python
class ChangeProcessor:
    def process(self, event: ChangeEvent) -> ProcessingResult:
        if event.change_type == "new_notification":
            # Download and ingest notification
            return self._ingest_notification(event)
        elif event.change_type == "amendment_published":
            # Trigger full act re-ingestion
            return self._trigger_reingest(event)
        elif event.change_type == "new_judgment":
            # Ingest case law
            return self._ingest_case_law(event)
        elif event.change_type == "registry_update":
            # Incremental registry update
            return self._update_registry(event)
```

---

## 9. Validation & Quality Assurance

### 9.1 Validation Rules

```python
class IngestionValidator:
    def validate(self, ingestion: IngestionMetadata) -> ValidationResult:
        errors = []
        warnings = []
        
        # Schema validation
        for chunk in ingestion.chunks:
            errors.extend(self._validate_chunk_schema(chunk))
            warnings.extend(self._validate_chunk_quality(chunk))
        
        # Hierarchy validation
        errors.extend(self._validate_hierarchy(ingestion.chunks))
        
        # Citation validation
        errors.extend(self._validate_citations(ingestion.chunks))
        
        # Completeness checks
        warnings.extend(self._check_completeness(ingestion))
        
        # Cross-reference validation
        warnings.extend(self._validate_cross_references(ingestion))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=ValidationStats(
                total_chunks=len(ingestion.chunks),
                chunks_with_errors=len([c for c in ingestion.chunks if c.validation_errors]),
                avg_extraction_confidence=np.mean([c.metadata.extraction_confidence for c in ingestion.chunks])
            )
        )
    
    def _validate_chunk_schema(self, chunk: LegalChunk) -> List[ValidationError]:
        errors = []
        required = [
            "source_id", "document_id", "version", "section",
            "authority_tier", "jurisdiction", "canonical_url", "content_hash"
        ]
        for field in required:
            if not getattr(chunk.metadata, field, None):
                errors.append(ValidationError(
                    chunk_id=chunk.chunk_id,
                    field=field,
                    message=f"Required field {field} is missing"
                ))
        return errors
    
    def _validate_hierarchy(self, chunks: List[LegalChunk]) -> List[ValidationError]:
        errors = []
        # Every section chunk must have act_title
        for chunk in chunks:
            if chunk.metadata.hierarchy_level >= 3 and not chunk.metadata.act_title:
                errors.append(ValidationError(
                    chunk_id=chunk.chunk_id,
                    field="act_title",
                    message="Section-level chunk missing act_title"
                ))
        return errors
```

---

## 10. Indexing

### 10.1 Multi-Index Strategy

```python
class MultiIndexer:
    def __init__(self):
        self.vector_index = VectorIndex()      # Dense embeddings
        self.lexical_index = LexicalIndex()    # BM25
        self.metadata_index = MetadataIndex()  # Filterable metadata
        self.graph_index = GraphIndex()        # Knowledge graph (optional)
    
    def index(self, chunks: List[LegalChunk], metadata: IngestionMetadata):
        # 1. Vector index (with metadata for pre-filtering)
        vectors = [(c.chunk_id, c.embedding, c.metadata.to_filter_dict()) for c in chunks if c.embedding]
        self.vector_index.upsert(vectors)
        
        # 2. Lexical index (BM25)
        docs = [(c.chunk_id, c.content, c.metadata.to_filter_dict()) for c in chunks]
        self.lexical_index.upsert(docs)
        
        # 3. Metadata index (for filtering)
        meta_docs = [c.metadata.to_filter_dict() for c in chunks]
        self.metadata_index.upsert(meta_docs)
        
        # 4. Graph index (entities + relationships)
        if self.graph_index:
            entities, relationships = self._extract_graph_elements(chunks, metadata)
            self.graph_index.upsert_entities(entities)
            self.graph_index.upsert_relationships(relationships)
        
        # 5. Update document registry
        self.metadata_index.upsert_document(metadata.to_document_record())
```

### 10.2 Index Update on Amendment

```python
class IndexUpdater:
    def handle_version_change(self, version_result: VersionResult):
        if version_result.action == "new_version":
            # 1. Mark old chunks as superseded (don't delete - for audit)
            self._mark_chunks_superseded(version_result.document_id, version_result.old_version)
            
            # 2. Index new chunks
            self.multi_indexer.index(version_result.new_chunks, version_result.new_metadata)
            
            # 3. Update document registry
            self.metadata_index.update_document_version(
                version_result.document_id,
                version_result.new_version
            )
            
            # 4. Log for audit
            self.audit_log.log(IndexUpdateEvent(
                document_id=version_result.document_id,
                old_version=version_result.old_version,
                new_version=version_result.new_version,
                affected_citations=version_result.affected_citations,
                timestamp=datetime.utcnow()
            ))
```

---

## 11. Source-Specific Ingestion Configurations

### 11.1 India Code Configuration

```python
INDIA_CODE_CONFIG = {
    "source_id": "india_code",
    "base_url": "https://www.indiacode.nic.in",
    "access_method": "official_api_request",  # Not scraping
    "document_types": ["LEGISLATION", "RULE"],
    "hierarchy_patterns": INDIAN_LEGISLATION_PATTERNS,
    "authority_tier": 1,
    "jurisdiction": "INDIA",
    "language": ["en", "hi"],
    "version_tracking": "amendment_date",
    "special_handling": {
        "definitions_section": "Section 2",
        "schedules_at_end": True,
        "footnote_style": "bottom_of_page",
    }
}
```

### 11.2 IP India Configuration

```python
IP_INDIA_CONFIG = {
    "source_id": "ip_india",
    "base_url": "https://ipindia.gov.in",
    "acts": {
        "patents": {"act_url": ".../patents-act-1970.pdf", "rules_url": ".../patents-rules-2003.pdf"},
        "trademarks": {"act_url": ".../trade-marks-act-1999.pdf", "rules_url": ".../trade-marks-rules-2017.pdf"},
        "designs": {"act_url": ".../designs-act-2000.pdf", "rules_url": ".../designs-rules-2001.pdf"},
        "gi": {"act_url": ".../geographical-indications-act-1999.pdf", "rules_url": ".../gi-rules-2002.pdf"},
        "copyright": {"act_url": ".../copyright-act-1957.pdf", "rules_url": ".../copyright-rules-2013.pdf"},
        "ppvfr": {"act_url": ".../ppvfr-act-2001.pdf", "rules_url": ".../ppvfr-rules-2003.pdf"},
        "sicldr": {"act_url": ".../sicldr-act-2000.pdf", "rules_url": ".../sicldr-rules-2002.pdf"},
    },
    "registry": {
        "patents": "InPASS (needs Playwright)",
        "trademarks": "TMR (needs Playwright)",
        "designs": "Design Registry (needs Playwright)",
        "gi": "GI Registry (needs Playwright)",
        "copyright": "Copyright Registry (needs Playwright)",
    },
    "guidelines": ["examination_guidelines", "practice_notices", "manuals"],
    "journals": ["patent_journal", "tm_journal", "design_journal", "gi_journal"],
    "authority_tier": {"act": 1, "rule": 1, "guideline": 2, "manual": 2, "registry": 3, "journal": 2},
    "jurisdiction": "INDIA",
}
```

### 11.3 NBA Configuration

```python
NBA_CONFIG = {
    "source_id": "nba",
    "base_url": "http://nbaindia.org",
    "documents": {
        "bd_act_2002": {"type": "LEGISLATION", "tier": 1},
        "bd_rules_2004": {"type": "RULE", "tier": 1},
        "abs_rules_2014": {"type": "RULE", "tier": 1},
        "abs_guidelines": {"type": "GUIDELINE", "tier": 2},
        "notifications": {"type": "NOTIFICATION", "tier": 2},
        "forms": {"type": "REGISTRY_RECORD", "tier": 3},  # Form I, II, III
        "vaps_classification": {"type": "GUIDELINE", "tier": 1, "critical": True},  # For formulation classification
        "state_rules": {"type": "RULE", "tier": 1},  # Federal jurisdiction
    },
    "critical_for_formulation": ["vaps_classification", "abs_rules_2014", "forms"],
    "jurisdiction": "INDIA",
}
```

---

## 12. Data Models for Ingestion

```protobuf
// Core ingestion models
message RawDocument {
  bytes content = 1;
  string mime_type = 2;
  string url = 3;
  map<string, string> headers = 4;
}

message ParsedDocument {
  string text = 1;
  DocumentStructure structure = 2;
  repeated Table tables = 3;
  repeated Footnote footnotes = 4;
  int32 page_count = 5;
  string parser_version = 6;
}

message DocumentStructure {
  repeated ActNode acts = 1;
  map<string, string> metadata = 2;
}

message ActNode {
  string id = 1;
  string number = 2;
  string title = 3;
  int32 page = 4;
  string parent_id = 5;
  repeated ChapterNode chapters = 6;
  int32 content_start = 7;
  int32 content_end = 8;
  map<string, string> metadata = 9;
}

message LegalChunk {
  string chunk_id = 1;
  string content = 2;
  repeated NodeRef hierarchy_path = 3;
  string chunk_type = 4;
  ChunkMetadata metadata = 5;
  repeated float embedding = 6;
  string content_hash = 7;
  int64 created_at = 8;
}

message ChunkMetadata {
  // Source
  string source_id = 1;
  string source_name = 2;
  SourceType source_type = 3;
  int32 authority_tier = 4;
  string jurisdiction = 5;
  
  // Document
  string document_id = 6;
  string document_title = 7;
  string version = 8;
  string effective_date = 9;
  string superseded_date = 10;
  bool is_superseded = 11;
  string supersedes_document_id = 12;
  string superseded_by_document_id = 13;
  
  // Hierarchy
  string act_title = 14;
  int32 act_year = 15;
  int32 act_number = 16;
  string chapter = 17;
  string chapter_number = 18;
  string part = 19;
  string section = 20;
  string subsection = 21;
  string clause = 22;
  int32 hierarchy_level = 23;
  
  // Citations
  string canonical_citation = 24;
  string canonical_url = 25;
  string marginal_note = 26;
  
  // Quality
  string parser_version = 27;
  float extraction_confidence = 28;
  bool has_tables = 29;
  bool has_footnotes = 30;
  
  // Chunking
  string parent_chunk_id = 31;
  repeated string child_chunk_ids = 32;
  int32 token_count = 33;
  string content_hash = 34;
}

enum SourceType {
  LEGISLATION = 0;
  RULE = 1;
  REGULATION = 2;
  NOTIFICATION = 3;
  GUIDELINE = 4;
  TREATY = 5;
  REGISTRY_RECORD = 6;
  PATENT_RECORD = 7;
  TRADEMARK_RECORD = 8;
  GI_RECORD = 9;
  DESIGN_RECORD = 10;
  TK_RESOURCE = 11;
  CASE_LAW = 12;
  ACADEMIC = 13;
  SECONDARY = 14;
}

message IngestionMetadata {
  string document_id = 1;
  string source_id = 2;
  SourceType source_type = 3;
  int32 authority_tier = 4;
  string jurisdiction = 5;
  string version = 6;
  string effective_date = 7;
  repeated LegalChunk chunks = 8;
  repeated Definition definitions = 9;
  repeated Schedule schedules = 10;
  repeated CrossReference cross_references = 11;
  DocumentQualityMetrics quality = 12;
}

message VersionChanges {
  bool has_changes = 1;
  repeated SectionInfo added_sections = 2;
  repeated SectionInfo removed_sections = 3;
  repeated SectionChange modified_sections = 4;
}

message SectionChange {
  string section = 1;
  string old_hash = 2;
  string new_hash = 3;
  string old_text = 4;
  string new_text = 5;
}

message ChangeEvent {
  string source_id = 1;
  string change_type = 2;  // new_notification, amendment_published, new_judgment, registry_update
  string url = 3;
  string title = 4;
  int64 detected_at = 5;
}
```

---

## 13. Amendment Handling Workflow

### 13.1 What Happens When a Law is Amended

```
AMENDMENT PUBLISHED (e.g., Patents Amendment Act, 2024)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. DETECTION                                                     │
│    - Source monitor detects new notification/act               │
│    - ChangeEvent: amendment_published                           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ACQUISITION                                                  │
│    - Download new Amendment Act PDF                             │
│    - Download consolidated updated Act (if published)           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. PARSING & STRUCTURE EXTRACTION                               │
│    - Parse amendment act (standalone)                           │
│    - Parse consolidated act (if available)                      │
│    - Extract amended sections, new sections, repealed sections  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. VERSION CREATION                                             │
│    - Create NEW document version (not overwrite)                │
│    - Version ID = amendment date (e.g., "2024-03-15")           │
│    - Link: old_version.superseded_by = new_version              │
│    - Link: new_version.supersedes = old_version                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. SECTION-LEVEL DIFFING                                        │
│    - Compare each section: old_hash vs new_hash                 │
│    - Classify: ADDED, REMOVED, MODIFIED, UNCHANGED              │
│    - For MODIFIED: compute text diff                            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. CHUNK RE-GENERATION                                          │
│    - Re-chunk only CHANGED sections (incremental)               │
│    - Preserve unchanged chunk IDs for citation stability        │
│    - New chunks get new IDs                                     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. INDEX UPDATE                                                 │
│    - Mark old chunks as superseded (soft delete)                │
│    - Insert new chunks                                          │
│    - Update document registry                                   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. CITATION IMPACT ANALYSIS                                     │
│    - Find all chunks citing modified sections                   │
│    - Flag for review: "Source section amended on DATE"          │
│    - Notify evaluation pipeline                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. AUDIT & NOTIFICATION                                         │
│    - Log full amendment trail                                   │
│    - Alert downstream systems                                   │
│    - Update "source freshness" metrics                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14. Failure Modes & Recovery

| Stage | Failure Mode | Detection | Recovery | Fallback |
|-------|--------------|-----------|----------|----------|
| Acquisition | Source unavailable | HTTP 4xx/5xx, timeout | Retry with exponential backoff (3x) | Skip source, alert, use cached |
| Acquisition | Auth expired | 401/403 | Refresh credentials, retry | Manual intervention |
| Parsing | PDF corrupt | pdfplumber exception | Try PyMuPDF → OCR → fail | Log, skip document |
| Parsing | OCR low quality | Confidence < 60% | Flag for manual review | Use raw text with low confidence |
| Structure | Hierarchy broken | No acts/chapters found | Fallback to flat chunking | Section-only extraction |
| Chunking | Section too large | Tokens > max even after split | Increase max_tokens for this doc | Truncate with warning |
| Metadata | Missing required field | Validation error | Infer from context (act title from filename) | Reject chunk, log |
| Deduplication | Hash collision | SHA256 collision (extremely rare) | Use chunk_id + content double-check | Manual resolution |
| Versioning | Amendment not detected | New version same hash as old | Content comparison + date check | Manual trigger |
| Indexing | Vector DB full | Write error | Scale cluster, batch retry | Queue for later |
| Change Detection | Source structure changed | Selector fails | Update selectors, alert | Manual check |

---

## 15. Evaluation & Testing

### 15.1 Ingestion Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Structure Extraction F1 | > 95% | Labeled test set (50 Acts) |
| Section Boundary Accuracy | > 98% | Compare with official PDF bookmarks |
| Citation Extraction Precision | > 90% | Manual spot-check |
| Metadata Completeness | 100% required fields | Automated schema validation |
| Chunk Hierarchy Accuracy | > 95% | Parent-child linkage correctness |
| Version Detection Accuracy | 100% | Known amendment test cases |
| Deduplication Precision | > 99% | No false duplicate removal |
| Content Hash Stability | 100% | Same content = same hash always |

### 15.2 Test Corpus

```python
TEST_CORPUS = {
    "indian_acts": [
        "Patents Act 1970 (with all amendments)",
        "Trade Marks Act 1999",
        "Designs Act 2000",
        "Copyright Act 1957",
        "Biological Diversity Act 2002",
        "Drugs and Cosmetics Act 1940",
        "FSSAI Act 2006",
    ],
    "rules": [
        "Patents Rules 2003",
        "Trade Marks Rules 2017",
        "Biological Diversity Rules 2004",
        "ABS Rules 2014",
    ],
    "treaties": [
        "CBD 1992",
        "Nagoya Protocol 2010",
        "TRIPS",
        "PCT",
    ],
    "edge_cases": [
        "Scanned PDF (poor quality)",
        "Act with complex schedules",
        "Act with extensive footnotes",
        "Bilingual Act (English + Hindi)",
        "Amendment Act (standalone)",
        "Ordinance (temporary)",
    ]
}
```

---

## 16. Phase 4 Completion Checklist

- [x] Acquisition strategy per source (7 sources, with Playwright for JS-heavy)
- [x] Parsing strategy (PDF, HTML, OCR fallback)
- [x] OCR handling (Tesseract + layout analysis)
- [x] Normalization (Unicode, legal abbreviations, whitespace)
- [x] Structure extraction (Act→Chapter→Part→Section→Subsection→Clause)
- [x] Chunking strategy (legal-hierarchy-aware, parent-child, token-budgeted)
- [x] Metadata generation (full provenance, authority tier, jurisdiction, version)
- [x] Deduplication (content hash + near-duplicate cosine)
- [x] Versioning (immutable versions, supersession links, section-level diff)
- [x] Change detection (source monitors, notification processing)
- [x] Indexing (vector + lexical + metadata + graph)
- [x] Validation (schema, hierarchy, citations, completeness)
- [x] Amendment handling workflow (9-step process)
- [x] Source-specific configs (India Code, IP India, NBA, CBD, WIPO, FSSAI, AYUSH)
- [x] Failure modes & recovery per stage
- [x] Evaluation metrics & test corpus
- [x] Protobuf data models for all entities

**Phase 4 Status: COMPLETE** ✅

---

## Next Phase: Phase 5 - Chunking Strategy Deep Dive

**Entry Criteria:** Phase 4 ingestion architecture signed off  
**Deliverable:** Detailed chunking comparison with optimal legal-RAG chunk representation and citation mapping specification

**Reference Documents:**
- `/architecture/phase1-requirements.md`
- `/architecture/phase2-system-architecture.md`
- `/architecture/phase3-rag-architecture.md`
- `/architecture/phase4-ingestion-architecture.md` (this document)
- `/data/corpus/` - Test corpus for validation