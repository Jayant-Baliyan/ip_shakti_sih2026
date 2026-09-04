# Phase 1: Requirements Engineering
## IP-SAKTI Sahayak - Complete Requirements Specification

**Status:** COMPLETE
**Version:** 1.0
**Date:** 2026-09-02

---

## 1. Functional Requirements

### 1.1 Core Capabilities by Domain

| FR-ID | Requirement | Description | Priority |
|-------|-------------|-------------|----------|
| FR-001 | Legal Provision Lookup | Retrieve exact sections, articles, clauses from Acts, Rules, Regulations, Treaties | P0 |
| FR-002 | Procedural Guidance | Step-by-step procedures for filings, registrations, compliance | P0 |
| FR-003 | Classification/Identification | Classify formulations, products, IP subject matter | P0 |
| FR-004 | Compliance Checking | Verify if a formulation/action complies with specific regulation | P0 |
| FR-005 | Comparative Analysis | Compare provisions across jurisdictions or versions | P1 |
| FR-006 | Prior-Art Search | Search TKDL, patent databases for traditional knowledge/prior art | P0 |
| FR-007 | Case Law Retrieval | Retrieve relevant court decisions with citations | P1 |
| FR-008 | Regulatory Pathway Identification | Identify applicable regulatory route for a product/formulation | P0 |
| FR-009 | ABS Guidance | Determine ABS obligations for biological resource access | P0 |
| FR-010 | IP Route Identification | Identify appropriate IP protection (patent/TM/GI/design/copyright/PVP) | P0 |

### 1.2 Cross-Cutting Functional Requirements

| FR-ID | Requirement | Description | Priority |
|-------|-------------|-------------|----------|
| FR-101 | Multilingual Interaction | Accept queries and respond in English + Indian languages | P0 |
| FR-102 | Jurisdiction Selection/Detection | Explicit selection or automatic detection of applicable jurisdiction | P0 |
| FR-103 | Authoritative Source Retrieval | Retrieve from official sources with provenance | P0 |
| FR-104 | Exact Citations | Provide section/article/clause numbers, not just document references | P0 |
| FR-105 | Confidence/Evidence Indication | Show confidence scores and evidence strength per claim | P0 |
| FR-106 | Safe Abstention | Explicitly decline when evidence is insufficient | P0 |
| FR-107 | Human/Legal-Expert Escalation | Route to human expert for complex/high-stakes queries | P1 |
| FR-108 | Version Awareness | Handle amended/superseded laws with effective dates | P0 |
| FR-109 | Source Authority Indication | Show authority tier (Tier 1-4) for each citation | P0 |
| FR-110 | Jurisdiction Isolation | Never mix laws from different jurisdictions in a single answer | P0 |

---

## 2. Non-Functional Requirements

| NFR-ID | Category | Requirement | Target | Measurement |
|--------|----------|-------------|--------|-------------|
| NFR-001 | Latency | End-to-end query response (simple) | < 3 seconds | p95 |
| NFR-002 | Latency | End-to-end query response (complex) | < 10 seconds | p95 |
| NFR-003 | Latency | Retrieval stage | < 500ms | p95 |
| NFR-004 | Latency | Reranking stage | < 300ms | p95 |
| NFR-005 | Latency | LLM generation | < 5 seconds | p95 |
| NFR-006 | Throughput | Concurrent queries | 50 QPS | sustained |
| NFR-007 | Availability | Uptime | 99.5% | monthly |
| NFR-008 | Accuracy | Retrieval Recall@10 | > 85% | benchmark |
| NFR-009 | Accuracy | Retrieval Precision@5 | > 70% | benchmark |
| NFR-010 | Accuracy | Citation Precision | > 90% | benchmark |
| NFR-011 | Accuracy | Groundedness | > 95% | benchmark |
| NFR-012 | Accuracy | Hallucination Rate | < 1% | benchmark |
| NFR-013 | Accuracy | Abstention Accuracy | > 95% | benchmark |
| NFR-014 | Scalability | Document corpus | 1M+ documents | storage/index |
| NFR-015 | Scalability | Concurrent users | 1000+ | concurrent |
| NFR-016 | Security | Data encryption | AES-256 at rest, TLS 1.3 in transit | audit |
| NFR-017 | Security | Authentication | OAuth 2.0 / OIDC | implementation |
| NFR-018 | Privacy | PII handling | No PII in logs/traces; user data isolation | audit |
| NFR-019 | Auditability | Full traceability | Answer → Claim → Evidence → Source | 100% |
| NFR-020 | Maintainability | Component modularity | Independent deployability | architecture review |

