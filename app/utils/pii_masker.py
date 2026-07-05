# app/utils/pii_masker.py
import re

# Common PII Patterns
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
PHONE_REGEX = r'\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b'
API_KEY_REGEX = r'(?:key|secret|token|password|passwd)(?:[\s|""|'']*[:|=]+[\s|""|'']*)[a-zA-Z0-9_\-]{8,}'

def mask_pii_data(text: str) -> str:
    if not isinstance(text, str):
        return text
        
    # Masking Email
    text = re.sub(EMAIL_REGEX, "[EMAIL_MASKED]", text)
    
    # Masking Phone Numbers
    text = re.sub(PHONE_REGEX, "[PHONE_MASKED]", text)
    
    return text