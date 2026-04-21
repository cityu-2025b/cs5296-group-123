# CS5296 Cloud Computing - Course Project

Subject: Real-Time Vector-Based Image Search Using AWS Streaming Services

Nature Of Project: Research

Group ID: Group123

Project Member:

| Name | SID |
| --- | --- |
| YAM Yat Wa | 55230160 |
| WONG Man Kin | 59230395 |
| LAI Siu Kwok | 55502170 |

## Overall System Architecture

The architecture is event-driven and serverless, with a main query handler and ingestion pipeline that generates embeddings and indexes them in OpenSearch. An S3 tiering handler moves objects across storage classes based on access patterns to balance performance and cost. The system supports both user queries (text or image) and real-time ingestion of new images with low-latency indexing.

<img width="724" height="155" alt="image" src="<img width="3786" height="1176" alt="image" src="https://github.com/user-attachments/assets/c3468575-e4b9-4b80-9b1e-5e3e2e5d0c6f" />


## Services Used

- Amazon API Gateway
- AWS Lambda
- Amazon S3 (Standard, Intelligent-Tiering, and archival tiers)
- Amazon DynamoDB
- Amazon EventBridge
- Amazon OpenSearch Service
- Amazon Bedrock (embedding and model inference)
- Amazon SNS (notifications)

## Key Features

- Text-to-image and image-to-image semantic search.
- Event-driven ingestion with low-latency indexing.
- Vector embeddings stored and queried in OpenSearch.
- Adaptive S3 storage tiering based on access patterns.
- Serverless scaling using AWS managed services.


## Project Structure

- [aosstack.yaml](aosstack.yaml): Infrastructure template for the stack.
- [build_lambda/](build_lambda/): Packaged Lambda dependencies and entrypoints.
- [dev-container/](dev-container/): Dev container configuration.
- [dev-image-descriptor/](dev-image-descriptor/): Local image descriptor tooling.
- [event/](event/): Sample event payloads or test artifacts.
- [image_processing_lambda/](image_processing_lambda/): Image processing Lambda code.
- [os_bedrock_connector/](os_bedrock_connector/): OpenSearch and Bedrock integration.
- [permission/](permission/): IAM permissions and helpers.
- [policy/](policy/): IAM policies for services.
- [query_handler/](query_handler/): Main query service handler.
- [s3_tiering_handler/](s3_tiering_handler/): S3 tiering automation handler.
- [test_py/](test_py/): Python tests and experiments.
- [load_test_k6.js](load_test_k6.js): Load testing script (k6).
- [requirements.txt](requirements.txt): Python dependencies.

## Data Flow Summary

1. Users upload images to S3 or submit a search request via API Gateway.
2. Lambda functions generate embeddings using Bedrock and persist metadata in DynamoDB.
3. Vector embeddings are indexed in OpenSearch for semantic search.
4. Queries return ranked image results with low latency.
5. Tiering automation moves S3 objects to the right storage class based on access.

## Prerequisites

- AWS account with permissions for S3, Lambda, OpenSearch, DynamoDB, EventBridge, and Bedrock.
- Python 3.x for local utilities and tests.
- k6 for load testing (optional).

## Configuration

The following items are required for deployment and local testing:

- S3 bucket names for ingestion and storage tiers.
- OpenSearch endpoint and index name.
- Bedrock model or embedding endpoint configuration.
- IAM roles and policies for Lambda execution.

Refer to [aosstack.yaml](aosstack.yaml) and the policy files in [policy/](policy/) for details.

## Deployment (High Level)

1. Review and customize [aosstack.yaml](aosstack.yaml).
2. Package Lambda dependencies in [build_lambda/](build_lambda/).
3. Deploy the stack using your preferred IaC workflow.
4. Verify OpenSearch index creation and connectivity.
5. Upload a sample image to trigger ingestion and indexing.

## Usage (High Level)

- Upload images to the ingestion S3 bucket to trigger indexing.
- Submit text or image queries to the API Gateway endpoint.
- Retrieve ranked results from OpenSearch-backed search responses.

If you want exact request and response formats, share your API payload examples and I can add them here.

## Testing

- Run Python-based checks using your local environment and dependencies from [requirements.txt](requirements.txt).

## Load Testing

- [load_test_k6.js](load_test_k6.js) contains the k6 script for query load testing.
- Update the target endpoint and test parameters in the script before running.
