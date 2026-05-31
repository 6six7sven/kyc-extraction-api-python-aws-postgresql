import os
import uuid
import boto3
import json
from fastapi import UploadFile, HTTPException
from typing import Tuple

from config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Initialize S3 client (AWS credentials read from environment variables)
AWS_REGION = settings.aws_region
s3_client = boto3.client('s3', region_name=AWS_REGION)
S3_BUCKET_NAME = settings.s3_bucket_name

def validate_image_file(file: UploadFile) -> None:
    """Validates that the uploaded file is a supported image type and within size limits."""
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )
        
    if file.size is not None and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
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