"""
IP-SAKTI Formulation Classification
Phase 14: Implements the formulation classification system for IP documents.
Classifies documents by IP type, legal category, and technical domain.
"""

import logging
import re
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
    FormulationType,
    Jurisdiction,
    TechnicalDomain,
)

logger = logging.getLogger(__name__)


class ClassificationMethod(str, Enum):
    """Classification methods."""
    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"
    LLM_BASED = "llm_based"
    HYBRID = "hybrid"


@dataclass
class ClassificationConfig:
    """Configuration for classification."""
    method: ClassificationMethod = ClassificationMethod.HYBRID
    confidence_threshold: float = 0.7
    enable_technical_domain: bool = True
    enable_formulation_type: bool = True
    enable_jurisdiction: bool = True
    ml_model_path: Optional[str] = None
    llm_model: str = "gpt-4"


@dataclass
class ClassificationResult:
    """Result of document classification."""
    document_id: str
    document_type: DocumentType
    formulation_type: Optional[FormulationType] = None
    technical_domains: List[TechnicalDomain] = field(default_factory=list)
    jurisdiction: Optional[Jurisdiction] = None
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    classified_at: datetime = field(default_factory=datetime.utcnow)


class Classifier(ABC):
    """Abstract base classifier."""
    
    @abstractmethod
    async def classify(self, document: Document) -> ClassificationResult:
        pass


class RuleBasedDocumentTypeClassifier(Classifier):
    """Rule-based document type classification."""
    
    # Document type patterns
    PATTERNS = {
        DocumentType.PATENT: [
            r'\bpatent\b',
            r'\binvention\b',
            r'\bclaims?\b',
            r'\bprior\s+art\b',
            r'\bpatent\s+application\b',
            r'\b(?:US|EP|WO|IN|CN|JP|KR|DE|GB|FR)\d{7,12}[A-Z]?\b',
            r'\b(?:IPC|CPC)\s*[:=]\s*[A-H]\d{2}[A-Z]',
        ],
        DocumentType.TRADEMARK: [
            r'\btrademark\b',
            r'\btrade\s*mark\b',
            r'\bmark\b',
            r'\brand\b',
            r'\b(?:TM|®|SM)\b',
            r'\blikelihood\s+of\s+confusion\b',
            r'\bdistinctive(?:ness)?\b',
            r'\bnice\s+classification\b',
        ],
        DocumentType.COPYRIGHT: [
            r'\bcopyright\b',
            r'\bwork\s+of\s+authorship\b',
            r'\bauthor\b',
            r'\binfringement\b',
            r'\bfair\s+use\b',
            r'\bderivative\s+work\b',
            r'\bmoral\s+rights\b',
        ],
        DocumentType.DESIGN: [
            r'\bdesign\b',
            r'\bappearance\b',
            r'\bvisual\s+features\b',
            r'\bornamental\b',
            r'\baesthetic\b',
            r'\bdesign\s+patent\b',
        ],
        DocumentType.CASE_LAW: [
            r'\bv\.\s+[A-Z]',
            r'\bcase\s+law\b',
            r'\bprecedent\b',
            r'\bjudgment\b',
            r'\bruling\b',
            r'\bopinion\b',
            r'\bdissent\b',
            r'\bconcurrence\b',
            r'\b\d{4}\s+[A-Z]+\s+\d+\b',  # Case citation format
        ],
        DocumentType.STATUTE: [
            r'\bstatute\b',
            r'\bact\b',
            r'\blegislation\b',
            r'\bsection\s+\d+',
            r'\barticle\s+\d+',
            r'\bchapter\s+\d+',
            r'\bpublic\s+law\b',
        ],
        DocumentType.REGULATION: [
            r'\bregulation\b',
            r'\brule\b',
            r'\badministrative\s+code\b',
            r'\bCFR\b',
            r'\bFederal\s+Register\b',
        ],
        DocumentType.TREATY: [
            r'\btreaty\b',
            r'\bconvention\b',
            r'\bagreement\b',
            r'\bprotocol\b',
            r'\bPCT\b',
            r'\bParis\s+Convention\b',
            r'\bBerne\s+Convention\b',
            r'\bTRIPS\b',
        ],
        DocumentType.LEGAL_OPINION: [
            r'\blegal\s+opinion\b',
            r'\bmemorandum\b',
            r'\badvice\b',
            r'\bcounsel\b',
            r'\battorney\s+opinion\b',
        ],
        DocumentType.SCHOLARLY_ARTICLE: [
            r'\babstract\b',
            r'\bkeywords\b',
            r'\bdoi\b',
            r'\bjournal\b',
            r'\bvolume\s+\d+\b',
            r'\bissue\s+\d+\b',
            r'\bpages?\s+\d+\s*-\s*\d+\b',
        ],
    }
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.compiled_patterns = {
            doc_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for doc_type, patterns in self.PATTERNS.items()
        }
    
    async def classify(self, document: Document) -> ClassificationResult:
        text = document.content or ""
        metadata = document.metadata
        
        # Score each document type
        scores = {}
        for doc_type, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(pattern.findall(text))
                score += matches
            scores[doc_type] = score
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            normalized = {k: v / total for k, v in scores.items()}
        else:
            normalized = {k: 0.0 for k in scores}
        
        # Get best match
        best_type = max(normalized, key=normalized.get)
        confidence = normalized[best_type]
        
        # Check if we have explicit metadata
        if metadata.document_type and metadata.document_type != DocumentType.OTHER:
            best_type = metadata.document_type
            confidence = max(confidence, 0.9)
        
        return ClassificationResult(
            document_id=document.id,
            document_type=best_type,
            confidence_scores={'document_type': confidence},
            metadata={'method': 'rule_based', 'all_scores': normalized},
        )


