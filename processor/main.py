import functions_framework
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import logging
import os
import json
from typing import Optional

# Initialize clients
logging_client = logging.Client()
logger = logging_client.logger('document_processor')
storage_client = storage.Client()
publisher = pubsub_v1.PublisherClient()

# Get environment variables
PROJECT_ID = os.getenv('PROJECT_ID')
CHUNK_TOPIC = os.getenv('CHUNK_TOPIC')
chunk_topic_name = f"projects/{PROJECT_ID}/topics/{CHUNK_TOPIC}"

def extract_text(bucket_name: str, file_name: str) -> Optional[str]:
    """
    Download and extract text from a document stored in Cloud Storage.
    
    Args:
        bucket_name: Name of the GCS bucket
        file_name: Name of the file in the bucket
        
    Returns:
        Extracted text as string or None if extraction fails
    """
    try:
        # Download file to /tmp/
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        local_path = f"/tmp/{file_name}"
        blob.download_to_filename(local_path)
        
        # Get file extension
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        # Extract text based on file type
        text = None
        if ext == '.pdf':
            # TODO: Implement PDF text extraction
            # from pypdf import PdfReader
            pass
        elif ext in ['.docx', '.doc']:
            # TODO: Implement DOCX text extraction
            # from docx import Document
            pass
        elif ext == '.txt':
            # TODO: Implement TXT text extraction
            with open(local_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext == '.md':
            # TODO: Implement Markdown text extraction
            # import markdown
            pass
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return None
            
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from {file_name}: {str(e)}")
        return None
        
    finally:
        # Clean up temporary file
        if os.path.exists(local_path):
            os.remove(local_path)

@functions_framework.cloud_event
def process_document(cloud_event):
    """
    Cloud Function triggered by Cloud Storage event.
    Extracts text from uploaded documents and publishes to Pub/Sub.
    """
    try:
        # Extract bucket and file information from the event
        data = cloud_event.data
        bucket_name = data["bucket"]
        file_name = data["name"]
        
        logger.info(f"Processing document: {file_name} from bucket: {bucket_name}")
        
        # Extract text from the document
        text = extract_text(bucket_name, file_name)
        
        if text:
            # Prepare message data
            message_data = {
                "file_name": file_name,
                "bucket_name": bucket_name,
                "content_type": data.get("contentType", "application/octet-stream"),
                "text": text
            }
            
            # Publish to Pub/Sub
            future = publisher.publish(
                chunk_topic_name,
                json.dumps(message_data).encode("utf-8")
            )
            future.result()  # Wait for message to be published
            
            logger.info(f"Successfully processed and published {file_name}")
        else:
            logger.warning(f"Failed to extract text from {file_name}")
            
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise 