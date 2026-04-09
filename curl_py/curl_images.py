import boto3
import base64

s3 = boto3.client('s3')

# 1. Get the object from S3
response = s3.get_object(Bucket='your-bucket-name', Key='image.jpg')
image_content = response['Body'].read()

# 2. Encode to Base64
base64_bytes = base64.b64encode(image_content)
base64_string = base64_bytes.decode('utf-8')

print(f"data:image/jpeg;base64,{base64_string}")
