# app/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

# Enums para mejor tipado
class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class LinkType(Enum):
    DOFOLLOW = "dofollow"
    NOFOLLOW = "nofollow"
    UNKNOWN = "unknown"

# Models existentes actualizados
@dataclass
class SerpResult:
    position: int
    title: str
    url: str
    snippet: str
    domain: str
    # Nuevos campos
    content: Optional[str] = None
    content_metrics: Optional[Dict] = None
    keyword_analysis: Optional[Dict] = None

@dataclass
class KeywordAnalysis:
    keyword: str
    occurrences: int
    density: float
    positions: List[int]
    in_title: bool
    optimal_density: float
    density_status: str
    # Nuevos campos para análisis competitivo
    competitor_avg_density: Optional[float] = None
    density_gap: Optional[float] = None
    title_usage_rate: Optional[float] = None
    content_patterns: Optional[List[str]] = field(default_factory=list)

@dataclass
class ContentMetrics:
    word_count: int
    character_count: int
    sentence_count: int
    paragraph_count: int
    avg_words_per_sentence: float
    avg_sentences_per_paragraph: Optional[float] = None
    # Nuevos campos
    dom_size: Optional[int] = None
    unique_words: Optional[int] = None
    vocabulary_richness: Optional[float] = None

@dataclass
class ReadabilityScore:
    flesch_reading_ease: float
    flesch_kincaid_grade: Optional[float] = None
    automated_readability_index: Optional[float] = None
    reading_level: str = ""
    complex_words: int = 0
    passive_voice_percentage: Optional[float] = None
    # Campo para idioma específico
    language_specific_score: Optional[Dict] = None

@dataclass
class SEOElements:
    title: Dict
    meta_description: Dict
    h1_tags: Dict
    canonical_url: Dict
    open_graph: Dict
    schema_markup: Dict
    # Nuevos campos
    robots: Optional[Dict] = None
    twitter_cards: Optional[Dict] = None
    images: Optional[Dict] = None
    internal_linking: Optional[Dict] = None

@dataclass
class PerformanceMetrics:
    load_time_seconds: float
    page_size_mb: float
    css_files: int
    javascript_files: int
    images: int
    resource_optimization_score: int
    # Nuevos campos
    compression_enabled: bool = False
    caching_enabled: bool = False
    security_score: Optional[float] = None
    mobile_score: Optional[float] = None
    pagespeed_insights: Optional[Dict] = None

@dataclass
class Recommendation:
    type: str
    priority: str
    title: str
    description: str
    impact: str
    category: str  # Nuevo campo obligatorio
    action: Optional[str] = None
    # Nuevos campos para análisis competitivo
    current_value: Optional[Any] = None
    target_value: Optional[Any] = None
    improvement: Optional[str] = None
    keyword: Optional[str] = None
    actions: Optional[List[str]] = field(default_factory=list)
    estimated_time: Optional[str] = None

# Nuevos models para funcionalidades añadidas

@dataclass
class CompetitiveAnalysis:
    """Análisis competitivo completo"""
    content_comparison: Dict
    keyword_insights: Dict[str, Dict]
    competitors_analyzed: int
    total_keywords_analyzed: int

@dataclass
class CompetitorData:
    """Datos de un competidor específico"""
    url: str
    title: str
    position: int
    content: str
    content_metrics: Dict
    keyword_analysis: Dict
    domain: str

@dataclass
class BacklinkSource:
    """Fuente de backlink detectada"""
    source: str
    type: str  # editorial_mention, directory_listing, social_profile, etc.
    authority_score: int
    detection_method: str
    link_type: LinkType
    anchor_text: str

@dataclass
class LinkOpportunity:
    """Oportunidad de link building"""
    type: str
    target: str
    difficulty: DifficultyLevel
    authority_potential: int
    priority_score: int
    description: str
    estimated_time: str
    url: Optional[str] = None
    actions: Optional[List[str]] = field(default_factory=list)

@dataclass
class SocialSignals:
    """Señales sociales del dominio"""
    facebook_shares: int = 0
    facebook_likes: int = 0
    facebook_comments: int = 0
    twitter_mentions: int = 0
    linkedin_shares: int = 0
    total_social_signals: int = 0
    signal_breakdown: Optional[Dict] = None

