from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class SerpResult:
    position: int
    title: str
    url: str
    snippet: str
    domain: str

@dataclass
class KeywordAnalysis:
    keyword: str
    occurrences: int
    density: float
    positions: List[int]
    in_title: bool
    optimal_density: float
    density_status: str

@dataclass
class ContentMetrics:
    word_count: int
    character_count: int
    sentence_count: int
    paragraph_count: int
    avg_words_per_sentence: float
    avg_sentences_per_paragraph: float

@dataclass
class ReadabilityScore:
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    automated_readability_index: float
    reading_level: str
    complex_words: int
    passive_voice_percentage: float

@dataclass
class SEOElements:
    title: Dict
    meta_description: Dict
    h1_tags: Dict
    canonical_url: Dict
    open_graph: Dict
    schema_markup: Dict

@dataclass
class PerformanceMetrics:
    load_time_seconds: float
    page_size_mb: float
    css_files: int
    javascript_files: int
    images: int
    resource_optimization_score: int

@dataclass
class Recommendation:
    type: str
    priority: str
    title: str
    description: str
    impact: str
    action: Optional[str] = None

@dataclass
class DomainAnalysis:
    domain: str
    domain_authority_score: int
    trust_score: int
    backlink_sources: List[Dict]
    social_signals: Dict
    technical_seo: Dict
    domain_age_years: Optional[float]