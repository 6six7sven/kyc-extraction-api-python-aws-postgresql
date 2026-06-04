# KYC ID Document Processing API

A FastAPI-based KYC (Know Your Customer) system that automatically extracts structured data from government-issued ID documents using AWS Textract and asynchronous task processing.

## Features

- **JWT Authentication**: Secure endpoint access with token-based authentication
- **High Throughput**: Capable of handling massive concurrent read-requests via FastAPI
- **Low Latency**: Reduced API response latency by offloading document analysis to background workers.
- **Async Processing**: Celery task queue for background document analysis
- **AWS Textract Integration**: Automatic extraction of ID field data (name, DOB, document number, etc.)
- **S3 Storage**: Secure file upload and storage with presigned URLs
- **PostgreSQL Persistence**: Track KYC task status and results
- **Image Validation**: Support for JPEG, PNG, and WebP formats
- **Infrastructure as Code**: Automated AWS provisioning (RDS, EC2, S3) using Terraform
- **Structured Logging**: Comprehensive logging for debugging and monitoring

## Tech Stack

- **Framework**: FastAPI (async web framework)
- **Task Queue**: Celery with Redis
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cloud Services**: AWS Textract, S3
- **Authentication**: PyJWT
- **Server**: Uvicorn
- **Infrastructure**: Terraform, Docker

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
├── terraform/                # Terraform IaC configuration
│   └── main.tf               # AWS infrastructure definitions
└── uploads/                   # Local upload directory (for development)
```
## Architecture Overview
- **Architecture Diagram**

![Kyc-API Architecture](images/kyc-arch.png)

- **Data Flow Diagram**

![Kyc-API DFD](images/kyc-dfd.jpg)

## Live Demo
![GIF](https://github.com/6six7sven/kyc-extraction-api-python-aws-postgresql/blob/terraform/images/api-showcase.gif?raw=true)

## Screenshots
  
  ### Swagger/OpenAPI Documentation
  ![swagger-openapi-doc](images/swagger-openapi-doc.jpg)

  ### Completed Task Status Example
  ![task-status-example](images/task-status-example.jpg)

  ### PostgreSQL Schema
  ![postgresql-schema](images/schema-diagram.jpg)

  ### Github Actions Workflow
  ![github-actions-workflow](images/gh-action-workflow.jpg)

</details>

## Engineering Decisions

**Why FastAPI?**
- FastAPI is built from the ground up to support asynchronous programming (`async`/`await`), which is critical for I/O-bound operations like uploading images to S3 or querying databases. It also provides automatic validation via Pydantic and generates interactive OpenAPI documentation (`/docs`) out of the box, drastically speeding up development and frontend integration.
- **Alternatives:** 
  - *Flask:* Synchronous by default and requires third-party plugins for OpenAPI docs and validation.
  - *Django:* Too heavyweight for a microservice focused purely on providing a REST API.

**Why Celery?**
- AWS Textract processing can take several seconds to complete. If we process the image synchronously, the HTTP request would hang and potentially timeout, creating a poor user experience. Celery allows us to immediately return a `202 Accepted` response with a `task_id`, offloading the heavy OCR processing to background worker nodes.
- **Alternatives Considered:**
  - *RQ (Redis Queue):* Simpler to set up, but less robust than Celery for scaling and complex workflows.
  - *FastAPI BackgroundTasks:* Runs in the same process as the API, meaning a high volume of heavy tasks could crash the API server.

**Why Redis?**
- Celery requires a message broker to pass task messages from the FastAPI web server to the background workers, and a result backend to store the immediate state of those tasks. Redis handles both roles incredibly fast because it is entirely in-memory.
- **Alternatives:**
  - *RabbitMQ:* Excellent for complex message routing, but requires more overhead and setup than Redis.
  - *Amazon SQS:* A great serverless alternative, but introduces cloud vendor lock-in for the message broker and can be slower than in-memory Redis.

**Why PostgreSQL?**
- We need relational integrity to tie Users to their specific KYC Tasks (a 1-to-many relationship). PostgreSQL handles concurrent connections beautifully in production and offers native `JSONB` column types, which is perfect for storing the highly variable, nested JSON structures returned by AWS Textract.
- **Alternatives:**
  - *MongoDB (NoSQL):* Good for storing arbitrary JSON, but less ideal for strict user schema and relational querying.
  - *SQLite:* Used in our pytest environment for speed, but lacks the concurrency handling required for a production API.

**Why Textract instead of traditional OCR (like Tesseract)?**
- Traditional open-source OCR engines (like Tesseract) simply extract raw text strings from an image. We would then have to write complex, error-prone Regex or NLP parsers to figure out which string is the "Name" vs the "Document Number". AWS Textract's `AnalyzeID` API uses machine learning specifically trained on ID documents to automatically return structured Key-Value pairs with confidence scores, eliminating the need for custom parsing logic.
- **Alternatives**
  - *Tesseract OCR:* Free and open-source, but requires heavy image pre-processing (OpenCV) and custom data parsing.
  - *Google Cloud Vision API / Azure AI Document Intelligence:* Comparable managed cloud AI services, but AWS Textract integrates seamlessly with our existing AWS S3 infrastructure.

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
   Copy the example environment file to create your `.env` file:
   ```bash
   cp .env.example .env
   ```
   
   **Important**: Update these values with your actual AWS credentials and database credentials for production use.

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

### Health Check

**GET** `/`
- Health check endpoint
- **Returns**: `{"message": "FastAPI Image Upload Server"}`

### User Registration

**POST** `/register`
- Register a new user account
- **Body**: 
  ```json
  {
    "username": "your_username",
    "password": "your_password"
  }
  ```
- **Returns**: `{"message": "User created successfully"}`
- **Status**: 201 (Created)

### Authentication

**POST** `/token`
- Get JWT access token for authenticated endpoints
- **Body** (form data): `username`, `password`
- **Returns**: 
  ```json
  {
    "access_token": "eyJhbGc...",
    "token_type": "bearer"
  }
  ```

### KYC Document Upload

**POST** `/kyc/upload-id` (Requires authentication)
- Upload and process a government ID document
- **Headers**: `Authorization: Bearer <access_token>`
- **Form Parameters**:
  - `file` (file): Image file (JPEG, PNG, WebP) - Max 5MB
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
- **Headers**: `Authorization: Bearer <access_token>`
- **Returns**: 
  ```json
  {
    "task_id": "celery-task-uuid",
    "user_id": "username",
    "status": "SUCCESS|PENDING|FAILURE",
    "upload_timestamp": "2026-05-31T10:30:00",
    "extracted_fields": { ... }
  }
  ```

### View User Task History

**GET** `/kyc/users/{user_id}/tasks` (Requires authentication)
- Retrieve a history of all past KYC tasks and their extracted data for a specific user
- **Headers**: `Authorization: Bearer <access_token>`
- **Note**: Users can only view their own task history
- **Returns**: 
  ```json
  {
    "user_id": "username",
    "tasks": [
      {
        "task_id": "...",
        "status": "SUCCESS|PENDING|FAILURE",
        "upload_timestamp": "...",
        "extracted_fields": { ... }
      }
    ]
  }
  ```

### Download Uploaded File

**GET** `/uploads/{filename}` (No authentication required)
- Redirect to an S3 presigned URL for the requested file
- **Note**: Presigned URL expires after 1 hour
- **Response**: HTTP 302 redirect to S3 URL

## API Usage Example

```bash
# Register a new user
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "securepassword"}'

