import json
import base64
from decimal import Decimal

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Any
from service import opensearch_service, grok_service, s3_service, dynamodb_service

app = APIGatewayRestResolver()

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,x-api-key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _json_response(status_code: int, payload: Any) -> Response:
    def _json_default(value: Any) -> Any:
        if isinstance(value, Decimal):
            return int(value) if value == value.to_integral_value() else float(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    return Response(
        status_code=status_code,
        body=json.dumps(payload, ensure_ascii=False, default=_json_default),
        content_type="application/json",
        headers=_CORS_HEADERS,
    )


def _format_search_hits(raw_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted_hits: list[dict[str, Any]] = []

    for hit in raw_hits:
        source = dict(hit.get("_source") or {})
        source.pop("description_embedding", None)

        if "image_base64" not in source:
            bucket = source.get("s3_bucket_name") or source.get("bucket")
            key = source.get("s3_file_path") or source.get("key")

            if bucket and key:
                try:
                    image_bytes = get_s3_image(bucket, key)
                    source["image_base64"] = base64.b64encode(image_bytes).decode("ascii")
                except Exception:
                    source["image_base64"] = None
            else:
                source["image_base64"] = None

        formatted_hits.append(
            {
                "_index": hit.get("_index"),
                "_id": hit.get("_id"),
                "_score": hit.get("_score"),
                "_source": source,
            }
        )

    return formatted_hits


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


@app.route("/text-search", method="OPTIONS")
def options_text_search() -> Any:
    return _json_response(200, {"ok": True})


@app.route("/search-image", method="OPTIONS")
def options_search_image() -> Any:
    return _json_response(200, {"ok": True})


@app.post("/search-image")
def search_image() -> Any:
    # 1. Parse base64 image from request
    # 2. Call llm to convert image to text
    # 3. Convert text to vector
    # 4. Search vector database for similar images
    # 5. Return results

    event = app.current_event.json_body or {}
    base64_image = event.get("image")

    if not base64_image:
        return _json_response(400, {"message": "Image is required"})

    try:
        grok_response = grok_service.image_to_description(base64_image)
        description = grok_response.get("description", "")
        opensearch_response = opensearch_service.search_image_by_description(description)
        return _json_response(200, _format_search_hits(opensearch_response))
    except Exception as exc:
        return _json_response(500, {"message": "search-image failed", "error": str(exc)})


@app.get("/text-search")
def text_search(size: int = 10) -> Any:
    # 1. Parse query parameter from request
    # 2. Convert text to vector
    # 3. Search vector database for similar images
    # 4. Return results
    event = app.current_event.query_string_parameters or {}
    input_text = event.get("inputText")
    use_ddb_description_search = _parse_bool(event.get("useDdbDescriptionSearch"), default=False)

    size_raw = event.get("size")
    if size_raw is not None:
        try:
            size = int(size_raw)
        except (TypeError, ValueError):
            return _json_response(400, {"message": "size must be an integer"})

    if size <= 0:
        return _json_response(400, {"message": "size must be greater than 0"})

    if not input_text:
        return _json_response(400, {"message": "inputText is required"})

    try:
        if use_ddb_description_search:
            ddb_response = dynamodb_service.search_image_by_description(input_text, size=size)
            return _json_response(200, _format_search_hits(ddb_response))

        # When AOS_MODEL_ID is configured, this performs neural search.
        # Otherwise it falls back to keyword match search.
        opensearch_response = opensearch_service.search_image_by_description(input_text, size=size)
        return _json_response(200, _format_search_hits(opensearch_response))
    except Exception as exc:
        return _json_response(500, {"message": "text-search failed", "error": str(exc)})

def get_s3_image(bucket: str, key: str) -> bytes:
    s3_response = s3_service.get_s3_object(bucket, key)
    return s3_response

def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
