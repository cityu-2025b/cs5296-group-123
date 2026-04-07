import boto3
from config import DDB_TABLE
from boto3.dynamodb.conditions import Key, Attr

dynamodb_client = boto3.client("dynamodb")
table = dynamodb_client.Table(DDB_TABLE)

def update_ddb_record(pk: str, storage_class: str, s3_bucket_name):
  update_result = table.update_item(
    Key={"PK": pk},
    UpdateExpression="set lastest_s3_storage_tier = :lastest_s3_storage_tier, s3_bucket_name = :s3_bucket_name",
    ExpressionAttributeValues={
      ":lastest_s3_storage_tier": storage_class,
      ":s3_bucket_name": s3_bucket_name
    },
    ReturnValues="UPDATED_NEW"
  )
  
  return update_result
  
  