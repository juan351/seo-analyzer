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
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from ..utils.language_detector import LanguageDetector
import threading
from datetime import datetime, timedelta
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultilingualSerpScraper:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.language_detector = LanguageDetector()
        self.driver = None

        # ✅ RATE LIMITING AGRESIVO
        self._last_request_time = {}
        self._request_lock = threading.Lock()
        self.min_delay_between_requests = 15  # 15 segundos mínimo
        self.max_requests_per_hour = 20       # Máximo 20 requests/hora
        self._hourly_requests = []

        # ✅ USER AGENTS ROTATIVOS REALISTAS
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
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
            
            logger.info("✅ Driver Selenium configurado correctamente")
            
        except Exception as e:
            logger.info(f"❌ Error configurando driver: {e}")
            self.driver = None

    def enforce_rate_limit(self, endpoint_key='default'):
        """Rate limiting agresivo para evitar bloqueos"""
        with self._request_lock:
            now = datetime.now()
            
            # ✅ Limpiar requests antiguos (más de 1 hora)
            self._hourly_requests = [
                req_time for req_time in self._hourly_requests 
                if now - req_time < timedelta(hours=1)
            ]
            
            # ✅ Verificar límite por hora
            if len(self._hourly_requests) >= self.max_requests_per_hour:
                oldest_request = min(self._hourly_requests)
                wait_time = (oldest_request + timedelta(hours=1) - now).total_seconds()
                if wait_time > 0:
                    print(f"🚫 Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
            
            # ✅ Verificar delay mínimo entre requests
            if endpoint_key in self._last_request_time:
                time_since_last = (now - self._last_request_time[endpoint_key]).total_seconds()
                if time_since_last < self.min_delay_between_requests:
                    wait_time = self.min_delay_between_requests - time_since_last
                    print(f"⏳ Rate limiting: waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
            
            # ✅ Registrar este request
            self._last_request_time[endpoint_key] = datetime.now()
            self._hourly_requests.append(datetime.now())

    def get_serp_results(self, keyword, location='US', language=None, pages=1):
        """Método principal con rate limiting y fallback inteligente"""
        
        # ✅ APLICAR RATE LIMITING
        cache_key = f"serp:{keyword}:{location}:{language}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            print(f"📋 Cache hit para: {keyword}")
            return cached_result
        
        print(f"🔍 Nueva búsqueda para: '{keyword}' - Aplicando rate limiting...")
        self.enforce_rate_limit(f"serp_{location}")
        
        # ✅ INTENTAR FALLBACK DIRECTO (más efectivo que Selenium)
        print(f"🚀 Usando método requests optimizado para: '{keyword}'")
        return self.get_serp_results_optimized(keyword, location, language, pages)

    def get_serp_results_optimized(self, keyword, location='US', language=None, pages=1):
        """Método optimizado usando requests con máxima evasión"""
        
        if not language:
            language = self.language_detector.detect_language(keyword)
        
        country_config = self.country_configs.get(location, self.country_configs['US'])
        
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
            # ✅ SESSION CON CONFIGURACIÓN AVANZADA
            session = requests.Session()
            
            # ✅ HEADERS ULTRA-REALISTAS CON ROTACI N
            headers = self.get_realistic_headers(country_config)
            session.headers.update(headers)
            
            # ✅ COOKIES INICIALES (simular visita previa)
            session.get(f"https://{country_config['domain']}", timeout=10)
            time.sleep(random.uniform(2, 4))
            
            for page in range(pages):
                if page > 0:
                    # Delay extra largo entre páginas
                    delay = random.uniform(20, 35)
                    print(f"⏳ Delay entre páginas: {delay:.1f} segundos...")
                    time.sleep(delay)
                
                # ✅ URL SIMPLE Y NATURAL
                encoded_keyword = quote_plus(keyword)
                url = f"https://{country_config['domain']}/search"
                
                params = {
                    'q': keyword,  # Sin encoding en params
                    'num': 10,
                    'hl': country_config['hl'],
                    'gl': country_config['gl']
                }
                
                if page > 0:
                    params['start'] = page * 10
                
                print(f"📄 Página {page + 1}: {url} - Params: {params}")
                
                # ✅ DELAY ALEATORIO ANTES DE REQUEST
                pre_delay = random.uniform(8, 15)
                print(f"⏳ Pre-request delay: {pre_delay:.1f} segundos...")
                time.sleep(pre_delay)
                
                # ✅ HACER REQUEST CON TIMEOUT LARGO
                try:
                    response = session.get(url, params=params, timeout=25)
                    
                    if response.status_code != 200:
                        print(f"❌ HTTP {response.status_code}: {response.reason}")
                        continue
                    
                    # ✅ VERIFICAR BLOQUEOS
                    if self.is_blocked(response):
                        print("🚫 Google bloqueó el request - Deteniendo scraping")
                        break
                    
                    # ✅ PARSEAR RESULTADOS
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_results = self.extract_organic_results_advanced(soup)
                    results['organic_results'].extend(page_results)
                    
                    print(f"✅ Página {page + 1}: {len(page_results)} resultados extraídos")
                    
                    # ✅ EXTRAER ELEMENTOS ADICIONALES (solo primera página)
                    if page == 0:
                        results['featured_snippet'] = self.extract_featured_snippet_bs4(soup)
                        results['people_also_ask'] = self.extract_people_also_ask_bs4(soup)
                        results['related_searches'] = self.extract_related_searches_bs4(soup)
                    
                except requests.RequestException as e:
                    print(f"❌ Error en request: {e}")
                    continue
            
            results['total_results'] = len(results['organic_results'])
            
            # ✅ CACHE AGRESIVO PARA REDUCIR REQUESTS
            cache_duration = 7200 if results['total_results'] > 0 else 1800  # 2h si hay resultados, 30min si no
            self.cache.set(f"serp:{keyword}:{location}:{language}:{pages}", results, cache_duration)
            
            print(f"🎯 TOTAL FINAL: {results['total_results']} resultados para '{keyword}'")
            return results
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            return results

    def get_realistic_headers(self, country_config):
        """Headers realistas con rotación"""
        base_headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': f"{country_config['hl']}-{country_config['gl'].upper()},{country_config['hl']};q=0.9,en;q=0.8",
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        # ✅ HEADERS ADICIONALES ALEATORIOS
        if random.random() > 0.5:
            base_headers['Sec-CH-UA'] = '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"'
            base_headers['Sec-CH-UA-Mobile'] = '?0'
            base_headers['Sec-CH-UA-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
        
        return base_headers

    def is_blocked(self, response):
        """Detectar si Google nos bloqueó"""
        blocked_indicators = [
            'sorry' in response.url.lower(),
            'captcha' in response.text.lower(),
            'unusual traffic' in response.text.lower(),
            'blocked' in response.text.lower(),
            'detected unusual' in response.text.lower(),
            '/search/howsearchworks' in response.url,
            response.status_code == 429
        ]
        
        return any(blocked_indicators)
    
    def get_serp_results(self, keyword, location='US', language=None, pages=1):
        """Método principal con rate limiting y fallback inteligente"""
        
        # ✅ APLICAR RATE LIMITING
        cache_key = f"serp:{keyword}:{location}:{language}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            print(f"📋 Cache hit para: {keyword}")
            return cached_result
        
        print(f"🔍 Nueva búsqueda para: '{keyword}' - Aplicando rate limiting...")
        self.enforce_rate_limit(f"serp_{location}")
        
        # ✅ INTENTAR FALLBACK DIRECTO (más efectivo que Selenium)
        print(f"🚀 Usando método requests optimizado para: '{keyword}'")
        return self.get_serp_results_optimized(keyword, location, language, pages)

    def get_serp_results_optimized(self, keyword, location='US', language=None, pages=1):
        """Método optimizado usando requests con máxima evasión"""
        
        if not language:
            language = self.language_detector.detect_language(keyword)
        
        country_config = self.country_configs.get(location, self.country_configs['US'])
        
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
            # ✅ SESSION CON CONFIGURACIÓN AVANZADA
            session = requests.Session()
            
            # ✅ HEADERS ULTRA-REALISTAS CON ROTACI N
            headers = self.get_realistic_headers(country_config)
            session.headers.update(headers)
            
            # ✅ COOKIES INICIALES (simular visita previa)
            session.get(f"https://{country_config['domain']}", timeout=10)
            time.sleep(random.uniform(2, 4))
            
            for page in range(pages):
                if page > 0:
                    # Delay extra largo entre páginas
                    delay = random.uniform(20, 35)
                    print(f"⏳ Delay entre páginas: {delay:.1f} segundos...")
                    time.sleep(delay)
                
                # ✅ URL SIMPLE Y NATURAL
                encoded_keyword = quote_plus(keyword)
                url = f"https://{country_config['domain']}/search"
                
                params = {
                    'q': keyword,  # Sin encoding en params
                    'num': 10,
                    'hl': country_config['hl'],
                    'gl': country_config['gl']
                }
                
                if page > 0:
                    params['start'] = page * 10
                
                print(f"📄 Página {page + 1}: {url} - Params: {params}")
                
                # ✅ DELAY ALEATORIO ANTES DE REQUEST
                pre_delay = random.uniform(8, 15)
                print(f"⏳ Pre-request delay: {pre_delay:.1f} segundos...")
                time.sleep(pre_delay)
                
                # ✅ HACER REQUEST CON TIMEOUT LARGO
                try:
                    response = session.get(url, params=params, timeout=25)
                    
                    if response.status_code != 200:
                        print(f"❌ HTTP {response.status_code}: {response.reason}")
                        continue
                    
                    # ✅ VERIFICAR BLOQUEOS
                    if self.is_blocked(response):
                        print("🚫 Google bloqueó el request - Deteniendo scraping")
                        break
                    
                    # ✅ PARSEAR RESULTADOS
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_results = self.extract_organic_results_advanced(soup)
                    results['organic_results'].extend(page_results)
                    
                    print(f"✅ Página {page + 1}: {len(page_results)} resultados extraídos")
                    
                    # ✅ EXTRAER ELEMENTOS ADICIONALES (solo primera página)
                    if page == 0:
                        results['featured_snippet'] = self.extract_featured_snippet_bs4(soup)
                        results['people_also_ask'] = self.extract_people_also_ask_bs4(soup)
                        results['related_searches'] = self.extract_related_searches_bs4(soup)
                    
                except requests.RequestException as e:
                    print(f"❌ Error en request: {e}")
                    continue
            
            results['total_results'] = len(results['organic_results'])
            
            # ✅ CACHE AGRESIVO PARA REDUCIR REQUESTS
            cache_duration = 7200 if results['total_results'] > 0 else 1800  # 2h si hay resultados, 30min si no
            self.cache.set(f"serp:{keyword}:{location}:{language}:{pages}", results, cache_duration)
            
            print(f"🎯 TOTAL FINAL: {results['total_results']} resultados para '{keyword}'")
            return results
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            return results

    def get_realistic_headers(self, country_config):
        """Headers realistas con rotación"""
        base_headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': f"{country_config['hl']}-{country_config['gl'].upper()},{country_config['hl']};q=0.9,en;q=0.8",
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        # ✅ HEADERS ADICIONALES ALEATORIOS
        if random.random() > 0.5:
            base_headers['Sec-CH-UA'] = '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"'
            base_headers['Sec-CH-UA-Mobile'] = '?0'
            base_headers['Sec-CH-UA-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
        
        return base_headers

    def is_blocked(self, response):
        """Detectar si Google nos bloqueó"""
        blocked_indicators = [
            'sorry' in response.url.lower(),
            'captcha' in response.text.lower(),
            'unusual traffic' in response.text.lower(),
            'blocked' in response.text.lower(),
            'detected unusual' in response.text.lower(),
            '/search/howsearchworks' in response.url,
            response.status_code == 429
        ]
        
        return any(blocked_indicators)
    
    def extract_organic_results_advanced(self, soup):
        """Extracción avanzada de resultados orgánicos"""
        results = []
        position = 1
        
        try:
            # ✅ SELECTORES MÚLTIPLES ACTUALIZADOS 2024
            selectors = [
                'div.g:not(.g-blk):not(.kp-blk)',  # Clásico mejorado
                'div.MjjYud',                       # Layout 2024
                'div.yuRUbf',                       # Intermedio
                'div[data-ved][jscontroller]:has(h3)', # Genérico
                '.rc',                              # Fallback clásico
            ]
            
            result_elements = []
            
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    if len(elements) >= 3:  # Al menos 3 resultados válidos
                        result_elements = elements
                        print(f"✅ Usando selector exitoso: {selector} ({len(elements)} elementos)")
                        break
                except Exception as e:
                    continue
            
            if not result_elements:
                print("⚠️ No se encontraron elementos con selectores estándar")
                return results
            
            for element in result_elements[:10]:  # Top 10
                try:
                    # ✅ EXTRACCIÓN ROBUSTA DE URL
                    url = self.extract_url_robust(element)
                    if not url:
                        continue
                    
                    # ✅ EXTRACCIÓN ROBUSTA DE TÍTULO
                    title = self.extract_title_robust(element)
                    if not title:
                        continue
                    
                    # ✅ SNIPPET
                    snippet = self.extract_snippet_robust(element)
                    
                    results.append({
                        'position': position,
                        'title': title,
                        'link': url,
                        'snippet': snippet,
                        'domain': self.extract_domain(url)
                    })
                    
                    position += 1
                    print(f"  ✅ Resultado {position-1}: {title[:60]}...")
                    
                except Exception as e:
                    print(f"⚠️ Error procesando elemento: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ Error en extracción avanzada: {e}")
        
        return results

    def extract_url_robust(self, element):
        """Extracción robusta de URLs"""
        url_selectors = [
            'a[href^="http"]',
            'a[href^="/url?q=http"]',
            'a[href*="://"]',
            'a[href]'
        ]
        
        for selector in url_selectors:
            try:
                link_elem = element.select_one(selector)
                if link_elem:
                    url = link_elem.get('href', '')
                    
                    # Limpiar URLs de Google
                    if '/url?q=' in url:
                        from urllib.parse import unquote
                        url = url.split('/url?q=')[1].split('&')[0]
                        url = unquote(url)
                    
                    # Verificar que es una URL válida y no de Google
                    if (url and url.startswith('http') and 
                        'google.com' not in url and 
                        'googleusercontent.com' not in url):
                        return url
            except:
                continue
        
        return None
    
    def extract_title_robust(self, element):
        """Extracción robusta de títulos"""
        title_selectors = [
            'h3',
            '.LC20lb',
            '[role="heading"]',
            '.DKV0Md',
            '.BNeawe.vvjwJb.AP7Wnd',
            'a h3',
            'div[role="heading"]'
        ]
        
        for selector in title_selectors:
            try:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 5:  # Título válido
                        return title
            except:
                continue
        
        return None

    def extract_snippet_robust(self, element):
        """Extracción robusta de snippets"""
        snippet_selectors = [
            '.VwiC3b',
            '.s3v9rd',
            '.st',
            '[data-content-feature="1"]',
            '.IsZvec',
            '.BNeawe.s3v9rd.AP7Wnd',
            '.aCOpRe span',
            '.hgKElc'
        ]
        
        for selector in snippet_selectors:
            try:
                snippet_elem = element.select_one(selector)
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                    if snippet and len(snippet) > 10:  # Snippet válido
                        return snippet
            except:
                continue
        
        return ""

    # ✅ MÉTODOS AUXILIARES PARA FEATURED SNIPPETS, ETC.
    def extract_featured_snippet_bs4(self, soup):
        """Extraer featured snippet"""
        try:
            selectors = [
                '.xpdopen .hgKElc',
                '.g .kp-blk',
                '.UDZeY',
                '.IThcWe',
                '.kp-blk .Uo8X3b',
                '.BNeawe.s3v9rd.AP7Wnd'
            ]
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 20:
                        return {
                            'text': text,
                            'source': 'Featured Snippet'
                        }
        except:
            pass
        return None

    def extract_people_also_ask_bs4(self, soup):
        """Extraer People Also Ask"""
        questions = []
        try:
            selectors = [
                '.related-question-pair',
                '.cbphWd',
                '[jsname="Cpkphb"]',
                '.JlqpRe'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements[:5]:
                    text = element.get_text(strip=True)
                    if text and '?' in text and len(text) > 10:
                        questions.append(text)
                if questions:
                    break
                    
        except:
            pass
        return questions[:5]

    def extract_related_searches_bs4(self, soup):
        """Extraer búsquedas relacionadas"""
        related = []
        try:
            selectors = [
                '.k8XOCe',
                '.s75CSd',
                '.AuVD',
                '.BNeawe.UPmit.AP7Wnd'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements[:8]:
                    text = element.get_text(strip=True)
                    if text and len(text) > 3:
                        related.append(text)
                if related:
                    break
                    
        except:
            pass
        return related[:8]

    def extract_domain(self, url):
        """Extraer dominio limpio"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return ""


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
                    logger.info(f"🔍 Selector '{selector}': {len(elements)} elementos")
                    
                    if len(elements) >= 3:  # Al menos 3 resultados válidos
                        result_elements = elements
                        successful_selector = selector
                        logger.info(f"✅ Usando selector: {selector}")
                        break
                        
                except Exception as e:
                    logger.info(f"❌ Error con selector '{selector}': {e}")
                    continue
            
            if not result_elements:
                logger.info("⚠️ No se encontraron elementos con ningún selector")
                # ✅ FALLBACK - Buscar cualquier enlace que parezca resultado
                try:
                    fallback_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href^="http"]:has(h3)')
                    if fallback_elements:
                        result_elements = fallback_elements[:10]
                        logger.info(f"🔄 Usando fallback: {len(result_elements)} elementos")
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
                        logger.info(f"✅ Resultado {position-1}: {title[:50]}...")
                    
                except Exception as e:
                    logger.info(f"⚠️ Error extrayendo resultado individual: {e}")
                    continue
            
            logger.info(f"📊 Total extraído: {len(results)} resultados")
            
        except Exception as e:
            logger.info(f"❌ Error extrayendo resultados orgánicos: {e}")
            import traceback
            traceback.logger.info_exc()
        
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
            logger.info(f"Error extrayendo featured snippet: {e}")
        
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
            logger.info(f"Error extrayendo People Also Ask: {e}")
        
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
            logger.info(f"Error extrayendo búsquedas relacionadas: {e}")
        
        return related[:8]

    def get_serp_google_api(self, keyword, location='US', language=None, pages=1):
        """Fallback usando Google Custom Search API (oficial)"""
        
        api_key = os.environ.get('GOOGLE_API_KEY')
        cx = os.environ.get('GOOGLE_CX')  # Custom Search Engine ID
        
        if not api_key or not cx:
            print("⚠️ Google API credentials not configured")
            return None
        
        if not language:
            language = self.language_detector.detect_language(keyword)
        
        results = {
            'keyword': keyword,
            'language': language,
            'location': location,
            'google_domain': 'google.com',
            'organic_results': [],
            'total_results': 0,
            'source': 'google_api'
        }
        
        try:
            # ✅ RATE LIMITING PARA API
            self.enforce_rate_limit('google_api')
            
            url = "https://www.googleapis.com/customsearch/v1"
            
            for page in range(pages):
                start_index = (page * 10) + 1
                
                params = {
                    'key': api_key,
                    'cx': cx,
                    'q': keyword,
                    'num': 10,
                    'start': start_index,
                    'lr': f'lang_{language}',
                    'gl': location.lower()
                }
                
                print(f"📡 Google API request for '{keyword}' - página {page + 1}")
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code != 200:
                    print(f"❌ Google API error: {response.status_code}")
                    break
                
                data = response.json()
                
                if 'items' not in data:
                    print("⚠️ No items in Google API response")
                    break
                
                # Procesar resultados
                for i, item in enumerate(data['items']):
                    position = (page * 10) + i + 1
                    
                    results['organic_results'].append({
                        'position': position,
                        'title': item.get('title', ''),
                        'link': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'domain': self.extract_domain(item.get('link', ''))
                    })
                
                print(f"✅ Google API: {len(data['items'])} resultados de página {page + 1}")
                
                # Delay entre páginas de API
                if page < pages - 1:
                    time.sleep(1)
            
            results['total_results'] = len(results['organic_results'])
            
            # Cache más largo para API (es más confiable)
            if results['total_results'] > 0:
                cache_key = f"serp_api:{keyword}:{location}:{language}:{pages}"
                self.cache.set(cache_key, results, 14400)  # 4 horas
            
            print(f"🎯 Google API TOTAL: {results['total_results']} resultados")
            return results
            
        except Exception as e:
            print(f"❌ Error en Google API: {e}")
            return None

    # ✅ MÉTODO PRINCIPAL ACTUALIZADO CON FALLBACKS INTELIGENTES
    def get_serp_results(self, keyword, location='US', language=None, pages=1):
        """Método principal con fallbacks en cascada"""
        
        # 1. Verificar cache primero
        cache_key = f"serp:{keyword}:{location}:{language}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            print(f"📋 Cache hit para: {keyword}")
            return cached_result
        
        print(f"🔍 Nueva búsqueda para: '{keyword}' en {location}")
        
        # 2. Intentar método optimizado (requests)
        results = self.get_serp_results_optimized(keyword, location, language, pages)
        
        if results and results['total_results'] > 0:
            print(f"✅ Método optimizado exitoso: {results['total_results']} resultados")
            return results
        
        # 3. Fallback a Google Custom Search API
        print("🔄 Fallback a Google API...")
        api_results = self.get_serp_google_api(keyword, location, language, min(pages, 1))  # API limitado a 1 página
        
        if api_results and api_results['total_results'] > 0:
            print(f"✅ Google API exitoso: {api_results['total_results']} resultados")
            return api_results
        
        # 4. Último fallback - resultados vacíos con estructura correcta
        print("⚠️ Todos los métodos fallaron - retornando estructura vacía")
        return {
            'keyword': keyword,
            'language': language or 'en',
            'location': location,
            'google_domain': self.country_configs.get(location, self.country_configs['US'])['domain'],
            'organic_results': [],
            'featured_snippet': None,
            'people_also_ask': [],
            'related_searches': [],
            'total_results': 0,
            'source': 'empty_fallback'
        }
    def close_driver(self):
        """Cerrar driver para reiniciar"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self._requests_count = 0
                logger.info("🔄 Driver reiniciado")
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
            
            logger.info(f"🔍 Obteniendo sugerencias para '{seed_keyword}' en {country}")
            
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
            logger.info(f"✅ Encontradas {len(clean_suggestions)} sugerencias")
            return result
            
        except Exception as e:
            logger.info(f"❌ Error getting keyword suggestions: {str(e)}")
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
                logger.info(f"Error obteniendo sugerencias para '{letter}': {e}")
                continue
        
        return suggestions
    
    def get_serp_results_fallback(self, keyword, location='US', language=None, pages=1):
        """Fallback usando requests cuando Selenium es bloqueado"""
        
        if not language:
            language = self.language_detector.detect_language(keyword)
        
        country_config = self.country_configs.get(location, self.country_configs['US'])
        
        cache_key = f"serp_fallback:{keyword}:{location}:{language}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            logger.info(f"📋 Usando SERP fallback cached para: {keyword}")
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
            logger.info(f"🔄 FALLBACK: Scrapeando con requests para '{keyword}'")
            
            import requests
            from bs4 import BeautifulSoup
            import time
            import random
            from urllib.parse import quote_plus
            
            session = requests.Session()
            
            # Headers ultra-realistas
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
            }
            
            session.headers.update(headers)
            
            for page in range(pages):
                if page > 0:
                    delay = random.uniform(15, 25)  # Delay largo entre páginas
                    logger.info(f"⏳ FALLBACK: Esperando {delay:.1f} segundos...")
                    time.sleep(delay)
                
                # URL simple para evitar detección
                encoded_keyword = quote_plus(keyword)
                url = f"https://www.google.com/search?q={encoded_keyword}&num=10"
                
                if page > 0:
                    url += f"&start={page * 10}"
                
                logger.info(f"📄 FALLBACK página {page + 1}: {url}")
                
                # Delay inicial
                time.sleep(random.uniform(5, 10))
                
                try:
                    response = session.get(url, timeout=20)
                    
                    if response.status_code != 200:
                        logger.info(f"❌ FALLBACK HTTP {response.status_code}")
                        continue
                    
                    # Verificar si nos bloquearon
                    if ('sorry' in response.url.lower() or 
                        'captcha' in response.text.lower() or 
                        'unusual traffic' in response.text.lower()):
                        logger.info("🚫 FALLBACK también bloqueado por Google")
                        break
                    
                    # Parsear con BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extraer resultados
                    page_results = self.extract_organic_results_bs4(soup)
                    results['organic_results'].extend(page_results)
                    
                    logger.info(f"✅ FALLBACK: {len(page_results)} resultados de página {page + 1}")
                    
                    # Si primera página, extraer elementos adicionales
                    if page == 0:
                        results['featured_snippet'] = self.extract_featured_snippet_bs4(soup)
                        results['people_also_ask'] = self.extract_people_also_ask_bs4(soup)
                        results['related_searches'] = self.extract_related_searches_bs4(soup)
                    
                except Exception as e:
                    logger.info(f"❌ Error en request fallback: {e}")
                    continue
            
            results['total_results'] = len(results['organic_results'])
            
            # Cache por 1 hora (menos tiempo porque puede ser menos confiable)
            if results['total_results'] > 0:
                self.cache.set(cache_key, results, 3600)
                logger.info(f"🎯 FALLBACK TOTAL: {results['total_results']} resultados")
            else:
                logger.info("⚠️ FALLBACK: No se encontraron resultados")
            
            return results
            
        except Exception as e:
            logger.info(f"❌ Error general en fallback: {e}")
            return results

    def extract_organic_results_bs4(self, soup):
        """Extraer resultados orgánicos usando BeautifulSoup"""
        results = []
        position = 1
        
        try:
            # Selectores para diferentes layouts de Google
            selectors = [
                'div.g:not(.g-blk)',      # Layout clásico
                'div.MjjYud',             # Nuevo layout 2024
                'div.yuRUbf',             # Layout intermedio
                'div[data-ved]:has(h3)',  # Genérico con heading
            ]
            
            result_elements = []
            successful_selector = None
            
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    logger.info(f"🔍 FALLBACK selector '{selector}': {len(elements)} elementos")
                    
                    if len(elements) >= 3:  # Al menos 3 resultados
                        result_elements = elements
                        successful_selector = selector
                        logger.info(f"✅ FALLBACK usando selector: {selector}")
                        break
                        
                except Exception as e:
                    logger.info(f"❌ FALLBACK error con selector '{selector}': {e}")
                    continue
            
            if not result_elements:
                logger.info("⚠️ FALLBACK: No se encontraron elementos con ningún selector")
                return results
            
            for element in result_elements[:10]:  # Top 10
                try:
                    # Extraer URL
                    url = ""
                    link_element = element.select_one('a[href^="http"], a[href^="/url?q=http"]')
                    
                    if link_element:
                        url = link_element.get('href', '')
                        
                        # Limpiar URLs de Google
                        if '/url?q=' in url:
                            from urllib.parse import unquote
                            url = url.split('/url?q=')[1].split('&')[0]
                            url = unquote(url)
                        
                        if not url or 'google.com' in url:
                            continue
                    
                    # Extraer título
                    title = ""
                    title_element = element.select_one('h3, .LC20lb, [role="heading"], .DKV0Md')
                    if title_element:
                        title = title_element.get_text(strip=True)
                    
                    # Extraer snippet
                    snippet = ""
                    snippet_element = element.select_one('.VwiC3b, .s3v9rd, .st, [data-content-feature="1"], .IsZvec')
                    if snippet_element:
                        snippet = snippet_element.get_text(strip=True)
                    
                    if title and url:
                        results.append({
                            'position': position,
                            'title': title,
                            'link': url,
                            'snippet': snippet,
                            'domain': self.extract_domain(url)
                        })
                        position += 1
                        logger.info(f"✅ FALLBACK resultado {position-1}: {title[:50]}...")
                        
                except Exception as e:
                    logger.info(f"⚠️ FALLBACK error extrayendo resultado: {e}")
                    continue
            
            logger.info(f"📊 FALLBACK total extraído: {len(results)} resultados")
            
        except Exception as e:
            logger.info(f"❌ FALLBACK error extrayendo resultados orgánicos: {e}")
        
        return results

    def extract_featured_snippet_bs4(self, soup):
        """Extraer featured snippet con BeautifulSoup"""
        try:
            selectors = ['.xpdopen .hgKElc', '.g .kp-blk', '.UDZeY', '.IThcWe']
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    return {
                        'text': element.get_text(strip=True),
                        'source': 'Featured Snippet'
                    }
        except:
            pass
        return None

    def extract_people_also_ask_bs4(self, soup):
        """Extraer preguntas con BeautifulSoup"""
        questions = []
        try:
            selectors = ['.related-question-pair', '.cbphWd', '[jsname="Cpkphb"]']
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements[:5]:
                    text = element.get_text(strip=True)
                    if text and '?' in text:
                        questions.append(text)
                if questions:
                    break
        except:
            pass
        return questions[:5]

    def extract_related_searches_bs4(self, soup):
        """Extraer búsquedas relacionadas con BeautifulSoup"""
        related = []
        try:
            selectors = ['.k8XOCe', '.s75CSd', '.AuVD']
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements[:8]:
                    text = element.get_text(strip=True)
                    if text:
                        related.append(text)
                if related:
                    break
        except:
            pass
        return related[:8]
    
    def get_rotating_proxy(self):
        """Configurar proxy rotativo (cuando tengas servicio)"""
        proxies = [
            # Lista de proxies rotativos
            # 'http://proxy1:port',
            # 'http://proxy2:port',
        ]
        
        if proxies:
            proxy = random.choice(proxies)
            return {
                'http': proxy,
                'https': proxy
            }
        return None

    def __del__(self):
        """Destructor para cerrar driver"""
        self.close_driver()