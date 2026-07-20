# app/utils/pii_masker.py

import re

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# -----------------------------
# Presidio Engines
# -----------------------------
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# -----------------------------
# Custom Regex (API Keys/Secrets)
# -----------------------------
API_KEY_REGEX = r'(?:key|secret|token|password|passwd)(?:[\s"\']*[:=]+[\s"\']*)[a-zA-Z0-9_\-]{8,}'

# -----------------------------
# Custom placeholders
# -----------------------------
operators = {
    "PERSON": OperatorConfig("replace", {"new_value": "John Doe"}),
    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "john@gmail.com"}),
    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "9876543210"}),
    "IP_ADDRESS": OperatorConfig("replace", {"new_value": "0.0.0.0"}),
    "URL": OperatorConfig("replace", {"new_value": "https://example.com"}),
    "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CARD_MASKED]"}),
}


def mask_pii_data(text: str) -> str:
    if not isinstance(text, str):
        return text

    # -----------------------------
    # Step 1: Detect PII using Presidio
    # -----------------------------
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=[
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "IP_ADDRESS",
        "URL",
        "CREDIT_CARD",
    ]
    )

    # -----------------------------
    # Step 2: Replace detected PII
    # -----------------------------
    masked = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators
    )

    text = masked.text

    # -----------------------------
    # Step 3: Mask API Keys using Regex
    # -----------------------------
    text = re.sub(
        API_KEY_REGEX,
        "sk-123456789abcdef",
        text,
        flags=re.IGNORECASE
    )

    return text