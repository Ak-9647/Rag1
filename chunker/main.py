import functions_framework
from google.cloud import firestore
from google.cloud import pubsub_v1
from google.cloud import logging
import os
import json
import base64
import uuid
from typing import List, Dict, Any, Optional

# Initialize clients
logging_client = logging.Client()
logger = logging_client.logger('document_chunker')
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

# Get environment variables
PROJECT_ID = os.getenv('PROJECT_ID')
EMBED_TOPIC = os.getenv('EMBED_TOPIC')
FIRESTORE_COLLECTION = os.getenv('FIRESTORE_COLLECTION')
embed_topic_name = f"projects/{PROJECT_ID}/topics/{EMBED_TOPIC}"

def simple_chunker(text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
    """
    Simple text chunking implementation.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        if end >= text_length:
            chunks.append(text[start:])
            break
            
        # Try to find a good breaking point (space or newline)
        while end < text_length and text[end] not in [' ', '\n']:
            end -= 1
            
        if end == start:  # No good breaking point found
            end = start + chunk_size  # Force break at chunk_size
            
        chunks.append(text[start:end])
        start = end - chunk_overlap
        
    return chunks

# Example of LangChain chunker (commented out for future use)
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter

def langchain_chunker(text: str) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)
"""

@functions_framework.cloud_event
def chunk_document(cloud_event):
    """
    Cloud Function triggered by Pub/Sub message.
    Chunks document text and publishes chunks for embedding.
    """
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["data"]).decode("utf-8")
        message_data = json.loads(pubsub_message)
        
        # Extract required fields
        file_name = message_data.get("file_name")
        bucket_name = message_data.get("bucket_name")
        text_content = message_data.get("text")
        
        if not all([file_name, bucket_name, text_content]):
            missing_fields = [field for field, value in {
                "file_name": file_name,
                "bucket_name": bucket_name,
                "text_content": text_content
            }.items() if not value]
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
        logger.info(f"Processing document: {file_name} from bucket: {bucket_name}")
        
        # Generate document reference ID
        doc_ref_id = f"{bucket_name}/{file_name}".replace("/", "_")
        
        # Get Firestore document reference
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(doc_ref_id)
        
        # Set initial metadata
        doc_ref.set({
            "file_name": file_name,
            "bucket_name": bucket_name,
            "processed_at": firestore.SERVER_TIMESTAMP,
            "status": "chunking"
        }, merge=True)
        
        # Chunk the text
        chunks = simple_chunker(text_content)
        chunk_count = len(chunks)
        
        # Update document with chunk count
        doc_ref.update({
            "chunk_count": chunk_count
        })
        
        # Get chunks subcollection reference
        chunks_collection_ref = doc_ref.collection('chunks')
        
        # Track publish results
        publish_successes = 0
        publish_failures = 0
        
        # Process each chunk
        for chunk_index, chunk_text in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chunk_ref = chunks_collection_ref.document(chunk_id)
            
            # Set chunk data
            chunk_ref.set({
                "chunk_index": chunk_index,
                "text": chunk_text,
                "embedding_status": "pending",
                "created_at": firestore.SERVER_TIMESTAMP
            })
            
            # Prepare embedding message
            embedding_message = {
                "doc_id": doc_ref_id,
                "chunk_id": chunk_id,
                "text": chunk_text,
                "firestore_collection": FIRESTORE_COLLECTION
            }
            
            try:
                # Publish to Pub/Sub
                future = publisher.publish(
                    embed_topic_name,
                    json.dumps(embedding_message).encode("utf-8")
                )
                future.result()  # Wait for confirmation
                publish_successes += 1
                
            except Exception as e:
                logger.error(f"Failed to publish chunk {chunk_id}: {str(e)}")
                publish_failures += 1
                # Update chunk status
                chunk_ref.update({
                    "embedding_status": "failed_publish",
                    "error": str(e)
                })
        
        # Update document status
        final_status = "embedding" if publish_failures == 0 else "partially_failed_embedding"
        doc_ref.update({
            "status": final_status,
            "publish_successes": publish_successes,
            "publish_failures": publish_failures
        })
        
        logger.info(
            f"Completed chunking {file_name}: {chunk_count} chunks, "
            f"{publish_successes} published successfully, {publish_failures} failed"
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise 