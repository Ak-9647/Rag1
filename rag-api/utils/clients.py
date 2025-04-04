from google.cloud import aiplatform
from google.cloud import firestore
from google.cloud import secretmanager
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
PROJECT_ID = os.getenv('GCP_PROJECT_ID')
REGION = os.getenv('GCP_REGION', 'us-central1')
COLLECTION_NAME = os.getenv('FIRESTORE_COLLECTION', 'documents')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'textembedding-gecko@latest')
GENERATION_MODEL = os.getenv('GENERATION_MODEL', 'text-bison@latest')
VS_INDEX_ID = os.getenv('VS_INDEX_ID', 'placeholder-index-id')
VS_ENDPOINT_ID = os.getenv('VS_ENDPOINT_ID', 'placeholder-endpoint-id')
VS_DEPLOYED_INDEX_ID = os.getenv('VS_DEPLOYED_INDEX_ID', 'rag_fun_embeddings_deployed')

try:
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=REGION)
    logger.info(f"Initialized Vertex AI with project {PROJECT_ID} in {REGION}")
    
    # Initialize clients
    db = firestore.Client()
    secret_client = secretmanager.SecretManagerServiceClient()
    storage_client = storage.Client()
    
    # Initialize models
    embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
    generation_model = TextGenerationModel.from_pretrained(GENERATION_MODEL)
    
    # Initialize Vector Search endpoint
    vs_index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
        index_endpoint_name=VS_ENDPOINT_ID,
        project=PROJECT_ID,
        location=REGION
    )
    
    logger.info("Successfully initialized all GCP clients and models")
    
except Exception as e:
    logger.error(f"Failed to initialize GCP clients: {str(e)}")
    raise 