---

## 3. User Personas

| Persona | Description | Primary Use Cases | Technical Proficiency |
|---------|-------------|-------------------|----------------------|
| **P1: IP Attorney / Patent Agent** | Professional handling patent/TM/Design filings, oppositions, litigation | Prior-art search, patentability assessment, procedural guidance, case law | High |
| **P2: Regulatory Affairs Professional** | Pharma/Ayurveda/food industry compliance | Regulatory pathway, classification, compliance checking, ABS | High |
| **P3: Ayurveda/Traditional Medicine Practitioner** | Vaidyas, formulators, manufacturers | Formulation classification, Ayurveda-Aahar, Drugs & Cosmetics, TKDL | Medium |
| **P4: Researcher / Academic** | IP law, TK, biodiversity, ABS researchers | Comparative analysis, treaty interpretation, case law, academic writing | High |
| **P5: Startup Founder / Entrepreneur** | Early-stage IP strategy, regulatory navigation | IP route identification, freedom-to-operate, regulatory basics | Medium |
| **P6: Policy Maker / Government Official** | Policy formulation, legislative review | Comparative law, impact assessment, international obligations | High |
| **P7: General Public / Citizen** | Basic IP/TK/ABS awareness | Simplified guidance, rights awareness, complaint procedures | Low |

---

## 4. User Journeys

### 4.1 Patent Prior-Art Search Journey
```
User (P1) → "Find prior art for herbal wound healing formulation with neem and turmeric"
→ Language: English → Jurisdiction: India (auto-detected) → Intent: Prior-art search
→ Formulation: Herbal/phytopharmaceutical → Retrieval: TKDL + InPASS + Patent journals
→ Evidence: TK entries, published applications, granted patents
→ Claims: "Neem+tumeric wound healing disclosed in TKDL entry XXXX" + "Patent INXXXX claims similar"
→ Citations: TKDL accession, Patent publication number, Section claims
→ Confidence: High (Tier 1 sources) → Answer with structured evidence
```

### 4.2 Trademark Availability Journey
```
User (P5) → "Can I trademark 'Himalayan Gold' for ayurvedic oils?"
→ Language: English → Jurisdiction: India → Intent: TM availability
→ Classification: Nice Class 3/5 → Retrieval: TMR database, TM Journal
→ Evidence: Existing marks, examination guidelines
→ Claims: "Similar marks exist in Class 5" + "Descriptive terms face objection under Section 9"
→ Citations: TM App numbers, Section 9 TM Act, Examination Guidelines para X
→ Confidence: Medium → Recommend professional search
```

### 4.3 Ayurveda Formulation Classification Journey
```
User (P3) → "My formulation has 15 herbs, classical reference in Sahasrayogam, manufactured traditionally. What category?"
→ Language: Hindi → Jurisdiction: India → Intent: Classification
→ Input extraction: Ingredients, classical reference, manufacturing method
→ Rule engine: Classical reference → Classical Medicine (Rule 158-B D&C Rules)
→ LLM reasoning: Verify classical text authenticity, ingredient match
→ Conflicting evidence: If marketed with modern claims → may be proprietary
→ Output: Classical Medicine (Schedule E(1)) with confidence 0.85
→ Citations: D&C Rules Rule 158-B, Sahasrayogam reference, Gazette notification
→ Escalation: If confidence < 0.7 → human expert
```