class RuleBasedFormulationClassifier(Classifier):
    """Rule-based formulation type classification."""
    
    FORMULATION_PATTERNS = {
        FormulationType.CLAIM: [
            r'\bclaim\s+\d+\b',
            r'\bclaims?\b',
            r'\bwhat\s+is\s+claimed\b',
            r'\bwe\s+claim\b',
            r'\bthe\s+invention\s+claimed\b',
        ],
        FormulationType.ABSTRACT: [
            r'\babstract\b',
            r'\bsummary\s+of\s+the\s+invention\b',
            r'\bbrief\s+summary\b',
        ],
        FormulationType.DESCRIPTION: [
            r'\bdetailed\s+description\b',
            r'\bdescription\s+of\s+the\s+invention\b',
            r'\bembodiment\b',
            r'\bpreferred\s+embodiment\b',
        ],
        FormulationType.DRAWINGS: [
            r'\bbrief\s+description\s+of\s+(?:the\s+)?drawings?\b',
            r'\bfigure\s+\d+\b',
            r'\bfig\.\s*\d+\b',
            r'\bdrawing\b',
        ],
        FormulationType.BACKGROUND: [
            r'\bbackground\s+(?:of\s+the\s+)?invention\b',
            r'\btechnical\s+field\b',
            r'\bstate\s+of\s+the\s+art\b',
            r'\bprior\s+art\b',
        ],
        FormulationType.SUMMARY: [
            r'\bsummary\s+of\s+the\s+invention\b',
            r'\bsummary\b',
            r'\bobject\s+of\s+the\s+invention\b',
        ],
    }
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.compiled_patterns = {
            ftype: [re.compile(p, re.IGNORECASE) for p in patterns]
            for ftype, patterns in self.FORMULATION_PATTERNS.items()
        }
    
    async def classify(self, document: Document) -> ClassificationResult:
        text = document.content or ""
        
        scores = {}
        for ftype, patterns in self.compiled_patterns.items():
            score = sum(len(p.findall(text)) for p in patterns)
            scores[ftype] = score
        
        total = sum(scores.values())
        if total > 0:
            normalized = {k: v / total for k, v in scores.items()}
        else:
            normalized = {k: 0.0 for k in scores}
        
        best_type = max(normalized, key=normalized.get)
        confidence = normalized[best_type]
        
        return ClassificationResult(
            document_id=document.id,
            document_type=document.metadata.document_type,
            formulation_type=best_type if confidence > self.config.confidence_threshold else None,
            confidence_scores={'formulation_type': confidence},
            metadata={'method': 'rule_based', 'all_scores': normalized},
        )


