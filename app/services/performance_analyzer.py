import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime
import json

class PerformanceAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def analyze_url(self, url):
        """Análisis completo de rendimiento de URL"""
        try:
            analysis = {
                'url': url,
                'core_web_vitals': self.analyze_core_web_vitals(url),
                'page_structure': self.analyze_page_structure(url),
                'resource_analysis': self.analyze_resources(url),
                'seo_elements': self.analyze_seo_elements(url),
                'performance_score': 0,
                'recommendations': []
            }
            
            # Calcular puntuación general
            analysis['performance_score'] = self.calculate_performance_score(analysis)
            
            # Generar recomendaciones
            analysis['recommendations'] = self.generate_performance_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            return {'url': url, 'error': str(e)}

    def analyze_core_web_vitals(self, url):
        """Análisis básico de Core Web Vitals"""
        try:
            start_time = time.time()
            response = requests.get(url, headers=self.headers, timeout=15)
            load_time = time.time() - start_time
            
            # Largest Contentful Paint (estimado)
            lcp_estimate = load_time * 1.2  # Estimación básica
            
            # First Input Delay (no se puede medir sin JavaScript real)
            fid_estimate = 50  # Estimación conservadora en ms
            
            # Cumulative Layout Shift (básico)
            cls_estimate = 0.1  # Estimación básica
            
            return {
                'largest_contentful_paint': {
                    'value': round(lcp_estimate, 2),
                    'rating': self.rate_lcp(lcp_estimate),
                    'unit': 'seconds'
                },
                'first_input_delay': {
                    'value': fid_estimate,
                    'rating': self.rate_fid(fid_estimate),
                    'unit': 'milliseconds'
                },
                'cumulative_layout_shift': {
                    'value': cls_estimate,
                    'rating': self.rate_cls(cls_estimate),
                    'unit': 'score'
                },
                'overall_rating': self.get_overall_cwv_rating(lcp_estimate, fid_estimate, cls_estimate)
            }
            
        except Exception as e:
            return {'error': str(e)}

    def rate_lcp(self, lcp_seconds):
        """Calificar Largest Contentful Paint"""
        if lcp_seconds <= 2.5:
            return 'good'
        elif lcp_seconds <= 4.0:
            return 'needs_improvement'
        else:
            return 'poor'

    def rate_fid(self, fid_ms):
        """Calificar First Input Delay"""
        if fid_ms <= 100:
            return 'good'
        elif fid_ms <= 300:
            return 'needs_improvement'
        else:
            return 'poor'

    def rate_cls(self, cls_score):
        """Calificar Cumulative Layout Shift"""
        if cls_score <= 0.1:
            return 'good'
        elif cls_score <= 0.25:
            return 'needs_improvement'
        else:
            return 'poor'

    def get_overall_cwv_rating(self, lcp, fid, cls):
        """Calificación general de Core Web Vitals"""
        ratings = [
            self.rate_lcp(lcp),
            self.rate_fid(fid),
            self.rate_cls(cls)
        ]
        
        if all(rating == 'good' for rating in ratings):
            return 'good'
        elif any(rating == 'poor' for rating in ratings):
            return 'poor'
        else:
            return 'needs_improvement'

    def analyze_page_structure(self, url):
        """Analizar estructura de la página"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Analizar headings
            headings = {}
            for i in range(1, 7):
                headings[f'h{i}'] = len(soup.find_all(f'h{i}'))
            
            # Analizar imágenes
            images = soup.find_all('img')
            images_without_alt = [img for img in images if not img.get('alt')]
            
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
            
            return {
                'headings': headings,
                'total_headings': sum(headings.values()),
                'images': {
                    'total': len(images),
                    'without_alt': len(images_without_alt),
                    'alt_text_ratio': (len(images) - len(images_without_alt)) / len(images) * 100 if images else 0
                },
                'links': {
                    'total': len(links),
                    'internal': len(internal_links),
                    'external': len(external_links),
                    'internal_ratio': len(internal_links) / len(links) * 100 if links else 0
                },
                'word_count': len(soup.get_text().split())
            }
            
        except Exception as e:
            return {'error': str(e)}

    def analyze_resources(self, url):
        """Analizar recursos de la página"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # CSS files
            css_files = soup.find_all('link', rel='stylesheet')
            css_count = len(css_files)
            
            # JavaScript files
            js_files = soup.find_all('script', src=True)
            js_count = len(js_files)
            
            # Images
            images = soup.find_all('img', src=True)
            image_count = len(images)
            
            # Page size estimation
            page_size = len(response.content)
            
            # Resource optimization score
            resource_score = 100
            if css_count > 5:
                resource_score -= 10
            if js_count > 10:
                resource_score -= 15
            if image_count > 20:
                resource_score -= 10
            if page_size > 1000000:  # 1MB
                resource_score -= 20
            
            return {
                'css_files': css_count,
                'javascript_files': js_count,
                'images': image_count,
                'page_size_bytes': page_size,
                'page_size_mb': round(page_size / 1048576, 2),
                'resource_optimization_score': max(resource_score, 0)
            }
            
        except Exception as e:
            return {'error': str(e)}

    def analyze_seo_elements(self, url):
        """Analizar elementos SEO de la página"""
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
            
            # Open Graph tags
            og_tags = {}
            og_elements = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
            for og in og_elements:
                property_name = og.get('property', '').replace('og:', '')
                og_tags[property_name] = og.get('content', '')
            
            # Schema markup
            schema_scripts = soup.find_all('script', type='application/ld+json')
            has_schema = len(schema_scripts) > 0
            
            return {
                'title': {
                    'text': title_text,
                    'length': len(title_text),
                    'exists': bool(title_text),
                    'optimal_length': 30 <= len(title_text) <= 60
                },
                'meta_description': {
                    'text': meta_desc_text,
                    'length': len(meta_desc_text),
                    'exists': bool(meta_desc_text),
                    'optimal_length': 120 <= len(meta_desc_text) <= 160
                },
                'meta_keywords': {
                    'text': meta_keywords_text,
                    'exists': bool(meta_keywords_text)
                },
                'h1_tags': {
                    'count': len(h1_tags),
                    'texts': [h1.get_text().strip() for h1 in h1_tags],
                    'optimal': len(h1_tags) == 1
                },
                'canonical_url': {
                    'url': canonical_url,
                    'exists': bool(canonical_url)
                },
                'open_graph': {
                    'tags': og_tags,
                    'complete': all(key in og_tags for key in ['title', 'description', 'image', 'url'])
                },
                'schema_markup': {
                    'exists': has_schema,
                    'count': len(schema_scripts)
                }
            }
            
        except Exception as e:
            return {'error': str(e)}

    def calculate_performance_score(self, analysis):
        """Calcular puntuación general de rendimiento"""
        score = 0
        max_score = 100
        
        try:
            # Core Web Vitals (40 puntos)
            cwv = analysis.get('core_web_vitals', {})
            if cwv.get('overall_rating') == 'good':
                score += 40
            elif cwv.get('overall_rating') == 'needs_improvement':
                score += 25
            elif cwv.get('overall_rating') == 'poor':
                score += 10
            
            # SEO Elements (30 puntos)
            seo = analysis.get('seo_elements', {})
            if seo.get('title', {}).get('optimal_length'):
                score += 8
            if seo.get('meta_description', {}).get('optimal_length'):
                score += 8
            if seo.get('h1_tags', {}).get('optimal'):
                score += 7
            if seo.get('canonical_url', {}).get('exists'):
                score += 4
            if seo.get('schema_markup', {}).get('exists'):
                score += 3
            
            # Resource Optimization (20 puntos)
            resources = analysis.get('resource_analysis', {})
            resource_score = resources.get('resource_optimization_score', 0)
            score += (resource_score / 100) * 20
            
            # Page Structure (10 puntos)
            structure = analysis.get('page_structure', {})
            if structure.get('images', {}).get('alt_text_ratio', 0) > 80:
                score += 5
            if structure.get('word_count', 0) > 300:
                score += 5
            
            return min(round(score), max_score)
            
        except:
            return 0

    def generate_performance_recommendations(self, analysis):
        """Generar recomendaciones de rendimiento"""
        recommendations = []
        
        try:
            # Core Web Vitals recommendations
            cwv = analysis.get('core_web_vitals', {})
            lcp = cwv.get('largest_contentful_paint', {})
            if lcp.get('rating') in ['needs_improvement', 'poor']:
                recommendations.append({
                    'type': 'core_web_vitals',
                    'priority': 'high',
                    'title': 'Improve Largest Contentful Paint',
                    'description': f'LCP is {lcp.get("value", 0)} seconds. Optimize images and server response time.',
                    'impact': 'high'
                })
            
            # SEO recommendations
            seo = analysis.get('seo_elements', {})
            
            if not seo.get('title', {}).get('exists'):
                recommendations.append({
                    'type': 'seo',
                    'priority': 'high',
                    'title': 'Add Title Tag',
                    'description': 'Page is missing a title tag. Add a descriptive title.',
                    'impact': 'high'
                })
            elif not seo.get('title', {}).get('optimal_length'):
                title_length = seo.get('title', {}).get('length', 0)
                recommendations.append({
                    'type': 'seo',
                    'priority': 'medium',
                    'title': 'Optimize Title Length',
                    'description': f'Title is {title_length} characters. Optimal range is 30-60 characters.',
                    'impact': 'medium'
                })
            
            if not seo.get('meta_description', {}).get('exists'):
                recommendations.append({
                    'type': 'seo',
                    'priority': 'high',
                    'title': 'Add Meta Description',
                    'description': 'Page is missing a meta description. Add a compelling description.',
                    'impact': 'high'
                })
            elif not seo.get('meta_description', {}).get('optimal_length'):
                desc_length = seo.get('meta_description', {}).get('length', 0)
                recommendations.append({
                    'type': 'seo',
                    'priority': 'medium',
                    'title': 'Optimize Meta Description Length',
                    'description': f'Meta description is {desc_length} characters. Optimal range is 120-160 characters.',
                    'impact': 'medium'
                })
            
            if not seo.get('h1_tags', {}).get('optimal'):
                h1_count = seo.get('h1_tags', {}).get('count', 0)
                if h1_count == 0:
                    recommendations.append({
                        'type': 'seo',
                        'priority': 'high',
                        'title': 'Add H1 Tag',
                        'description': 'Page is missing an H1 tag. Add a descriptive heading.',
                        'impact': 'medium'
                    })
                elif h1_count > 1:
                    recommendations.append({
                        'type': 'seo',
                        'priority': 'medium',
                        'title': 'Multiple H1 Tags Found',
                        'description': f'Found {h1_count} H1 tags. Use only one H1 per page.',
                        'impact': 'medium'
                    })
            
            # Resource optimization recommendations
            resources = analysis.get('resource_analysis', {})
            
            if resources.get('css_files', 0) > 5:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'title': 'Reduce CSS Files',
                    'description': f'Found {resources.get("css_files")} CSS files. Consider combining them.',
                    'impact': 'medium'
                })
            
            if resources.get('javascript_files', 0) > 10:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'title': 'Reduce JavaScript Files',
                    'description': f'Found {resources.get("javascript_files")} JS files. Consider combining and minifying.',
                    'impact': 'medium'
                })
            
            if resources.get('page_size_mb', 0) > 2:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'high',
                    'title': 'Reduce Page Size',
                    'description': f'Page size is {resources.get("page_size_mb")} MB. Optimize images and resources.',
                    'impact': 'high'
                })
            
            # Image optimization recommendations
            structure = analysis.get('page_structure', {})
            images = structure.get('images', {})
            
            if images.get('without_alt', 0) > 0:
                recommendations.append({
                    'type': 'accessibility',
                    'priority': 'medium',
                    'title': 'Add Alt Text to Images',
                    'description': f'{images.get("without_alt")} images are missing alt text.',
                    'impact': 'medium'
                })
            
            return recommendations
            
        except Exception as e:
            return [{'type': 'error', 'description': f'Error generating recommendations: {str(e)}'}]