### 4.4 ABS Compliance Check Journey
```
User (P2) → "German company wants to access Indian medicinal plant for research. ABS process?"
→ Language: English → Jurisdiction: India + International (Nagoya) → Intent: ABS guidance
→ Resource: Medicinal plant (biological resource) → User: Non-Indian entity
→ Retrieval: BD Act 2002, ABS Rules 2014, NBA guidelines, Nagoya Protocol
→ Evidence: Section 3 BD Act (prior approval), Rule 14-17 ABS Rules (application process)
→ Claims: "Foreign entity needs NBA approval (Form I)" + "MAT required (Section 21)"
→ Citations: BD Act Sections 3, 7, 21; ABS Rules 14-17, 19-20; Nagoya Art 6, 15
→ Confidence: High → Structured step-by-step process
```

### 4.5 Regulatory Pathway Identification Journey
```
User (P5) → "Herbal immunity booster powder - food supplement or Ayurveda medicine?"
→ Language: English → Jurisdiction: India → Intent: Regulatory pathway
→ Input: Ingredients, claims ("immunity booster"), dosage form
→ Formulation classification: Ayurveda-Aahar vs. ASU Drug vs. Nutraceutical
→ Retrieval: FSSAI Ayurveda-Aahar regulations, D&C Rules, AYUSH guidelines
→ Evidence: Claim type determines category; "immunity" = therapeutic claim → ASU Drug
→ Claims: "Therapeutic claims → ASU Drug license (D&C Act)" + "Food claims → FSSAI license"
→ Citations: D&C Act Section 3(a), Rule 158-B; FSSAI Ayurveda-Aahar Regulations 2022
→ Confidence: Medium → Escalation for borderline cases
```

### 4.6 International Treaty Obligation Check Journey
```
User (P6) → "India's obligations under Nagoya Protocol for digital sequence information (DSI)"
→ Language: English → Jurisdiction: International (India party) → Intent: Treaty interpretation
→ Retrieval: CBD, Nagoya Protocol text, COP decisions, India's national reports
→ Evidence: Nagoya Art 2 (DSI scope under discussion), COP 15 Decision, India's ABS Rules
→ Claims: "DSI not explicitly in Nagoya text" + "India's ABS Rules cover 'derivatives'"
→ Citations: Nagoya Protocol Articles 2, 10; CBD COP 15/7; BD Act Section 2(c); ABS Rules
→ Confidence: Medium (evolving area) → Flag as interpretive
```

---

## 5. Query Categories

| Category | Description | Example Queries | Retrieval Strategy |
|----------|-------------|-----------------|-------------------|
| **QC-01: Provision Lookup** | Exact legal text retrieval | "Section 3(d) Patents Act", "Article 27 TRIPS" | Direct section lookup + vector |
| **QC-02: Procedural** | Step-by-step process | "How to file PCT in India?", "GI registration process" | Structured retrieval + guidelines |
| **QC-03: Classification** | Categorize subject matter | "Is this a classical medicine?", "Nice class for herbal soap" | Rule engine + LLM reasoning |
| **QC-04: Compliance** | Check against requirements | "Does my product need ABS approval?", "FSSAI label requirements" | Rule-based + evidence retrieval |
| **QC-05: Comparative** | Cross-jurisdiction/version | "Patent term India vs US", "GI protection EU vs India" | Multi-jurisdiction retrieval |
| **QC-06: Prior-Art** | Search existing knowledge | "TKDL entries for ashwagandha", "Patents on neem extraction" | Specialized DB search (TKDL, InPASS) |
| **QC-07: Case Law** | Judicial decisions | "Supreme Court on Section 3(d)", "Delhi HC trademark dilution" | Case law DB + citation network |
| **QC-08: Regulatory Pathway** | Identify applicable regime | "Regulatory path for herbal capsule", "Cosmetic vs drug boundary" | Classification + provision lookup |
| **QC-09: Treaty Obligation** | International law interpretation | "Nagoya DSI obligations", "TRIPS flexibilities for pharma" | Treaty text + COP decisions + national law |
| **QC-10: Fact Verification** | Verify specific claim | "Is turmeric patented?", "Does India recognize plant patents" | Authority-weighted retrieval |

---

## 6. Legal/Regulatory Domains

### 6.1 India - Primary Domains

