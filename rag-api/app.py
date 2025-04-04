from flask import Flask, jsonify, request, g
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
import uuid
from datetime import datetime, timedelta
from google.cloud import firestore
from utils.clients import (
    db, 
    embedding_model, 
    generation_model, 
    vs_index_endpoint, 
    storage_client,
    COLLECTION_NAME,
    VS_DEPLOYED_INDEX_ID
)
from utils.auth import firebase_auth_required

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all API routes
# Note: In production, restrict origins to specific domains
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Define the upload bucket name
UPLOAD_BUCKET_NAME = "rag-fun-documents"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route('/api/query', methods=['POST'])
@firebase_auth_required
def query():
    """
    RAG query endpoint that:
    1. Embeds the user query
    2. Searches for similar vectors
    3. Retrieves relevant chunks
    4. Generates an answer using the LLM
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        query_text = data.get('query')
        
        if not query_text:
            return jsonify({"error": "Missing 'query' field in request"}), 400
            
        # Get authenticated user ID
        user_id = g.user['uid']
        logger.info(f"Processing query from user: {user_id}")
        
        # Step 1: Embed the query
        logger.info("Generating query embedding")
        embeddings = embedding_model.get_embeddings([query_text])
        
        if not embeddings or not embeddings[0].values:
            return jsonify({"error": "Failed to generate query embedding"}), 500
            
        query_embedding = embeddings[0].values
        logger.info("Successfully generated query embedding")
        
        # Step 2: Search for similar vectors
        logger.info("Searching for similar vectors")
        # Note: In production, ensure VS_DEPLOYED_INDEX_ID is properly configured
        search_response = vs_index_endpoint.find_neighbors(
            deployed_index_id=VS_DEPLOYED_INDEX_ID,
            queries=[query_embedding],
            num_neighbors=5
        )
        
        logger.info(f"Vector search response received")
        
        # Check if search response is valid
        if not search_response or not search_response[0]:
            logger.warning("No results returned from vector search")
            return jsonify({"answer": "Could not find relevant information to answer your query."}), 200
            
        # Get the list of neighbor objects
        neighbors = search_response[0]
        
        # Extract chunk IDs using list comprehension
        neighbor_ids = [neighbor.id for neighbor in neighbors]
        
        # Check if neighbor_ids is empty
        if not neighbor_ids:
            logger.warning("No neighbor IDs found in search response")
            return jsonify({"answer": "Could not find relevant information to answer your query."}), 200
            
        logger.info(f"Found {len(neighbor_ids)} relevant chunks: {neighbor_ids}")
        
        # Step 3: Retrieve chunks from Firestore using collection group query
        chunks = []
        retrieved_chunks_map = {}
        
        try:
            # Use collection group query to find chunks by ID
            chunk_query = db.collection_group('chunks').where(
                firestore.FieldPath.document_id(), 'in', neighbor_ids
            )
            
            # Stream the results
            stream = chunk_query.stream()
            
            # Process each document in the stream
            for chunk_doc in stream:
                if chunk_doc.exists:
                    chunk_data = chunk_doc.to_dict()
                    retrieved_chunks_map[chunk_doc.id] = {
                        'id': chunk_doc.id,
                        'text': chunk_data.get('text', '')
                    }
                else:
                    logger.warning(f"Document reference exists but document does not: {chunk_doc.id}")
            
            # Create final chunks list preserving the relevance order from Vector Search
            for chunk_id in neighbor_ids:
                if chunk_id in retrieved_chunks_map:
                    chunks.append(retrieved_chunks_map[chunk_id])
                else:
                    logger.warning(f"Chunk {chunk_id} not found in Firestore")
                    
        except Exception as e:
            logger.error(f"Error retrieving chunks from Firestore: {str(e)}", exc_info=True)
            return jsonify({"error": "Failed to retrieve relevant information from the database"}), 500
            
        # Check if any chunks were retrieved
        if not chunks:
            logger.warning("No chunks retrieved from Firestore")
            return jsonify({"answer": "Found potentially relevant documents, but could not retrieve the specific details."}), 200
            
        logger.info(f"Retrieved {len(chunks)} chunks from Firestore")
        
        # Step 4: Construct prompt
        context_string = "\n\n".join([chunk["text"] for chunk in chunks])
        
        prompt = f"""
        You are a helpful assistant that answers questions based on the provided context.
        Answer the following question using ONLY the information in the context below.
        If the context doesn't contain relevant information to answer the question, say "I don't have enough information to answer this question."
        Do not make up information or use knowledge outside the provided context.
        
        Context:
        {context_string}
        
        Question: {query_text}
        
        Answer:
        """
        
        # Step 5: Generate answer
        logger.info("Generating answer with LLM")
        response = generation_model.predict(
            prompt,
            temperature=0.2,
            max_output_tokens=1024
        )
        
        answer = response.text
        logger.info("Successfully generated answer")
        
        # Step 6: Return response
        return jsonify({
            "answer": answer,
            "context_chunks": [chunk["id"] for chunk in chunks]  # For debugging/transparency
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing your query"}), 500

@app.route('/api/generate_upload_url', methods=['POST'])
@firebase_auth_required
def generate_upload_url():
    """
    Generate a signed URL for uploading files directly to Google Cloud Storage.
    This endpoint requires Firebase authentication.
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        file_name = data.get('fileName')
        content_type = data.get('contentType')
        
        if not file_name or not content_type:
            return jsonify({"error": "Missing 'fileName' or 'contentType' in request"}), 400
            
        # Get authenticated user ID
        user_id = g.user['uid']
        logger.info(f"Generating upload URL for user: {user_id}, file: {file_name}")
        
        # Get the bucket
        bucket = storage_client.bucket(UPLOAD_BUCKET_NAME)
        
        # Create a unique blob name to prevent collisions
        # Format: user_id/uuid-filename
        blob_name = f"{user_id}/{uuid.uuid4()}-{file_name}"
        
        # Get the blob
        blob = bucket.blob(blob_name)
        
        # Generate signed URL
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=content_type
        )
        
        logger.info(f"Generated signed URL for blob: {blob_name}")
        
        return jsonify({
            "signedUrl": signed_url,
            "blobName": blob_name
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating signed URL: {str(e)}")
        return jsonify({"error": "Failed to generate upload URL"}), 500

if __name__ == '__main__':
    # Run the app locally on port 8080
    app.run(host='0.0.0.0', port=8080, debug=True) 