# Login and get access token
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=myuser&password=securepassword"

# Save the token (example)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Upload ID document for processing
curl -X POST http://localhost:8000/kyc/upload-id \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/id_photo.jpg"

# Check task status
curl -X GET http://localhost:8000/tasks/abc123def456 \
  -H "Authorization: Bearer $TOKEN"

# View all your past KYC tasks
curl -X GET http://localhost:8000/kyc/users/myuser/tasks \
  -H "Authorization: Bearer $TOKEN"

# Get presigned URL for an uploaded file
curl -X GET http://localhost:8000/uploads/filename.jpg
```

## Security Considerations

- **Password Hashing**: All passwords are hashed using bcrypt before storage
- **JWT Secrets**: Use a strong, randomly generated secret for `SECRET_KEY` in production
- **S3 Presigned URLs**: Generated URLs expire after 1 hour by default
- **HTTPS**: Use HTTPS in production (configure in reverse proxy/load balancer)
- **Rate Limiting**: Consider adding rate limiting middleware for production deployments
- **CORS**: Configure CORS settings in FastAPI for frontend integration

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
- Maximum file size: 5MB

### Task Status Values
- `PENDING`: File uploaded, processing in queue
- `SUCCESS`: Processing completed successfully, extracted data is available
- `FAILURE`: Processing failed, check extracted_fields for error message

### AWS Textract Confidence Threshold
Adjust confidence scoring in `services/ocr_service.py` to filter low-confidence extractions. By default, all extractions are returned with confidence scores for manual filtering.

## Troubleshooting

### Common Issues

**"Could not validate credentials" error**
- Ensure your JWT token is valid and not expired (expires after 30 minutes)
- Include the token in the Authorization header: `Authorization: Bearer <token>`

**"File too large" error**
- Maximum file size is 5MB
- Compress or resize your image and try again

**"Invalid file type" error**
- Only JPEG, PNG, and WebP formats are supported
- Convert your image to one of these formats

**S3 Connection Errors**
- Verify AWS credentials are set in `.env`
- Ensure the IAM user has S3 permissions
- Check S3 bucket name is correct and exists

**Database Connection Errors**
- Ensure PostgreSQL is running on the configured host/port
- Check DATABASE_URL in `.env` is correct
- Verify database credentials are correct

**Celery Worker Not Processing Tasks**
- Ensure Redis is running on the configured REDIS_URL
- Check worker logs: `celery -A worker worker --loglevel=debug`
- Verify AWS Textract credentials are configured

## Development

### Running Tests
```bash
# Install test dependencies (if not already installed)
pip install pytest httpx

# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run specific test file
PYTHONPATH=. pytest tests/test_main.py -v

# Run with coverage report
PYTHONPATH=. pytest tests/ --cov=. --cov-report=html
```

### Code Structure

- **main.py**: FastAPI application with all endpoint definitions
- **worker.py**: Celery worker task definition for background OCR processing
- **config.py**: Application settings and configuration using Pydantic
- **db/database.py**: SQLAlchemy database setup and session management
- **db/models.py**: SQLAlchemy ORM models for KYCTask and User
- **services/ocr_service.py**: AWS Textract integration for ID document processing
- **utils/auth.py**: JWT token creation and validation utilities
- **utils/file_utils.py**: S3 file upload and image validation utilities
- **utils/logger.py**: Structured logging configuration
- **tests/conftest.py**: Pytest configuration and shared test fixtures
- **tests/test_main.py**: API endpoint tests

## Infrastructure

AWS resources are provisioned through Terraform.

The public deployment has been decommissioned to avoid ongoing cloud costs, but the full infrastructure can be recreated using the Terraform configuration included in this repository.

## AWS Setup for Self-Hosting

If you are deploying this API for your own project, you will need to configure the following in your AWS account:

1. **S3 Bucket**: Create a private S3 bucket to store uploaded ID images and extracted JSON data.
2. **IAM User**: Create an IAM User with Programmatic Access (Access Key & Secret Key).
3. **IAM Permissions**: Attach the `AmazonS3FullAccess` and `AmazonTextractFullAccess` policies to your IAM user.
4. Add the IAM credentials and Bucket name to your `.env` file.


## Logging

Logs are output to stdout with timestamps and log levels. Configure logging level in `utils/logger.py`.