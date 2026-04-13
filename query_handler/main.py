from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from service import opensearch_service, grok_service, s3_service

app = APIGatewayRestResolver()


@app.post("/search-image")
def search_image() -> Response:
    # 1. Parse base64 image from request
    # 2. Call llm to convert image to text
    # 3. Convert text to vector
    # 4. Search vector database for similar images
    # 5. Return results

    event = app.current_event.json_body
    base64_image = event.get("image")

    if not base64_image:
        return Response(status_code=400, body="Image is required")
    
    grok_response = grok_service.image_to_description(base64_image)
    
    opensearch_response = opensearch_service.search_image_by_description(grok_response["description"])
    
    response = opensearch_response
    
    return response


@app.get("/text-search")
def text_search(size: int = 10) -> Response:
    # 1. Parse query parameter from request
    # 2. Convert text to vector
    # 3. Search vector database for similar images
    # 4. Return results
    event = app.current_event.query_string_parameters
    input_text = event.get("inputText", None)
    size = int(event.get("size", size))

    if not input_text:
        return Response(status_code=400, body="inputText is required")

    # Call Bedrock API to convert image to description
    # This is a placeholder implementation. Replace with actual API call.
    opensearch_response = opensearch_service.search_image_by_description(input_text, size=size)
    
    response = opensearch_response
    
    return response

def get_s3_image(bucket: str, key: str) -> bytes:
    s3_response = s3_service.get_s3_object(bucket, key)
    return s3_response

def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
