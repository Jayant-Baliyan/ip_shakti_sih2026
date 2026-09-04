# Phase 9: Jurisdiction Engine Architecture

## Overview

This document designs the **Jurisdiction Engine** for IP-SAKTI. The engine explicitly determines applicable jurisdiction(s), regulatory authority/regime, and legal provisions for every query. It enforces **hard isolation** between jurisdictions—never allowing silent mixing of Indian law, foreign law, and international treaties.

**Key Principle**: Jurisdiction is not inferred implicitly. Every query, retrieval, and answer must have an explicit, auditable jurisdiction context. Multi-jurisdiction queries are handled with explicit segmentation, not blending.

---

## 1. Requirements

### 1.1 Functional Requirements

| Requirement | Description |
|------------|-------------|
| **FR-JE-01** | Maintain authoritative taxonomy of jurisdictions (India Central, India States, EU, USA, Japan, International, PCT, WIPO, WTO, etc.) |
| **FR-JE-02** | Determine applicable jurisdiction(s) from query, formulation classification, user context |
| **FR-JE-03** | Map jurisdiction → regulatory authority → applicable legislation/regulations |
| **FR-JE-04** | Handle temporal validity: amendments, repeals, prospective/retrospective application |
| **FR-JE-05** | Resolve conflicts: lex posterior, lex specialis, federal vs state, treaty vs domestic |
| **FR-JE-06** | Enforce hard isolation: separate retrieval indices, separate answer segments per jurisdiction |
| **FR-JE-07** | Explicit multi-jurisdiction handling: segmented answers with clear attribution |
| **FR-JE-08** | Track jurisdiction provenance for every retrieved chunk and generated claim |
| **FR-JE-09** | Support jurisdiction-specific retrieval filters (metadata pre-filter) |
| **FR-JE-10** | Version jurisdiction rules with amendment tracking |

### 1.2 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| **NFR-JE-01** | Jurisdiction determination latency: < 50ms (p95) |
| **NFR-JE-02** | Zero silent jurisdiction mixing in retrieval or generation |
| **NFR-JE-03** | 100% traceability: every chunk/claim → jurisdiction |
| **NFR-JE-04** | Conflict resolution accuracy: > 95% on test cases |

---

## 2. Jurisdiction Taxonomy

### 2.1 Jurisdiction Hierarchy

```
JURISDICTION
├── INDIA
│   ├── INDIA_CENTRAL (Parliament, Central Govt)
│   │   ├── Acts of Parliament
│   │   ├── Central Rules/Regulations
│   │   ├── Central Guidelines/Notifications
│   │   └── Supreme Court / High Court (federal questions)
│   ├── INDIA_STATE (State Legislatures)
│   │   ├── State Acts (e.g., State Biodiversity Rules)
│   │   ├── State Rules/Regulations
│   │   └── High Courts (state matters)
│   └── INDIA_UT (Union Territories)
├── INTERNATIONAL_TREATY
│   ├── CBD (Convention on Biological Diversity)
│   ├── NAGOYA (Nagoya Protocol)
│   ├── TRIPS (WTO Agreement)
│   ├── PCT (Patent Cooperation Treaty)
│   ├── MADRID (Madrid Protocol)
│   ├── HAGUE (Hague Agreement)
│   ├── BUDAPEST (Budapest Treaty)
│   ├── GRATK (GRATK Treaty 2024)
│   ├── PARIS (Paris Convention)
│   └── BERNE (Berne Convention)
├── REGIONAL
│   ├── EU (EU Regulations, Directives, CJEU)
│   ├── ARIPO (African Regional IP Organization)
│   ├── OAPI (African Intellectual Property Organization)
│   └── EAPO (Eurasian Patent Organization)
├── NATIONAL_FOREIGN
│   ├── USA (USC, CFR, USPTO, Federal Courts)
│   ├── JAPAN (Japanese Patent Act, JPO, Courts)
│   ├── UK (UK Patents Act, UKIPO, Courts)
│   ├── CANADA (Canadian Patent Act, CIPO)
│   ├── AUSTRALIA (Australian Patents Act, IP Australia)
│   ├── SINGAPORE (Singapore Patents Act, IPOS)
│   └── OTHER (extensible)
├── INTERNATIONAL_ORG
│   ├── WIPO (WIPO-administered treaties, Standing Committees)
│   ├── WTO (TRIPS, Dispute Settlement)
│   ├── WHO (International Health Regulations)
│   └── FAO (Plant Treaty, Codex Alimentarius)
└── CUSTOM_JURISDICTION
    └── User-defined (for research/comparison)
```

### 2.2 Jurisdiction Metadata Schema

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
from datetime import date

class JurisdictionType(str, Enum):
    NATIONAL = "national"
    STATE_PROVINCIAL = "state_provincial"
    INTERNATIONAL_TREATY = "international_treaty"
    REGIONAL = "regional"
    INTERNATIONAL_ORG = "international_org"
    CUSTOM = "custom"

class JurisdictionLevel(str, Enum):
    SUPRANATIONAL = "supranational"    # EU, WIPO treaties
    FEDERAL_CENTRAL = "federal_central"  # India Central, USA Federal
    STATE_PROVINCIAL = "state_provincial"  # India States, US States
    LOCAL = "local"

@dataclass
class Jurisdiction:
    jurisdiction_id: str                    # e.g., "INDIA_CENTRAL", "EU", "USA", "CBD"
    display_name: str                       # "India (Central)", "European Union"
    type: JurisdictionType
    level: JurisdictionLevel
    parent_jurisdiction: Optional[str] = None  # e.g., INDIA_STATE -> INDIA
    child_jurisdictions: List[str] = field(default_factory=list)
    
    # Authority mapping
    legislative_authority: str              # "Parliament of India", "European Parliament"
    executive_authority: str                # "Central Government", "European Commission"
    judicial_authority: List[str] = field(default_factory=list)  # ["Supreme Court of India", "High Courts"]
    regulatory_authorities: List[str] = field(default_factory=list)  # ["CDSCO", "FSSAI", "NBA", "IP India"]
    
    # Applicable law categories
    applicable_act_types: List[str] = field(default_factory=list)
    applicable_regulations: List[str] = field(default_factory=list)
    
    # Temporal
    established_date: Optional[date] = None
    status: str = "ACTIVE"  # ACTIVE, SUPERSEDED, HISTORICAL
    
    # Metadata
    iso_code: Optional[str] = None          # "IN", "US", "JP", "EU"
    wipo_code: Optional[str] = None         # "IN", "US", "JP", "EP", "WO"
    wto_member: bool = False
    pct_member: bool = False
    madrid_member: bool = False
    hague_member: bool = False
    
    # For treaties
    depositary: Optional[str] = None
    entry_into_force: Optional[date] = None
    parties: List[str] = field(default_factory=list)  # Jurisdiction IDs of parties
