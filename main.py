from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pathlib import Path
from celery.result import AsyncResult

from services.ocr_service import process_image
from utils.file_utils import validate_image_file, save_upload_with_uuid, get_s3_presigned_url
from utils.logger import setup_logger
from worker import process_image_task, celery_app

app = FastAPI()
logger = setup_logger(__name__)


@app.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...), 
    search_text: Optional[str] = Form(None),
    min_confidence: float = Form(0.0),
    fuzzy_threshold: int = Form(80)
):
    """
    Upload an image file.
    
    Args:
        file: Image file to upload
        search_text: Optional text to search for within the extracted strings
        min_confidence: Minimum OCR confidence threshold to keep a bounding box
        fuzzy_threshold: The match percentage threshold (0-100) for fuzzy searching
        
    Returns:
        JSON response with extracted text and a URL to the annotated image
        JSON response with a task_id to poll for results
    """
    logger.info(f"Received upload request for file: {file.filename}")
    try:
        # Validate file is an image
        validate_image_file(file)
        
        # Save the file
        file_path, unique_filename = await save_upload_with_uuid(file)
        logger.info(f"File saved successfully as {unique_filename}")
        
        # Dispatch the OCR processing to a background Celery worker
        task = process_image_task.delay(
            str(file_path), 
            search_text,
            min_confidence,
            fuzzy_threshold
        )
        logger.info(f"Dispatched background task {task.id} for image {unique_filename}.")

        return JSONResponse(
            status_code=202,
            content={
                "message": "Image uploaded and is processing in the background.",
                "task_id": task.id
            }
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
