# Phase 8: Formulation Classification Architecture

## Overview

This document designs the **Formulation Classification Engine** for IP-SAKTI. The engine determines the regulatory classification of a formulation/product under Indian law, which directly affects:
- Applicable regulatory regime (D&C Act, FSSAI, AYUSH, etc.)
- Licensing requirements
- ABS (Access and Benefit Sharing) obligations
- Labeling requirements
- Import/export restrictions

**Key Principle**: Deterministic legal rules (Schedule E, Section 3(d), Rule 158, etc.) take precedence. LLM reasoning is ONLY for:
- Borderline cases where rules conflict or are ambiguous
- Evidence completeness assessment
- Confidence calibration
- Human escalation recommendations

**LLM MUST NEVER silently override deterministic legal rules.**

---

## 1. Requirements

### 1.1 Functional Requirements

| Requirement | Description |
|------------|-------------|
| **FR-FC-01** | Extract structured formulation data from unstructured user input (ingredients, dosage, claims, preparation method, intended use) |
| **FR-FC-02** | Apply deterministic classification rules per D&C Act, FSSAI, AYUSH regulations |
| **FR-FC-03** | Handle 8 formulation classes: Classical Medicine, Generic Medicine, Patent/Proprietary, New/Non-classical, Phytopharmaceutical, Ayurveda-Aahar, Nutraceutical, Cosmetic |
| **FR-FC-04** | For borderline cases, invoke LLM reasoning with retrieved legal evidence |
| **FR-FC-05** | Compute confidence score combining rule match strength, LLM agreement, evidence completeness |
| **FR-FC-06** | Escalate to human expert when confidence < 0.6 OR conflicting classifications OR novel formulations |
| **FR-FC-07** | Provide classification rationale traceable to specific legal provisions |
| **FR-FC-08** | Output classification with applicable regulatory regime, licensing requirements, ABS obligations |
| **FR-FC-09** | Support multilingual input (English + 12 Indian languages) |
| **FR-FC-10** | Version classification rules with amendment tracking |

### 1.2 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| **NFR-FC-01** | Classification latency: < 2s (p95) for deterministic path |
| **NFR-FC-02** | Classification latency: < 10s (p95) with LLM reasoning |
| **NFR-FC-03** | Deterministic rule accuracy: 100% on clear-cut cases |
| **NFR-FC-04** | LLM-assisted accuracy: > 90% F1 on expert-annotated borderline cases |
| **NFR-FC-05** | Escalation precision: < 5% false escalations (clear cases sent to human) |
| **NFR-FC-06** | Escalation recall: > 95% of truly ambiguous cases escalated |

---

## 2. Formulation Class Taxonomy

### 2.1 Classification Hierarchy

```
FORMULATION
├── DRUG (D&C Act)
│   ├── CLASSICAL_MEDICINE
│   │   ├── Ayurveda (First Schedule, D&C Act)
│   │   ├── Siddha (First Schedule, D&C Act)
│ │   ├── Unani (First Schedule, D&C Act)
│ │   └── Schedule E(1) Drugs (D&C Act)
│   ├── GENERIC_MEDICINE (D&C Act Section 3(b))
│   ├── PATENT_PROPRIETARY_MEDICINE (Rule 158, D&C Rules; Form 24/25)
│   ├── NEW_DRUG (D&C Act Section 12; Rule 122)
│   │   ├── New Chemical Entity
│   │   ├── New Indication
│   │   ├── New Route/Strength
│   │   └── Phytopharmaceutical (CDSCO 2017 Guidelines)
│   └── BIOLOGICAL (D&C Act; CDSCO Guidelines)
├── FOOD (FSSAI Act)
│   ├── AYURVEDA_AAHAR (FSSAI 2022 Regulations)
│   ├── NUTRACEUTICAL (FSSAI 2016/2022 Regulations)
│   │   ├── Health Supplement
│   │   ├── Nutraceutical
│   │   ├── Food for Special Dietary Use (FSDU)
│   │   ├── Food for Special Medical Purpose (FSMP)
│   │   └── Prebiotic/Probiotic
│   ├── FOOD_INGREDIENT
│   └── NOVEL_FOOD
├── COSMETIC (D&C Act Section 3(aaa))
│   ├── HERBAL_COSMETIC
│   └── SYNTHETIC_COSMETIC
└── TRADITIONAL_KNOWLEDGE (TKDL / ABS)
    ├── TK_FORMULATION (TKDL documented)
    └── COMMUNITY_KNOWLEDGE (PBR documented)
```

### 2.2 Class Definitions & Legal Basis

| Class | Legal Basis | Key Criteria | Regulatory Regime |
|-------|-------------|--------------|-------------------|
| **Classical Medicine** | D&C Act First Schedule + Schedule E(1) | Listed in First Schedule; traditional text reference; ingredients per classical text | D&C Act; State Licensing Authority; ASU Drugs Rules |
| **Generic Medicine** | D&C Act Section 3(b) | Same active ingredient, strength, dosage form as approved drug; bioequivalent | D&C Act; Central Licensing Authority |
| **Patent/Proprietary Medicine** | D&C Rules Rule 158; Form 24/25 | Not in First Schedule; proprietary formula; manufactured under license | D&C Rules; State Licensing Authority; Form 24/25 |
| **New Drug** | D&C Act Section 12; Rule 122 | Not used in India to significant extent; new therapeutic entity | D&C Act; CDSCO; CT Rules 2019 |
| **Phytopharmaceutical** | CDSCO 2017 Guidelines | Plant-based; standardized extract; defined markers; clinical data | D&C Act; CDSCO; Phytopharmaceutical Guidelines |
| **Ayurveda-Aahar** | FSSAI Ayurveda-Aahar Regulations 2022 | Food prepared per Ayurveda texts; health claims per Schedule | FSSAI; Food License; Ayurveda-Aahar Regulations |
| **Nutraceutical** | FSSAI 2016/2022 Regulations | Food with health benefits; defined categories | FSSAI; Nutraceutical Regulations |
| **Cosmetic** | D&C Act Section 3(aaa) | External application; cleansing, beautifying, altering appearance | D&C Act; Cosmetic Rules 2020 |

---

## 3. Input Extraction Design

### 3.1 Input Schema

```python
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

class DosageForm(str, Enum):
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"
    OINTMENT = "ointment"
    POWDER = "powder"
    DECOCTION = "decoction"  # kwath
    PILL = "pill"  # gutika/vati
    OIL = "oil"  # taila
    GHrita = "ghrita"
    ASHAVA = "asava"  # fermented
    ARISTHA = "arishta"  # fermented
    CHURNA = "churna"
    LEHYA = "lehya"  # confection
    OTHER = "other"

class PreparationMethod(str, Enum):
    CLASSICAL_TEXT = "classical_text"  # per Ayurveda/Siddha/Unani text
    MODERN_PHARMA = "modern_pharma"
    EXTRACTION = "extraction"
    FERMENTATION = "fermentation"
    CALCINATION = "calcination"  # bhasma
    PURIFICATION = "purification"  # shodhana
    OTHER = "other"

class IntendedUse(str, Enum):
    THERAPEUTIC = "therapeutic"
    PROPHYLACTIC = "prophylactic"
    HEALTH_SUPPLEMENT = "health_supplement"
    COSMETIC = "cosmetic"
    FOOD = "food"
    RESEARCH = "research"
    EXPORT = "export"

@dataclass
class Ingredient:
    name: str
    scientific_name: Optional[str] = None
    common_names: List[str] = field(default_factory=list)
    quantity: Optional[str] = None  # e.g., "500mg", "1 part"
    unit: Optional[str] = None
    plant_part: Optional[str] = None  # root, leaf, bark, fruit, seed, whole_plant
    is_biological_resource: bool = False
    geographical_origin: Optional[str] = None
    is_scheduled: bool = False  # Scheduled E(1), etc.
    is_prohibited: bool = False
    traditional_use: Optional[str] = None

@dataclass
class FormulationInput:
    # Required
    product_name: str
    ingredients: List[Ingredient]
    
    # Strongly recommended
    dosage_form: Optional[DosageForm] = None
    preparation_method: Optional[PreparationMethod] = None
    intended_use: Optional[IntendedUse] = None
    manufacturer: Optional[str] = None
    manufacturing_site: Optional[str] = None
    
    # Optional but valuable
    claims: List[str] = field(default_factory=list)
    traditional_text_reference: Optional[str] = None  # e.g., "Charaka Samhita Chikitsa Sthana 5/12"
    classical_formula_name: Optional[str] = None  # e.g., "Triphala", "Chyawanprash"
    marketing_material: Optional[str] = None
    label_text: Optional[str] = None
    existing_license: Optional[str] = None
    export_countries: List[str] = field(default_factory=list)
    
    # Context
    language: str = "en"
    user_context: Optional[str] = None  # "startup founder", "researcher", etc.
```

