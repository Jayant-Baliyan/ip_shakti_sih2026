# Phase 7: Knowledge Graph Architecture

## Overview

This document designs the knowledge graph (KG) architecture for IP-SAKTI. The KG is NOT a replacement for vector retrieval but a complementary layer that enables:
- Multi-hop legal reasoning (AMENDS → SUPERSEDES → IMPLEMENTS)
- Conflict detection between provisions
- Entity-centric retrieval (find all sections related to "Section 3(d)")
- Temporal versioning of legal provisions
- Cross-jurisdiction treaty mapping

**Key Principle**: Graph retrieval is an OPTIONAL enhancement module. Vector+lexical retrieval remains the primary path. Graph is invoked only when query analysis indicates multi-hop or entity-centric needs.

---

## 1. Requirements

### 1.1 Functional Requirements

| Requirement | Description |
|------------|-------------|
| **FR-KG-01** | Represent legal hierarchy: Act → Chapter → Section → Subsection → Clause |
| **FR-KG-02** | Model amendment relationships: AMENDS, SUPERSEDES, INSERTS, DELETES, MODIFIES |
| **FR-KG-03** | Model cross-reference relationships: REFERENCES, DEFINES, IMPLEMENTS, DELEGATES |
| **FR-KG-04** | Model treaty-domestic law mapping: IMPLEMENTS (treaty → domestic act) |
| **FR-KG-05** | Model case law relationships: CITES, OVERRULES, DISTINGUISHES, FOLLOWS |
| **FR-KG-06** | Model formulation classification: CLASSIFIES_AS, EXEMPTS, REQUIRES_LICENSE |
| **FR-KG-07** | Support temporal queries: "What did Section 3(d) say in 2010?" |
| **FR-KG-08** | Support conflict detection: CONFLICTS_WITH between provisions |
| **FR-KG-09** | Enable graph-augmented retrieval for multi-hop queries |
| **FR-KG-10** | Entity resolution: map "Section 3(d)" mentions to canonical KG node |

### 1.2 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| **NFR-KG-01** | Graph query latency: < 200ms (p95) |
| **NFR-KG-02** | Graph build time: < 2h for full corpus |
| **NFR-KG-03** | Incremental update: < 5min per amendment |
| **NFR-KG-04** | Storage: < 50GB for full Indian IP corpus |
| **NFR-KG-05** | Entity linking accuracy: > 90% F1 |

---

## 2. Entity Schema

### 2.1 Core Legal Entities

