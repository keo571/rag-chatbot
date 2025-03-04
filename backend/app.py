import os
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import uuid
import shutil
import requests
from bs4 import BeautifulSoup
import tempfile
import urllib.parse
import sqlite3

# Vector database and embedding imports
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Document loaders
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredURLLoader,
    CSVLoader
)

# Document splitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

# LLM imports
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA


# Initialize FastAPI app
app = FastAPI(title="RAG Chatbot API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to store uploaded files
UPLOAD_DIR = Path("./uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)

# Directory for vector database
VECTORDB_DIR = Path("./vectordb")
VECTORDB_DIR.mkdir(exist_ok=True)

# SQLite database for metadata
DB_PATH = "./knowledge_base.db"

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT,
        source_type TEXT,
        source_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# Initialize embeddings model
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Initialize vector store
vector_store = Chroma(
    persist_directory=str(VECTORDB_DIR),
    embedding_function=embedding_model
)

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# Load environment variables from .env file
load_dotenv()

# LLM initialization
llm = GoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.5,
    top_p=0.85,
    max_output_tokens=2048,
)

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []

class DocumentInfo(BaseModel):
    id: str
    title: str
    source_type: str
    source_path: str
    created_at: str

class URLSubmission(BaseModel):
    url: str
    title: Optional[str] = None

# Helper functions
def get_loader_for_file(file_path: str):
    """Return appropriate document loader based on file extension."""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == ".pdf":
        return PyPDFLoader(file_path)
    elif file_ext in [".docx", ".doc"]:
        return Docx2txtLoader(file_path)
    elif file_ext == ".csv":
        return CSVLoader(file_path)
    else:  # Default to text loader for .txt and others
        return TextLoader(file_path)

def process_url(url: str):
    """Fetch and process content from a URL."""
    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL format")
    
    try:
        # Fetch URL content
        loader = UnstructuredURLLoader(urls=[url])
        documents = loader.load()
        return documents
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing URL: {str(e)}")

def store_document_metadata(doc_id: str, title: str, source_type: str, source_path: str):
    """Store document metadata in SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (id, title, source_type, source_path) VALUES (?, ?, ?, ?)",
        (doc_id, title, source_type, source_path)
    )
    conn.commit()
    conn.close()

def get_document_metadata(doc_id: str = None):
    """Retrieve document metadata from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if doc_id:
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
    else:
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

# API endpoints
@app.post("/upload/file", response_model=DocumentInfo)
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(None)
):
    """Upload and process a document file."""
    # Generate unique ID for the document
    doc_id = str(uuid.uuid4())
    
    # Create directory for this document
    doc_dir = UPLOAD_DIR / doc_id
    doc_dir.mkdir(exist_ok=True)
    
    # Save the file
    file_path = doc_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        # Get appropriate loader
        loader = get_loader_for_file(str(file_path))
        documents = loader.load()
        
        # Split documents
        splits = text_splitter.split_documents(documents)
        
        # Add to vector store
        vector_store.add_documents(splits)
        
        # Store metadata
        doc_title = title if title else file.filename
        store_document_metadata(doc_id, doc_title, "file", str(file_path))
        
        return {
            "id": doc_id,
            "title": doc_title,
            "source_type": "file",
            "source_path": str(file_path),
            "created_at": "" # This will be filled by DB default
        }
    except Exception as e:
        # Clean up on failure
        shutil.rmtree(doc_dir)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/upload/url", response_model=DocumentInfo)
async def upload_url(submission: URLSubmission):
    """Process and add a URL to the knowledge base."""
    doc_id = str(uuid.uuid4())
    
    try:
        # Process the URL
        documents = process_url(submission.url)
        
        # Split documents
        splits = text_splitter.split_documents(documents)
        
        # Add to vector store
        vector_store.add_documents(splits)
        vector_store.persist()
        
        # Generate title if not provided
        title = submission.title
        if not title:
            try:
                response = requests.get(submission.url)
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else submission.url
            except:
                title = submission.url
        
        # Store metadata
        store_document_metadata(doc_id, title, "url", submission.url)
        
        return {
            "id": doc_id,
            "title": title,
            "source_type": "url",
            "source_path": submission.url,
            "created_at": "" # This will be filled by DB default
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Process a chat message using RAG."""
    try:
        # Create a retriever from the vector store
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        
        # Create a prompt template
        prompt_template = """
        You are an AI assistant with access to a knowledge base. 
        Use the following context to answer the question.
        
        Context: {context}
        
        Question: {question}
        
        Answer:
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create the RAG chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
        # Run the chain
        result = qa_chain({"query": message.message})
        
        # Extract answer and sources
        answer = result["result"]
        source_documents = result.get("source_documents", [])
        
        # Format sources info
        sources = []
        for doc in source_documents:
            source_info = {
                "text": doc.page_content[:200] + "...",
                "metadata": doc.metadata
            }
            sources.append(source_info)
        
        return {
            "response": answer,
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all documents in the knowledge base."""
    return get_document_metadata()

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the knowledge base."""
    # Get document metadata
    doc_info = get_document_metadata(doc_id)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store (this is simplified - in production you'd need a more robust approach)
    # For proper deletion, you'd need to track document IDs in the vector store
    
    # Delete the file if it's a local file
    if doc_info["source_type"] == "file":
        try:
            file_path = Path(doc_info["source_path"])
            if file_path.exists():
                file_path.unlink()
                # Also try to remove parent dir if it's empty
                if file_path.parent.exists() and not any(file_path.parent.iterdir()):
                    file_path.parent.rmdir()
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
    
    # Delete from SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Document {doc_id} deleted"}

# For running the app
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
