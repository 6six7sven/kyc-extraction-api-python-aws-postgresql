import easyocr
import cv2
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from fuzzywuzzy import fuzz

# Initialize EasyOCR reader for English (loads models into memory)
reader = easyocr.Reader(['en'])

def process_image(
    file_path: Path, 
    search_text: Optional[str] = None,
    min_confidence: float = 0.0,
    fuzzy_threshold: int = 80
) -> Tuple[List[Dict[str, Any]], Path]:
    """
    Extract text from an image, filter by search_text, and draw bounding boxes.
    Returns the extracted data and the path to the annotated image.
    """
    # Extract text using EasyOCR
    ocr_results = reader.readtext(str(file_path))
    
    # Read the image with OpenCV to draw bounding boxes
    image = cv2.imread(str(file_path))
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

    # Save the annotated image
    annotated_filename = f"annotated_{file_path.name}"
    annotated_file_path = file_path.parent / annotated_filename
    cv2.imwrite(str(annotated_file_path), image)

    return extracted_data, annotated_file_path