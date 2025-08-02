from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
import time
import random
import json
import re
from urllib.parse import urljoin, urlparse

class SerpScraper:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.ua = UserAgent()
        self.setup_driver()
        
    def setup_driver(self):
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

    def get_serp_results(self, keyword, location='US', pages=1):
        """Scraping completo de resultados SERP"""
        cache_key = f"serp:{keyword}:{location}:{pages}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        results = {
            'keyword': keyword,
            'location': location,
            'organic_results': [],
            'featured_snippet': None,
            'people_also_ask': [],
            'related_searches': [],
            'total_results': 0
        }
        
        try:
            for page in range(pages):
                start = page * 10
                url = f"https://www.google.com/search?q={keyword}&start={start}&gl={location}&hl=en"
                
                # Delay aleatorio entre requests
                time.sleep(random.uniform(2, 5))
                
                self.driver.get(url)
                
                # Esperar a que cargue la página
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Extraer resultados orgánicos
                organic = self.extract_organic_results(soup, start)
                results['organic_results'].extend(organic)
                
                # Solo en la primera página, extraer features especiales
                if page == 0:
                    results['featured_snippet'] = self.extract_featured_snippet(soup)
                    results['people_also_ask'] = self.extract_people_also_ask(soup)
                    results['related_searches'] = self.extract_related_searches(soup)
                    results['total_results'] = self.extract_total_results(soup)
            
            # Cache por 1 hora
            self.cache.set(cache_key, results, 3600)
            return results
            
        except Exception as e:
            print(f"Error scraping SERP: {str(e)}")
            return results

    def extract_organic_results(self, soup, start_position):
        """Extraer resultados orgánicos"""
        results = []
        
        # Selectores para diferentes tipos de resultados
        result_selectors = [
            'div.g',
            'div[data-ved]',
            '.rc'
        ]
        
        for selector in result_selectors:
            elements = soup.select(selector)
            if elements:
                break
        
        position = start_position + 1
        
        for element in elements:
            try:
                # Título
                title_elem = element.select_one('h3, .LC20lb, .DKV0Md')
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # URL
                link_elem = element.select_one('a[href]')
                url = link_elem.get('href') if link_elem else ''
                
                # Snippet
                snippet_selectors = ['.VwiC3b', '.s3v9rd', '.st']
                snippet = ''
                for sel in snippet_selectors:
                    snippet_elem = element.select_one(sel)
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                        break
                
                if title and url and url.startswith('http'):
                    results.append({
                        'position': position,
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'domain': urlparse(url).netloc
                    })
                    position += 1
                    
            except Exception as e:
                continue
        
        return results

    def extract_featured_snippet(self, soup):
        """Extraer featured snippet"""
        snippet_selectors = [
            '.kp-blk',
            '.xpdopen',
            '.g mnr-c g-blk',
            '.kno-ecr-pt'
        ]
        
        for selector in snippet_selectors:
            element = soup.select_one(selector)
            if element:
                return {
                    'type': 'paragraph',
                    'content': element.get_text(strip=True),
                    'source_url': self.extract_snippet_url(element)
                }
        
        return None

    def extract_people_also_ask(self, soup):
        """Extraer People Also Ask"""
        paa_questions = []
        
        # Diferentes selectores para PAA
        paa_selectors = [
            '.related-question-pair',
            '.cbphWd',
            '[data-ved*="PAA"]'
        ]
        
        for selector in paa_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    question_elem = elem.select_one('.CSkcDe, .oQaa0b')
                    if question_elem:
                        paa_questions.append(question_elem.get_text(strip=True))
                break
        
        return paa_questions[:4]  # Máximo 4 preguntas

    def extract_related_searches(self, soup):
        """Extraer búsquedas relacionadas"""
        related = []
        
        # Selectores para búsquedas relacionadas
        related_selectors = [
            '.brs_col p',
            '.AuVD',
            '.s75CSd'
        ]
        
        for selector in related_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 5:  # Filtrar textos muy cortos
                        related.append(text)
                break
        
        return related[:8]  # Máximo 8 relacionadas

    def extract_total_results(self, soup):
        """Extraer número total de resultados"""
        result_stats = soup.select_one('#result-stats, .LHJvCe')
        if result_stats:
            text = result_stats.get_text()
            # Buscar números en el texto
            numbers = re.findall(r'[\d,]+', text)
            if numbers:
                return int(numbers[0].replace(',', ''))
        return 0

    def get_keyword_suggestions(self, seed_keyword, country='US'):
        """Obtener sugerencias de keywords usando Google Suggest"""
        cache_key = f"suggestions:{seed_keyword}:{country}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        suggestions = []
        
        try:
            # Google Suggest API
            url = "http://suggestqueries.google.com/complete/search"
            params = {
                'client': 'chrome',
                'q': seed_keyword,
                'gl': country.lower(),
                'hl': 'en'
            }
            
            headers = {
                'User-Agent': self.ua.random
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    suggestions = data[1]  # Las sugerencias están en el índice 1
            
            # Obtener también variaciones alfabéticas
            alphabet_suggestions = self.get_alphabet_suggestions(seed_keyword, country)
            suggestions.extend(alphabet_suggestions)
            
            # Limpiar y deduplicar
            suggestions = list(set([s.lower() for s in suggestions if s and len(s) > 2]))
            suggestions.sort()
            
            result = {
                'seed_keyword': seed_keyword,
                'suggestions': suggestions[:50],  # Máximo 50 sugerencias
                'total_found': len(suggestions)
            }
            
            # Cache por 24 horas
            self.cache.set(cache_key, result, 86400)
            return result
            
        except Exception as e:
            print(f"Error getting keyword suggestions: {str(e)}")
            return {'seed_keyword': seed_keyword, 'suggestions': [], 'total_found': 0}

    def get_alphabet_suggestions(self, seed_keyword, country):
        """Obtener sugerencias usando el método alfabético"""
        suggestions = []
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        
        for letter in alphabet[:5]:  # Solo primeras 5 letras para no sobrecargar
            try:
                url = "http://suggestqueries.google.com/complete/search"
                params = {
                    'client': 'chrome',
                    'q': f"{seed_keyword} {letter}",
                    'gl': country.lower(),
                    'hl': 'en'
                }
                
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if len(data) > 1:
                        suggestions.extend(data[1])
                
                time.sleep(0.5)  # Delay para no ser bloqueado
                
            except:
                continue
        
        return suggestions

    def extract_snippet_url(self, element):
        """Extraer URL del featured snippet"""
        link = element.select_one('a[href]')
        return link.get('href') if link else ''

    def __del__(self):
        """Cerrar driver al destruir objeto"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass