import nltk
from textstat import flesch_reading_ease
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
from urllib.parse import urlparse, urljoin
import time
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

    def comprehensive_analysis(self, content, target_keywords=None, competitor_contents=None, language=None):
        """Análisis completo autónomo - encuentra competidores automáticamente"""
        
        # Detectar idioma
        if not language:
            language = self.language_detector.detect_language(content)
        
        # Si no se proporcionan keywords, extraerlas automáticamente
        if not target_keywords:
            target_keywords = self.extract_keywords_from_content(content, language)
        
        print(f"🔍 Keywords extraídas: {target_keywords}")
        
        cache_key = f"auto_analysis:{language}:{hash(content)}:{hash(str(target_keywords))}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            print("📋 Usando resultado cached")
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
        
        # Análisis semántico
        if SPACY_AVAILABLE and language in self.nlp_models:
            analysis['semantic_analysis'] = self.semantic_analysis(content, language)
        else:
            analysis['semantic_analysis'] = self.basic_semantic_analysis(content, language)
        
        # ANÁLISIS COMPETITIVO AUTOMÁTICO
        print("🏆 Iniciando análisis competitivo automático...")
        competitive_data = self.auto_competitive_analysis(target_keywords, content, language)
        
        if competitive_data and competitive_data.get('competitors_analyzed', 0) > 0:
            analysis['competitive_analysis'] = competitive_data
            
            # Generar sugerencias competitivas
            competitive_suggestions = self.generate_competitive_suggestions(
                competitive_data, analysis, target_keywords
            )
            analysis['optimization_suggestions'].extend(competitive_suggestions)
            print(f"💡 Generadas {len(competitive_suggestions)} sugerencias competitivas")
        else:
            print("⚠️ No se pudieron obtener datos competitivos")
        
        # Generar sugerencias básicas
        basic_suggestions = self.generate_suggestions(analysis, language)
        analysis['optimization_suggestions'].extend(basic_suggestions)
        
        analysis['content_score'] = self.calculate_content_score(analysis)
        
        # Cache por 2 horas
        self.cache.set(cache_key, analysis, 7200)
        return analysis

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
            print(f"Error extrayendo keywords: {e}")
            return ['contenido', 'información']

    def get_stop_words(self, language):
        """Stop words básicas por idioma"""
        stop_words = {
            'es': {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'como', 'pero', 'sus', 'han', 'muy', 'más', 'me', 'mi', 'este', 'esta', 'esta', 'estos', 'estas'},
            'en': {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        }
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
                print(f"🔍 Buscando competidores para: {keyword}")
                
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
                    print(f"📄 Scrapeando: {url}")
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
            print(f"Error en análisis competitivo: {e}")
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
            print(f"Error scrapeando {url}: {e}")
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
                related_terms = self.extract_related_terms_from_patterns(content_patterns, keyword)
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

    def extract_related_terms_from_patterns(self, patterns, main_keyword):
        """Extraer términos relacionados de los patrones de contenido competidores"""
        try:
            all_text = ' '.join(patterns).lower()
            
            # Remover la keyword principal para encontrar términos relacionados
            all_text = all_text.replace(main_keyword.lower(), '')
            
            # Extraer palabras significativas
            words = re.findall(r'\b[a-záéíóúüñ]+\b', all_text) if 'spanish' in str(type(self)) else re.findall(r'\b[a-zA-Z]+\b', all_text)
            
            # Filtrar stop words y palabras muy cortas
            stop_words = self.get_stop_words('es')  # Asumiendo español por defecto
            significant_words = [
                word for word in words 
                if len(word) > 4 and word not in stop_words
            ]
            
            # Contar frecuencias y devolver las más comunes
            word_freq = Counter(significant_words)
            return [word for word, count in word_freq.most_common(8) if count > 1]
            
        except Exception as e:
            print(f"Error extrayendo términos relacionados: {e}")
            return []

    def analyze_competitors(self, keywords, my_domain, top_n=5):
        """Método público para análisis de competidores independiente"""
        try:
            from ..services.serp_scraper import MultilingualSerpScraper
            
            print(f"🏆 Analizando competidores para keywords: {keywords}")
            
            serp_scraper = MultilingualSerpScraper(self.cache)
            competitors_found = {}
            all_competitors = []
            
            for keyword in keywords:
                print(f"🔍 Buscando competidores para: {keyword}")
                
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
            print(f"Error analizando competidores: {e}")
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