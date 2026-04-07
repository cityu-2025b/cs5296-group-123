import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_MODEL = "grok-4-1-fast-non-reasoning"
DEFAULT_IMAGE_OUTPUT = "./image_descriptions.json"
DEFAULT_DETAIL = "high"
VALID_DETAILS = {"auto", "low", "high"}

SYSTEM_PROMPT = (
    "You are an automotive vision labeling assistant. "
    "Generate descriptions optimized for semantic/vector search. "
    "Be factual, avoid guessing beyond visible evidence, and provide concise normalized attributes."
)

USER_PROMPT = (
    "Analyze this image and return JSON only. No markdown, no extra text. "
    "Use this schema exactly:\n"
    "{\n"
    "  \"long_description\": string,\n"
    "  \"short_caption\": string,\n"
    "  \"vehicle\": {\n"
    "    \"make\": string,\n"
    "    \"model_guess\": string,\n"
    "    \"body_style\": string,\n"
    "    \"color\": string\n"
    "  },\n"
    "  \"scene\": {\n"
    "    \"environment\": string,\n"
    "    \"lighting\": string,\n"
    "    \"camera_view\": string,\n"
    "    \"motion\": string\n"
    "  },\n"
    "  \"visual_attributes\": [string],\n"
    "  \"query_phrases\": [string]\n"
    "}\n"
    "Rules: query_phrases should contain natural user-like search queries such as color + body style + view + scene."
)


def load_env_file(env_path: Path = Path(".env")) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Describe one image with Grok (xAI) and optionally append output to JSON log."
    )
    parser.add_argument("--image", required=True, help="Image filename or path.")
    parser.add_argument(
        "--image-output",
        "--output-json",
        dest="image_output",
        default=DEFAULT_IMAGE_OUTPUT,
        help="Path to JSON log output file.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="xAI model name to use for image description.",
    )
    parser.add_argument(
        "--detail",
        choices=["auto", "low", "high"],
        default=None,
        help="Vision detail level for image parsing.",
    )
    return parser.parse_args()


def get_api_key() -> str:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API key. Set XAI_API_KEY in your environment.")
    return api_key


def get_api_host() -> str:
    api_host = os.environ.get("XAI_API_HOST")
    if api_host:
        return api_host

    base_url = os.environ.get("XAI_BASE_URL", "").strip()
    if not base_url:
        return "api.x.ai"

    if "://" not in base_url:
        return base_url

    parsed = urlparse(base_url)
    return parsed.netloc or "api.x.ai"


def get_api_base_url() -> str:
    base_url = os.environ.get("XAI_BASE_URL", "").strip()
    if base_url:
        return base_url.rstrip("/")
    return f"https://{get_api_host()}/v1"


def get_timeout_seconds() -> float:
    raw = os.environ.get("XAI_TIMEOUT", "3600").strip()
    try:
        return float(raw)
    except ValueError:
        return 3600.0


def resolve_image_path(image: str | Path) -> Path:
    image_path = Path(image).resolve()
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {image_path.suffix}")
    return image_path


def to_data_url(image_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    mime_type = mime_type or "image/jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def to_data_url_from_bytes(image_bytes: bytes, image_name: str, mime_type: str | None = None) -> str:
    guessed_mime, _ = mimetypes.guess_type(image_name)
    resolved_mime = mime_type or guessed_mime or "image/jpeg"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{resolved_mime};base64,{encoded}"


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _safe_parse_json(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(_extract_json_object(text))
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        return None
    return None


def _clean_structured(structured: dict[str, Any] | None) -> dict[str, Any] | None:
    if not structured:
        return None
    cleaned = dict(structured)
    cleaned.pop("confidence", None)
    return cleaned


def _build_search_text(structured: dict[str, Any], fallback_desc: str) -> str:
    if not structured:
        return fallback_desc

    vehicle = structured.get("vehicle", {}) if isinstance(structured.get("vehicle"), dict) else {}
    scene = structured.get("scene", {}) if isinstance(structured.get("scene"), dict) else {}
    attrs = structured.get("visual_attributes", [])
    queries = structured.get("query_phrases", [])

    parts: list[str] = []
    for value in [
        structured.get("short_caption"),
        structured.get("long_description"),
        vehicle.get("make"),
        vehicle.get("model_guess"),
        vehicle.get("body_style"),
        vehicle.get("color"),
        scene.get("environment"),
        scene.get("lighting"),
        scene.get("camera_view"),
        scene.get("motion"),
    ]:
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

    if isinstance(attrs, list):
        parts.extend(str(x).strip() for x in attrs if str(x).strip())
    if isinstance(queries, list):
        parts.extend(str(x).strip() for x in queries if str(x).strip())

    return " | ".join(parts) if parts else fallback_desc


def describe_image(model: str, image_path: Path, detail: str) -> dict[str, Any]:
    data_url = to_data_url(image_path)

    return _describe_from_data_url(model, data_url, detail)


def _describe_from_data_url(model: str, data_url: str, detail: str) -> dict[str, Any]:
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
                            "url": data_url,
                            "detail": detail,
                        },
                    },
                ],
            },
        ],
    }

    response = requests.post(
        f"{get_api_base_url()}/chat/completions",
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=get_timeout_seconds(),
    )
    response.raise_for_status()

    body = response.json()
    raw_desc = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not raw_desc:
        raw_desc = json.dumps(body, ensure_ascii=False)

    structured = _clean_structured(_safe_parse_json(raw_desc))
    search_text = _build_search_text(structured or {}, raw_desc)

    return {
        "search_text": search_text,
        "structured": structured,
    }


def _append_description_log(output_json: Path, image_name: str, result: dict[str, Any]) -> None:
    records = load_existing_json(output_json)
    records[image_name] = {
        "search_text": result["search_text"],
        "structured": result["structured"],
    }
    try:
        save_json(output_json, records)
        print(f"Saved description log for: {image_name}")
    except OSError as exc:
        print(f"Warning: failed to write image description log: {exc}")



def run_pipeline(
    *,
    image: str | Path,
    image_output: str | Path | None = None,
    model: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    load_env_file()

    output_json_raw = (
        str(image_output) if image_output is not None else os.environ.get("IMAGE_OUTPUT", DEFAULT_IMAGE_OUTPUT)
    )
    model_name = model or os.environ.get("XAI_MODEL") or DEFAULT_MODEL
    detail_level = (detail or os.environ.get("XAI_IMAGE_DETAIL") or DEFAULT_DETAIL).lower().strip()
    if detail_level not in VALID_DETAILS:
        detail_level = DEFAULT_DETAIL

    image_path = resolve_image_path(image)
    output_json = Path(output_json_raw).resolve()

    get_api_key()
    print(f"Processing: {image_path.name}")
    result = describe_image(model_name, image_path, detail_level)
    _append_description_log(output_json, image_path.name, result)

    return {
        "image": image_path.name,
        "search_text": result["search_text"],
        "structured": result["structured"],
        "output_json": str(output_json),
    }


def run_pipeline_from_bytes(
    *,
    image_bytes: bytes,
    image_name: str,
    image_mime_type: str | None = None,
    image_output: str | Path | None = None,
    model: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    load_env_file()

    output_json_raw = (
        str(image_output) if image_output is not None else os.environ.get("IMAGE_OUTPUT", DEFAULT_IMAGE_OUTPUT)
    )
    model_name = model or os.environ.get("XAI_MODEL") or DEFAULT_MODEL
    detail_level = (detail or os.environ.get("XAI_IMAGE_DETAIL") or DEFAULT_DETAIL).lower().strip()
    if detail_level not in VALID_DETAILS:
        detail_level = DEFAULT_DETAIL

    output_json = Path(output_json_raw).resolve()
    data_url = to_data_url_from_bytes(image_bytes, image_name, image_mime_type)

    get_api_key()
    print(f"Processing: {image_name}")
    result = _describe_from_data_url(model_name, data_url, detail_level)
    _append_description_log(output_json, image_name, result)

    return {
        "image": image_name,
        "search_text": result["search_text"],
        "structured": result["structured"],
        "output_json": str(output_json),
    }


def load_existing_json(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def save_json(path: Path, data: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        image=args.image,
        image_output=args.image_output,
        model=args.model,
        detail=args.detail,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
