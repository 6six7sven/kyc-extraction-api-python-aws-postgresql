from celery import Celery
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from services.ocr_service import process_id_document

# Initialize Celery
# Broker: Redis is used to pass messages between FastAPI and Celery
# Backend: Redis is used to store the results of the completed tasks
celery_app = Celery(
    "ocr_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(name="process_id_task")
def process_id_task(file_path_str: str):
    """Background task to run KYC extraction on an ID document."""
    
    # Run the Textract AI extraction
    extracted_data = process_id_document(file_path_str)
    
    return {
        "kyc_data": extracted_data
    }