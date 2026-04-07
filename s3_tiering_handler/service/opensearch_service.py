from requests import Response
from opensearchpy import OpenSearch

from config import  AOS_HOST, AOS_USERNAME, AOS_PASSWORD, AOS_INDEX_NAME

opensearch_client = OpenSearch(
    hosts=[{"host": AOS_HOST, "port": 443}],
    http_auth=(AOS_USERNAME, AOS_PASSWORD),
    use_ssl=True,
    verify_certs=True,
    ssl_show_warn=False,
    http_compress=True
)

def search_image_with_infrequenty_access(storage_class: str, threshold_in_days=5) -> Response:
    threshold_in_millis_second = threshold_in_days * 24 * 60 * 60 * 1000

    query_request = {
      "query": {
        "bool": {
          "should": [
            {
              "script": {
                "script": {
                  "source": f"""
                    if (doc['created_time'].size() == 0 || doc['last_accessed_time'].size() == 0) return false;
                    long diff = doc['last_accessed_time'] - doc['created_time'];
                    if (diff > {threshold_in_millis_second} && doc['storage_class] != {storage_class}) return true;
                    return false;
                  """
                }
              }
            },
            {
              "bool": {
                "must": [
                  {
                    "range": {
                      "created_time": {
                        "lte": f"now-{threshold_in_days}d/d"
                      }
                    },
                  }
                ],
                "must_not": [
                  {
                    "exists": {
                      "field": "last_accessed_time"
                    }
                  },
                  {
                    "term": {
                      "name": storage_class
                    }
                  }
                ]
              }
            }
          ],
          "minimum_should_match": 1
        }
      }
    }
    
    response = opensearch_client.search(
        index=AOS_INDEX_NAME,
        body=query_request
    )
    
    result = response["hits"]["hits"]
    
    return result