| Domain | Key Sources | Document Types | Special Handling |
|--------|-------------|----------------|------------------|
| **Patents** | Patents Act 1970, Patents Rules 2003 (amended), Manual of Patent Practice | LEGISLATION, RULE, GUIDELINE, PATENT_RECORD | Version tracking critical (2005, 2016, 2020, 2024 amendments) |
| **Trade Marks** | TM Act 1999, TM Rules 2017, Examination Guidelines | LEGISLATION, RULE, GUIDELINE, TRADEMARK_RECORD | Nice classification, well-known marks |
| **Geographical Indications** | GI Act 1999, GI Rules 2002, GI Journal | LEGISLATION, RULE, REGISTRY_RECORD, GI_RECORD | Registry records distinct from legislation |
| **Copyright** | Copyright Act 1957, Copyright Rules 2013 | LEGISLATION, RULE, REGISTRY_RECORD | International treaties (Berne, WIPO Copyright Treaty) |
| **Designs** | Designs Act 2000, Designs Rules 2001 | LEGISLATION, RULE, DESIGN_RECORD | Hague System interplay |
| **Plant Variety Protection** | PPVFR Act 2001, PPVFR Rules 2003 | LEGISLATION, RULE, REGISTRY_RECORD | UPOV interface, farmers' rights |
| **Biological Diversity** | BD Act 2002, BD Rules 2004, ABS Rules 2014 | LEGISLATION, RULE, REGULATION, GUIDELINE | State rules, BMC/PBR interplay |
| **Access & Benefit Sharing** | Nagoya Protocol, BD Act, ABS Rules, NBA Guidelines | TREATY, LEGISLATION, RULE, GUIDELINE | PIC, MAT, compliance certificates |
| **Drugs & Cosmetics** | D&C Act 1940, D&C Rules 1945, ASU Rules | LEGISLATION, RULE, REGULATION, GUIDELINE | Schedule E(1), Rule 158-B, ASU Drugs |
| **Drugs & Magic Remedies** | DMR Act 1954, DMR Rules 1955 | LEGISLATION, RULE | Prohibited advertisements |
| **FSSAI / Ayurveda-Aahar** | FSS Act 2006, Ayurveda-Aahar Regulations 2022 | LEGISLATION, REGULATION, GUIDELINE | Food vs. medicine boundary |
| **AYUSH** | NCISM Act 2020, NCH Act 2020, AYUSH Guidelines | LEGISLATION, REGULATION, GUIDELINE | Education, practice, drug standards |
| **TKDL** | TKDL database (where accessible) | TK_RESOURCE | Access restrictions apply |
| **Case Law** | Supreme Court, High Courts, IPAB (legacy), Commercial Courts | CASE_LAW | Citation network, precedent weight |

### 6.2 International Domains

| Domain | Key Sources | Document Types | Notes |
|--------|-------------|----------------|-------|
| **TRIPS** | WTO Agreement, Dispute Settlement reports | TREATY, CASE_LAW | Minimum standards, flexibilities |
| **CBD** | Convention text, COP decisions, SBSTTA reports | TREATY, REGULATION | National implementation varies |
| **Nagoya Protocol** | Protocol text, COP-MOP decisions, ABS Clearing-House | TREATY, REGULATION | PIC, MAT, compliance |
| **WIPO GRATK** | Treaty text (2024), WIPO guidance | TREATY | New treaty - implementation pending |
| **PCT** | PCT Treaty, Regulations, Administrative Instructions, WIPO Handbook | TREATY, REGULATION, GUIDELINE | National phase entry rules |
| **Madrid** | Madrid Agreement/Protocol, Common Regulations | TREATY, REGULATION | International registration |
| **Hague** | Hague Act, Common Regulations | TREATY, REGULATION | International designs |
| **Budapest** | Budapest Treaty, Regulations | TREATY, REGULATION | Microorganism deposit |
| **UPOV** | UPOV 1991 Convention | TREATY | PVP - India not member but relevant |

---

## 7. Jurisdiction Dimensions

### 7.1 Jurisdiction Taxonomy

