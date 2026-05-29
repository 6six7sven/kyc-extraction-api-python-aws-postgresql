import os
import tempfile
import boto3
from urllib.parse import urlparse
import easyocr
import cv2
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from fuzzywuzzy import fuzz

# Initialize S3 client
s3_client = boto3.client('s3')

# Initialize EasyOCR reader for English (loads models into memory)
reader = easyocr.Reader(['en'])

def process_image(
    file_uri: str, 
    search_text: Optional[str] = None,
    min_confidence: float = 0.0,
    fuzzy_threshold: int = 80
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Download an image from S3, extract text, filter by search_text, 
    draw bounding boxes, and upload the annotated image back to S3.
    Returns the extracted data and the new annotated filename.
    """
    # Parse S3 URI
    parsed_uri = urlparse(file_uri)
    bucket = parsed_uri.netloc
    key = parsed_uri.path.lstrip('/')
    
    # Create temporary files for processing
    ext = Path(key).suffix or '.jpg'
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
        temp_input_path = tmp_in.name
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_out:
        temp_output_path = tmp_out.name
        
    try:
        # Download file from S3 to temporary storage
        s3_client.download_file(bucket, key, temp_input_path)
        
        # Extract text using EasyOCR
        ocr_results = reader.readtext(temp_input_path)
        
        # Read the image with OpenCV to draw bounding boxes
        image = cv2.imread(temp_input_path)
        if image is None:
            raise ValueError("Failed to load image file. It might be corrupted or unsupported.")
            
        extracted_data = []
        for bbox, text, conf in ocr_results:
            # Filter out text read below the minimum confidence threshold
            if conf < min_confidence:
                continue

            # If search_text is provided, use fuzzy string matching 
            if search_text:
                match_score = fuzz.partial_ratio(search_text.lower(), text.lower())
                if match_score < fuzzy_threshold:
                    continue

            # Draw bounding box on the image (green rectangle, 2px thickness)
            top_left = (int(bbox[0][0]), int(bbox[0][1]))
            bottom_right = (int(bbox[2][0]), int(bbox[2][1]))
            cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)
            
            extracted_data.append({
                "bounding_box": [[int(coord[0]), int(coord[1])] for coord in bbox],
                "text": text,
                "confidence": float(conf)
            })

        # Save the annotated image temporarily
        cv2.imwrite(temp_output_path, image)
        
        # Upload annotated image back to S3
        annotated_filename = f"annotated_{Path(key).name}"
        s3_client.upload_file(
            temp_output_path, 
            bucket, 
            annotated_filename,
            ExtraArgs={'ContentType': f'image/{ext.lstrip(".")}'}
        )

        return extracted_data, annotated_filename
        
    finally:
        # Clean up temporary files to free up disk space in the container/worker
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)