class TechnicalDomainClassifier(Classifier):
    """Classify technical domain of IP documents."""
    
    DOMAIN_KEYWORDS = {
        TechnicalDomain.MECHANICAL: [
            'mechanical', 'machine', 'engine', 'gear', 'shaft', 'bearing', 'piston',
            'valve', 'pump', 'compressor', 'turbine', 'mechanism', 'lever', 'cam',
            'clutch', 'brake', 'transmission', 'suspension', 'chassis', 'frame',
        ],
        TechnicalDomain.ELECTRICAL: [
            'electrical', 'electronic', 'circuit', 'voltage', 'current', 'power',
            'transformer', 'capacitor', 'inductor', 'resistor', 'diode', 'transistor',
            'pcb', 'printed circuit', 'wiring', 'connector', 'switch', 'relay',
        ],
        TechnicalDomain.CHEMICAL: [
            'chemical', 'compound', 'molecule', 'polymer', 'catalyst', 'reaction',
            'synthesis', 'formulation', 'composition', 'pharmaceutical', 'drug',
            'medicament', 'therapeutic', 'active ingredient', 'excipient',
        ],
        TechnicalDomain.BIOTECHNOLOGY: [
            'biotech', 'biotechnology', 'gene', 'protein', 'enzyme', 'antibody',
            'dna', 'rna', 'pcr', 'sequencing', 'cell', 'tissue', 'organism',
            'genetic', 'genome', 'crispr', 'vector', 'plasmid', 'expression',
        ],
        TechnicalDomain.COMPUTER_SOFTWARE: [
            'software', 'algorithm', 'program', 'code', 'application', 'app',
            'database', 'network', 'server', 'client', 'api', 'interface',
            'machine learning', 'artificial intelligence', 'neural network',
            'deep learning', 'blockchain', 'cryptocurrency', 'smart contract',
        ],
        TechnicalDomain.PHARMACEUTICAL: [
            'pharmaceutical', 'drug', 'medicine', 'therapeutic', 'treatment',
            'dosage', 'formulation', 'delivery', 'bioavailability', 'pharmacokinetics',
            'clinical trial', 'fda', 'ema', 'approval', 'indication',
        ],
        TechnicalDomain.MATERIALS: [
            'material', 'alloy', 'composite', 'ceramic', 'metal', 'polymer',
            'coating', 'surface', 'nanoparticle', 'nanomaterial', 'graphene',
            'carbon fiber', 'tensile', 'hardness', 'conductivity',
        ],
        TechnicalDomain.TELECOMMUNICATIONS: [
            'telecommunication', 'wireless', 'cellular', '5g', '4g', 'lte',
            'wifi', 'bluetooth', 'antenna', 'signal', 'modulation', 'frequency',
            'bandwidth', 'spectrum', 'channel', 'protocol', 'packet',
        ],
        TechnicalDomain.AUTOMOTIVE: [
            'automotive', 'vehicle', 'car', 'truck', 'automobile', 'engine',
            'transmission', 'chassis', 'suspension', 'brake', 'steering',
            'electric vehicle', 'hybrid', 'autonomous', 'adas',
        ],
        TechnicalDomain.AEROSPACE: [
            'aerospace', 'aircraft', 'airplane', 'jet', 'rocket', 'satellite',
            'propulsion', 'aerodynamic', 'avionics', 'flight', 'airframe',
            'turbine', 'compressor', 'combustor', 'nozzle',
        ],
        TechnicalDomain.ENERGY: [
            'energy', 'power', 'solar', 'wind', 'battery', 'fuel cell',
            'renewable', 'grid', 'inverter', 'converter', 'storage',
            'photovoltaic', 'turbine', 'generator', 'distribution',
        ],
        TechnicalDomain.ENVIRONMENTAL: [
            'environmental', 'pollution', 'waste', 'water treatment', 'air quality',
            'recycling', 'sustainability', 'carbon', 'emission', 'green',
            'circular economy', 'biodegradable', 'remediation',
        ],
    }
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        # Compile keywords for faster matching
        self.domain_keywords = {
            domain: [kw.lower() for kw in keywords]
            for domain, keywords in self.DOMAIN_KEYWORDS.items()
        }
    
    async def classify(self, document: Document) -> ClassificationResult:
        text = (document.content or "").lower()
        
        scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(text.count(kw) for kw in keywords)
            scores[domain] = score
        
        # Get top domains
        sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_domains = [d for d, s in sorted_domains if s > 0][:3]
        
        confidence = scores[top_domains[0]] / max(sum(scores.values()), 1) if top_domains else 0.0
        
        return ClassificationResult(
            document_id=document.id,
            document_type=document.metadata.document_type,
            technical_domains=top_domains,
            confidence_scores={'technical_domain': confidence},
            metadata={'method': 'keyword_based', 'all_scores': {d.value: s for d, s in scores.items()}},
        )


