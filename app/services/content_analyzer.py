import nltk
from textstat import flesch_reading_ease, flesch_kincaid_grade, automated_readability_index
import spacy
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

class ContentAnalyzer:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.nlp = spacy.load('en_core_web_sm')
        self.stop_words = set(nltk.corpus.stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
    def comprehensive_analysis(self, content, target_keywords, competitor_contents):
        """Análisis completo de contenido"""
        cache_key = f"content_analysis:{hash(content)}:{hash(str(target_keywords))}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        analysis = {
            'basic_metrics': self.get_basic_metrics(content),
            'readability': self.analyze_readability(content),
            'keyword_analysis': self.analyze_keywords(content, target_keywords),
            'semantic_analysis': self.semantic_analysis(content),
            'structure_analysis': self.analyze_structure(content),
            'competitor_comparison': self.compare_with_competitors(content, competitor_contents),
            'optimization_suggestions': [],
            'content_score': 0
        }
        
        # Generar sugerencias basadas en el análisis
        analysis['optimization_suggestions'] = self.generate_suggestions(analysis)
        analysis['content_score'] = self.calculate_content_score(analysis)
        
        # Cache por 1 hora
        self.cache.set(cache_key, analysis, 3600)
        return analysis

    def get_basic_metrics(self, content):
        """Métricas básicas del contenido"""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        return {
            'word_count': len(words),
            'character_count': len(content),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'paragraph_count': len([p for p in paragraphs if p.strip()]),
            'avg_words_per_sentence': len(words) / max(len(sentences), 1),
            'avg_sentences_per_paragraph': len(sentences) / max(len(paragraphs), 1)
        }

    def analyze_readability(self, content):
        """Análisis de legibilidad"""
        try:
            return {
                'flesch_reading_ease': flesch_reading_ease(content),
                'flesch_kincaid_grade': flesch_kincaid_grade(content),
                'automated_readability_index': automated_readability_index(content),
                'reading_level': self.get_reading_level(flesch_reading_ease(content)),
                'complex_words': self.count_complex_words(content),
                'passive_voice_percentage': self.calculate_passive_voice(content)
            }
        except:
            return {
                'flesch_reading_ease': 0,
                'flesch_kincaid_grade': 0,
                'automated_readability_index': 0,
                'reading_level': 'Unknown',
                'complex_words': 0,
                'passive_voice_percentage': 0
            }

    def get_reading_level(self, flesch_score):
        """Determinar nivel de lectura basado en Flesch score"""
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
        elif flesch_score >= 30:
            return 'Difficult'
        else:
            return 'Very Difficult'

    def count_complex_words(self, content):
        """Contar palabras complejas (3+ sílabas)"""
        words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
        complex_words = 0
        
        for word in words:
            if self.count_syllables(word) >= 3:
                complex_words += 1
        
        return complex_words

    def count_syllables(self, word):
        """Contar sílabas en una palabra"""
        vowels = 'aeiouy'
        count = 0
        prev_was_vowel = False
        
        for char in word.lower():
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        
        if word.endswith('e'):
            count -= 1
        
        return max(1, count)

    def calculate_passive_voice(self, content):
        """Calcular porcentaje de voz pasiva"""
        doc = self.nlp(content)
        passive_count = 0
        total_sentences = len(list(doc.sents))
        
        for sent in doc.sents:
            if self.is_passive_voice(sent):
                passive_count += 1
        
        return (passive_count / max(total_sentences, 1)) * 100

    def is_passive_voice(self, sentence):
        """Detectar si una oración está en voz pasiva"""
        passive_markers = ['is', 'are', 'was', 'were', 'been', 'being']
        tokens = [token.text.lower() for token in sentence]
        
        for i, token in enumerate(tokens):
            if token in passive_markers and i < len(tokens) - 1:
                next_token = sentence[i + 1]
                if next_token.tag_ in ['VBN']:  # Past participle
                    return True
        return False

    def analyze_keywords(self, content, target_keywords):
        """Análisis de keywords"""
        content_lower = content.lower()
        word_count = len(content.split())
        
        keyword_analysis = {}
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            occurrences = content_lower.count(keyword_lower)
            density = (occurrences / word_count) * 100 if word_count > 0 else 0
            
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
                'occurrences': occurrences,
                'density': round(density, 2),
                'positions': positions,
                'in_title': keyword_lower in content_lower[:100],  # Primeros 100 chars
                'optimal_density': self.get_optimal_density(keyword),
                'density_status': self.evaluate_density(density, keyword)
            }
        
        return keyword_analysis

    def get_optimal_density(self, keyword):
        """Obtener densidad óptima para una keyword"""
        word_count = len(keyword.split())
        if word_count == 1:
            return 1.5  # 1-2% para keywords de una palabra
        elif word_count == 2:
            return 1.0  # 0.5-1.5% para frases de dos palabras
        else:
            return 0.5  # 0.3-0.7% para frases largas

    def evaluate_density(self, current_density, keyword):
        """Evaluar si la densidad es óptima"""
        optimal = self.get_optimal_density(keyword)
        
        if current_density == 0:
            return 'missing'
        elif current_density < optimal * 0.5:
            return 'too_low'
        elif current_density > optimal * 2:
            return 'too_high'
        else:
            return 'optimal'

    def semantic_analysis(self, content):
        """Análisis semántico del contenido"""
        doc = self.nlp(content)
        
        # Entidades nombradas
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        entity_types = Counter([ent.label_ for ent in doc.ents])
        
        # Frases nominales importantes
        noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
        
        # Palabras clave por TF-IDF
        try:
            tfidf_matrix = self.vectorizer.fit_transform([content])
            feature_names = self.vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Top 20 términos por TF-IDF
            top_terms = sorted(zip(feature_names, tfidf_scores), key=lambda x: x[1], reverse=True)[:20]
        except:
            top_terms = []
        
        return {
            'entities': entities[:20],  # Top 20 entidades
            'entity_types': dict(entity_types),
            'noun_phrases': noun_phrases[:15],  # Top 15 frases nominales
            'semantic_density': len(entities) / len(content.split()) if content.split() else 0,
            'top_terms': top_terms,
            'topic_diversity': len(set([ent.label_ for ent in doc.ents]))
        }

    def analyze_structure(self, content):
        """Análisis de estructura del contenido"""
        lines = content.split('\n')
        
        # Detectar headings (basado en patrones comunes)
        headings = {
            'h1': len([line for line in lines if line.strip().startswith('#') and not line.strip().startswith('##')]),
            'h2': len([line for line in lines if line.strip().startswith('##') and not line.strip().startswith('###')]),
            'h3': len([line for line in lines if line.strip().startswith('###')])
        }
        
        # Detectar listas
        bullet_points = len([line for line in lines if line.strip().startswith(('*', '-', '•'))])
        numbered_lists = len([line for line in lines if re.match(r'^\s*\d+\.', line.strip())])
        
        # Detectar párrafos
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        return {
            'headings': headings,
            'total_headings': sum(headings.values()),
            'bullet_points': bullet_points,
            'numbered_lists': numbered_lists,
            'paragraph_count': len(paragraphs),
            'avg_paragraph_length': round(avg_paragraph_length, 1),
            'structure_score': self.calculate_structure_score(headings, paragraphs, bullet_points)
        }

    def calculate_structure_score(self, headings, paragraphs, bullet_points):
        """Calcular puntuación de estructura"""
        score = 0
        
        # Puntos por headings
        if headings['h1'] >= 1:
            score += 20
        if headings['h2'] >= 2:
            score += 20
        if headings['h3'] >= 1:
            score += 10
        
        # Puntos por párrafos bien estructurados
        if 3 <= len(paragraphs) <= 15:
            score += 20
        
        # Puntos por listas
        if bullet_points > 0:
            score += 15
        
        # Bonus por estructura balanceada
        if headings['h2'] > 0 and len(paragraphs) > 2:
            score += 15
        
        return min(score, 100)

    def compare_with_competitors(self, content, competitor_contents):
        """Comparar con contenido de competidores"""
        if not competitor_contents:
            return {'comparison_available': False}
        
        try:
            all_contents = [content] + competitor_contents
            tfidf_matrix = self.vectorizer.fit_transform(all_contents)
            
            # Similarity scores
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # Análisis de gaps
            my_words = set(content.lower().split())
            competitor_words = set()
            for comp_content in competitor_contents:
                competitor_words.update(comp_content.lower().split())
            
            missing_words = competitor_words - my_words
            unique_words = my_words - competitor_words
            
            # Métricas comparativas
            my_metrics = self.get_basic_metrics(content)
            competitor_metrics = [self.get_basic_metrics(comp) for comp in competitor_contents]
            
            avg_competitor_words = np.mean([m['word_count'] for m in competitor_metrics])
            avg_competitor_sentences = np.mean([m['sentence_count'] for m in competitor_metrics])
            
            return {
                'comparison_available': True,
                'similarity_scores': similarities.tolist(),
                'avg_similarity': float(np.mean(similarities)),
                'content_gaps': list(missing_words)[:20],  # Top 20 palabras faltantes
                'unique_content': list(unique_words)[:20],  # Top 20 palabras únicas
                'word_count_comparison': {
                    'mine': my_metrics['word_count'],
                    'competitor_avg': int(avg_competitor_words),
                    'difference': my_metrics['word_count'] - int(avg_competitor_words)
                },
                'sentence_count_comparison': {
                    'mine': my_metrics['sentence_count'],
                    'competitor_avg': int(avg_competitor_sentences),
                    'difference': my_metrics['sentence_count'] - int(avg_competitor_sentences)
                }
            }
        except Exception as e:
            return {'comparison_available': False, 'error': str(e)}

    def generate_suggestions(self, analysis):
        """Generar sugerencias de optimización"""
        suggestions = []
        
        # Sugerencias de longitud de contenido
        word_count = analysis['basic_metrics']['word_count']
        if word_count < 300:
            suggestions.append({
                'type': 'content_length',
                'priority': 'high',
                'message': f'Increase content length. Current: {word_count} words. Recommended: 500+ words.',
                'action': 'Add more comprehensive information and details.'
            })
        elif word_count > 3000:
            suggestions.append({
                'type': 'content_length',
                'priority': 'medium',
                'message': f'Content is very long ({word_count} words). Consider breaking into multiple pages.',
                'action': 'Split content or add table of contents for better user experience.'
            })
        
        # Sugerencias de legibilidad
        flesch_score = analysis['readability']['flesch_reading_ease']
        if flesch_score < 30:
            suggestions.append({
                'type': 'readability',
                'priority': 'high',
                'message': 'Content is very difficult to read. Simplify language and sentence structure.',
                'action': 'Use shorter sentences, simpler words, and active voice.'
            })
        elif flesch_score < 50:
            suggestions.append({
                'type': 'readability',
                'priority': 'medium',
                'message': 'Content readability can be improved.',
                'action': 'Consider using simpler language and shorter sentences.'
            })
        
        # Sugerencias de keywords
        for keyword, data in analysis['keyword_analysis'].items():
            if data['density_status'] == 'missing':
                suggestions.append({
                    'type': 'keyword_missing',
                    'priority': 'high',
                    'message': f'Target keyword "{keyword}" is not found in content.',
                    'action': f'Add "{keyword}" naturally throughout the content.'
                })
            elif data['density_status'] == 'too_low':
                suggestions.append({
                    'type': 'keyword_density',
                    'priority': 'medium',
                    'message': f'Keyword "{keyword}" density is too low ({data["density"]}%).',
                    'action': f'Increase usage to ~{data["optimal_density"]}% density.'
                })
            elif data['density_status'] == 'too_high':
                suggestions.append({
                    'type': 'keyword_density',
                    'priority': 'medium',
                    'message': f'Keyword "{keyword}" density is too high ({data["density"]}%).',
                    'action': 'Reduce keyword usage to avoid over-optimization.'
                })
        
        # Sugerencias de estructura
        headings = analysis['structure_analysis']['headings']
        if headings['h1'] == 0:
            suggestions.append({
                'type': 'structure',
                'priority': 'high',
                'message': 'No H1 heading found.',
                'action': 'Add a clear H1 heading that includes your main keyword.'
            })
        
        if headings['h2'] < 2 and word_count > 500:
            suggestions.append({
                'type': 'structure',
                'priority': 'medium',
                'message': 'Add more H2 headings to improve content structure.',
                'action': 'Break content into sections with descriptive H2 headings.'
            })
        
        # Sugerencias basadas en comparación con competidores
        if analysis['competitor_comparison']['comparison_available']:
            comp_data = analysis['competitor_comparison']
            word_diff = comp_data['word_count_comparison']['difference']
            
            if word_diff < -200:
                suggestions.append({
                    'type': 'competitor_analysis',
                    'priority': 'medium',
                    'message': f'Content is {abs(word_diff)} words shorter than competitor average.',
                    'action': 'Consider adding more comprehensive information to match competitor depth.'
                })
            
            if comp_data['content_gaps']:
                suggestions.append({
                    'type': 'content_gaps',
                    'priority': 'medium',
                    'message': f'Found {len(comp_data["content_gaps"])} terms commonly used by competitors.',
                    'action': f'Consider including terms like: {", ".join(comp_data["content_gaps"][:5])}'
                })
        
        return suggestions

    def calculate_content_score(self, analysis):
        """Calcular puntuación general del contenido"""
        score = 0
        
        # Puntuación por longitud (max 25 puntos)
        word_count = analysis['basic_metrics']['word_count']
        if 300 <= word_count <= 2000:
            score += 25
        elif 200 <= word_count < 300 or 2000 < word_count <= 3000:
            score += 15
        elif word_count > 100:
            score += 5
        
        # Puntuación por legibilidad (max 20 puntos)
        flesch_score = analysis['readability']['flesch_reading_ease']
        if 60 <= flesch_score <= 80:
            score += 20
        elif 50 <= flesch_score < 60 or 80 < flesch_score <= 90:
            score += 15
        elif flesch_score >= 30:
            score += 10
        
        # Puntuación por keywords (max 25 puntos)
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
        
        # Puntuación por estructura (max 20 puntos)
        score += analysis['structure_analysis']['structure_score'] * 0.2
        
        # Puntuación por diversidad semántica (max 10 puntos)
        topic_diversity = analysis['semantic_analysis']['topic_diversity']
        if topic_diversity >= 5:
            score += 10
        elif topic_diversity >= 3:
            score += 7
        elif topic_diversity >= 1:
            score += 4
        
        return min(round(score), 100)

    def analyze_competitors(self, keywords, my_domain, top_n=5):
        """Análisis completo de competidores"""
        cache_key = f"competitor_analysis:{hash(str(keywords))}:{my_domain}:{top_n}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Implementar scraping de competidores sería muy extenso aquí
        # Por ahora retornamos estructura de ejemplo
        result = {
            'keywords_analyzed': keywords,
            'my_domain': my_domain,
            'competitors_found': [],
            'content_gaps': [],
            'opportunities': [],
            'analysis_timestamp': str(np.datetime64('now'))
        }
        
        # Cache por 24 horas
        self.cache.set(cache_key, result, 86400)
        return result