```cypher
// ============================================
// NODE LABELS
// ============================================

// Legislative Hierarchy
(:Act {
    act_id: String,           // "A1970-39"
    short_title: String,      // "Patents Act, 1970"
    long_title: String,
    act_number: Integer,      // 39
    act_year: Integer,        // 1970
    jurisdiction: Jurisdiction,  // INDIA
    authority_tier: Integer,  // 1
    enactment_date: Date,
    commencement_date: Date,
    status: ActStatus,        // IN_FORCE, REPEALED, AMENDED
    source_url: String,
    content_hash: String
})

(:Chapter {
    chapter_id: String,       // "A1970-39_CH2"
    act_id: String,
    number: String,           // "II"
    title: String,
    ordinal: Integer
})

(:Part {
    part_id: String,
    chapter_id: String,
    designation: String,      // "A", "B", "I", "II"
    title: String,
    ordinal: Integer
})

(:Section {
    section_id: String,       // "A1970-39_S3"
    act_id: String,
    chapter_id: String?,      // nullable
    part_id: String?,         // nullable
    number: String,           // "3"
    title: String?,           // "What are not inventions"
    full_text: String,        // Full section text
    ordinal: Integer,
    status: ProvisionStatus,  // IN_FORCE, AMENDED, REPEALED, NOT_YET_IN_FORCE
    effective_from: Date,
    effective_to: Date?,
    source_chunk_ids: [String]  // Links to Phase 5 chunks
})

(:Subsection {
    subsection_id: String,    // "A1970-39_S3_SS1"
    section_id: String,
    designation: String,      // "(1)", "(2)", "1"
    text: String,
    ordinal: Integer,
    status: ProvisionStatus,
    effective_from: Date,
    effective_to: Date?,
    source_chunk_ids: [String]
})

(:Clause {
    clause_id: String,        // "A1970-39_S3_SS1_CL_d"
    subsection_id: String?,
    section_id: String,       // Direct link for clauses without subsection
    designation: String,      // "(d)", "(i)", "a"
    text: String,
    ordinal: Integer,
    status: ProvisionStatus,
    effective_from: Date,
    effective_to: Date?,
    source_chunk_ids: [String]
})

// Definitions
(:Definition {
    definition_id: String,    // "A1970-39_DEF_invention"
    act_id: String,
    section_id: String?,      // Section containing definition
    term: String,             // "invention"
    defined_text: String,     // Full definition text
    is_inclusive: Boolean,    // "means" vs "includes"
    source_chunk_ids: [String]
})

// Treaties & International
(:Treaty {
    treaty_id: String,        // "TRIPS", "CBD", "NAGOYA", "PCT"
    short_name: String,
    full_name: String,
    adoption_date: Date,
    entry_into_force_date: Date,
    status: TreatyStatus,     // IN_FORCE, SUPERSEDED
    depositary: String,
    source_url: String,
    authority_tier: Integer   // 1
})

(:TreatyArticle {
    article_id: String,       // "TRIPS_Art27"
    treaty_id: String,
    number: String,           // "27"
    title: String?,
    text: String,
    ordinal: Integer,
    source_chunk_ids: [String]
})

// Case Law
(:Case {
    case_id: String,          // "SC_2013_2_SCC_1"
    citation: String,         // "Novartis v. Union of India, (2013) 2 SCC 1"
    court: Court,             // SUPREME_COURT, HIGH_COURT_DELHI, etc.
    jurisdiction: Jurisdiction,
    decision_date: Date,
    case_type: CaseType,      // APPEAL, WRIT_PETITION, REVIEW, etc.
    subject_matter: [String], // ["patent", "section_3d", "pharmaceutical"]
    source_url: String,
    authority_tier: Integer,  // 1 for SC, 2 for HC
    full_text_hash: String
})

(:Paragraph {
    paragraph_id: String,
    case_id: String,
    number: String,           // "12", "[12]"
    text: String,
    is_headnote: Boolean,
    is_holding: Boolean,      // Ratio decidendi
    source_chunk_ids: [String]
})

// Regulatory Guidance
(:Guideline {
    guideline_id: String,
    title: String,
    issuing_authority: String, // "NBA", "FSSAI", "CDSCO", "IP_India"
    jurisdiction: Jurisdiction,
    document_type: DocType,   // GUIDELINE, NOTIFICATION, CIRCULAR, FORM
    publication_date: Date,
    effective_date: Date?,
    status: GuidelineStatus,  // IN_FORCE, SUPERSEDED, WITHDRAWN
    authority_tier: Integer,  // 1 or 2
    source_url: String,
    source_chunk_ids: [String]
})

// Formulations & Products
(:Formulation {
    formulation_id: String,
    name: String,
    classification: FormulationClass,  // CLASSICAL, PATENT_PROPRIETARY, etc.
    ingredients: [IngredientRef],
    dosage_form: String,
    traditional_status: Boolean,
    source_reference: String
})

(:Ingredient {
    ingredient_id: String,
    name: String,
    scientific_name: String?,
    common_names: [String],
    plant_part: String?,      // root, leaf, bark, etc.
    is_biological_resource: Boolean
})

// Biological Resources (ABS)
(:BiologicalResource {
    resource_id: String,
    scientific_name: String,
    common_names: [String],
    geographical_origin: [String],
    is_endemic: Boolean,
    cites_appendix: String?,  // I, II, III
    iucn_status: String?
})

// ABS Applications
(:ABSApplication {
    application_id: String,
    applicant: String,
    biological_resources: [String],  // resource_ids
    associated_tk: [String],         // TK identifiers
    access_type: AccessType,         // RESEARCH, COMMERCIAL, BOTH
    status: ABSStatus,
    filing_date: Date,
    approval_date: Date?
})

// Registry Records (Patents, Trademarks, GI, Designs)
(:PatentRecord {
    record_id: String,        // "IN_2020_12345"
    application_number: String,
    title: String,
    applicants: [String],
    inventors: [String],
    ipc_classes: [String],
    filing_date: Date,
    publication_date: Date?,
    grant_date: Date?,
    status: PatentStatus,
    claims_text: String,
    abstract: String,
    source_chunk_ids: [String]
})

(:TrademarkRecord {
    record_id: String,
    application_number: String,
    mark_text: String,
    mark_image_hash: String?,
    nice_classes: [Integer],
    applicant: String,
    filing_date: Date,
    registration_date: Date?,
    status: TMStatus,
    goods_services: String,
    source_chunk_ids: [String]
})

// Geographic Indications
(:GIRecord {
    record_id: String,
    gi_name: String,
    goods: String,
    geographical_area: String,
    registered_proprietor: String,
    filing_date: Date,
    registration_date: Date,
    status: GIStatus,
    source_chunk_ids: [String]
})

// Traditional Knowledge
(:TKEntry {
    tk_id: String,            // TKDL reference
    formulation_name: String,
    system_of_medicine: String,  // AYURVEDA, UNANI, SIDDHA, YOGA
    ingredients: [IngredientRef],
    preparation_method: String,
    therapeutic_use: String,
    source_reference: String,   // TKDL book/page
    prior_art_date: Date,
    is_digitized: Boolean
})
```

---

## 3. Relationship Schema

### 3.1 Legislative Relationships