class JurisdictionClassifier(Classifier):
    """Classify jurisdiction of IP documents."""
    
    JURISDICTION_KEYWORDS = {
        Jurisdiction.US: [
            'uspto', 'united states', 'america', 'federal circuit', 'supreme court',
            'district court', 'ptab', 'cafc', 'usc', 'cfr', 'american',
        ],
        Jurisdiction.EP: [
            'epo', 'european patent office', 'european', 'ep patent', 'european patent',
            'epc', 'european patent convention', 'munich', 'the hague',
        ],
        Jurisdiction.WO: [
            'wipo', 'pct', 'international application', 'world intellectual property',
            'international search', 'international preliminary examination',
        ],
        Jurisdiction.IN: [
            'india', 'indian', 'ipab', 'controller of patents', 'delhi high court',
            'supreme court of india', 'indian patent office', 'mumbai', 'chennai',
            'kolkata', 'new delhi',
        ],
        Jurisdiction.CN: [
            'china', 'chinese', 'cnipa', 'sipo', 'beijing', 'shanghai',
            'chinese patent office',
        ],
        Jurisdiction.JP: [
            'japan', 'japanese', 'jpo', 'japan patent office', 'tokyo',
        ],
        Jurisdiction.UK: [
            'uk', 'united kingdom', 'ukipo', 'ewhc', 'ewca', 'british',
            'london', 'cardiff',
        ],
        Jurisdiction.DE: [
            'germany', 'german', 'dpma', 'bundespatentgericht', 'munich',
        ],
        Jurisdiction.FR: [
            'france', 'french', 'inpi', 'paris',
        ],
        Jurisdiction.KR: [
            'korea', 'korean', 'kipris', 'kipo', 'seoul',
        ],
    }
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.jurisdiction_keywords = {
            jur: [kw.lower() for kw in keywords]
            for jur, keywords in self.JURISDICTION_KEYWORDS.items()
        }
    
    async def classify(self, document: Document) -> ClassificationResult:
        text = (document.content or "").lower()
        
        scores = {}
        for jur, keywords in self.jurisdiction_keywords.items():
            score = sum(text.count(kw) for kw in keywords)
            scores[jur] = score
        
        # Check explicit metadata
        if document.metadata.jurisdiction and document.metadata.jurisdiction != Jurisdiction.UNKNOWN:
            return ClassificationResult(
                document_id=document.id,
                document_type=document.metadata.document_type,
                jurisdiction=document.metadata.jurisdiction,
                confidence_scores={'jurisdiction': 0.95},
                metadata={'method': 'metadata', 'source': 'explicit'},
            )
        
        sorted_jurs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_jur = sorted_jurs[0][0] if sorted_jurs[0][1] > 0 else Jurisdiction.UNKNOWN
        confidence = sorted_jurs[0][1] / max(sum(scores.values()), 1) if sorted_jurs[0][1] > 0 else 0.0
        
        return ClassificationResult(
            document_id=document.id,
            document_type=document.metadata.document_type,
            jurisdiction=best_jur,
            confidence_scores={'jurisdiction': confidence},
            metadata={'method': 'keyword_based', 'all_scores': {j.value: s for j, s in scores.items()}},
        )


