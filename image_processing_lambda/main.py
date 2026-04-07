import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

import boto3
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response

from grok_image_describer import run_pipeline_from_bytes

processor = BatchProcessor(event_type=EventType.SQS)
s3_client = boto3.client("s3")
ddb = boto3.resource("dynamodb")

IMAGE_TABLE_NAME = os.environ.get("IMAGE_STORE_DYNAMODB_TABLE", "image_store")
DESCRIPTION_LOG_PATH = os.environ.get("IMAGE_DESCRIPTION_LOG", "/tmp/image_descriptions.json")
XAI_MODEL = os.environ.get("XAI_MODEL")
XAI_IMAGE_DETAIL = os.environ.get("XAI_IMAGE_DETAIL")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

if DESCRIPTION_LOG_PATH.startswith("./"):
    DESCRIPTION_LOG_PATH = f"/tmp/{Path(DESCRIPTION_LOG_PATH).name}"


def _parse_sqs_body(record: dict[str, Any]) -> dict[str, Any]:
    body = record.get("body", "")
    if isinstance(body, str):
        if not body.strip():
            print("Skipping empty SQS message body")
            return {}
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            print("Skipping non-JSON SQS message body")
            return {}
    else:
        payload = body

    # Support SNS->SQS fanout where the actual event is in Message.
    if isinstance(payload, dict) and isinstance(payload.get("Message"), str):
        try:
            return json.loads(payload["Message"])
        except json.JSONDecodeError:
            pass

    if isinstance(payload, dict):
        return payload
    print("Skipping SQS message body that is not a JSON object")
    return {}


def _extract_s3_entities(payload: dict[str, Any]) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    for item in payload.get("Records", []):
        if item.get("eventSource") != "aws:s3":
            continue
        s3_info = item.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name")
        key = s3_info.get("object", {}).get("key")
        if bucket and key:
            entities.append({"bucket": bucket, "key": unquote_plus(key)})
    return entities


def _read_s3_object_bytes(bucket: str, key: str) -> tuple[bytes, str | None]:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content_type = response.get("ContentType")
    body_stream = response["Body"]
    try:
        payload = body_stream.read()
    finally:
        body_stream.close()
    return payload, content_type


def _save_result_to_ddb(bucket: str, key: str, result: dict[str, Any]) -> None:
    table = ddb.Table(IMAGE_TABLE_NAME)
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(
        Item={
            "PK": f"IMAGE#{bucket}",
            "SK": f"OBJECT#{key}",
            "bucket": bucket,
            "object_key": key,
            "name": Path(key).name,
            "description": result.get("search_text", ""),
            "structured": result.get("structured"),
            "processed_at": now,
        }
    )


def record_handler(record: dict[str, Any]) -> None:
    payload = _parse_sqs_body(record)
    s3_entities = _extract_s3_entities(payload)
    if not s3_entities:
        print("Skipping SQS record with no S3 payload")
        return

    for entity in s3_entities:
        bucket = entity["bucket"]
        key = entity["key"]
        if Path(key).suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"Skipping non-image object: s3://{bucket}/{key}")
            continue
        print(f"Processing s3://{bucket}/{key}")

        image_bytes, content_type = _read_s3_object_bytes(bucket, key)
        describe_result = run_pipeline_from_bytes(
            image_bytes=image_bytes,
            image_name=Path(key).name,
            image_mime_type=content_type,
            image_output=DESCRIPTION_LOG_PATH,
            model=XAI_MODEL,
            detail=XAI_IMAGE_DETAIL,
        )

        # DynamoDB persistence is intentionally disabled until table is ready.
        # _save_result_to_ddb(bucket, key, describe_result)

        print(
            json.dumps(
                {
                    "bucket": bucket,
                    "key": key,
                    "description_preview": describe_result.get("search_text", "")[:120],
                },
                ensure_ascii=False,
            )
        )
    


def lambda_handler(event, context):
    return process_partial_response(
        event=event, record_handler=record_handler, processor=processor, context=context)

