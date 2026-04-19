from requests import Response
from opensearchpy import OpenSearch
from datetime import datetime, timezone

from config import  AOS_HOST, AOS_USERNAME, AOS_PASSWORD, AOS_INDEX_NAME

opensearch_client = OpenSearch(
    hosts=[{"host": AOS_HOST, "port": 443}],
    http_auth=(AOS_USERNAME, AOS_PASSWORD),
    use_ssl=True,
    verify_certs=True,
    ssl_show_warn=False,
    http_compress=True
)

def search_image_with_infrequenty_access(storage_class: str, threshold_in_days=5):
    threshold_in_seconds = threshold_in_days * 24 * 60 * 60
    cutoff_epoch_seconds = int(datetime.now(timezone.utc).timestamp()) - threshold_in_seconds

    query_request = {
      "query": {
        "bool": {
          "should": [
            {
              "script": {
                "script": {
                  "source": f"""
                    if (doc['last_accessed_time'].size() == 0) return false;
                    long diff = new Date().getTime() / 1000 - doc['last_accessed_time'].value;
                    if (diff > {threshold_in_seconds}L && doc['lastest_s3_storage_tier.keyword'].value != "{storage_class}") return true;
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
                        "lte": cutoff_epoch_seconds
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
    print(query_request)
    response = opensearch_client.search(
        index=AOS_INDEX_NAME,
        body=query_request
    )
    
    print(response["hits"]["total"]["value"])
    if response["hits"]["total"]["value"] == 0:
        return []
    
    result = [hit["_source"] for hit in response["hits"]["hits"]]
    
    return result