import nltk
from textstat import flesch_reading_ease
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse, urljoin
import time
import logging
import math

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from ..utils.language_detector import LanguageDetector

class MultilingualContentAnalyzer:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.language_detector = LanguageDetector()
        self.nlp_models = {}
        self.load_models()
        
        # Headers para scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        # AGREGAR: Inicialización de capacidades IA
        self.semantic_model_available = False
        self.sentence_model = None
        self.openai_available = False
        
        try:
            from sentence_transformers import SentenceTransformer
            self.sentence_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
            self.semantic_model_available = True
            logger.info("✅ Sentence Transformers disponible")
        except ImportError:
            logger.info("ℹ️ Sentence Transformers no disponible")
        
        # Preparar OpenAI si está configurado
        if hasattr(self, 'openai_client') and self.openai_client:
            self.openai_available = True
            logger.info("✅ OpenAI disponible")
        
    def load_models(self):
        """Cargar modelos disponibles"""
        if not SPACY_AVAILABLE:
            logger.info("⚠️ Spacy no disponible, usando análisis básico")
            return
            
        for lang_code, config in self.language_detector.get_supported_languages().items():
            try:
                model_name = config['spacy_model']
                self.nlp_models[lang_code] = spacy.load(model_name)
                logger.info(f"✅ Modelo {model_name} cargado")
            except OSError:
                logger.info(f"❌ Modelo {model_name} no encontrado")

   
    def extract_keywords_from_content(self, content, language, max_keywords=5):
        """Extraer keywords principales del contenido"""
        try:
            # Limpiar texto
            text = re.sub(r'[^\w\s]', ' ', content.lower())
            words = text.split()
            
            # Filtrar stop words básicas
            stop_words = self.get_stop_words(language)
            filtered_words = [w for w in words if len(w) > 3 and w not in stop_words]
            
            # Contar frecuencias
            word_freq = Counter(filtered_words)
            
            # Extraer frases de 2-3 palabras también
            phrases = []
            for i in range(len(words)-1):
                if len(words[i]) > 3 and len(words[i+1]) > 3:
                    phrase = f"{words[i]} {words[i+1]}"
                    if not any(stop in phrase for stop in stop_words):
                        phrases.append(phrase)
            
            phrase_freq = Counter(phrases)
            
            # Combinar palabras individuales y frases
            keywords = []
            
            # Top palabras individuales
            for word, freq in word_freq.most_common(3):
                if freq > 1:  # Aparece al menos 2 veces
                    keywords.append(word)
            
            # Top frases
            for phrase, freq in phrase_freq.most_common(2):
                if freq > 1:
                    keywords.append(phrase)
            
            return keywords[:max_keywords] if keywords else ['contenido', 'información']
            
        except Exception as e:
            logger.info(f"Error extrayendo keywords: {e}")
            return ['contenido', 'información']

    def get_stop_words(self, language):
        """Stop words exhaustivas por idioma usando NLTK"""
        stop_words = {
            'es': set(nltk.corpus.stopwords.words('spanish')),
            'en': set(nltk.corpus.stopwords.words('english')),
            'fr': set(nltk.corpus.stopwords.words('french')),
            'de': set(nltk.corpus.stopwords.words('german')),
            'pt': set(nltk.corpus.stopwords.words('portuguese')),
            'it': set(nltk.corpus.stopwords.words('italian'))
        }
        # Si el idioma no está soportado, usa inglés por defecto
        return stop_words.get(language, stop_words['en'])

    def auto_competitive_analysis(self, keywords, my_content, language):
        """Análisis competitivo completamente automático"""
        try:
            from ..services.serp_scraper import MultilingualSerpScraper
            
            serp_scraper = MultilingualSerpScraper(self.cache)
            competitors_data = {}
            all_competitor_contents = []
            
            # Para cada keyword, obtener top competidores
            for keyword in keywords:
                logger.info(f"🔍 Buscando competidores para: {keyword}")
                
                # Obtener SERP
                serp_results = serp_scraper.get_serp_results(
                    keyword, 
                    location='US' if language == 'en' else 'ES',
                    language=language,
                    pages=1
                )
                
                if not serp_results or 'organic_results' not in serp_results:
                    continue
                
                # Obtener top 3-5 resultados
                top_results = serp_results['organic_results'][:5]
                keyword_competitors = []
                
                for result in top_results:
                    url = result.get('link', '')
                    if not url:
                        continue
                    
                    # Hacer scraping del contenido
                    logger.info(f"📄 Scrapeando: {url}")
                    content = self.scrape_content(url)
                    
                    if content and len(content) > 200:  # Mínimo de contenido
                        competitor_data = {
                            'url': url,
                            'title': result.get('title', ''),
                            'position': result.get('position', 0),
                            'content': content,
                            'content_metrics': self.get_basic_metrics(content),
                            'keyword_analysis': self.analyze_keywords(content, [keyword], language)
                        }
                        
                        keyword_competitors.append(competitor_data)
                        all_competitor_contents.append(content)
                        
                        # Límite para no sobrecargar
                        if len(keyword_competitors) >= 3:
                            break
                    
                    # Delay entre requests
                    time.sleep(1)
                
                competitors_data[keyword] = keyword_competitors
            
            if not all_competitor_contents:
                return None
            
            # Análisis comparativo
            return self.compare_with_competitors(
                my_content, keywords, competitors_data, all_competitor_contents, language
            )
            
        except Exception as e:
            logger.info(f"Error en análisis competitivo: {e}")
            return None

    def scrape_content(self, url):
        """Scraping inteligente del contenido de una página"""
        try:
            # Verificar cache
            cache_key = f"scraped_content:{hash(url)}"
            cached_content = self.cache.get(cache_key)
            if cached_content:
                return cached_content
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remover scripts, styles, etc.
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Intentar encontrar el contenido principal
            content_selectors = [
                'article',
                '[role="main"]',
                '.content',
                '.post-content',
                '.entry-content',
                '.main-content',
                'main',
                '.container'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(strip=True)
                        if len(text) > len(content):
                            content = text
                    if len(content) > 500:  # Suficiente contenido encontrado
                        break
            
            # Si no encontró contenido específico, usar todo el body
            if len(content) < 200:
                body = soup.find('body')
                if body:
                    content = body.get_text(strip=True)
            
            # Limpiar y normalizar
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            
            # Cache por 24 horas
            if len(content) > 100:
                self.cache.set(cache_key, content, 86400)
            
            return content
            
        except Exception as e:
            logger.info(f"Error scrapeando {url}: {e}")
            return ""

    def compare_with_competitors(self, my_content, keywords, competitors_data, all_competitor_contents, language):
        """Comparación detallada con competidores"""
        
        my_metrics = self.get_basic_metrics(my_content)
        my_keyword_analysis = self.analyze_keywords(my_content, keywords, language)
        
        # Métricas agregadas de competidores
        competitor_metrics = [self.get_basic_metrics(content) for content in all_competitor_contents]
        
        if not competitor_metrics:
            return None
        
        avg_competitor_words = sum(m['word_count'] for m in competitor_metrics) / len(competitor_metrics)
        avg_competitor_sentences = sum(m['sentence_count'] for m in competitor_metrics) / len(competitor_metrics)
        avg_competitor_paragraphs = sum(m['paragraph_count'] for m in competitor_metrics) / len(competitor_metrics)
        
        # Análisis por keyword
        keyword_insights = {}
        for keyword in keywords:
            if keyword in competitors_data:
                competitors = competitors_data[keyword]
                
                keyword_densities = []
                title_usage = 0
                content_patterns = []
                
                for comp in competitors:
                    kw_analysis = comp.get('keyword_analysis', {})
                    if keyword in kw_analysis:
                        keyword_densities.append(kw_analysis[keyword]['density'])
                        if kw_analysis[keyword]['in_title']:
                            title_usage += 1
                    
                    # Extraer patrones de contenido relacionados con la keyword
                    content = comp['content'].lower()
                    sentences_with_keyword = [
                        sent.strip() for sent in content.split('.')
                        if keyword.lower() in sent and len(sent) > 20
                    ]
                    content_patterns.extend(sentences_with_keyword[:3])
                
                avg_density = sum(keyword_densities) / len(keyword_densities) if keyword_densities else 0
                my_density = my_keyword_analysis.get(keyword, {}).get('density', 0)
                
                keyword_insights[keyword] = {
                    'my_density': my_density,
                    'competitor_avg_density': avg_density,
                    'density_gap': avg_density - my_density,
                    'title_usage_rate': (title_usage / len(competitors)) * 100 if competitors else 0,
                    'my_title_usage': my_keyword_analysis.get(keyword, {}).get('in_title', False),
                    'content_patterns': content_patterns[:5],  # Top 5 patrones
                    'competitors_analyzed': len(competitors)
                }
        
        return {
            'content_comparison': {
                'my_word_count': my_metrics['word_count'],
                'competitor_avg_words': int(avg_competitor_words),
                'word_count_gap': my_metrics['word_count'] - avg_competitor_words,
                'my_paragraphs': my_metrics['paragraph_count'],
                'competitor_avg_paragraphs': avg_competitor_paragraphs,
                'paragraph_gap': my_metrics['paragraph_count'] - avg_competitor_paragraphs
            },
            'keyword_insights': keyword_insights,
            'competitors_analyzed': len(all_competitor_contents),
            'total_keywords_analyzed': len(keywords)
        }

    def generate_competitive_suggestions(self, competitive_data, analysis, keywords):
        """Generar sugerencias específicas estilo Surfer SEO"""
        suggestions = []
        
        content_comp = competitive_data.get('content_comparison', {})
        keyword_insights = competitive_data.get('keyword_insights', {})
        
        # 1. Sugerencias de longitud de contenido
        word_gap = content_comp.get('word_count_gap', 0)
        if word_gap < -200:  # Mi contenido es significativamente más corto
            target_words = content_comp.get('competitor_avg_words', 0)
            suggestions.append({
                'type': 'content_length',
                'priority': 'high',
                'category': 'Content Length',
                'message': f'Expandir contenido. Competidores top promedian {target_words} palabras vs tus {content_comp.get("my_word_count", 0)}.',
                'current_value': content_comp.get('my_word_count', 0),
                'target_value': target_words,
                'improvement': f'Añadir ~{abs(int(word_gap))} palabras'
            })
        elif word_gap > 500:  # Mi contenido es mucho más largo
            suggestions.append({
                'type': 'content_length',
                'priority': 'medium',
                'category': 'Content Length',
                'message': f'Considerar reducir contenido. Tu contenido es {int(word_gap)} palabras más largo que la competencia.',
                'current_value': content_comp.get('my_word_count', 0),
                'target_value': content_comp.get('competitor_avg_words', 0),
                'improvement': 'Contenido más conciso puede mejorar UX'
            })
        
        # 2. Sugerencias por keyword específica
        for keyword, insights in keyword_insights.items():
            density_gap = insights.get('density_gap', 0)
            
            # Densidad de keyword
            if density_gap > 0.5:  # Competidores usan más la keyword
                suggestions.append({
                    'type': 'keyword_density',
                    'priority': 'high',
                    'category': 'Keyword Optimization',
                    'keyword': keyword,
                    'message': f'Aumentar uso de "{keyword}". Competidores: {insights["competitor_avg_density"]:.1f}% vs tuyo: {insights["my_density"]:.1f}%',
                    'current_value': f'{insights["my_density"]:.1f}%',
                    'target_value': f'{insights["competitor_avg_density"]:.1f}%',
                    'improvement': f'Usar "{keyword}" ~{int(density_gap * content_comp.get("my_word_count", 100) / 100)} veces más'
                })
            
            # Uso en título
            title_usage_rate = insights.get('title_usage_rate', 0)
            my_title_usage = insights.get('my_title_usage', False)
            
            if title_usage_rate > 60 and not my_title_usage:
                suggestions.append({
                    'type': 'title_optimization',
                    'priority': 'high',
                    'category': 'Title Optimization',
                    'keyword': keyword,
                    'message': f'Incluir "{keyword}" en el título. {title_usage_rate:.0f}% de competidores top lo hacen.',
                    'current_value': 'No incluida en título',
                    'target_value': 'Incluir en título',
                    'improvement': 'Optimizar título para mejor CTR'
                })
            
            # Patrones de contenido
            content_patterns = insights.get('content_patterns', [])
            if content_patterns:
                # Extraer temas/conceptos relacionados de los patrones
                related_terms = self.extract_related_terms_from_patterns(content_patterns, keyword, analysis.get('detected_language', 'en'))
                if related_terms:
                    suggestions.append({
                        'type': 'semantic_content',
                        'priority': 'medium',
                        'category': 'Semantic Optimization',
                        'keyword': keyword,
                        'message': f'Para "{keyword}", considera incluir términos relacionados que usan competidores.',
                        'current_value': 'Términos relacionados limitados',
                        'target_value': f'Incluir: {", ".join(related_terms[:3])}',
                        'improvement': f'Añadir contexto semántico con: {", ".join(related_terms[:5])}',
                        'related_terms': related_terms
                    })
        
        # 3. Sugerencias de estructura
        paragraph_gap = content_comp.get('paragraph_gap', 0)
        if paragraph_gap < -3:  # Muchos menos párrafos que competidores
            suggestions.append({
                'type': 'content_structure',
                'priority': 'medium',
                'category': 'Content Structure',
                'message': f'Mejorar estructura. Competidores usan ~{content_comp.get("competitor_avg_paragraphs", 0):.0f} párrafos vs tus {content_comp.get("my_paragraphs", 0)}.',
                'current_value': f'{content_comp.get("my_paragraphs", 0)} párrafos',
                'target_value': f'~{content_comp.get("competitor_avg_paragraphs", 0):.0f} párrafos',
                'improvement': 'Dividir contenido en más secciones para mejor legibilidad'
            })
        
        # 4. Sugerencia general de competitividad
        competitors_count = competitive_data.get('competitors_analyzed', 0)
        if competitors_count > 0:
            suggestions.append({
                'type': 'competitive_analysis',
                'priority': 'info',
                'category': 'Competitive Intelligence',
                'message': f'Análisis basado en {competitors_count} competidores top en SERPs.',
                'current_value': f'Analizados {competitors_count} competidores',
                'target_value': 'Implementar sugerencias competitivas',
                'improvement': 'Aplicar las optimizaciones sugeridas para superar a la competencia'
            })
        
        return suggestions

    def extract_related_terms_from_patterns(self, patterns, main_keyword, language=None):
        """Extraer términos relacionados de los patrones de contenido competidores"""
        try:
            all_text = ' '.join(patterns).lower()
            all_text = all_text.replace(main_keyword.lower(), '')
            # Regex por idioma (soporte acentos en ES/PT/IT/FR/DE)
            lang = language or self.language_detector.detect_language(all_text) or 'en'
            if language in ('es', 'pt', 'it', 'fr', 'de'):
                words = re.findall(r'\b[a-záéíóúüñçàèìòùäëïöüß]+\b', all_text, flags=re.IGNORECASE)
            else:
                words = re.findall(r'\b[a-zA-Z]+\b', all_text)
            stop_words = self.get_stop_words(language)
            significant = [w for w in words if len(w) > 4 and w not in stop_words]
            word_freq = Counter(significant)
            return [w for w, c in word_freq.most_common(8) if c > 1]
            
        except Exception as e:
            logger.info(f"Error extrayendo términos relacionados: {e}")
            return []

    def analyze_competitors(self, keywords, my_domain, top_n=5):
        """Método público para análisis de competidores independiente"""
        try:
            from ..services.serp_scraper import MultilingualSerpScraper
            
            logger.info(f"🏆 Analizando competidores para keywords: {keywords}")
            
            serp_scraper = MultilingualSerpScraper(self.cache)
            competitors_found = {}
            all_competitors = []
            
            for keyword in keywords:
                logger.info(f"🔍 Buscando competidores para: {keyword}")
                
                # Obtener SERP
                serp_results = serp_scraper.get_serp_results(keyword, location='US', pages=1)
                
                if not serp_results or 'organic_results' not in serp_results:
                    continue
                
                # Filtrar nuestro dominio y obtener competidores
                competitors = []
                for result in serp_results['organic_results'][:top_n * 2]:  # Buscar más para filtrar
                    url = result.get('link', '')
                    if url and my_domain not in url:
                        competitor_domain = urlparse(url).netloc
                        
                        # Evitar duplicados por dominio
                        if not any(comp['domain'] == competitor_domain for comp in competitors):
                            competitors.append({
                                'domain': competitor_domain,
                                'url': url,
                                'title': result.get('title', ''),
                                'position': result.get('position', 0),
                                'snippet': result.get('snippet', '')
                            })
                        
                        if len(competitors) >= top_n:
                            break
                
                competitors_found[keyword] = competitors
                all_competitors.extend(competitors)
            
            # Análisis agregado
            unique_competitors = {}
            for comp in all_competitors:
                domain = comp['domain']
                if domain not in unique_competitors:
                    unique_competitors[domain] = {
                        'domain': domain,
                        'urls': [comp['url']],
                        'titles': [comp['title']],
                        'avg_position': comp['position'],
                        'keywords_ranking': [list(competitors_found.keys())[0]]  # Simplificado
                    }
                else:
                    unique_competitors[domain]['urls'].append(comp['url'])
                    unique_competitors[domain]['titles'].append(comp['title'])
            
            return {
                'keywords_analyzed': keywords,
                'my_domain': my_domain,
                'competitors_by_keyword': competitors_found,
                'unique_competitors': list(unique_competitors.values()),
                'total_competitors_found': len(unique_competitors),
                'analysis_summary': {
                    'avg_competitors_per_keyword': len(all_competitors) / len(keywords) if keywords else 0,
                    'most_common_competitors': self.get_most_frequent_competitors(all_competitors)
                }
            }
            
        except Exception as e:
            logger.info(f"Error analizando competidores: {e}")
            return {
                'error': f'Error analyzing competitors: {str(e)}',
                'competitors_found': 0,
                'keywords_analyzed': keywords
            }

    def get_most_frequent_competitors(self, competitors):
        """Encontrar competidores que aparecen en múltiples keywords"""
        domain_freq = Counter(comp['domain'] for comp in competitors)
        return [
            {'domain': domain, 'appearances': count}
            for domain, count in domain_freq.most_common(5)
        ]

    # Métodos existentes que ya tienes (mantener sin cambios)
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
                'category': 'Content Basics',
                'message': f'{msg}. Actual: {word_count} palabras.',
                'current_value': f'{word_count} palabras',
                'target_value': '300+ palabras',
                'improvement': 'Añadir más contenido de valor'
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
        
        # Bonus por análisis competitivo
        if analysis.get('competitive_analysis'):
            score += 10  # Bonus por tener datos competitivos
        
        return min(round(score), 100)
   
    
    def extract_semantic_terms(self, content, language, target_keywords, max_terms=25):  # AUMENTAR
        """Devolver más términos con sistema de prioridades"""
        
        # NIVEL 1: Algoritmo base con más términos
        base_terms = self._extract_terms_universal_algorithm(content, language, target_keywords, max_terms * 2)
        
        # NIVEL 2: Enhancement con Sentence Transformers
        if self.semantic_model_available and len(base_terms) > 0:
            enhanced_terms = self._enhance_with_sentence_transformers(
                base_terms, content, language, target_keywords
            )
        else:
            enhanced_terms = base_terms
        
        # NIVEL 3: Clasificar por prioridades y devolver MÁS términos
        return self._categorize_and_expand_terms(enhanced_terms, max_terms)

    def _categorize_and_expand_terms(self, terms, max_terms):
        """Clasificar términos por prioridad estilo Surfer"""
        
        categorized = {
            'high_priority': {},     # 8-10 términos
            'medium_priority': {},   # 10-12 términos  
            'low_priority': {}       # 5-8 términos
        }
        
        for term, frequency in terms.items():
            # Criterios para clasificación
            term_length = len(term)
            
            if frequency >= 5 and term_length >= 6:
                categorized['high_priority'][term] = frequency
            elif frequency >= 3 and term_length >= 5:
                categorized['medium_priority'][term] = frequency  
            elif frequency >= 2:
                categorized['low_priority'][term] = frequency
        
        # Combinar manteniendo balance
        final_terms = {}
        
        # Tomar hasta 10 high priority
        high_terms = dict(sorted(categorized['high_priority'].items(), 
                            key=lambda x: x[1], reverse=True)[:10])
        final_terms.update(high_terms)
        
        # Tomar hasta 12 medium priority  
        medium_terms = dict(sorted(categorized['medium_priority'].items(), 
                                key=lambda x: x[1], reverse=True)[:12])
        final_terms.update(medium_terms)
        
        # Completar con low priority hasta llegar a max_terms
        remaining_slots = max_terms - len(final_terms)
        if remaining_slots > 0:
            low_terms = dict(sorted(categorized['low_priority'].items(), 
                                key=lambda x: x[1], reverse=True)[:remaining_slots])
            final_terms.update(low_terms)
        
        return final_terms
    

    def _extract_terms_universal_algorithm(self, content, language, target_keywords, max_terms):
        """NIVEL 1: Algoritmo universal mejorado (reemplaza _extract_terms_technical_algorithm)"""
        
        clean_content = re.sub(r'[^\w\s]', ' ', content.lower())
        words = clean_content.split()
        
        # Filtrado técnico básico
        stop_words = self.get_stop_words(language)
        
        technically_valid = [
            word for word in words 
            if len(word) > 3 and word not in stop_words 
            and not any(kw.lower() in word.lower() for kw in target_keywords)
            and not self._is_technical_junk_universal(word)
        ]
        
        word_freq = Counter(technically_valid)
        
        # FILTRADO SEMÁNTICO UNIVERSAL (NUEVO)
        semantic_terms = {}
        for word, count in word_freq.most_common(max_terms * 4):
            if count >= 3:
                # Extraer contextos
                contexts = self._extract_term_contexts_detailed(content, word, window=8)
                
                # Aplicar filtrado semántico universal
                if self._is_semantically_valuable_universal(word, contexts, language):
                    semantic_terms[word] = count
        
        return dict(sorted(semantic_terms.items(), key=lambda x: x[1], reverse=True)[:max_terms])
    
    

    def _is_technically_valid_term_complete(self, word, exclude_keywords, language, stop_words):
        """TU ALGORITMO COMPLETO de validación técnica"""
        
        # Longitud válida
        if len(word) < 4 or len(word) > 20:
            return False
        
        # No es número puro
        if word.isdigit():
            return False
        
        # No es keyword principal
        if any(kw.lower() in word.lower() for kw in exclude_keywords):
            return False
        
        # Stop words técnicas
        if word in stop_words:
            return False
        
        # Patrones problemáticos (TU LISTA COMPLETA)
        problematic_patterns = [
            r'\d{3,}',        # 3+ dígitos consecutivos
            r'www\.',         # URLs
            r'http',          # Enlaces
            r'@',             # Emails/mentions
            r'\.com|\.org',   # Dominios
            r'^[a-z]{1,2}$',  # Letras sueltas (a, de, el, etc.)
        ]
        
        if any(re.search(pattern, word) for pattern in problematic_patterns):
            return False
        
        return True

    def _get_comprehensive_technical_stops(self, language):
        """TU LISTA COMPLETA de stop words técnicas"""
        technical_stops = {
            'es': {
                # Meta-términos web/referencias
                'artículo', 'página', 'sitio', 'website', 'enlace', 'link', 
                'comentario', 'usuario', 'autor', 'fecha', 'publicado', 'actualizado',
                'versión', 'edición', 'capítulo', 'sección', 'párrafo',
                'imagen', 'foto', 'video', 'audio', 'archivo', 'documento',
                
                # Términos de navegación
                'inicio', 'home', 'menú', 'buscar', 'encontrar', 'siguiente', 'anterior',
                'arriba', 'abajo', 'izquierda', 'derecha', 'centro',
                
                # Términos temporales vagos
                'ahora', 'hoy', 'ayer', 'mañana', 'reciente', 'nuevo', 'viejo', 'actual',
                'antes', 'después', 'durante', 'mientras', 'todavía', 'aún',
                
                # Términos genéricos de cantidad/calidad
                'mucho', 'poco', 'bastante', 'demasiado', 'suficiente',
                'bueno', 'malo', 'mejor', 'peor', 'grande', 'pequeño',
                'fácil', 'difícil', 'simple', 'complejo', 'normal', 'especial',
                
                # Conectores y rellenos
                'realmente', 'verdaderamente', 'obviamente', 'claramente',
                'específicamente', 'particularmente', 'especialmente', 'principalmente',
                'generalmente', 'normalmente', 'usualmente', 'frecuentemente',
                
                # Referencias bibliográficas (universales)
                'fuente', 'referencia', 'cita', 'bibliografía', 'nota', 'pie',
                'índice', 'tabla', 'contenido', 'resumen', 'introducción', 'conclusión'
            },
            'en': {
                'article', 'page', 'site', 'website', 'link', 'url',
                'comment', 'user', 'author', 'date', 'published', 'updated',
                'version', 'edition', 'chapter', 'section', 'paragraph',
                'image', 'photo', 'video', 'audio', 'file', 'document',
                'home', 'menu', 'search', 'find', 'next', 'previous',
                'above', 'below', 'left', 'right', 'center',
                'now', 'today', 'yesterday', 'tomorrow', 'recent', 'new', 'old', 'current',
                'before', 'after', 'during', 'while', 'still', 'yet',
                'much', 'little', 'enough', 'too', 'quite',
                'good', 'bad', 'better', 'worse', 'big', 'small',
                'easy', 'hard', 'simple', 'complex', 'normal', 'special',
                'really', 'truly', 'obviously', 'clearly', 'definitely',
                'specifically', 'particularly', 'especially', 'mainly',
                'generally', 'normally', 'usually', 'frequently',
                'source', 'reference', 'citation', 'bibliography', 'note', 'footnote',
                'index', 'table', 'content', 'summary', 'introduction', 'conclusion'
            }
        }
        return technical_stops.get(language, technical_stops['en'])

    def _calculate_technical_quality_complete(self, word, full_content, language):
        """TU ALGORITMO COMPLETO de calidad técnica"""
        
        score = 0.0
        
        # 1. Longitud óptima
        if 5 <= len(word) <= 12:
            score += 0.3
        elif 4 <= len(word) <= 15:
            score += 0.2
        else:
            score += 0.1
        
        # 2. Patrón de caracteres
        letter_ratio = sum(c.isalpha() for c in word) / len(word)
        if letter_ratio >= 0.8:
            score += 0.2
        
        # 3. Frecuencia relativa
        content_words = full_content.lower().split()
        word_count = content_words.count(word)
        total_words = len(content_words)
        
        if total_words > 0:
            frequency = word_count / total_words
            if 0.002 <= frequency <= 0.02:  # Frecuencia óptima (no muy rara, no muy común)
                score += 0.3
            elif 0.001 <= frequency <= 0.03:
                score += 0.2
        
        # 4. Patrones limpios
        clean_patterns = [
            r'^[a-záéíóúüñ]+$',  # Solo letras (español)
            r'^[a-zA-Z]+$'       # Solo letras (inglés)
        ]
        
        if any(re.match(pattern, word) for pattern in clean_patterns):
            score += 0.2
        
        return min(score, 1.0)

    def _enhance_with_sentence_transformers(self, base_terms, content, language, target_keywords):
        """NIVEL 2: Enhancement con Sentence Transformers"""
        if not self.semantic_model_available:
            return base_terms
        
        try:
            import numpy as np
            
            # Crear embedding del contenido principal
            main_embedding = self.sentence_model.encode([content])
            
            # Evaluar relevancia semántica de cada término
            enhanced_terms = {}
            keyword_context = " ".join(target_keywords)
            keyword_embedding = self.sentence_model.encode([keyword_context])
            
            for term, frequency in base_terms.items():
                # Crear contextos donde aparece el término
                term_contexts = self._extract_term_contexts(content, term)
                
                if term_contexts:
                    context_text = " ".join(term_contexts)
                    context_embedding = self.sentence_model.encode([context_text])
                    
                    # Similitud con keywords principales
                    similarity = np.dot(keyword_embedding, context_embedding.T)[0][0]
                    
                    # Solo mantener términos semánticamente relevantes
                    if similarity > 0.25:  # Umbral de relevancia semántica
                        # Boost por similitud semántica
                        enhanced_frequency = frequency * (1 + similarity)
                        enhanced_terms[term] = enhanced_frequency
                        
            # Ordenar por frecuencia enhanced
            sorted_enhanced = sorted(enhanced_terms.items(), key=lambda x: x[1], reverse=True)

            import gc
            gc.collect()
            return dict(sorted_enhanced[:15])
            
        except Exception as e:
            logger.error(f"Error en Sentence Transformers: {e}")
            return base_terms

    def _extract_term_contexts(self, content, term, window=30):
        """Extraer contextos donde aparece un término"""
        words = content.lower().split()
        contexts = []
        
        for i, word in enumerate(words):
            if term.lower() in word:
                start = max(0, i - window)
                end = min(len(words), i + window)
                context = " ".join(words[start:end])
                contexts.append(context)
                
                if len(contexts) >= 3:  # Máximo 3 contextos
                    break
        
        return contexts

    def _enhance_with_openai(self, terms, content, keywords):
        """NIVEL 3: Enhancement con OpenAI (preparado)"""
        
        if not self.openai_available:
            return terms
        
        try:
            # Preparar contexto optimizado para IA
            terms_list = list(terms.keys())[:10]
            sample_content = content[:800]  # Muestra para no exceder tokens
            
            prompt = f"""
            Analiza estos términos SEO extraídos de competidores para "{keywords[0]}":
            
            TÉRMINOS: {terms_list}
            MUESTRA CONTENIDO: {sample_content}
            
            Evalúa cada término 1-10 en relevancia semántica.
            Sugiere 2-3 términos adicionales importantes.
            
            JSON response:
            {{
                "enhanced_terms": [{{"term": "ejemplo", "relevance": 8}}],
                "suggested_terms": ["nuevo1", "nuevo2"],
                "filtered_out": ["irrelevante1"]
            }}
            """
            
            # Llamada a OpenAI (preparada para cuando esté disponible)
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.2
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            return self._merge_ai_results(terms, ai_result)
            
        except Exception as e:
            logger.error(f"OpenAI enhancement falló: {e}")
            return terms

    def _merge_ai_results(self, base_terms, ai_result):
        """Integrar resultados de IA con análisis base"""
        final_terms = {}
        
        # Aplicar scores de IA a términos base
        for term, frequency in base_terms.items():
            ai_term = next((t for t in ai_result.get('enhanced_terms', []) if t['term'] == term), None)
            if ai_term and ai_term['relevance'] >= 6:
                # Boost por IA
                final_terms[term] = frequency * (ai_term['relevance'] / 10)
            elif term not in ai_result.get('filtered_out', []):
                final_terms[term] = frequency
        
        # Agregar términos sugeridos por IA
        for suggested_term in ai_result.get('suggested_terms', []):
            final_terms[suggested_term] = 5  # Frecuencia estimada
        
        return dict(sorted(final_terms.items(), key=lambda x: x[1], reverse=True)[:15])

    def extract_important_ngrams(self, content, language, target_keywords):
        """Extraer n-gramas priorizando frases más completas (3-4 palabras)"""
        clean_content = re.sub(r'[^\w\s]', ' ', content.lower())
        words = clean_content.split()
        
        ngrams = defaultdict(int)
        stop_words = self.get_stop_words(language)
        
        # CAMBIO: Priorizar n-gramas más largos
        for n in [5, 4, 3, 2]:  # Orden invertido: primero 4-gramas, luego 3, finalmente 2
            for i in range(len(words) - n + 1):
                ngram_words = words[i:i+n]
                
                if self._is_coherent_phrase(ngram_words, stop_words, target_keywords, language):
                    ngram = ' '.join(ngram_words)
                    
                    # BONUS por longitud: n-gramas más largos tienen mayor peso
                    weight_bonus = n * 0.5  # 4-gramas = +2.0, 3-gramas = +1.5, bigramas = +1.0
                    ngrams[ngram] += (1 * weight_bonus)
        
        # Solo frases que aparecen múltiples veces Y tienen sentido
        coherent_ngrams = {}
        for ngram, weighted_count in ngrams.items():
            # Calcular frecuencia real (sin bonus)
            real_count = content.lower().count(ngram)
            
            if real_count >= 2:  # Frecuencia mínima real
                coherence_score = self._calculate_phrase_coherence(ngram, content, target_keywords, language)
                
                # FILTRO ADICIONAL: Priorizar frases más largas con mejor coherencia
                if coherence_score > 0.4:  # Umbral más bajo para compensar longitud
                    # Score final combina frecuencia, longitud y coherencia
                    final_score = weighted_count * coherence_score
                    coherent_ngrams[ngram] = final_score
        
        # Ordenar por score final y tomar los mejores
        return dict(sorted(coherent_ngrams.items(), key=lambda x: x[1], reverse=True)[:15])
    
    def _is_coherent_phrase(self, words, stop_words, target_keywords, language):
        """Verificar coherencia semántica con bonus para frases más largas"""
        
        # 1. Filtros básicos (mantener)
        connective_stops = {
            'es': {'del', 'de', 'la', 'el', 'los', 'las', 'por', 'para', 'con', 'sin', 'que', 'como', 'una', 'uno'},
            'en': {'the', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'to', 'from', 'that', 'which', 'a', 'an'}
        }
        
        conn_stops = connective_stops.get(language, connective_stops['en'])
        
        # Más flexible con frases largas: solo verificar que no EMPIECEN mal
        if words[0] in conn_stops:
            return False
        
        # 2. Para frases de 3+ palabras, ser más permisivo
        if len(words) >= 3:
            # Al menos 60% palabras sustantivas
            substantial_words = sum(1 for word in words if len(word) > 4 and word not in stop_words)
            substantial_ratio = substantial_words / len(words)
            
            return substantial_ratio >= 0.5  # Más permisivo para frases largas
        
        else:  # Bigramas: ser más estricto
            substantial_words = sum(1 for word in words if len(word) > 4 and word not in stop_words)
            substantial_ratio = substantial_words / len(words)
            
            return substantial_ratio >= 0.8  # Más estricto para bigramas

    def _calculate_phrase_coherence(self, phrase, full_content, target_keywords, language):
        """Calcular coherencia con bonus para frases más largas"""
        score = 0.0
        words = phrase.split()
        
        # BONUS BASE por longitud
        length_bonus = {
            2: 0.0,   # Sin bonus para bigramas
            3: 0.2,   # Bonus moderado para trigramas
            4: 0.4,   # Bonus alto para tetragramas
            5: 0.5    # Bonus máximo para 5+ palabras
        }
        
        phrase_length = len(words)
        score += length_bonus.get(phrase_length, 0.5)
        
        # 1. Proximidad a keywords (mantener)
        phrase_contexts = self._extract_term_contexts_detailed(full_content, phrase, window=20)
        if phrase_contexts:
            keyword_proximity = sum(1 for context in phrase_contexts 
                                if any(kw.lower() in context.lower() for kw in target_keywords))
            proximity_ratio = keyword_proximity / len(phrase_contexts)
            score += proximity_ratio * 0.3
        
        # 2. Especificidad técnica (mantener pero ajustar para frases largas)
        technical_words = sum(1 for word in words if len(word) > 6)
        specificity = technical_words / len(words)
        score += specificity * 0.3
        
        # 3. NUEVO: Bonus por "completitud semántica" de frases largas
        if phrase_length >= 3:
            # Verificar que no sea solo relleno + una palabra técnica
            non_filler_words = [w for w in words if len(w) > 5]
            if len(non_filler_words) >= 2:  # Al menos 2 palabras sustantivas
                score += 0.2
        
        return min(score, 1.0)

    def count_term_in_content(self, content, term, language):
        """Contar ocurrencias de un término específico"""
        clean_content = self.clean_content_for_analysis(content)
        term_clean = self.clean_content_for_analysis(term)
        
        # Contar ocurrencias exactas
        exact_count = clean_content.lower().count(term_clean.lower())
        
        # Contar variaciones (plural/singular)
        variations = self.get_term_variations(term_clean, language)
        total_count = exact_count
        
        for variation in variations:
            if variation.lower() != term_clean.lower():
                total_count += clean_content.lower().count(variation.lower())
        
        return total_count

    def get_term_variations(self, term, language):
        """Obtener variaciones de un término (plural, singular, etc.)"""
        variations = [term]
        
        if language == 'es':
            # Variaciones en español
            if term.endswith('s'):
                variations.append(term[:-1])  # Plural a singular
            else:
                variations.append(term + 's')  # Singular a plural
            
            # Variaciones de género básicas
            if term.endswith('o'):
                variations.append(term[:-1] + 'a')
            elif term.endswith('a'):
                variations.append(term[:-1] + 'o')
                
        elif language == 'en':
            # Variaciones en inglés
            if term.endswith('s'):
                variations.append(term[:-1])
            else:
                variations.append(term + 's')
            
            if term.endswith('y'):
                variations.append(term[:-1] + 'ies')
        
        return list(set(variations))

        
        # Análisis básico para keywords principales
        for keyword in target_keywords:
            current_count = self.count_term_in_content(content, keyword, language)
            
            # Estimaciones básicas basadas en longitud del contenido
            if my_word_count < 500:
                optimal = 3
            elif my_word_count < 1000:
                optimal = 5
            else:
                optimal = max(7, int(my_word_count / 200))
            
            recommendations['keywords'].append({
                'term': keyword,
                'type': 'primary_keyword',
                'current_count': current_count,
                'recommended_count': {
                    'min': max(1, int(optimal * 0.6)),
                    'optimal': optimal,
                    'max': int(optimal * 1.4)
                },
                'competitor_average': optimal,  # Estimación
                'priority': 'high' if current_count < optimal * 0.5 else 'medium',
                'competitors_using': 0  # No hay datos
            })
        
        return {
            'term_frequency_analysis': {
                'keywords': recommendations['keywords'],
                'ngrams': recommendations['ngrams'],
                'semantic_terms': recommendations['semantic_terms'],
                'content_analysis': {
                    'my_word_count': my_word_count,
                    'competitor_avg_words': 0,
                    'my_total_terms': sum(term['current_count'] for term in recommendations['keywords']),
                    'competitor_avg_terms': 0
                }
            },
            'competitors_analyzed': 0,
            'analysis_timestamp': time.time()
        }

    # MÉTODO MODIFICADO PARA INTEGRAR EL ANÁLISIS DE TÉRMINOS

    def comprehensive_analysis(self, content, target_keywords=None, competitor_contents=None, language=None):
        """Análisis completo con integración de frecuencia de términos"""
        
        # Tu código existente hasta el análisis competitivo...
        if not language:
            language = self.language_detector.detect_language(content)
        
        if not target_keywords:
            target_keywords = self.extract_keywords_from_content(content, language)
        
        logger.info(f"🔍 Keywords extraídas: {target_keywords}")
        
        cache_key = f"comprehensive_analysis:{language}:{hash(content)}:{hash(str(target_keywords))}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            logger.info("📋 Usando resultado cached")
            return cached_result
        
        # Análisis básico del contenido
        analysis = {
            'detected_language': language,
            'language_name': self.language_detector.get_language_config(language)['name'],
            'extracted_keywords': target_keywords,
            'basic_metrics': self.get_basic_metrics(content),
            'readability': self.analyze_readability(content, language),
            'keyword_analysis': self.analyze_keywords(content, target_keywords, language),
            'content_score': 0,
            'optimization_suggestions': [],
            'competitive_analysis': None
        }
        
        # NUEVO: Análisis de frecuencia de términos
        logger.info("🎯 Iniciando análisis de frecuencia de términos...")
        term_frequency_data = self.analyze_term_frequency_competitors(content, target_keywords, language)
        analysis['term_frequency_analysis'] = term_frequency_data['term_frequency_analysis']
        
        # Análisis semántico (tu código existente)
        if SPACY_AVAILABLE and language in self.nlp_models:
            analysis['semantic_analysis'] = self.semantic_analysis(content, language)
        else:
            analysis['semantic_analysis'] = self.basic_semantic_analysis(content, language)
        
        # Análisis competitivo automático (tu código existente)
        logger.info("🏆 Iniciando análisis competitivo automático...")
        competitive_data = self.auto_competitive_analysis(target_keywords, content, language)
        
        if competitive_data and competitive_data.get('competitors_analyzed', 0) > 0:
            analysis['competitive_analysis'] = competitive_data
            
            competitive_suggestions = self.generate_competitive_suggestions(
                competitive_data, analysis, target_keywords
            )
            analysis['optimization_suggestions'].extend(competitive_suggestions)
            logger.info(f"💡 Generadas {len(competitive_suggestions)} sugerencias competitivas")
        else:
            logger.info("⚠️ No se pudieron obtener datos competitivos")
        
        # NUEVO: Generar sugerencias de términos
        term_suggestions = self.generate_term_frequency_suggestions(analysis['term_frequency_analysis'])
        analysis['optimization_suggestions'].extend(term_suggestions)
        
        # Generar sugerencias básicas (tu código existente)
        basic_suggestions = self.generate_suggestions(analysis, language)
        analysis['optimization_suggestions'].extend(basic_suggestions)
        
        analysis['content_score'] = self.calculate_content_score(analysis)
        
        # Cache por 2 horas
        self.cache.set(cache_key, analysis, 7200)
        return analysis

    def generate_term_frequency_suggestions(self, term_analysis):
        """Generar sugerencias específicas basadas en análisis de términos"""
        suggestions = []
        
        # Sugerencias para keywords principales
        for term_data in term_analysis.get('keywords', []):
            current = term_data['current_count']
            optimal = term_data['recommended_count']['optimal']
            min_count = term_data['recommended_count']['min']
            
            if current < min_count:
                suggestions.append({
                    'type': 'term_frequency',
                    'priority': 'high',
                    'category': 'Optimización de Términos',
                    'term': term_data['term'],
                    'message': f'Aumentar uso de "{term_data["term"]}". Actual: {current}, Recomendado: {optimal}',
                    'current_value': f'{current} veces',
                    'target_value': f'{optimal} veces',
                    'improvement': f'Añadir "{term_data["term"]}" {optimal - current} veces más',
                    'term_type': 'keyword'
                })
            elif current > term_data['recommended_count']['max']:
                suggestions.append({
                    'type': 'term_frequency',
                    'priority': 'medium',
                    'category': 'Optimización de Términos',
                    'term': term_data['term'],
                    'message': f'Reducir uso de "{term_data["term"]}". Puede parecer spam.',
                    'current_value': f'{current} veces',
                    'target_value': f'{optimal} veces',
                    'improvement': f'Reducir "{term_data["term"]}" a ~{optimal} veces',
                    'term_type': 'keyword'
                })
        
        # Sugerencias para términos semánticos importantes
        important_semantic = [
            term for term in term_analysis.get('semantic_terms', [])
            if term['priority'] == 'high' and term['current_count'] == 0
        ][:3]  # Top 3 términos semánticos faltantes
        
        for term_data in important_semantic:
            suggestions.append({
                'type': 'semantic_terms',
                'priority': 'medium',
                'category': 'Contenido Semántico',
                'term': term_data['term'],
                'message': f'Incluir término relacionado "{term_data["term"]}" usado por {term_data["competitors_using"]} competidores.',
                'current_value': 'No incluido',
                'target_value': f'{term_data["recommended_count"]["optimal"]} veces',
                'improvement': f'Añadir "{term_data["term"]}" para enriquecer el contenido',
                'term_type': 'semantic'
            })
        
        # Sugerencias para n-gramas importantes
        important_ngrams = [
            term for term in term_analysis.get('ngrams', [])
            if term['priority'] == 'high' and term['current_count'] < term['recommended_count']['min']
        ][:2]  # Top 2 n-gramas importantes
        
        for term_data in important_ngrams:
            suggestions.append({
                'type': 'ngram_optimization',
                'priority': 'medium',
                'category': 'Frases Clave',
                'term': term_data['term'],
                'message': f'Incluir frase "{term_data["term"]}" usada por competidores.',
                'current_value': f'{term_data["current_count"]} veces',
                'target_value': f'{term_data["recommended_count"]["optimal"]} veces',
                'improvement': f'Usar frase "{term_data["term"]}" {term_data["recommended_count"]["optimal"] - term_data["current_count"]} veces más',
                'term_type': 'ngram'
            })
        
        return suggestions

    
    def analyze_term_frequency_competitors(self, content, target_keywords, language=None):
        """
        Análisis completo de frecuencia de términos comparando con competidores
        Similar a Surfer SEO
        """
        if not language:
            language = self.language_detector.detect_language(content)
        
        cache_key = f"term_frequency:{language}:{hash(content)}:{hash(str(target_keywords))}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            logger.info("📋 Usando análisis de términos cached")
            return cached_result
        
        logger.info("🎯 Iniciando análisis de frecuencia de términos...")
        
        # 1. Obtener contenido de competidores
        competitors_content = self.get_competitors_content_for_terms(target_keywords, language)
        
        if not competitors_content:
            logger.info("⚠️ No se pudieron obtener competidores, usando análisis básico")
            return self.basic_term_frequency_analysis(content, target_keywords, language)
        
        # 2. Analizar frecuencia en competidores
        competitor_term_analysis = self.analyze_competitors_term_frequency(
            competitors_content, target_keywords, language
        )
        
        # 3. Analizar contenido actual
        my_term_analysis = self.analyze_content_terms(content, language)
        
        # 4. Generar recomendaciones basadas en competidores
        term_recommendations = self.generate_term_recommendations(
            my_term_analysis, competitor_term_analysis, target_keywords, content, language
        )
        
        result = {
            'term_frequency_analysis': {
                'keywords': term_recommendations['keywords'],
                'ngrams': term_recommendations['ngrams'],
                'semantic_terms': term_recommendations['semantic_terms'],
                'content_analysis': {
                    'my_word_count': len(content.split()),
                    'competitor_avg_words': competitor_term_analysis['avg_word_count'],
                    'my_total_terms': sum(term['current_count'] for term in term_recommendations['keywords']),
                    'competitor_avg_terms': competitor_term_analysis['avg_total_terms']
                }
            },
            'competitors_analyzed': len(competitors_content),
            'analysis_timestamp': time.time()
        }
        
        # Cache por 2 horas
        self.cache.set(cache_key, result, 7200)
        return result

    def get_competitors_content_for_terms(self, keywords, language, max_competitors=5):
        """Obtener contenido de competidores para análisis de términos"""
        try:
            from ..services.serp_scraper import MultilingualSerpScraper
            
            serp_scraper = MultilingualSerpScraper(self.cache)
            all_competitor_contents = []
            
            # Usar la keyword principal (primera) para encontrar competidores
            main_keyword = keywords[0] if keywords else "contenido"
            
            logger.info(f"🔍 Buscando competidores para análisis de términos: {main_keyword}")
            
            serp_results = serp_scraper.get_serp_results(
                main_keyword,
                location='US' if language == 'en' else 'ES',
                language=language,
                pages=1
            )
            
            if not serp_results or 'organic_results' not in serp_results:
                return []
            
            # Obtener top resultados
            top_results = serp_results['organic_results'][:max_competitors * 2]
            
            for result in top_results:
                url = result.get('link', '')
                if not url:
                    continue
                
                logger.info(f"📄 Scrapeando para análisis de términos: {url}")
                content = self.scrape_content(url)
                
                if content and len(content) > 500:  # Mínimo de contenido
                    all_competitor_contents.append({
                        'url': url,
                        'content': content,
                        'word_count': len(content.split()),
                        'title': result.get('title', '')
                    })
                    
                    if len(all_competitor_contents) >= max_competitors:
                        break
                
                time.sleep(1)  # Delay entre requests
            
            logger.info(f"✅ Obtenidos {len(all_competitor_contents)} competidores para análisis")
            return all_competitor_contents
            
        except Exception as e:
            logger.info(f"Error obteniendo competidores para términos: {e}")
            return []

    def analyze_competitors_term_frequency(self, competitors_content, target_keywords, language):
        """Analizar frecuencia de términos en contenido de competidores"""
        from collections import defaultdict
        
        # Extraer todos los términos importantes de competidores
        all_terms = defaultdict(list)  # term -> [count1, count2, count3...]
        all_ngrams = defaultdict(list)  # ngram -> [count1, count2, count3...]
        word_counts = []
        total_terms_per_competitor = []
        
        for competitor in competitors_content:
            content = competitor['content']
            word_count = competitor['word_count']
            word_counts.append(word_count)
            
            # Contar términos objetivo
            target_term_count = 0
            for keyword in target_keywords:
                count = self.count_term_in_content(content, keyword, language)
                all_terms[keyword].append(count)
                target_term_count += count
            
            # Extraer términos semánticos importantes
            semantic_terms = self.extract_semantic_terms(content, language, target_keywords)
            for term, count in semantic_terms.items():
                all_terms[term].append(count)
                target_term_count += count
            
            # Analizar n-gramas (frases de 2-3 palabras)
            ngrams = self.extract_important_ngrams(content, language, target_keywords)
            for ngram, count in ngrams.items():
                all_ngrams[ngram].append(count)
            
            total_terms_per_competitor.append(target_term_count)
        
        # Calcular promedios y estadísticas
        avg_word_count = sum(word_counts) / len(word_counts) if word_counts else 1000
        avg_total_terms = sum(total_terms_per_competitor) / len(total_terms_per_competitor) if total_terms_per_competitor else 0
        
        # Procesar estadísticas por término
        term_stats = {}
        for term, counts in all_terms.items():
            if counts:  # Solo si hay datos
                avg_count = sum(counts) / len(counts)
                max_count = max(counts)
                min_count = min(counts)
                
                term_stats[term] = {
                    'avg_count': avg_count,
                    'max_count': max_count,
                    'min_count': min_count,
                    'competitors_using': len([c for c in counts if c > 0]),
                    'recommended_min': max(1, int(avg_count * 0.7)),
                    'recommended_optimal': max(2, int(avg_count)),
                    'recommended_max': max(3, int(avg_count * 1.3))
                }
        
        # Procesar n-gramas
        ngram_stats = {}
        for ngram, counts in all_ngrams.items():
            if counts and len([c for c in counts if c > 0]) >= 2:  # Al menos 2 competidores lo usan
                avg_count = sum(counts) / len(counts)
                ngram_stats[ngram] = {
                    'avg_count': avg_count,
                    'competitors_using': len([c for c in counts if c > 0]),
                    'recommended_min': max(1, int(avg_count * 0.5)),
                    'recommended_optimal': max(1, int(avg_count)),
                    'recommended_max': max(2, int(avg_count * 1.2))
                }
        
        return {
            'term_stats': term_stats,
            'ngram_stats': ngram_stats,
            'avg_word_count': avg_word_count,
            'avg_total_terms': avg_total_terms,
            'competitors_analyzed': len(competitors_content)
        }

    def analyze_content_terms(self, content, language):
        """Analizar términos en el contenido actual"""
        clean_content = self.clean_content_for_analysis(content)
        words = clean_content.split()
        
        return {
            'word_count': len(words),
            'unique_words': len(set(words)),
            'content_cleaned': clean_content
        }

   
 

    def analyze_competitors_with_terms(self, keywords, my_domain, my_content, top_n=7):
        """Versión con datos reales de competidores"""
        try:
            logger.info("🚀 INICIANDO analyze_competitors_with_terms")
            
            language = self.language_detector.detect_language(my_content)
            location = 'ES' if language == 'es' else 'US'
            
            logger.info(f"🏆 Análisis optimizado para idioma: {language}, ubicación: {location}")
            
            from urllib.parse import urlparse
            from ..services.serp_scraper import MultilingualSerpScraper
            
            serp_scraper = MultilingualSerpScraper(self.cache)
            main_keyword = keywords[0]
            
            serp_results = serp_scraper.get_serp_results(
                main_keyword,
                location=location,
                language=language,
                pages=1
            )
            
            if not serp_results or 'organic_results' not in serp_results:
                return {'error': 'No SERP results found'}
            
            # Los resultados YA están filtrados por el SERP scraper
            organic_results = serp_results['organic_results']
            logger.info(f"🎯 Recibidos {len(organic_results)} competidores realistas")

            competitors = []
            competitors_with_content = []
            competitors_real_data = []  # NUEVO: Array para datos reales
            
            for i, result in enumerate(serp_results['organic_results'][:5]):
                url = result.get('link', '')
                title = result.get('title', '')
                position = result.get('position', i + 1)
                
                logger.info(f"🔍 Competidor: {url}")
                logger.info(f"🔍 Posición Google: {position}")

                if not url or my_domain in url:
                    continue
                
                try:
                    domain = urlparse(url).netloc
                except:
                    continue
                
                competitor_data = {
                    'domain': domain,
                    'url': url,
                    'title': title,
                    'position': position,
                    'snippet': result.get('snippet', '')
                }
                competitors.append(competitor_data)
                
                # Scraping para obtener datos reales
                if len(competitors_with_content) < 4:
                    try:
                        content = self.scrape_content_fast(url)
                        if content and len(content) > 200:
                            # Calcular métricas reales
                            word_count = len(content.split())
                            char_count = len(content)
                            
                            # Densidad de keyword principal
                            keyword_density = 0
                            if word_count > 0:
                                keyword_count = content.lower().count(keywords[0].lower())
                                keyword_density = round((keyword_count / word_count) * 100, 2)
                            
                            # Estimación de SEO Score basado en posición y métricas
                            seo_score = max(60, 95 - (position * 3))  # Posición 1=92, 2=89, etc.
                            logger.info(f"🔍 SEO Score calculado: {seo_score}")
                            if word_count < 300:
                                seo_score -= 10
                            elif word_count > 2000:
                                seo_score += 5
                            
                            competitors_with_content.append({
                                'url': url,
                                'content': content,
                                'title': title,
                                'domain': domain
                            })

                            logger.info(f"SEO agregado a competitors_real_data: {min(95, max(60, seo_score))}")
                            
                            # NUEVO: Guardar datos reales calculados
                            competitors_real_data.append({
                                'domain': domain,
                                'url': url,
                                'title': title,
                                'position': position,
                                'word_count': word_count,
                                'char_count': char_count,
                                'keyword_density': keyword_density,
                                'seo_score': min(95, max(60, seo_score)),
                                'content_preview': content[:200] + '...' if len(content) > 200 else content
                            })
                            
                            logger.info(f"✅ Competidor realista scrapeado: {domain} - {word_count} palabras, density: {keyword_density}%")
                            
                    except Exception as e:
                        logger.error(f"❌ Error scrapeando {url}: {e}")
                        
                        # Agregar datos estimados si falla el scraping
                        competitors_real_data.append({
                            'domain': domain,
                            'url': url,
                            'title': title,
                            'position': position,
                            'word_count': 600 + (i * 150),  # Estimación más baja para sitios normales
                            'char_count': 3000 + (i * 750),
                            'keyword_density': max(0.8, 2.2 - (i * 0.2)),
                            'seo_score': max(65, 85 - (position * 3)), # Scores más realistas
                            'content_preview': 'Contenido no disponible',
                            'scraped': False
                        })
            
            logger.info(f"📊 RESUMEN: {len(competitors)} competidores, {len(competitors_with_content)} con contenido, {len(competitors_real_data)} con datos reales")
            
            # Análisis de términos
            term_analysis = {}
            if competitors_with_content:
                try:
                    term_analysis = self.analyze_terms_from_real_competitors(
                        my_content, keywords, competitors_with_content, language
                    )
                    logger.info("✅ Análisis de términos completado")
                except Exception as e:
                    logger.error(f"❌ Error en análisis de términos: {e}")
                    term_analysis = {}
            
            # Construir respuesta con datos reales
            response = {
                'keywords_analyzed': keywords,
                'my_domain': my_domain,
                'competitors_by_keyword': {keywords[0]: competitors},
                'unique_competitors': [
                    {
                        'domain': comp['domain'], 
                        'urls': [comp['url']], 
                        'titles': [comp['title']],
                        'avg_position': comp['position'],
                        'keywords_ranking': keywords
                    } 
                    for comp in competitors
                ],
                'total_competitors_found': len(competitors),
                'term_frequency_analysis': term_analysis,
                
                # NUEVO: Datos reales de competidores
                'competitors_real_data': competitors_real_data,
                
                'analysis_summary': {
                    'avg_competitors_per_keyword': len(competitors),
                    'most_common_competitors': [
                        {'domain': comp['domain'], 'appearances': 1} 
                        for comp in competitors[:5]
                    ]
                }
            }
            
            logger.info("🎉 ANÁLISIS CON DATOS REALES COMPLETADO")
            return response
            
        except Exception as e:
            logger.error(f"💥 ERROR: {str(e)}")
            return {'error': str(e)}

    def scrape_content_fast(self, url, timeout=8):
        """Scraping rápido y seguro"""
        try:
            logger.info(f"🕷️ Scrapeando rápido: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            logger.info(f"📡 Response recibido: {len(response.content)} bytes")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Limpieza básica
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            
            # Buscar contenido principal
            main_selectors = ['article', 'main', '.content', '.post-content']
            content = ""
            
            for selector in main_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    if len(content) > 100:
                        break
            
            # Fallback al body completo
            if len(content) < 100:
                body = soup.find('body')
                if body:
                    content = body.get_text(strip=True)
            
            # Limpiar y limitar
            content = re.sub(r'\s+', ' ', content)[:2000]  # Máximo 2000 caracteres
            
            logger.info(f"✅ Contenido extraído: {len(content)} caracteres")
            return content
            
        except Exception as e:
            logger.error(f"❌ Error en scrape_content_fast para {url}: {e}")
            return ""

    def analyze_terms_from_real_competitors(self, my_content, keywords, competitors_content, language):
        """MEJORAR análisis manteniendo la estructura actual"""
        logger.info("🔍 Iniciando análisis de términos mejorado")
        
        try:
            # Mantener lógica actual
            all_competitor_text = " ".join([comp['content'] for comp in competitors_content])
            
            # ESTRATEGIA HÍBRIDA (las funciones mejoradas automáticamente usarán los 3 niveles)
            logger.info("🔍 Llamando extract_semantic_terms...")
            semantic_terms = self.extract_semantic_terms(all_competitor_text, language, keywords, max_terms=25)
            logger.info(f"🔍 Términos extraídos: {len(semantic_terms)}")
            logger.info(f"🔍 Términos: {list(semantic_terms.keys())[:10]}")
            important_ngrams = self.extract_important_ngrams(all_competitor_text, language, keywords)
            
            # Mantener análisis de keywords actual
            keyword_analysis = []
            for keyword in keywords:
                my_count = self.count_term_in_content(my_content, keyword, language)
                comp_counts = [self.count_term_in_content(comp['content'], keyword, language) for comp in competitors_content]
                avg_comp_count = sum(comp_counts) / len(comp_counts) if comp_counts else 2
                
                keyword_analysis.append({
                    'term': keyword,
                    'type': 'primary_keyword',
                    'current_count': my_count,
                    'competitor_average': round(avg_comp_count, 1),
                    'recommended_count': max(2, int(avg_comp_count)),
                    'priority': 'high' if my_count < avg_comp_count * 0.5 else 'medium'
                })
            
            # MEJORAR análisis semántico con filtrado de calidad
            semantic_analysis = []
            for term, comp_frequency in semantic_terms.items():
                my_count = self.count_term_in_content(my_content, term, language)
                
                # AGREGAR validación de calidad
                if comp_frequency >= 3:
                    quality_score = self._calculate_word_quality(term, all_competitor_text)
                    if quality_score > 0.4:  # Solo términos de calidad
                        semantic_analysis.append({
                            'term': term,
                            'type': 'semantic_term',
                            'current_count': my_count,
                            'competitor_average': comp_frequency,
                            'recommended_count': max(1, int(comp_frequency * 0.7)),
                            'priority': 'high' if my_count == 0 and comp_frequency >= 5 else 'medium'
                        })
            
            # Mantener resto del código actual...
            ngram_analysis = []
            for ngram, comp_frequency in important_ngrams.items():
                my_count = self.count_term_in_content(my_content, ngram, language)
                if comp_frequency >= 2:
                    ngram_analysis.append({
                        'term': ngram,
                        'type': 'ngram',
                        'current_count': my_count,
                        'competitor_average': comp_frequency,
                        'recommended_count': max(1, comp_frequency),
                        'priority': 'medium' if my_count == 0 else 'low'
                    })
            
            # Mantener estructura de respuesta actual
            my_word_count = len(my_content.split())
            competitor_word_counts = [len(comp['content'].split()) for comp in competitors_content]
            avg_competitor_words = sum(competitor_word_counts) / len(competitor_word_counts) if competitor_word_counts else 1000
            
            return {
                'keywords': keyword_analysis,
                'semantic_terms': semantic_analysis[:20],
                'ngrams': ngram_analysis[:12], 
                'content_analysis': {
                    'my_word_count': my_word_count,
                    'competitor_avg_words': int(avg_competitor_words),
                    'competitors_analyzed': len(competitors_content)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error en análisis: {e}")
            return {'keywords': [], 'semantic_terms': [], 'ngrams': [], 'content_analysis': {}}
        

   
    def _get_additional_stop_words(self, language):
        """Método auxiliar para stop words técnicas"""
        technical_stops = {
            'es': {
                'artículo', 'página', 'sitio', 'enlace', 'comentario', 'usuario', 'autor', 
                'fecha', 'publicado', 'imagen', 'video', 'inicio', 'menú', 'buscar',
                'ahora', 'hoy', 'nuevo', 'mejor', 'bueno', 'fácil', 'realmente', 'muy',
                'fuente', 'referencia', 'contenido', 'introducción'
            },
            'en': {
                'article', 'page', 'site', 'link', 'comment', 'user', 'author',
                'date', 'published', 'image', 'video', 'home', 'menu', 'search', 
                'now', 'today', 'new', 'better', 'good', 'easy', 'really', 'very',
                'source', 'reference', 'content', 'introduction'
            }
        }
        return technical_stops.get(language, technical_stops['en'])

    def _is_technical_junk(self, word):
        """Filtrar términos técnicamente inválidos"""
        if word.isdigit():
            return True
        if re.search(r'\d{3,}|www\.|http|@|\.com', word):
            return True
        if len(word) > 20:
            return True
        return False

    def _calculate_word_quality(self, word, full_content):
        """Score de calidad simple"""
        score = 0.0
        
        # Longitud óptima
        if 5 <= len(word) <= 12:
            score += 0.5
        elif 4 <= len(word) <= 15:
            score += 0.3
        
        # Proporción de letras
        if sum(c.isalpha() for c in word) / len(word) >= 0.8:
            score += 0.3
        
        # Frecuencia razonable
        content_words = full_content.lower().split()
        if content_words:
            frequency = content_words.count(word) / len(content_words)
            if 0.002 <= frequency <= 0.02:
                score += 0.2
        
        return min(score, 1.0)
    
    def _is_semantically_valuable_universal(self, term, contexts, language):
        """Filtrado universal por estructura lingüística, NO por tema"""
        
        # 1. FILTRAR PALABRAS DEMASIADO ABSTRACTAS (universal)
        if self._is_too_abstract_universal(term, language):
            logger.info(f"🚫 Filtrado por abstracto: {term}")
            return False
        
        # 2. VERIFICAR QUE TENGA FUNCIÓN SEMÁNTICA (no solo gramatical)
        if not self._has_semantic_function(term, contexts, language):
            logger.info(f"🚫 Filtrado por falta función semántica: {term}")
            return False
        
        # 3. DEBE APARECER EN CONTEXTOS INFORMATIVOS (no solo conectivos)
        if not self._appears_in_informative_contexts(term, contexts):
            logger.info(f"🚫 Filtrado por contextos no informativos: {term}")
            return False
        
        return True

    def _is_too_abstract_universal(self, word, language):
        """Detectar palabras universalmente demasiado abstractas"""
        
        # Patrones universales de abstracción excesiva
        overly_abstract_patterns = {
            'es': [
                # Palabras de 4 letras o menos que no sean técnicas
                lambda w: len(w) <= 4 and w not in ['php', 'css', 'html', 'api', 'sql'],
                
                # Palabras que terminan en conceptos demasiado amplios
                lambda w: w.endswith(('cosa', 'vida', 'modo', 'tipo', 'vez')),
                
                # Pronombres interrogativos/demostrativos
                lambda w: w in ['cómo', 'qué', 'cuál', 'esto', 'eso', 'aquello'],
                
                # Cuantificadores vagos
                lambda w: w in ['mucho', 'poco', 'algo', 'nada', 'todo', 'todos']
            ],
            
            'en': [
                lambda w: len(w) <= 4 and w not in ['html', 'css', 'api', 'sql', 'php'],
                lambda w: w.endswith(('thing', 'way', 'time', 'kind', 'type')),
                lambda w: w in ['how', 'what', 'which', 'this', 'that', 'those'],
                lambda w: w in ['much', 'many', 'some', 'any', 'all', 'most']
            ]
        }
        
        patterns = overly_abstract_patterns.get(language, overly_abstract_patterns['en'])
        return any(pattern(word) for pattern in patterns)

    def _has_semantic_function(self, term, contexts, language):
        """Verificar que la palabra tenga función semántica (no solo gramatical)"""
        
        if not contexts:
            return False
        
        # Analizar si la palabra aporta información específica en sus contextos
        informative_contexts = 0
        
        for context in contexts:
            words_around = self._get_words_around_term(context, term)
            
            # Si está rodeada de palabras específicas/técnicas, probablemente sea informativa
            specific_neighbors = sum(1 for w in words_around 
                                if len(w) > 5 and not self._is_too_abstract_universal(w, language))
            
            if specific_neighbors >= 2:  # Al menos 2 palabras específicas cerca
                informative_contexts += 1
        
        # Al menos 60% de contextos deben ser informativos
        return (informative_contexts / len(contexts)) >= 0.6

    def _appears_in_informative_contexts(self, term, contexts):
        """Verificar que no aparezca solo en contextos conectivos/estructurales"""
        
        structural_indicators = [
            # Patrones que indican texto estructural, no informativo
            r'\b(página|artículo|capítulo|sección|índice|tabla|menú)\b',
            r'\b(anterior|siguiente|arriba|abajo|inicio|fin)\b', 
            r'\b(publicado|actualizado|editado|versión|fecha)\b',
            r'\b(comentar|compartir|enlace|link|url|clic)\b',
            r'\b(ejemplo|por ejemplo|es decir|o sea)\b'
        ]
        
        informative_contexts = 0
        
        for context in contexts:
            context_lower = context.lower()
            
            # Si el contexto NO contiene indicadores estructurales, es informativo
            is_structural = any(re.search(pattern, context_lower) for pattern in structural_indicators)
            
            if not is_structural:
                informative_contexts += 1
        
        # Al menos 70% de contextos deben ser informativos
        return (informative_contexts / len(contexts)) >= 0.7

    def _get_words_around_term(self, context, term, window=3):
        """Obtener palabras que rodean al término en el contexto"""
        words = context.lower().split()
        
        try:
            term_index = words.index(term.lower())
            start = max(0, term_index - window)
            end = min(len(words), term_index + window + 1)
            
            # Excluir el término mismo
            around_words = words[start:term_index] + words[term_index+1:end]
            return around_words
            
        except ValueError:
            return []

    def _is_complete_semantic_unit(self, phrase_words, language):
        """Verificar que la frase sea una unidad semántica completa (universal)"""
        
        # 1. NO debe empezar/terminar con partículas gramaticales
        grammatical_particles = {
            'es': {'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'por', 'para', 'con', 'sin', 'que', 'como', 'cuando', 'donde'},
            'en': {'the', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'to', 'from', 'that', 'which', 'when', 'where'}
        }
        
        particles = grammatical_particles.get(language, grammatical_particles['en'])
        
        if phrase_words[0] in particles or phrase_words[-1] in particles:
            return False
        
        # 2. DEBE tener al menos una palabra "núcleo semántico" (sustantivo/concepto)
        potential_nuclei = [w for w in phrase_words if len(w) > 5]  # Palabras largas suelen ser conceptuales
        
        if len(potential_nuclei) == 0:
            return False
        
        # 3. Ratio de contenido vs función gramatical
        content_words = sum(1 for w in phrase_words if w not in particles and len(w) > 3)
        content_ratio = content_words / len(phrase_words)
        
        return content_ratio >= 0.6  # Al menos 60% palabras de contenido

    def _calculate_semantic_completeness(self, phrase, full_content):
        """Medir qué tan completa semánticamente es la frase"""
        
        # Buscar contextos donde aparece la frase
        phrase_contexts = self._extract_term_contexts_detailed(full_content, phrase, window=10)
        
        if not phrase_contexts:
            return 0.0
        
        completeness_score = 0.0
        
        for context in phrase_contexts:
            # ¿La frase funciona como una unidad de información?
            words_before = context.split(phrase)[0].split()[-3:] if phrase in context else []
            words_after = context.split(phrase)[-1].split()[:3] if phrase in context else []
            
            # Si puede funcionar independientemente (no necesita palabras antes/después para tener sentido)
            if self._can_stand_alone_semantically(phrase, words_before, words_after):
                completeness_score += 1.0
        
        return min(completeness_score / len(phrase_contexts), 1.0)

    def _extract_term_contexts_detailed(self, content, term, window=15):
        """Extraer contextos específicos y detallados"""
        words = content.lower().split()
        contexts = []
        
        for i, word in enumerate(words):
            if term.lower() == word.lower():  # Coincidencia exacta
                start = max(0, i - window)
                end = min(len(words), i + window)
                context = " ".join(words[start:end])
                
                # Solo contextos con suficiente contenido
                if len(context.split()) >= 8:
                    contexts.append(context)
        
        return contexts[:5]  # Máximo 5 contextos

    def _can_stand_alone_semantically(self, phrase, words_before, words_after):
        """¿Puede la frase funcionar como unidad semántica independiente?"""
        
        # Si necesita palabras antes/después para completar el sentido, no es autónoma
        dependency_indicators_before = ['es', 'son', 'fue', 'era', 'será', 'está', 'estaba', 'is', 'are', 'was', 'will', 'has', 'have']
        dependency_indicators_after = ['de', 'del', 'que', 'para', 'por', 'of', 'that', 'for', 'to', 'with']
        
        # Si las palabras inmediatamente antes/después indican dependencia, la frase no es autónoma
        needs_before = any(word in dependency_indicators_before for word in words_before)
        needs_after = any(word in dependency_indicators_after for word in words_after)
        
        return not (needs_before or needs_after)

   
    def _is_valid_ngram_smart(self, words, stop_words):
        """Validación mejorada de n-gramas"""
        # Longitud mínima
        if any(len(word) < 3 for word in words):
            return False
        
        # No solo stop words
        if all(word in stop_words for word in words):
            return False
        
        # Al menos una palabra significativa
        significant_count = sum(1 for word in words if word not in stop_words and len(word) > 4)
        return significant_count > 0
    
    def clean_content_for_analysis(self, content):
        """Limpiar contenido para análisis de términos"""
        # Remover HTML
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Normalizar espacios
        content = re.sub(r'\s+', ' ', content)
        
        # Mantener solo letras, números y espacios (incluyendo acentos)
        content = re.sub(r'[^\w\s]', ' ', content, flags=re.UNICODE)
        
        return content.strip()

    def generate_term_recommendations(self, my_analysis, competitor_analysis, target_keywords, my_content, language):
        """Generar recomendaciones específicas para cada término"""
        
        recommendations = {
            'keywords': [],
            'ngrams': [],
            'semantic_terms': []
        }
        
        my_word_count = my_analysis['word_count']
        
        # 1. Analizar keywords principales
        for keyword in target_keywords:
            current_count = self.count_term_in_content(my_content, keyword, language)
            
            if keyword in competitor_analysis['term_stats']:
                stats = competitor_analysis['term_stats'][keyword]
                
                recommendations['keywords'].append({
                    'term': keyword,
                    'type': 'primary_keyword',
                    'current_count': current_count,
                    'recommended_count': {
                        'min': stats['recommended_min'],
                        'optimal': stats['recommended_optimal'],
                        'max': stats['recommended_max']
                    },
                    'competitor_average': stats['avg_count'],
                    'priority': self.calculate_term_priority(current_count, stats),
                    'competitors_using': stats['competitors_using']
                })
        
        # 2. Términos semánticos importantes
        semantic_limit = 8
        semantic_count = 0
        
        for term, stats in competitor_analysis['term_stats'].items():
            if term not in target_keywords and semantic_count < semantic_limit:
                current_count = self.count_term_in_content(my_content, term, language)
                
                # Solo incluir si es significativo
                if stats['competitors_using'] >= 2 and stats['avg_count'] >= 2:
                    recommendations['semantic_terms'].append({
                        'term': term,
                        'type': 'semantic',
                        'current_count': current_count,
                        'recommended_count': {
                            'min': stats['recommended_min'],
                            'optimal': stats['recommended_optimal'],
                            'max': stats['recommended_max']
                        },
                        'competitor_average': stats['avg_count'],
                        'priority': self.calculate_term_priority(current_count, stats),
                        'competitors_using': stats['competitors_using']
                    })
                    semantic_count += 1
        
        # 3. N-gramas importantes
        for ngram, stats in competitor_analysis['ngram_stats'].items():
            current_count = self.count_term_in_content(my_content, ngram, language)
            
            recommendations['ngrams'].append({
                'term': ngram,
                'type': 'ngram',
                'current_count': current_count,
                'recommended_count': {
                    'min': stats['recommended_min'],
                    'optimal': stats['recommended_optimal'],
                    'max': stats['recommended_max']
                },
                'competitor_average': stats['avg_count'],
                'priority': self.calculate_term_priority(current_count, stats),
                'competitors_using': stats['competitors_using']
            })
        
        return recommendations

    def calculate_term_priority(self, current_count, competitor_stats):
        """Calcular prioridad de optimización para un término"""
        optimal_count = competitor_stats['recommended_optimal']
        gap = optimal_count - current_count
        
        if gap > optimal_count * 0.7:  # Falta más del 70%
            return 'high'
        elif gap > optimal_count * 0.3:  # Falta más del 30%
            return 'medium'
        else:
            return 'low'

    def basic_term_frequency_analysis(self, content, target_keywords, language):
        """Análisis básico cuando no hay datos de competidores"""
        logger.info("📊 Realizando análisis básico de términos")
        
        my_word_count = len(content.split())
        recommendations = {
            'keywords': [],
            'ngrams': [],
            'semantic_terms': []
        }
        
        # Análisis básico para keywords principales
        for keyword in target_keywords:
            current_count = self.count_term_in_content(content, keyword, language)
            
            # Estimaciones básicas basadas en longitud del contenido
            if my_word_count < 500:
                optimal = 3
            elif my_word_count < 1000:
                optimal = 5
            else:
                optimal = max(7, int(my_word_count / 200))
            
            recommendations['keywords'].append({
                'term': keyword,
                'type': 'primary_keyword',
                'current_count': current_count,
                'recommended_count': {
                    'min': max(1, int(optimal * 0.6)),
                    'optimal': optimal,
                    'max': int(optimal * 1.4)
                },
                'competitor_average': optimal,  # Estimación
                'priority': 'high' if current_count < optimal * 0.5 else 'medium',
                'competitors_using': 0  # No hay datos
            })
        
        return {
            'term_frequency_analysis': {
                'keywords': recommendations['keywords'],
                'ngrams': recommendations['ngrams'],
                'semantic_terms': recommendations['semantic_terms'],
                'content_analysis': {
                    'my_word_count': my_word_count,
                    'competitor_avg_words': 0,
                    'my_total_terms': sum(term['current_count'] for term in recommendations['keywords']),
                    'competitor_avg_terms': 0
                }
            },
            'competitors_analyzed': 0,
            'analysis_timestamp': time.time()
        }
