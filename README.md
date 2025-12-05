# Norrsken Vision App

A Flask application that uses Google Cloud Vision API and Vertex AI to describe images.

## Prerequisites

- Docker
- Google Cloud Project with Vision API and Vertex AI API enabled.
- Google Cloud Application Default Credentials (JSON key file or `gcloud` auth).

## Running with Docker

1. **Build the Image**
   ```bash
   docker build -t norrsken-app .
   ```

2. **Run the Container**
   You need to provide your GCP Project ID and mount your credentials.

   **Option A: Using `gcloud` credentials (local dev)**
   ```bash
   docker run -p 8080:8080 \
     -e PORT=8080 \
     -e GCP_PROJECT=your-project-id \
     -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/application_default_credentials.json \
     -v $HOME/.config/gcloud/application_default_credentials.json:/tmp/keys/application_default_credentials.json:ro \
     norrsken-app
   ```

   **Option B: Using a Service Account Key JSON**
   Assume your key is at `./service-account-key.json`:
   ```bash
   docker run -p 8080:8080 \
     -e PORT=8080 \
     -e GCP_PROJECT=your-project-id \
     -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/key.json \
     -v $(pwd)/service-account-key.json:/tmp/keys/key.json:ro \
     norrsken-app
   ```

### Running Locally with uv

   ```bash
   uv run main.py
   ```

   The app will start on port 8080 (default).

   **Test the endpoint**:
   ```bash
   curl -X POST -F "image=@/path/to/image.jpg" http://localhost:8080/upload
   ```

## Deploy to Google Cloud (Simplest Way)

We have provided a script to automate the setup and deployment to **Cloud Run**.

1. **Login and set your project** (if not already done):
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Run the deploy script**:
   ```bash
   ./deploy.sh
   ```

   This script will:
   - Enable required APIs (Vision, Vertex AI, etc.).
   - Build your container in the cloud.
   - Deploy it to a public HTTPS URL.
