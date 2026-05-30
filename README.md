# FastAPI KYC AI Extraction Engine

A production-ready, asynchronous FastAPI application for processing Identity Documents (KYC). It leverages AWS Textract to automatically extract structured data (Name, DOB, Document Number, etc.) from government IDs, using a background task queue to remain highly responsive.

## Architecture

This application is built with a highly scalable, cloud-native architecture:

* **FastAPI:** Handles incoming HTTP requests, input validation, and API routing.
* **Celery & Redis:** Manages the background task queue. Heavy document processing is handed off to Celery workers via Redis, preventing the web server from blocking during AI extraction.
* **AWS S3:** Provides secure cloud storage for the original uploaded identity documents and the generated JSON extraction files. Presigned URLs are used for secure temporary access.
* **AWS Textract:** An enterprise machine learning service used to accurately extract structured Key-Value pairs specifically from identity documents (Passports, Driver's Licenses, etc.).
* **PostgreSQL (via SQLAlchemy):** Stores persistent records of all KYC tasks, mapping `user_id`s to their extracted AI fields, timestamps, and task statuses. Compatible with AWS RDS.

## Setup

### 1. Prerequisites
- **Redis** running locally (or remotely) on `localhost:6379`.
- **PostgreSQL** running locally (or via AWS RDS).
- **AWS Account** with S3 and Textract permissions configured.

### 2. Environment Variables
Create a `.env` file in the root of the project with the following configuration:
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket_name
SECRET_KEY=your_jwt_secret_key

# Database Connection (Local or AWS RDS)
DATABASE_URL=postgresql://postgres:password@db:5432/kyc_db
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
