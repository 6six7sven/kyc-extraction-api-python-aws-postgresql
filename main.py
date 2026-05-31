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
from utils.auth import create_access_token, get_current_user, verify_password, get_password_hash

from db.database import engine, get_db, Base
from db.models import KYCTask, User

# Create PostgreSQL tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = setup_logger(__name__)


# Pydantic Response Models for Auto-Documentation
class TaskResponse(BaseModel):
    message: str
    task_id: str

class UserCreate(BaseModel):
    username: str
    password: str


@app.post("/register", status_code=201)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user in the database."""
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Simple endpoint to authenticate and issue a JWT token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/kyc/upload-id", response_model=TaskResponse, status_code=202)
async def upload_id_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Upload a government-issued ID (Passport, Driver's License) for KYC extraction.
    
    Args:
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
            user_id=current_user,
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
    task_record = db.query(KYCTask).filter(KYCTask.task_id == task_id, KYCTask.user_id == current_user).first()
    
    if not task_record:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
        
    return {
        "task_id": task_record.task_id,
        "user_id": task_record.user_id,
        "status": task_record.status,
        "upload_timestamp": task_record.upload_timestamp.isoformat(),
        "extracted_fields": task_record.extracted_fields
    }


@app.get("/kyc/users/{user_id}/tasks")
async def get_user_tasks(user_id: str, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Retrieve a history of all past KYC tasks and their extracted data for a specific user."""
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only view your own task history.")
        
    tasks = db.query(KYCTask).filter(KYCTask.user_id == user_id).order_by(KYCTask.upload_timestamp.desc()).all()
    
    return {
        "user_id": user_id,
        "tasks": [
            {
                "task_id": task.task_id,
                "status": task.status,
                "upload_timestamp": task.upload_timestamp.isoformat(),
                "extracted_fields": task.extracted_fields
            }
            for task in tasks
        ]
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
