# app/utils/language_detector.py (versión simplificada)
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import spacy
import re

# Seed fijo para resultados consistentes
DetectorFactory.seed = 0

class LanguageDetector:
    def __init__(self):
        self.supported_languages = {
            'en': {
                'name': 'English',
                'spacy_model': 'en_core_web_sm',
                'google_domain': 'google.com',
                'stopwords_lang': 'english'
            },
            'es': {
                'name': 'Español',
                'spacy_model': 'es_core_news_sm',
                'google_domain': 'google.es',
                'stopwords_lang': 'spanish'
            }
        }
    
    def detect_language(self, text):
        """Detectar idioma del texto usando langdetect simple"""
        try:
            # Limpiar texto
            clean_text = re.sub(r'[^\w\s]', '', text.lower())
            
            if len(clean_text) < 30:
                return 'en'  # Default para textos muy cortos
            
            # Detectar idioma
            detected = detect(clean_text)
            
            # Mapear detecciones comunes a nuestros idiomas soportados
            language_mapping = {
                'en': 'en',
                'es': 'es',
                'ca': 'es',  # Catalán -> Español
                'gl': 'es',  # Gallego -> Español
                'pt': 'es',  # Portugués -> Español (similar)
                'fr': 'en',  # Francés -> Inglés (por simplicidad)
                'de': 'en',  # Alemán -> Inglés (por simplicidad)
                'it': 'en',  # Italiano -> Inglés (por simplicidad)
            }
            
            return language_mapping.get(detected, 'en')
                
        except (LangDetectException, Exception):
            # Método de detección alternativo por patrones
            return self.detect_by_patterns(text)
    
    def detect_by_patterns(self, text):
        """Detección alternativa por patrones de texto"""
        text_lower = text.lower()
        
        # Patrones españoles
        spanish_patterns = [
            r'\b(el|la|los|las|un|una|de|en|con|por|para|que|se|es|son|está|están)\b',
            r'[áéíóúüñ]',
            r'\b(español|españa|seo|posicionamiento|optimización)\b'
        ]
        
        spanish_score = 0
        for pattern in spanish_patterns:
            matches = len(re.findall(pattern, text_lower))
            spanish_score += matches
        
        # Si hay suficientes patrones españoles, es español
        if spanish_score > len(text.split()) * 0.1:
            return 'es'
        
        return 'en'  # Default inglés
    
    def get_language_config(self, lang_code):
        """Obtener configuración para un idioma"""
        return self.supported_languages.get(lang_code, self.supported_languages['en'])
    
    def is_supported(self, lang_code):
        """Verificar si el idioma está soportado"""
        return lang_code in self.supported_languages
    
    def get_supported_languages(self):
        """Obtener lista de idiomas soportados"""
        return self.supported_languages