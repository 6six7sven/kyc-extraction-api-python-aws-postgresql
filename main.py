from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from celery.result import AsyncResult
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from utils.file_utils import validate_image_file, save_upload_with_uuid, get_s3_presigned_url
from utils.logger import setup_logger
from worker import process_id_task, celery_app
from utils.auth import create_access_token, get_current_user

from db.database import engine, get_db, Base
from db.models import KYCTask

# Create PostgreSQL tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = setup_logger(__name__)


# Pydantic Response Models for Auto-Documentation
class TaskResponse(BaseModel):
    message: str
    task_id: str


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Simple endpoint to authenticate and issue a JWT token."""
    # Hardcoded dummy credentials for simplicity (use a database in production!)
    if form_data.username != "admin" or form_data.password != "secret":
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/kyc/upload-id", response_model=TaskResponse, status_code=202)
async def upload_id_document(
    user_id: str = Form(..., description="The unique ID of the user uploading the document"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Upload a government-issued ID (Passport, Driver's License) for KYC extraction.
    
    Args:
        user_id: Unique identifier for the user
        file: Image file to upload (JPEG, PNG, WebP)
        
    Returns:
        JSON response with a task_id to poll for KYC results
    """
    logger.info(f"Received KYC upload request for file: {file.filename}")
    try:
        # Validate file is an image
        validate_image_file(file)
        
        # Save the file
        file_path, unique_filename = await save_upload_with_uuid(file)
        logger.info(f"File saved successfully as {unique_filename}")
        
        # Dispatch the KYC processing to a background Celery worker
        task = process_id_task.delay(str(file_path))
        
        # Save the initial task record to PostgreSQL
        db_task = KYCTask(
            task_id=task.id,
            user_id=user_id,
            status="PENDING"
        )
        db.add(db_task)
        db.commit()
        
        logger.info(f"Dispatched background task {task.id} for image {unique_filename}.")

        return TaskResponse(
            message="ID Document uploaded and is undergoing KYC analysis.",
            task_id=task.id
        )
    
    except HTTPException as e:
        logger.warning(f"Validation error: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error processing image upload: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal server error occurred while processing the image."}
        )


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Check the status and results of a background KYC task from PostgreSQL"""
    task_record = db.query(KYCTask).filter(KYCTask.task_id == task_id).first()
    
    if not task_record:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
        
    return {
        "task_id": task_record.task_id,
        "user_id": task_record.user_id,
        "status": task_record.status,
        "upload_timestamp": task_record.upload_timestamp.isoformat(),
        "extracted_fields": task_record.extracted_fields
    }


@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Redirect to an S3 presigned URL for the requested file"""
    try:
        presigned_url = get_s3_presigned_url(filename)
        return RedirectResponse(url=presigned_url)
    except Exception as e:
        logger.error(f"Error generating presigned URL for {filename}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Could not generate file URL"})


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FastAPI Image Upload Server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
