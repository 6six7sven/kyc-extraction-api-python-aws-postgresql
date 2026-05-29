from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from celery.result import AsyncResult
from pydantic import BaseModel

from utils.file_utils import validate_image_file, save_upload_with_uuid, get_s3_presigned_url
from utils.logger import setup_logger
from worker import process_id_task, celery_app

app = FastAPI()
logger = setup_logger(__name__)


# Pydantic Response Models for Auto-Documentation
class TaskResponse(BaseModel):
    message: str
    task_id: str


@app.post("/kyc/upload-id", response_model=TaskResponse, status_code=202)
async def upload_id_document(file: UploadFile = File(...)):
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
async def get_task_status(task_id: str):
    """Check the status of a background OCR task"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        return JSONResponse(content={"status": "PENDING"})
    elif task_result.state == 'SUCCESS':
        return JSONResponse(content={"status": "SUCCESS", "result": task_result.result})
    elif task_result.state == 'FAILURE':
        logger.error(f"Task {task_id} failed: {task_result.info}")
        return JSONResponse(content={"status": "FAILURE", "error": str(task_result.info)}, status_code=500)
    else:
        return JSONResponse(content={"status": task_result.state})


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
