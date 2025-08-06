from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

from .services.backlink_analyzer import BacklinkAnalyzer
from .services.performance_analyzer import PerformanceAnalyzer
from .utils.cache import CacheManager
from .utils.helpers import validate_request, handle_error
from functools import wraps
from .services.content_analyzer import MultilingualContentAnalyzer
from .services.serp_scraper import MultilingualSerpScraper
from .utils.language_detector import LanguageDetector
load_dotenv()



def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY') or request.args.get('api_key')
        if not api_key or api_key != API_KEY:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
API_KEY = os.getenv('API_KEY', 'your-api-key')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar servicios
cache_manager = CacheManager()
backlink_analyzer = BacklinkAnalyzer(cache_manager)
performance_analyzer = PerformanceAnalyzer()

# Inicializar servicios multiidioma
language_detector = LanguageDetector()
serp_scraper = MultilingualSerpScraper(cache_manager)
content_analyzer = MultilingualContentAnalyzer(cache_manager)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/content/analyze', methods=['POST'])
@limiter.limit("20 per minute")
@require_api_key
def analyze_content():
    """Análisis completo de contenido multiidioma"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['content', 'target_keywords']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        content = data['content']
        target_keywords = data['target_keywords']
        competitor_contents = data.get('competitor_contents', [])
        language = data.get('language')  # Opcional, se detecta automáticamente
        
        logger.info(f"Starting multilingual content analysis. Language: {language}")
        
        analysis = content_analyzer.comprehensive_analysis(
            content, target_keywords, competitor_contents, language
        )
        
        return jsonify({
            'success': True,
            'data': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in multilingual content analysis: {str(e)}")
        return handle_error(e)

@app.route('/serp/search', methods=['POST'])
@limiter.limit("10 per minute")
@require_api_key
def search_serp():
    """Obtener resultados SERP multiidioma"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['keywords']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        keywords = data['keywords']
        location = data.get('location', 'US')
        language = data.get('language')  # Opcional
        pages = min(data.get('pages', 1), 3)
        
        results = {}
        for keyword in keywords:
            logger.info(f"Scraping SERP for keyword: {keyword}, language: {language}")
            serp_data = serp_scraper.get_serp_results(keyword, location, language, pages)
            results[keyword] = serp_data
        
        return jsonify({
            'success': True,
            'data': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in multilingual SERP search: {str(e)}")
        return handle_error(e)

@app.route('/languages/supported', methods=['GET'])
def get_supported_languages():
    """Obtener idiomas soportados"""
    try:
        languages = language_detector.get_supported_languages()
        return jsonify({
            'success': True,
            'data': {
                'supported_languages': languages,
                'total_languages': len(languages)
            }
        })
    except Exception as e:
        return handle_error(e)

@app.route('/languages/detect', methods=['POST'])
@require_api_key
def detect_language():
    """Detectar idioma de un texto"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['text']):
            return jsonify({'error': 'Missing text field'}), 400
        
        text = data['text']
        detected_lang = language_detector.detect_language(text)
        lang_config = language_detector.get_language_config(detected_lang)
        
        return jsonify({
            'success': True,
            'data': {
                'detected_language': detected_lang,
                'language_name': lang_config['name'],
                'confidence': 'high' if len(text) > 100 else 'medium',
                'is_supported': language_detector.is_supported(detected_lang)
            }
        })
        
    except Exception as e:
        return handle_error(e)

@app.route('/backlinks/analyze', methods=['POST'])
@limiter.limit("5 per minute")
@require_api_key
def analyze_backlinks():
    """Análisis de backlinks y autoridad de dominio"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['domain']):
            return jsonify({'error': 'Missing domain field'}), 400
        
        domain = data['domain']
        logger.info(f"Analyzing backlinks for domain: {domain}")
        
        analysis = backlink_analyzer.analyze_domain(domain)
        
        return jsonify({
            'success': True,
            'data': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in backlink analysis: {str(e)}")
        return handle_error(e)

@app.route('/performance/analyze', methods=['POST'])
@limiter.limit("10 per minute")
@require_api_key
def analyze_performance():
    """Análisis de rendimiento web"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['url']):
            return jsonify({'error': 'Missing URL field'}), 400
        
        url = data['url']
        logger.info(f"Analyzing performance for URL: {url}")
        
        analysis = performance_analyzer.analyze_url(url)
        
        return jsonify({
            'success': True,
            'data': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in performance analysis: {str(e)}")
        return handle_error(e)

@app.route('/keywords/suggestions', methods=['POST'])
@limiter.limit("15 per minute")
@require_api_key
def keyword_suggestions():
    """Sugerencias de keywords relacionadas"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['seed_keyword']):
            return jsonify({'error': 'Missing seed_keyword field'}), 400
        
        seed_keyword = data['seed_keyword']
        country = data.get('country', 'US')
        
        logger.info(f"Getting keyword suggestions for: {seed_keyword}")
        
        suggestions = serp_scraper.get_keyword_suggestions(seed_keyword, country)
        
        return jsonify({
            'success': True,
            'data': suggestions,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting keyword suggestions: {str(e)}")
        return handle_error(e)

@app.route('/competitors/analyze', methods=['POST'])
@limiter.limit("3 per minute")  
@require_api_key
def analyze_competitors():
    """Endpoint con mapping correcto para WordPress"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['keywords', 'my_domain']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        keywords = data['keywords']
        my_domain = data['my_domain'] 
        content = data.get('content', '')
        
        logger.info(f"Análisis para: {keywords}")
        
        # Obtener análisis completo
        if content and len(content) > 100:
            analysis = content_analyzer.analyze_competitors_with_terms(keywords, my_domain, content)
        else:
            analysis = content_analyzer.analyze_competitors(keywords, my_domain)
        
        if analysis.get('error'):
            return jsonify({'error': analysis['error']}), 500
        
        # MAPEAR CORRECTAMENTE los datos para WordPress
        term_analysis = analysis.get('term_frequency_analysis', {})
        content_analysis = term_analysis.get('content_analysis', {})
        
        # Construir lista de competidores para WordPress
        wp_competitors = []
        unique_competitors = analysis.get('unique_competitors', [])
        
        for comp in unique_competitors:
            wp_competitors.append({
                'domain': comp['domain'],
                'url': comp['urls'][0] if comp.get('urls') else '',
                'title': comp['titles'][0] if comp.get('titles') else comp['domain'],
                'position': comp.get('avg_position', 0),
                'word_count': 1000,  # Estimación
                'content_score': 85,  # Estimación
                'keyword_density': 1.2  # Estimación
            })
        
        # Calcular densidades reales si hay análisis de términos
        your_density = 0
        average_density = 1.5
        
        if term_analysis.get('keywords'):
            keyword_data = term_analysis['keywords'][0]  # Primera keyword
            if content_analysis.get('my_word_count', 0) > 0:
                your_density = round((keyword_data['current_count'] / content_analysis['my_word_count']) * 100, 2)
                average_density = round((keyword_data['competitor_average'] / content_analysis.get('competitor_avg_words', 1000)) * 100, 2)
        
        # Generar sugerencias para WordPress
        wp_suggestions = []
        
        if term_analysis.get('keywords'):
            for term_data in term_analysis['keywords']:
                current = term_data['current_count']
                recommended = term_data['recommended_count']
                
                if current < recommended:
                    wp_suggestions.append({
                        'title': f'Aumentar uso de "{term_data["term"]}"',
                        'message': f'Usar "{term_data["term"]}" {recommended - current} veces más. Actual: {current}, Óptimo: {recommended}',
                        'priority': term_data['priority'],
                        'icon': '🎯',
                        'type': 'keyword_optimization'
                    })
                elif current > recommended * 1.5:
                    wp_suggestions.append({
                        'title': f'Reducir "{term_data["term"]}"',
                        'message': f'Demasiadas repeticiones ({current}). Reducir a ~{recommended}',
                        'priority': 'medium',
                        'icon': '⚠️',
                        'type': 'keyword_optimization'
                    })
        
        # Análisis del contenido
        my_word_count = content_analysis.get('my_word_count', len(content.split()) if content else 0)
        competitor_avg_words = content_analysis.get('competitor_avg_words', 1200)
        
        if my_word_count > 0 and competitor_avg_words > 0:
            if my_word_count < competitor_avg_words * 0.7:
                wp_suggestions.append({
                    'title': 'Expandir contenido',
                    'message': f'Tu contenido ({my_word_count} palabras) es más corto que competidores ({competitor_avg_words} promedio)',
                    'priority': 'high',
                    'icon': '📝',
                    'type': 'content_length'
                })
        
        # Respuesta formateada para WordPress
        response_data = {
            'competitors': wp_competitors,
            'total_competitors': len(wp_competitors),
            'average_word_count': competitor_avg_words,
            'your_word_count': my_word_count,
            
            'keyword_analysis': {
                'your_density': your_density,
                'average_density': average_density,
                'recommended_density': {
                    'min': 0.5,
                    'max': 2.5
                }
            },
            
            'content_structure': {
                'your_headings': content.count('#') + content.count('<h') if content else 0,
                'average_headings': 6,  # Estimación basada en competidores
                'your_paragraphs': len([p for p in content.split('\n\n') if p.strip()]) if content else 0,
                'average_paragraphs': max(8, int(competitor_avg_words / 150))  # Estimación
            },
            
            'suggestions': wp_suggestions,
            'missing_keywords': [],
            'top_keywords': keywords,
            
            # DATOS NUEVOS: Análisis de términos para WordPress
            'term_frequency_analysis': {
                'enabled': True,
                'keywords_analyzed': len(term_analysis.get('keywords', [])),
                'competitors_analyzed': content_analysis.get('competitors_analyzed', 0),
                'keyword_recommendations': term_analysis.get('keywords', []),
                'content_gap': {
                    'word_difference': my_word_count - competitor_avg_words,
                    'status': 'longer' if my_word_count > competitor_avg_words else 'shorter',
                    'recommendation': 'optimal' if abs(my_word_count - competitor_avg_words) < 200 else 'needs_adjustment'
                }
            },
            
            'analysis_summary': {
                'analyzed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'api_used': True,
                'cache_duration': 3600,
                'competitors_found': len(wp_competitors),
                'analysis_type': 'term_frequency' if term_analysis else 'basic'
            }
        }
        
        logger.info(f"✅ Respuesta formateada: {len(wp_competitors)} competidores, {len(wp_suggestions)} sugerencias")
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': str(e.description)
    }), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end'
    }), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=3000)