```cypher
// ============================================
// RELATIONSHIP TYPES
// ============================================

// Hierarchy (Containment)
(:Act)-[:HAS_CHAPTER]->(:Chapter)
(:Chapter)-[:HAS_PART]->(:Part)
(:Chapter)-[:HAS_SECTION]->(:Section)  // Direct if no Part
(:Part)-[:HAS_SECTION]->(:Section)
(:Section)-[:HAS_SUBSECTION]->(:Subsection)
(:Subsection)-[:HAS_CLAUSE]->(:Clause)
(:Section)-[:HAS_CLAUSE]->(:Clause)    // Direct if no Subsection
(:Section)-[:HAS_DEFINITION]->(:Definition)

// Amendment Relationships (TEMPORAL - critical!)
(:AmendmentAct)-[:AMENDS]->(:Act)
(:AmendmentAct)-[:AMENDS_SECTION]->(:Section)  // Specific section amended
(:AmendmentAct)-[:INSERTS]->(:Section)         // New section inserted
(:AmendmentAct)-[:DELETES]->(:Section)         // Section deleted
(:AmendmentAct)-[:SUBSTITUTES]->(:Section)     // Section replaced
(:AmendmentAct)-[:MODIFIES]->(:Section)        // Text modified

// Version tracking
(:Section)-[:HAS_VERSION]->(:SectionVersion)   // For temporal queries
(:SectionVersion)-[:SUPERSEDES]->(:SectionVersion)
(:SectionVersion)-[:EFFECTIVE_FROM]->(:Date)

// Cross-References (within same Act)
(:Section)-[:REFERENCES]->(:Section)           // "as per Section 5"
(:Section)-[:DEFINES_TERM]->(:Definition)      // Section contains definition
(:Definition)-[:DEFINED_IN]->(:Section)        // Reverse
(:Clause)-[:REFERENCES]->(:Clause)

// Implementation Relationships (Treaty → Domestic)
(:TreatyArticle)-[:IMPLEMENTED_BY]->(:Section)  // Treaty obligation → domestic provision
(:Section)-[:IMPLEMENTS]->(:TreatyArticle)      // Reverse
(:Act)-[:IMPLEMENTS_TREATY]->(:Treaty)          // Act-level

// Delegation (Act → Rules/Regulations)
(:Section)-[:DELEGATES_TO]->(:Rule)             // "Central Government may make rules"
(:Rule)-[:MADE_UNDER]->(:Section)               // Rule cites enabling section
(:Act)-[:HAS_RULES]->(:RulesInstrument)

// Case Law Relationships
(:Case)-[:CITES]->(:Case)                       // Precedent citation
(:Case)-[:OVERRULES]->(:Case)                   // Explicit overruling
(:Case)-[:DISTINGUISHES]->(:Case)               // Distinguished
(:Case)-[:FOLLOWS]->(:Case)                     // Follows precedent
(:Case)-[:INTERPRETS]->(:Section)               // Case interprets statutory provision
(:Section)-[:INTERPRETED_BY]->(:Case)           // Reverse
(:Paragraph)-[:QUOTES]->(:Section)              // Paragraph quotes statute
(:Paragraph)-[:DISCUSSES]->(:Section)           // Paragraph discusses provision

// Regulatory Guidance Relationships
(:Guideline)-[:CLARIFIES]->(:Section)           // Guideline clarifies statute
(:Guideline)-[:IMPLEMENTS]->(:Section)          // Guideline implements rule
(:Section)-[:HAS_GUIDELINE]->(:Guideline)       // Reverse
(:Notification)-[:AMENDS]->(:Guideline)         // Notification amends guideline

// Formulation Classification
(:Formulation)-[:CLASSIFIED_AS]->(:FormulationClass)
(:Formulation)-[:CONTAINS]->(:Ingredient)
(:Ingredient)-[:DERIVED_FROM]->(:BiologicalResource)
(:Formulation)-[:REQUIRES_ABS]->(:ABSRequirement)
(:Formulation)-[:EXEMPT_FROM]->(:Provision)     // Exemption

// ABS Relationships
(:ABSApplication)-[:ACCESSES]->(:BiologicalResource)
(:ABSApplication)-[:USES_TK]->(:TKEntry)
(:ABSApplication)-[:SUBMITTED_TO]->(:Authority)  // NBA, SBB
(:BiologicalResource)-[:FOUND_IN]->(:State)     // Geographical origin

// Conflict Detection
(:Section)-[:CONFLICTS_WITH]->(:Section)        // Direct conflict
(:Section)-[:OVERRIDES]->(:Section)             // Lex specialis / later in time
(:Provision)-[:SUBJECT_TO]->(:Provision)        // "Subject to Section X"

// Registry Relationships
(:PatentRecord)-[:CLAIMS_PRIORITY_FROM]->(:PatentRecord)  // Priority claim
(:PatentRecord)-[:CITES_PRIOR_ART]->(:PatentRecord)       // Citation
(:PatentRecord)-[:RELATES_TO]->(:Section)                 // Patent relates to legal provision
(:TrademarkRecord)-[:OPPOSED_BY]->(:TrademarkRecord)      // Opposition
(:GIRecord)-[:AUTHORIZED_USER]->(:Party)                   // Authorized user
```

---

## 4. Key Relationships: Which Are Actually Useful?

### 4.1 High-Value Relationships (CORE - Build First)

| Relationship | Use Case | Query Example |
|-------------|----------|---------------|
| `AMENDS_SECTION` / `SUPERSEDES` | Temporal versioning, "What was the law in 2010?" | Historical queries |
| `IMPLEMENTS` / `IMPLEMENTED_BY` | Treaty-domestic mapping | "Which Indian sections implement TRIPS Art 27?" |
| `INTERPRETS` / `INTERPRETED_BY` | Case law linkage | "How has SC interpreted Section 3(d)?" |
| `DELEGATES_TO` / `MADE_UNDER` | Act → Rules linkage | "What rules are made under Section 159?" |
| `REFERENCES` (statutory) | Cross-reference resolution | "Section 3(d) refers to which sections?" |
| `CONTAINS` (hierarchy) | Hierarchy traversal | "All sections in Chapter II" |
| `CLASSIFIES_AS` | Formulation routing | "Is this formulation classical?" |