```
JURISDICTION
├── NATIONAL
│   ├── India (Central)
│   │   ├── Parliament (Acts)
│   │   ├── Ministries (Rules/Regulations)
│   │   ├── Regulatory Bodies (Guidelines/Notifications)
│   │   ├── Courts (Case Law)
│   │   └── Registries (Patent/TM/Design/GI/PVP)
│   └── Indian States
│       ├── State Legislatures (State Acts)
│       ├── State Biodiversity Boards (Rules/Notifications)
│       ├── State Drug Licensing Authorities
│       └── State AYUSH Departments
├── INTERNATIONAL_TREATY
│   ├── WTO (TRIPS)
│   ├── CBD / Nagoya Protocol
│   ├── WIPO (PCT, Madrid, Hague, Budapest, GRATK)
│   └── UPOV
├── REGIONAL
│   ├── ARIPO (Africa)
│   ├── OAPI (Africa)
│   ├── EAPO (Eurasia)
│   └── EU (EUIPO, EPO)
└── FOREIGN_NATIONAL
    ├── USA (USPTO, Federal Courts, State laws)
    ├── EU (EPO, EUIPO, CJEU, National laws)
    ├── Japan (JPO, Courts)
    ├── China (CNIPA, Courts)
    └── Others (as needed)
```

### 7.2 Jurisdiction Detection Rules

| Signal | Weight | Action |
|--------|--------|--------|
| Explicit user selection | 1.0 | Override all |
| Query mentions jurisdiction | 0.8 | Strong signal |
| Cited law/section jurisdiction | 0.9 | Binding |
| User location/profile | 0.3 | Weak default |
| Document corpus availability | 0.5 | Practical constraint |

### 7.3 Multi-Jurisdiction Query Handling

- **Separate answer sections** per jurisdiction
- **Explicit conflict identification** when laws conflict
- **No silent mixing** - each claim tagged with jurisdiction
- **Temporal validity** per jurisdiction (effective dates)

---

## 8. Language Dimensions

### 8.1 Supported Languages (Phased)

| Phase | Languages | Script | Priority |
|-------|-----------|--------|----------|
| 1 (MVP) | English, Hindi | Latin, Devanagari | P0 |
| 2 | Tamil, Telugu, Bengali, Marathi | Respective scripts | P1 |
| 3 | Gujarati, Kannada, Malayalam, Punjabi, Urdu | Respective scripts | P1 |
| 4 | International: French, Spanish, Arabic, Chinese, Russian | Latin, Arabic, Cyrillic, Han | P2 |

### 8.2 Language Requirements

| Requirement | Specification |
|-------------|---------------|
| **Detection** | Automatic (fastText / CLD3) + user override |
| **Query Translation** | Translate query to English for retrieval; preserve original for response |
| **Legal Term Preservation** | Never translate legal terms of art (e.g., "prior art", "novelty", "inventive step", "Section 3(d)") |
| **Multilingual Embeddings** | Use multilingual models (e.g., jina-embeddings-v3, multilingual-e5-large) |
| **Cross-lingual Retrieval** | Retrieve in original language + translated query (dual) |
| **Response Generation** | Generate in query language; citations in source language |
| **Terminology Normalization** | Canonical term mapping per language (e.g., "पेटेंट" ↔ "patent") |

---

## 9. Source Authority Levels

| Tier | Authority | Examples | Retrieval Weight | Citation Requirement |
|------|-----------|----------|------------------|---------------------|
| **Tier 1** | **Official Primary Law** | Acts, Rules, Regulations, Treaties, Official Registries, Court Judgments, Official Gazettes | 1.0 (highest) | Mandatory for legal claims |
| **Tier 2** | **Official Secondary** | Government guidelines, examination manuals, official notifications, institutional publications (WIPO, NBA, IP India) | 0.8 | Strongly preferred |
| **Tier 3** | **Academic/Research** | Peer-reviewed journals, law reviews, empirical studies, WIPO publications | 0.5 | Supplementary only |
| **Tier 4** | **Commentary/Analysis** | Legal blogs, practitioner articles, commercial commentaries, news | 0.2 | Never sole basis for legal claim |

### 9.1 Authority Enforcement Rules

1. **Legal claims MUST have Tier 1 or Tier 2 evidence**
2. **Tier 3/4 can only supplement, not establish legal propositions**
3. **Retrieval ranking MUST incorporate authority tier**
4. **Citation display MUST show authority tier**
5. **Abstention triggered if only Tier 3/4 evidence for legal claim**