### 3.2 Extraction Pipeline

```python
class FormulationExtractor:
    """
    Extract structured formulation data from user input.
    Handles: free text, structured forms, multilingual input.
    """
    
    def __init__(self, llm_client, terminologies: TerminologyService):
        self.llm = llm_client
        self.terminologies = terminologies
        self.ingredient_normalizer = IngredientNormalizer(terminologies)
    
    def extract(self, raw_input: str, language: str = "en") -> FormulationInput:
        # 1. Language detection & translation if needed
        if language != "en":
            raw_input = self._translate_to_english(raw_input, language)
        
        # 2. Structured extraction via LLM with schema
        extraction_prompt = self._build_extraction_prompt(raw_input)
        extracted = self.llm.extract_structured(extraction_prompt, FormulationInput)
        
        # 3. Normalize ingredients against terminologies
        for ing in extracted.ingredients:
            normalized = self.ingredient_normalizer.normalize(ing.name)
            if normalized:
                ing.scientific_name = normalized.scientific_name
                ing.common_names = normalized.synonyms
                ing.plant_part = normalized.common_plant_part
                ing.is_biological_resource = normalized.in_biological_resources_db
        
        # 4. Detect scheduled/prohibited ingredients
        self._flag_regulatory_ingredients(extracted)
        
        # 5. Infer missing fields from context
        self._infer_missing_fields(extracted)
        
        return extracted
    
    def _build_extraction_prompt(self, text: str) -> str:
        return f"""
Extract formulation data from the following input. Return JSON matching the schema.

Input: "{text}"

Extract:
1. product_name
2. ingredients (list: name, quantity, unit, plant_part if mentioned)
3. dosage_form (tablet/capsule/syrup/ointment/powder/decoction/pill/oil/ghrita/asava/arishta/churna/lehya/other)
4. preparation_method (classical_text/modern_pharma/extraction/fermentation/calcination/purification/other)
5. intended_use (therapeutic/prophylactic/health_supplement/cosmetic/food/research/export)
6. claims (list of health/beauty claims)
7. traditional_text_reference (if mentioned, e.g., "Charaka Samhita 5/12")
8. classical_formula_name (if mentioned, e.g., "Triphala")
9. manufacturer, manufacturing_site
10. marketing_material, label_text, existing_license
11. export_countries

If uncertain, use null. Do not hallucinate.
"""
```

---

## 4. Deterministic Rule Engine

### 4.1 Rule Structure

```python
from dataclasses import dataclass
from typing import Callable, Optional
from enum import Enum

class RuleResult(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    CONFLICT = "conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"

@dataclass
class ClassificationRule:
    rule_id: str
    name: str
    formulation_class: FormulationClass
    legal_basis: str  # e.g., "D&C Act Schedule E(1)", "Rule 158 D&C Rules"
    authority_tier: int  # 1 = primary legislation, 2 = rules, 3 = guidelines
    
    # Conditions (ALL must be true for match)
    conditions: List[Callable[[FormulationInput], bool]]
    
    # Exclusions (ANY true = no match)
    exclusions: List[Callable[[FormulationInput], bool]] = field(default_factory=list)
    
    # Priority for conflict resolution (higher = more specific)
    priority: int = 0
    
    # Evidence required for this rule
    required_evidence: List[str] = field(default_factory=list)
    
    def evaluate(self, formulation: FormulationInput) -> RuleResult:
        # Check exclusions first
        for exclusion in self.exclusions:
            if exclusion(formulation):
                return RuleResult.NO_MATCH
        
        # Check all conditions
        unmet = []
        for condition in self.conditions:
            if not condition(formulation):
                unmet.append(condition.__name__)
        
        if not unmet:
            return RuleResult.MATCH
        elif len(unmet) == len(self.conditions):
            return RuleResult.NO_MATCH
        else:
            return RuleResult.INSUFFICIENT_EVIDENCE
```

### 4.2 Core Deterministic Rules

#### Rule Set 1: Classical Medicine (D&C Act First Schedule + Schedule E(1))

```python
CLASSICAL_MEDICINE_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-001",
        name="First Schedule Classical Medicine",
        formulation_class=FormulationClass.CLASSICAL_MEDICINE,
        legal_basis="Drugs & Cosmetics Act, First Schedule (Ayurveda/Siddha/Unani)",
        authority_tier=1,
        priority=100,
        conditions=[
            lambda f: f.classical_formula_name is not None,
            lambda f: f.classical_formula_name in FIRST_SCHEDULE_FORMULAS,
            lambda f: f.preparation_method == PreparationMethod.CLASSICAL_TEXT,
            lambda f: all(ing.name in CLASSICAL_INGREDIENTS for ing in f.ingredients),
        ],
        exclusions=[
            lambda f: any(ing.is_prohibited for ing in f.ingredients),
            lambda f: f.intended_use == IntendedUse.COSMETIC,
        ],
        required_evidence=["classical_formula_name", "traditional_text_reference"]
    ),
    
    ClassificationRule(
        rule_id="FC-RULE-002",
        name="Schedule E(1) Drug",
        formulation_class=FormulationClass.CLASSICAL_MEDICINE,
        legal_basis="Drugs & Cosmetics Act, Schedule E(1)",
        authority_tier=1,
        priority=95,
        conditions=[
            lambda f: any(ing.is_scheduled_e1 for ing in f.ingredients),
            lambda f: f.dosage_form in CLASSICAL_DOSAGE_FORMS,
        ],
        exclusions=[
            lambda f: f.intended_use == IntendedUse.COSMETIC,
        ],
        required_evidence=["scheduled_ingredient_evidence"]
    ),
]

FIRST_SCHEDULE_FORMULAS = {
    # Ayurveda
    "triphala", "chyawanprash", "ashwagandha_churna", "brahmi_vati",
    "mahayograj_guggulu", "kaishore_guggulu", "punarnavadi_mandur",
    # ... 500+ classical formulas from First Schedule
    # Siddha
    "kabasura_kudineer", "nilavembu_kudineer", "thiriphala_chooranam",
    # Unani
    "majoon_dabeedul_ward", "habbe_mumsik", "roghan_badam_shirin",
}

SCHEDULE_E1_INGREDIENTS = {
    "aconite", "bhanga", "datura", "kuchla", "vatsanabha",  # toxic herbs
    # ... full Schedule E(1) list
}
```

#### Rule Set 2: Generic Medicine (D&C Act Section 3(b))

```python
GENERIC_MEDICINE_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-010",
        name="Generic Medicine Definition",
        formulation_class=FormulationClass.GENERIC_MEDICINE,
        legal_basis="Drugs & Cosmetics Act Section 3(b)",
        authority_tier=1,
        priority=80,
        conditions=[
            lambda f: f.dosage_form in MODERN_DOSAGE_FORMS,
            lambda f: not f.classical_formula_name,
            lambda f: f.preparation_method == PreparationMethod.MODERN_PHARMA,
            lambda f: all(not ing.is_biological_resource for ing in f.ingredients),
        ],
        exclusions=[
            lambda f: f.intended_use in [IntendedUse.COSMETIC, IntendedUse.FOOD],
            lambda f: any(ing.name in CLASSICAL_FORMULA_INDICATORS for ing in f.ingredients),
        ],
        required_evidence=["active_ingredient", "strength", "bioequivalence_data"]
    ),
]
```

#### Rule Set 3: Patent/Proprietary Medicine (Rule 158, D&C Rules)

