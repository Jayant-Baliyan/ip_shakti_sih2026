# IP-SAKTI Sahayak - Corpus Source Investigation Report

**Date:** 2026-09-02  
**Status:** COMPLETE - Primary source investigation finished  
**Objective:** Investigate and document all authoritative public sources for corpus assembly

---

## Executive Summary

Investigated 5 primary authoritative sources as specified in the problem statement. All sources are publicly accessible with varying degrees of structured data availability. India Code has robots.txt restrictions requiring alternative access strategies. Other sources are openly accessible with well-structured content hierarchies.

---

## Source 1: India Code (indiacode.nic.in)

### Access Status
- **robots.txt**: Blocks all crawlers (`Disallow: /`)
- **Direct fetching**: Not possible via automated means
- **Legal status**: Official government source - terms of use must be reviewed
- **Alternative access**: Manual download, official API if available, or authorized bulk access

### Content Coverage
- Central Acts (Parliament legislation)
- Statutory Rules and Regulations
- Subordinate legislation
- Amendments with effective dates
- Legislative hierarchy: Act → Chapter → Section → Subsection → Clause

### Key Findings
1. **Structure**: Hierarchical legal document structure is well-defined
2. **Versions**: Multiple amendment versions available (critical for version tracking)
3. **Languages**: English and Hindi available
4. **Format**: HTML pages with PDF downloads
5. **Search**: Built-in search but no public API documented

### Ingestion Strategy
| Approach | Feasibility | Notes |
|----------|-------------|-------|
| Web scraping | ❌ Blocked | robots.txt prohibits |
| Manual PDF download | ✅ Possible | Labor-intensive but legal |
| Official API request | 🔍 Investigate | Contact Legislative Department |
| Bulk data agreement | 🔍 Investigate | Government data portal (data.gov.in) |
| India Code mobile app | 🔍 Investigate | May have API endpoints |

### Recommended Action
1. Request official bulk access from Legislative Department, Ministry of Law & Justice
2. Check data.gov.in for published datasets
3. Prepare manual ingestion pipeline for PDFs as fallback
4. Document all version metadata (amendment number, effective date, notification number)

---

## Source 2: IP India (ipindia.gov.in)

### Access Status
- **robots.txt**: Allows all crawlers (`Disallow:` empty)
- **Direct fetching**: ✅ Fully accessible
- **Content type**: HTML with embedded JavaScript, PDF downloads

### Content Coverage

#### Patents
| Resource | URL Pattern | Type |
|----------|-------------|------|
| Patents Act (all amendments) | `/resource/patents-resources-act` | LEGISLATION |
| Patents Rules | `/resource/patents-resources-rules` | RULE |
| Examination Guidelines | `/resource/patents-resources-guidelines` | GUIDELINE |
| Manuals | `/resource/patents-resources-manuals` | GUIDELINE |
| InPASS Public Search | `search.ipindia.gov.in` | PATENT_RECORD |
| Patent Journals | `search.ipindia.gov.in/IPOJournal/Journal/Patent` | REGISTRY_RECORD |

#### Designs
| Resource | URL Pattern | Type |
|----------|-------------|------|
| Designs Act | `/designs-resources-act` | LEGISLATION |
| Designs Rules | `/designs-resources-rules` | RULE |
| Design Search | `search.ipindia.gov.in/designsearch` | DESIGN_RECORD |
| Design e-Register | `search.ipindia.gov.in/DesignApplicationStatus/DesignEregister` | REGISTRY_RECORD |

