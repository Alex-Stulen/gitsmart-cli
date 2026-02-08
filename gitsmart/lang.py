import pycountry


def is_valid_language(code):
    """Return True if code is a valid ISO 639-1 language code."""
    if not code or len(code) != 2:
        return False
    return pycountry.languages.get(alpha_2=code.lower()) is not None


def language_name(code):
    """Return human-readable language name for an ISO 639-1 code."""
    lang = pycountry.languages.get(alpha_2=code.lower())
    return lang.name if lang else code