### 4.2 Medium-Value Relationships (OPTIONAL - Phase 2+)

| Relationship | Use Case |
|-------------|----------|
| `OVERRIDES` / `SUBJECT_TO` | Conflict resolution |
| `CITES` (case law) | Precedent chain |
| `ACCESSES` / `USES_TK` | ABS compliance checking |
| `CLAIMS_PRIORITY_FROM` | Patent family |
| `HAS_VERSION` | Fine-grained temporal |

### 4.3 Low-Value / Experimental (EXPERIMENTAL)

| Relationship | Reason |
|-------------|--------|
| `DISTINGUISHES` | Rarely decisive |
| `AUTHORIZED_USER` | GI-specific, niche |
| `FOUND_IN` (State) | Geographical, limited use |

---

## 5. Graph Construction Pipeline

### 5.1 From Chunks to Graph (Phase 5 → Phase 7)

```python
class GraphBuilder:
    def __init__(self, graph_db: GraphDatabase):
        self.graph = graph_db
        self.entity_extractor = LegalEntityExtractor()
        self.relation_extractor = LegalRelationExtractor()
    
    def build_from_chunks(self, chunks: List[LegalChunk]):
        """Build KG from Phase 5 chunked documents."""
        
        # 1. Create legislative hierarchy nodes
        self._create_hierarchy_nodes(chunks)
        
        # 2. Extract and link definitions
        self._extract_definitions(chunks)
        
        # 3. Extract statutory cross-references
        self._extract_statutory_references(chunks)
        
        # 4. Build amendment chains
        self._build_amendment_chains(chunks)
        
        # 5. Link case law (separate ingestion)
        self._link_case_law()
        
        # 6. Link treaty implementations
        self._link_treaty_implementations()
        
        # 7. Link guidelines/notifications
        self._link_regulatory_guidance()
    
    def _create_hierarchy_nodes(self, chunks: List[LegalChunk]):
        """Create Act/Chapter/Section nodes from chunk hierarchy metadata."""
        acts_seen = set()
        chapters_seen = set()
        sections_seen = set()
        
        for chunk in chunks:
            h = chunk.hierarchy
            
            # Act node
            if h.act_id not in acts_seen:
                self.graph.create_act_node(
                    act_id=h.act_id,
                    short_title=h.act_short_title,
                    jurisdiction=h.jurisdiction,
                    authority_tier=chunk.source_provenance.authority_tier
                )
                acts_seen.add(h.act_id)
            
            # Chapter node
            if h.chapter and f"{h.act_id}_{h.chapter}" not in chapters_seen:
                self.graph.create_chapter_node(...)
                chapters_seen.add(f"{h.act_id}_{h.chapter}")
                self.graph.link(h.act_id, "HAS_CHAPTER", f"{h.act_id}_{h.chapter}")
            
            # Section node
            if h.section and h.section not in sections_seen:
                section_id = f"{h.act_id}_S{h.section}"
                self.graph.create_section_node(
                    section_id=section_id,
                    act_id=h.act_id,
                    chapter_id=f"{h.act_id}_{h.chapter}" if h.chapter else None,
                    number=h.section,
                    text=chunk.text,  # Full section text
                    status=chunk.amendment_status,
                    effective_from=chunk.effective_date,
                    source_chunk_ids=[chunk.chunk_id]
                )
                sections_seen.add(section_id)
                
                # Link to chapter/part
                parent = f"{h.act_id}_{h.part}" if h.part else (f"{h.act_id}_{h.chapter}" if h.chapter else h.act_id)
                rel = "HAS_SECTION" if h.chapter or h.part else "HAS_SECTION"
                self.graph.link(parent, rel, section_id)
            
            # Subsection/Clause nodes (similar pattern)
            ...
```

### 5.2 Entity Extraction for Relationships

```python
class LegalEntityExtractor:
    """
    Extract entity mentions from chunk text and link to KG nodes.
    """
    PATTERNS = {
        'section': r'Section\s+(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?(?:\([ivx]+\))?)',
        'article': r'Article\s+(\d+[A-Z]?)',
        'rule': r'Rule\s+(\d+[A-Z]?)',
        'clause': r'Clause\s+(\([a-z]\)|\([ivx]+\))',
        'schedule': r'Schedule\s+([IVX]+)',
        'act_name': r'(Patents?|Trade Marks?|Copyright|Designs?|Geographical Indications?|Biological Diversity|Drugs? and Cosmetics?|FSSAI)\s+Act,?\s*\d{4}',
        'case_citation': r'(\w+\s+v\.?\s+\w+.+?\(\d{4}\)\s+\d+\s+\w+\s+\d+)',
    }
    
    def extract_mentions(self, text: str, context_act_id: str) -> List[EntityMention]:
        mentions = []
        for entity_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append(EntityMention(
                    text=match.group(),
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    context_act_id=context_act_id
                ))
        return mentions
    
    def resolve_to_kg_node(self, mention: EntityMention) -> Optional[str]:
        """Map mention to canonical KG node ID."""
        if mention.entity_type == 'section':
            # "Section 3(d)" in context of Patents Act 1970
            section_num = self._parse_section_number(mention.text)
            return f"{mention.context_act_id}_S{section_num}"
        # ... other types
```

