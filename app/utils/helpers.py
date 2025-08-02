from flask import jsonify
import re
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def validate_request(data, required_fields):
    """Validate that request contains required fields"""
    if not data:
        return False
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    
    return True

def handle_error(error):
    """Handle and format errors consistently"""
    logger.error(f"API Error: {str(error)}")
    
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'Something went wrong processing your request'
    }), 500

def validate_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def validate_domain(domain):
    """Validate domain format"""
    domain_pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    return bool(domain_pattern.match(domain))

def sanitize_keyword(keyword):
    """Sanitize keyword input"""
    if not keyword:
        return ''
    
    # Remove extra whitespace and convert to lowercase
    keyword = re.sub(r'\s+', ' ', keyword.strip().lower())
    
    # Remove special characters except basic punctuation
    keyword = re.sub(r'[^\w\s\-\.]', '', keyword)
    
    return keyword

def format_number(number):
    """Format numbers for display"""
    if number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    else:
        return str(number)

def calculate_percentage_change(old_value, new_value):
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0 if new_value == 0 else 100
    
    return round(((new_value - old_value) / old_value) * 100, 2)

def extract_domain_from_url(url):
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url

def rate_limit_key(identifier, endpoint):
    """Generate rate limit key"""
    return f"rate_limit:{identifier}:{endpoint}"

def success_response(data, message="Success"):
    """Format success response"""
    return jsonify({
        'success': True,
        'message': message,
        'data': data,
        'timestamp': str(datetime.now().isoformat())
    })

def error_response(message, status_code=400):
    """Format error response"""
    return jsonify({
        'success': False,
        'error': message,
        'timestamp': str(datetime.now().isoformat())
    }), status_code