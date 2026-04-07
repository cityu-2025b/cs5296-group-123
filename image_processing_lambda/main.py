import json
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response
from aws_lambda_powertools.utilities.data_classes import S3Event


processor = BatchProcessor(event_type=EventType.SQS)


def record_handler(record):
    payload: S3Event = json.loads(record["s3"])
    print(f"Processing record with payload: {payload}")


def lambda_handler(event, context):
    return process_partial_response(
        event=event, record_handler=record_handler, processor=processor, context=context)