```python
PATENT_PROPRIETARY_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-020",
        name="Patent/Proprietary Medicine - Rule 158",
        formulation_class=FormulationClass.PATENT_PROPRIETARY_MEDICINE,
        legal_basis="Drugs & Cosmetics Rules, Rule 158; Form 24/25",
        authority_tier=2,
        priority=90,
        conditions=[
            lambda f: f.dosage_form in MODERN_DOSAGE_FORMS,
            lambda f: not f.classical_formula_name,
            lambda f: f.preparation_method == PreparationMethod.MODERN_PHARMA,
            lambda f: f.existing_license in ["Form 24", "Form 25", "Form 24A", "Form 25A"],
        ],
        exclusions=[
            lambda f: f.intended_use == IntendedUse.COSMETIC,
            lambda f: any(ing.name in FIRST_SCHEDULE_FORMULAS for ing in f.ingredients),
        ],
        required_evidence=["license_number", "formula_composition"]
    ),
]
```

#### Rule Set 4: New Drug / Phytopharmaceutical (Section 12, Rule 122, CDSCO 2017)

```python
NEW_DRUG_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-030",
        name="New Drug - Section 12 D&C Act",
        formulation_class=FormulationClass.NEW_DRUG,
        legal_basis="Drugs & Cosmetics Act Section 12; Rule 122 D&C Rules",
        authority_tier=1,
        priority=85,
        conditions=[
            lambda f: f.preparation_method == PreparationMethod.MODERN_PHARMA,
            lambda f: f.intended_use == IntendedUse.THERAPEUTIC,
            lambda f: not _is_approved_in_india(f.ingredients),  # Not used to significant extent
        ],
        exclusions=[],
        required_evidence=["clinical_trial_data", "cdsc_approval"]
    ),
    
    ClassificationRule(
        rule_id="FC-RULE-031",
        name="Phytopharmaceutical - CDSCO 2017",
        formulation_class=FormulationClass.PHYTOPHARMACEUTICAL,
        legal_basis="CDSCO Guidelines for Phytopharmaceuticals 2017",
        authority_tier=2,
        priority=88,
        conditions=[
            lambda f: f.preparation_method in [PreparationMethod.EXTRACTION, PreparationMethod.PURIFICATION],
            lambda f: any(ing.is_biological_resource for ing in f.ingredients),
            lambda f: f.dosage_form in [DosageForm.TABLET, DosageForm.CAPSULE, DosageForm.SYRUP],
            lambda f: _has_standardized_markers(f.ingredients),  # Defined chemical markers
            lambda f: _has_preclinical_data(f),  # Preclinical safety data
        ],
        exclusions=[
            lambda f: f.classical_formula_name in FIRST_SCHEDULE_FORMULAS,
        ],
        required_evidence=["standardized_extract_spec", "marker_compounds", "preclinical_data", "clinical_data_phase"]
    ),
]
```

#### Rule Set 5: Ayurveda-Aahar (FSSAI 2022)

```python
AYURVEDA_AAHAR_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-040",
        name="Ayurveda-Aahar - FSSAI 2022",
        formulation_class=FormulationClass.AYURVEDA_AAHAR,
        legal_basis="FSSAI (Ayurveda-Aahar) Regulations, 2022",
        authority_tier=1,
        priority=85,
        conditions=[
            lambda f: f.intended_use in [IntendedUse.FOOD, IntendedUse.HEALTH_SUPPLEMENT],
            lambda f: f.preparation_method == PreparationMethod.CLASSICAL_TEXT,
            lambda f: f.traditional_text_reference is not None,
            lambda f: _is_food_ingredient(f.ingredients),  # All ingredients are food-grade
            lambda f: _claims_permitted_ayurveda_aahar(f.claims),  # Claims per Schedule
        ],
        exclusions=[
            lambda f: any(ing.is_scheduled_e1 for ing in f.ingredients),
            lambda f: f.dosage_form in [DosageForm.TABLET, DosageForm.CAPSULE, DosageForm.INJECTION],
        ],
        required_evidence=["traditional_text_ref", "food_grade_ingredients", "schedule_claims"]
    ),
]
```

#### Rule Set 6: Nutraceutical (FSSAI 2016/2022)

```python
NUTRACEUTICAL_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-050",
        name="Health Supplement - FSSAI 2016",
        formulation_class=FormulationClass.NUTRACEUTICAL,
        legal_basis="FSSAI (Health Supplements, Nutraceuticals, FSDU, FSMP) Regulations, 2016/2022",
        authority_tier=1,
        priority=75,
        conditions=[
            lambda f: f.intended_use == IntendedUse.HEALTH_SUPPLEMENT,
            lambda f: _is_permitted_nutraceutical_ingredient(f.ingredients),
            lambda f: _claims_permitted_nutraceutical(f.claims),
            lambda f: f.dosage_form in [DosageForm.TABLET, DosageForm.CAPSULE, DosageForm.POWDER, DosageForm.SYRUP],
        ],
        exclusions=[
            lambda f: any(ing.is_scheduled_e1 for ing in f.ingredients),
            lambda f: f.classical_formula_name in FIRST_SCHEDULE_FORMULAS,
            lambda f: f.therapeutic_claims_present(),
        ],
        required_evidence=["ingredient_permitted_list", "label_compliance", "rda_compliance"]
    ),
    
    ClassificationRule(
        rule_id="FC-RULE-051",
        name="Food for Special Dietary Use (FSDU)",
        formulation_class=FormulationClass.NUTRACEUTICAL,
        legal_basis="FSSAI Regulations 2016/2022",
        authority_tier=1,
        priority=75,
        conditions=[
            lambda f: f.intended_use == IntendedUse.HEALTH_SUPPLEMENT,
            lambda f: _is_fsdu_category(f.claims),
            lambda f: _medical_supervision_required(f),
        ],
        exclusions=[],
        required_evidence=["medical_purpose_evidence", "compositional_standards"]
    ),
]
```

#### Rule Set 7: Cosmetic (D&C Act Section 3(aaa))

```python
COSMETIC_RULES = [
    ClassificationRule(
        rule_id="FC-RULE-060",
        name="Cosmetic Definition - D&C Act Section 3(aaa)",
        formulation_class=FormulationClass.COSMETIC,
        legal_basis="Drugs & Cosmetics Act Section 3(aaa); Cosmetic Rules 2020",
        authority_tier=1,
        priority=90,
        conditions=[
            lambda f: f.intended_use == IntendedUse.COSMETIC,
            lambda f: f.dosage_form in [DosageForm.OINTMENT, DosageForm.OIL, DosageForm.POWDER, DosageForm.CREAM, DosageForm.LOTION],
            lambda f: _is_external_application_only(f),
            lambda f: _claims_permitted_cosmetic(f.claims),
        ],
        exclusions=[
            lambda f: f.intended_use == IntendedUse.THERAPEUTIC,
            lambda f: any(ing.is_scheduled_e1 for ing in f.ingredients),
        ],
        required_evidence=["external_use_only", "cosmetic_claims", "ingredient_safety"]
    ),
]
```

### 4.3 Rule Engine Execution

```python
class DeterministicRuleEngine:
    """
    Executes deterministic classification rules in priority order.
    Returns classification if single unambiguous match, otherwise returns conflicts.
    """
    
    def __init__(self):
        self.all_rules = (
            CLASSICAL_MEDICINE_RULES +
            GENERIC_MEDICINE_RULES +
            PATENT_PROPRIETARY_RULES +
            NEW_DRUG_RULES +
            AYURVEDA_AAHAR_RULES +
            NUTRACEUTICAL_RULES +
            COSMETIC_RULES
        )
        # Sort by priority (descending)
        self.all_rules.sort(key=lambda r: r.priority, reverse=True)
    
    def classify(self, formulation: FormulationInput) -> DeterministicResult:
        matches = []
        conflicts = []
        insufficient = []
        
        for rule in self.all_rules:
            result = rule.evaluate(formulation)
            if result == RuleResult.MATCH:
                matches.append(rule)
            elif result == RuleResult.CONFLICT:
                conflicts.append(rule)
            elif result == RuleResult.INSUFFICIENT_EVIDENCE:
                insufficient.append((rule, rule.required_evidence))
        
        # Conflict resolution
        if len(matches) == 1:
            return DeterministicResult(
                classification=matches[0].formulation_class,
                rule=matches[0],
                confidence=1.0,
                status="DETERMINISTIC_MATCH",
                evidence_matched=matches[0].required_evidence
            )
        
        elif len(matches) > 1:
            # Multiple matches - check if same class
            classes = set(m.formulation_class for m in matches)
            if len(classes) == 1:
                # Same class, multiple rules - take highest priority
                best_rule = max(matches, key=lambda r: r.priority)
                return DeterministicResult(
                    classification=best_rule.formulation_class,
                    rule=best_rule,
                    confidence=0.95,
                    status="DETERMINISTIC_MATCH_MULTI_RULE",
                    evidence_matched=best_rule.required_evidence
                )
            else:
                # Different classes - TRUE CONFLICT
                return DeterministicResult(
                    classification=None,
                    rule=None,
                    confidence=0.0,
                    status="DETERMINISTIC_CONFLICT",
                    conflicting_rules=matches,
                    missing_evidence=[e for _, e in insufficient]
                )
        
        else:
            # No deterministic match
            return DeterministicResult(
                classification=None,
                rule=None,
                confidence=0.0,
                status="NO_DETERMINISTIC_MATCH",
                missing_evidence=[e for _, e in insufficient]
            )

@dataclass
class DeterministicResult:
    classification: Optional[FormulationClass]
    rule: Optional[ClassificationRule]
    confidence: float
    status: str  # DETERMINISTIC_MATCH, DETERMINISTIC_MATCH_MULTI_RULE, DETERMINISTIC_CONFLICT, NO_DETERMINISTIC_MATCH
    evidence_matched: List[str] = field(default_factory=list)
    conflicting_rules: List[ClassificationRule] = field(default_factory=list)
    missing_evidence: List[List[str]] = field(default_factory=list)
```

