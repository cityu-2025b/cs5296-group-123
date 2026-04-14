import os
from typing import Any

from opensearchpy import OpenSearch

from config import  AOS_HOST, AOS_MODEL_ID, AOS_USERNAME, AOS_PASSWORD, AOS_INDEX_NAME

OS_REQUEST_TIMEOUT = int(os.environ.get("AOS_REQUEST_TIMEOUT", "30"))

opensearch_client = OpenSearch(
    hosts=[{"host": AOS_HOST, "port": 443}],
    http_auth=(AOS_USERNAME, AOS_PASSWORD),
    use_ssl=True,
    verify_certs=True,
    ssl_show_warn=False,
    http_compress=True,
    timeout=OS_REQUEST_TIMEOUT,
    max_retries=2,
    retry_on_timeout=True,
)

def search_image_by_description(query_text: str, size: int = 5, nearest_k: int = 3) -> list[dict[str, Any]]:
    if AOS_MODEL_ID:
        query_request = {
            "size": size,
            "query": {
                "neural": {
                    "description_embedding": {
                        "query_text": query_text,
                        "model_id": AOS_MODEL_ID,
                        "k": nearest_k,
                    }
                }
            },
        }
    else:
        query_request = {
            "size": size,
            "query": {
                "match": {
                    "description": {
                        "query": query_text,
                    }
                }
            },
        }
    
    response = opensearch_client.search(
        index=AOS_INDEX_NAME,
        body=query_request,
        params={"request_timeout": OS_REQUEST_TIMEOUT},
    )
    
    result = response["hits"]["hits"]
    
    return result