### 5.3 Relation Extraction

```python
class LegalRelationExtractor:
    """
    Extract relationships between entities from text.
    Uses pattern matching + LLM for complex cases.
    """
    
    AMENDMENT_PATTERNS = [
        (r'(?:amended|substituted|inserted|deleted|omitted)\s+by\s+(.+?)(?:\s+Act|\s*$)', 'AMENDS'),
        (r'(?:as\s+)?(?:inserted|added)\s+by\s+(.+?)(?:\s+Act|\s*$)', 'INSERTS'),
        (r'(?:omitted|deleted)\s+by\s+(.+?)(?:\s+Act|\s*$)', 'DELETES'),
        (r'(?:substituted|replaced)\s+by\s+(.+?)(?:\s+Act|\s*$)', 'SUBSTITUTES'),
    ]
    
    CROSS_REF_PATTERNS = [
        (r'(?:under|pursuant to|in accordance with)\s+(Section|Article|Rule)\s+(\d+)', 'REFERENCES'),
        (r'(?:as defined in|as per)\s+(Section|Clause)\s+(\d+)', 'REFERENCES'),
        (r'(?:subject to|notwithstanding)\s+(?:the provisions of\s+)?(Section|Article)\s+(\d+)', 'SUBJECT_TO'),
    ]
    
    def extract_relations(self, chunk: LegalChunk) -> List[Relation]:
        relations = []
        text = chunk.text_normalized
        
        # Amendment relations (from amendment notes in chunk)
        for pattern, rel_type in self.AMENDMENT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                amendment_act = self._normalize_act_name(match.group(1))
                relations.append(Relation(
                    source=f"{chunk.hierarchy.act_id}_S{chunk.hierarchy.section}",
                    target=amendment_act,
                    type=rel_type,
                    evidence=match.group(),
                    confidence=0.9
                ))
        
        # Cross-references
        for pattern, rel_type in self.CROSS_REF_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                ref_type = match.group(1)
                ref_num = match.group(2)
                target_id = f"{chunk.hierarchy.act_id}_{ref_type[0]}{ref_num}"
                relations.append(Relation(
                    source=chunk.chunk_id,
                    target=target_id,
                    type=rel_type,
                    evidence=match.group(),
                    confidence=0.8
                ))
        
        return relations
```

---

## 6. Graph Retrieval Patterns

### 6.1 Query Types That Benefit from Graph

```python
class GraphQueryPlanner:
    """
    Determine when to use graph retrieval vs vector retrieval.
    """
    
    GRAPH_QUERY_TYPES = {
        # Temporal queries
        'temporal_version': {
            'patterns': [r'what (was|were) .+ in \d{4}', r'as of \d{4}', r'before \d{4} amendment'],
            'graph_pattern': 'MATCH (s:Section)-[:HAS_VERSION*]->(v:SectionVersion) WHERE v.effective_from <= $date RETURN v'
        },
        
        # Treaty implementation
        'treaty_implementation': {
            'patterns': [r'implement', r'TRIPS', r'CBD', r'Nagoya', r'Paris Convention', r'PCT'],
            'graph_pattern': 'MATCH (ta:TreatyArticle)-[:IMPLEMENTED_BY]->(s:Section) WHERE ta.treaty_id = $treaty RETURN s'
        },
        
        # Case law interpretation
        'case_interpretation': {
            'patterns': [r'interpret', r'held that', r'judgment', r'Supreme Court', r'High Court', r'case law'],
            'graph_pattern': 'MATCH (c:Case)-[:INTERPRETS]->(s:Section) WHERE s.section_id = $section RETURN c'
        },
        
        # Amendment chain
        'amendment_history': {
            'patterns': [r'amend', r'history of', r'evolution of', r'changed'],
            'graph_pattern': 'MATCH (a:AmendmentAct)-[:AMENDS_SECTION]->(s:Section) WHERE s.section_id = $section RETURN a'
        },
        
        # Delegated legislation
        'delegated_rules': {
            'patterns': [r'rules under', r'regulation under', r'made under section'],
            'graph_pattern': 'MATCH (s:Section)-[:DELEGATES_TO]->(r:Rule) WHERE s.section_id = $section RETURN r'
        },
        
        # Conflict detection
        'conflict_check': {
            'patterns': [r'conflict', r'override', r'prevail', r'inconsistent'],
            'graph_pattern': 'MATCH (s1:Section)-[:CONFLICTS_WITH|OVERRIDES]->(s2:Section) WHERE s1.section_id = $section RETURN s2'
        },
        
        # Formulation classification
        'formulation_classification': {
            'patterns': [r'classif', r'category of', r'type of medicine', r'classical', r'patent.*proprietary'],
            'graph_pattern': 'MATCH (f:Formulation)-[:CLASSIFIED_AS]->(fc:FormulationClass) WHERE f.name CONTAINS $name RETURN fc'
        }
    }
    
    def should_use_graph(self, query_analysis: QueryAnalysis) -> bool:
        """Decide if graph retrieval adds value for this query."""
        # Use graph for:
        # - Explicit multi-hop queries
        # - Temporal/historical queries
        # - Treaty implementation queries
        # - Case law interpretation queries
        # - Amendment history queries
        # - Conflict detection queries
        
        intent = query_analysis.intent_category
        graph_intents = {
            'TEMPORAL_VERSION', 'TREATY_IMPLEMENTATION', 'CASE_INTERPRETATION',
            'AMENDMENT_HISTORY', 'DELEGATED_LEGISLATION', 'CONFLICT_DETECTION',
            'FORMULATION_CLASSIFICATION', 'ABS_COMPLIANCE'
        }
        return intent in graph_intents
```

