import os
import logging
import functools
import json
from flask import request, jsonify, g
import firebase_admin
from firebase_admin import credentials, auth
from .clients import secret_client

# Configure logging
logger = logging.getLogger(__name__)

# Firebase Admin SDK initialization
try:
    # Get Firebase credentials from Secret Manager
    FIREBASE_CREDENTIALS_SECRET = os.getenv('FIREBASE_CREDENTIALS_SECRET')
    SECRET_VERSION = os.getenv('SECRET_VERSION', 'latest')
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
    
    if not all([FIREBASE_CREDENTIALS_SECRET, GCP_PROJECT_ID]):
        raise ValueError("Missing required environment variables for Firebase initialization")
    
    # Access the secret
    secret_name = f"projects/{GCP_PROJECT_ID}/secrets/{FIREBASE_CREDENTIALS_SECRET}/versions/{SECRET_VERSION}"
    response = secret_client.access_secret_version(request={"name": secret_name})
    credentials_json = response.payload.data.decode("UTF-8")
    
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(json.loads(credentials_json))
    firebase_admin.initialize_app(cred)
    logger.info("Successfully initialized Firebase Admin SDK")
    
except Exception as e:
    logger.critical(f"Failed to initialize Firebase Admin SDK: {str(e)}")
    raise

def firebase_auth_required(f):
    """
    Decorator to verify Firebase ID tokens.
    Attaches the decoded token to Flask's g object.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
            
        id_token = auth_header.split('Bearer ')[1]
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token, check_revoked=True)
            
            # Attach the decoded token to Flask's g object
            g.user = decoded_token
            
            return f(*args, **kwargs)
            
        except auth.ExpiredIdTokenError:
            return jsonify({"error": "Token has expired"}), 401
            
        except auth.InvalidIdTokenError:
            return jsonify({"error": "Invalid token"}), 401
            
        except auth.RevokedIdTokenError:
            return jsonify({"error": "Token has been revoked"}), 401
            
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return jsonify({"error": "Authentication failed"}), 401
            
    return decorated_function 