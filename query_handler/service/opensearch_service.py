from requests import Response
from opensearchpy import OpenSearch

from config import  AOS_HOST, AOS_MODEL_ID, AOS_USERNAME, AOS_PASSWORD, AOS_INDEX_NAME

opensearch_client = OpenSearch(
    hosts=[{"host": AOS_HOST, "port": 443}],
    http_auth=(AOS_USERNAME, AOS_PASSWORD),
    use_ssl=True,
    verify_certs=True,
    ssl_show_warn=False,
    http_compress=True
)

def search_image_by_description(query_text: str, size: int = 5, nearest_k: int= 3) -> Response:
    query_request = {
        "size": size,
        "query": {
            "neural": {
                "description_embedding": {
                    "query_text": query_text,
                    "model_id": AOS_MODEL_ID,
                    "k": nearest_k
                }
            }
        }
    }
    
    response = opensearch_client.search(
        index=AOS_INDEX_NAME,
        body=query_request
    )
    
    result = response["hits"]["hits"]
    
    return result