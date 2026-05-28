from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

from services.ocr_service import process_image
from utils.file_utils import validate_image_file, save_upload_with_uuid, UPLOAD_DIR
from utils.logger import setup_logger

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
    """
    logger.info(f"Received upload request for file: {file.filename}")
    try:
        # Validate file is an image
        validate_image_file(file)
        
        # Save the file
        file_path, unique_filename = await save_upload_with_uuid(file)
        logger.info(f"File saved successfully as {unique_filename}")
        
        # Process the image with OCR service
        extracted_data, annotated_file_path = process_image(
            file_path, 
            search_text=search_text,
            min_confidence=min_confidence,
            fuzzy_threshold=fuzzy_threshold
        )
        logger.info(f"Successfully processed image {unique_filename}. Extracted {len(extracted_data)} items.")

        return JSONResponse(content={
            "extracted_data": extracted_data,
            "annotated_image_url": f"/uploads/{annotated_file_path.name}"
        })
    
    except HTTPException as e:
        logger.warning(f"Validation error: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error processing image upload: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal server error occurred while processing the image."}
        )


@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded and annotated images"""
    file_path = UPLOAD_DIR / filename
    
    # Directory traversal validation
    if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        logger.warning(f"Path traversal attempt detected: {filename}")
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
        
    if file_path.exists():
        return FileResponse(path=str(file_path))
    logger.warning(f"Requested file not found: {filename}")
    return JSONResponse(status_code=404, content={"error": "File not found"})


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FastAPI Image Upload Server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