```

### 2.3 Pre-populated Jurisdiction Registry

```python
JURISDICTION_REGISTRY = {
    "INDIA_CENTRAL": Jurisdiction(
        jurisdiction_id="INDIA_CENTRAL",
        display_name="India (Central Government)",
        type=JurisdictionType.NATIONAL,
        level=JurisdictionLevel.FEDERAL_CENTRAL,
        legislative_authority="Parliament of India",
        executive_authority="Central Government",
        judicial_authority=["Supreme Court of India", "High Courts of India"],
        regulatory_authorities=["CDSCO", "FSSAI", "NBA", "IP India", "AYUSH Ministry", "MoEFCC"],
        applicable_act_types=["ACT", "AMENDMENT_ACT", "ORDINANCE"],
        applicable_regulations=["RULE", "REGULATION", "NOTIFICATION", "GUIDELINE", "ORDER"],
        iso_code="IN",
        wipo_code="IN",
        wto_member=True,
        pct_member=True,
        madrid_member=True,
        hague_member=True,
    ),
    
    "INDIA_STATE": Jurisdiction(
        jurisdiction_id="INDIA_STATE",
        display_name="India (State Governments)",
        type=JurisdictionType.STATE_PROVINCIAL,
        level=JurisdictionLevel.STATE_PROVINCIAL,
        parent_jurisdiction="INDIA_CENTRAL",
        legislative_authority="State Legislatures",
        executive_authority="State Governments",
        judicial_authority=["High Courts of respective states"],
        regulatory_authorities=["State Licensing Authorities (AYUSH)", "State Biodiversity Boards", "State Drug Controllers"],
        applicable_act_types=["STATE_ACT", "STATE_AMENDMENT"],
        applicable_regulations=["STATE_RULE", "STATE_NOTIFICATION", "STATE_ORDER"],
        iso_code="IN",
    ),
    
    "CBD": Jurisdiction(
        jurisdiction_id="CBD",
        display_name="Convention on Biological Diversity",
        type=JurisdictionType.INTERNATIONAL_TREATY,
        level=JurisdictionLevel.SUPRANATIONAL,
        legislative_authority="Conference of Parties (COP)",
        executive_authority="CBD Secretariat",
        judicial_authority=[],
        regulatory_authorities=["National Focal Points", "ABS Clearing-House"],
        applicable_act_types=["TREATY", "PROTOCOL", "COP_DECISION"],
        applicable_regulations=["GUIDELINE", "NOTIFICATION"],
        depositary="UN Secretary-General",
        entry_into_force=date(1993, 12, 29),
        parties=["INDIA_CENTRAL", "EU", "USA", "..."],  # 196 parties
    ),
    
    "NAGOYA": Jurisdiction(
        jurisdiction_id="NAGOYA",
        display_name="Nagoya Protocol on ABS",
        type=JurisdictionType.INTERNATIONAL_TREATY,
        level=JurisdictionLevel.SUPRANATIONAL,
        parent_jurisdiction="CBD",
        legislative_authority="COP-MOP",
        executive_authority="CBD Secretariat",
        regulatory_authorities=["National Focal Points", "ABS Clearing-House", "Competent National Authorities"],
        applicable_act_types=["PROTOCOL", "COP_MOP_DECISION"],
        applicable_regulations=["GUIDELINE", "MODEL_CONTRACTUAL_CLAUSES"],
        depositary="UN Secretary-General",
        entry_into_force=date(2014, 10, 12),
        parties=["INDIA_CENTRAL", "EU", "..."],  # 138 parties
    ),
    
    "TRIPS": Jurisdiction(
        jurisdiction_id="TRIPS",
        display_name="WTO TRIPS Agreement",
        type=JurisdictionType.INTERNATIONAL_TREATY,
        level=JurisdictionLevel.SUPRANATIONAL,
        legislative_authority="WTO Ministerial Conference / General Council",
        executive_authority="WTO Secretariat",
        judicial_authority=["WTO Dispute Settlement Body", "Appellate Body"],
        regulatory_authorities=["National IP Offices"],
        applicable_act_types=["AGREEMENT", "DECISION", "DECLARATION"],
        applicable_regulations=["GUIDELINES"],
        wto_member=True,
    ),
    
    "PCT": Jurisdiction(
        jurisdiction_id="PCT",
        display_name="Patent Cooperation Treaty",
        type=JurisdictionType.INTERNATIONAL_TREATY,
        level=JurisdictionLevel.SUPRANATIONAL,
        legislative_authority="PCT Assembly",
        executive_authority="WIPO International Bureau",
        judicial_authority=[],
        regulatory_authorities=["Receiving Offices", "International Searching Authorities", "International Preliminary Examining Authorities"],
        applicable_act_types=["TREATY", "REGULATIONS", "ADMINISTRATIVE_INSTRUCTIONS"],
        applicable_regulations=["GUIDELINES", "CIRCULARS"],
        wipo_code="WO",
        pct_member=True,
    ),
    
    "USA": Jurisdiction(
        jurisdiction_id="USA",
        display_name="United States of America",
        type=JurisdictionType.NATIONAL,
        level=JurisdictionLevel.FEDERAL_CENTRAL,
        legislative_authority="US Congress",
        executive_authority="US Federal Government",
        judicial_authority=["US Supreme Court", "US Courts of Appeals", "US District Courts", "PTAB"],
        regulatory_authorities=["USPTO", "FDA", "USDA", "FTC"],
        applicable_act_types=["USC", "PUBLIC_LAW"],
        applicable_regulations=["CFR", "FEDERAL_REGISTER", "USPTO_RULES", "FDA_GUIDANCE"],
        iso_code="US",
        wipo_code="US",
        wto_member=True,
        pct_member=True,
        madrid_member=True,
        hague_member=True,
    ),
    
    "EU": Jurisdiction(
        jurisdiction_id="EU",
        display_name="European Union",
        type=JurisdictionType.REGIONAL,
        level=JurisdictionLevel.SUPRANATIONAL,
        legislative_authority="European Parliament + Council of EU",
        executive_authority="European Commission",
        judicial_authority=["CJEU", "General Court"],
        regulatory_authorities=["EUIPO", "EPO", "EMA", "EFSA"],
        applicable_act_types=["REGULATION", "DIRECTIVE", "DECISION", "RECOMMENDATION"],
        applicable_regulations=["IMPLEMENTING_ACT", "DELEGATED_ACT", "GUIDELINE"],
        iso_code="EU",
        wipo_code="EP",
        wto_member=True,
        pct_member=True,
        madrid_member=True,
        hague_member=True,
    ),
    
    "JAPAN": Jurisdiction(
        jurisdiction_id="JAPAN",
        display_name="Japan",
        type=JurisdictionType.NATIONAL,
        level=JurisdictionLevel.FEDERAL_CENTRAL,
        legislative_authority="National Diet",
        executive_authority="Cabinet of Japan",
        judicial_authority=["Supreme Court of Japan", "High Courts", "IP High Court"],
        regulatory_authorities=["JPO", "PMDA", "MHLW"],
        applicable_act_types=["ACT", "CABINET_ORDER"],
        applicable_regulations=["MINISTERIAL_ORDINANCE", "JPO_GUIDELINES", "PMDA_NOTIFICATIONS"],
        iso_code="JP",
        wipo_code="JP",
        wto_member=True,
        pct_member=True,
        madrid_member=True,
        hague_member=True,
    ),
}
```

---

## 3. Jurisdiction Determination

### 3.1 Input Signals

```python
@dataclass
class JurisdictionDeterminationInput:
    # From query
    query_text: str
    query_language: str
    explicit_jurisdiction_mentions: List[str]  # Extracted from query
    
    # From formulation classification (Phase 8)
    formulation_classification: Optional[ClassificationResult] = None
    
    # From user context
    user_location: Optional[str] = None        # User's country/state
    user_role: Optional[str] = None            # "attorney", "researcher", "startup", "regulator"
    target_markets: List[str] = field(default_factory=list)  # Export destinations
    
    # From conversation history
    previous_jurisdiction: Optional[str] = None
    conversation_context: Optional[str] = None
    
    # Explicit user override
    user_specified_jurisdiction: Optional[str] = None
