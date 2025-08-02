# app/utils/language_detector.py
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import spacy
from collections import Counter
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
            },
            'fr': {
                'name': 'Français',
                'spacy_model': 'fr_core_news_sm',
                'google_domain': 'google.fr',
                'stopwords_lang': 'french'
            },
            'de': {
                'name': 'Deutsch',
                'spacy_model': 'de_core_news_sm',
                'google_domain': 'google.de',
                'stopwords_lang': 'german'
            }
        }
    
    def detect_language(self, text):
        """Detectar idioma del texto"""
        try:
            # Limpiar texto
            clean_text = re.sub(r'[^\w\s]', '', text.lower())
            
            if len(clean_text) < 50:
                return 'en'  # Default para textos muy cortos
            
            detected = detect(clean_text)
            
            # Si el idioma detectado está soportado, devolverlo
            if detected in self.supported_languages:
                return detected
            else:
                return 'en'  # Default a inglés
                
        except LangDetectException:
            return 'en'  # Default en caso de error
    
    def get_language_config(self, lang_code):
        """Obtener configuración para un idioma"""
        return self.supported_languages.get(lang_code, self.supported_languages['en'])
    
    def is_supported(self, lang_code):
        """Verificar si el idioma está soportado"""
        return lang_code in self.supported_languages
    
    def get_supported_languages(self):
        """Obtener lista de idiomas soportados"""
        return self.supported_languages