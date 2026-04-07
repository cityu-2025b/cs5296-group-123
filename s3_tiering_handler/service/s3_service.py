import boto3

s3_client = boto3.client("s3")

# storage class
# STANDARD
# STANDARD_IA
# GLACIER_IR
# GLACIER

def move_file(source_bucket, source_s3_key, target_bucket, target_s3_key, storage_class, delete_source_file: bool=False):
    s3_move_response = s3_client.meta.client.copy(
      {"Bucket": source_bucket, "Key": source_s3_key},
      target_bucket,
      target_s3_key,
      StorageClass=storage_class
    )
    
    if s3_move_response:
        if delete_source_file:
            s3_client.delete_object(
              Bucket=source_bucket,
              Key=source_s3_key
            )
          
    return True