---

## 5. LLM Reasoning for Borderline Cases

### 5.1 When LLM is Invoked

The LLM is invoked ONLY when deterministic engine returns:
- `DETERMINISTIC_CONFLICT` - Multiple rules match different classes
- `NO_DETERMINISTIC_MATCH` - No rule fully matches
- Evidence gaps that could be resolved with legal interpretation

### 5.2 LLM Reasoning Design

```python
class LLMReasoningEngine:
    """
    LLM-assisted classification for borderline cases.
    Uses retrieved legal evidence + formulation data.
    """
    
    def __init__(self, llm_client, retrieval_engine):
        self.llm = llm_client
        self.retrieval = retrieval_engine
    
    def reason(self, formulation: FormulationInput, 
               deterministic_result: DeterministicResult) -> LLMReasoningResult:
        
        # 1. Retrieve relevant legal evidence
        evidence = self._retrieve_evidence(formulation, deterministic_result)
        
        # 2. Build reasoning prompt
        prompt = self._build_reasoning_prompt(formulation, deterministic_result, evidence)
        
        # 3. Get LLM reasoning
        response = self.llm.generate_structured(prompt, LLMReasoningOutput)
        
        # 4. Validate LLM output against deterministic rules
        validated = self._validate_against_deterministic(response, deterministic_result)
        
        return validated
    
    def _retrieve_evidence(self, formulation: FormulationInput, 
                          det_result: DeterministicResult) -> List[Evidence]:
        queries = []
        
        # Query for each candidate class from conflicts
        if det_result.conflicting_rules:
            for rule in det_result.conflicting_rules:
                queries.append(f"classification criteria {rule.formulation_class.value} {rule.legal_basis}")
        
        # Query for specific ingredients
        for ing in formulation.ingredients:
            if ing.is_biological_resource:
                queries.append(f"ABS classification {ing.name} biological resource")
            if ing.is_scheduled_e1:
                queries.append(f"Schedule E(1) {ing.name} classification")
        
        # Query for preparation method
        if formulation.preparation_method:
            queries.append(f"{formulation.preparation_method.value} formulation classification")
        
        # Retrieve
        all_evidence = []
        for q in queries:
            results = self.retrieval.retrieve(q, top_k=5)
            all_evidence.extend(results)
        
        # Deduplicate by chunk_id
        return self._deduplicate_evidence(all_evidence)
    
    def _build_reasoning_prompt(self, formulation: FormulationInput,
                               det_result: DeterministicResult,
                               evidence: List[Evidence]) -> str:
        
        evidence_text = "\n\n".join([
            f"[Source: {e.source_id} | Authority: Tier {e.authority_tier} | Section: {e.section_ref}]\n{e.text}"
            for e in evidence
        ])
        
        conflict_info = ""
        if det_result.status == "DETERMINISTIC_CONFLICT":
            conflict_info = f"""
DETERMINISTIC CONFLICT DETECTED:
The following rules matched with DIFFERENT classifications:
{chr(10).join(f'- {r.rule_id}: {r.formulation_class.value} (basis: {r.legal_basis})' for r in det_result.conflicting_rules)}
"""
        elif det_result.status == "NO_DETERMINISTIC_MATCH":
            conflict_info = f"""
NO DETERMINISTIC MATCH:
Missing evidence for rules:
{chr(10).join(f'- {r.rule_id} ({r.formulation_class.value}): missing {ev}' for r, ev in det_result.missing_evidence)}
"""
        
        return f"""
You are a legal expert in Indian drug, food, cosmetic, and traditional medicine regulation.
Classify the following formulation based on Indian law.

FORMULATION:
- Product: {formulation.product_name}
- Ingredients: {', '.join(f"{i.name} ({i.quantity}{i.unit or ''})" for i in formulation.ingredients)}
- Dosage Form: {formulation.dosage_form.value if formulation.dosage_form else 'Not specified'}
- Preparation Method: {formulation.preparation_method.value if formulation.preparation_method else 'Not specified'}
- Intended Use: {formulation.intended_use.value if formulation.intended_use else 'Not specified'}
- Classical Formula Name: {formulation.classical_formula_name or 'None'}
- Traditional Text Reference: {formulation.traditional_text_reference or 'None'}
- Claims: {', '.join(formulation.claims) if formulation.claims else 'None'}

{conflict_info}

LEGAL EVIDENCE:
{evidence_text}

TASK:
1. Analyze which formulation class(es) apply based on the legal evidence
2. If deterministic rules conflict, explain WHICH rule takes precedence and WHY (cite specific legal hierarchy: Act > Rules > Guidelines)
3. If no deterministic match, determine the most appropriate class with reasoning
4. Identify any ABS (Access and Benefit Sharing) obligations under Biological Diversity Act 2002
5. Identify applicable licensing requirements

OUTPUT (JSON):
{{
  "classification": "CLASS_NAME",
  "reasoning": "Step-by-step legal reasoning citing specific provisions",
  "confidence": 0.0-1.0,
  "deterministic_override": false,  // MUST BE FALSE - LLM never overrides deterministic rules
  "applicable_regime": "D&C Act / FSSAI / AYUSH / etc.",
  "licensing_requirements": ["license1", "license2"],
  "abs_obligations": ["obligation1", "obligation2"],
  "key_evidence_citations": ["source_id:section_ref", ...],
  "uncertainties": ["uncertainty1", "uncertainty2"],
  "recommended_additional_evidence": ["evidence1", "evidence2"]
}}
"""
```

### 5.3 LLM Output Validation

```python
@dataclass
class LLMReasoningOutput:
    classification: str
    reasoning: str
    confidence: float
    deterministic_override: bool  # Must be false
    applicable_regime: str
    licensing_requirements: List[str]
    abs_obligations: List[str]
    key_evidence_citations: List[str]
    uncertainties: List[str]
    recommended_additional_evidence: List[str]

class LLMReasoningEngine:
    # ... (previous code)
    
    def _validate_against_deterministic(self, llm_output: LLMReasoningOutput,
                                        det_result: DeterministicResult) -> LLMReasoningResult:
        # CRITICAL: LLM must never override deterministic match
        if det_result.status in ["DETERMINISTIC_MATCH", "DETERMINISTIC_MATCH_MULTI_RULE"]:
            if llm_output.classification != det_result.classification.value:
                # Log violation, force deterministic result
                logger.warning(f"LLM attempted to override deterministic rule: {llm_output.classification} vs {det_result.classification}")
                return LLMReasoningResult(
                    classification=det_result.classification,
                    reasoning=f"Overrode LLM recommendation. Deterministic rule {det_result.rule.rule_id} takes precedence per legal hierarchy.",
                    confidence=det_result.confidence,
                    source="DETERMINISTIC_OVERRIDE",
                    validation_status="LLM_OVERRULED"
                )
        
        # For conflicts/no-match, validate LLM classification is legally plausible
        valid_classes = [c.value for c in FormulationClass]
        if llm_output.classification not in valid_classes:
            logger.error(f"LLM returned invalid classification: {llm_output.classification}")
            return LLMReasoningResult(
                classification=None,
                reasoning="LLM returned invalid classification",
                confidence=0.0,
                source="VALIDATION_FAILED",
                validation_status="INVALID_CLASS"
            )
        
        # Check if LLM classification conflicts with any deterministic EXCLUSION
        for rule in self.all_rules:
            if rule.formulation_class.value == llm_output.classification:
                for exclusion in rule.exclusions:
                    if exclusion(formulation):  # formulation from context
                        return LLMReasoningResult(
                            classification=None,
                            reasoning=f"LLM classification {llm_output.classification} violates exclusion in rule {rule.rule_id}",
                            confidence=0.0,
                            source="VALIDATION_FAILED",
                            validation_status="EXCLUSION_VIOLATION"
                        )
        
        return LLMReasoningResult(
            classification=FormulationClass(llm_output.classification),
            reasoning=llm_output.reasoning,
            confidence=llm_output.confidence,
            source="LLM_REASONING",
            validation_status="VALIDATED",
            applicable_regime=llm_output.applicable_regime,
            licensing_requirements=llm_output.licensing_requirements,
            abs_obligations=llm_output.abs_obligations,
            key_evidence_citations=llm_output.key_evidence_citations,
            uncertainties=llm_output.uncertainties,
            recommended_additional_evidence=llm_output.recommended_additional_evidence
        )
```

