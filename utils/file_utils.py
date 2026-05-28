import os
import uuid
import boto3
from fastapi import UploadFile, HTTPException
from typing import Tuple

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

# Initialize S3 client (AWS credentials read from environment variables)
s3_client = boto3.client('s3')
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