#### Trade Marks
| Resource | URL Pattern | Type |
|----------|-------------|------|
| TM Act | `/trade-marks-resources-act` | LEGISLATION |
| TM Rules | `/trade-marks-resources-rules` | RULE |
| TM Manuals | `/trade-marks-resources-manual` | GUIDELINE |
| TM Guidelines | `/trade-marks-resources-guidelines` | GUIDELINE |
| TM Search | `ipindia.gov.in/trade-marks-before-you-apply-search-existing-trademarks` | TRADEMARK_RECORD |
| TM Journals | `search.ipindia.gov.in/IPOJournal/Journal/Trademark` | REGISTRY_RECORD |
| Well-known Marks | `/trade-marks-publications-list-of-well-known-trade-marks` | REGISTRY_RECORD |

#### Geographical Indications
| Resource | URL Pattern | Type |
|----------|-------------|------|
| GI Act | `/geographical-indications-resources-act` | LEGISLATION |
| GI Rules | `/geographical-indications-resources-rules` | RULE |
| GI Search | `search.ipindia.gov.in/GIRPublicSearch` | GI_RECORD |
| Registered GIs (Part A) | `/geographical-indications-track-application-list-of-registered-gi` | GI_RECORD |
| Registered Users (Part B) | `/part-b-register-list-of-registered-authorised-users` | GI_RECORD |
| GI Journal | `search.ipindia.gov.in/IPOJournal/Journal/GIR` | REGISTRY_RECORD |

#### Copyright
| Resource | URL Pattern | Type |
|----------|-------------|------|
| Copyright Act | `/copyright-acts` | LEGISLATION |
| Copyright Rules | `/copyright-rules` | RULE |
| Copyright Search | `copyright.gov.in/SearchRoc.aspx` | REGISTRY_RECORD |
| Copyright Journals | `copyright.gov.in/CopyrightJournal.aspx` | REGISTRY_RECORD |

#### SICLDR (Semiconductor Integrated Circuits Layout-Design Registry)
| Resource | URL Pattern | Type |
|----------|-------------|------|
| Act & Rules | `/sicldr-resources-act-rules` | LEGISLATION, RULE |
| Forms | `/sicldr-resources-forms` | REGULATION |

### Key Findings
1. **Acts available as PDFs** with version dates (e.g., "incorporating all amendments till 01-08-2024")
2. **Multiple amendment versions** preserved (1999, 2002, 2005, 2021, 2023, 2024)
3. **Hindi versions available** for major Acts
4. **Registry records** (InPASS, TMR, Design, GI) are searchable but require JavaScript
5. **Journals** published regularly with application/grant data
6. **Examination guidelines** and **manuals** provide interpretive guidance (Tier 2 authority)

### Ingestion Strategy
| Component | Method | Priority |
|-----------|--------|----------|
| Acts & Rules (PDF) | Direct PDF download + text extraction | P0 |
| Guidelines & Manuals (PDF/HTML) | HTML parsing + PDF extraction | P0 |
| Registry records (InPASS, TMR, etc.) | API investigation → scraping fallback | P1 |
| Journals | HTML parsing of journal pages | P1 |
| Search interfaces | Selenium/Playwright for JS-rendered content | P2 |

### Version Tracking
- Each Act PDF has: publish date, version description, language
- Amendment Acts are separate documents with own dates
- Must construct version chain: Original Act → Amendment 1 → Amendment 2 → Current Consolidated

---

## Source 3: National Biodiversity Authority (nbaindia.org)

### Access Status
- **robots.txt**: Returns HTML homepage (no standard robots.txt)
- **Direct fetching**: ✅ Accessible but Drupal-based with JavaScript
- **Content type**: HTML (Drupal CMS), PDF downloads

### Content Coverage

#### Core Legal Documents
| Document | URL | Type |
|----------|-----|------|
| Biological Diversity Act, 2002 | `/acts-and-rules/acts` | LEGISLATION |
| Biological Diversity Rules, 2004 | `/acts-and-rules/rules` | RULE |
| ABS Regulations, 2014 | `/acts-and-rules/rules` | REGULATION |
| State Biodiversity Rules | `/acts-and-rules/state-biodiversity-rules` | RULE (State-level) |
| Notifications & Guidelines | `/public-information/notification-guidelines` | NOTIFICATION, GUIDELINE |

