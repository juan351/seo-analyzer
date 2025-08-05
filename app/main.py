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
    """Análisis de competidores basado en keywords - RESTAURADO + análisis opcional de términos"""
    try:
        data = request.get_json()
        
        if not validate_request(data, ['keywords', 'my_domain']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        keywords = data['keywords']
        my_domain = data['my_domain']
        top_n = min(data.get('top_competitors', 5), 10)
        
        # Campos opcionales para nueva funcionalidad
        content = data.get('content', '')
        
        logger.info(f"Analyzing competitors for keywords: {keywords}")
        
        # TU ANÁLISIS ORIGINAL QUE FUNCIONA (sin cambiar nada)
        analysis = content_analyzer.analyze_competitors(keywords, my_domain, top_n)
        
        # NUEVO: Si se proporciona contenido, agregar análisis de términos
        if content and len(content) > 100:
            logger.info("Adding term frequency analysis")
            try:
                # Usar los competidores reales que ya encontraste
                term_analysis = content_analyzer.analyze_competitors_with_terms(
                    keywords, my_domain, content, top_n
                )
                
                # Agregar solo si fue exitoso
                if term_analysis and 'term_frequency_analysis' in term_analysis:
                    analysis['term_frequency_analysis'] = term_analysis['term_frequency_analysis']
                    logger.info("Term frequency analysis added successfully")
                
            except Exception as e:
                logger.info(f"Term analysis failed (non-critical): {e}")
                # Continuar sin análisis de términos
        
        logger.info(f"Competitor analysis complete: {analysis}")
        
        # RESPUESTA ORIGINAL (sin cambiar formato)
        return jsonify({
            'success': True,
            'data': analysis,  # Tu estructura original
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