```

### 3.2 Determination Algorithm

```python
class JurisdictionEngine:
    """
    Determines applicable jurisdiction(s) for a query.
    Returns ordered list with confidence scores.
    """
    
    def __init__(self, registry: JurisdictionRegistry, llm_client):
        self.registry = registry
        self.llm = llm_client
        self.deterministic_rules = self._load_deterministic_rules()
    
    def determine(self, input: JurisdictionDeterminationInput) -> JurisdictionDeterminationResult:
        # 1. Explicit user override (highest priority)
        if input.user_specified_jurisdiction:
            return self._create_result(
                jurisdictions=[input.user_specified_jurisdiction],
                confidence=1.0,
                method="USER_SPECIFIED",
                reasoning="User explicitly specified jurisdiction"
            )
        
        # 2. Formulation classification → regulatory regime mapping
        regime_jurisdictions = self._map_regime_to_jurisdiction(input.formulation_classification)
        
        # 3. Query-based signals
        query_jurisdictions = self._extract_from_query(input.query_text, input.query_language)
        
        # 4. User context signals
        context_jurisdictions = self._extract_from_context(input)
        
        # 5. Combine with weighted scoring
        scored = self._score_jurisdictions(
            regime_jurisdictions, query_jurisdictions, context_jurisdictions, input
        )
        
        # 6. Apply conflict resolution rules
        resolved = self._resolve_conflicts(scored, input)
        
        # 7. If ambiguous, use LLM for disambiguation
        if len(resolved) > 1 and self._is_ambiguous(resolved):
            llm_result = self._llm_disambiguate(input, resolved)
            return llm_result
        
        return self._create_result(
            jurisdictions=[j.jurisdiction_id for j in resolved],
            confidence=resolved[0].confidence if resolved else 0.0,
            method="DETERMINISTIC",
            reasoning=self._build_reasoning(resolved, input)
        )
    
    def _map_regime_to_jurisdiction(self, classification: Optional[ClassificationResult]) -> List[ScoredJurisdiction]:
        """Map formulation class to default jurisdiction(s)."""
        if not classification:
            return []
        
        regime_map = {
            FormulationClass.CLASSICAL_MEDICINE: ["INDIA_CENTRAL", "INDIA_STATE"],
            FormulationClass.GENERIC_MEDICINE: ["INDIA_CENTRAL"],
            FormulationClass.PATENT_PROPRIETARY_MEDICINE: ["INDIA_CENTRAL", "INDIA_STATE"],
            FormulationClass.NEW_DRUG: ["INDIA_CENTRAL"],
            FormulationClass.PHYTOPHARMACEUTICAL: ["INDIA_CENTRAL"],
            FormulationClass.AYURVEDA_AAHAR: ["INDIA_CENTRAL"],
            FormulationClass.NUTRACEUTICAL: ["INDIA_CENTRAL"],
            FormulationClass.COSMETIC: ["INDIA_CENTRAL", "INDIA_STATE"],
            FormulationClass.TK_FORMULATION: ["INDIA_CENTRAL", "CBD", "NAGOYA"],
        }
        
        jurisdictions = regime_map.get(classification.classification, ["INDIA_CENTRAL"])
        return [ScoredJurisdiction(j, 0.9, "FORMULATION_CLASS") for j in jurisdictions]
    
    def _extract_from_query(self, query: str, language: str) -> List[ScoredJurisdiction]:
        """Extract jurisdiction mentions from query text."""
        jurisdictions = []
        query_lower = query.lower()
        
        # Explicit jurisdiction keywords
        JURISDICTION_KEYWORDS = {
            "INDIA_CENTRAL": ["india", "indian", "central government", "parliament", "cdsco", "fssai", "nba", "ip india", "patents act", "trademarks act", "copyright act", "designs act", "biological diversity act", "drugs and cosmetics act", "fssai act", "ayush"],
            "INDIA_STATE": ["state government", "state rule", "state biodiversity board", "sla", "state licensing", "maharashtra", "karnataka", "tamil nadu", "gujarat", "kerala"],
            "CBD": ["cbd", "convention on biological diversity", "cop", "conference of parties"],
            "NAGOYA": ["nagoya", "nagoya protocol", "abs", "access and benefit sharing", "cop-mop"],
            "TRIPS": ["trips", "wto", "world trade organization", "trade-related aspects"],
            "PCT": ["pct", "patent cooperation treaty", "international application", "wipo", "isa", "ipea"],
            "MADRID": ["madrid", "madrid protocol", "international registration", "trademark international"],
            "HAGUE": ["hague", "hague agreement", "industrial design", "international design"],
            "USA": ["usa", "united states", "us ", "u.s.", "fda", "uspto", "usc", "cfr", "american"],
            "EU": ["eu", "european union", "europe", "ema", "euipo", "epo", "ce mark", "gdpr", "regulation (eu)"],
            "JAPAN": ["japan", "japanese", "jpo", "pmda", "mhlw", "japanese patent"],
        }
        
        for jid, keywords in JURISDICTION_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in query_lower:
                    score += 0.3
            if score > 0:
                jurisdictions.append(ScoredJurisdiction(jid, min(score, 1.0), "QUERY_KEYWORD"))
        
        return jurisdictions
    
    def _extract_from_context(self, input: JurisdictionDeterminationInput) -> List[ScoredJurisdiction]:
        jurisdictions = []
        
        # User location
        if input.user_location:
            loc_map = {
                "IN": "INDIA_CENTRAL", "IN-MH": "INDIA_STATE", "IN-KA": "INDIA_STATE",
                "US": "USA", "US-CA": "USA", "JP": "JAPAN", "DE": "EU", "FR": "EU"
            }
            if input.user_location in loc_map:
                jurisdictions.append(ScoredJurisdiction(loc_map[input.user_location], 0.5, "USER_LOCATION"))
        
        # Target markets (export)
        for market in input.target_markets:
            if market in ["USA", "US"]: jurisdictions.append(ScoredJurisdiction("USA", 0.7, "TARGET_MARKET"))
            elif market in ["EU", "EPO"]: jurisdictions.append(ScoredJurisdiction("EU", 0.7, "TARGET_MARKET"))
            elif market in ["JP", "JAPAN"]: jurisdictions.append(ScoredJurisdiction("JAPAN", 0.7, "TARGET_MARKET"))
            elif market in ["WO", "PCT"]: jurisdictions.append(ScoredJurisdiction("PCT", 0.8, "TARGET_MARKET"))
        
        # Previous jurisdiction (conversation continuity)
        if input.previous_jurisdiction:
            jurisdictions.append(ScoredJurisdiction(input.previous_jurisdiction, 0.4, "CONVERSATION_HISTORY"))
        
        return jurisdictions
    
    def _score_jurisdictions(self, *sources) -> List[ScoredJurisdiction]:
        """Combine and score jurisdictions from multiple sources."""
        combined = {}
        for source in sources:
            for sj in source:
                if sj.jurisdiction_id not in combined:
                    combined[sj.jurisdiction_id] = ScoredJurisdiction(sj.jurisdiction_id, 0.0, "")
                combined[sj.jurisdiction_id].confidence += sj.confidence
                combined[sj.jurisdiction_id].sources.append(sj.source)
        
        # Normalize and sort
        results = list(combined.values())
        for r in results:
            r.confidence = min(r.confidence, 1.0)
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def _resolve_conflicts(self, scored: List[ScoredJurisdiction], input: JurisdictionDeterminationInput) -> List[ScoredJurisdiction]:
        """Apply conflict resolution principles."""
        if len(scored) <= 1:
            return scored
        
        # Principle 1: Explicit > Implicit
        explicit = [s for s in scored if s.source in ["USER_SPECIFIED", "FORMULATION_CLASS"]]
        if explicit:
            return explicit[:1]
        
        # Principle 2: More specific jurisdiction wins (State > Central for state matters)
        # But Central > State for central legislation
        # This requires knowing the query intent - defer to LLM if complex
        
        # Principle 3: Treaty jurisdiction only if treaty-specific query
        treaty_jurisdictions = {"CBD", "NAGOYA", "TRIPS", "PCT", "MADRID", "HAGUE", "BUDAPEST", "GRATK", "PARIS", "BERNE"}
        has_treaty = any(s.jurisdiction_id in treaty_jurisdictions for s in scored)
        has_national = any(s.jurisdiction_id not in treaty_jurisdictions for s in scored)
        
        if has_treaty and has_national:
            # Check if query is about treaty implementation
            if self._is_treaty_implementation_query(input.query_text):
                # Keep both but separate
                return scored
            else:
                # Default to national unless treaty explicitly mentioned
                return [s for s in scored if s.jurisdiction_id not in treaty_jurisdictions] or scored[:1]
        
        return scored[:2]  # Top 2 for multi-jurisdiction handling
    
    def _is_treaty_implementation_query(self, query: str) -> bool:
        treaty_terms = ["implement", "treaty obligation", "article", "cop decision", "cop-mop", "nagoya", "cbd", "trips"]
        query_lower = query.lower()
        return any(term in query_lower for term in treaty_terms)
