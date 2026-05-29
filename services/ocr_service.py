import os
import boto3
from urllib.parse import urlparse

# Initialize AWS clients
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
textract_client = boto3.client('textract', region_name=AWS_REGION)

def process_id_document(file_uri: str) -> dict:
    """
    Instructs AWS Textract to analyze an ID document directly from S3.
    Returns a structured dictionary of the extracted Key-Value pairs.
    """
    # Parse S3 URI
    parsed_uri = urlparse(file_uri)
    bucket = parsed_uri.netloc
    key = parsed_uri.path.lstrip('/')
    
    # Call AWS Textract AnalyzeID
    response = textract_client.analyze_id(
        DocumentPages=[{'S3Object': {'Bucket': bucket, 'Name': key}}]
    )
    
    # Parse the Textract response into a clean dictionary
    extracted_data = {}
    for doc_fields in response.get('IdentityDocuments', []):
        for field in doc_fields.get('IdentityDocumentFields', []):
            field_type = field.get('Type', {}).get('Text', 'UNKNOWN')
            field_value = field.get('ValueDetection', {}).get('Text', '')
            confidence = field.get('ValueDetection', {}).get('Confidence', 0.0)
            
            extracted_data[field_type] = {
                "value": field_value,
                "confidence": float(confidence)
            }
            
    return extracted_data