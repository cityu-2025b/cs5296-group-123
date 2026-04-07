import os
import json
import boto3
import requests
import cfnresponse
from requests_aws4auth import AWS4Auth

AOS_INDEX_NAME = os.environ.get('AOS_INDEX_NAME')
AOS_HOST = os.environ.get('AOS_HOST')
AOS_REGION = os.environ.get('AOS_REGION')
AOS_USERNAME = os.environ.get('AOS_USERNAME')
AOS_PASSWORD = os.environ.get('AOS_PASSWORD')
AWS_SERVICE = os.environ.get('AOS_SERVICE')
LAMBDA_ROLE = os.environ.get('LAMBDA_ROLE')
AOSI_ROLE = os.environ.get('AOSI_ROLE')
BEDROCK_ROLE = os.environ.get('BEDROCK_ROLE')
BEDROCK_REGION = os.environ.get('BEDROCK_REGION')
HTTP_HEADERS = {"Content-Type": "application/json"}


def attach_lambda_role_to_admin_user():

    admin_user = AOS_USERNAME
    admin_password = AOS_PASSWORD

    url = f'https://{AOS_HOST}/_plugins/_security/api/rolesmapping/all_access'

    payload = {
        "hosts": [],
        "users": [admin_user],
        "backend_roles": [LAMBDA_ROLE, AOSI_ROLE]
    }

    r = requests.put(url, auth=(admin_user, admin_password),
                     json=payload, headers=HTTP_HEADERS)

    if r.status_code == 200:
        print(f'Successfully attached "{LAMBDA_ROLE}" to "{admin_user}" user')
        return True
    else:
        print(f'Failed to attach "{LAMBDA_ROLE}" to "{admin_user}" user')
        print(r.text)
        return False


def get_aws_credentials():
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(credentials.access_key, credentials.secret_key,
                        AOS_REGION, AWS_SERVICE, session_token=credentials.token)
    return aws_auth


def create_bedrock_connector():
    aws_auth = get_aws_credentials()

    url = f'https://{AOS_HOST}/_plugins/_ml/connectors/_create'

    payload = {
        "name": "Bedrock embeddings",
        "description": "Connector for Bedrock embeddings",
        "version": 1,
        "protocol": "aws_sigv4",
        "credential": {
            "roleArn": BEDROCK_ROLE,
        },
        "parameters": {
            "region": BEDROCK_REGION,
            "service_name": "bedrock",
        },
        "actions": [
            {
                "action_type": "predict",
                "method": "POST",
                "headers": {
                    "content-type": "application/json",
                    "x-amz-content-sha256": "required"
                },
                "url": "https://bedrock-runtime.us-east-1.amazonaws.com/model/amazon.titan-embed-text-v1/invoke",
                "request_body": "{ \"inputText\": \"${parameters.inputText}\" }",
                "pre_process_function": "\n    StringBuilder builder = new StringBuilder();\n    builder.append(\"\\\"\");\n    String first = params.text_docs[0];\n    builder.append(first);\n    builder.append(\"\\\"\");\n    def parameters = \"{\" +\"\\\"inputText\\\":\" + builder + \"}\";\n    return  \"{\" +\"\\\"parameters\\\":\" + parameters + \"}\";",
                "post_process_function": "\n      def name = \"sentence_embedding\";\n      def dataType = \"FLOAT32\";\n      if (params.embedding == null || params.embedding.length == 0) {\n        return params.message;\n      }\n      def shape = [params.embedding.length];\n      def json = \"{\" +\n                 \"\\\"name\\\":\\\"\" + name + \"\\\",\" +\n                 \"\\\"data_type\\\":\\\"\" + dataType + \"\\\",\" +\n                 \"\\\"shape\\\":\" + shape + \",\" +\n                 \"\\\"data\\\":\" + params.embedding +\n                 \"}\";\n      return json;\n    "
            },
        ]
    }

    r = requests.post(url, auth=aws_auth, json=payload, headers=HTTP_HEADERS)

    if r.status_code == 200:
        print(f'Successfully created Bedrock connector')
        return json.loads(r.text)["connector_id"]
    else:
        print(f'Failed to create Bedrock connector')
        print(r.text)
        return None


