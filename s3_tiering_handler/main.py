import json
from service import dynamodb_service, opensearch_service, s3_service
from config import S3_BUCKET_GLACIER_FLEXIBLE_RETRIEVAL, S3_BUCKET_GLACIER_INSTANT_RETRIEVAL, S3_BUCKET_STANDARD_IA

# | Threshold in Days | Expected Storage Class |
# |-------------------|------------------------|
# | <= 5              | STANDARD               |
# | > 5 and <= 10     | STANDARD_IA            |
# | > 10 and <= 30    | GLACIER_IR             |
# | > 30              | GLACIER                |


def lambda_handler(event, context):
    # handle glacier ir -> glacier
    
    to_glacier = opensearch_service.search_image_with_infrequenty_access("GLACIER", 30)
    for docs in to_glacier:
        s3_file_name = docs["s3_file_path"]
        s3_service.move_file(docs["s3_bucket_name"], s3_file_name, S3_BUCKET_GLACIER_FLEXIBLE_RETRIEVAL, s3_file_name, "GLACIER")
        dynamodb_service.update_ddb_record(docs['PK'], docs["SK"], storage_class="GLACIER", s3_bucket_name=S3_BUCKET_GLACIER_FLEXIBLE_RETRIEVAL)


    # handle standard id -> glacier ir
    to_glacier_ir = opensearch_service.search_image_with_infrequenty_access("GLACIER_IR", 10)
    for docs in to_glacier_ir:
        s3_file_name = docs["s3_file_path"]
        s3_service.move_file(docs["s3_bucket_name"], s3_file_name, S3_BUCKET_GLACIER_INSTANT_RETRIEVAL, s3_file_name, "GLACIER_IR")
        dynamodb_service.update_ddb_record(docs['PK'], docs["SK"], storage_class="GLACIER_IR", s3_bucket_name=S3_BUCKET_GLACIER_INSTANT_RETRIEVAL)

    
    # handle standard -> standard ia
    to_standard_ia = opensearch_service.search_image_with_infrequenty_access("STANDARD_IA", 5)
    for docs in to_standard_ia:
        s3_file_name = docs["s3_file_path"]
        s3_service.move_file(docs["s3_bucket_name"], s3_file_name, S3_BUCKET_STANDARD_IA, s3_file_name, "STANDARD", delete_source_file=False)
        dynamodb_service.update_ddb_record(docs['PK'], docs["SK"], storage_class="STANDARD", s3_bucket_name=S3_BUCKET_STANDARD_IA)