```

---

## 4. Authority & Regime Mapping

### 4.1 Jurisdiction → Authority → Law Mapping

```python
@dataclass
class RegulatoryRegime:
    jurisdiction_id: str
    authority: str                          # e.g., "CDSCO", "FSSAI", "NBA", "IP India"
    legislation: List[str]                  # Act IDs applicable
    regulations: List[str]                  # Rule/Regulation IDs applicable
    guidelines: List[str]                   # Guideline IDs applicable
    case_law_authority: List[str]           # Court IDs
    subject_matter: List[str]               # ["patent", "trademark", "ayurveda", "abs", "food", "cosmetic"]

REGULATORY_REGIMES = {
    "INDIA_CENTRAL": [
        RegulatoryRegime(
            jurisdiction_id="INDIA_CENTRAL",
            authority="CDSCO",
            legislation=["A1940-23", "A1954-16", "A1970-39", "A1999-47", "A2000-16", "A2001-53", "A2005-34"],
            regulations=["D&C_RULES_1945", "PATENT_RULES_2003", "TM_RULES_2017", "DESIGN_RULES_2001", "COPYRIGHT_RULES_2013"],
            guidelines=["CDSCO_PHYTO_2017", "CDSCO_CLINICAL_2019", "CDSCO_COSMETIC_2020"],
            case_law_authority=["SUPREME_COURT_INDIA", "HIGH_COURT_DELHI", "HIGH_COURT_MUMBAI", "IPAB"],
            subject_matter=["drug", "cosmetic", "clinical_trial", "phytopharmaceutical", "new_drug"]
        ),
        RegulatoryRegime(
            jurisdiction_id="INDIA_CENTRAL",
            authority="FSSAI",
            legislation=["A2006-34"],
            regulations=["FSSAI_NUTRACEUTICAL_2016", "FSSAI_AYURVEDA_AAHAR_2022", "FSSAI_LICENSING_2011"],
            guidelines=["FSSAI_PRODUCT_APPROVAL", "FSSAI_LABELING_2020"],
            case_law_authority=["SUPREME_COURT_INDIA", "HIGH_COURTS"],
            subject_matter=["food", "nutraceutical", "ayurveda_aahar", "health_supplement", "fsdu", "fsmp"]
        ),
        RegulatoryRegime(
            jurisdiction_id="INDIA_CENTRAL",
            authority="NBA",
            legislation=["A2002-18"],
            regulations=["BD_RULES_2004", "ABS_RULES_2014"],
            guidelines=["NBA_ABS_GUIDELINES", "NBA_VAPS_CLASSIFICATION"],
            case_law_authority=["SUPREME_COURT_INDIA", "HIGH_COURTS", "NGT"],
            subject_matter=["biodiversity", "abs", "biological_resource", "traditional_knowledge", "pbr"]
        ),
        RegulatoryRegime(
            jurisdiction_id="INDIA_CENTRAL",
            authority="IP_INDIA",
            legislation=["A1970-39", "A1999-47", "A1999-48", "A2000-16", "A1957-14", "A2001-53"],
            regulations=["PATENT_RULES_2003", "TM_RULES_2017", "GI_RULES_2002", "DESIGN_RULES_2001", "COPYRIGHT_RULES_2013", "SICLDR_RULES"],
            guidelines=["PATENT_EXAMINATION_GUIDELINES", "TM_EXAMINATION_GUIDELINES", "GI_GUIDELINES"],
            case_law_authority=["SUPREME_COURT_INDIA", "HIGH_COURT_DELHI", "HIGH_COURT_MUMBAI", "IPAB"],
            subject_matter=["patent", "trademark", "geographical_indication", "design", "copyright", "sicldr"]
        ),
        RegulatoryRegime(
            jurisdiction_id="INDIA_CENTRAL",
            authority="AYUSH_MINISTRY",
            legislation=["A2020-14", "A2020-15"],  # NCISM Act, NCH Act
            regulations=["ASU_DRUGS_RULES", "ASU_GOOD_MANUFACTURING_PRACTICES"],
            guidelines=["AYUSH_PHARMACOPOEIA", "AYUSH_FORMULARY"],
            case_law_authority=["SUPREME_COURT_INDIA", "HIGH_COURTS"],
            subject_matter=["ayurveda", "unani", "siddha", "yoga", "naturopathy", "classical_medicine"]
        ),
    ],
    
    "INDIA_STATE": [
        RegulatoryRegime(
            jurisdiction_id="INDIA_STATE",
            authority="STATE_LICENSING_AUTHORITY_AYUSH",
            legislation=[],  # State Acts
            regulations=["STATE_ASU_RULES"],
            guidelines=[],
            case_law_authority=["HIGH_COURTS"],
            subject_matter=["ayurveda_manufacturing", "classical_medicine_license"]
        ),
        RegulatoryRegime(
            jurisdiction_id="INDIA_STATE",
            authority="STATE_BIODIVERSITY_BOARD",
            legislation=["STATE_BD_RULES"],
            regulations=["STATE_BD_RULES"],
            guidelines=["SBB_GUIDELINES"],
            case_law_authority=["HIGH_COURTS", "NGT"],
            subject_matter=["abs_application", "biodiversity_heritage_sites", "pbr"]
        ),
        RegulatoryRegime(
            jurisdiction_id="INDIA_STATE",
            authority="STATE_DRUG_CONTROLLER",
            legislation=[],
            regulations=["STATE_D&C_RULES"],
            guidelines=[],
            case_law_authority=["HIGH_COURTS"],
            subject_matter=["drug_manufacturing_license", "drug_sale_license", "cosmetic_license"]
        ),
    ],
    
    "CBD": [
        RegulatoryRegime(
            jurisdiction_id="CBD",
            authority="CBD_SECRETARIAT",
            legislation=["CBD_1992"],
            regulations=[],
            guidelines=["BONN_GUIDELINES", "AKWE_KON_GUIDELINES", "MOOT_GUIDELINES"],
            case_law_authority=[],
            subject_matter=["biodiversity_conservation", "sustainable_use", "abs", "traditional_knowledge", "protected_areas"]
        ),
    ],
    
    "NAGOYA": [
        RegulatoryRegime(
            jurisdiction_id="NAGOYA",
            authority="ABS_CLEARING_HOUSE",
            legislation=["NAGOYA_PROTOCOL_2010"],
            regulations=[],
            guidelines=["MODEL_CONTRACTUAL_CLAUSES", "COMMUNITY_PROTOCOLS_GUIDELINES", "AWARENESS_RAISING_GUIDELINES"],
            case_law_authority=[],
            subject_matter=["abs", "prior_informed_consent", "mutually_agreed_terms", "compliance", "checkpoints"]
        ),
    ],
    
    "TRIPS": [
        RegulatoryRegime(
            jurisdiction_id="TRIPS",
            authority="WTO_COUNCIL_TRIPS",
            legislation=["TRIPS_AGREEMENT_1994"],
            regulations=[],
            guidelines=["DOHA_DECLARATION", "TRIPS_PUBLIC_HEALTH", "GEOGRAPHICAL_INDICATIONS"],
            case_law_authority=["WTO_DSB_PANEL", "WTO_APPELLATE_BODY"],
            subject_matter=["patent", "trademark", "copyright", "gi", "trade_secret", "enforcement", "public_health"]
        ),
    ],
    
    "PCT": [
        RegulatoryRegime(
            jurisdiction_id="PCT",
            authority="WIPO_IB",
            legislation=["PCT_TREATY", "PCT_REGULATIONS", "PCT_ADMIN_INSTRUCTIONS"],
            regulations=[],
            guidelines=["PCT_GUIDE", "ISA_GUIDELINES", "IPEA_GUIDELINES"],
            case_law_authority=[],
            subject_matter=["international_patent_application", "search", "preliminary_examination", "national_phase"]
        ),
    ],
    
    "USA": [
        RegulatoryRegime(
            jurisdiction_id="USA",
            authority="USPTO",
            legislation=["35_USC", "15_USC", "35_USC_CPC"],
            regulations=["37_CFR", "MPEP", "USPTO_RULES"],
            guidelines=["USPTO_EXAMINATION_GUIDELINES", "PTAB_PRECEDENTIAL_OPINIONS"],
            case_law_authority=["US_SUPREME_COURT", "CAFC", "US_DISTRICT_COURTS", "PTAB"],
            subject_matter=["patent", "trademark", "post_grant", "appeal"]
        ),
        RegulatoryRegime(
            jurisdiction_id="USA",
            authority="FDA",
            legislation=["FD&C_ACT", "PHSA", "BPCIA"],
            regulations=["21_CFR", "FDA_GUIDANCES"],
            guidelines=["FDA_DRUG_GUIDANCES", "FDA_BIOL_GUIDANCES"],
            case_law_authority=["US_SUPREME_COURT", "CAFC", "US_DISTRICT_COURTS"],
            subject_matter=["drug", "biologic", "biosimilar", "generic", "clinical_trial"]
        ),
    ],
}
```

---

## 5. Temporal Validity Engine

### 5.1 Version-Aware Jurisdiction Resolution

```python
@dataclass
class TemporalJurisdictionQuery:
    jurisdiction_id: str
    as_of_date: date
    subject_matter: Optional[str] = None