---

## 6. Confidence Calculation

### 6.1 Multi-Signal Confidence Model

```python
@dataclass
class ConfidenceSignals:
    # Deterministic signals
    rule_match_strength: float = 0.0      # 1.0 if perfect match, 0.5 if partial, 0 if no match
    rule_authority_tier: float = 0.0      # 1.0 for Tier 1, 0.8 for Tier 2, 0.6 for Tier 3
    evidence_completeness: float = 0.0    # Fraction of required evidence present
    
    # LLM signals (only if LLM invoked)
    llm_confidence: float = 0.0           # LLM's self-reported confidence
    llm_evidence_support: float = 0.0     # Fraction of LLM citations that are valid
    llm_deterministic_agreement: float = 0.0  # 1.0 if LLM agrees with deterministic, 0 if conflicts
    
    # Context signals
    ingredient_identification_quality: float = 0.0  # How well ingredients mapped to known DB
    traditional_text_verification: float = 0.0      # Classical text reference verified
    claim_consistency: float = 0.0                  # Claims consistent with class

class ConfidenceCalculator:
    """
    Computes final confidence from multiple signals.
    Weights configurable per deployment.
    """
    
    # Default weights (must sum to 1.0)
    WEIGHTS = {
        # Deterministic path
        "rule_match_strength": 0.35,
        "rule_authority_tier": 0.20,
        "evidence_completeness": 0.15,
        
        # LLM path (only used if LLM invoked)
        "llm_confidence": 0.10,
        "llm_evidence_support": 0.10,
        "llm_deterministic_agreement": 0.05,
        
        # Context
        "ingredient_identification_quality": 0.03,
        "traditional_text_verification": 0.02,
        "claim_consistency": 0.0,
    }
    
    def calculate(self, signals: ConfidenceSignals, 
                  path: str) -> float:
        """path: 'deterministic' or 'llm_assisted' """
        
        if path == "deterministic":
            # Only deterministic signals
            weights = {
                "rule_match_strength": 0.50,
                "rule_authority_tier": 0.30,
                "evidence_completeness": 0.20,
            }
        else:
            weights = self.WEIGHTS
        
        score = sum(
            getattr(signals, k) * w 
            for k, w in weights.items()
        )
        
        # Penalty for uncertainties
        if signals.llm_deterministic_agreement < 1.0 and path == "llm_assisted":
            score *= 0.9  # 10% penalty for LLM-deterministic disagreement
        
        return min(1.0, max(0.0, score))
```

### 6.2 Signal Computation

```python
def compute_signals(formulation: FormulationInput,
                   det_result: DeterministicResult,
                   llm_result: Optional[LLMReasoningResult],
                   evidence: List[Evidence]) -> ConfidenceSignals:
    
    signals = ConfidenceSignals()
    
    # Rule match strength
    if det_result.status.startswith("DETERMINISTIC_MATCH"):
        signals.rule_match_strength = 1.0
        signals.rule_authority_tier = det_result.rule.authority_tier / 4.0  # Normalize tier 1-4
        signals.evidence_completeness = len(det_result.evidence_matched) / max(1, len(det_result.rule.required_evidence))
    elif det_result.status == "DETERMINISTIC_CONFLICT":
        signals.rule_match_strength = 0.5  # Partial - multiple rules match
        signals.rule_authority_tier = max(r.authority_tier for r in det_result.conflicting_rules) / 4.0
        signals.evidence_completeness = 0.3
    else:
        signals.rule_match_strength = 0.0
        signals.rule_authority_tier = 0.0
        signals.evidence_completeness = 0.0
    
    # LLM signals
    if llm_result:
        signals.llm_confidence = llm_result.confidence
        signals.llm_evidence_support = _compute_evidence_support(llm_result.key_evidence_citations, evidence)
        signals.llm_deterministic_agreement = 1.0 if (
            det_result.classification and 
            llm_result.classification == det_result.classification
        ) else 0.0
    
    # Context signals
    signals.ingredient_identification_quality = _compute_ingredient_quality(formulation.ingredients)
    signals.traditional_text_verification = 1.0 if _verify_traditional_text(formulation) else 0.0
    signals.claim_consistency = _compute_claim_consistency(formulation, det_result.classification or llm_result.classification)
    
    return signals
```

---

## 7. Human Escalation System

### 7.1 Escalation Triggers

```python
class EscalationTrigger:
    """Evaluates whether human expert review is required."""
    
    TRIGGERS = [
        # Low confidence
        ("LOW_CONFIDENCE", lambda ctx: ctx.final_confidence < 0.6),
        
        # Deterministic conflict
        ("DETERMINISTIC_CONFLICT", lambda ctx: ctx.det_result.status == "DETERMINISTIC_CONFLICT"),
        
        # LLM-deterministic disagreement
        ("LLM_DETERMINISTIC_DISAGREEMENT", lambda ctx: 
            ctx.llm_result and ctx.det_result.classification and 
            ctx.llm_result.classification != ctx.det_result.classification),
        
        # Novel formulation (no similar in corpus)
        ("NOVEL_FORMULATION", lambda ctx: ctx.novelty_score > 0.8),
        
        # Scheduled/toxic ingredients
        ("SCHEDULED_INGREDIENT", lambda ctx: 
            any(ing.is_scheduled_e1 for ing in ctx.formulation.ingredients)),
        
        # High-value biological resource
        ("HIGH_VALUE_BIOLOGICAL_RESOURCE", lambda ctx:
            any(ing.is_biological_resource and ing.geographical_origin == "India" 
                for ing in ctx.formulation.ingredients)),
        
        # Therapeutic claims for food/cosmetic
        ("THERAPEUTIC_CLAIMS_NON_DRUG", lambda ctx:
            ctx.classification in [FormulationClass.NUTRACEUTICAL, FormulationClass.AYURVEDA_AAHAR, FormulationClass.COSMETIC] and
            any(_is_therapeutic_claim(c) for c in ctx.formulation.claims)),
        
        # Export to regulated markets
        ("EXPORT_REGULATED_MARKET", lambda ctx:
            any(c in ["USA", "EU", "Japan", "Canada", "Australia"] for c in ctx.formulation.export_countries)),
        
        # Multiple applicable regimes
        ("MULTI_REGIME_AMBIGUITY", lambda ctx: ctx.multi_regime_score > 0.7),
    ]
    
    def evaluate(self, context: EscalationContext) -> EscalationDecision:
        triggered = []
        for name, check in self.TRIGGERS:
            if check(context):
                triggered.append(name)
        
        if not triggered:
            return EscalationDecision(escalate=False, reasons=[])
        
        # Determine urgency
        urgency = "HIGH" if any(t in ["SCHEDULED_INGREDIENT", "HIGH_VALUE_BIOLOGICAL_RESOURCE", "THERAPEUTIC_CLAIMS_NON_DRUG"] for t in triggered) else "NORMAL"
        
        return EscalationDecision(
            escalate=True,
            reasons=triggered,
            urgency=urgency,
            recommended_expert=self._recommend_expert(triggered, context)
        )
    
    def _recommend_expert(self, triggers: List[str], context: EscalationContext) -> str:
        if "SCHEDULED_INGREDIENT" in triggers:
            return "D&C Act Specialist (Schedule E)"
        elif "HIGH_VALUE_BIOLOGICAL_RESOURCE" in triggers:
            return "NBA/ABS Expert"
        elif "THERAPEUTIC_CLAIMS_NON_DRUG" in triggers:
            return "FSSAI/AYUSH Regulatory Expert"
        elif "EXPORT_REGULATED_MARKET" in triggers:
            return "International Regulatory Affairs Specialist"
        elif "DETERMINISTIC_CONFLICT" in triggers:
            return "Senior Drug Regulatory Lawyer"
        else:
            return "General Regulatory Affairs Expert"
```

