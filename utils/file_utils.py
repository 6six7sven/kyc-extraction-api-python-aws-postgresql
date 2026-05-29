import os
import uuid
import boto3
import json
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException
from typing import Tuple

load_dotenv()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

# Initialize S3 client (AWS credentials read from environment variables)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3_client = boto3.client('s3', region_name=AWS_REGION)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "my-ocr-bucket")

def validate_image_file(file: UploadFile) -> None:
    """Validates that the uploaded file is a supported image type."""
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )

async def save_upload_with_uuid(file: UploadFile) -> Tuple[str, str]:
    """Saves the file to AWS S3 with a UUID filename to prevent collisions."""
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Read the file asynchronously
    contents = await file.read()
    
    # Upload to S3
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME, 
        Key=unique_filename, 
        Body=contents,
        ContentType=file.content_type
    )
        
    s3_uri = f"s3://{S3_BUCKET_NAME}/{unique_filename}"
    return s3_uri, unique_filename

def get_s3_presigned_url(filename: str, expiration: int = 3600) -> str:
    """Generates a presigned URL for secure frontend access to the image."""
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': filename},
        ExpiresIn=expiration
    )

def save_json_to_s3(data: dict, original_s3_uri: str) -> str:
    """Saves dictionary data as a JSON file in S3."""
    filename = original_s3_uri.split('/')[-1]
    base_name = os.path.splitext(filename)[0]
    json_filename = f"{base_name}_kyc.json"
    
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=json_filename,
        Body=json.dumps(data, indent=4),
        ContentType='application/json'
    )
    
    return f"s3://{S3_BUCKET_NAME}/{json_filename}"