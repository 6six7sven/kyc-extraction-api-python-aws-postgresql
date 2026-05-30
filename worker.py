from celery import Celery
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from services.ocr_service import process_id_document
from utils.file_utils import save_json_to_s3

from db.database import SessionLocal
from db.models import KYCTask

# Initialize Celery
# Broker: Redis is used to pass messages between FastAPI and Celery
# Backend: Redis is used to store the results of the completed tasks
celery_app = Celery(
    "ocr_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(name="process_id_task", bind=True)
def process_id_task(self, file_path_str: str):
    """Background task to run KYC extraction on an ID document."""
    task_id = self.request.id
    
    try:
        # Run the Textract AI extraction
        extracted_data = process_id_document(file_path_str)
        
        # Save the extracted data to S3 as a JSON file
        json_s3_uri = save_json_to_s3(extracted_data, file_path_str)
        status = "SUCCESS"
    except Exception as e:
        extracted_data = {"error": str(e)}
        json_s3_uri = None
        status = "FAILURE"
        
    # Update PostgreSQL Database
    db = SessionLocal()
    task_record = db.query(KYCTask).filter(KYCTask.task_id == task_id).first()
    if task_record:
        task_record.status = status
        task_record.extracted_fields = extracted_data
        db.commit()
    db.close()
    
    return {
        "kyc_data": extracted_data,
        "saved_json_uri": json_s3_uri
    }