### 7.2 Escalation Workflow

```python
@dataclass
class EscalationContext:
    formulation: FormulationInput
    det_result: DeterministicResult
    llm_result: Optional[LLMReasoningResult]
    final_confidence: float
    classification: Optional[FormulationClass]
    novelty_score: float
    multi_regime_score: float

@dataclass
class EscalationDecision:
    escalate: bool
    reasons: List[str]
    urgency: str  # HIGH, NORMAL, LOW
    recommended_expert: str

class EscalationManager:
    def __init__(self, notification_service, expert_registry):
        self.notifications = notification_service
        self.experts = expert_registry
    
    def escalate(self, decision: EscalationDecision, context: EscalationContext) -> EscalationCase:
        case = EscalationCase(
            case_id=generate_id("ESC"),
            formulation=context.formulation,
            automated_classification=context.classification,
            automated_confidence=context.final_confidence,
            escalation_reasons=decision.reasons,
            urgency=decision.urgency,
            assigned_expert=decision.recommended_expert,
            status="PENDING",
            created_at=datetime.utcnow(),
            det_result=context.det_result,
            llm_result=context.llm_result
        )
        
        # Notify expert
        self.notifications.send_expert_notification(
            expert_id=decision.recommended_expert,
            case=case
        )
        
        # Log for audit
        self._audit_log(case)
        
        return case
    
    def resolve(self, case_id: str, expert_decision: ExpertDecision) -> ClassificationResult:
        case = self.get_case(case_id)
        case.expert_decision = expert_decision
        case.status = "RESOLVED"
        case.resolved_at = datetime.utcnow()
        
        # Update classification with expert decision
        return ClassificationResult(
            classification=expert_decision.classification,
            confidence=1.0,  # Expert decision = max confidence
            source="HUMAN_EXPERT",
            reasoning=expert_decision.reasoning,
            escalation_case=case,
            regulatory_output=self._build_regulatory_output(expert_decision.classification, context.formulation)
        )
```

---

## 8. Regulatory Output Generation

### 8.1 Output Schema

```python
@dataclass
class RegulatoryRequirement:
    requirement_type: str  # LICENSE, APPROVAL, NOTIFICATION, COMPLIANCE, ABS
    authority: str         # CDSCO, SLA, FSSAI, NBA, SBB, etc.
    regulation: str        # Specific regulation/rule
    description: str
    timeline: Optional[str] = None
    fees: Optional[str] = None
    forms: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)

@dataclass
class ClassificationResult:
    formulation_id: str
    classification: FormulationClass
    confidence: float
    source: str  # DETERMINISTIC, LLM_REASONING, HUMAN_EXPERT
    reasoning: str
    
    # Regulatory outputs
    applicable_regimes: List[str]           # ["D&C Act", "FSSAI", "Biological Diversity Act"]
    licensing_requirements: List[RegulatoryRequirement]
    abs_obligations: List[RegulatoryRequirement]
    labeling_requirements: List[RegulatoryRequirement]
    import_export_requirements: List[RegulatoryRequirement]
    
    # Traceability
    deterministic_rule: Optional[str] = None
    llm_evidence_citations: List[str] = field(default_factory=list)
    escalation_case: Optional[EscalationCase] = None
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    processed_at: datetime = field(default_factory=datetime.utcnow)
    engine_version: str = "1.0"
```

### 8.2 Regulatory Requirement Mapping

```python
REGULATORY_REQUIREMENTS = {
    FormulationClass.CLASSICAL_MEDICINE: {
        "licensing": [
            RegulatoryRequirement(
                requirement_type="LICENSE",
                authority="State Licensing Authority (AYUSH)",
                regulation="D&C Act; ASU Drugs Rules, Rule 158",
                description="Manufacturing license for ASU drugs",
                forms=["Form 24-D", "Form 25-D"],
                prerequisites=["GMP compliance", "Classical text reference", "Ingredient sourcing"]
            ),
        ],
        "abs": [
            RegulatoryRequirement(
                requirement_type="ABS",
                authority="National Biodiversity Authority / State Biodiversity Board",
                regulation="Biological Diversity Act 2002, ABS Rules 2014",
                description="Prior approval for commercial utilization of biological resources",
                prerequisites=["Form I (NBA)", "Form II (SBB)", "PIC/MAT"]
            ),
        ],
        "labeling": [
            RegulatoryRequirement(
                requirement_type="COMPLIANCE",
                authority="AYUSH Ministry",
                regulation="ASU Drugs Rules; Schedule E(1) labeling",
                description="Label must include: classical reference, ingredients, dosage, warnings"
            ),
        ],
    },
    
    FormulationClass.PHYTOPHARMACEUTICAL: {
        "licensing": [
            RegulatoryRequirement(
                requirement_type="APPROVAL",
                authority="CDSCO",
                regulation="D&C Act Section 12; Rule 122; Phytopharmaceutical Guidelines 2017",
                description="New drug approval via CT Rules 2019 pathway",
                forms=["Form CT-04", "Form CT-06"],
                prerequisites=["Standardized extract", "Marker compounds", "Preclinical data", "Clinical trial protocol"]
            ),
        ],
        "abs": [
            RegulatoryRequirement(
                requirement_type="ABS",
                authority="NBA",
                regulation="Biological Diversity Act 2002",
                description="ABS approval for biological resource access",
                prerequisites=["Form I", "Prior Informed Consent", "Mutually Agreed Terms"]
            ),
        ],
    },
    
    FormulationClass.AYURVEDA_AAHAR: {
        "licensing": [
            RegulatoryRequirement(
                requirement_type="LICENSE",
                authority="FSSAI (State/Central)",
                regulation="FSSAI Act 2006; Ayurveda-Aahar Regulations 2022",
                description="Food license for Ayurveda-Aahar manufacture/sale",
                forms=["FSSAI License/Registration"],
                prerequisites=["Food-grade ingredients", "Schedule claims only", "GMP/FSMS"]
            ),
        ],
        "labeling": [
            RegulatoryRequirement(
                requirement_type="COMPLIANCE",
                authority="FSSAI",
                regulation="Ayurveda-Aahar Regulations 2022, Schedule",
                description="Label: 'Ayurveda Aahar', classical reference, ingredients, 'Not a medicine' disclaimer"
            ),
        ],
    },
    
    FormulationClass.NUTRACEUTICAL: {
        "licensing": [
            RegulatoryRequirement(
                requirement_type="LICENSE",
                authority="FSSAI (Central)",
                regulation="FSSAI (Health Supplements, Nutraceuticals, FSDU, FSMP) Regulations 2016/2022",
                description="Central license for nutraceutical manufacture",
                prerequisites=["Permitted ingredients only", "RDA compliance", "No therapeutic claims"]
            ),
        ],
        "labeling": [
            RegulatoryRequirement(
                requirement_type="COMPLIANCE",
                authority="FSSAI",
                regulation="FSSAI Nutraceutical Regulations, Schedule I/II",
                description="Label: 'Health Supplement', 'Not for medicinal use', RDA %, ingredients"
            ),
        ],
    },
    
    FormulationClass.COSMETIC: {
        "licensing": [
            RegulatoryRequirement(
                requirement_type="LICENSE",
                authority="State Licensing Authority",
                regulation="D&C Act Section 3(aaa); Cosmetic Rules 2020",
                description="Cosmetic manufacturing license",
                forms=["Form COS-1", "Form COS-2"],
                prerequisites=["GMP", "Ingredient safety assessment", "No prohibited substances"]
            ),
        ],
        "labeling": [
            RegulatoryRequirement(
                requirement_type="COMPLIANCE",
                authority="CDSCO",
                regulation="Cosmetic Rules 2020, Rule 14",
                description="Label: ingredients, batch no, mfg/exp date, 'For external use only'"
            ),
        ],
    },
}
```

