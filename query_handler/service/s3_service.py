import boto3

s3_client = boto3.client("s3")

def get_s3_object(bucket: str, key: str) -> bytes:
    s3_client = boto3.client("s3")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body_stream = response["Body"]
    try:
        payload = body_stream.read()
    finally:
        body_stream.close()
    return payload