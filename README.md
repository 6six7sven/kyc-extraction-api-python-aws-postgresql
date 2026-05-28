# FastAPI Image Upload Server

A simple FastAPI application for uploading images.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install easyocr
pip install opencv-python
```

2. Run the server:
```bash
python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### POST `/upload-image`
Upload an image file.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: 
  - `file`: image file (required)
  - `search_text`: string to search for within the extracted text (optional)

**Response:**
Returns a JSON object containing the extracted text data and a URL to the annotated image.
```json
{
  "extracted_data": [...],
  "annotated_image_url": "/uploads/annotated_image.jpg"
}
```

**Error Response:**
```json
{
  "error": "File must be an image"
}
```

### GET `/`
Health check endpoint.

## Example Usage

Using curl:
```bash
curl -X POST -F "file=@path/to/image.jpg" -F "search_text=target" http://localhost:8000/upload-image
```

Using Python:
```python
import requests

with open('image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/upload-image', files=files)
    with open('annotated_result.jpg', 'wb') as out_f:
        out_f.write(response.content)
```

## Uploaded Images

Images are saved to the `uploads/` directory.