class MLClassifier(Classifier):
    """ML-based classifier (placeholder for actual model)."""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.model = None  # Would load actual model
    
    async def classify(self, document: Document) -> ClassificationResult:
        # Placeholder - would use actual ML model
        # For now, return low confidence
        return ClassificationResult(
            document_id=document.id,
            document_type=document.metadata.document_type,
            confidence_scores={'ml': 0.5},
            metadata={'method': 'ml', 'note': 'placeholder'},
        )


class LLMClassifier(Classifier):
    """LLM-based classifier (placeholder for actual LLM call)."""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.model = config.llm_model
    
    async def classify(self, document: Document) -> ClassificationResult:
        # Placeholder - would call LLM
        return ClassificationResult(
            document_id=document.id,
            document_type=document.metadata.document_type,
            confidence_scores={'llm': 0.8},
            metadata={'method': 'llm', 'model': self.model, 'note': 'placeholder'},
        )


class HybridClassifier(Classifier):
    """Hybrid classifier combining multiple methods."""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.rule_based = RuleBasedDocumentTypeClassifier(config)
        self.formulation_classifier = RuleBasedFormulationClassifier(config)
        self.domain_classifier = TechnicalDomainClassifier(config)
        self.jurisdiction_classifier = JurisdictionClassifier(config)
        self.ml_classifier = MLClassifier(config)
        self.llm_classifier = LLMClassifier(config)
    
    async def classify(self, document: Document) -> ClassificationResult:
        # Run all classifiers
        results = await asyncio.gather(
            self.rule_based.classify(document),
            self.formulation_classifier.classify(document),
            self.domain_classifier.classify(document),
            self.jurisdiction_classifier.classify(document),
        )
        
        doc_type_result, formulation_result, domain_result, jur_result = results
        
        # Combine confidence scores
        confidence_scores = {}
        confidence_scores.update(doc_type_result.confidence_scores)
        confidence_scores.update(formulation_result.confidence_scores)
        confidence_scores.update(domain_result.confidence_scores)
        confidence_scores.update(jur_result.confidence_scores)
        
        # Use rule-based for document type (most reliable)
        final_doc_type = doc_type_result.document_type
        final_formulation = formulation_result.formulation_type
        final_domains = domain_result.technical_domains
        final_jurisdiction = jur_result.jurisdiction
        
        # If ML/LLM available and confidence low, could use them as tiebreaker
        if confidence_scores.get('document_type', 0) < self.config.confidence_threshold:
            ml_result = await self.ml_classifier.classify(document)
            llm_result = await self.llm_classifier.classify(document)
            # Could implement ensemble logic here
        
        return ClassificationResult(
            document_id=document.id,
            document_type=final_doc_type,
            formulation_type=final_formulation,
            technical_domains=final_domains,
            jurisdiction=final_jurisdiction,
            confidence_scores=confidence_scores,
            metadata={
                'method': 'hybrid',
                'components': {
                    'document_type': doc_type_result.metadata,
                    'formulation_type': formulation_result.metadata,
                    'technical_domain': domain_result.metadata,
                    'jurisdiction': jur_result.metadata,
                },
            },
        )


