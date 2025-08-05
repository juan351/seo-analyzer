# app/services/serp_scraper.py (versión corregida)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import requests
from urllib.parse import quote_plus
from ..utils.language_detector import LanguageDetector

class MultilingualSerpScraper:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.language_detector = LanguageDetector()
        self.driver = None
        
        # Mapeo correcto de países a configuraciones de Google
        self.country_configs = {
            'US': {'domain': 'google.com', 'gl': 'us', 'hl': 'en'},
            'ES': {'domain': 'google.com', 'gl': 'es', 'hl': 'es'},  # España
            'AR': {'domain': 'google.com.ar', 'gl': 'ar', 'hl': 'es'},  # Argentina
            'MX': {'domain': 'google.com.mx', 'gl': 'mx', 'hl': 'es'},  # México
            'CO': {'domain': 'google.com.co', 'gl': 'co', 'hl': 'es'},  # Colombia
            'CL': {'domain': 'google.cl', 'gl': 'cl', 'hl': 'es'},      # Chile
            'PE': {'domain': 'google.com.pe', 'gl': 'pe', 'hl': 'es'},  # Perú
            'UK': {'domain': 'google.co.uk', 'gl': 'uk', 'hl': 'en'},   # Reino Unido
            'FR': {'domain': 'google.fr', 'gl': 'fr', 'hl': 'fr'},      # Francia
            'DE': {'domain': 'google.de', 'gl': 'de', 'hl': 'de'},      # Alemania
        }

    def setup_driver(self):
        """Configurar driver de Selenium con anti-detección mejorada"""
        if self.driver:
            return
            
        try:
            chrome_options = Options()
            
            # Configuración anti-detección
            chrome_options.add_argument('--headless=new')  # Nuevo modo headless
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1366,768')  # Resolución común
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')  # Más sigiloso
            chrome_options.add_argument('--user-data-dir=/tmp/chrome-user-data')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            
            # User agents reales
            realistic_user_agents = [
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            ]
            chrome_options.add_argument(f'--user-agent={random.choice(realistic_user_agents)}')
            
                    # ✅ USAR ChromeDriver instalado en Dockerfile
            import os
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
            
            from selenium.webdriver.chrome.service import Service
            service = Service(chromedriver_path)
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Scripts anti-detección
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": random.choice(realistic_user_agents)
            })
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'es']});
                    window.chrome = {runtime: {}};
                    Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
                '''
            })
            
            print("✅ Driver Selenium configurado correctamente")
            
        except Exception as e:
            print(f"❌ Error configurando driver: {e}")
            self.driver = None

    def get_serp_results(self, keyword, location='US', language=None, pages=1):
        """Scraping SERP completo y funcional"""
        print(f"🔍 INICIO - Scrapeando SERP para: '{keyword}' en {location}")
        # Detectar idioma si no se proporciona
        if not language:
            language = self.language_detector.detect_language(keyword)
        
        # Obtener configuración del país
        country_config = self.country_configs.get(location, self.country_configs['US'])
        print(f"🌍 Configuración país: {country_config}")
        cache_key = f"serp:{keyword}:{location}:{language}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            print(f"📋 Usando SERP cached para: {keyword}")
            return cached_result
        
        results = {
            'keyword': keyword,
            'language': language,
            'location': location,
            'google_domain': country_config['domain'],
            'organic_results': [],
            'featured_snippet': None,
            'people_also_ask': [],
            'related_searches': [],
            'total_results': 0
        }
        
        try:
            # Configurar driver si no existe
            print(f"🚗 Estado del driver: {self.driver}")
            if not self.driver:
                self.setup_driver()
            
            if not self.driver:
                print("❌ No se pudo configurar el driver")
                return results
            
            print(f"✅ Driver configurado: {type(self.driver)}")
            
            for page in range(pages):
                

                delay = random.uniform(8, 15)  # 8-15 segundos entre requests
                print(f"⏳ Esperando {delay:.1f} segundos...")
                time.sleep(delay)
                
                # URL correcta con parámetros de país e idioma
                encoded_keyword = quote_plus(keyword)
                url = f"https://www.google.com/search?q={encoded_keyword}"
                
                print(f"📄 Accediendo: {url}")
                
                self.driver.get(url)

                # ✅ VERIFICAR SI GOOGLE NOS BLOQUEÓ
                current_url = self.driver.current_url
                page_title = self.driver.title.lower()
                
                if 'sorry' in current_url or 'captcha' in page_title or 'blocked' in page_title:
                    print("🚫 GOOGLE BLOQUEÓ - Cambiando a fallback")
                    self.driver.quit()
                    self.driver = None
                    return self.get_serp_results_fallback(keyword, location, language, pages)
                
                # Esperar que cargue la página
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g, div[data-ved]'))
                    )
                except TimeoutException:
                    print("⏰ Timeout esperando resultados")
                    continue
                
                # Extraer resultados orgánicos
                page_results = self.extract_organic_results()
                results['organic_results'].extend(page_results)
                
                # Extraer featured snippet (solo primera página)
                if page == 0:
                    results['featured_snippet'] = self.extract_featured_snippet()
                    results['people_also_ask'] = self.extract_people_also_ask()
                    results['related_searches'] = self.extract_related_searches()
                
                print(f"✅ Extraídos {len(page_results)} resultados de página {page + 1}")
            
            results['total_results'] = len(results['organic_results'])
            
            # Cache por 2 horas
            if results['total_results'] > 0:
                self.cache.set(cache_key, results, 7200)
                print(f"🎯 Total de resultados encontrados: {results['total_results']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error scraping SERP: {str(e)}")
            return results
        
        finally:
            # Limpiar después de un tiempo para evitar detección
            if hasattr(self, '_requests_count'):
                self._requests_count += 1
                if self._requests_count > 10:  # Restart driver cada 10 requests
                    self.close_driver()
            else:
                self._requests_count = 1

    def extract_organic_results(self):
        """Extraer resultados orgánicos con selectores actualizados 2024"""
        results = []
        
        try:
            # ✅ SELECTORES ACTUALIZADOS para Google 2024
            selectors = [
                'div.MjjYud',      # Nuevo layout 2024
                'div.yuRUbf',      # Layout intermedio
                'div.g:not(.g-blk)', # Layout clásico
                'div[data-ved]:has(h3)', # Genérico con heading
            ]
            
            result_elements = []
            successful_selector = None
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"🔍 Selector '{selector}': {len(elements)} elementos")
                    
                    if len(elements) >= 3:  # Al menos 3 resultados válidos
                        result_elements = elements
                        successful_selector = selector
                        print(f"✅ Usando selector: {selector}")
                        break
                        
                except Exception as e:
                    print(f"❌ Error con selector '{selector}': {e}")
                    continue
            
            if not result_elements:
                print("⚠️ No se encontraron elementos con ningún selector")
                # ✅ FALLBACK - Buscar cualquier enlace que parezca resultado
                try:
                    fallback_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href^="http"]:has(h3)')
                    if fallback_elements:
                        result_elements = fallback_elements[:10]
                        print(f"🔄 Usando fallback: {len(result_elements)} elementos")
                except:
                    pass
            
            if not result_elements:
                return results
            
            position = len(results) + 1
            
            for element in result_elements[:10]:  # Top 10 por página
                try:
                    # ✅ EXTRACCIÓN MEJORADA de URL
                    url = ""
                    link_selectors = ['a[href^="http"]', 'a[href^="/url?q=http"]', 'a']
                    
                    for link_sel in link_selectors:
                        try:
                            link_element = element.find_element(By.CSS_SELECTOR, link_sel)
                            url = link_element.get_attribute('href')
                            
                            # Limpiar URLs de Google
                            if '/url?q=' in url:
                                url = url.split('/url?q=')[1].split('&')[0]
                                from urllib.parse import unquote
                                url = unquote(url)
                            
                            if url and 'http' in url and 'google.com' not in url:
                                break
                        except:
                            continue
                    
                    if not url or 'google.com' in url:
                        continue
                    
                    # ✅ EXTRACCIÓN MEJORADA de título
                    title = ""
                    title_selectors = ['h3', '.LC20lb', '[role="heading"]', '.DKV0Md']
                    
                    for title_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                            title = title_elem.text.strip()
                            if title:
                                break
                        except:
                            continue
                    
                    # ✅ EXTRACCIÓN MEJORADA de snippet
                    snippet = ""
                    snippet_selectors = ['.VwiC3b', '.s3v9rd', '.st', '[data-content-feature="1"]', '.IsZvec']
                    
                    for snippet_sel in snippet_selectors:
                        try:
                            snippet_elem = element.find_element(By.CSS_SELECTOR, snippet_sel)
                            snippet = snippet_elem.text.strip()
                            if snippet:
                                break
                        except:
                            continue
                    
                    if title and url:
                        results.append({
                            'position': position,
                            'title': title,
                            'link': url,
                            'snippet': snippet,
                            'domain': self.extract_domain(url)
                        })
                        position += 1
                        print(f"✅ Resultado {position-1}: {title[:50]}...")
                    
                except Exception as e:
                    print(f"⚠️ Error extrayendo resultado individual: {e}")
                    continue
            
            print(f"📊 Total extraído: {len(results)} resultados")
            
        except Exception as e:
            print(f"❌ Error extrayendo resultados orgánicos: {e}")
            import traceback
            traceback.print_exc()
        
        return results

    def extract_domain(self, url):
        """Extraer dominio limpio de una URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return ""

    def extract_featured_snippet(self):
        """Extraer featured snippet si existe"""
        try:
            selectors = [
                '.xpdopen .hgKElc',
                '.g .kp-blk',
                '.UDZeY',
                '.IThcWe'
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    return {
                        'text': element.text.strip(),
                        'source': 'Featured Snippet'
                    }
                except:
                    continue
                    
        except Exception as e:
            print(f"Error extrayendo featured snippet: {e}")
        
        return None

    def extract_people_also_ask(self):
        """Extraer preguntas relacionadas"""
        questions = []
        try:
            selectors = ['.related-question-pair', '.cbphWd', '[jsname="Cpkphb"]']
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements[:5]:  # Top 5
                        text = element.text.strip()
                        if text and '?' in text:
                            questions.append(text)
                    if questions:
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"Error extrayendo People Also Ask: {e}")
        
        return questions[:5]

    def extract_related_searches(self):
        """Extraer búsquedas relacionadas"""
        related = []
        try:
            selectors = ['.k8XOCe', '.s75CSd', '.AuVD']
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements[:8]:  # Top 8
                        text = element.text.strip()
                        if text:
                            related.append(text)
                    if related:
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"Error extrayendo búsquedas relacionadas: {e}")
        
        return related[:8]

    def close_driver(self):
        """Cerrar driver para reiniciar"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self._requests_count = 0
                print("🔄 Driver reiniciado")
            except:
                pass

    def get_keyword_suggestions(self, seed_keyword, country='US', language=None):
        """Sugerencias de keywords con configuración corregida"""
        
        if not language:
            language = self.language_detector.detect_language(seed_keyword)
        
        country_config = self.country_configs.get(country, self.country_configs['US'])
        
        cache_key = f"suggestions:{seed_keyword}:{country}:{language}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        suggestions = []
        
        try:
            # Google Suggest API con configuración correcta
            url = "http://suggestqueries.google.com/complete/search"
            params = {
                'client': 'chrome',
                'q': seed_keyword,
                'gl': country_config['gl'],  # Parámetro de país corregido
                'hl': country_config['hl']   # Parámetro de idioma corregido
            }
            
            print(f"🔍 Obteniendo sugerencias para '{seed_keyword}' en {country}")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    suggestions = data[1]  # Las sugerencias están en el índice 1
            
            # Obtener también variaciones alfabéticas
            alphabet_suggestions = self.get_alphabet_suggestions(seed_keyword, country_config, language)
            suggestions.extend(alphabet_suggestions)
            
            # Limpiar y deduplicar
            clean_suggestions = []
            seen = set()
            
            for suggestion in suggestions:
                if isinstance(suggestion, str):
                    clean_suggestion = suggestion.lower().strip()
                    if (clean_suggestion and 
                        len(clean_suggestion) > 2 and 
                        clean_suggestion not in seen and
                        clean_suggestion != seed_keyword.lower()):
                        clean_suggestions.append(suggestion)
                        seen.add(clean_suggestion)
            
            result = {
                'seed_keyword': seed_keyword,
                'language': language,
                'country': country,
                'suggestions': clean_suggestions[:50],
                'total_found': len(clean_suggestions)
            }
            
            # Cache por 24 horas
            self.cache.set(cache_key, result, 86400)
            print(f"✅ Encontradas {len(clean_suggestions)} sugerencias")
            return result
            
        except Exception as e:
            print(f"❌ Error getting keyword suggestions: {str(e)}")
            return {
                'seed_keyword': seed_keyword,
                'language': language,
                'country': country,
                'suggestions': [],
                'total_found': 0,
                'error': str(e)
            }

    def get_alphabet_suggestions(self, seed_keyword, country_config, language):
        """Obtener sugerencias usando método alfabético"""
        suggestions = []
        
        # Alfabetos por idioma
        alphabets = {
            'en': 'abcdefghijklmnopqrstuvwxyz',
            'es': 'abcdefghijklmnñopqrstuvwxyz',
            'fr': 'abcdefghijklmnopqrstuvwxyz',
            'de': 'abcdefghijklmnopqrstuvwxyzäöü',
            'pt': 'abcdefghijklmnopqrstuvwxyzç'
        }
        
        alphabet = alphabets.get(language, alphabets['en'])
        
        # Solo usar las primeras letras para no sobrecargar
        for letter in alphabet[:6]:  
            try:
                url = "http://suggestqueries.google.com/complete/search"
                params = {
                    'client': 'chrome',
                    'q': f"{seed_keyword} {letter}",
                    'gl': country_config['gl'],
                    'hl': country_config['hl']
                }
                
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if len(data) > 1 and isinstance(data[1], list):
                        suggestions.extend(data[1])
                
                time.sleep(0.5)  # Delay entre requests
                
            except Exception as e:
                print(f"Error obteniendo sugerencias para '{letter}': {e}")
                continue
        
        return suggestions

    def __del__(self):
        """Destructor para cerrar driver"""
        self.close_driver()