### 6.2 Graph Retrieval Execution

```python
class GraphRetriever:
    def __init__(self, graph_db: GraphDatabase):
        self.graph = graph_db
        self.query_planner = GraphQueryPlanner()
    
    def retrieve(self, query: str, analysis: QueryAnalysis, 
                 vector_evidence: List[SelectedEvidence]) -> GraphEvidence:
        """
        Execute graph retrieval as supplement to vector retrieval.
        """
        if not self.query_planner.should_use_graph(analysis):
            return GraphEvidence(nodes=[], paths=[], used=False)
        
        # Extract entities from query and vector evidence
        entities = self._extract_query_entities(query, vector_evidence)
        
        # Execute relevant graph patterns
        graph_results = []
        for entity in entities:
            patterns = self.query_planner.get_patterns_for_entity(entity, analysis)
            for pattern in patterns:
                results = self.graph.execute(pattern, entity.parameters)
                graph_results.extend(results)
        
        # Convert to evidence format compatible with vector results
        evidence = self._convert_to_evidence(graph_results)
        
        return GraphEvidence(
            nodes=evidence,
            paths=graph_results,
            used=True,
            query_type=analysis.intent_category
        )
    
    def _convert_to_evidence(self, graph_results: List[GraphResult]) -> List[SelectedEvidence]:
        """Convert graph nodes/paths to SelectedEvidence format."""
        evidence = []
        for result in graph_results:
            # Get chunk IDs from node metadata
            chunk_ids = result.node.properties.get('source_chunk_ids', [])
            for chunk_id in chunk_ids:
                chunk = self.chunk_store.get(chunk_id)
                if chunk:
                    evidence.append(SelectedEvidence(
                        chunk=chunk,
                        relevance_score=result.score,
                        source='graph',
                        graph_path=result.path
                    ))
        return evidence
```

---

## 7. Hybrid Retrieval: Vector + Graph

### 7.1 Integration Architecture

```
                    ┌─────────────────────┐
                    │    USER QUERY       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  QUERY ANALYSIS     │
                    │  (Phase 3)          │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
    │  VECTOR+LEXICAL │ │   GRAPH      │ │  FORMULATION │
    │  RETRIEVAL      │ │  RETRIEVAL   │ │  CLASSIFIER  │
    │  (Phase 6)      │ │  (Phase 7)   │ │  (Phase 8)   │
    └────────┬────────┘ └──────┬───────┘ └──────┬───────┘
             │                 │                │
             ▼                 ▼                ▼
    ┌─────────────────────────────────────────────────┐
    │           EVIDENCE FUSION (RRF)                 │
    │  - Vector evidence (weight: 1.0)                │
    │  - Graph evidence (weight: 0.8)                 │
    │  - Formulation hints (weight: 0.5)              │
    └────────────────────┬────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  RERANKING + MMR    │
              └─────────────────────┘
```

### 7.2 Fusion Weights

| Evidence Source | Weight | Rationale |
|----------------|--------|-----------|
| Vector + Lexical (Primary) | 1.0 | Broad coverage, handles semantic queries |
| Graph (Targeted) | 0.8 | High precision for specific patterns, but limited coverage |
| Formulation Classification | 0.5 | Metadata signal, not direct evidence |

---

## 8. Graph Database Technology Selection

### 8.1 Requirements

| Requirement | Target |
|------------|--------|
| **Scale** | ~1M nodes, ~5M relationships |
| **Query Language** | Cypher (standard) or Gremlin |
| **ACID** | Required for consistency |
| **Temporal** | Native temporal support preferred |
| **Embeddings** | Vector search integration (optional) |
| **Deployment** | Docker, Kubernetes compatible |
| **Cost** | Open-source preferred for hackathon |

### 8.2 Options Comparison

| Database | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Neo4j Community** | Mature, Cypher, ACID, plugins, temporal | Memory-heavy, single-node free | **CORE** (production) |
| **FalkorDB** | Redis-based, fast, GraphQL, low memory | Smaller community | **OPTIONAL** (hackathon) |
| **Kuzu** | Embedded, columnar, fast OLAP, Cypher | No HA, single-node | **OPTIONAL** (analytics) |
| **Memgraph** | In-memory, streaming, open-source | RAM-heavy | **EXPERIMENTAL** |
| **ArangoDB** | Multi-model, AQL, scalable | Complex, less graph-optimized | Not recommended |
| **JanusGraph** | Scalable, Cassandra/HBase backend | Complex setup, Gremlin only | Overkill |

**Recommendation**: 
- **Hackathon/Dev**: FalkorDB (Redis-based, fast, easy Docker)
- **Production**: Neo4j (mature, tooling, temporal, clustering)

---

## 9. Incremental Updates

### 9.1 Amendment Processing

