import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime
import json
import ssl
import socket
from urllib.request import urlopen
import gzip
from io import BytesIO

class PerformanceAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def analyze_url(self, url):
        """Análisis completo y realista de rendimiento de URL"""
        try:
            print(f"🔍 Analizando rendimiento de: {url}")
            
            analysis = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'loading_performance': self.analyze_loading_performance(url),
                'page_structure': self.analyze_page_structure(url),
                'resource_analysis': self.analyze_resources(url),
                'seo_elements': self.analyze_seo_elements(url),
                'security_analysis': self.analyze_security(url),
                'mobile_friendliness': self.analyze_mobile_friendliness(url),
                'performance_score': 0,
                'recommendations': []
            }
            
            # Intentar obtener datos de PageSpeed Insights si está disponible
            try:
                psi_data = self.get_pagespeed_insights(url)
                if psi_data:
                    analysis['pagespeed_insights'] = psi_data
            except Exception as e:
                print(f"⚠️ No se pudo obtener PageSpeed Insights: {e}")
            
            # Calcular puntuación general
            analysis['performance_score'] = self.calculate_performance_score(analysis)
            
            # Generar recomendaciones
            analysis['recommendations'] = self.generate_performance_recommendations(analysis)
            
            print(f"✅ Análisis completado. Score: {analysis['performance_score']}/100")
            return analysis
            
        except Exception as e:
            print(f"❌ Error analizando URL: {e}")
            return {'url': url, 'error': str(e)}

    def analyze_loading_performance(self, url):
        """Análisis real de velocidad de carga"""
        try:
            performance_data = {
                'response_times': [],
                'dns_lookup_time': 0,
                'connection_time': 0,
                'ssl_handshake_time': 0,
                'time_to_first_byte': 0,
                'full_page_load_time': 0,
                'page_size': 0,
                'compression_enabled': False,
                'http_version': 'HTTP/1.1',
                'status_code': 0
            }
            
            # Múltiples mediciones para mayor precisión
            response_times = []
            
            for i in range(3):
                start_time = time.time()
                try:
                    response = requests.get(url, headers=self.headers, timeout=15, stream=True)
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    if i == 0:  # Solo en la primera medición
                        performance_data['status_code'] = response.status_code
                        performance_data['page_size'] = len(response.content)
                        
                        # Verificar compresión
                        content_encoding = response.headers.get('content-encoding', '')
                        performance_data['compression_enabled'] = 'gzip' in content_encoding or 'br' in content_encoding
                        
                        # Verificar HTTP version (aproximado)
                        if 'http/2' in str(response.headers).lower():
                            performance_data['http_version'] = 'HTTP/2'
                    
                    time.sleep(1)  # Delay entre mediciones
                    
                except Exception as e:
                    print(f"Error en medición {i+1}: {e}")
                    continue
            
            if response_times:
                performance_data['response_times'] = response_times
                performance_data['full_page_load_time'] = sum(response_times) / len(response_times)
                performance_data['time_to_first_byte'] = min(response_times)
            
            # Análisis DNS (básico)
            try:
                domain = urlparse(url).netloc
                dns_start = time.time()
                socket.gethostbyname(domain)
                performance_data['dns_lookup_time'] = time.time() - dns_start
            except:
                pass
            
            return performance_data
            
        except Exception as e:
            print(f"Error analizando rendimiento de carga: {e}")
            return {'error': str(e)}

    def get_pagespeed_insights(self, url, api_key=None):
        """Obtener datos reales de Google PageSpeed Insights"""
        if not api_key:
            # Intentar obtener API key de variables de entorno
            import os
            api_key = os.getenv('GOOGLE_PAGESPEED_API_KEY')
        
        if not api_key:
            return None
        
        try:
            psi_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
            params = {
                'url': url,
                'key': api_key,
                'category': ['PERFORMANCE', 'SEO', 'BEST_PRACTICES'],
                'strategy': 'DESKTOP'
            }
            
            response = requests.get(psi_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                lighthouse_result = data.get('lighthouseResult', {})
                categories = lighthouse_result.get('categories', {})
                
                return {
                    'performance_score': categories.get('performance', {}).get('score', 0) * 100,
                    'seo_score': categories.get('seo', {}).get('score', 0) * 100,
                    'best_practices_score': categories.get('best-practices', {}).get('score', 0) * 100,
                    'core_web_vitals': self.extract_core_web_vitals(lighthouse_result),
                    'opportunities': self.extract_opportunities(lighthouse_result)
                }
            
        except Exception as e:
            print(f"Error obteniendo PageSpeed Insights: {e}")
        
        return None

    def extract_core_web_vitals(self, lighthouse_result):
        """Extraer Core Web Vitals reales de Lighthouse"""
        audits = lighthouse_result.get('audits', {})
        
        return {
            'largest_contentful_paint': {
                'value': audits.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000,
                'rating': audits.get('largest-contentful-paint', {}).get('score', 0),
                'unit': 'seconds'
            },
            'first_input_delay': {
                'value': audits.get('max-potential-fid', {}).get('numericValue', 0),
                'rating': audits.get('max-potential-fid', {}).get('score', 0),
                'unit': 'milliseconds'
            },
            'cumulative_layout_shift': {
                'value': audits.get('cumulative-layout-shift', {}).get('numericValue', 0),
                'rating': audits.get('cumulative-layout-shift', {}).get('score', 0),
                'unit': 'score'
            }
        }

    def extract_opportunities(self, lighthouse_result):
        """Extraer oportunidades de mejora de Lighthouse"""
        audits = lighthouse_result.get('audits', {})
        opportunities = []
        
        opportunity_audits = [
            'unused-css-rules', 'unused-javascript', 'modern-image-formats',
            'uses-optimized-images', 'efficient-animated-content',
            'render-blocking-resources', 'uses-text-compression'
        ]
        
        for audit_key in opportunity_audits:
            audit = audits.get(audit_key, {})
            if audit.get('score', 1) < 1:  # Si no es perfecto
                opportunities.append({
                    'type': audit_key,
                    'title': audit.get('title', ''),
                    'description': audit.get('description', ''),
                    'potential_savings': audit.get('details', {}).get('overallSavingsMs', 0)
                })
        
        return opportunities

    def analyze_page_structure(self, url):
        """Analizar estructura de la página (mejorado)"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Analizar headings
            headings = {}
            heading_hierarchy = []
            for i in range(1, 7):
                headings_found = soup.find_all(f'h{i}')
                headings[f'h{i}'] = len(headings_found)
                for h in headings_found:
                    heading_hierarchy.append({
                        'level': i,
                        'text': h.get_text().strip()[:100]
                    })
            
            # Analizar imágenes con más detalle
            images = soup.find_all('img')
            images_analysis = {
                'total': len(images),
                'without_alt': 0,
                'with_lazy_loading': 0,
                'optimized_formats': 0,
                'large_images': 0
            }
            
            for img in images:
                if not img.get('alt'):
                    images_analysis['without_alt'] += 1
                
                if img.get('loading') == 'lazy':
                    images_analysis['with_lazy_loading'] += 1
                
                src = img.get('src', '')
                if any(fmt in src.lower() for fmt in ['.webp', '.avif']):
                    images_analysis['optimized_formats'] += 1
                
                # Detectar imágenes grandes (básico)
                if any(size in src for size in ['1920', '1080', '2048']):
                    images_analysis['large_images'] += 1
            
            # Analizar enlaces
            links = soup.find_all('a', href=True)
            internal_links = []
            external_links = []
            
            domain = urlparse(url).netloc
            
            for link in links:
                href = link['href']
                if href.startswith('http'):
                    if domain in href:
                        internal_links.append(href)
                    else:
                        external_links.append(href)
                elif href.startswith('/'):
                    internal_links.append(href)
            
            # Analizar scripts y estilos
            scripts = soup.find_all('script')
            inline_scripts = len([s for s in scripts if not s.get('src')])
            external_scripts = len([s for s in scripts if s.get('src')])
            
            styles = soup.find_all('style')
            inline_styles = len(styles)
            external_stylesheets = len(soup.find_all('link', rel='stylesheet'))
            
            return {
                'headings': headings,
                'heading_hierarchy': heading_hierarchy,
                'total_headings': sum(headings.values()),
                'images': images_analysis,
                'links': {
                    'total': len(links),
                    'internal': len(internal_links),
                    'external': len(external_links),
                    'internal_ratio': len(internal_links) / len(links) * 100 if links else 0
                },
                'scripts': {
                    'inline': inline_scripts,
                    'external': external_scripts,
                    'total': inline_scripts + external_scripts
                },
                'styles': {
                    'inline': inline_styles,
                    'external': external_stylesheets,
                    'total': inline_styles + external_stylesheets
                },
                'word_count': len(soup.get_text().split()),
                'dom_size': len(soup.find_all())
            }
            
        except Exception as e:
            print(f"Error analizando estructura: {e}")
            return {'error': str(e)}

    def analyze_resources(self, url):
        """Análisis avanzado de recursos"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Analizar recursos externos
            external_resources = {
                'css': [],
                'js': [],
                'images': [],
                'fonts': [],
                'other': []
            }
            
            # CSS
            for css in soup.find_all('link', rel='stylesheet'):
                href = css.get('href', '')
                if href:
                    external_resources['css'].append(href)
            
            # JavaScript
            for js in soup.find_all('script', src=True):
                src = js.get('src', '')
                if src:
                    external_resources['js'].append(src)
            
            # Images
            for img in soup.find_all('img', src=True):
                src = img.get('src', '')
                if src and src.startswith('http'):
                    external_resources['images'].append(src)
            
            # Fonts
            for link in soup.find_all('link'):
                href = link.get('href', '')
                if 'font' in href.lower() or 'googleapis.com/css' in href:
                    external_resources['fonts'].append(href)
            
            # Calcular tamaños estimados y métricas
            page_size = len(response.content)
            
            # Analizar compresión
            content_encoding = response.headers.get('content-encoding', '')
            is_compressed = 'gzip' in content_encoding or 'br' in content_encoding or 'deflate' in content_encoding
            
            # Analizar caching
            cache_control = response.headers.get('cache-control', '')
            expires = response.headers.get('expires', '')
            etag = response.headers.get('etag', '')
            has_caching = bool(cache_control or expires or etag)
            
            # Resource optimization score
            resource_score = 100
            css_count = len(external_resources['css'])
            js_count = len(external_resources['js'])
            font_count = len(external_resources['fonts'])
            
            if css_count > 3:
                resource_score -= min(css_count * 3, 15)
            if js_count > 5:
                resource_score -= min(js_count * 2, 20)
            if font_count > 2:
                resource_score -= min(font_count * 5, 15)
            if not is_compressed:
                resource_score -= 20
            if not has_caching:
                resource_score -= 15
            if page_size > 2000000:  # 2MB
                resource_score -= 25
            
            return {
                'external_resources': external_resources,
                'resource_counts': {
                    'css_files': css_count,
                    'javascript_files': js_count,
                    'external_images': len(external_resources['images']),
                    'font_files': font_count,
                    'total_external': sum(len(resources) for resources in external_resources.values())
                },
                'page_size': {
                    'bytes': page_size,
                    'mb': round(page_size / 1048576, 2),
                    'kb': round(page_size / 1024, 2)
                },
                'optimization': {
                    'compression_enabled': is_compressed,
                    'compression_type': content_encoding,
                    'caching_enabled': has_caching,
                    'cache_headers': {
                        'cache_control': cache_control,
                        'expires': expires,
                        'etag': bool(etag)
                    }
                },
                'resource_optimization_score': max(resource_score, 0)
            }
            
        except Exception as e:
            print(f"Error analizando recursos: {e}")
            return {'error': str(e)}

    def analyze_security(self, url):
        """Análisis de seguridad web"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            security_headers = {
                'https': url.startswith('https://'),
                'hsts': 'strict-transport-security' in response.headers,
                'content_security_policy': 'content-security-policy' in response.headers,
                'x_frame_options': 'x-frame-options' in response.headers,
                'x_content_type_options': 'x-content-type-options' in response.headers,
                'referrer_policy': 'referrer-policy' in response.headers,
                'x_xss_protection': 'x-xss-protection' in response.headers
            }
            
            # Calcular score de seguridad
            security_score = 0
            total_checks = len(security_headers)
            
            for check, passed in security_headers.items():
                if passed:
                    security_score += 1
            
            security_percentage = (security_score / total_checks) * 100
            
            return {
                'security_headers': security_headers,
                'security_score': security_percentage,
                'security_grade': self.get_security_grade(security_percentage),
                'missing_headers': [header for header, present in security_headers.items() if not present]
            }
            
        except Exception as e:
            print(f"Error analizando seguridad: {e}")
            return {'error': str(e)}

    def get_security_grade(self, percentage):
        """Obtener calificación de seguridad"""
        if percentage >= 85:
            return 'A'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 55:
            return 'C'
        elif percentage >= 40:
            return 'D'
        else:
            return 'F'

    def analyze_mobile_friendliness(self, url):
        """Análisis básico de mobile-friendliness"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            mobile_analysis = {
                'viewport_meta': False,
                'responsive_design': False,
                'mobile_optimized_fonts': False,
                'touch_friendly_elements': True,  # Asumimos true por defecto
                'mobile_score': 0
            }
            
            # Verificar viewport meta tag
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            if viewport:
                content = viewport.get('content', '').lower()
                mobile_analysis['viewport_meta'] = True
                mobile_analysis['responsive_design'] = 'width=device-width' in content
            
            # Verificar media queries en CSS (básico)
            styles = soup.find_all('style')
            css_text = ' '.join([style.get_text() for style in styles])
            has_media_queries = '@media' in css_text and ('max-width' in css_text or 'min-width' in css_text)
            
            if has_media_queries:
                mobile_analysis['responsive_design'] = True
            
            # Verificar fuentes optimized para mobile
            if 'font-size' in css_text:
                mobile_analysis['mobile_optimized_fonts'] = True
            
            # Calcular score móvil
            mobile_checks = [
                mobile_analysis['viewport_meta'],
                mobile_analysis['responsive_design'],
                mobile_analysis['mobile_optimized_fonts'],
                mobile_analysis['touch_friendly_elements']
            ]
            
            mobile_analysis['mobile_score'] = (sum(mobile_checks) / len(mobile_checks)) * 100
            
            return mobile_analysis
            
        except Exception as e:
            print(f"Error analizando mobile-friendliness: {e}")
            return {'error': str(e)}

    def analyze_seo_elements(self, url):
        """Análisis SEO mejorado y más completo"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Title tag
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ''
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_desc_text = meta_desc.get('content', '').strip() if meta_desc else ''
            
            # Meta keywords (deprecated but still analyzed)
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            meta_keywords_text = meta_keywords.get('content', '').strip() if meta_keywords else ''
            
            # H1 tags
            h1_tags = soup.find_all('h1')
            
            # Canonical URL
            canonical = soup.find('link', rel='canonical')
            canonical_url = canonical.get('href') if canonical else ''
            
            # Robots meta
            robots_meta = soup.find('meta', attrs={'name': 'robots'})
            robots_content = robots_meta.get('content', '').lower() if robots_meta else ''
            
            # Open Graph tags
            og_tags = {}
            og_elements = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
            for og in og_elements:
                property_name = og.get('property', '').replace('og:', '')
                og_tags[property_name] = og.get('content', '')
            
            # Twitter Card tags
            twitter_tags = {}
            twitter_elements = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
            for twitter in twitter_elements:
                name = twitter.get('name', '').replace('twitter:', '')
                twitter_tags[name] = twitter.get('content', '')
            
            # Schema markup
            schema_scripts = soup.find_all('script', type='application/ld+json')
            schema_data = []
            for script in schema_scripts:
                try:
                    schema_json = json.loads(script.get_text())
                    schema_data.append(schema_json)
                except:
                    pass
            
            # Alt text analysis
            images = soup.find_all('img')
            images_with_alt = [img for img in images if img.get('alt')]
            alt_text_ratio = len(images_with_alt) / len(images) * 100 if images else 100
            
            # Internal linking
            links = soup.find_all('a', href=True)
            domain = urlparse(url).netloc
            internal_links = [link for link in links if domain in link.get('href', '') or link.get('href', '').startswith('/')]
            
            return {
                'title': {
                    'text': title_text,
                    'length': len(title_text),
                    'exists': bool(title_text),
                    'optimal_length': 30 <= len(title_text) <= 60,
                    'has_brand': any(word in title_text.lower() for word in ['brand', 'company'] if title_text)
                },
                'meta_description': {
                    'text': meta_desc_text,
                    'length': len(meta_desc_text),
                    'exists': bool(meta_desc_text),
                    'optimal_length': 120 <= len(meta_desc_text) <= 160,
                    'has_call_to_action': any(cta in meta_desc_text.lower() for cta in ['learn', 'discover', 'get', 'find', 'read'] if meta_desc_text)
                },
                'meta_keywords': {
                    'text': meta_keywords_text,
                    'exists': bool(meta_keywords_text),
                    'deprecated': True
                },
                'headings': {
                    'h1_count': len(h1_tags),
                    'h1_texts': [h1.get_text().strip() for h1 in h1_tags],
                    'optimal_h1': len(h1_tags) == 1,
                    'h1_length_ok': len(h1_tags[0].get_text().strip()) <= 70 if h1_tags else False
                },
                'canonical': {
                    'url': canonical_url,
                    'exists': bool(canonical_url),
                    'is_self_referencing': canonical_url == url if canonical_url else False
                },
                'robots': {
                    'meta_exists': bool(robots_meta),
                    'content': robots_content,
                    'noindex': 'noindex' in robots_content,
                    'nofollow': 'nofollow' in robots_content
                },
                'open_graph': {
                    'tags': og_tags,
                    'complete': all(key in og_tags for key in ['title', 'description', 'image', 'url']),
                    'tag_count': len(og_tags)
                },
                'twitter_cards': {
                    'tags': twitter_tags,
                    'exists': bool(twitter_tags),
                    'complete': 'card' in twitter_tags and 'title' in twitter_tags
                },
                'schema_markup': {
                    'exists': len(schema_data) > 0,
                    'count': len(schema_data),
                    'types': [schema.get('@type', 'Unknown') for schema in schema_data if isinstance(schema, dict)]
                },
                'images': {
                    'total': len(images),
                    'with_alt': len(images_with_alt),
                    'alt_text_ratio': alt_text_ratio,
                    'alt_text_complete': alt_text_ratio >= 90
                },
                'internal_linking': {
                    'total_links': len(links),
                    'internal_links': len(internal_links),
                    'internal_ratio': len(internal_links) / len(links) * 100 if links else 0
                }
            }
            
        except Exception as e:
            print(f"Error analizando elementos SEO: {e}")
            return {'error': str(e)}

    def calculate_performance_score(self, analysis):
        """Calcular puntuación general de rendimiento (mejorado)"""
        score = 0
        max_score = 100
        
        try:
            # Loading Performance (25 puntos)
            loading = analysis.get('loading_performance', {})
            load_time = loading.get('full_page_load_time', 10)
            
            if load_time <= 2:
                score += 25
            elif load_time <= 4:
                score += 20
            elif load_time <= 6:
                score += 15
            elif load_time <= 8:
                score += 10
            else:
                score += 5
            
            # PageSpeed Insights (25 puntos) - si está disponible
            psi = analysis.get('pagespeed_insights')
            if psi:
                psi_score = psi.get('performance_score', 0) / 100 * 25
                score += psi_score
            else:
                # Fallback basado en análisis propio
                resource_score = analysis.get('resource_analysis', {}).get('resource_optimization_score', 0)
                score += (resource_score / 100) * 25
            
            # SEO Elements (25 puntos)
            seo = analysis.get('seo_elements', {})
            seo_score = 0
            
            if seo.get('title', {}).get('optimal_length'):
                seo_score += 5
            if seo.get('meta_description', {}).get('optimal_length'):
                seo_score += 5
            if seo.get('headings', {}).get('optimal_h1'):
                seo_score += 4
            if seo.get('canonical', {}).get('exists'):
                seo_score += 3
            if seo.get('schema_markup', {}).get('exists'):
                seo_score += 3
            if seo.get('open_graph', {}).get('complete'):
                seo_score += 3
            if seo.get('images', {}).get('alt_text_complete'):
                seo_score += 2
            
            score += seo_score
            
            # Security (15 puntos)
            security = analysis.get('security_analysis', {})
            security_percentage = security.get('security_score', 0)
            score += (security_percentage / 100) * 15
            
            # Mobile Friendliness (10 puntos)
            mobile = analysis.get('mobile_friendliness', {})
            mobile_score = mobile.get('mobile_score', 0)
            score += (mobile_score / 100) * 10
            
            return min(round(score), max_score)
            
        except Exception as e:
            print(f"Error calculando score: {e}")
            return 0

    def generate_performance_recommendations(self, analysis):
        """Generar recomendaciones detalladas y actionables"""
        recommendations = []
        
        try:
            # Loading Performance recommendations
            loading = analysis.get('loading_performance', {})
            load_time = loading.get('full_page_load_time', 0)
            
            if load_time > 4:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'high',
                    'category': 'Loading Speed',
                    'title': 'Improve Page Load Time',
                    'description': f'Page loads in {load_time:.2f} seconds. Target: under 3 seconds.',
                    'impact': 'high',
                    'actions': [
                        'Optimize images and use modern formats (WebP, AVIF)',
                        'Enable compression (gzip/brotli)',
                        'Minimize CSS and JavaScript files',
                        'Use a Content Delivery Network (CDN)'
                    ]
                })
            
            # Resource optimization recommendations
            resources = analysis.get('resource_analysis', {})
            
            if not resources.get('optimization', {}).get('compression_enabled'):
                recommendations.append({
                    'type': 'performance',
                    'priority': 'high',
                    'category': 'Resource Optimization',
                    'title': 'Enable Compression',
                    'description': 'Enable gzip or brotli compression to reduce file sizes.',
                    'impact': 'high',
                    'actions': [
                        'Configure server to enable gzip compression',
                        'Consider brotli compression for better results',
                        'Compress HTML, CSS, and JavaScript files'
                    ]
                })
            
            if not resources.get('optimization', {}).get('caching_enabled'):
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'category': 'Caching',
                    'title': 'Implement Browser Caching',
                    'description': 'Set proper cache headers to improve repeat visit performance.',
                    'impact': 'medium',
                    'actions': [
                        'Set Cache-Control headers for static resources',
                        'Use ETags for cache validation',
                        'Configure expires headers'
                    ]
                })
            
            resource_counts = resources.get('resource_counts', {})
            if resource_counts.get('css_files', 0) > 3:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'category': 'Resource Optimization',
                    'title': 'Reduce CSS Files',
                    'description': f'Found {resource_counts["css_files"]} CSS files. Consider combining them.',
                    'impact': 'medium',
                    'actions': [
                        'Combine multiple CSS files into one',
                        'Use CSS minification',
                        'Remove unused CSS rules'
                    ]
                })
            
            if resource_counts.get('javascript_files', 0) > 5:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'category': 'Resource Optimization',
                    'title': 'Optimize JavaScript',
                    'description': f'Found {resource_counts["javascript_files"]} JS files. Consider optimization.',
                    'impact': 'medium',
                    'actions': [
                        'Combine and minify JavaScript files',
                        'Use async/defer attributes for non-critical scripts',
                        'Remove unused JavaScript code'
                    ]
                })
            
            page_size = resources.get('page_size', {}).get('mb', 0)
            if page_size > 2:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'high',
                    'category': 'Page Size',
                    'title': 'Reduce Page Size',
                    'description': f'Page size is {page_size} MB. Target: under 2MB.',
                    'impact': 'high',
                    'actions': [
                        'Optimize and compress images',
                        'Use modern image formats (WebP, AVIF)',
                        'Implement lazy loading for images',
                        'Remove unnecessary resources'
                    ]
                })
            
            # SEO recommendations
            seo = analysis.get('seo_elements', {})
            
            if not seo.get('title', {}).get('exists'):
                recommendations.append({
                    'type': 'seo',
                    'priority': 'critical',
                    'category': 'SEO Basics',
                    'title': 'Add Title Tag',
                    'description': 'Page is missing a title tag. This is critical for SEO.',
                    'impact': 'critical',
                    'actions': [
                        'Add a descriptive title tag to the page',
                        'Keep title between 30-60 characters',
                        'Include primary keyword in title'
                    ]
                })
            elif not seo.get('title', {}).get('optimal_length'):
                title_length = seo.get('title', {}).get('length', 0)
                recommendations.append({
                    'type': 'seo',
                    'priority': 'high',
                    'category': 'SEO Optimization',
                    'title': 'Optimize Title Length',
                    'description': f'Title is {title_length} characters. Optimal range is 30-60 characters.',
                    'impact': 'high',
                    'actions': [
                        'Adjust title length to 30-60 characters',
                        'Ensure title is descriptive and compelling',
                        'Include primary keyword near the beginning'
                    ]
                })
            
            if not seo.get('meta_description', {}).get('exists'):
                recommendations.append({
                    'type': 'seo',
                    'priority': 'high',
                    'category': 'SEO Basics',
                    'title': 'Add Meta Description',
                    'description': 'Page is missing a meta description. This affects click-through rates.',
                    'impact': 'high',
                    'actions': [
                        'Add a compelling meta description',
                        'Keep description between 120-160 characters',
                        'Include a call-to-action'
                    ]
                })
            elif not seo.get('meta_description', {}).get('optimal_length'):
                desc_length = seo.get('meta_description', {}).get('length', 0)
                recommendations.append({
                    'type': 'seo',
                    'priority': 'medium',
                    'category': 'SEO Optimization',
                    'title': 'Optimize Meta Description Length',
                    'description': f'Meta description is {desc_length} characters. Optimal range is 120-160 characters.',
                    'impact': 'medium',
                    'actions': [
                        'Adjust meta description to 120-160 characters',
                        'Make it compelling and relevant',
                        'Include target keywords naturally'
                    ]
                })
            
            if not seo.get('headings', {}).get('optimal_h1'):
                h1_count = seo.get('headings', {}).get('h1_count', 0)
                if h1_count == 0:
                    recommendations.append({
                        'type': 'seo',
                        'priority': 'high',
                        'category': 'Content Structure',
                        'title': 'Add H1 Tag',
                        'description': 'Page is missing an H1 tag. This is important for SEO structure.',
                        'impact': 'high',
                        'actions': [
                            'Add a descriptive H1 tag to the page',
                            'Include primary keyword in H1',
                            'Make H1 unique and relevant to page content'
                        ]
                    })
                elif h1_count > 1:
                    recommendations.append({
                        'type': 'seo',
                        'priority': 'medium',
                        'category': 'Content Structure',
                        'title': 'Multiple H1 Tags Found',
                        'description': f'Found {h1_count} H1 tags. Use only one H1 per page.',
                        'impact': 'medium',
                        'actions': [
                            'Use only one H1 tag per page',
                            'Convert additional H1s to H2 or H3 tags',
                            'Maintain proper heading hierarchy'
                        ]
                    })
            
            if not seo.get('canonical', {}).get('exists'):
                recommendations.append({
                    'type': 'seo',
                    'priority': 'medium',
                    'category': 'Technical SEO',
                    'title': 'Add Canonical URL',
                    'description': 'Add canonical URL to prevent duplicate content issues.',
                    'impact': 'medium',
                    'actions': [
                        'Add self-referencing canonical tag',
                        'Ensure canonical URL is accessible',
                        'Use absolute URLs in canonical tags'
                    ]
                })
            
            if not seo.get('schema_markup', {}).get('exists'):
                recommendations.append({
                    'type': 'seo',
                    'priority': 'medium',
                    'category': 'Structured Data',
                    'title': 'Implement Schema Markup',
                    'description': 'Add structured data to help search engines understand your content.',
                    'impact': 'medium',
                    'actions': [
                        'Add relevant schema.org markup',
                        'Use JSON-LD format for structured data',
                        'Test markup with Google\'s Structured Data Testing Tool'
                    ]
                })
            
            # Image optimization recommendations
            images = seo.get('images', {})
            if images.get('alt_text_ratio', 100) < 90:
                missing_alt = images.get('total', 0) - images.get('with_alt', 0)
                recommendations.append({
                    'type': 'accessibility',
                    'priority': 'medium',
                    'category': 'Image Optimization',
                    'title': 'Add Alt Text to Images',
                    'description': f'{missing_alt} images are missing alt text.',
                    'impact': 'medium',
                    'actions': [
                        'Add descriptive alt text to all images',
                        'Keep alt text concise and relevant',
                        'Use empty alt="" for decorative images'
                    ]
                })
            
            # Security recommendations
            security = analysis.get('security_analysis', {})
            missing_headers = security.get('missing_headers', [])
            
            if not security.get('security_headers', {}).get('https'):
                recommendations.append({
                    'type': 'security',
                    'priority': 'critical',
                    'category': 'Security',
                    'title': 'Enable HTTPS',
                    'description': 'Site is not using HTTPS. This is critical for security and SEO.',
                    'impact': 'critical',
                    'actions': [
                        'Install SSL certificate',
                        'Redirect all HTTP traffic to HTTPS',
                        'Update all internal links to use HTTPS'
                    ]
                })
            
            if 'content_security_policy' in missing_headers:
                recommendations.append({
                    'type': 'security',
                    'priority': 'medium',
                    'category': 'Security Headers',
                    'title': 'Implement Content Security Policy',
                    'description': 'Add CSP header to prevent XSS attacks.',
                    'impact': 'medium',
                    'actions': [
                        'Define Content-Security-Policy header',
                        'Start with a restrictive policy',
                        'Test thoroughly before deployment'
                    ]
                })
            
            # Mobile recommendations
            mobile = analysis.get('mobile_friendliness', {})
            if not mobile.get('viewport_meta'):
                recommendations.append({
                    'type': 'mobile',
                    'priority': 'high',
                    'category': 'Mobile Optimization',
                    'title': 'Add Viewport Meta Tag',
                    'description': 'Add viewport meta tag for proper mobile display.',
                    'impact': 'high',
                    'actions': [
                        'Add <meta name="viewport" content="width=device-width, initial-scale=1">',
                        'Test mobile responsiveness',
                        'Ensure content fits mobile screens'
                    ]
                })
            
            if not mobile.get('responsive_design'):
                recommendations.append({
                    'type': 'mobile',
                    'priority': 'high',
                    'category': 'Mobile Optimization',
                    'title': 'Implement Responsive Design',
                    'description': 'Make your website responsive for mobile devices.',
                    'impact': 'high',
                    'actions': [
                        'Use CSS media queries for responsive design',
                        'Test on various device sizes',
                        'Optimize touch targets for mobile'
                    ]
                })
            
            # PageSpeed Insights recommendations (if available)
            psi = analysis.get('pagespeed_insights')
            if psi and psi.get('opportunities'):
                for opportunity in psi['opportunities'][:3]:  # Top 3 opportunities
                    recommendations.append({
                        'type': 'pagespeed',
                        'priority': 'medium',
                        'category': 'PageSpeed Optimization',
                        'title': opportunity.get('title', 'PageSpeed Optimization'),
                        'description': opportunity.get('description', ''),
                        'impact': 'medium' if opportunity.get('potential_savings', 0) > 500 else 'low',
                        'actions': ['Implement based on PageSpeed Insights recommendation']
                    })
            
            return recommendations
            
        except Exception as e:
            print(f"Error generando recomendaciones: {e}")
            return [{
                'type': 'error',
                'priority': 'low',
                'category': 'System',
                'title': 'Error Generating Recommendations',
                'description': f'Error generating recommendations: {str(e)}',
                'impact': 'low'
            }]