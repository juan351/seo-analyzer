# app/services/content_analyzer.py (versión multiidioma)
import nltk
from textstat import flesch_reading_ease, flesch_kincaid_grade
import spacy
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re
from ..utils.language_detector import LanguageDetector

class MultilingualContentAnalyzer:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.language_detector = LanguageDetector()
        self.nlp_models = {}  # Cache de modelos spacy
        self.load_models()
        
    def load_models(self):
        """Cargar modelos de spacy para idiomas soportados"""
        for lang_code, config in self.language_detector.get_supported_languages().items():
            try:
                model_name = config['spacy_model']
                self.nlp_models[lang_code] = spacy.load(model_name)
                print(f"✅ Modelo {model_name} cargado para {config['name']}")
            except OSError:
                print(f"❌ No se pudo cargar {model_name} para {config['name']}")
                # Fallback a inglés si no está disponible
                if lang_code != 'en':
                    self.nlp_models[lang_code] = self.nlp_models.get('en')

    def comprehensive_analysis(self, content, target_keywords, competitor_contents, language=None):
        """Análisis completo de contenido multiidioma"""
        
        # Detectar idioma si no se proporciona
        if not language:
            language = self.language_detector.detect_language(content)
        
        lang_config = self.language_detector.get_language_config(language)
        
        cache_key = f"content_analysis:{language}:{hash(content)}:{hash(str(target_keywords))}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        analysis = {
            'detected_language': language,
            'language_name': lang_config['name'],
            'basic_metrics': self.get_basic_metrics(content, language),
            'readability': self.analyze_readability(content, language),
            'keyword_analysis': self.analyze_keywords(content, target_keywords, language),
            'semantic_analysis': self.semantic_analysis(content, language),
            'structure_analysis': self.analyze_structure(content, language),
            'competitor_comparison': self.compare_with_competitors(content, competitor_contents, language),
            'optimization_suggestions': [],
            'content_score': 0
        }
        
        # Generar sugerencias basadas en el análisis
        analysis['optimization_suggestions'] = self.generate_suggestions(analysis, language)
        analysis['content_score'] = self.calculate_content_score(analysis)
        
        # Cache por 1 hora
        self.cache.set(cache_key, analysis, 3600)
        return analysis

    def get_basic_metrics(self, content, language):
        """Métricas básicas adaptadas por idioma"""
        # Para español, las oraciones pueden ser más largas naturalmente
        multipliers = {
            'en': 1.0,
            'es': 1.2,  # Las oraciones en español tienden a ser más largas
            'fr': 1.15,
            'de': 1.3   # Alemán tiene oraciones muy largas
        }
        
        multiplier = multipliers.get(language, 1.0)
        
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        avg_words_per_sentence = len(words) / max(len(sentences), 1)
        
        return {
            'word_count': len(words),
            'character_count': len(content),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'paragraph_count': len([p for p in paragraphs if p.strip()]),
            'avg_words_per_sentence': avg_words_per_sentence,
            'avg_sentences_per_paragraph': len(sentences) / max(len(paragraphs), 1),
            'optimal_sentence_length': avg_words_per_sentence <= (20 * multiplier)
        }

    def analyze_readability(self, content, language):
        """Análisis de legibilidad adaptado por idioma"""
        try:
            if language == 'es':
                return self.analyze_spanish_readability(content)
            elif language == 'en':
                return {
                    'flesch_reading_ease': flesch_reading_ease(content),
                    'flesch_kincaid_grade': flesch_kincaid_grade(content),
                    'reading_level': self.get_reading_level(flesch_reading_ease(content)),
                    'complex_words': self.count_complex_words(content, language),
                    'passive_voice_percentage': self.calculate_passive_voice(content, language)
                }
            else:
                # Para otros idiomas, análisis básico
                return self.analyze_basic_readability(content, language)
        except:
            return {
                'flesch_reading_ease': 0,
                'reading_level': 'Unknown',
                'complex_words': 0,
                'passive_voice_percentage': 0
            }

    def analyze_spanish_readability(self, content):
        """Análisis de legibilidad específico para español"""
        
        # Fórmula de Flesch adaptada al español (Szigriszt)
        words = len(content.split())
        sentences = len(re.split(r'[.!?]+', content))
        syllables = self.count_syllables_spanish(content)
        
        if sentences == 0 or words == 0:
            return {'reading_level': 'Unknown', 'flesch_reading_ease': 0}
        
        # Fórmula Szigriszt para español
        flesch_spanish = 206.84 - (1.02 * (words / sentences)) - (0.60 * (syllables / words))
        
        return {
            'flesch_reading_ease': round(flesch_spanish, 2),
            'reading_level': self.get_spanish_reading_level(flesch_spanish),
            'complex_words': self.count_complex_words_spanish(content),
            'passive_voice_percentage': self.calculate_passive_voice_spanish(content),
            'syllables_per_word': round(syllables / words, 2) if words > 0 else 0
        }

    def count_syllables_spanish(self, content):
        """Contar sílabas en español"""
        words = re.findall(r'\b[a-záéíóúüñ]+\b', content.lower())
        total_syllables = 0
        
        for word in words:
            # Reglas básicas para contar sílabas en español
            vowels = 'aeiouáéíóúü'
            syllable_count = 0
            prev_was_vowel = False
            
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not prev_was_vowel:
                    syllable_count += 1
                prev_was_vowel = is_vowel
            
            # Ajustes para diptongos y hiatos
            if 'ai' in word or 'ei' in word or 'oi' in word or 'ui' in word:
                syllable_count -= word.count('ai') + word.count('ei') + word.count('oi') + word.count('ui')
            
            total_syllables += max(1, syllable_count)
        
        return total_syllables

    def get_spanish_reading_level(self, flesch_score):
        """Niveles de lectura para español según Szigriszt"""
        if flesch_score >= 81:
            return 'Muy fácil'
        elif flesch_score >= 66:
            return 'Fácil'
        elif flesch_score >= 51:
            return 'Algo fácil'
        elif flesch_score >= 36:
            return 'Normal'
        elif flesch_score >= 21:
            return 'Algo difícil'
        elif flesch_score >= 6:
            return 'Difícil'
        else:
            return 'Muy difícil'

    def count_complex_words_spanish(self, content):
        """Contar palabras complejas en español (4+ sílabas)"""
        words = re.findall(r'\b[a-záéíóúüñ]+\b', content.lower())
        complex_count = 0
        
        for word in words:
            if len(word) > 6:  # Palabras largas en español
                syllables = self.count_syllables_spanish(word)
                if syllables >= 4:
                    complex_count += 1
        
        return complex_count

    def calculate_passive_voice_spanish(self, content):
        """Detectar voz pasiva en español"""
        if not self.nlp_models.get('es'):
            return 0
        
        doc = self.nlp_models['es'](content)
        passive_count = 0
        total_sentences = len(list(doc.sents))
        
        # Patrones de voz pasiva en español
        passive_patterns = [
            'ser + participio',  # "fue construido"
            'se + verbo',        # "se construyó"
        ]
        
        for sent in doc.sents:
            text = sent.text.lower()
            # Detectar "ser + participio"
            if any(word in text for word in ['fue', 'fueron', 'es', 'son', 'era', 'eran']) and \
               any(token.tag_.startswith('V') and token.tag_.endswith('P') for token in sent):
                passive_count += 1
            # Detectar "se + verbo"
            elif ' se ' in text and any(token.pos_ == 'VERB' for token in sent):
                passive_count += 1
        
        return (passive_count / max(total_sentences, 1)) * 100

    def semantic_analysis(self, content, language):
        """Análisis semántico multiidioma"""
        nlp = self.nlp_models.get(language, self.nlp_models.get('en'))
        if not nlp:
            return {'error': f'No model available for language: {language}'}
        
        doc = nlp(content)
        
        # Entidades nombradas
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        entity_types = Counter([ent.label_ for ent in doc.ents])
        
        # Frases nominales importantes
        noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
        
        # Configurar stopwords por idioma
        lang_config = self.language_detector.get_language_config(language)
        stopwords_lang = lang_config['stopwords_lang']
        
        try:
            stop_words = set(nltk.corpus.stopwords.words(stopwords_lang))
        except:
            stop_words = set(nltk.corpus.stopwords.words('english'))
        
        # TF-IDF con stopwords del idioma correcto
        vectorizer = TfidfVectorizer(
            max_features=1000, 
            stop_words=list(stop_words),
            ngram_range=(1, 2)
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform([content])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Top 20 términos por TF-IDF
            top_terms = sorted(zip(feature_names, tfidf_scores), key=lambda x: x[1], reverse=True)[:20]
        except:
            top_terms = []
        
        return {
            'entities': entities[:20],
            'entity_types': dict(entity_types),
            'noun_phrases': noun_phrases[:15],
            'semantic_density': len(entities) / len(content.split()) if content.split() else 0,
            'top_terms': top_terms,
            'topic_diversity': len(set([ent.label_ for ent in doc.ents])),
            'language_specific_features': self.get_language_specific_features(content, language)
        }

    def get_language_specific_features(self, content, language):
        """Características específicas por idioma"""
        features = {}
        
        if language == 'es':
            # Características específicas del español
            features.update({
                'accent_usage': len(re.findall(r'[áéíóúüñ]', content.lower())),
                'subjunctive_usage': len(re.findall(r'\b(sea|fuera|hubiera|tuviera)\b', content.lower())),
                'formal_pronouns': len(re.findall(r'\b(usted|ustedes)\b', content.lower())),
                'regional_variations': self.detect_spanish_variations(content)
            })
        elif language == 'en':
            # Características específicas del inglés
            features.update({
                'contractions': len(re.findall(r"[a-z]+'[a-z]+", content.lower())),
                'phrasal_verbs': self.count_phrasal_verbs(content),
                'modal_verbs': len(re.findall(r'\b(can|could|may|might|will|would|shall|should|must)\b', content.lower()))
            })
        
        return features

    def detect_spanish_variations(self, content):
        """Detectar variaciones regionales del español"""
        variations = {
            'spain': len(re.findall(r'\b(vosotros|ordenador|móvil|coche)\b', content.lower())),
            'mexico': len(re.findall(r'\b(ustedes|computadora|celular|carro)\b', content.lower())),
            'argentina': len(re.findall(r'\b(vos|che|quilombo)\b', content.lower()))
        }
        return max(variations, key=variations.get) if any(variations.values()) else 'neutral'

    def count_phrasal_verbs(self, content):
        """Contar phrasal verbs en inglés"""
        phrasal_verbs = [
            'give up', 'look up', 'put off', 'turn on', 'turn off', 'pick up',
            'set up', 'break down', 'come up', 'go on', 'find out', 'work out'
        ]
        count = 0
        content_lower = content.lower()
        for pv in phrasal_verbs:
            count += content_lower.count(pv)
        return count

    def analyze_keywords(self, content, target_keywords, language):
        """Análisis de keywords adaptado por idioma"""
        content_lower = content.lower()
        word_count = len(content.split())
        
        keyword_analysis = {}
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            
            # Búsqueda exacta
            exact_occurrences = content_lower.count(keyword_lower)
            
            # Búsqueda de variaciones por idioma
            variations = self.get_keyword_variations(keyword, language)
            variation_occurrences = 0
            
            for variation in variations:
                variation_occurrences += content_lower.count(variation.lower())
            
            total_occurrences = exact_occurrences + variation_occurrences
            density = (total_occurrences / word_count) * 100 if word_count > 0 else 0
            
            # Posiciones de las keywords
            positions = []
            start = 0
            while True:
                pos = content_lower.find(keyword_lower, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            keyword_analysis[keyword] = {
                'occurrences': exact_occurrences,
                'variation_occurrences': variation_occurrences,
                'total_occurrences': total_occurrences,
                'density': round(density, 2),
                'positions': positions,
                'in_title': keyword_lower in content_lower[:100],
                'optimal_density': self.get_optimal_density(keyword, language),
                'density_status': self.evaluate_density(density, keyword, language),
                'variations_found': variations
            }
        
        return keyword_analysis

    def get_keyword_variations(self, keyword, language):
        """Obtener variaciones de keywords por idioma"""
        variations = []
        
        if language == 'es':
            # Variaciones en español (plural, género, etc.)
            variations.extend(self.get_spanish_variations(keyword))
        elif language == 'en':
            # Variaciones en inglés (plural, sinónimos básicos)
            variations.extend(self.get_english_variations(keyword))
        
        return variations

    def get_spanish_variations(self, keyword):
        """Generar variaciones en español"""
        variations = []
        words = keyword.split()
        
        for word in words:
            # Plurales básicos
            if word.endswith('a'):
                variations.append(word + 's')  # casa -> casas
            elif word.endswith('o'):
                variations.append(word + 's')  # libro -> libros
            elif word.endswith(('e', 'í', 'ú')):
                variations.append(word + 's')  # coche -> coches
            elif word.endswith(('l', 'r', 'n', 's')):
                variations.append(word + 'es')  # animal -> animales
            
            # Género básico
            if word.endswith('o'):
                variations.append(word[:-1] + 'a')  # bueno -> buena
            elif word.endswith('a'):
                variations.append(word[:-1] + 'o')  # buena -> bueno
        
        return variations

    def get_english_variations(self, keyword):
        """Generar variaciones en inglés"""
        variations = []
        words = keyword.split()
        
        for word in words:
            # Plurales básicos
            if word.endswith('y'):
                variations.append(word[:-1] + 'ies')  # city -> cities
            elif word.endswith(('s', 'sh', 'ch', 'x', 'z')):
                variations.append(word + 'es')  # box -> boxes
            else:
                variations.append(word + 's')  # cat -> cats
            
            # Formas verbales básicas
            if len(word) > 3:
                variations.append(word + 'ing')  # run -> running
                variations.append(word + 'ed')   # run -> runned (básico)
        
        return variations

    def get_optimal_density(self, keyword, language):
        """Densidad óptima adaptada por idioma"""
        word_count = len(keyword.split())
        
        # En español las oraciones tienden a ser más largas
        multipliers = {
            'en': 1.0,
            'es': 0.8,  # Densidad ligeramente menor por oraciones más largas
            'fr': 0.85,
            'de': 0.7   # Alemán tiene palabras muy largas
        }
        
        multiplier = multipliers.get(language, 1.0)
        
        if word_count == 1:
            return 1.5 * multiplier
        elif word_count == 2:
            return 1.0 * multiplier
        else:
            return 0.5 * multiplier

    def generate_suggestions(self, analysis, language):
        """Generar sugerencias adaptadas por idioma"""
        suggestions = []
        lang_config = self.language_detector.get_language_config(language)
        
        # Sugerencias de longitud adaptadas por idioma
        word_count = analysis['basic_metrics']['word_count']
        
        # Longitudes óptimas por idioma
        optimal_lengths = {
            'en': {'min': 300, 'ideal': 1500, 'max': 3000},
            'es': {'min': 350, 'ideal': 1800, 'max': 3500},  # Español tiende a ser más verbose
            'fr': {'min': 320, 'ideal': 1600, 'max': 3200},
            'de': {'min': 280, 'ideal': 1400, 'max': 2800}   # Alemán más conciso por palabras largas
        }
        
        length_config = optimal_lengths.get(language, optimal_lengths['en'])
        
        if word_count < length_config['min']:
            suggestions.append({
                'type': 'content_length',
                'priority': 'high',
                'message': f'Aumentar longitud del contenido. Actual: {word_count} palabras. Recomendado: {length_config["min"]}+ palabras.',
                'action': f'Agregar más información detallada en {lang_config["name"]}.'
            })
        elif word_count > length_config['max']:
            suggestions.append({
                'type': 'content_length',
                'priority': 'medium',
                'message': f'El contenido es muy largo ({word_count} palabras). Considerar dividir en múltiples páginas.',
                'action': 'Dividir contenido o agregar tabla de contenidos.'
            })
        
        # Sugerencias de legibilidad específicas por idioma
        readability = analysis['readability']
        
        if language == 'es':
            flesch_score = readability.get('flesch_reading_ease', 0)
            if flesch_score < 36:  # "Normal" en escala española
                suggestions.append({
                    'type': 'readability',
                    'priority': 'high',
                    'message': 'El contenido es difícil de leer en español. Simplificar estructura.',
                    'action': 'Usar oraciones más cortas y vocabulario más simple.'
                })
        elif language == 'en':
            flesch_score = readability.get('flesch_reading_ease', 0)
            if flesch_score < 50:
                suggestions.append({
                    'type': 'readability',
                    'priority': 'high',
                    'message': 'Content is difficult to read. Simplify language and structure.',
                    'action': 'Use shorter sentences and simpler vocabulary.'
                })
        
        # Sugerencias específicas por idioma
        if language == 'es':
            suggestions.extend(self.get_spanish_specific_suggestions(analysis))
        elif language == 'en':
            suggestions.extend(self.get_english_specific_suggestions(analysis))
        
        return suggestions

    def get_spanish_specific_suggestions(self, analysis):
        """Sugerencias específicas para contenido en español"""
        suggestions = []
        
        # Verificar uso de acentos
        lang_features = analysis['semantic_analysis'].get('language_specific_features', {})
        accent_usage = lang_features.get('accent_usage', 0)
        word_count = analysis['basic_metrics']['word_count']
        
        if accent_usage / word_count < 0.02:  # Muy pocos acentos
            suggestions.append({
                'type': 'language_quality',
                'priority': 'medium',
                'message': 'Verificar el uso correcto de acentos y tildes.',
                'action': 'Revisar ortografía y acentuación en español.'
            })
        
        # Verificar variación regional
        regional_var = lang_features.get('regional_variations', 'neutral')
        if regional_var != 'neutral':
            suggestions.append({
                'type': 'language_consistency',
                'priority': 'low',
                'message': f'Contenido parece orientado a {regional_var}. Verificar si es intencional.',
                'action': 'Considerar usar español neutro para mayor alcance.'
            })
        
        return suggestions

    def get_english_specific_suggestions(self, analysis):
        """Sugerencias específicas para contenido en inglés"""
        suggestions = []
        
        lang_features = analysis['semantic_analysis'].get('language_specific_features', {})
        
        # Verificar uso de contracciones
        contractions = lang_features.get('contractions', 0)
        word_count = analysis['basic_metrics']['word_count']
        
        if contractions / word_count > 0.05:  # Muchas contracciones
            suggestions.append({
                'type': 'language_formality',
                'priority': 'low',
                'message': 'High usage of contractions detected. Consider more formal tone.',
                'action': 'Reduce contractions for more professional content.'
            })
        
        return suggestions