class TemporalValidityEngine:
    """
    Determines which version of a law/regulation applies at a given date.
    Handles amendments, repeals, prospective/retrospective application.
    """
    
    def __init__(self, graph_db: GraphDatabase):
        self.graph = graph_db
    
    def get_applicable_version(self, query: TemporalJurisdictionQuery) -> ApplicableVersion:
        """
        Returns the version of the legal provision applicable as_of_date.
        """
        # 1. Find the provision in the jurisdiction
        provisions = self._find_provisions(query.jurisdiction_id, query.subject_matter)
        
        # 2. For each provision, find version chain
        applicable = []
        for prov in provisions:
            version = self._get_version_at_date(prov, query.as_of_date)
            if version:
                applicable.append(ApplicableProvision(
                    provision_id=prov.provision_id,
                    version=version,
                    jurisdiction=query.jurisdiction_id,
                    authority_tier=prov.authority_tier
                ))
        
        # 3. Apply conflict resolution across provisions
        resolved = self._resolve_temporal_conflicts(applicable, query.as_of_date)
        
        return ApplicableVersion(
            query=query,
            provisions=resolved,
            determination_date=date.today(),
            confidence=self._compute_confidence(resolved)
        )
    
    def _get_version_at_date(self, provision: Provision, target_date: date) -> Optional[ProvisionVersion]:
        """Walk the SUPERSEDES chain to find version effective at target_date."""
        current = self.graph.get_current_version(provision.provision_id)
        
        while current:
            effective_from = current.effective_from
            effective_to = current.effective_to
            
            if effective_from <= target_date and (effective_to is None or effective_to >= target_date):
                return current
            
            # Walk back
            superseded = self.graph.get_superseded_version(current.version_id)
            if not superseded:
                break
            current = superseded
        
        return None
    
    def _resolve_temporal_conflicts(self, provisions: List[ApplicableProvision], as_of_date: date) -> List[ApplicableProvision]:
        """Apply lex posterior, lex specialis, federal > state."""
        # Group by subject matter
        by_subject = {}
        for p in provisions:
            by_subject.setdefault(p.subject_matter, []).append(p)
        
        resolved = []
        for subject, provs in by_subject.items():
            # Sort by: authority_tier (asc), effective_from (desc), specificity
            provs.sort(key=lambda x: (x.authority_tier, -x.version.effective_from.toordinal(), -x.specificity_score))
            resolved.append(provs[0])  # Most authoritative, most recent, most specific
        
        return resolved
