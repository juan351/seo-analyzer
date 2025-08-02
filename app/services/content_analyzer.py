# app/services/content_analyzer.py (sin dependencias problemáticas)
import nltk
from textstat import flesch_reading_ease
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from ..utils.language_detector import LanguageDetector
import re
from collections import Counter

class MultilingualContentAnalyzer:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.language_detector = LanguageDetector()
        self.nlp_models = {}
        self.load_models()
        
    def load_models(self):
        """Cargar modelos disponibles"""
        if not SPACY_AVAILABLE:
            print("⚠️ Spacy no disponible, usando análisis básico")
            return
            
        for lang_code, config in self.language_detector.get_supported_languages().items():
            try:
                model_name = config['spacy_model']
                self.nlp_models[lang_code] = spacy.load(model_name)
                print(f"✅ Modelo {model_name} cargado")
            except OSError:
                print(f"❌ Modelo {model_name} no encontrado")

    def comprehensive_analysis(self, content, target_keywords, competitor_contents, language=None):
        """Análisis completo simplificado"""
        
        # Detectar idioma
        if not language:
            language = self.language_detector.detect_language(content)
        
        cache_key = f"content_analysis:{language}:{hash(content)}:{hash(str(target_keywords))}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        analysis = {
            'detected_language': language,
            'language_name': self.language_detector.get_language_config(language)['name'],
            'basic_metrics': self.get_basic_metrics(content),
            'readability': self.analyze_readability(content, language),
            'keyword_analysis': self.analyze_keywords(content, target_keywords, language),
            'content_score': 0,
            'optimization_suggestions': []
        }
        
        # Análisis semántico solo si spacy está disponible
        if SPACY_AVAILABLE and language in self.nlp_models:
            analysis['semantic_analysis'] = self.semantic_analysis(content, language)
        else:
            analysis['semantic_analysis'] = self.basic_semantic_analysis(content, language)
        
        # Generar sugerencias
        analysis['optimization_suggestions'] = self.generate_suggestions(analysis, language)
        analysis['content_score'] = self.calculate_content_score(analysis)
        
        # Cache por 1 hora
        self.cache.set(cache_key, analysis, 3600)
        return analysis

    def get_basic_metrics(self, content):
        """Métricas básicas universales"""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        return {
            'word_count': len(words),
            'character_count': len(content),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'paragraph_count': len([p for p in paragraphs if p.strip()]),
            'avg_words_per_sentence': len(words) / max(len(sentences), 1)
        }

    def analyze_readability(self, content, language):
        """Análisis de legibilidad simplificado"""
        try:
            if language == 'es':
                return self.analyze_spanish_readability(content)
            else:
                return {
                    'flesch_reading_ease': flesch_reading_ease(content),
                    'reading_level': self.get_reading_level(flesch_reading_ease(content)),
                    'complex_words': self.count_complex_words(content)
                }
        except:
            return {
                'flesch_reading_ease': 50,
                'reading_level': 'Standard',
                'complex_words': 0
            }

    def analyze_spanish_readability(self, content):
        """Análisis específico para español"""
        words = len(content.split())
        sentences = len(re.split(r'[.!?]+', content))
        
        if sentences == 0 or words == 0:
            return {'reading_level': 'Unknown', 'flesch_reading_ease': 50}
        
        # Fórmula aproximada para español
        avg_sentence_length = words / sentences
        flesch_spanish = 100 - (1.02 * avg_sentence_length)
        
        return {
            'flesch_reading_ease': round(max(0, min(100, flesch_spanish)), 2),
            'reading_level': self.get_spanish_reading_level(flesch_spanish),
            'complex_words': self.count_complex_words_spanish(content)
        }

    def get_spanish_reading_level(self, flesch_score):
        """Niveles para español"""
        if flesch_score >= 80:
            return 'Muy fácil'
        elif flesch_score >= 65:
            return 'Fácil'
        elif flesch_score >= 50:
            return 'Normal'
        elif flesch_score >= 35:
            return 'Difícil'
        else:
            return 'Muy difícil'

    def count_complex_words_spanish(self, content):
        """Palabras complejas en español"""
        words = re.findall(r'\b[a-záéíóúüñ]+\b', content.lower())
        return len([w for w in words if len(w) > 7])

    def count_complex_words(self, content):
        """Palabras complejas en inglés"""
        words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
        return len([w for w in words if len(w) > 6])

    def get_reading_level(self, flesch_score):
        """Niveles para inglés"""
        if flesch_score >= 90:
            return 'Very Easy'
        elif flesch_score >= 80:
            return 'Easy'
        elif flesch_score >= 70:
            return 'Fairly Easy'
        elif flesch_score >= 60:
            return 'Standard'
        elif flesch_score >= 50:
            return 'Fairly Difficult'
        else:
            return 'Difficult'

    def analyze_keywords(self, content, target_keywords, language):
        """Análisis básico de keywords"""
        content_lower = content.lower()
        word_count = len(content.split())
        
        keyword_analysis = {}
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            occurrences = content_lower.count(keyword_lower)
            density = (occurrences / word_count) * 100 if word_count > 0 else 0
            
            keyword_analysis[keyword] = {
                'occurrences': occurrences,
                'density': round(density, 2),
                'density_status': self.evaluate_density(density),
                'in_title': keyword_lower in content_lower[:100]
            }
        
        return keyword_analysis

    def evaluate_density(self, density):
        """Evaluar densidad de keyword"""
        if density == 0:
            return 'missing'
        elif density < 0.5:
            return 'too_low'
        elif density > 3:
            return 'too_high'
        else:
            return 'optimal'

    def basic_semantic_analysis(self, content, language):
        """Análisis semántico básico sin spacy"""
        words = content.lower().split()
        word_freq = Counter(words)
        
        return {
            'top_words': word_freq.most_common(10),
            'unique_words': len(set(words)),
            'vocabulary_richness': len(set(words)) / len(words) if words else 0
        }

    def semantic_analysis(self, content, language):
        """Análisis semántico con spacy"""
        if language not in self.nlp_models:
            return self.basic_semantic_analysis(content, language)
        
        nlp = self.nlp_models[language]
        doc = nlp(content)
        
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        return {
            'entities': entities[:10],
            'entity_count': len(entities),
            'noun_phrases': [chunk.text for chunk in doc.noun_chunks][:10]
        }

    def generate_suggestions(self, analysis, language):
        """Sugerencias básicas"""
        suggestions = []
        
        word_count = analysis['basic_metrics']['word_count']
        if word_count < 300:
            msg = "Aumentar longitud del contenido" if language == 'es' else "Increase content length"
            suggestions.append({
                'type': 'content_length',
                'priority': 'high',
                'message': f'{msg}. Actual: {word_count} palabras.'
            })
        
        return suggestions

    def calculate_content_score(self, analysis):
        """Calcular puntuación general del contenido"""
        score = 0
        
        # Puntuación por longitud (30 puntos)
        word_count = analysis['basic_metrics']['word_count']
        if 300 <= word_count <= 2000:
            score += 30
        elif 200 <= word_count < 300:
            score += 20
        elif word_count >= 100:
            score += 10
        
        # Puntuación por legibilidad (25 puntos)
        flesch_score = analysis['readability'].get('flesch_reading_ease', 50)
        if 60 <= flesch_score <= 80:
            score += 25
        elif 50 <= flesch_score < 60 or 80 < flesch_score <= 90:
            score += 20
        elif flesch_score >= 30:
            score += 15
        
        # Puntuación por keywords (25 puntos)
        keyword_scores = []
        for keyword, data in analysis['keyword_analysis'].items():
            if data['density_status'] == 'optimal':
                keyword_scores.append(25)
            elif data['density_status'] in ['too_low', 'too_high']:
                keyword_scores.append(15)
            else:
                keyword_scores.append(0)
        
        if keyword_scores:
            score += sum(keyword_scores) / len(keyword_scores)
        
        # Puntuación por diversidad semántica (20 puntos)
        semantic = analysis.get('semantic_analysis', {})
        if 'entities' in semantic:
            entity_count = len(semantic.get('entities', []))
            score += min(entity_count * 2, 20)
        elif 'vocabulary_richness' in semantic:
            richness = semantic.get('vocabulary_richness', 0)
            score += richness * 20
        
        return min(round(score), 100)
        