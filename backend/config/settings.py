import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploaded_files"
VECTORDB_DIR = BASE_DIR / "vectordb"
DB_PATH = BASE_DIR / "knowledge_base.db"

# Create necessary directories
UPLOAD_DIR.mkdir(exist_ok=True)
VECTORDB_DIR.mkdir(exist_ok=True)

# API Configuration
CORS_ORIGINS = ["*"]  # Update this in production

# Model Configuration
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL_NAME = "gemini-1.5-flash-latest"
LLM_TEMPERATURE = 0.7
LLM_TOP_P = 0.9
LLM_MAX_OUTPUT_TOKENS = 2048

# Document Processing Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Vector Store Configuration
VECTOR_SEARCH_TOP_K = 3 