```

### 5.2 Amendment Effect Analysis

```python
@dataclass
class AmendmentEffect:
    amendment_act_id: str
    amendment_date: date
    affected_provisions: List[ProvisionChange]
    retrospective: bool
    transitional_provisions: List[str]

class AmendmentAnalyzer:
    """
    Analyzes amendment acts to determine:
    - Which provisions are affected
    - Whether changes are prospective or retrospective
    - Transitional provisions
    """
    
    def analyze(self, amendment_chunk: LegalChunk) -> AmendmentEffect:
        # Extract amendment text
        text = amendment_chunk.text
        
        # Parse for standard amendment patterns
        changes = []
        
        # Pattern: "Section X is amended by..."
        # Pattern: "In Section X, for '...' substitute '...'"
        # Pattern: "After Section X, insert..."
        # Pattern: "Section X shall be omitted"
        
        # Use LLM for complex amendments
        prompt = f"""
        Analyze this amendment text and extract:
        1. Amendment Act name and date
        2. Each provision affected (Act, Section, Subsection)
        3. Type of change: INSERT, DELETE, SUBSTITUTE, MODIFY, REPEAL
        4. Whether retrospective application is stated
        5. Any transitional provisions
        
        Text: {text}
        
        Return structured JSON.
        """
        result = self.llm.extract_structured(prompt, AmendmentEffect)
        
        # Store in KG for temporal queries
        self._store_amendment_effect(result)
        
        return result
```

---

## 6. Conflict Resolution

### 6.1 Conflict Types & Resolution Rules

```python
class ConflictType(str, Enum):
    FEDERAL_VS_STATE = "federal_vs_state"
    TREATY_VS_DOMESTIC = "treaty_vs_domestic"
    LEX_POSTERIOR = "lex_posterior"           # Later law prevails
    LEX_SPECIALIS = "lex_specialis"           # Specific law prevails over general
    LEX_SUPERIOR = "lex_superior"             # Higher hierarchy prevails
    CONCURRENT = "concurrent"                  # Both apply (different aspects)

CONFLICT_RESOLUTION_RULES = [
    # Federal > State (Constitutional)
    ConflictRule(
        conflict_type=ConflictType.FEDERAL_VS_STATE,
        condition=lambda c: c.federal_authority_tier < c.state_authority_tier,
        resolution="FEDERAL_PREVAILS",
        rationale="Article 246 + Seventh Schedule: Central legislation on Union List prevails"
    ),
    
    # Treaty implementation: Domestic law implementing treaty prevails for domestic application
    ConflictRule(
        conflict_type=ConflictType.TREATY_VS_DOMESTIC,
        condition=lambda c: c.domestic_act_implements_treaty,
        resolution="DOMESTIC_IMPLEMENTATION_PREVAILS",
        rationale="Dualist system: Treaty obligations implemented via domestic law"
    ),
    
    # Lex posterior: Later amendment prevails
    ConflictRule(
        conflict_type=ConflictType.LEX_POSTERIOR,
        condition=lambda c: c.provision1.effective_date > c.provision2.effective_date,
        resolution="LATER_PREVAILS",
        rationale="General principle: leges posteriores priores contrarias abrogant"
    ),
    
    # Lex specialis: Specific provision prevails over general
    ConflictRule(
        conflict_type=ConflictType.LEX_SPECIALIS,
        condition=lambda c: c.provision1.specificity > c.provision2.specificity,
        resolution="SPECIFIC_PREVAILS",
        rationale="lex specialis derogat legi generali"
    ),
    
    # Authority tier: Tier 1 > Tier 2 > Tier 3 > Tier 4
    ConflictRule(
        conflict_type=ConflictType.LEX_SUPERIOR,
        condition=lambda c: c.provision1.authority_tier < c.provision2.authority_tier,
        resolution="HIGHER_TIER_PREVAILS",
        rationale="Hierarchy of norms: Constitution > Act > Rules > Guidelines"
    ),
]

class ConflictResolver:
    def resolve(self, provisions: List[ApplicableProvision], context: ConflictContext) -> ResolutionResult:
        conflicts = self._detect_conflicts(provisions)
        resolutions = []
        
        for conflict in conflicts:
            for rule in CONFLICT_RESOLUTION_RULES:
                if rule.condition(conflict):
                    resolutions.append(ConflictResolution(
                        conflict=conflict,
                        rule=rule,
                        prevailing=rule.resolution,
                        rationale=rule.rationale
                    ))
                    break
        
        return ResolutionResult(
            original_provisions=provisions,
            conflicts=conflicts,
            resolutions=resolutions,
            final_provisions=self._apply_resolutions(provisions, resolutions)
        )
```

---

## 7. Hard Isolation Enforcement

### 7.1 Retrieval-Level Isolation

```python
class JurisdictionIsolationFilter:
    """
    Enforces hard jurisdiction isolation at metadata pre-filter stage.
    This is a NON-NEGOTIABLE requirement - implemented at retrieval engine level.
    """
    
    def __init__(self, jurisdiction_engine: JurisdictionEngine):
        self.jurisdiction_engine = jurisdiction_engine
    
    def build_metadata_filter(self, query: str, context: QueryContext) -> MetadataFilter:
        """
        Build HARD metadata filter for retrieval.
        This runs BEFORE any vector/lexical search.
        """
        # Determine applicable jurisdictions
        jurisdiction_result = self.jurisdiction_engine.determine(
            JurisdictionDeterminationInput(
                query_text=query,
                query_language=context.language,
                formulation_classification=context.formulation_classification,
                user_location=context.user_location,
                target_markets=context.target_markets
            )
        )
        
        # Build filter: ONLY these jurisdictions allowed
        primary_jurisdictions = jurisdiction_result.jurisdictions[:1]  # Primary only for isolation
        secondary_jurisdictions = jurisdiction_result.jurisdictions[1:] if len(jurisdiction_result.jurisdictions) > 1 else []
        
        # Hard filter: jurisdiction_id IN (primary)
        # This is ENFORCED at vector DB query level
        filter = MetadataFilter(
            must_match={
                "jurisdiction_id": primary_jurisdictions  # Hard requirement
            },
            should_match={
                "jurisdiction_id": secondary_jurisdictions  # Soft boost only
            },
            must_not_match={
                "jurisdiction_id": self._get_excluded_jurisdictions(primary_jurisdictions)
            }
        )
        
        # Attach jurisdiction context for downstream
        context.jurisdiction_context = JurisdictionContext(
            primary=primary_jurisdictions,
            secondary=secondary_jurisdictions,
            determination_result=jurisdiction_result,
            filter=filter
        )
        
        return filter
    
    def _get_excluded_jurisdictions(self, primary: List[str]) -> List[str]:
        """Get jurisdictions that should be explicitly excluded."""
        # For India primary, exclude foreign national laws unless treaty
        if "INDIA_CENTRAL" in primary or "INDIA_STATE" in primary:
            return ["USA", "EU", "JAPAN", "UK", "CANADA", "AUSTRALIA", "SINGAPORE"]
        return []


