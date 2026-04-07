import boto3
from config import DDB_TABLE
from boto3.dynamodb.conditions import Key, Attr

dynamodb_client = boto3.client("dynamodb")
table = dynamodb_client.Table(DDB_TABLE)

def update_ddb_record(pk: str, storage_class: str):
  update_result = table.update_item(
    Key={"PK": pk},
    UpdateExpression="set STORAGE_CLASS = :storage_class",
    ExpressionAttributeValues={
      ":storage_class": storage_class
    },
    ReturnValues="UPDATED_NEW"
  )
  
  return update_result
  
  