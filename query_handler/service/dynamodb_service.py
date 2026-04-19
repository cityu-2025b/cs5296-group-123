import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr

DDB_TABLE_NAME = os.environ.get("DDB_TABLE") or os.environ.get("IMAGE_STORE_DYNAMODB_TABLE", "image_store")
DDB_PK_NAME = os.environ.get("IMAGE_STORE_DYNAMODB_PK_NAME", "pk")
DDB_SK_NAME = os.environ.get("IMAGE_STORE_DYNAMODB_SK_NAME", "sk")
DDB_SCAN_LIMIT = int(os.environ.get("DDB_SCAN_LIMIT", "100"))
DDB_MAX_SCAN_PAGES = int(os.environ.get("DDB_MAX_SCAN_PAGES", "10"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DDB_TABLE_NAME)


def _tokenize(query_text: str) -> list[str]:
    return [token.strip().lower() for token in query_text.split() if token.strip()]


def _score_item(description: str, tokens: list[str]) -> int:
    text = description.lower()
    return sum(1 for token in tokens if token in text)


def search_image_by_description(query_text: str, size: int = 10) -> list[dict[str, Any]]:
    tokens = _tokenize(query_text)
    if not tokens or size <= 0:
        return []

    # Scan with a broad contains filter first, then rank in memory by token matches.
    filter_expr = Attr("description").contains(tokens[0])

    scan_kwargs: dict[str, Any] = {
        "FilterExpression": filter_expr,
        "Limit": max(size * 3, DDB_SCAN_LIMIT),
    }

    items: list[dict[str, Any]] = []
    pages_read = 0

    while pages_read < DDB_MAX_SCAN_PAGES:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        pages_read += 1

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

        if len(items) >= size * 8:
            break

    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        description = str(item.get("description", ""))
        score = _score_item(description, tokens)
        if score <= 0:
            continue
        ranked.append((score, item))

    ranked.sort(key=lambda pair: pair[0], reverse=True)

    hits: list[dict[str, Any]] = []
    for score, item in ranked[:size]:
        hits.append(
            {
                "_index": DDB_TABLE_NAME,
                "_id": item.get(DDB_PK_NAME) or item.get(DDB_SK_NAME),
                "_score": float(score),
                "_source": item,
            }
        )

    return hits