class JurisdictionContext:
    """Carries jurisdiction info through entire pipeline."""
    primary: List[str]
    secondary: List[str]
    determination_result: JurisdictionDeterminationResult
    filter: MetadataFilter
    
    def get_retrieval_jurisdictions(self) -> List[str]:
        return self.primary
    
    def get_generation_jurisdictions(self) -> List[str]:
        return self.primary + self.secondary
    
    def requires_multi_jurisdiction_answer(self) -> bool:
        return len(self.secondary) > 0
```

### 7.2 Generation-Level Isolation

```python
class JurisdictionAwareGenerator:
    """
    Generates answers with explicit jurisdiction attribution.
    NEVER mixes legal provisions from different jurisdictions in same claim.
    """
    
    def generate(self, query: str, evidence: List[Evidence], jurisdiction_ctx: JurisdictionContext) -> GeneratedAnswer:
        # Group evidence by jurisdiction
        evidence_by_jurisdiction = self._group_by_jurisdiction(evidence)
        
        # Generate answer segments per jurisdiction
        segments = []
        for jur_id, jur_evidence in evidence_by_jurisdiction.items():
            segment = self._generate_segment(query, jur_evidence, jur_id)
            segments.append(AnswerSegment(
                jurisdiction=jur_id,
                content=segment.content,
                citations=segment.citations,
                confidence=segment.confidence
            ))
        
        # If multi-jurisdiction, add comparison/summary segment
        if len(segments) > 1:
            comparison = self._generate_comparison(query, segments)
            segments.append(AnswerSegment(
                jurisdiction="MULTI_JURISDICTION_COMPARISON",
                content=comparison,
                citations=[],
                confidence=0.8
            ))
        
        return GeneratedAnswer(
            query=query,
            segments=segments,
            jurisdiction_context=jurisdiction_ctx
        )
    
    def _generate_segment(self, query: str, evidence: List[Evidence], jurisdiction: str) -> SegmentResult:
        # Build prompt with ONLY this jurisdiction's evidence
        prompt = self._build_jurisdiction_prompt(query, evidence, jurisdiction)
        response = self.llm.generate(prompt)
        
        # Verify no cross-jurisdiction contamination
        self._verify_jurisdiction_purity(response, jurisdiction)
        
        return SegmentResult(content=response.text, citations=response.citations, confidence=response.confidence)
```

---

## 8. Multi-Jurisdiction Query Handling

### 8.1 Explicit Segmentation

```python
@dataclass
class MultiJurisdictionQuery:
    original_query: str
    sub_queries: List[SubQuery]  # One per jurisdiction
    
@dataclass
class SubQuery:
    jurisdiction: str
    query_text: str
    intent: str
    formulation_context: Optional[FormulationContext]

class MultiJurisdictionPlanner:
    """
    Decomposes multi-jurisdiction queries into jurisdiction-segmented sub-queries.
    """
    
    def plan(self, query: str, jurisdiction_ctx: JurisdictionContext) -> MultiJurisdictionQuery:
        primary = jurisdiction_ctx.primary[0]
        secondary = jurisdiction_ctx.secondary
        
        sub_queries = []
        
        # Primary jurisdiction sub-query
        sub_queries.append(SubQuery(
            jurisdiction=primary,
            query_text=query,
            intent="PRIMARY_ANSWER",
            formulation_context=jurisdiction_ctx.formulation_context
        ))
        
        # Secondary jurisdiction sub-queries
        for jur in secondary:
            # Rewrite query for that jurisdiction's legal framework
            rewritten = self._rewrite_for_jurisdiction(query, primary, jur)
            sub_queries.append(SubQuery(
                jurisdiction=jur,
                query_text=rewritten,
                intent="COMPARATIVE" if len(secondary) > 1 else "SECONDARY_ANSWER",
                formulation_context=jurisdiction_ctx.formulation_context
            ))
        
        return MultiJurisdictionQuery(original_query=query, sub_queries=sub_queries)
    
    def _rewrite_for_jurisdiction(self, query: str, from_jur: str, to_jur: str) -> str:
        """Rewrite query to target jurisdiction's legal terminology."""
        # e.g., "Section 3(d) patentability" (India) → "Section 101 patent eligibility" (USA)
        # Use LLM with jurisdiction mapping
        mapping = self._get_terminology_mapping(from_jur, to_jur)
        prompt = f"Rewrite this legal query for {to_jur} jurisdiction using local terminology:\n{query}\nMapping: {mapping}"
        return self.llm.generate(prompt).text
```

### 8.2 Comparative Answer Generation

```python
class ComparativeAnswerGenerator:
    def generate(self, segments: List[AnswerSegment]) -> ComparativeAnswer:
        # Build comparison table
        comparison = self._build_comparison_table(segments)
        
        # Generate narrative comparison
        narrative = self._generate_narrative(segments)
        
        return ComparativeAnswer(
            summary=narrative,
            comparison_table=comparison,
            jurisdictions=[s.jurisdiction for s in segments],
            key_differences=self._extract_key_differences(segments),
            harmonization_notes=self._identify_harmonization(segments)
        )
```

---

## 9. Integration Points

### 9.1 With Query Analysis (Phase 3)

```python
# JurisdictionEngine feeds into QueryAnalysis
class QueryAnalysisInput:
    jurisdiction_context: JurisdictionContext
    
    def get_retrieval_hints(self) -> RetrievalHints:
        return RetrievalHints(
            jurisdiction_filter=self.jurisdiction_context.filter,
            applicable_regimes=[self._get_regime(j) for j in self.jurisdiction_context.primary],
            authority_tiers=[1, 2],  # Primary + secondary authority
            temporal_constraint=self.jurisdiction_context.temporal_constraint
        )