#### ABS-Specific Resources
| Resource | URL | Type |
|----------|-----|------|
| ABS Application Process | `/application-form/Process` | REGULATION |
| Forms & Fees (Form I-IV) | `/application-form/form-application-fee` | REGULATION |
| ABS Agreements | `/content/23/1/1/absagreement.html` | REGISTRY_RECORD |
| Model Agreements | Various PDFs | REGULATION |
| Guidelines - Access to Biological Resources | `/content/22/1/1/guidelines.html` | GUIDELINE |
| Guidelines - Associated Traditional Knowledge | `/content/22/1/1/guidelines.html` | GUIDELINE |
| Guidelines - Fair & Equitable Sharing | `/content/22/1/1/guidelines.html` | GUIDELINE |

#### Operational Data
| Data | Status | Notes |
|------|--------|-------|
| ABS e-filing Statistics | Public dashboard | 12,248 applications received (as of Aug 2026) |
| BHS (Biodiversity Heritage Sites) | 57 sites | `/public-information/bhs-site-page` |
| BMCs (Biodiversity Management Committees) | 276,653 | `/sbbs/bmc-details-page` |
| PBRs (People's Biodiversity Registers) | 272,648 | `/public-information/pbr` |
| Case Studies | Published | `/content/25/1/1/casestudies.html` |

#### Key PDFs Identified
1. **Classification of biological resources, Derivatives and VAPs** (343.85 KB) - Critical for formulation classification
2. **Submission of Declaration (Form-10)** for foreign biological resources (452.22 KB)
3. **Procedure for Red Sanders approval** (205.34 KB)
4. **Internship programme, holiday lists, notices** - Supplementary

### Key Findings
1. **Drupal CMS** - content rendered server-side but navigation is JavaScript-heavy
2. **Acts/Rules pages** appear to list documents but may require clicking to PDFs
3. **State Biodiversity Rules** - critical for federal jurisdiction handling
4. **ABS Forms I-IV** - structured procedural data
5. **VAPs (Value Added Products) classification** - directly relevant to formulation classification
6. **BMC/PBR/BHS statistics** - registry-style data

### Ingestion Strategy
| Component | Method | Priority |
|-----------|--------|----------|
| Acts & Rules PDFs | Direct PDF download | P0 |
| Notifications & Guidelines | HTML parsing + PDF extraction | P0 |
| ABS Forms & Process | HTML parsing | P0 |
| VAPs Classification PDF | PDF extraction (critical for formulation) | P0 |
| State Biodiversity Rules | Iterate state pages | P1 |
| ABS Agreements/Case Studies | HTML + PDF | P2 |
| Operational Statistics | API/dashboard scraping | P3 |

---

## Source 4: Traditional Knowledge Digital Library (tkdl.res.in)

### Access Status
- **Public access**: ❌ **RESTRICTED** - Only overview pages accessible
- **Full database**: Requires authorized access agreement
- **Patent offices**: Formal access agreement required
- **Researchers**: Case-by-case basis
- **General public**: Only overview information

### Publicly Accessible Content
| Page | URL | Content |
|------|-----|---------|
| Home | `/tkdl/langdefault/common/Home.asp` | Overview |
| About | `/tkdl/langdefault/common/Aboutus.asp` | Mission, structure |
| Objectives | `/tkdl/langdefault/common/Objective.asp` | Prevent misappropriation |
| Coverage | `/tkdl/langdefault/common/Coverage.asp` | Systems covered |
| Achievements | `/tkdl.langdefault/common/Achievements.asp` | Patent revocations |
| Publications | `/tkdl/langdefault/common/Publications.asp` | Research papers |
| Patents | `/tkdl/langdefault/common/Patents.asp` | Revoked patents list |
| FAQ | `/tkdl/langdefault/common/FAQ.asp` | Access info |

### Key Information from Public Pages
- **Collaborative project**: CSIR + Ministry of AYUSH
- **Purpose**: Prevent misappropriation at international patent offices
- **Languages**: English, German, French, Japanese, Spanish
- **Systems covered**: Ayurveda, Unani, Siddha, Yoga
- **Format**: Ancient texts converted to patent-compatible format
- **Access model**: Patent offices under agreements; limited public access

### Ingestion Strategy
| Approach | Status | Action |
|----------|--------|--------|
| Public overview pages | ✅ Accessible | Ingest for context/metadata |
| Full TKDL database | ❌ Restricted | **Do not attempt unauthorized access** |
| Patent revocation list | ✅ Public | Ingest as CASE_LAW/PATENT_RECORD |
| Publications list | ✅ Public | Ingest as ACADEMIC |
| Official access request | 🔍 Required | Contact TKDL for research access |

### Critical Decision
**Do not scrape or attempt unauthorized access to TKDL full database.** Design corpus architecture to:
1. Use publicly accessible overview + revocation data
2. Link to official TKDL as external authoritative source
3. Accept that TKDL prior-art searches require official access
4. Clearly communicate this limitation to users

---

## Source 5: International Treaties (CBD, WIPO, WTO)

### Access Status
All treaty texts are publicly available from official depositories.

### CBD / Nagoya Protocol (cbd.int)
| Resource | URL | Type |
|----------|-----|------|
| Nagoya Protocol Text | `/abs/text/` | TREATY |
| COP-MOP Decisions | `/decisions/np-mop` | REGULATION |
| ABS Clearing-House | `absch.cbd.int` | REGISTRY_RECORD |
| Country Profiles | `absch.cbd.int/search/countries` | REGULATION |
| Bonn Guidelines | `/abs/bonn/` | GUIDELINE |
| Notifications | `/abs/notifications/` | NOTIFICATION |

### WIPO Treaties
| Treaty | Source | Type |
|--------|--------|------|
| PCT | wipo.int/pct | TREATY, REGULATION |
| Madrid | wipo.int/madrid | TREATY, REGULATION |
| Hague | wipo.int/hague | TREATY, REGULATION |
| Budapest | wipo.int/budapest | TREATY, REGULATION |
| GRATK (2024) | wipo.int/gratk | TREATY |

### WTO
| Resource | Source | Type |
|----------|--------|------|
| TRIPS Agreement | wto.org | TREATY |
| Dispute Settlement Reports | wto.org | CASE_LAW |

---

## Source 6: FSSAI / Ayurveda-Aahar (fssai.gov.in)

### Access Status
- **JavaScript-heavy** - requires translator widget
- **Content**: Act, Regulations, Notifications available but need rendering

### Key Documents Needed
| Document | Type | Priority |
|----------|------|----------|
| FSS Act 2006 | LEGISLATION | P0 |
| Ayurveda-Aahar Regulations 2022 | REGULATION | P0 |
| Food Safety Standards Regulations | REGULATION | P1 |
| Labeling Regulations | REGULATION | P1 |
| Nutraceutical Regulations | REGULATION | P1 |

### Ingestion Strategy
- Use headless browser (Playwright) for JavaScript-rendered content
- Target PDF downloads where available
- Priority: Ayurveda-Aahar Regulations (directly relevant to formulation classification)

---

## Source 7: AYUSH Ministry (ayush.gov.in)

### Access Status
- Public website with regulations, guidelines, standards

### Key Documents Needed
| Document | Type | Priority |
|----------|------|----------|
| NCISM Act 2020 | LEGISLATION | P1 |
| NCH Act 2020 | LEGISLATION | P1 |
| ASU Drugs Rules | RULE | P0 |
| Pharmacopoeia Standards | REGULATION | P1 |
| AYUSH Guidelines | GUIDELINE | P1 |

---

## Consolidated Source Inventory

### Tier 1 - Official Primary Law (Authority Weight: 1.0)
| Source | Jurisdiction | Doc Types | Access | Status |
|--------|-------------|-----------|--------|--------|
| India Code | India (Central) | LEGISLATION, RULE | Restricted (robots) | 🔍 Need official access |
| IP India Acts | India | LEGISLATION, RULE | ✅ Open | ✅ Ready |
| NBA Acts/Rules | India | LEGISLATION, RULE, REGULATION | ✅ Open | ✅ Ready |
| CBD/Nagoya | International | TREATY, REGULATION | ✅ Open | ✅ Ready |
| WIPO Treaties | International | TREATY, REGULATION | ✅ Open | ✅ Ready |
| WTO TRIPS | International | TREATY | ✅ Open | ✅ Ready |
| FSSAI Act/Regs | India | LEGISLATION, REGULATION | 🔍 JS-heavy | ⚠️ Needs rendering |
| AYUSH Acts | India | LEGISLATION, RULE | ✅ Open | ⏳ Pending |

### Tier 2 - Official Secondary (Authority Weight: 0.8)
| Source | Jurisdiction | Doc Types | Access | Status |
|--------|-------------|-----------|--------|--------|
| IP India Guidelines/Manuals | India | GUIDELINE | ✅ Open | ✅ Ready |
| NBA Guidelines/Notifications | India | GUIDELINE, NOTIFICATION | ✅ Open | ✅ Ready |
| Patent/TM/Design/GI Journals | India | REGISTRY_RECORD | ✅ Open | ✅ Ready |
| ABS Clearing-House | International | REGISTRY_RECORD | ✅ Open | ✅ Ready |
| Examination Guidelines | India | GUIDELINE | ✅ Open | ✅ Ready |
| FSSAI Notifications | India | NOTIFICATION | 🔍 JS-heavy | ⚠️ Needs rendering |
| AYUSH Guidelines | India | GUIDELINE | ✅ Open | ⏳ Pending |

### Tier 3 - Registry Records (Authority Weight: 0.9 for factual data)
| Source | Record Types | Access | Status |
|--------|--------------|--------|--------|
| InPASS (Patents) | PATENT_RECORD | JS search | 🔍 Needs Playwright |
| TMR (Trademarks) | TRADEMARK_RECORD | JS search | 🔍 Needs Playwright |
| Design Registry | DESIGN_RECORD | JS search | 🔍 Needs Playwright |
| GI Registry | GI_RECORD | JS search | 🔍 Needs Playwright |
| Copyright Registry | REGISTRY_RECORD | ASP.NET | 🔍 Needs Playwright |
| ABS e-filing | REGISTRY_RECORD | JS portal | 🔍 Needs Playwright |

### Tier 4 - Traditional Knowledge (Authority Weight: 1.0 but restricted)
| Source | Record Types | Access | Status |
|--------|--------------|--------|--------|
| TKDL | TK_RESOURCE | Restricted | ❌ No direct access |
| Public revocations | TK_RESOURCE/CASE_LAW | ✅ Open | ✅ Ready |

### Tier 5 - Academic/Supplementary (Authority Weight: 0.5)
- Peer-reviewed IP/TK/ABS literature
- Law review articles
- WIPO publications
- **Ingestion**: Phase 3+ (after core corpus established)

---

## Ingestion Priority Phases

### Phase 1 (MVP - Hackathon Core)
1. **IP India Acts & Rules** (Patents, TM, Designs, GI, Copyright, SICLDR) - PDFs available
2. **NBA Acts & Rules** (BD Act 2002, Rules 2004, ABS Rules 2014) - PDFs available
3. **NBA Guidelines & Notifications** - HTML + PDF
4. **CBD / Nagoya Protocol** - Treaty texts + COP decisions
5. **WIPO Treaty texts** - PCT, Madrid, Hague, Budapest
6. **Public TKDL data** - Overview, revocations, achievements
7. **VAPs Classification PDF** (NBA) - Critical for formulation classification

### Phase 2 (Post-MVP)
1. **India Code** - Via official access or manual PDF collection
2. **FSSAI / Ayurveda-Aahar** - Playwright rendering
3. **AYUSH Ministry** - Acts, Rules, Guidelines
4. **Registry Records** - InPASS, TMR, Design, GI, Copyright, ABS (Playwright)
4. **State Biodiversity Rules** - All states
5. **Case Law** - Indian Kanoon (if accessible), Supreme Court/HC websites

### Phase 3 (Research/Enhancement)
1. **Academic literature** - Semantic Scholar, PubMed, law journals
2. **WIPO publications** - Guides, studies
3. **International case law** - EPO, USPTO, CJEU, etc.
4. **Full TKDL** - If official access granted

---

## Technical Ingestion Requirements

### Document Metadata Schema (per source)
```json
{
  "source_id": "uuid",
  "source_name": "India Code / IP India / NBA / CBD / WIPO / FSSAI / AYUSH / TKDL",
  "source_type": "LEGISLATION|RULE|REGULATION|NOTIFICATION|GUIDELINE|TREATY|REGISTRY_RECORD|PATENT_RECORD|TRADEMARK_RECORD|GI_RECORD|DESIGN_RECORD|TK_RESOURCE|CASE_LAW|ACADEMIC|SECONDARY",
  "authority_tier": 1|2|3|4,
  "jurisdiction": "India|International|India-State-{state}",
  "title": "Official document title",
  "document_id": "stable identifier (Act number, Rule number, Treaty article)",
  "version": "version string (e.g., '2024-08-01 consolidated', 'Amendment 2023')",
  "publication_date": "ISO 8601",
  "effective_date": "ISO 8601",
  "superseded_date": "ISO 8601 or null",
  "amendment_status": "original|amended|consolidated|repealed",
  "language": "en|hi|ta|te|bn|mr|gu|kn|ml|pa|ur|fr|es|ar|zh|ru",
  "canonical_url": "official stable URL",
  "retrieval_timestamp": "ISO 8601",
  "content_hash": "SHA-256 of content",
  "access_level": "public|restricted|authorized",
  "provenance": "direct_download|api|manual|playwright_rendered",
  "parent_document": "document_id of parent (for amendments)",
  "section_identifiers": ["Section 3", "Section 3(d)", "Rule 158-B", ...]
}
```

### Version Handling Protocol
1. **Never overwrite** - Each version gets new document_id with version suffix
2. **Supersession links** - `supersedes` and `superseded_by` relationships
3. **Effective date validation** - Only retrieve versions effective at query time
4. **Change detection** - Periodic re-fetch; compare content_hash
5. **Amendment tracking** - Parse amendment Acts to link to amended sections

### Chunking Requirements (for Phase 5)
- Preserve legal hierarchy: Act → Chapter → Part → Section → Subsection → Clause → Subclause
- Each chunk must map to: `document_id + section_path + clause_numbers`
- Citations must resolve to: exact section/article/clause with version

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| India Code access denied | High - missing core legislation | Medium | Manual PDF collection; data.gov.in; official request |
| TKDL inaccessible | High - no prior-art data | High | Use public revocations only; clear user communication |
| Registry records need JS | Medium - no structured search | High | Playwright/Selenium automation |
| FSSAI JS rendering | Medium - missing food/Ayurveda-Aahar | Medium | Playwright rendering pipeline |
| Source changes break ingestion | Medium - stale data | Medium | Content hashing; scheduled re-validation; monitoring |
| Version confusion | High - wrong law applied | Medium | Strict version metadata; effective date filtering |

---

## Next Steps

1. ✅ **Phase 1 Requirements Engineering** - COMPLETE
2. ⏳ **Update plan.md** with this investigation
3. 🔄 **Phase 2 System-Level Architecture** - Design complete system architecture
4. 📋 **Phase 3 RAG Architecture** - Deep retrieval design
5. 📄 **Phase 4 Legal Document Ingestion** - Detailed ingestion pipeline design
6. ✂️ **Phase 5 Chunking Strategy** - Legal-specific chunking design
7. 🔍 **Phase 6 Retrieval Engine** - Hybrid retrieval design
8. 🕸️ **Phase 7 Knowledge Graph** - Entity/relationship design
9. 💊 **Phase 8 Formulation Classification** - Rule engine + LLM design
10. ⚖️ **Phase 9 Jurisdiction Engine** - Explicit jurisdiction handling
11. 📎 **Phase 10 Citation-First Generation** - Grounded generation design
... (continue through Phase 26)

---

## Appendix: Source URLs Reference

### Primary Ingestion URLs (Phase 1)
```
IP India Patents Act:        https://ipindia.gov.in/resource/patents-resources-act
IP India Patents Rules:      https://ipindia.gov.in/resource/patents-resources-rules
IP India Patents Guidelines: https://ipindia.gov.in/resource/patents-resources-guidelines
IP India Patents Manuals:    https://ipindia.gov.in/resource/patents-resources-manuals
IP India Designs Act:        https://ipindia.gov.in/designs-resources-act
IP India Designs Rules:      https://ipindia.gov.in/designs-resources-rules
IP India TM Act:             https://ipindia.gov.in/trade-marks-resources-act
IP India TM Rules:           https://ipindia.gov.in/trade-marks-resources-rules
IP India TM Manuals:         https://ipindia.gov.in/trade-marks-resources-manual
IP India TM Guidelines:      https://ipindia.gov.in/trade-marks-resources-guidelines
IP India GI Act:             https://ipindia.gov.in/geographical-indications-resources-act
IP India GI Rules:           https://ipindia.gov.in/geographical-indications-resources-rules
IP India GI Manuals:         https://ipindia.gov.in/geographical-indications-resources-manual
IP India GI Guidelines:      https://ipindia.gov.in/geographical-indications-resources-guidelines
IP India Copyright Act:      https://ipindia.gov.in/copyright-acts
IP India Copyright Rules:    https://ipindia.gov.in/copyright-rules
IP India SICLDR:             https://ipindia.gov.in/sicldr-resources-act-rules

NBA Acts:                    https://nbaindia.org/acts-and-rules/acts
NBA Rules:                   https://nbaindia.org/acts-and-rules/rules
NBA State Rules:             https://nbaindia.org/acts-and-rules/state-biodiversity-rules
NBA Notifications:           https://nbaindia.org/public-information/notification-guidelines
NBA ABS Forms:               https://nbaindia.org/application-form/form-application-fee
NBA ABS Process:             https://nbaindia.org/application-form/Process
NBA VAPs Classification:     https://nbaindia.org/sites/default/files/2026-08/vaps.pdf
NBA Form-10:                 https://nbaindia.org/sites/default/files/2026-04/sub_form10.pdf

CBD Nagoya Protocol:         https://www.cbd.int/abs/text/
CBD ABS Clearing-House:      https://absch.cbd.int/
CBD Bonn Guidelines:         https://www.cbd.int/abs/bonn/
CBD Notifications:           https://www.cbd.int/abs/notifications/

WIPO PCT:                    https://www.wipo.int/pct/en/
WIPO Madrid:                 https://www.wipo.int/madrid/en/
WIPO Hague:                  https://www.wipo.int/hague/en/
WIPO Budapest:               https://www.wipo.int/budapest/en/
WIPO GRATK:                  https://www.wipo.int/gratk/en/

TKDL Public:                 https://tkdl.res.in/tkdl/langdefault/common/
TKDL Patents (revocations):  https://tkdl.res.in/tkdl/langdefault/common/Patents.asp
```

---

*End of Corpus Source Investigation Report*