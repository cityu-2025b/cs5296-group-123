import json
import os

import requests


DEFAULT_XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_XAI_MODEL = "grok-4-1-fast-non-reasoning"
DEFAULT_IMAGE_DETAIL = "high"
DEFAULT_TIMEOUT_SECONDS = 30.0

SYSTEM_PROMPT = (
    "You are an automotive vision labeling assistant. "
    "Generate descriptions optimized for semantic/vector search. "
    "Be factual, avoid guessing beyond visible evidence, and provide concise normalized attributes."
)

USER_PROMPT = (
    "Analyze this image and return JSON only. No markdown, no extra text. "
    "Use this schema exactly: {\"description\": string}. "
    "The description should include visible vehicle identity (if clear), body style, color, setting, camera view, and notable visual cues "
    "in one compact retrieval-oriented sentence."
)


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _safe_parse_description(text: str) -> str | None:
    try:
        payload = json.loads(_extract_json_object(text))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        description = payload.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()
    return None


def _to_data_url(image_base64_or_data_url: str) -> str:
    if image_base64_or_data_url.startswith("data:image"):
        return image_base64_or_data_url
    return f"data:image/jpeg;base64,{image_base64_or_data_url}"


def image_to_description(image: str) -> dict[str, str]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing XAI_API_KEY")

    base_url = os.environ.get("XAI_BASE_URL", DEFAULT_XAI_BASE_URL).rstrip("/")
    model = os.environ.get("XAI_MODEL", DEFAULT_XAI_MODEL)
    detail = os.environ.get("XAI_IMAGE_DETAIL", DEFAULT_IMAGE_DETAIL)
    timeout = float(os.environ.get("XAI_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _to_data_url(image),
                            "detail": detail,
                        },
                    },
                ],
            },
        ],
    }

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    body = response.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = _safe_parse_description(content)
    description = parsed or content.strip()
    if not description:
        raise RuntimeError("xAI response did not include description text")

    return {"description": description}