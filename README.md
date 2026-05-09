# Document Processing System

A web application for OCR text extraction and translation of scanned documents, plus merging multiple images/PDFs into a single PDF.

Built with **FastAPI** (backend) and **Streamlit** (frontend), powered by **Google Cloud Vision API** and **Google Cloud Translation API**.

---

## Features

### OCR & Translation
- Upload an image (JPG/PNG) or PDF
- Select source and target languages from any pair supported by Cloud Translation API
- Extract text via Google Cloud Vision API
  - Digital PDFs: fast direct extraction
  - Scanned PDFs / images: Vision API OCR
- Edit the extracted text before translating
- Translate with Google Cloud Translation API
- Download the translation result as a `.txt` file

### PDF Compiler
- Upload multiple images (JPG/PNG) and/or PDFs
- Merge them into a single A4-sized PDF in upload order
- Download the compiled PDF

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, Uvicorn |
| Frontend | Python 3.10, Streamlit |
| OCR | Google Cloud Vision API |
| Translation | Google Cloud Translation API v3 |
| PDF processing | PyMuPDF (fitz) |
| Image processing | Pillow |
| Containers | Docker, Docker Compose |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A Google Cloud Platform account
- A GCP project with billing enabled

---

## GCP Setup

### 1. Create or select a GCP project

Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project or select an existing one. Note your **Project ID**.

### 2. Enable the required APIs

In the Cloud Console, navigate to **APIs & Services → Library** and enable:

- **Cloud Vision API**
- **Cloud Translation API**

Or run via `gcloud`:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable vision.googleapis.com translate.googleapis.com
```

### 3. Create a service account

1. Go to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
3. Enter a name (e.g. `docs-helper-sa`) and click **Create and Continue**
4. Assign the following roles:
   - **Editor** (simplest option for personal use)
   - Or for minimal permissions: **Cloud Translation API User** (`roles/cloudtranslate.user`) — Cloud Vision API does not have a dedicated user role; enabling the API for a same-project service account is sufficient
5. Click **Done**

### 4. Download the service account key

1. Click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key → Create new key**
4. Select **JSON** and click **Create**
5. Save the downloaded file — you will place it in the repository as `credentials/gcp-key.json` in the next step

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/docs_helper.git
cd docs_helper
```

### 2. Place the service account key

Create the `credentials/` directory and copy the JSON key you downloaded:

```bash
mkdir credentials
cp /path/to/downloaded-key.json credentials/gcp-key.json
```

> `credentials/` is listed in `.gitignore` and will never be committed.

### 3. Create the `.env` file

Copy the example and fill in your Project ID:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GCP_PROJECT_ID=your-gcp-project-id
```

Replace `your-gcp-project-id` with the **Project ID** from step 1 (e.g. `my-project-123`).

---

## Start with Docker Compose

```bash
docker-compose up --build
```

The first build downloads Python base images and installs dependencies — this may take a few minutes.

To run in the background:

```bash
docker-compose up --build -d
```

To stop:

```bash
docker-compose down
```

---

## Access the App

| Service | URL |
|---|---|
| Streamlit frontend | http://localhost:8501 |
| FastAPI backend (docs) | http://localhost:8000/docs |

---

## Project Structure

```
docs_helper/
├── backend/
│   ├── main.py            # FastAPI app (OCR, translation, PDF endpoints)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py             # Home page
│   ├── pages/
│   │   ├── 1_OCR翻訳.py   # OCR & Translation page
│   │   └── 2_PDFコンパイラ.py  # PDF Compiler page
│   ├── requirements.txt
│   └── Dockerfile
├── credentials/           # Place gcp-key.json here (gitignored)
├── .env                   # Local env vars (gitignored)
├── .env.example
└── docker-compose.yml
```

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `GCP_PROJECT_ID` | Your GCP project ID | `my-project-123` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to the service account key (set automatically by Docker Compose) | `/credentials/gcp-key.json` |
| `BACKEND_URL` | Backend URL used by the frontend (set automatically by Docker Compose) | `http://backend:8000` |