@dataclass
class TechnicalSEO:
    """Análisis técnico SEO completo"""
    ssl_certificate: Dict
    dns_records: Dict
    server_response: Dict
    security_headers: Dict
    mobile_friendly: Dict
    page_speed: Dict
    crawlability: Dict
    technical_score: int

@dataclass
class TrustSignals:
    """Señales de confianza del dominio"""
    whois_transparency: Dict
    ssl_trust: Dict
    domain_age: Dict
    business_verification: Dict
    social_presence: Dict
    content_quality: Dict
    external_validation: Dict
    trust_score: int
    trust_level: str

@dataclass
class DomainAnalysis:
    domain: str
    domain_authority_score: int
    trust_score: int
    backlink_sources: List[BacklinkSource]
    social_signals: SocialSignals
    technical_seo: TechnicalSEO
    domain_age_years: Optional[float]
    # Nuevos campos
    timestamp: str
    trust_signals: Optional[TrustSignals] = None
    competitor_analysis: Optional[Dict] = None
    link_building_opportunities: Optional[Dict] = None

@dataclass
class ContentAnalysisResult:
    """Resultado completo del análisis de contenido"""
    detected_language: str
    language_name: str
    extracted_keywords: List[str]
    basic_metrics: ContentMetrics
    readability: ReadabilityScore
    keyword_analysis: Dict[str, KeywordAnalysis]
    semantic_analysis: Dict
    content_score: int
    optimization_suggestions: List[Recommendation]
    # Nuevos campos
    competitive_analysis: Optional[CompetitiveAnalysis] = None
    timestamp: str = ""

@dataclass
class SerPAnalysisResult:
    """Resultado del análisis SERP"""
    keyword: str
    language: str
    location: str
    google_domain: str
    organic_results: List[SerpResult]
    featured_snippet: Optional[Dict] = None
    people_also_ask: List[str] = field(default_factory=list)
    related_searches: List[str] = field(default_factory=list)
    total_results: int = 0

@dataclass
class KeywordSuggestion:
    """Sugerencia de keyword"""
    keyword: str
    search_volume: Optional[int] = None
    competition: Optional[str] = None
    cpc: Optional[float] = None
    relevance_score: Optional[float] = None

@dataclass
class KeywordSuggestionsResult:
    """Resultado de sugerencias de keywords"""
    seed_keyword: str
    language: str
    country: str
    suggestions: List[str]
    total_found: int
    detailed_suggestions: Optional[List[KeywordSuggestion]] = field(default_factory=list)

@dataclass
class CompetitorAnalysisResult:
    """Resultado del análisis de competidores"""
    keywords_analyzed: List[str]
    my_domain: str
    competitors_by_keyword: Dict[str, List[Dict]]
    unique_competitors: List[Dict]
    total_competitors_found: int
    analysis_summary: Dict

@dataclass
class APIResponse:
    """Respuesta estándar de la API"""
    success: bool
    data: Any
    timestamp: str
    error: Optional[str] = None
    cache_hit: bool = False

# Funciones helper para conversión
def dict_to_dataclass(cls, data: Dict) -> Any:
    """Convertir diccionario a dataclass"""
    if not isinstance(data, dict):
        return data
    
    try:
        # Obtener campos del dataclass
        field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
        kwargs = {}
        
        for key, value in data.items():
            if key in field_types:
                kwargs[key] = value
        
        return cls(**kwargs)
    except Exception as e:
        print(f"Error converting dict to {cls.__name__}: {e}")
        return data

def dataclass_to_dict(obj: Any) -> Dict:
    """Convertir dataclass a diccionario"""
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if hasattr(value, '__dataclass_fields__'):
                result[field_name] = dataclass_to_dict(value)
            elif isinstance(value, list):
                result[field_name] = [
                    dataclass_to_dict(item) if hasattr(item, '__dataclass_fields__') else item
                    for item in value
                ]
            else:
                result[field_name] = value
        return result
    return obj

# Validadores
def validate_priority(priority: str) -> bool:
    """Validar que la prioridad sea válida"""
    return priority in [p.value for p in Priority]

def validate_difficulty(difficulty: str) -> bool:
    """Validar que la dificultad sea válida"""
    return difficulty in [d.value for d in DifficultyLevel]

def validate_link_type(link_type: str) -> bool:
    """Validar que el tipo de link sea válido"""
    return link_type in [lt.value for lt in LinkType]