```python
class IncrementalGraphUpdater:
    def process_amendment(self, amendment_act: LegalChunk):
        """
        Process an amendment act and update graph incrementally.
        """
        # 1. Create AmendmentAct node
        amendment_node = self.graph.create_amendment_node(amendment_act)
        
        # 2. Parse amendment text for specific changes
        changes = self._parse_amendment_text(amendment_act.text)
        
        for change in changes:
            target_section_id = f"{change.act_id}_S{change.section_number}"
            
            if change.type == 'INSERT':
                # Create new section version
                new_version = self.graph.create_section_version(
                    section_id=target_section_id,
                    text=change.new_text,
                    effective_date=amendment_act.effective_date,
                    amendment_act_id=amendment_node.id
                )
                self.graph.link(amendment_node.id, "INSERTS", new_version.id)
                
            elif change.type == 'DELETE':
                # Mark current version as superseded
                current = self.graph.get_current_version(target_section_id)
                self.graph.link(current.id, "SUPERSEDES_BY", amendment_node.id)
                current.properties['status'] = 'REPEALED'
                current.properties['effective_to'] = amendment_act.effective_date
                
            elif change.type == 'SUBSTITUTE':
                # Create new version, link old → new
                old_version = self.graph.get_current_version(target_section_id)
                new_version = self.graph.create_section_version(...)
                self.graph.link(old_version.id, "SUPERSEDES", new_version.id)
                self.graph.link(amendment_node.id, "AMENDS_SECTION", new_version.id)
                
            elif change.type == 'MODIFY':
                # Create new version with modifications
                old_version = self.graph.get_current_version(target_section_id)
                new_text = self._apply_modification(old_version.text, change.modification)
                new_version = self.graph.create_section_version(...)
                self.graph.link(old_version.id, "SUPERSEDES", new_version.id)
                self.graph.link(amendment_node.id, "MODIFIES", new_version.id)
        
        # 3. Update cross-references if section numbers changed
        self._update_cross_references(changes)
```

---

## 10. Temporal Queries

### 10.1 Version Graph Model

```cypher
// Each Section has versions linked chronologically
(:Section {section_id: "A1970-39_S3"})-[:CURRENT_VERSION]->(:SectionVersion {version_id: "v3", text: "...", effective_from: "2021-09-15"})
(:SectionVersion {version_id: "v3"})-[:SUPERSEDES]->(:SectionVersion {version_id: "v2", text: "...", effective_from: "2005-01-01", effective_to: "2021-09-14"})
(:SectionVersion {version_id: "v2"})-[:SUPERSEDES]->(:SectionVersion {version_id: "v1", text: "...", effective_from: "1970-04-20", effective_to: "2004-12-31"})
```

### 10.2 Temporal Query Examples

```cypher
// What did Section 3(d) say on 2010-01-01?
MATCH (s:Section {section_id: "A1970-39_S3"})-[:HAS_VERSION]->(v:SectionVersion)
WHERE v.effective_from <= date("2010-01-01") 
  AND (v.effective_to IS NULL OR v.effective_to >= date("2010-01-01"))
RETURN v.text

// Show evolution of Section 3(d)
MATCH (s:Section {section_id: "A1970-39_S3"})-[:HAS_VERSION*]->(v:SectionVersion)
RETURN v.version_id, v.effective_from, v.effective_to, v.text
ORDER BY v.effective_from
```

---

## 11. Entity Resolution (Chunk → Graph)

### 11.1 Linking Retrieved Chunks to KG

```python
class ChunkToGraphLinker:
    """
    Link retrieved chunks (from Phase 6) to KG nodes for enhanced context.
    """
    def link_chunks_to_graph(self, chunks: List[LegalChunk]) -> List[GraphLinkedChunk]:
        linked = []
        for chunk in chunks:
            # Primary link: chunk's hierarchy → section node
            section_id = f"{chunk.hierarchy.act_id}_S{chunk.hierarchy.section}"
            section_node = self.graph.get_node(section_id)
            
            # Additional links: definitions, cross-refs in chunk
            mentions = self.entity_extractor.extract_mentions(chunk.text, chunk.hierarchy.act_id)
            linked_nodes = []
            for mention in mentions:
                kg_id = self.entity_extractor.resolve_to_kg_node(mention)
                if kg_id:
                    linked_nodes.append(kg_id)
            
            linked.append(GraphLinkedChunk(
                chunk=chunk,
                primary_kg_node=section_id,
                related_kg_nodes=linked_nodes,
                graph_context=self._get_graph_context(section_id, linked_nodes)
            ))
        return linked
    
    def _get_graph_context(self, primary: str, related: List[str]) -> GraphContext:
        """Fetch relevant graph neighborhood for context."""
        # 1-hop neighborhood
        neighbors = self.graph.get_neighbors(primary, max_hops=1)
        
        # Specific relationship types
        amendments = self.graph.get_related(primary, "AMENDS_SECTION|SUPERSEDES|INSERTS")
        interpretations = self.graph.get_related(primary, "INTERPRETED_BY")
        implementations = self.graph.get_related(primary, "IMPLEMENTS|IMPLEMENTED_BY")
        delegated = self.graph.get_related(primary, "DELEGATES_TO")
        
        return GraphContext(
            neighbors=neighbors,
            amendments=amendments,
            interpretations=interpretations,
            implementations=implementations,
            delegated_legislation=delegated
        )
```

---

## 12. Evaluation of Graph Utility