def register_bedrock_model(connector_id):
    headers = {"Content-Type": "application/json"}
    aws_auth = get_aws_credentials()

    url = f'https://{AOS_HOST}/_plugins/_ml/models/_register'

    payload = {
        "name": "Bedrock Multimodal embeddings model",
        "function_name": "remote",
        "description": "Bedrock Multimodal embeddings model",
        "connector_id": connector_id
    }

    r = requests.post(url, auth=aws_auth, json=payload, headers=headers)

    if r.status_code == 200:
        print(
            f'Successfully registered Bedrock model. Model id: {json.loads(r.text)["model_id"]}')
        model_id = json.loads(r.text)["model_id"]
    else:
        print(f'Failed to register Bedrock model')
        print(r.text)
        return (None, None)

    url = f'https://{AOS_HOST}/_plugins/_ml/models/{model_id}/_deploy'

    r = requests.post(url, auth=aws_auth, headers=headers)

    if r.status_code == 200:
        deploy_status = json.loads(r.text)["status"]
        print(
            f'Successfully deployed the model, Deployment status: {deploy_status}')

    return (model_id, deploy_status)


def test_aos_bedrock_connection(model_id):
    aws_auth = get_aws_credentials()
    headers = {"Content-Type": "application/json"}
    url = f'https://{AOS_HOST}/_plugins/_ml/models/{model_id}/_predict'

    payload = {
        "parameters": {
            "inputText": "hello"
        }
    }

    r = requests.post(url, auth=aws_auth, json=payload, headers=headers)
    if r.status_code == 200:
        print(f'Successfully tested AOS-Bedrock connection')
        embed = json.loads(r.text)["inference_results"][0]["output"][0]["data"]
        print(f'Dimensions of the embedding: {len(embed)}')
        print(embed[0:5])
        return True
    else:
        print(f'Failed to test AOS-Bedrock connection')
        print(r.text)
        return False


def ingestion_pipeline(model_id):
    aws_auth = get_aws_credentials()
    url = f'https://{AOS_HOST}/_ingest/pipeline/bedrock-embeddings-ingest-pipeline'

    payload = {
        "description": "Ingestion pipeline - Extract embeddings using Amazon Bedrock",
        "processors": [
            {
                "text_embedding": {
                    "model_id": model_id,
                    "field_map": {
                        "description": "description_embedding"
                    }
                }
            }
        ]
    }

    r = requests.put(url, auth=aws_auth, json=payload, headers=HTTP_HEADERS)

    if r.status_code == 200:
        print(f'Successfully created ingestion pipeline')
        return True
    else:
        print(f'Failed to create ingestion pipeline')
        print(r.text)
        return False


def create_knn_index():
    aws_auth = get_aws_credentials()
    url = f'https://{AOS_HOST}/{AOS_INDEX_NAME}'

    payload = {
        "settings": {
            "index.knn": True,
            "default_pipeline": "bedrock-embeddings-ingest-pipeline"
        },
        "mappings": {
            "properties": {
                "name": {
                    "type": "text"
                },
                "description_embedding": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "engine": "faiss",
                        "space_type": "l2",
                        "name": "hnsw",
                        "parameters": {}
                    }
                },
                "description": {
                    "type": "text"
                }
            }
        }
    }

    r = requests.delete(url, auth=aws_auth, headers=HTTP_HEADERS)
    r = requests.put(url, auth=aws_auth, json=payload, headers=HTTP_HEADERS)

    if r.status_code == 200:
        print(f'Successfully created KNN index')
        return True
    else:
        print(f'Failed to create KNN index')
        print(r.text)
        return False


def create_test_document():
    aws_auth = get_aws_credentials()
    url = f'https://{AOS_HOST}/{AOS_INDEX_NAME}/_doc/1'

    payload = {
        "name": "Product 1",
        "description": "This is a product description"
    }

    r = requests.put(url, auth=aws_auth, json=payload, headers=HTTP_HEADERS)

    if r.status_code == 201:
        print(f'Successfully created a test document')
        return True
    else:
        print(f'Failed to create a test document')
        print(r.text)
        return False


def lambda_handler(event, context):
    if not attach_lambda_role_to_admin_user():
        print("Failed to attach lambda role to admin user")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    connector_id = create_bedrock_connector()
    if not connector_id:
        print("Failed to create Bedrock connector")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    model_id, deploy_status = register_bedrock_model(connector_id)

    if not model_id and not deploy_status:
        print("Failed to register Bedrock model")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    print("Connector id, Model id, Deployment status:",
          connector_id, model_id, deploy_status)

    if not ingestion_pipeline(model_id):
        print("Failed to create ingestion pipeline")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    if not test_aos_bedrock_connection(model_id):
        print("Failed to test AOS-Bedrock connection")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    if not create_knn_index():
        print("Failed to create KNN index")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    if not create_test_document():
        print("Failed to create document")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    print("Successfully created OpenSearch connector for Bedrock")
    cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
