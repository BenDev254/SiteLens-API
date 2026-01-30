def extract_gemini_text(gemini_response: dict | None) -> str:
    """Extracts text from a Gemini response dictionary.

    Args:
        gemini_response (dict | None): The response from the Gemini API.

    Returns:
        str: The extracted text, or an empty string if not found.
    """
    if gemini_response is None:
        return ""

    # Navigate through the nested structure to find the text
    try:
        return gemini_response["candidates"][0]["message"]["content"]["text"]
    except (KeyError, IndexError, TypeError):
        return ""


def classify(text: str) -> dict:
    t = text.lower()

    return {
        "critical": any(k in t for k in [
            "fall", "missing harness", "exposed rebar", "impalement"
        ]),
        "complaint": "recommended" not in t and "unable" not in t,
    }