---

## 10. Safety Requirements

| SR-ID | Requirement | Implementation |
|-------|-------------|----------------|
| SR-001 | No fabrication of legal authority | Citation verification against source index |
| SR-002 | No hallucination of statutes/sections/rules | Claim → evidence entailment check |
| SR-003 | No fabrication of patent records/case citations | Registry record verification |
| SR-004 | No fabrication of URLs | Canonical URL registry |
| SR-005 | Jurisdiction isolation | Jurisdiction tag on every chunk; filter at retrieval |
| SR-006 | Explicit abstention | Confidence threshold + evidence sufficiency check |
| SR-007 | Version correctness | Effective date validation; superseded version flagging |
| SR-008 | Contradiction detection | Flag conflicting sources; present both with authority |
| SR-009 | Prompt injection defense | Input sanitization; system prompt isolation |
| SR-010 | Malicious document defense | Content validation; sandboxed parsing |

---

## 11. Privacy Requirements

| PR-ID | Requirement | Implementation |
|-------|-------------|----------------|
| PR-001 | Query data minimization | No PII in query logs; hash user IDs |
| PR-002 | Conversation memory isolation | Per-session; opt-in persistence; TTL |
| PR-003 | User preference storage | Encrypted; user-controlled; GDPR/PDP Act compliant |
| PR-004 | No training on user data | Explicit opt-out default; no fine-tuning on queries |
| PR-005 | Audit log anonymization | Pseudonymized trace IDs; no query text in metrics |

---

## 12. Audit Requirements

| AR-ID | Requirement | Implementation |
|-------|-------------|----------------|
| AR-001 | Full answer traceability | Trace ID: Query → Retrieval → Evidence → Prompt → Model → Claims → Citations → Answer |
| AR-002 | Retrieval decision logging | Why each chunk retrieved (scores, filters, fusion) |
| AR-003 | Citation verification log | Each claim's evidence mapping + verification result |
| AR-004 | Version audit | Document version at retrieval time |
| AR-005 | Human escalation log | Trigger, expert assignment, resolution |
| AR-006 | Feedback capture | User feedback on accuracy/helpfulness |

---

## 13. Explainability Requirements

| ER-ID | Requirement | Implementation |
|-------|-------------|----------------|
| ER-001 | Why this jurisdiction? | Jurisdiction detection signals + weights |
| ER-002 | Why this formulation class? | Rule engine trace + LLM reasoning trace |
| ER-003 | Why these sources? | Retrieval scores, authority tiers, filters |
| ER-004 | Confidence breakdown | Per-claim confidence (evidence strength, authority, entailment) |
| ER-005 | Abstention reason | Specific evidence gap identified |

---

## 14. Citation Requirements

| CR-ID | Requirement | Specification |
|-------|-------------|---------------|
| CR-001 | Exact locator | Section/Article/Clause/Rule/Paragraph number |
| CR-002 | Document version | Version ID, effective date, amendment number |
| CR-003 | Canonical URL | Official source URL (stable) |
| CR-004 | Authority tier | Tier 1-4 label |
| CR-005 | Source type | LEGISLATION/RULE/TREATY/REGISTRY_RECORD/etc. |
| CR-006 | Jurisdiction | Explicit jurisdiction tag |
| CR-007 | Language | Source language + translation status |
| CR-008 | Retrieval timestamp | When evidence was retrieved |
| CR-009 | Verification status | Verified/Unverified/Conflicted |

---

## 15. Update/Versioning Requirements

| VR-ID | Requirement | Specification |
|-------|-------------|---------------|
| VR-001 | Amendment detection | Monitor sources for changes (scheduled + webhook) |
| VR-002 | Version preservation | Never overwrite; new version + supersession link |
| VR-003 | Change detection | Diff engine; classify change type (textual, structural, repeal) |
| VR-004 | Re-indexing | Incremental re-index of affected chunks |
| VR-005 | Affected citation detection | Find all answers citing changed sections |
| VR-006 | Audit trail | Immutable log of all version changes |
| VR-007 | User notification | Alert users with saved queries on relevant changes |

