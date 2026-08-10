import re

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider


# -----------------------------
# spaCy Configuration
# -----------------------------

configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {
            "lang_code": "en",
            "model_name": "en_core_web_sm"
        }
    ],
}

provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(
    nlp_engine=nlp_engine,
    supported_languages=["en"]
)

anonymizer = AnonymizerEngine()


# -----------------------------
# Custom Regex
# -----------------------------

API_KEY_REGEX = r'(?i:key|secret|token|password|passwd)(?:[\s"\']*[:=]+[\s"\']*)[a-zA-Z0-9_-]{8,}'


# -----------------------------
# Custom placeholders
# -----------------------------

operators = {
    "PERSON": OperatorConfig("replace", {"new_value": "John Doe"}),
    "EMAIL_ADDRESS": OperatorConfig(
        "replace",
        {"new_value": "john@gmail.com"}
    ),
    "PHONE_NUMBER": OperatorConfig(
        "replace",
        {"new_value": "9876543210"}
    ),
    "IP_ADDRESS": OperatorConfig(
        "replace",
        {"new_value": "0.0.0.0"}
    ),
    "URL": OperatorConfig(
        "replace",
        {"new_value": "https://example.com"}
    ),
    "CREDIT_CARD": OperatorConfig(
        "replace",
        {"new_value": "[CARD_MASKED]"}
    ),
}


def mask_pii_data(text: str) -> str:
    if not isinstance(text, str):
        return text

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
        ],
    )

    masked = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    text = masked.text

    text = re.sub(
        API_KEY_REGEX,
        "sk-123456789abcdef",
        text,
        flags=re.IGNORECASE,
    )

    return text