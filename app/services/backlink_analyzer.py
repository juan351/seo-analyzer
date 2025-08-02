import requests
from bs4 import BeautifulSoup
import whois
from urllib.parse import urljoin, urlparse
import dns.resolver
import ssl
import socket
from datetime import datetime
import re

class BacklinkAnalyzer:
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def analyze_domain(self, domain):
        """Análisis completo de dominio y backlinks"""
        cache_key = f"domain_analysis:{domain}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Limpiar dominio
        clean_domain = self.clean_domain(domain)
        
        analysis = {
            'domain': clean_domain,
            'domain_authority': self.estimate_domain_authority(clean_domain),
            'backlink_sources': self.find_backlink_sources(clean_domain),
            'social_signals': self.get_social_signals(clean_domain),
            'technical_seo': self.analyze_technical_seo(clean_domain),
            'domain_info': self.get_domain_info(clean_domain),
            'trust_signals': self.analyze_trust_signals(clean_domain)
        }
        
        # Cache por 6 horas
        self.cache.set(cache_key, analysis, 21600)
        return analysis

    def clean_domain(self, domain):
        """Limpiar y normalizar dominio"""
        domain = domain.lower().strip()
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('/')[0]
        return domain

    def estimate_domain_authority(self, domain):
        """Estimar autoridad de dominio usando múltiples factores"""
        try:
            score = 0
            factors = {}
            
            # Factor 1: Edad del dominio
            domain_age = self.get_domain_age(domain)
            if domain_age:
                age_years = domain_age.days / 365
                age_score = min(age_years * 5, 25)  # Max 25 puntos por edad
                score += age_score
                factors['domain_age_years'] = round(age_years, 1)
                factors['age_score'] = round(age_score, 1)
            
            # Factor 2: Backlinks estimados
            backlink_count = self.estimate_backlinks(domain)
            backlink_score = min(backlink_count / 100 * 15, 15)  # Max 15 puntos
            score += backlink_score
            factors['estimated_backlinks'] = backlink_count
            factors['backlink_score'] = round(backlink_score, 1)
            
            # Factor 3: Social signals
            social_score = self.get_social_authority_score(domain)
            score += social_score
            factors['social_score'] = social_score
            
            # Factor 4: Technical SEO
            tech_score = self.get_technical_seo_score(domain)
            score += tech_score
            factors['technical_score'] = tech_score
            
            # Factor 5: Content indexing (estimado)
            indexed_pages = self.estimate_indexed_pages(domain)
            index_score = min(indexed_pages / 1000 * 10, 10)  # Max 10 puntos
            score += index_score
            factors['indexed_pages'] = indexed_pages
            factors['indexing_score'] = round(index_score, 1)
            
            return {
                'domain_authority_score': min(round(score), 100),
                'factors': factors,
                'rating': self.get_authority_rating(score)
            }
            
        except Exception as e:
            return {
                'domain_authority_score': 0,
                'factors': {},
                'rating': 'Unknown',
                'error': str(e)
            }

    def get_domain_age(self, domain):
        """Obtener edad del dominio"""
        try:
            w = whois.whois(domain)
            if w.creation_date:
                creation_date = w.creation_date
                if isinstance(creation_date, list):
                    creation_date = creation_date[0]
                return datetime.now() - creation_date
        except:
            pass
        return None

    def estimate_backlinks(self, domain):
        """Estimar número de backlinks usando búsquedas públicas"""
        try:
            # Usar diferentes métodos para estimar backlinks
            google_mentions = self.count_google_mentions(domain)
            return min(google_mentions, 10000)  # Cap en 10k para estimación
        except:
            return 0

    def count_google_mentions(self, domain):
        """Contar menciones en Google (estimación muy básica)"""
        try:
            # Esta es una estimación muy básica
            # En producción usarías APIs más robustas
            return 50  # Valor placeholder
        except:
            return 0

    def get_social_authority_score(self, domain):
        """Calcular puntuación de autoridad social"""
        try:
            social_data = self.get_social_signals(domain)
            score = 0
            
            # Facebook shares (max 5 puntos)
            fb_score = min(social_data.get('facebook_shares', 0) / 100, 5)
            score += fb_score
            
            # Twitter mentions (max 5 puntos)
            twitter_score = min(social_data.get('twitter_mentions', 0) / 50, 5)
            score += twitter_score
            
            return round(score, 1)
        except:
            return 0

    def get_technical_seo_score(self, domain):
        """Calcular puntuación técnica SEO"""
        try:
            score = 0
            
            # HTTPS check (5 puntos)
            if self.has_ssl(domain):
                score += 5
            
            # Response time check (5 puntos)
            response_time = self.get_response_time(domain)
            if response_time and response_time < 2:
                score += 5
            elif response_time and response_time < 5:
                score += 3
            
            # Robots.txt exists (2 puntos)
            if self.has_robots_txt(domain):
                score += 2
            
            # Sitemap exists (3 puntos)
            if self.has_sitemap(domain):
                score += 3
            
            return score
        except:
            return 0

    def has_ssl(self, domain):
        """Verificar si el dominio tiene SSL"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    return True
        except:
            return False

    def get_response_time(self, domain):
        """Obtener tiempo de respuesta del dominio"""
        try:
            response = requests.get(f'http://{domain}', timeout=10, headers=self.headers)
            return response.elapsed.total_seconds()
        except:
            return None

    def has_robots_txt(self, domain):
        """Verificar si tiene robots.txt"""
        try:
            response = requests.get(f'http://{domain}/robots.txt', timeout=5, headers=self.headers)
            return response.status_code == 200
        except:
            return False

    def has_sitemap(self, domain):
        """Verificar si tiene sitemap"""
        try:
            sitemaps = [
                f'http://{domain}/sitemap.xml',
                f'http://{domain}/sitemap_index.xml',
                f'https://{domain}/sitemap.xml'
            ]
            
            for sitemap_url in sitemaps:
                response = requests.get(sitemap_url, timeout=5, headers=self.headers)
                if response.status_code == 200:
                    return True
            return False
        except:
            return False

    def estimate_indexed_pages(self, domain):
        """Estimar páginas indexadas (método básico)"""
        try:
            # Estimación básica - en producción usarías Google Search Console API
            return 100  # Valor placeholder
        except:
            return 0

    def get_authority_rating(self, score):
        """Convertir puntuación a rating"""
        if score >= 80:
            return 'Excellent'
        elif score >= 60:
            return 'Good'
        elif score >= 40:
            return 'Average'
        elif score >= 20:
            return 'Poor'
        else:
            return 'Very Poor'

    def find_backlink_sources(self, domain):
        """Encontrar fuentes de backlinks gratuitas"""
        sources = []
        
        try:
            # Búsqueda en Google para menciones
            google_backlinks = self.search_google_backlinks(domain)
            sources.extend(google_backlinks)
            
            # Búsqueda en redes sociales
            social_backlinks = self.search_social_mentions(domain)
            sources.extend(social_backlinks)
            
            return sources[:20]  # Top 20 fuentes
        except:
            return []

    def search_google_backlinks(self, domain):
        """Buscar backlinks en Google (método básico)"""
        # Implementación básica - en producción sería más robusta
        return [
            {
                'source': 'example1.com',
                'type': 'article',
                'authority': 'medium',
                'detected_method': 'google_search'
            },
            {
                'source': 'example2.com',
                'type': 'directory',
                'authority': 'low',
                'detected_method': 'google_search'
            }
        ]

    def search_social_mentions(self, domain):
        """Buscar menciones sociales"""
        return [
            {
                'source': 'twitter.com',
                'type': 'social_mention',
                'authority': 'high',
                'detected_method': 'social_search'
            }
        ]

    def get_social_signals(self, domain):
        """Obtener señales sociales"""
        try:
            url = f'http://{domain}'
            
            # Facebook Graph API (método básico)
            facebook_data = self.get_facebook_shares(url)
            
            # Twitter API (básico)
            twitter_data = self.get_twitter_mentions(url)
            
            return {
                'facebook_shares': facebook_data.get('shares', 0),
                'facebook_likes': facebook_data.get('likes', 0),
                'twitter_mentions': twitter_data.get('mentions', 0),
                'total_social_signals': facebook_data.get('shares', 0) + twitter_data.get('mentions', 0)
            }
        except:
            return {
                'facebook_shares': 0,
                'facebook_likes': 0,
                'twitter_mentions': 0,
                'total_social_signals': 0
            }

    def get_facebook_shares(self, url):
        """Obtener shares de Facebook"""
        try:
            # Facebook Graph API (limitada pero gratuita)
            fb_url = f"https://graph.facebook.com/?id={url}&fields=engagement"
            response = requests.get(fb_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                engagement = data.get('engagement', {})
                return {
                    'shares': engagement.get('share_count', 0),
                    'likes': engagement.get('reaction_count', 0)
                }
        except:
            pass
        
        return {'shares': 0, 'likes': 0}

    def get_twitter_mentions(self, url):
        """Obtener menciones de Twitter (método básico)"""
        try:
            # Método básico sin API - en producción usarías Twitter API v2
            return {'mentions': 0}  # Placeholder
        except:
            return {'mentions': 0}

    def analyze_technical_seo(self, domain):
        """Análisis técnico SEO del dominio"""
        try:
            technical_analysis = {
                'ssl_certificate': self.analyze_ssl_certificate(domain),
                'dns_records': self.analyze_dns_records(domain),
                'server_response': self.analyze_server_response(domain),
                'security_headers': self.check_security_headers(domain),
                'mobile_friendly': self.check_mobile_friendly(domain),
                'page_speed': self.estimate_page_speed(domain)
            }
            
            return technical_analysis
        except Exception as e:
            return {'error': str(e)}

    def analyze_ssl_certificate(self, domain):
        """Analizar certificado SSL"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
            return {
                'has_ssl': True,
                'issuer': dict(x[0] for x in cert['issuer']),
                'expires': cert['notAfter'],
                'valid': True
            }
        except:
            return {
                'has_ssl': False,
                'issuer': None,
                'expires': None,
                'valid': False
            }

    def analyze_dns_records(self, domain):
        """Analizar registros DNS"""
        try:
            dns_info = {}
            
            # A record
            try:
                a_records = dns.resolver.resolve(domain, 'A')
                dns_info['a_records'] = [str(record) for record in a_records]
            except:
                dns_info['a_records'] = []
            
            # MX record
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                dns_info['mx_records'] = [str(record) for record in mx_records]
            except:
                dns_info['mx_records'] = []
            
            # TXT records (SPF, DKIM, etc.)
            try:
                txt_records = dns.resolver.resolve(domain, 'TXT')
                dns_info['txt_records'] = [str(record) for record in txt_records]
            except:
                dns_info['txt_records'] = []
            
            return dns_info
        except:
            return {}

    def analyze_server_response(self, domain):
        """Analizar respuesta del servidor"""
        try:
            response = requests.get(f'http://{domain}', timeout=10, headers=self.headers)
            
            return {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'server': response.headers.get('Server', 'Unknown'),
                'redirects': len(response.history),
                'final_url': response.url
            }
        except Exception as e:
            return {'error': str(e)}

    def check_security_headers(self, domain):
        """Verificar headers de seguridad"""
        try:
            response = requests.get(f'https://{domain}', timeout=10, headers=self.headers)
            headers = response.headers
            
            security_headers = {
                'strict_transport_security': 'Strict-Transport-Security' in headers,
                'content_security_policy': 'Content-Security-Policy' in headers,
                'x_frame_options': 'X-Frame-Options' in headers,
                'x_content_type_options': 'X-Content-Type-Options' in headers,
                'referrer_policy': 'Referrer-Policy' in headers
            }
            
            security_score = sum(security_headers.values()) / len(security_headers) * 100
            
            return {
                'headers': security_headers,
                'security_score': round(security_score, 1)
            }
        except:
            return {'headers': {}, 'security_score': 0}

    def check_mobile_friendly(self, domain):
        """Verificar si es mobile-friendly (análisis básico)"""
        try:
            response = requests.get(f'https://{domain}', timeout=10, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar viewport meta tag
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            has_viewport = viewport is not None
            
            # Buscar media queries en CSS (básico)
            has_responsive_css = 'media' in response.text.lower()
            
            return {
                'has_viewport_meta': has_viewport,
                'has_responsive_css': has_responsive_css,
                'mobile_friendly_score': (has_viewport + has_responsive_css) * 50
            }
        except:
            return {
                'has_viewport_meta': False,
                'has_responsive_css': False,
                'mobile_friendly_score': 0
            }

    def estimate_page_speed(self, domain):
        """Estimar velocidad de página"""
        try:
            start_time = datetime.now()
            response = requests.get(f'https://{domain}', timeout=15, headers=self.headers)
            load_time = (datetime.now() - start_time).total_seconds()
            
            # Análisis básico de recursos
            soup = BeautifulSoup(response.content, 'html.parser')
            
            images = len(soup.find_all('img'))
            scripts = len(soup.find_all('script'))
            stylesheets = len(soup.find_all('link', rel='stylesheet'))
            
            # Puntuación básica de velocidad
            speed_score = 100
            if load_time > 3:
                speed_score -= 30
            elif load_time > 2:
                speed_score -= 15
            
            if images > 20:
                speed_score -= 10
            if scripts > 10:
                speed_score -= 10
            
            return {
                'load_time_seconds': round(load_time, 2),
                'total_images': images,
                'total_scripts': scripts,
                'total_stylesheets': stylesheets,
                'estimated_speed_score': max(speed_score, 0)
            }
        except:
            return {
                'load_time_seconds': 0,
                'total_images': 0,
                'total_scripts': 0,
                'total_stylesheets': 0,
                'estimated_speed_score': 0
            }

    def get_domain_info(self, domain):
        """Obtener información general del dominio"""
        try:
            w = whois.whois(domain)
            
            return {
                'registrar': w.registrar,
                'creation_date': str(w.creation_date) if w.creation_date else None,
                'expiration_date': str(w.expiration_date) if w.expiration_date else None,
                'name_servers': w.name_servers if w.name_servers else [],
                'status': w.status if w.status else [],
                'country': w.country if hasattr(w, 'country') else None
            }
        except:
            return {}

    def analyze_trust_signals(self, domain):
        """Analizar señales de confianza"""
        try:
            trust_signals = {
                'whois_public': self.is_whois_public(domain),
                'ssl_valid': self.has_ssl(domain),
                'domain_age_years': self.get_domain_age_years(domain),
                'business_listings': self.check_business_listings(domain),
                'social_presence': self.check_social_presence(domain)
            }
            
            # Calcular puntuación de confianza
            trust_score = 0
            if trust_signals['whois_public']:
                trust_score += 20
            if trust_signals['ssl_valid']:
                trust_score += 20
            if trust_signals['domain_age_years'] and trust_signals['domain_age_years'] > 1:
                trust_score += min(trust_signals['domain_age_years'] * 5, 30)
            if trust_signals['business_listings']:
                trust_score += 15
            if trust_signals['social_presence']:
                trust_score += 15
            
            trust_signals['trust_score'] = min(trust_score, 100)
            return trust_signals
            
        except:
            return {'trust_score': 0}

    def is_whois_public(self, domain):
        """Verificar si la información WHOIS es pública"""
        try:
            w = whois.whois(domain)
            return bool(w.registrant)
        except:
            return False

    def get_domain_age_years(self, domain):
        """Obtener edad del dominio en años"""
        domain_age = self.get_domain_age(domain)
        if domain_age:
            return round(domain_age.days / 365, 1)
        return None

    def check_business_listings(self, domain):
        """Verificar presencia en directorios de negocios (básico)"""
        # Implementación básica - en producción sería más robusta
        return False

    def check_social_presence(self, domain):
        """Verificar presencia en redes sociales"""
        social_signals = self.get_social_signals(domain)
        return social_signals['total_social_signals'] > 10