---

## 16. Scalability Requirements

| SCR-ID | Dimension | Target | Strategy |
|--------|-----------|--------|----------|
| SCR-001 | Document count | 1M+ | Partitioned vector index; sharded PostgreSQL |
| SCR-002 | Chunk count | 50M+ | Hierarchical indexing; parent-child |
| SCR-003 | Query throughput | 50 QPS sustained | Async pipeline; caching; horizontal scaling |
| SCR-004 | Multilingual index | 15+ languages | Language-partitioned indices; shared multilingual embeddings |
| SCR-005 | Knowledge graph | 10M+ nodes/edges | Property graph DB (Neo4j/Kuzu); partitioned |
| SCR-006 | Ingestion throughput | 10K docs/hour | Parallel workers; streaming pipeline |

---

## 17. Failure Modes

| FM-ID | Failure Mode | Detection | Recovery | Fallback | User-Facing |
|-------|--------------|-----------|----------|----------|-------------|
| FM-001 | No relevant document | Retrieval returns empty | Expand query; try broader filters | "No authoritative source found" | Clear statement + suggestion |
| FM-002 | Outdated law retrieved | Version check fails; effective date past | Flag version; retrieve current | Show both versions with warning | "This may be outdated" banner |
| FM-003 | Conflicting law versions | Multiple versions for same section | Present all with dates/authority | Latest valid version | Comparison table |
| FM-004 | Wrong jurisdiction | Jurisdiction classifier low confidence | Ask user clarification | Multi-jurisdiction answer | "Assuming India..." disclaimer |
| FM-005 | Wrong formulation class | Rule engine + LLM disagreement | Flag for human review | Conservative classification | "Uncertain - consult expert" |
| FM-006 | Poor OCR quality | OCR confidence < threshold | Flag for manual review | Use alternative source | "Source quality low" |
| FM-007 | Misleading document | Authority tier low; fact-check fails | Cross-reference with Tier 1 | Exclude from legal claims | "Secondary source only" |
| FM-008 | Conflicting sources | Multiple Tier 1 sources disagree | Present conflict; no synthesis | Show both with analysis | "Authorities differ" |
| FM-009 | Hallucinated citation | Citation verification fails | Regenerate with verified citations | Abstain | "Cannot verify this claim" |
| FM-010 | Incomplete citation | Missing locator/version/URL | Attempt enrichment | Partial citation + warning | "Citation incomplete" |
| FM-011 | Multilingual retrieval failure | Low cross-lingual scores | Translate query; retry | English-only retrieval | "Limited results in X language" |
| FM-012 | Graph retrieval failure | Graph DB timeout/error | Fallback to vector-only | Vector-only results | Silent fallback (log) |
| FM-013 | Vector DB failure | Connection error | Read replica; cached results | Lexical-only (BM25) | Degraded mode notice |
| FM-014 | LLM failure | API error/timeout | Retry; fallback model | Cached/template response | "Service temporarily limited" |
| FM-015 | External API failure | Source API down | Cached data; stale warning | Offline mode | "Some sources unavailable" |

---

## 18. Out-of-Scope Cases

| OS-ID | Case | Reason | Handling |
|-------|------|--------|----------|
| OS-001 | Legal advice (application to specific facts) | Unauthorized practice of law | Disclaimer; escalate to attorney |
| OS-002 | Case outcome prediction | Speculative; not information retrieval | Decline; explain limitation |
| OS-003 | Novel legal argument generation | Creative legal work | Decline; provide authorities only |
| OS-004 | Non-public/private document access | Legal/ethical constraints | Link to official access procedure |
| OS-005 | Real-time regulatory filing | Transactional; not advisory | Link to official portal |
| OS-006 | Valuation of IP assets | Requires financial/legal expertise | Decline; provide relevant factors |
| OS-007 | Freedom-to-operate opinion | Legal opinion; high liability | Decline; provide search guidance |
| OS-008 | Litigation strategy | Attorney work product | Decline; provide case law retrieval |

---

## 19. Requirements Matrix (Traceability)

| Req ID | Category | Phase Dependencies | Testable | MVP |
|--------|----------|-------------------|----------|-----|
| FR-001 to FR-010 | Functional | Phases 2,3,4,6,10 | Yes | Yes |
| FR-101 to FR-110 | Cross-functional | Phases 2,9,10,11,12 | Yes | Partial |
| NFR-001 to NFR-020 | Non-functional | Phases 2,6,16,17,20,21 | Yes | Yes |
| P1-P7 | Personas | All phases | N/A | N/A |
| Journeys 4.1-4.6 | User journeys | Phases 2,8,9,10 | Yes (E2E tests) | Yes |
| QC-01 to QC-10 | Query categories | Phases 2,3,6 | Yes | Yes |
| Domains 6.1-6.2 | Legal domains | Phases 4,7,11 | N/A | Phased |
| Jurisdiction 7.1-7.3 | Jurisdiction | Phases 2,9,10 | Yes | Yes |
| Language 8.1-8.2 | Language | Phases 2,12 | Yes | Partial |
| Authority 9.1 | Source authority | Phases 4,6,11 | Yes | Yes |
| Safety 10.1-10.10 | Safety | Phases 10,11,19 | Yes | Yes |
| Privacy 11.1-11.5 | Privacy | Phases 14,16,19 | Yes | Yes |
| Audit 12.1-12.6 | Audit | Phases 2,10,16,21 | Yes | Yes |
| Explainability 13.1-13.5 | Explainability | Phases 9,10,21 | Yes | Partial |
| Citation 14.1-14.9 | Citations | Phases 4,5,10,11 | Yes | Yes |
| Versioning 15.1-15.7 | Versioning | Phases 4,7,15 | Yes | Partial |
| Scalability 16.1-16.6 | Scalability | Phases 6,7,15,20 | Load test | Phase 2 |
| Failure 17.1-17.15 | Failure modes | Phases 2,6,10,16,22 | Chaos test | Yes |
| Out-of-scope 18.1-18.8 | Out-of-scope | Phases 2,10 | N/A | Yes |

---

## 20. Open Research Questions (Phase 1)

| ORQ-ID | Question | Impact | Priority |
|--------|----------|--------|----------|
| ORQ-01 | What is the publicly accessible scope of TKDL? | Corpus coverage | P0 |
| ORQ-02 | Can India Code be legally scraped/API-accessed at scale? | Ingestion strategy | P0 |
| ORQ-03 | What is the optimal chunk size for Indian legal texts? | Retrieval quality | P1 |
| ORQ-04 | Does GraphRAG measurably improve legal QA over hybrid vector+lexical? | Architecture complexity | P1 |
| ORQ-05 | Which multilingual embedding model best preserves Indian legal terminology? | Multilingual quality | P1 |
| ORQ-06 | What confidence threshold balances abstention vs. helpfulness? | User trust | P1 |
| ORQ-07 | How to handle "derivative" definition in ABS for DSI? | Legal accuracy | P1 |
| ORQ-08 | Can formulation classification be fully deterministic? | Reliability | P1 |

---

## 21. Phase 1 Completion Checklist

- [x] Functional requirements documented (1.1, 1.2)
- [x] Non-functional requirements documented (2)
- [x] User personas defined (3)
- [x] User journeys documented (4)
- [x] Query categories defined (5)
- [x] Legal/regulatory domains enumerated (6)
- [x] Jurisdiction dimensions designed (7)
- [x] Language dimensions specified (8)
- [x] Source authority levels defined (9)
- [x] Safety requirements specified (10)
- [x] Privacy requirements specified (11)
- [x] Audit requirements specified (12)
- [x] Explainability requirements specified (13)
- [x] Citation requirements specified (14)
- [x] Update/versioning requirements specified (15)
- [x] Scalability requirements specified (16)
- [x] Failure modes analyzed (17)
- [x] Out-of-scope cases defined (18)
- [x] Requirements matrix with traceability (19)
- [x] Open research questions identified (20)

**Phase 1 Status: COMPLETE** ✅

---

## Next Phase: Phase 2 - System-Level Architecture

**Entry Criteria:** Phase 1 requirements signed off
**Exit Criteria:** Complete system architecture with component specifications, data flows, interfaces, and evaluation methods per component