---

## 9. Complete Classification Pipeline

```python
class FormulationClassificationEngine:
    """
    Main orchestration engine for formulation classification.
    """
    
    def __init__(self, 
                 extractor: FormulationExtractor,
                 rule_engine: DeterministicRuleEngine,
                 llm_engine: LLMReasoningEngine,
                 confidence_calc: ConfidenceCalculator,
                 escalation_mgr: EscalationManager,
                 regulatory_mapper: RegulatoryMapper):
        self.extractor = extractor
        self.rule_engine = rule_engine
        self.llm_engine = llm_engine
        self.confidence = confidence_calc
        self.escalation = escalation_mgr
        self.regulatory = regulatory_mapper
    
    def classify(self, raw_input: str, language: str = "en",
                user_context: Optional[str] = None) -> ClassificationResult:
        
        # 1. Extract structured input
        formulation = self.extractor.extract(raw_input, language)
        formulation.user_context = user_context
        
        # 2. Run deterministic rules
        det_result = self.rule_engine.classify(formulation)
        
        # 3. LLM reasoning if needed
        llm_result = None
        if det_result.status in ["DETERMINISTIC_CONFLICT", "NO_DETERMINISTIC_MATCH"]:
            llm_result = self.llm_engine.reason(formulation, det_result)
        
        # 4. Determine final classification
        if det_result.status.startswith("DETERMINISTIC_MATCH"):
            final_class = det_result.classification
            source = "DETERMINISTIC"
            reasoning = f"Deterministic rule {det_result.rule.rule_id}: {det_result.rule.legal_basis}"
        elif llm_result and llm_result.validation_status == "VALIDATED":
            final_class = llm_result.classification
            source = "LLM_REASONING"
            reasoning = llm_result.reasoning
        else:
            # No clear path - escalate
            final_class = None
            source = "ESCALATION_REQUIRED"
            reasoning = "Insufficient evidence for automated classification"
        
        # 5. Compute confidence
        signals = compute_signals(formulation, det_result, llm_result, llm_result.evidence if llm_result else [])
        path = "deterministic" if source == "DETERMINISTIC" else "llm_assisted"
        final_confidence = self.confidence.calculate(signals, path)
        
        # 6. Check escalation
        esc_context = EscalationContext(
            formulation=formulation,
            det_result=det_result,
            llm_result=llm_result,
            final_confidence=final_confidence,
            classification=final_class,
            novelty_score=self._compute_novelty(formulation),
            multi_regime_score=self._compute_multi_regime(formulation, final_class)
        )
        esc_decision = self.escalation.trigger.evaluate(esc_context)
        
        if esc_decision.escalate:
            esc_case = self.escalation.escalate(esc_decision, esc_context)
            return ClassificationResult(
                formulation_id=formulation.product_name,
                classification=final_class,
                confidence=final_confidence,
                source=source,
                reasoning=reasoning,
                warnings=[f"ESCALATED: {', '.join(esc_decision.reasons)}"],
                escalation_case=esc_case
            )
        
        # 7. Build regulatory output
        regulatory_output = self.regulatory.map_requirements(final_class, formulation)
        
        return ClassificationResult(
            formulation_id=generate_id("FC"),
            classification=final_class,
            confidence=final_confidence,
            source=source,
            reasoning=reasoning,
            applicable_regimes=regulatory_output["regimes"],
            licensing_requirements=regulatory_output["licensing"],
            abs_obligations=regulatory_output["abs"],
            labeling_requirements=regulatory_output["labeling"],
            import_export_requirements=regulatory_output["import_export"],
            deterministic_rule=det_result.rule.rule_id if det_result.rule else None,
            llm_evidence_citations=llm_result.key_evidence_citations if llm_result else [],
            warnings=self._generate_warnings(formulation, final_class, det_result, llm_result)
        )
```

---

## 10. Multilingual Support

### 10.1 Language Processing

```python
class MultilingualFormulationProcessor:
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi",
        "bn": "Bengali",
        "te": "Telugu",
        "mr": "Marathi",
        "ta": "Tamil",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "or": "Odia",
        "as": "Assamese",
        "ur": "Urdu",
    }
    
    def __init__(self, translation_service, terminology_db):
        self.translator = translation_service
        self.terminology = terminology_db
    
    def process(self, input_text: str, language: str) -> FormulationInput:
        if language != "en":
            # Translate to English for processing
            english_text = self.translator.translate(input_text, language, "en")
        else:
            english_text = input_text
        
        # Extract with English prompt
        formulation = self.extractor.extract(english_text, "en")
        
        # Translate output back if needed
        formulation.original_language = language
        formulation.original_text = input_text
        
        return formulation
```

### 10.2 Terminology Preservation

Critical legal/technical terms must NOT be translated:
- Section numbers (Section 3(d), Rule 158)
- Schedule names (Schedule E(1), First Schedule)
- Latin botanical names
- Classical formula names (Triphala, Chyawanprash)
- Legal terms (bioequivalence, phytopharmaceutical, nutraceutical)

```python
PROTECTED_TERMS = {
    "en": [
        r"Section\s+\d+[A-Z]?(?:\([^)]+\))?",  # Section 3(d)
        r"Rule\s+\d+[A-Z]?",
        r"Schedule\s+[A-Z(][^)]+\)?",
        r"Form\s+\d+[A-Z]?",
        r"\b[A-Z]{2,}\d*\b",  # Abbreviations: CDSCO, FSSAI, NBA, ABS
        r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*",  # Proper nouns: Triphala, Chyawanprash
    ],
    # Add patterns for each Indian language
}
```

---

## 11. Versioning & Amendment Tracking

### 11.1 Rule Versioning

```python
@dataclass
class RuleVersion:
    rule_id: str
    version: int
    effective_from: date
    effective_to: Optional[date]
    rule: ClassificationRule
    amendment_source: str  # e.g., "D&C Amendment Act 2024"
    change_type: str       # "NEW", "MODIFIED", "REPEALED"
    
class RuleVersionManager:
    def __init__(self, graph_db):
        self.graph = graph_db
    
    def get_active_rules(self, as_of_date: date = None) -> List[ClassificationRule]:
        if as_of_date is None:
            as_of_date = date.today()
        
        query = """
        MATCH (r:ClassificationRule)-[:HAS_VERSION]->(v:RuleVersion)
        WHERE v.effective_from <= $date 
          AND (v.effective_to IS NULL OR v.effective_to >= $date)
          AND v.change_type != 'REPEALED'
        RETURN v ORDER BY v.priority DESC
        """
        return [self._deserialize(r) for r in self.graph.execute(query, {"date": as_of_date})]
    
    def add_amendment(self, amendment_act: LegalChunk):
        """Process amendment and create new rule versions."""
        changes = self._parse_amendment_for_rules(amendment_act)
        for change in changes:
            old_rule = self.get_rule(change.rule_id)
            new_version = RuleVersion(
                rule_id=change.rule_id,
                version=old_rule.version + 1,
                effective_from=amendment_act.effective_date,
                effective_to=None,
                rule=change.new_rule,
                amendment_source=amendment_act.act_id,
                change_type="MODIFIED"
            )
            # Mark old version as superseded
            self.graph.update(old_rule.version_id, {"effective_to": amendment_act.effective_date})
            self.graph.create(new_version)
```

---

## 12. Integration Points

### 12.1 With Query Analysis (Phase 3)

```python
# Classification feeds into Query Analysis
class QueryAnalysisInput:
    formulation_classification: Optional[ClassificationResult] = None
    
    def get_retrieval_hints(self) -> RetrievalHints:
        if not self.formulation_classification:
            return RetrievalHints()
        
        cls = self.formulation_classification.classification
        return RetrievalHints(
            preferred_jurisdictions=self._get_jurisdictions(cls),
            preferred_authority_tiers=self._get_authority_tiers(cls),
            required_sources=self._get_required_sources(cls),
            boost_terms=self._get_boost_terms(cls),
            filter_metadata=self._get_metadata_filters(cls)
        )
```

### 12.2 With Retrieval Engine (Phase 6)

```python
# Classification determines metadata filters for retrieval
CLASS_TO_METADATA_FILTER = {
    FormulationClass.CLASSICAL_MEDICINE: {
        "source_types": ["LEGISLATION", "RULE", "GUIDELINE"],
        "authority_tiers": [1, 2],
        "jurisdictions": ["INDIA"],
        "acts": ["Drugs and Cosmetics Act", "ASU Drugs Rules"],
        "schedules": ["First Schedule", "Schedule E(1)"]
    },
    FormulationClass.PHYTOPHARMACEUTICAL: {
        "source_types": ["LEGISLATION", "RULE", "GUIDELINE"],
        "authority_tiers": [1, 2],
        "jurisdictions": ["INDIA"],
        "acts": ["Drugs and Cosmetics Act", "D&C Rules"],
        "guidelines": ["CDSCO Phytopharmaceutical Guidelines 2017"]
    },
    FormulationClass.AYURVEDA_AAHAR: {
        "source_types": ["LEGISLATION", "REGULATION"],
        "authority_tiers": [1],
        "jurisdictions": ["INDIA"],
        "acts": ["FSSAI Act 2006"],
        "regulations": ["Ayurveda-Aahar Regulations 2022"]
    },
    # ... etc
}
```

### 12.3 With Knowledge Graph (Phase 7)

```python
# KG stores formulation classifications
# Query: "What regulations apply to my Triphala tablet?"
# → KG: (Formulation:Triphala)-[:CLASSIFIED_AS]->(Class:CLASSICAL_MEDICINE)
# → Retrieval: Filter by CLASSICAL_MEDICINE metadata
```

---

## 13. Evaluation Framework

### 13.1 Test Dataset Design

```python
@dataclass
class ClassificationTestCase:
    case_id: str
    formulation_input: FormulationInput
    expected_classification: FormulationClass
    expected_confidence_range: Tuple[float, float]
    expected_escalation: bool
    expected_regulatory_requirements: List[str]
    notes: str
    source: str  # "expert_annotated", "regulatory_precedent", "synthetic"

# Example test cases
TEST_CASES = [
    ClassificationTestCase(
        case_id="TC-001",
        formulation_input=FormulationInput(
            product_name="Triphala Tablets",
            ingredients=[Ingredient(name="Haritaki"), Ingredient(name="Bibhitaki"), Ingredient(name="Amalaki")],
            dosage_form=DosageForm.TABLET,
            preparation_method=PreparationMethod.CLASSICAL_TEXT,
            classical_formula_name="Triphala",
            traditional_text_reference="Charaka Samhita Chikitsa Sthana 5/12",
            intended_use=IntendedUse.THERAPEUTIC
        ),
        expected_classification=FormulationClass.CLASSICAL_MEDICINE,
        expected_confidence_range=(0.95, 1.0),
        expected_escalation=False,
        expected_regulatory_requirements=["ASU Manufacturing License", "Schedule E(1) compliance"],
        source="expert_annotated"
    ),
    
    ClassificationTestCase(
        case_id="TC-002",
        formulation_input=FormulationInput(
            product_name="Ashwagandha Extract Capsules",
            ingredients=[Ingredient(name="Withania somnifera", plant_part="root", quantity="500", unit="mg")],
            dosage_form=DosageForm.CAPSULE,
            preparation_method=PreparationMethod.EXTRACTION,
            intended_use=IntendedUse.HEALTH_SUPPLEMENT,
            claims=["stress relief", "immunity booster"]
        ),
        expected_classification=FormulationClass.NUTRACEUTICAL,  # Could also be Phytopharmaceutical
        expected_confidence_range=(0.6, 0.8),
        expected_escalation=True,  # Borderline
        expected_regulatory_requirements=["FSSAI License", "Possible CDSCO approval if therapeutic claims"],
        notes="Borderline: extraction + capsule + health claims. Could be nutraceutical or phytopharmaceutical",
        source="expert_annotated"
    ),
    
    ClassificationTestCase(
        case_id="TC-003",
        formulation_input=FormulationInput(
            product_name="New Molecule X Tablet",
            ingredients=[Ingredient(name="Compound X", scientific_name="Novel Chemical Entity")],
            dosage_form=DosageForm.TABLET,
            preparation_method=PreparationMethod.MODERN_PHARMA,
            intended_use=IntendedUse.THERAPEUTIC
        ),
        expected_classification=FormulationClass.NEW_DRUG,
        expected_confidence_range=(0.9, 1.0),
        expected_escalation=False,
        expected_regulatory_requirements=["CDSCO New Drug Approval", "CT Rules 2019 Clinical Trials"],
        source="regulatory_precedent"
    ),
]
```

### 13.2 Evaluation Metrics

| Metric | Target |
|--------|--------|
| **Deterministic Accuracy** | 100% on clear-cut cases (TC-001, TC-003 types) |
| **Borderline F1** | > 90% on expert-annotated borderline cases |
| **Escalation Precision** | < 5% false escalations |
| **Escalation Recall** | > 95% true ambiguous cases escalated |
| **Regulatory Output Completeness** | 100% of applicable requirements identified |
| **Latency (deterministic)** | < 2s p95 |
| **Latency (LLM-assisted)** | < 10s p95 |

---

## 14. Open Research Questions

| ID | Question | Status |
|----|----------|--------|
| ORQ-39 | Optimal confidence threshold for escalation (0.55 vs 0.6 vs 0.65)? | Experiment |
| ORQ-40 | How to handle formulations spanning multiple classes (e.g., food + cosmetic)? | Multi-label design |
| ORQ-41 | Can LLM reliably extract ingredient quantities from free text in Indian languages? | Need evaluation |
| ORQ-42 | Should classical formula matching use fuzzy matching or exact only? | Exact for legal certainty |
| ORQ-43 | How to validate "traditional text reference" claims automatically? | Link to TKDL/First Schedule DB |
| ORQ-44 | State-specific rule variations (e.g., State ASU Rules)? | Federal > State hierarchy |
| ORQ-45 | Integration with NBA's VAPs (Vulnerable/Endangered/Threatened) classification? | Real-time API needed |

---

## 15. Implementation Priority

| Component | Priority | Dependencies |
|-----------|----------|--------------|
| Input Extraction (English) | **CORE** | LLM API, Terminology DB |
| Deterministic Rule Engine | **CORE** | Legal rule corpus (Phase 4 ingestion) |
| Classical Formula DB (First Schedule) | **CORE** | Data entry / extraction from Acts |
| Schedule E(1) Ingredient DB | **CORE** | Data entry |
| LLM Reasoning Module | **CORE** | Retrieval Engine (Phase 6) |
| Confidence Calculator | **CORE** | - |
| Escalation System | **CORE** | Notification infrastructure |
| Regulatory Output Mapper | **CORE** | Legal requirements database |
| Multilingual Support | **OPTIONAL** | Translation service, Multilingual terminology |
| Rule Versioning | **OPTIONAL** | Amendment ingestion (Phase 4), KG (Phase 7) |
| ABS Integration | **OPTIONAL** | NBA database access, Biological Resource DB |

---

## 16. Summary

| Aspect | Decision |
|--------|----------|
| **Core Approach** | Deterministic rules first, LLM only for gaps/conflicts |
| **Legal Hierarchy** | Act > Rules > Guidelines > LLM reasoning |
| **Classes** | 8 primary classes covering Drugs, Food, Cosmetics, TK |
| **Escalation Threshold** | Confidence < 0.6 OR conflict OR scheduled ingredient |
| **LLM Constraint** | NEVER overrides deterministic match |
| **Output** | Classification + Regulatory requirements + Traceability |
| **Integration** | Feeds Query Analysis (Phase 3), Retrieval Filters (Phase 6), KG (Phase 7) |

---

## 17. Next Phase: Phase 9 - Jurisdiction Engine

Phase 9 will design the **Jurisdiction Engine** that:
- Explicitly handles jurisdiction (India, EU, USA, Japan, International, PCT, WIPO, etc.)
- Determines applicable authority/regime per jurisdiction
- Handles temporal validity of laws
- Resolves conflicts between regimes
- **Never allows silent jurisdiction mixing** (hard isolation enforced)

The formulation classification output feeds directly into jurisdiction determination (e.g., Classical Medicine → India D&C Act jurisdiction; PCT application → WIPO jurisdiction).