```

### 9.2 With Retrieval Engine (Phase 6)

```python
# RetrievalEngine receives hard jurisdiction filter
class RetrievalEngine:
    def retrieve(self, query: str, analysis: QueryAnalysis) -> RetrievalResult:
        # Jurisdiction filter is MANDATORY - retrieved at metadata pre-filter
        jurisdiction_filter = analysis.jurisdiction_context.filter
        
        # This filter is applied BEFORE any scoring
        candidates = self.vector_store.search(
            query_embedding=query_embedding,
            metadata_filter=jurisdiction_filter.must_match,  # HARD FILTER
            top_k=100
        )
        # ... rest of pipeline
```

### 9.3 With Formulation Classification (Phase 8)

```python
# Formulation classification provides default jurisdiction mapping
class FormulationToJurisdictionMapper:
    DEFAULT_MAPPING = {
        FormulationClass.CLASSICAL_MEDICINE: ["INDIA_CENTRAL", "INDIA_STATE", "CBD", "NAGOYA"],
        FormulationClass.GENERIC_MEDICINE: ["INDIA_CENTRAL", "TRIPS"],
        FormulationClass.PATENT_PROPRIETARY_MEDICINE: ["INDIA_CENTRAL", "INDIA_STATE"],
        FormulationClass.NEW_DRUG: ["INDIA_CENTRAL", "PCT"],
        FormulationClass.PHYTOPHARMACEUTICAL: ["INDIA_CENTRAL", "CBD", "NAGOYA"],
        FormulationClass.AYURVEDA_AAHAR: ["INDIA_CENTRAL"],
        FormulationClass.NUTRACEUTICAL: ["INDIA_CENTRAL", "CODEX"],
        FormulationClass.COSMETIC: ["INDIA_CENTRAL", "INDIA_STATE", "EU"],  # EU cosmetic regs often referenced
    }
```

### 9.4 With Knowledge Graph (Phase 7)

```python
# KG stores jurisdiction hierarchy and treaty relationships
# Query: "What are India's CBD obligations for ABS?"
# KG: (INDIA_CENTRAL)-[:PARTY_TO]->(CBD)-[:HAS_PROTOCOL]->(NAGOYA)
# → Retrieval: Filter to INDIA_CENTRAL + CBD + NAGOYA jurisdictions
```

---

## 10. Evaluation Framework

### 10.1 Test Cases

```python
JURISDICTION_TEST_CASES = [
    JurisdictionTestCase(
        case_id="JUR-001",
        query="What does Section 3(d) of the Patents Act say?",
        expected_primary="INDIA_CENTRAL",
        expected_secondary=[],
        formulation_class=FormulationClass.NEW_DRUG,
        notes="Clear India-specific query"
    ),
    JurisdictionTestCase(
        case_id="JUR-002",
        query="Compare patent eligibility in India and USA for software inventions",
        expected_primary="INDIA_CENTRAL",
        expected_secondary=["USA"],
        formulation_class=None,
        notes="Explicit multi-jurisdiction comparative query"
    ),
    JurisdictionTestCase(
        case_id="JUR-003",
        query="What are the ABS requirements for exporting Indian herbal extracts to EU?",
        expected_primary="INDIA_CENTRAL",
        expected_secondary=["EU", "NAGOYA", "CBD"],
        formulation_class=FormulationClass.PHYTOPHARMACEUTICAL,
        notes="Cross-border: India ABS + EU import + Treaty obligations"
    ),
    JurisdictionTestCase(
        case_id="JUR-004",
        query="नागोया प्रोटोकॉल के तहत PIC और MAT की आवश्यकताएं क्या हैं?",
        expected_primary="NAGOYA",
        expected_secondary=["INDIA_CENTRAL", "CBD"],
        formulation_class=None,
        notes="Hindi query about Nagoya Protocol - treaty primary, India implementation secondary"
    ),
    JurisdictionTestCase(
        case_id="JUR-005",
        query="What are the cosmetic labeling requirements?",
        expected_primary="INDIA_CENTRAL",
        expected_secondary=["INDIA_STATE"],
        formulation_class=FormulationClass.COSMETIC,
        notes="Cosmetic → CDSCO (Central) + State Licensing Authority"
    ),
]
```

### 10.2 Metrics

| Metric | Target |
|--------|--------|
| Primary jurisdiction accuracy | 100% on explicit queries |
| Secondary jurisdiction relevance | > 90% precision |
| Zero silent mixing rate | 100% (hard requirement) |
| Conflict resolution accuracy | > 95% |
| Temporal version accuracy | 100% on test dates |
| Latency | < 50ms p95 |

---

## 11. Open Research Questions

| ID | Question | Status |
|----|----------|--------|
| ORQ-46 | Optimal confidence threshold for multi-jurisdiction triggering? | Experiment |
| ORQ-47 | How to handle "global" queries with no jurisdiction specified? | Default to user location + India |
| ORQ-48 | State vs Central conflict resolution for concurrent list subjects? | Constitutional analysis needed |
| ORQ-49 | Treaty self-execution vs implementation: when does treaty apply directly? | Legal research |
| ORQ-50 | Retrospective amendment detection accuracy? | Need annotated dataset |
| ORQ-51 | Custom jurisdiction support for enterprise users? | Product decision |

---

## 12. Implementation Priority

| Component | Priority | Dependencies |
|-----------|----------|--------------|
| Jurisdiction Registry | **CORE** | - |
| Deterministic Determination | **CORE** | Phase 8 (formulation class) |
| Hard Isolation Filter | **CORE** | Phase 6 (retrieval engine) |
| Authority/Regime Mapping | **CORE** | Phase 4 (ingestion metadata) |
| Temporal Validity Engine | **OPTIONAL** | Phase 7 (KG temporal) |
| Conflict Resolver | **OPTIONAL** | Phase 7 (KG relationships) |
| Multi-Jurisdiction Planner | **OPTIONAL** | Phase 13 (agentic) |
| Comparative Generator | **EXPERIMENTAL** | Phase 10 (citation-first) |

---

## 13. Summary

| Aspect | Decision |
|--------|----------|
| **Core Principle** | Explicit jurisdiction context for every query/retrieval/answer |
| **Isolation** | HARD metadata filter at pre-filter stage (non-negotiable) |
| **Taxonomy** | 15+ jurisdictions across 5 types (National, State, Treaty, Regional, Org) |
| **Determination** | Formulation class → Query keywords → User context → LLM disambiguation |
| **Conflict Resolution** | Constitutional hierarchy + Lex posterior + Lex specialis + Authority tier |
| **Temporal** | Version chains via KG (SUPERSEDES), amendment effect analysis |
| **Multi-Jurisdiction** | Explicit segmentation → Separate retrieval → Segmented generation → Comparison |
| **Integration** | Feeds Phase 3 (query analysis), Phase 6 (retrieval filter), Phase 8 (formulation default), Phase 7 (KG) |

---

## 14. Next Phase: Phase 10 - Citation-First Generation

Phase 10 will design the **Citation-First Generation Engine** that:
- Takes jurisdiction-isolated evidence as input
- Extracts claims from evidence
- Maps every claim to supporting evidence
- Generates answer from claims (not from parametric knowledge)
- Verifies every citation before output
- Abstains when evidence insufficient