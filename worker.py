from celery import Celery
from pathlib import Path
from typing import Optional

from services.ocr_service import process_image

# Initialize Celery
# Broker: Redis is used to pass messages between FastAPI and Celery
# Backend: Redis is used to store the results of the completed tasks
celery_app = Celery(
    "ocr_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(name="process_image_task")
def process_image_task(file_path_str: str, search_text: Optional[str] = None, min_confidence: float = 0.0, fuzzy_threshold: int = 80):
    """Background task to run OCR on an image."""
    # Celery tasks must take serializable arguments, so we convert the string back to a Path
    file_path = Path(file_path_str)
    
    # Run the heavy OCR extraction
    extracted_data, annotated_file_path = process_image(
        file_path, search_text, min_confidence, fuzzy_threshold
    )
    
    # Return purely JSON serializable data
    return {
        "extracted_data": extracted_data,
        "annotated_image_url": f"/uploads/{annotated_file_path.name}"
    }