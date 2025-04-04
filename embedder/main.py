import functions_framework
from google.cloud import firestore
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import logging
import os
import json
import base64
import traceback

# Initialize clients
logging_client = logging.Client()
logger = logging_client.logger('document_embedder')
db = firestore.Client()
storage_client = storage.Client()

# Get environment variables
PROJECT_ID = os.getenv('PROJECT_ID')
REGION = os.getenv('REGION')
GCS_OUTPUT_BUCKET = os.getenv('GCS_OUTPUT_BUCKET')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'textembedding-gecko@latest')

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)
embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

# Define GCS output prefix
gcs_output_prefix = "embeddings/"

@functions_framework.cloud_event
def embed_document_chunk(cloud_event):
    """
    Cloud Function triggered by Pub/Sub message.
    Generates embeddings for document chunks and stores them in GCS.
    """
    try:
        # Decode Pub/Sub message
        try:
            pubsub_message = base64.b64decode(cloud_event.data["data"]).decode("utf-8")
            message_data = json.loads(pubsub_message)
        except Exception as e:
            logger.error(f"Failed to decode Pub/Sub message: {str(e)}")
            raise ValueError("Invalid message format") from e
        
        # Extract required fields
        doc_id = message_data.get("doc_id")
        chunk_id = message_data.get("chunk_id")
        text_to_embed = message_data.get("text")
        firestore_collection = message_data.get("firestore_collection")
        
        if not all([doc_id, chunk_id, text_to_embed, firestore_collection]):
            missing_fields = [field for field, value in {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "text": text_to_embed,
                "firestore_collection": firestore_collection
            }.items() if not value]
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        logger.info(f"Processing chunk {chunk_id} from document {doc_id}")
        
        # Get Firestore chunk document reference
        chunk_ref = db.collection(firestore_collection).document(doc_id).collection('chunks').document(chunk_id)
        
        try:
            # Generate embedding
            embeddings = embedding_model.get_embeddings([text_to_embed])
            
            if not embeddings or not embeddings[0].values:
                raise ValueError("No embedding generated")
                
            embedding_vector = embeddings[0].values
            logger.info(f"Successfully generated embedding for chunk {chunk_id}")
            
            # Update Firestore chunk document
            chunk_ref.update({
                "embedding_status": "completed",
                "embedded_at": firestore.SERVER_TIMESTAMP
            })
            
            # Prepare Vector Search Batch Update format
            embedding_data = {
                "id": chunk_id,
                "embedding": embedding_vector
            }
            
            # Convert to JSONL format
            embedding_jsonl = json.dumps(embedding_data) + "\n"
            
            # Construct GCS blob name
            output_blob_name = f"{gcs_output_prefix}{chunk_id}.jsonl"
            
            # Get GCS bucket and blob
            bucket = storage_client.bucket(GCS_OUTPUT_BUCKET)
            blob = bucket.blob(output_blob_name)
            
            # Upload to GCS
            blob.upload_from_string(
                embedding_jsonl,
                content_type='application/jsonl'
            )
            
            logger.info(f"Successfully uploaded embedding to GCS: {output_blob_name}")
            
        except Exception as e:
            logger.error(
                f"Error processing chunk {chunk_id}: {str(e)}",
                exc_info=True
            )
            
            # Update Firestore with error status
            try:
                chunk_ref.update({
                    "embedding_status": "failed",
                    "error": str(e)
                })
            except Exception as firestore_error:
                logger.error(
                    f"Failed to update Firestore error status: {str(firestore_error)}",
                    exc_info=True
                )
            
            raise
            
    except Exception as e:
        logger.error(f"Error in embed_document_chunk: {str(e)}", exc_info=True)
        raise