class FormulationClassificationPipeline:
    """Pipeline for classifying document formulations."""
    
    def __init__(self, config: Optional[ClassificationConfig] = None, settings: Optional[Settings] = None):
        self.config = config or ClassificationConfig()
        self.settings = settings or get_settings()
        self.classifier = self._create_classifier()
    
    def _create_classifier(self) -> Classifier:
        if self.config.method == ClassificationMethod.RULE_BASED:
            return RuleBasedDocumentTypeClassifier(self.config)
        elif self.config.method == ClassificationMethod.ML_BASED:
            return MLClassifier(self.config)
        elif self.config.method == ClassificationMethod.LLM_BASED:
            return LLMClassifier(self.config)
        else:
            return HybridClassifier(self.config)
    
    async def classify_document(self, document: Document) -> ClassificationResult:
        """Classify a single document."""
        return await self.classifier.classify(document)
    
    async def classify_batch(self, documents: List[Document]) -> List[ClassificationResult]:
        """Classify multiple documents."""
        return await asyncio.gather(*[self.classify_document(doc) for doc in documents])
    
    async def classify_chunks(self, chunks: List[DocumentChunk]) -> List[ClassificationResult]:
        """Classify document chunks (for formulation type within documents)."""
        results = []
        for chunk in chunks:
            # Create a pseudo-document for chunk
            pseudo_doc = Document(
                id=chunk.id,
                content=chunk.content,
                metadata=chunk.metadata,
            )
            result = await self.classifier.classify(pseudo_doc)
            results.append(result)
        return results


class FormulationDetector:
    """Detect formulation types within document sections."""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.classifier = RuleBasedFormulationClassifier(config)
    
    async def detect_formulations(
        self,
        document: Document,
    ) -> Dict[str, List[Tuple[int, int, FormulationType]]]:
        """Detect formulation types in document sections.
        
        Returns dict of section_name -> list of (start, end, formulation_type)
        """
        formulations = {}
        
        # Split document into sections
        sections = self._split_sections(document.content or "")
        
        for section_name, section_text, start, end in sections:
            pseudo_doc = Document(
                id=document.id,
                content=section_text,
                metadata=document.metadata,
            )
            result = await self.classifier.classify(pseudo_doc)
            
            if result.formulation_type and result.confidence_scores.get('formulation_type', 0) > self.config.confidence_threshold:
                if section_name not in formulations:
                    formulations[section_name] = []
                formulations[section_name].append((start, end, result.formulation_type))
        
        return formulations
    
    def _split_sections(self, text: str) -> List[Tuple[str, str, int, int]]:
        """Split text into sections with positions."""
        sections = []
        lines = text.split('\n')
        current_section = "unknown"
        current_content = []
        section_start = 0
        char_pos = 0
        
        section_headers = {
            'abstract': ['abstract'],
            'background': ['background', 'background of the invention'],
            'summary': ['summary', 'summary of the invention', 'object of the invention'],
            'description': ['detailed description', 'description of the invention', 'description'],
            'claims': ['claims', 'what is claimed', 'we claim'],
            'drawings': ['brief description of the drawings', 'drawings', 'figures'],
        }
        
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            
            # Check for section header
            matched_section = None
            for section, headers in section_headers.items():
                for header in headers:
                    if line_lower.startswith(header) or line_lower == header:
                        matched_section = section
                        break
                if matched_section:
                    break
            
            if matched_section:
                # Save previous section
                if current_content:
                    content = '\n'.join(current_content)
                    sections.append((current_section, content, section_start, char_pos - len(content)))
                
                current_section = matched_section
                current_content = [line]
                section_start = char_pos
            else:
                current_content.append(line)
            
            char_pos += len(line) + 1  # +1 for newline
        
        # Save last section
        if current_content:
            content = '\n'.join(current_content)
            sections.append((current_section, content, section_start, char_pos))
        
        return sections


def create_classification_pipeline(
    method: ClassificationMethod = ClassificationMethod.HYBRID,
    confidence_threshold: float = 0.7,
    **kwargs
) -> FormulationClassificationPipeline:
    """Factory to create classification pipeline."""
    config = ClassificationConfig(
        method=method,
        confidence_threshold=confidence_threshold,
        **kwargs
    )
    return FormulationClassificationPipeline(config)