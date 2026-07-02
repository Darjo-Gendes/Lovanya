import json
import re


def extract_json(raw: str) -> dict:
    """Pull a JSON object out of model output, tolerating markdown fences
    and surrounding prose. Falls back to a parse-error record so a bad
    generation never crashes the pipeline."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": raw}
