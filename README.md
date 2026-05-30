# KYC ID Document Processing API

A FastAPI-based KYC (Know Your Customer) system that automatically extracts structured data from government-issued ID documents using AWS Textract and asynchronous task processing.

## Features

- **JWT Authentication**: Secure endpoint access with token-based authentication
- **Async Processing**: Celery task queue for background document analysis
- **AWS Textract Integration**: Automatic extraction of ID field data (name, DOB, document number, etc.)
- **S3 Storage**: Secure file upload and storage with presigned URLs
- **PostgreSQL Persistence**: Track KYC task status and results
- **Image Validation**: Support for JPEG, PNG, and WebP formats
- **Structured Logging**: Comprehensive logging for debugging and monitoring

## Tech Stack

- **Framework**: FastAPI (async web framework)
- **Task Queue**: Celery with Redis
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cloud Services**: AWS Textract, S3
- **Authentication**: PyJWT
- **Server**: Uvicorn

## Project Structure

```
├── main.py                    # FastAPI application with endpoint definitions
├── requirements.txt           # Python dependencies
├── worker.py                  # Celery worker configuration
├── services/
│   └── ocr_service.py        # AWS Textract integration
├── utils/
│   ├── file_utils.py         # S3 upload & image validation
│   ├── logger.py             # Logging configuration
│   └── auth.py               # JWT token management
├── db/
│   ├── database.py           # Database connection setup
│   └── models.py             # SQLAlchemy models
└── uploads/                   # Local upload directory (for development)
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- AWS account with Textract and S3 access

### Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd learningAPI
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # or
   source venv/bin/activate  # Linux/macOS
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-ocr-bucket
   DATABASE_URL=postgresql://user:password@localhost/kyc_db
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=your-secret-key
   ```

5. **Initialize the database**
   ```bash
   python -c "from db.database import engine, Base; Base.metadata.create_all(bind=engine)"
   ```

## Running the Application

### Using Docker Compose (Recommended)

The easiest way to run the entire stack (FastAPI, Celery, Redis, PostgreSQL) is using Docker Compose:
```bash
docker-compose up --build
```

### Running Manually

### Start Redis
```bash
redis-server
```

### Start Celery Worker
```bash
celery -A worker worker --loglevel=info
```

### Start FastAPI Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

## API Endpoints

### Authentication

**POST** `/token`
- Get JWT access token
- **Body**: `username`, `password`
- **Returns**: `access_token`, `token_type`

### KYC Document Upload

**POST** `/kyc/upload-id` (Requires authentication)
- Upload and process a government ID document
- **Form Parameters**:
  - `user_id` (string): Unique user identifier
  - `file` (file): Image file (JPEG, PNG, WebP)
- **Returns**: 
  ```json
  {
    "message": "ID Document uploaded and is undergoing KYC analysis.",
    "task_id": "celery-task-uuid"
  }
  ```
- **Status**: 202 (Accepted)

### Query Task Status

**GET** `/tasks/{task_id}` (Requires authentication)
- Poll for KYC extraction results
- **Returns**: Task status and extracted ID data

## API Usage Example

```bash
# Get token
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"

# Upload ID document
curl -X POST http://localhost:8000/kyc/upload-id \
  -H "Authorization: Bearer <access_token>" \
  -F "user_id=user123" \
  -F "file=@id_photo.jpg"
```

## Extracted Data Format

AWS Textract returns ID fields with the following structure:

```json
{
  "FIRST_NAME": {
    "value": "John",
    "confidence": 0.95
  },
  "LAST_NAME": {
    "value": "Doe",
    "confidence": 0.98
  },
  "DATE_OF_BIRTH": {
    "value": "01/15/1990",
    "confidence": 0.97
  },
  "DOCUMENT_NUMBER": {
    "value": "D123456789",
    "confidence": 0.99
  }
}
```

## Configuration

### Supported Image Types
- JPEG/JPG
- PNG
- WebP

### AWS Textract Confidence Threshold
Adjust confidence scoring in `services/ocr_service.py` to filter low-confidence extractions.

## Development

### Running Tests
```bash
pytest tests/
```

### Docker Deployment
A `docker-compose.yml` is available for containerized deployment with PostgreSQL and Redis.

## Logging

Logs are output to stdout with timestamps and log levels. Configure logging level in `utils/logger.py`.

## Security Notes

- **Authentication**: Currently uses hardcoded credentials (`admin/secret`) for development. Implement database-backed user authentication for production.
- **Environment Variables**: Store sensitive credentials in `.env` files (never commit to version control).
- **S3 Permissions**: Restrict S3 bucket access using IAM policies.
- **JWT Secret**: Use a strong, random secret key for JWT signing.

## Troubleshooting

- **S3 Upload Fails**: Check AWS credentials and bucket permissions
- **Celery Tasks Not Processing**: Ensure Redis is running and Celery worker is active
- **Database Connection Error**: Verify PostgreSQL connection string and that the database exists
- **Textract Errors**: Ensure the image is clear and readable; check AWS Textract quotas