### 12.1 Experimental Framework

```python
class GraphUtilityExperiment:
    """
    Measure whether graph retrieval improves over vector-only baseline.
    """
    def run_experiment(self, test_queries: List[TestQuery]) -> ExperimentResult:
        results = []
        for query in test_queries:
            # Baseline: Vector + Lexical only
            vector_evidence = self.vector_retriever.retrieve(query)
            vector_answer = self.generator.generate(query, vector_evidence)
            vector_score = self.evaluator.score(query, vector_answer)
            
            # Enhanced: Vector + Graph
            graph_evidence = self.graph_retriever.retrieve(query, vector_evidence)
            fused_evidence = self.fuse_evidence(vector_evidence, graph_evidence)
            graph_answer = self.generator.generate(query, fused_evidence)
            graph_score = self.evaluator.score(query, graph_answer)
            
            results.append(QueryResult(
                query_id=query.id,
                vector_score=vector_score,
                graph_score=graph_score,
                improvement=graph_score - vector_score,
                graph_evidence_count=len(graph_evidence.nodes)
            ))
        
        return ExperimentResult(
            mean_improvement=mean(r.improvement for r in results),
            significant_improvement_rate=sum(1 for r in results if r.improvement > 0.05) / len(results),
            by_category=self._group_by_category(results)
        )
```

### 12.2 Success Criteria

| Metric | Threshold for "Graph Helps" |
|--------|----------------------------|
| **Mean answer quality improvement** | > 5% (statistically significant) |
| **Significant improvement rate** | > 30% of queries |
| **No regression on non-graph queries** | < 1% degradation |
| **Latency overhead** | < 200ms p95 |

---

## 13. Failure Modes & Mitigations

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| **Graph DB unavailable** | Connection timeout | Graceful degradation: skip graph, use vector only |
| **Incomplete graph** | Low node/edge count | Fallback to vector; log coverage gap |
| **Entity resolution errors** | Low linking rate | Conservative: only link high-confidence |
| **Stale amendment data** | Version mismatch | Rebuild amendment chains on corpus update |
| **Query planner false positive** | Graph returns empty | Cache negative decisions per query type |

---

## 14. Open Research Questions

| ID | Question | Status |
|----|----------|--------|
| ORQ-34 | Graph vs Vector for "What does Section 3(d) say?" (simple lookup)? | Likely vector wins |
| ORQ-35 | Optimal graph hop depth for legal reasoning (1 vs 2 vs 3)? | Experiment |
| ORQ-36 | Should we embed KG nodes and do vector search on graph? | Hybrid approach |
| ORQ-37 | Can LLM generate Cypher queries reliably for legal KG? | Experimental |
| ORQ-38 | How to handle "implied" relationships not explicit in text? | LLM extraction |

---

## 15. Implementation Priority

| Component | Priority | Phase |
|-----------|----------|-------|
| Legislative hierarchy nodes (Act/Chapter/Section) | **CORE** | Phase 1 |
| Amendment relationships (AMENDS, SUPERSEDES) | **CORE** | Phase 1 |
| Treaty implementation links | **CORE** | Phase 1 |
| Case law interpretation links | **OPTIONAL** | Phase 2 |
| Statutory cross-references (REFERENCES) | **CORE** | Phase 1 |
| Delegated legislation (Rules under Section) | **OPTIONAL** | Phase 2 |
| Formulation classification graph | **OPTIONAL** | Phase 2 |
| ABS application tracking | **EXPERIMENTAL** | Phase 3 |
| Graph-augmented retrieval integration | **OPTIONAL** | Phase 2 |
| Temporal versioning queries | **OPTIONAL** | Phase 2 |
| Conflict detection (CONFLICTS_WITH) | **EXPERIMENTAL** | Phase 3 |

---

## 16. Summary: KG Architecture Decision

| Aspect | Decision |
|--------|----------|
| **Role** | OPTIONAL enhancement module (not primary retrieval) |
| **Database** | FalkorDB (hackathon) / Neo4j (production) |
| **Core Entities** | Act, Chapter, Section, Subsection, Clause, Definition, Treaty, Case, Guideline |
| **Core Relationships** | Hierarchy, AMENDS/SUPERSEDES, IMPLEMENTS, INTERPRETS, DELEGATES_TO, REFERENCES |
| **Construction** | From Phase 5 chunks + separate case law/treaty ingestion |
| **Query Integration** | Triggered by query analysis (multi-hop, temporal, treaty, case law) |
| **Fusion** | RRF with graph weight 0.8 |
| **Temporal** | Version chain per Section (HAS_VERSION → SUPERSEDES) |
| **Evaluation** | A/B test vs vector-only; must show >5% improvement on target query types |

---

## 17. Next Phase: Phase 8 - Formulation Classification

The KG provides the `CLASSIFIES_AS` relationship and `FormulationClass` nodes. Phase 8 will design the **deterministic + AI-assisted classification engine** that:
- Extracts ingredients, dosage, claims from user input
- Applies deterministic legal rules (Schedule E, Rule 158, etc.)
- Uses LLM for borderline cases
- Outputs classification with confidence
- Escalates to human expert when uncertain

**Key interface**: Classification engine outputs `FormulationClass` which feeds into Query Analysis (Phase 3) and Retrieval Filters (Phase 6).