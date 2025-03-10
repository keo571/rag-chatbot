import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional

from models.schemas import DocumentInfo, URLSubmission, DocumentResponse
from services.document import DocumentService
from services.vector_store import VectorStoreService
from config.settings import UPLOAD_DIR

router = APIRouter(prefix="/documents", tags=["documents"])
vector_store_service = VectorStoreService()

@router.post("/upload/file", response_model=DocumentInfo)
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None)
):
    """Upload and process a document file."""
    # Generate unique ID
    doc_id = str(uuid.uuid4())
    
    # Create directory for document
    doc_dir = UPLOAD_DIR / doc_id
    doc_dir.mkdir(exist_ok=True)
    
    try:
        # Save file
        file_path = doc_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Store metadata first
        doc_title = title if title else file.filename
        DocumentService.store_document_metadata(doc_id, doc_title, "file", str(file_path))
        
        # Process document
        loader = DocumentService.get_loader_for_file(str(file_path))
        documents = loader.load()
        
        # Add to vector store with metadata
        vector_store_service.add_documents(documents, str(file_path))
        
        return DocumentInfo(
            id=doc_id,
            title=doc_title,
            source_type="file",
            source_path=str(file_path),
            created_at=""  # Will be filled by DB
        )
    except Exception as e:
        # Clean up on failure
        shutil.rmtree(doc_dir)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/upload/url", response_model=DocumentInfo)
async def upload_url(submission: URLSubmission):
    """Process and add a URL to the knowledge base."""
    doc_id = str(uuid.uuid4())
    
    try:
        # Generate title if not provided
        title = submission.title or DocumentService.get_url_title(submission.url)
        
        # Store metadata first
        DocumentService.store_document_metadata(doc_id, title, "url", submission.url)
        
        try:
            # Process URL
            documents = DocumentService.process_url(submission.url)
            
            # Add to vector store
            vector_store_service.add_documents(documents, submission.url)
            
            return DocumentInfo(
                id=doc_id,
                title=title,
                source_type="url",
                source_path=submission.url,
                created_at=""  # Will be filled by DB
            )
        except Exception as e:
            # If processing fails, clean up the metadata
            DocumentService.delete_document(doc_id)
            raise HTTPException(status_code=400, detail=f"Error processing URL content: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")

@router.get("", response_model=List[DocumentInfo])
async def list_documents():
    """List all documents in the knowledge base."""
    return DocumentService.get_document_metadata()

@router.delete("/{doc_id}", response_model=DocumentResponse)
async def delete_document(doc_id: str):
    """Delete a document from the knowledge base."""
    if DocumentService.delete_document(doc_id):
        return DocumentResponse(
            status="success",
            message=f"Document {doc_id} deleted"
        )
    else:
        raise HTTPException(status_code=404, detail="Document not found") 