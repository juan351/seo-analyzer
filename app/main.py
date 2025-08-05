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
    """Análisis de competidores basado en keywords con análisis de términos opcional"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['keywords']):
            return jsonify({'error': 'Missing required field: keywords'}), 400
        
        keywords = data['keywords']
        my_domain = data.get('my_domain', '')
        content = data.get('content', '')  # NUEVO: contenido opcional
        title = data.get('title', '')      # NUEVO: título opcional
        top_n = min(data.get('top_competitors', 5), 10)
        language = data.get('language')
        
        logger.info(f"Analyzing competitors for keywords: {keywords}")
        
        # Análisis básico de competidores (tu funcionalidad existente)
        competitor_analysis = content_analyzer.analyze_competitors(keywords, my_domain, top_n)
        
        # NUEVO: Si se proporciona contenido, hacer análisis de términos
        term_analysis = None
        if content:
            logger.info("Content provided, performing term frequency analysis")
            term_analysis = content_analyzer.analyze_term_frequency_competitors(
                content=content,
                target_keywords=keywords,
                language=language
            )
        
        # Formatear respuesta
        response_data = {
            'competitors': competitor_analysis.get('unique_competitors', []),
            'total_competitors': competitor_analysis.get('total_competitors_found', 0),
            'average_word_count': 1200,  # Valor por defecto
            'your_word_count': len(content.split()) if content else 0,
            
            'keyword_analysis': {
                'your_density': 0.14,  # Se puede calcular si hay contenido
                'average_density': 1.5,
                'recommended_density': {'min': 0.5, 'max': 2.5}
            },
            
            'content_structure': {
                'your_headings': content.count('#') + content.count('<h') if content else 0,
                'average_headings': 4,
                'your_paragraphs': content.count('\n\n') + content.count('<p>') if content else 0,
                'average_paragraphs': 10
            },
            
            'suggestions': [],
            
            'missing_keywords': [],
            'top_keywords': [],
            
            'analysis_summary': {
                'analyzed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'api_used': True,
                'cache_duration': 3600,
                'api_summary': {
                    'avg_competitors_per_keyword': competitor_analysis.get('total_competitors_found', 0) / max(len(keywords), 1),
                    'most_common_competitors': competitor_analysis.get('analysis_summary', {}).get('most_common_competitors', [])
                }
            }
        }
        
        # NUEVO: Agregar análisis de términos si está disponible
        if term_analysis:
            response_data['term_frequency_analysis'] = term_analysis['term_frequency_analysis']
            
            # Generar sugerencias basadas en términos
            term_suggestions = []
            for term_data in term_analysis['term_frequency_analysis']['keywords']:
                current = term_data['current_count']
                optimal = term_data['recommended_count']['optimal']
                min_count = term_data['recommended_count']['min']
                
                if current < min_count:
                    term_suggestions.append({
                        'title': f'Optimizar "{term_data["term"]}"',
                        'message': f'Usar "{term_data["term"]}" {optimal - current} veces más. Actual: {current}, Recomendado: {optimal}',
                        'priority': 'high',
                        'icon': '🎯',
                        'action': 'optimize_keywords',
                        'term': term_data['term'],
                        'current_count': current,
                        'target_count': optimal
                    })
                elif current > term_data['recommended_count']['max']:
                    term_suggestions.append({
                        'title': f'Reducir "{term_data["term"]}"',
                        'message': f'"{term_data["term"]}" aparece demasiado ({current} veces). Reducir a ~{optimal}',
                        'priority': 'medium',
                        'icon': '⚠️',
                        'action': 'reduce_keywords',
                        'term': term_data['term'],
                        'current_count': current,
                        'target_count': optimal
                    })
            
            # Agregar sugerencias de términos semánticos
            for term_data in term_analysis['term_frequency_analysis']['semantic_terms'][:3]:
                if term_data['current_count'] == 0 and term_data['priority'] == 'high':
                    term_suggestions.append({
                        'title': f'Incluir "{term_data["term"]}"',
                        'message': f'Agregar término relacionado "{term_data["term"]}" usado por competidores.',
                        'priority': 'medium',
                        'icon': '💡',
                        'action': 'add_semantic_term',
                        'term': term_data['term'],
                        'current_count': 0,
                        'target_count': term_data['recommended_count']['optimal']
                    })
            
            response_data['suggestions'] = term_suggestions
            
            # Actualizar métricas con datos reales
            if term_analysis['term_frequency_analysis']['content_analysis']['competitor_avg_words'] > 0:
                response_data['average_word_count'] = int(term_analysis['term_frequency_analysis']['content_analysis']['competitor_avg_words'])
        
        logger.info(f"Competitor analysis complete with {len(response_data.get('suggestions', []))} suggestions")
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in competitor analysis: {str(e)}")
        return handle_error(e)

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