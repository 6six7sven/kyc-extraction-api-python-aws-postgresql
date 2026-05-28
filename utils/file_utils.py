import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from typing import Tuple

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def validate_image_file(file: UploadFile) -> None:
    """Validates that the uploaded file is a supported image type."""
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )

async def save_upload_with_uuid(file: UploadFile) -> Tuple[Path, str]:
    """Saves the file with a UUID filename to prevent collisions and path traversal."""
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save the file asynchronously
    contents = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
        
    return file_path, unique_filename