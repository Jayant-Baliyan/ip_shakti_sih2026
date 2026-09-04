"""
IP-SAKTI Jurisdiction Engine
Phase 15: Implements the jurisdiction engine for multi-jurisdiction IP analysis.
Handles jurisdiction-specific laws, procedures, and cross-jurisdiction analysis.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from ip_sakti.config.loader import Settings, get_settings
from ip_sakti.core.models import (
    Document,
    DocumentChunk,
    DocumentType,
    Jurisdiction,
    JurisdictionRule,
    LegalProvision,
    PatentOffice,
    ProcedureStep,
    ProcedureTimeline,
)
from ip_sakti.classification.formulation import JurisdictionClassifier, ClassificationConfig

logger = logging.getLogger(__name__)


class JurisdictionEngineMode(str, Enum):
    """Jurisdiction engine operating modes."""
    SINGLE = "single"          # Single jurisdiction analysis
    COMPARATIVE = "comparative"  # Compare across jurisdictions
    HARMONIZATION = "harmonization"  # Find harmonized provisions
    FTO = "freedom_to_operate"    # Freedom to operate analysis
    VALIDITY = "validity"          # Validity challenge analysis


@dataclass
class JurisdictionConfig:
    """Configuration for jurisdiction engine."""
    default_jurisdiction: Jurisdiction = Jurisdiction.US
    supported_jurisdictions: List[Jurisdiction] = field(default_factory=lambda: [
        Jurisdiction.US, Jurisdiction.EP, Jurisdiction.WO,
        Jurisdiction.IN, Jurisdiction.CN, Jurisdiction.JP,
        Jurisdiction.UK, Jurisdiction.DE, Jurisdiction.FR,
        Jurisdiction.KR, Jurisdiction.CA, Jurisdiction.AU,
    ])
    enable_procedural_timelines: bool = True
    enable_legal_provisions: bool = True
    enable_office_actions: bool = True
    cache_ttl_hours: int = 24


@dataclass
class JurisdictionAnalysisResult:
    """Result of jurisdiction analysis."""
    jurisdiction: Jurisdiction
    document_id: str
    applicable_provisions: List[LegalProvision] = field(default_factory=list)
    procedural_timeline: Optional[ProcedureTimeline] = None
    office_actions: List[Dict[str, Any]] = field(default_factory=list)
    key_differences: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComparativeAnalysisResult:
    """Result of comparative jurisdiction analysis."""
    base_jurisdiction: Jurisdiction
    comparison_jurisdictions: List[Jurisdiction]
    document_id: str
    provision_comparison: Dict[str, Dict[Jurisdiction, LegalProvision]] = field(default_factory=dict)
    procedural_comparison: Dict[str, Any] = field(default_factory=dict)
    harmonization_opportunities: List[str] = field(default_factory=list)
    divergence_points: List[str] = field(default_factory=list)
    strategic_recommendations: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


class LegalProvisionStore(ABC):
    """Abstract base for legal provision storage."""
    
    @abstractmethod
    async def get_provisions(
        self,
        jurisdiction: Jurisdiction,
        document_type: DocumentType,
        topic: Optional[str] = None,
    ) -> List[LegalProvision]:
        pass
    
    @abstractmethod
    async def get_provision(
        self,
        jurisdiction: Jurisdiction,
        provision_id: str,
    ) -> Optional[LegalProvision]:
        pass
    
    @abstractmethod
    async def search_provisions(
        self,
        query: str,
        jurisdictions: List[Jurisdiction],
        document_type: Optional[DocumentType] = None,
    ) -> List[LegalProvision]:
        pass


class InMemoryProvisionStore(LegalProvisionStore):
    """In-memory legal provision store with built-in IP law data."""
    
    def __init__(self):
        self.provisions: Dict[str, LegalProvision] = {}
        self._load_builtin_provisions()
    
    def _load_builtin_provisions(self) -> None:
        """Load built-in IP law provisions for major jurisdictions."""
        # This would normally be loaded from a database
        # Here we define key provisions for major jurisdictions
        
        provisions_data = [
            # US Patent Law
            {
                'id': 'us_35_101',
                'jurisdiction': Jurisdiction.US,
                'document_type': DocumentType.STATUTE,
                'title': '35 U.S.C. § 101 - Inventions Patentable',
                'text': 'Whoever invents or discovers any new and useful process, machine, manufacture, or composition of matter, or any new and useful improvement thereof, may obtain a patent therefor, subject to the conditions and requirements of this title.',
                'topic': 'patentable_subject_matter',
                'hierarchy_level': 1,
            },
            {
                'id': 'us_35_102',
                'jurisdiction': Jurisdiction.US,
                'document_type': DocumentType.STATUTE,
                'title': '35 U.S.C. § 102 - Conditions for Patentability; Novelty',
                'text': 'A person shall be entitled to a patent unless the claimed invention was patented, described in a printed publication, or in public use, on sale, or otherwise available to the public before the effective filing date of the claimed invention.',
                'topic': 'novelty',
                'hierarchy_level': 1,
            },
            {
                'id': 'us_35_103',
                'jurisdiction': Jurisdiction.US,
                'document_type': DocumentType.STATUTE,
                'title': '35 U.S.C. § 103 - Conditions for Patentability; Non-obviousness',
                'text': 'A patent for a claimed invention may not be obtained if the differences between the claimed invention and the prior art are such that the claimed invention as a whole would have been obvious before the effective filing date of the claimed invention to a person having ordinary skill in the art to which the claimed invention pertains.',
                'topic': 'non_obviousness',
                'hierarchy_level': 1,
            },
            {
                'id': 'us_35_112',
                'jurisdiction': Jurisdiction.US,
                'document_type': DocumentType.STATUTE,
                'title': '35 U.S.C. § 112 - Specification',
                'text': 'The specification shall contain a written description of the invention, and of the manner and process of making and using it, in such full, clear, concise, and exact terms as to enable any person skilled in the art to which it pertains to make and use the same.',
                'topic': 'enablement_written_description',
                'hierarchy_level': 1,
            },
            # EP Patent Law (EPC)
            {
                'id': 'ep_art_52',
                'jurisdiction': Jurisdiction.EP,
                'document_type': DocumentType.TREATY,
                'title': 'EPC Article 52 - Patentable Inventions',
                'text': 'European patents shall be granted for any inventions, in all fields of technology, provided that they are new, involve an inventive step and are susceptible of industrial application.',
                'topic': 'patentable_subject_matter',
                'hierarchy_level': 1,
            },
            {
                'id': 'ep_art_54',
                'jurisdiction': Jurisdiction.EP,
                'document_type': DocumentType.TREATY,
                'title': 'EPC Article 54 - Novelty',
                'text': 'An invention shall be considered to be new if it does not form part of the state of the art.',
                'topic': 'novelty',
                'hierarchy_level': 1,
            },
            {
                'id': 'ep_art_56',
                'jurisdiction': Jurisdiction.EP,
                'document_type': DocumentType.TREATY,
                'title': 'EPC Article 56 - Inventive Step',
                'text': 'An invention shall be considered as involving an inventive step if, having regard to the state of the art, it is not obvious to a person skilled in the art.',
                'topic': 'inventive_step',
                'hierarchy_level': 1,
            },
            {
                'id': 'ep_art_83',
                'jurisdiction': Jurisdiction.EP,
                'document_type': DocumentType.TREATY,
                'title': 'EPC Article 83 - Disclosure of the Invention',
                'text': 'The European patent application shall disclose the invention in a manner sufficiently clear and complete for it to be carried out by a person skilled in the art.',
                'topic': 'sufficiency_of_disclosure',
                'hierarchy_level': 1,
            },
            # PCT
            {
                'id': 'pct_art_33',
                'jurisdiction': Jurisdiction.WO,
                'document_type': DocumentType.TREATY,
                'title': 'PCT Article 33 - International Preliminary Examination Criteria',
                'text': 'The criteria for international preliminary examination are novelty, inventive step, and industrial application.',
                'topic': 'patentability_criteria',
                'hierarchy_level': 1,
            },
            # India Patent Law
            {
                'id': 'in_sec_3',
                'jurisdiction': Jurisdiction.IN,
                'document_type': DocumentType.STATUTE,
                'title': 'Indian Patents Act Section 3 - What are not Inventions',
                'text': 'The following are not inventions within the meaning of this Act: (a) an invention which is frivolous or which claims anything obviously contrary to well established natural laws; (b) an invention the primary or intended use or commercial exploitation of which could be contrary to public order or morality...',
                'topic': 'excluded_subject_matter',
                'hierarchy_level': 1,
            },
            {
                'id': 'in_sec_2_1_j',
                'jurisdiction': Jurisdiction.IN,
                'document_type': DocumentType.STATUTE,
                'title': 'Indian Patents Act Section 2(1)(j) - Definition of Invention',
                'text': 'Invention means a new product or process involving an inventive step and capable of industrial application.',
                'topic': 'invention_definition',
                'hierarchy_level': 1,
            },
            # China Patent Law
            {
                'id': 'cn_art_22',
                'jurisdiction': Jurisdiction.CN,
                'document_type': DocumentType.STATUTE,
                'title': 'Chinese Patent Law Article 22 - Novelty',
                'text': 'Novelty means that, before the date of filing, no identical invention or utility model has been publicly disclosed in publications or in any other way in the world, nor has any other person filed previously with the patent administration department under the State Council for an identical invention or utility model.',
                'topic': 'novelty',
                'hierarchy_level': 1,
            },
            {
                'id': 'cn_art_22_3',
                'jurisdiction': Jurisdiction.CN,
                'document_type': DocumentType.STATUTE,
                'title': 'Chinese Patent Law Article 22.3 - Inventive Step',
                'text': 'Inventive step means that, as compared with the prior art, the invention has prominent substantive features and represents a notable progress.',
                'topic': 'inventive_step',
                'hierarchy_level': 1,
            },
            # Trademark provisions
            {
                'id': 'us_15_1051',
                'jurisdiction': Jurisdiction.US,
                'document_type': DocumentType.STATUTE,
                'title': '15 U.S.C. § 1051 - Application for Registration',
                'text': 'The owner of a trademark used in commerce may request registration of its trademark on the principal register established by this chapter.',
                'topic': 'trademark_registration',
                'hierarchy_level': 1,
            },
            {
                'id': 'us_15_1125',
                'jurisdiction': Jurisdiction.US,
                'document_type': DocumentType.STATUTE,
                'title': '15 U.S.C. § 1125 - False Designations of Origin',
                'text': 'Any person who uses in commerce any word, term, name, symbol, or device... which is likely to cause confusion... shall be liable in a civil action by any person who believes that he or she is or is likely to be damaged by such act.',
                'topic': 'trademark_infringement',
                'hierarchy_level': 1,
            },
            # EU Trademark
            {
                'id': 'eu_reg_2017_1001_art_4',
                'jurisdiction': Jurisdiction.EU,
                'document_type': DocumentType.REGULATION,
                'title': 'EUTMR Article 4 - Signs of which a trade mark may consist',
                'text': 'A trade mark may consist of any signs, in particular words, including personal names, or designs, letters, numerals, colours, the shape of goods or of the packaging of goods, or sounds...',
                'topic': 'trademark_subject_matter',
                'hierarchy_level': 1,
            },
        ]
        
        for prov_data in provisions_data:
            provision = LegalProvision(
                id=prov_data['id'],
                jurisdiction=prov_data['jurisdiction'],
                document_type=prov_data['document_type'],
                title=prov_data['title'],
                text=prov_data['text'],
                topic=prov_data['topic'],
                hierarchy_level=prov_data['hierarchy_level'],
            )
            self.provisions[provision.id] = provision
    
    async def get_provisions(
        self,
        jurisdiction: Jurisdiction,
        document_type: DocumentType,
        topic: Optional[str] = None,
    ) -> List[LegalProvision]:
        results = []
        for prov in self.provisions.values():
            if prov.jurisdiction == jurisdiction and prov.document_type == document_type:
                if topic is None or prov.topic == topic:
                    results.append(prov)
        return results
    
    async def get_provision(
        self,
        jurisdiction: Jurisdiction,
        provision_id: str,
    ) -> Optional[LegalProvision]:
        # Search by ID (jurisdiction prefix + id)
        for prov in self.provisions.values():
            if prov.jurisdiction == jurisdiction and prov.id.endswith(provision_id):
                return prov
        return None
    
    async def search_provisions(
        self,
        query: str,
        jurisdictions: List[Jurisdiction],
        document_type: Optional[DocumentType] = None,
    ) -> List[LegalProvision]:
        results = []
        query_lower = query.lower()
        for prov in self.provisions.values():
            if prov.jurisdiction not in jurisdictions:
                continue
            if document_type and prov.document_type != document_type:
                continue
            if query_lower in prov.text.lower() or query_lower in prov.title.lower() or query_lower in prov.topic.lower():
                results.append(prov)
        return results


class ProceduralTimelineStore(ABC):
    """Abstract base for procedural timeline storage."""
    
    @abstractmethod
    async def get_timeline(
        self,
        jurisdiction: Jurisdiction,
        procedure_type: str,
    ) -> Optional[ProcedureTimeline]:
        pass


class InMemoryProceduralStore(ProceduralTimelineStore):
    """In-memory procedural timeline store."""
    
    def __init__(self):
        self.timelines: Dict[str, ProcedureTimeline] = {}
        self._load_builtin_timelines()
    
    def _load_builtin_timelines(self) -> None:
        """Load built-in procedural timelines."""
        
        # US Patent Prosecution Timeline
        us_patent_steps = [
            ProcedureStep(
                id='us_filing',
                name='Filing Application',
                description='File patent application with USPTO',
                deadline_days=0,
                is_mandatory=True,
                fees={'filing_fee': 300, 'search_fee': 660, 'exam_fee': 760},
            ),
            ProcedureStep(
                id='us_publication',
                name='Publication',
                description='Application published 18 months after priority date',
                deadline_days=540,  # 18 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='us_examination_request',
                name='Request Examination',
                description='Request examination (if not requested at filing)',
                deadline_days=730,  # 24 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='us_first_office_action',
                name='First Office Action',
                description='Receive first office action from examiner',
                deadline_days=1095,  # ~36 months (varies)
                is_mandatory=False,
            ),
            ProcedureStep(
                id='us_response',
                name='Applicant Response',
                description='Respond to office action',
                deadline_days=60,  # 3 months, extendable to 6
                is_mandatory=True,
            ),
            ProcedureStep(
                id='us_allowance',
                name='Notice of Allowance',
                description='Receive notice of allowance',
                deadline_days=1460,  # ~48 months
                is_mandatory=False,
            ),
            ProcedureStep(
                id='us_issue_fee',
                name='Issue Fee Payment',
                description='Pay issue fee',
                deadline_days=90,  # 3 months from allowance
                is_mandatory=True,
            ),
            ProcedureStep(
                id='us_patent_grant',
                name='Patent Grant',
                description='Patent issues',
                deadline_days=30,
                is_mandatory=True,
            ),
        ]
        
        self.timelines['us_patent_prosecution'] = ProcedureTimeline(
            id='us_patent_prosecution',
            jurisdiction=Jurisdiction.US,
            procedure_type='patent_prosecution',
            name='US Patent Prosecution',
            steps=us_patent_steps,
            total_estimated_days=1800,
        )
        
        # EP Patent Prosecution Timeline
        ep_patent_steps = [
            ProcedureStep(
                id='ep_filing',
                name='Filing at EPO',
                description='File European patent application',
                deadline_days=0,
                is_mandatory=True,
                fees={'filing_fee': 125, 'search_fee': 1350},
            ),
            ProcedureStep(
                id='ep_search_report',
                name='European Search Report',
                description='Receive search report and opinion',
                deadline_days=180,  # ~6 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='ep_publication',
                name='Publication',
                description='Application published with search report',
                deadline_days=540,  # 18 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='ep_examination_request',
                name='Request Examination',
                description='Request substantive examination',
                deadline_days=730,  # 24 months from filing
                is_mandatory=True,
                fees={'exam_fee': 1740},
            ),
            ProcedureStep(
                id='ep_first_communication',
                name='First Examination Communication',
                description='Receive first communication from examining division',
                deadline_days=1095,  # ~36 months
                is_mandatory=False,
            ),
            ProcedureStep(
                id='ep_response',
                name='Response to Communication',
                description='Respond to examining division',
                deadline_days=120,  # 4 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='ep_grant',
                name='Decision to Grant',
                description='EPO decides to grant patent',
                deadline_days=1460,
                is_mandatory=False,
            ),
            ProcedureStep(
                id='ep_validation',
                name='National Validation',
                description='Validate in designated states',
                deadline_days=90,  # 3 months from grant
                is_mandatory=True,
            ),
        ]
        
        self.timelines['ep_patent_prosecution'] = ProcedureTimeline(
            id='ep_patent_prosecution',
            jurisdiction=Jurisdiction.EP,
            procedure_type='patent_prosecution',
            name='EP Patent Prosecution',
            steps=ep_patent_steps,
            total_estimated_days=1800,
        )
        
        # PCT Timeline
        pct_steps = [
            ProcedureStep(
                id='pct_filing',
                name='International Filing',
                description='File PCT application at receiving office',
                deadline_days=0,
                is_mandatory=True,
            ),
            ProcedureStep(
                id='pct_search',
                name='International Search',
                description='ISA issues search report and written opinion',
                deadline_days=120,  # 4 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='pct_publication',
                name='International Publication',
                description='WIPO publishes application (18 months)',
                deadline_days=540,
                is_mandatory=True,
            ),
            ProcedureStep(
                id='pct_preliminary_exam',
                name='International Preliminary Examination (Optional)',
                description='Request and receive preliminary examination report',
                deadline_days=720,  # 22 months
                is_mandatory=False,
            ),
            ProcedureStep(
                id='pct_national_phase',
                name='National Phase Entry',
                description='Enter national/regional phase in designated offices',
                deadline_days=730,  # 30/31 months from priority
                is_mandatory=True,
            ),
        ]
        
        self.timelines['pct_procedure'] = ProcedureTimeline(
            id='pct_procedure',
            jurisdiction=Jurisdiction.WO,
            procedure_type='pct_procedure',
            name='PCT International Procedure',
            steps=pct_steps,
            total_estimated_days=900,
        )
        
        # India Patent Prosecution
        in_patent_steps = [
            ProcedureStep(
                id='in_filing',
                name='Filing at Indian Patent Office',
                description='File patent application in India',
                deadline_days=0,
                is_mandatory=True,
            ),
            ProcedureStep(
                id='in_publication',
                name='Publication',
                description='Application published (18 months or early)',
                deadline_days=540,
                is_mandatory=True,
            ),
            ProcedureStep(
                id='in_examination_request',
                name='Request Examination',
                description='File Form 18 for examination request',
                deadline_days=1095,  # 48 months
                is_mandatory=True,
            ),
            ProcedureStep(
                id='in_fcr',
                name='First Examination Report (FER)',
                description='Receive First Examination Report',
                deadline_days=1460,
                is_mandatory=False,
            ),
            ProcedureStep(
                id='in_response',
                name='Response to FER',
                description='Respond to FER within 6 months (extendable)',
                deadline_days=180,
                is_mandatory=True,
            ),
            ProcedureStep(
                id='in_hearing',
                name='Hearing (if required)',
                description='Attend hearing if objections persist',
                deadline_days=365,
                is_mandatory=False,
            ),
            ProcedureStep(
                id='in_grant',
                name='Grant of Patent',
                description='Patent granted and published',
                deadline_days=1825,
                is_mandatory=False,
            ),
        ]
        
        self.timelines['in_patent_prosecution'] = ProcedureTimeline(
            id='in_patent_prosecution',
            jurisdiction=Jurisdiction.IN,
            procedure_type='patent_prosecution',
            name='India Patent Prosecution',
            steps=in_patent_steps,
            total_estimated_days=2000,
        )
    
    async def get_timeline(
        self,
        jurisdiction: Jurisdiction,
        procedure_type: str,
    ) -> Optional[ProcedureTimeline]:
        key = f"{jurisdiction.value}_{procedure_type}"
        return self.timelines.get(key)


class PatentOfficeInterface(ABC):
    """Abstract base for patent office API interfaces."""
    
    @abstractmethod
    async def get_application_status(
        self,
        application_number: str,
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_office_actions(
        self,
        application_number: str,
    ) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def file_document(
        self,
        application_number: str,
        document_type: str,
        content: bytes,
    ) -> Dict[str, Any]:
        pass


class MockPatentOfficeInterface(PatentOfficeInterface):
    """Mock patent office interface for development."""
    
    def __init__(self, jurisdiction: Jurisdiction):
        self.jurisdiction = jurisdiction
    
    async def get_application_status(self, application_number: str) -> Dict[str, Any]:
        return {
            'application_number': application_number,
            'status': 'pending_examination',
            'jurisdiction': self.jurisdiction.value,
            'last_action_date': '2024-01-15',
            'next_deadline': '2024-04-15',
        }
    
    async def get_office_actions(self, application_number: str) -> List[Dict[str, Any]]:
        return [
            {
                'id': 'oa_001',
                'date': '2024-01-15',
                'type': 'non_final_rejection',
                'issues': ['102 rejection', '103 rejection'],
                'response_due': '2024-04-15',
            }
        ]
    
    async def file_document(
        self,
        application_number: str,
        document_type: str,
        content: bytes,
    ) -> Dict[str, Any]:
        return {
            'success': True,
            'receipt_number': f'RCP-{uuid.uuid4().hex[:8]}',
            'filing_date': datetime.utcnow().isoformat(),
        }


class JurisdictionEngine:
    """Main jurisdiction engine for multi-jurisdiction IP analysis."""
    
    def __init__(self, config: Optional[JurisdictionConfig] = None, settings: Optional[Settings] = None):
        self.config = config or JurisdictionConfig()
        self.settings = settings or get_settings()
        
        # Stores
        self.provision_store = InMemoryProvisionStore()
        self.procedural_store = InMemoryProceduralStore()
        
        # Office interfaces (mock for now)
        self.office_interfaces: Dict[Jurisdiction, PatentOfficeInterface] = {}
        for jur in self.config.supported_jurisdictions:
            self.office_interfaces[jur] = MockPatentOfficeInterface(jur)
        
        # Classifier
        self.classifier = JurisdictionClassifier(ClassificationConfig())
        
        # Cache
        self._analysis_cache: Dict[str, Tuple[Any, datetime]] = {}
    
    async def analyze_jurisdiction(
        self,
        document: Document,
        jurisdiction: Optional[Jurisdiction] = None,
        mode: JurisdictionEngineMode = JurisdictionEngineMode.SINGLE,
    ) -> JurisdictionAnalysisResult:
        """Analyze document for specific jurisdiction."""
        target_jurisdiction = jurisdiction or self._detect_jurisdiction(document)
        
        # Check cache
        cache_key = f"{document.id}_{target_jurisdiction.value}_{mode.value}"
        if cache_key in self._analysis_cache:
            cached, cached_time = self._analysis_cache[cache_key]
            if (datetime.utcnow() - cached_time).total_seconds() < self.config.cache_ttl_hours * 3600:
                return cached
        
        result = JurisdictionAnalysisResult(
            jurisdiction=target_jurisdiction,
            document_id=document.id,
        )
        
        # Get applicable legal provisions
        if self.config.enable_legal_provisions:
            result.applicable_provisions = await self._get_applicable_provisions(
                document, target_jurisdiction
            )
        
        # Get procedural timeline
        if self.config.enable_procedural_timelines:
            result.procedural_timeline = await self._get_procedural_timeline(
                document, target_jurisdiction
            )
        
        # Get office actions
        if self.config.enable_office_actions:
            result.office_actions = await self._get_office_actions(document, target_jurisdiction)
        
        # Risk assessment
        result.risk_assessment = self._assess_risks(document, target_jurisdiction, result)
        
        # Recommendations
        result.recommendations = self._generate_recommendations(document, target_jurisdiction, result)
        
        # Calculate confidence
        result.confidence = self._calculate_confidence(result)
        
        # Cache result
        self._analysis_cache[cache_key] = (result, datetime.utcnow())
        
        return result
    
    def _detect_jurisdiction(self, document: Document) -> Jurisdiction:
        """Detect jurisdiction from document."""
        # Use classifier
        import asyncio
        result = asyncio.run(self.classifier.classify(document))
        return result.jurisdiction or self.config.default_jurisdiction
    
    async def _get_applicable_provisions(
        self,
        document: Document,
        jurisdiction: Jurisdiction,
    ) -> List[LegalProvision]:
        """Get legal provisions applicable to document."""
        provisions = []
        
        if document.metadata.document_type == DocumentType.PATENT:
            # Patent-specific provisions
            topics = ['patentable_subject_matter', 'novelty', 'non_obviousness', 'inventive_step', 'enablement_written_description', 'sufficiency_of_disclosure']
            for topic in topics:
                provs = await self.provision_store.get_provisions(jurisdiction, DocumentType.STATUTE, topic)
                if not provs:
                    provs = await self.provision_store.get_provisions(jurisdiction, DocumentType.TREATY, topic)
                provisions.extend(provs)
        elif document.metadata.document_type == DocumentType.TRADEMARK:
            topics = ['trademark_registration', 'trademark_infringement', 'trademark_subject_matter']
            for topic in topics:
                provs = await self.provision_store.get_provisions(jurisdiction, DocumentType.STATUTE, topic)
                if not provs:
                    provs = await self.provision_store.get_provisions(jurisdiction, DocumentType.REGULATION, topic)
                provisions.extend(provs)
        
        return provisions
    
    async def _get_procedural_timeline(
        self,
        document: Document,
        jurisdiction: Jurisdiction,
    ) -> Optional[ProcedureTimeline]:
        """Get procedural timeline for document type in jurisdiction."""
        if document.metadata.document_type == DocumentType.PATENT:
            return await self.procedural_store.get_timeline(jurisdiction, 'patent_prosecution')
        elif jurisdiction == Jurisdiction.WO:
            return await self.procedural_store.get_timeline(jurisdiction, 'pct_procedure')
        return None
    
    async def _get_office_actions(
        self,
        document: Document,
        jurisdiction: Jurisdiction,
    ) -> List[Dict[str, Any]]:
        """Get office actions for document."""
        # Would need application number from document metadata
        app_number = document.metadata.get('application_number')
        if not app_number:
            return []
        
        interface = self.office_interfaces.get(jurisdiction)
        if not interface:
            return []
        
        try:
            return await interface.get_office_actions(app_number)
        except Exception as e:
            logger.warning(f"Failed to get office actions: {e}")
            return []
    
    def _assess_risks(
        self,
        document: Document,
        jurisdiction: Jurisdiction,
        result: JurisdictionAnalysisResult,
    ) -> Dict[str, Any]:
        """Assess risks for document in jurisdiction."""
        risks = {
            'patentability': 'medium',
            'enforcement': 'medium',
            'procedural': 'low',
            'cost': 'medium',
        }
        
        # Adjust based on jurisdiction
        if jurisdiction in (Jurisdiction.US, Jurisdiction.EP):
            risks['enforcement'] = 'high'
        elif jurisdiction in (Jurisdiction.CN, Jurisdiction.IN):
            risks['procedural'] = 'high'  # Longer timelines
        
        # Adjust based on provisions found
        if not result.applicable_provisions:
            risks['patentability'] = 'high'  # Unclear law
        
        return risks
    
    def _generate_recommendations(
        self,
        document: Document,
        jurisdiction: Jurisdiction,
        result: JurisdictionAnalysisResult,
    ) -> List[str]:
        """Generate recommendations for jurisdiction."""
        recommendations = []
        
        if result.procedural_timeline:
            next_steps = [s for s in result.procedural_timeline.steps if s.deadline_days > 0]
            if next_steps:
                recommendations.append(f"Next procedural step: {next_steps[0].name} (due in {next_steps[0].deadline_days} days)")
        
        if result.risk_assessment.get('patentability') == 'high':
            recommendations.append("Consider prior art search before filing in this jurisdiction")
        
        if result.risk_assessment.get('procedural') == 'high':
            recommendations.append("Allow extra time for prosecution; consider expedited examination if available")
        
        if jurisdiction == Jurisdiction.US and document.metadata.document_type == DocumentType.PATENT:
            recommendations.append("Consider Track One prioritized examination for faster grant")
        
        return recommendations
    
    def _calculate_confidence(self, result: JurisdictionAnalysisResult) -> float:
        """Calculate confidence in analysis."""
        confidence = 0.5
        
        if result.applicable_provisions:
            confidence += 0.2
        if result.procedural_timeline:
            confidence += 0.1
        if result.office_actions:
            confidence += 0.1
        if result.recommendations:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def compare_jurisdictions(
        self,
        document: Document,
        base_jurisdiction: Jurisdiction,
        comparison_jurisdictions: List[Jurisdiction],
    ) -> ComparativeAnalysisResult:
        """Compare document across jurisdictions."""
        result = ComparativeAnalysisResult(
            base_jurisdiction=base_jurisdiction,
            comparison_jurisdictions=comparison_jurisdictions,
            document_id=document.id,
        )
        
        # Analyze base jurisdiction
        base_analysis = await self.analyze_jurisdiction(document, base_jurisdiction)
        
        # Compare provisions
        for prov in base_analysis.applicable_provisions:
            topic = prov.topic
            result.provision_comparison[topic] = {base_jurisdiction: prov}
            
            for comp_jur in comparison_jurisdictions:
                comp_provs = await self.provision_store.get_provisions(
                    comp_jur, document.metadata.document_type, topic
                )
                if comp_provs:
                    result.provision_comparison[topic][comp_jur] = comp_provs[0]
        
        # Compare procedural timelines
        base_timeline = base_analysis.procedural_timeline
        if base_timeline:
            result.procedural_comparison[base_jurisdiction.value] = {
                'total_days': base_timeline.total_estimated_days,
                'num_steps': len(base_timeline.steps),
                'key_deadlines': [
                    {'step': s.name, 'days': s.deadline_days}
                    for s in base_timeline.steps if s.deadline_days > 0
                ][:5],
            }
        
        for comp_jur in comparison_jurisdictions:
            comp_timeline = await self.procedural_store.get_timeline(comp_jur, 'patent_prosecution')
            if comp_timeline:
                result.procedural_comparison[comp_jur.value] = {
                    'total_days': comp_timeline.total_estimated_days,
                    'num_steps': len(comp_timeline.steps),
                    'key_deadlines': [
                        {'step': s.name, 'days': s.deadline_days}
                        for s in comp_timeline.steps if s.deadline_days > 0
                    ][:5],
                }
        
        # Find harmonization opportunities
        result.harmonization_opportunities = self._find_harmonization(result)
        
        # Find divergence points
        result.divergence_points = self._find_divergences(result)
        
        # Strategic recommendations
        result.strategic_recommendations = self._generate_strategic_recommendations(result)
        
        return result
    
    def _find_harmonization(self, result: ComparativeAnalysisResult) -> List[str]:
        """Find harmonized provisions across jurisdictions."""
        harmonized = []
        
        for topic, provs in result.provision_comparison.items():
            jurisdictions_with_prov = list(provs.keys())
            if len(jurisdictions_with_prov) >= 3:  # At least 3 jurisdictions
                harmonized.append(f"{topic}: harmonized across {len(jurisdictions_with_prov)} jurisdictions")
        
        return harmonized
    
    def _find_divergences(self, result: ComparativeAnalysisResult) -> List[str]:
        """Find divergent provisions across jurisdictions."""
        divergences = []
        
        for topic, provs in result.provision_comparison.items():
            jurisdictions_with_prov = list(provs.keys())
            if len(jurisdictions_with_prov) < len(result.comparison_jurisdictions) + 1:
                missing = set(result.comparison_jurisdictions) - set(jurisdictions_with_prov)
                if missing:
                    divergences.append(f"{topic}: missing in {', '.join(j.value for j in missing)}")
        
        # Check timeline divergences
        if len(result.procedural_comparison) > 1:
            total_days = {
                jur: data.get('total_days', 0)
                for jur, data in result.procedural_comparison.items()
            }
            max_days = max(total_days.values())
            min_days = min(total_days.values())
            if max_days - min_days > 365:
                divergences.append(f"Procedural timeline varies by {(max_days - min_days) // 30} months across jurisdictions")
        
        return divergences
    
    def _generate_strategic_recommendations(self, result: ComparativeAnalysisResult) -> List[str]:
        """Generate strategic recommendations from comparative analysis."""
        recommendations = []
        
        # Filing strategy
        if Jurisdiction.US in result.comparison_jurisdictions and Jurisdiction.EP in result.comparison_jurisdictions:
            recommendations.append("Consider PCT route for coordinated US/EP prosecution")
        
        if Jurisdiction.IN in result.comparison_jurisdictions:
            recommendations.append("India requires separate examination request (Form 18) within 48 months")
        
        if Jurisdiction.CN in result.comparison_jurisdictions:
            recommendations.append("China has utility model option for faster protection (10-year term)")
        
        # Cost optimization
        recommendations.append("Consider filing in jurisdictions with highest commercial value first")
        
        return recommendations
    
    async def fto_analysis(
        self,
        document: Document,
        jurisdictions: List[Jurisdiction],
    ) -> Dict[str, Any]:
        """Freedom to operate analysis across jurisdictions."""
        results = {}
        
        for jur in jurisdictions:
            analysis = await self.analyze_jurisdiction(document, jur, JurisdictionEngineMode.FTO)
            results[jur.value] = {
                'risk_level': analysis.risk_assessment.get('patentability', 'unknown'),
                'key_provisions': [p.title for p in analysis.applicable_provisions[:3]],
                'recommendations': analysis.recommendations,
            }
        
        return {
            'document_id': document.id,
            'jurisdictions_analyzed': [j.value for j in jurisdictions],
            'results': results,
            'overall_risk': 'high' if any(r['risk_level'] == 'high' for r in results.values()) else 'medium',
        }
    
    async def validity_analysis(
        self,
        patent_document: Document,
        jurisdictions: List[Jurisdiction],
    ) -> Dict[str, Any]:
        """Validity challenge analysis across jurisdictions."""
        results = {}
        
        for jur in jurisdictions:
            analysis = await self.analyze_jurisdiction(patent_document, jur, JurisdictionEngineMode.VALIDITY)
            
            # Focus on validity-specific provisions
            validity_provisions = [
                p for p in analysis.applicable_provisions
                if p.topic in ('novelty', 'non_obviousness', 'inventive_step', 'enablement_written_description', 'sufficiency_of_disclosure')
            ]
            
            results[jur.value] = {
                'validity_grounds': [p.topic for p in validity_provisions],
                'key_provisions': [p.title for p in validity_provisions],
                'risk_assessment': analysis.risk_assessment,
            }
        
        return {
            'patent_id': patent_document.id,
            'jurisdictions_analyzed': [j.value for j in jurisdictions],
            'results': results,
        }
    
    def get_supported_jurisdictions(self) -> List[Jurisdiction]:
        """Get list of supported jurisdictions."""
        return self.config.supported_jurisdictions
    
    def get_patent_office(self, jurisdiction: Jurisdiction) -> Optional[PatentOfficeInterface]:
        """Get patent office interface for jurisdiction."""
        return self.office_interfaces.get(jurisdiction)


def create_jurisdiction_engine(
    config: Optional[JurisdictionConfig] = None,
    settings: Optional[Settings] = None,
) -> JurisdictionEngine:
    """Factory to create jurisdiction engine."""
    return JurisdictionEngine(config, settings)