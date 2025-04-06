# RAG Application

This repository contains a Retrieval-Augmented Generation (RAG) application built with Next.js, Flask, and Google Cloud services.

## Project Structure

- `raggy-frontend/`: Next.js frontend application
- `rag-api/`: Flask backend API
- `embedder/`: Document embedding service
- `chunker/`: Document chunking service
- `processor/`: Document processing service

## Deployment

This project uses Google Cloud Build for continuous integration and deployment. The deployment pipeline is defined in `cloudbuild.yaml`.

### Prerequisites

1. Google Cloud Platform account with the following APIs enabled:
   - Cloud Build
   - Cloud Run
   - Cloud Functions
   - Artifact Registry
   - Cloud Storage
   - Firestore
   - Vertex AI

2. Google Cloud CLI installed and configured

3. Docker installed locally (for testing)

### Deployment Steps

1. **Set up environment variables in Cloud Build**

   Create a Cloud Build trigger and set the following environment variables:
   - `PROJECT_ID`: Your Google Cloud project ID
   - `REGION`: The region where you want to deploy your services (e.g., `us-central1`)

2. **Create Artifact Registry repository**

   The Cloud Build pipeline will create the repository if it doesn't exist, but you can also create it manually:

   ```bash
   gcloud artifacts repositories create rag-fun \
     --repository-format=docker \
     --location=$REGION
   ```

3. **Trigger the build**

   You can trigger the build manually or set up a trigger to run on push to a specific branch:

   ```bash
   gcloud builds submit --config=cloudbuild.yaml
   ```

### What the Pipeline Does

The Cloud Build pipeline performs the following steps:

1. Sets up environment variables
2. Creates an Artifact Registry repository if it doesn't exist
3. Builds and pushes Docker images for:
   - Frontend (Next.js)
   - API (Flask)
   - Embedder service
   - Chunker service
   - Processor service
4. Deploys the frontend and API to Cloud Run
5. Deploys the embedder, chunker, and processor as Cloud Functions
6. Updates environment variables for the deployed services

## Local Development

### Frontend

```bash
cd raggy-frontend
npm install
npm run dev
```

### API

```bash
cd rag-api
pip install -r requirements.txt
python app.py
```

### Embedder, Chunker, and Processor

```bash
cd embedder  # or chunker or processor
pip install -r requirements.txt
python main.py
```

## Environment Variables

### Frontend (.env.local)

```
NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-auth-domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-storage-bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=your-measurement-id
NEXT_PUBLIC_API_URL=https://rag-fun-api-region.a.run.app
```

### API (.env)

```
GCP_PROJECT_ID=your-project-id
GCP_REGION=your-region
FIRESTORE_COLLECTION=documents
EMBEDDING_MODEL=textembedding-gecko@latest
GENERATION_MODEL=text-bison@latest
VS_INDEX_ID=your-index-id
VS_ENDPOINT_ID=your-endpoint-id
VS_DEPLOYED_INDEX_ID=your-deployed-index-id
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 