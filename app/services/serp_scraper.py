# app/services/serp_scraper.py (versión multiidioma)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import random
from ..utils.language_detector import LanguageDetector

class MultilingualSerpScraper:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.language_detector = LanguageDetector()
        self.setup_driver()

    # app/services/serp_scraper.py


    def setup_driver(self):
        """Configurar driver de Selenium"""
        from selenium.webdriver.chrome.options import Options
        from fake_useragent import UserAgent
        
        self.ua = UserAgent()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def get_serp_results(self, keyword, location='US', language=None, pages=1):
        """Scraping SERP adaptado por idioma y ubicación"""
        
        # Detectar idioma si no se proporciona
        if not language:
            language = self.language_detector.detect_language(keyword)
        
        lang_config = self.language_detector.get_language_config(language)
        
        # Usar dominio de Google apropiado para el idioma
        google_domain = lang_config['google_domain']
        
        cache_key = f"serp:{keyword}:{location}:{language}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        results = {
            'keyword': keyword,
            'language': language,
            'location': location,
            'google_domain': google_domain,
            'organic_results': [],
            'featured_snippet': None,
            'people_also_ask': [],
            'related_searches': [],
            'total_results': 0
        }
        
        try:
            for page in range(pages):
                start = page * 10
                
                # URL adaptada por idioma y ubicación
                url = f"https://{google_domain}/search?q={keyword}&start={start}&gl={location}&hl={language}"
                
                time.sleep(random.uniform(2, 5))
                self.driver.get(url)
                
                # Resto del scraping...
                # (código similar al anterior pero adaptado)
                
            self.cache.set(cache_key, results, 3600)
            return results
            
        except Exception as e:
            print(f"Error scraping SERP: {str(e)}")
            return results

    def get_keyword_suggestions(self, seed_keyword, country='US', language=None):
        """Sugerencias de keywords adaptadas por idioma"""
        
        if not language:
            language = self.language_detector.detect_language(seed_keyword)
        
        lang_config = self.language_detector.get_language_config(language)
        google_domain = lang_config['google_domain']
        
        cache_key = f"suggestions:{seed_keyword}:{country}:{language}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        suggestions = []
        
        try:
            # Google Suggest API con parámetros de idioma
            url = "http://suggestqueries.google.com/complete/search"
            params = {
                'client': 'chrome',
                'q': seed_keyword,
                'gl': country.lower(),
                'hl': language  # Parámetro de idioma
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    suggestions = data[1]  # Las sugerencias están en el índice 1
            
            # Obtener también variaciones alfabéticas en el idioma correspondiente
            alphabet_suggestions = self.get_alphabet_suggestions(seed_keyword, country, language)
            suggestions.extend(alphabet_suggestions)
            
            # Limpiar y deduplicar
            suggestions = list(set([s.lower() for s in suggestions if s and len(s) > 2]))
            suggestions.sort()
            
            result = {
                'seed_keyword': seed_keyword,
                'language': language,
                'country': country,
                'suggestions': suggestions[:50],
                'total_found': len(suggestions)
            }
            
            # Cache por 24 horas
            self.cache.set(cache_key, result, 86400)
            return result
            
        except Exception as e:
            print(f"Error getting keyword suggestions: {str(e)}")
            return {
                'seed_keyword': seed_keyword,
                'language': language,
                'suggestions': [],
                'total_found': 0
            }

    def get_alphabet_suggestions(self, seed_keyword, country, language):
        """Obtener sugerencias usando método alfabético por idioma"""
        suggestions = []
        
        # Alfabetos por idioma
        alphabets = {
            'en': 'abcdefghijklmnopqrstuvwxyz',
            'es': 'abcdefghijklmnñopqrstuvwxyz',
            'fr': 'abcdefghijklmnopqrstuvwxyz',
            'de': 'abcdefghijklmnopqrstuvwxyzäöü'
        }
        
        alphabet = alphabets.get(language, alphabets['en'])
        
        for letter in alphabet[:8]:  # Primeras 8 letras para no sobrecargar
            try:
                url = "http://suggestqueries.google.com/complete/search"
                params = {
                    'client': 'chrome',
                    'q': f"{seed_keyword} {letter}",
                    'gl': country.lower(),
                    'hl': language
                }
                
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if len(data) > 1:
                        suggestions.extend(data[1])
                
                time.sleep(0.5)
                
            except:
                continue
        
        return suggestions