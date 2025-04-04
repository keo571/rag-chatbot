import uuid
from pathlib import Path
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException, UploadFile
import traceback

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredURLLoader,
    CSVLoader
)
from langchain.docstore.document import Document

from config.database import get_db, get_dict_cursor
from config.settings import UPLOAD_DIR
from models.schemas import DocumentInfo
from services.vector_store import VectorStoreService

class DocumentService:
    """Service for managing documents in the knowledge base.
    
    This service handles:
    - Document loading and processing (files and URLs)
    - Document metadata management
    - Document deletion and cleanup
    """
    
    # ==========================================
    # Document Loading and Processing
    # ==========================================
    
    @staticmethod
    def get_loader_for_file(file_path: str, metadata: DocumentInfo):
        """Return appropriate document loader based on file extension.
        
        Args:
            file_path: Path to the file to load
            metadata: Document metadata to attach to the documents
            
        Returns:
            A LangChain document loader appropriate for the file type
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Create base metadata
        doc_metadata = {
            "title": metadata.title,
            "source_type": metadata.source_type,
            "source_path": metadata.source_path,
            "doc_id": metadata.id,
            "split_id": ""  # Will be set in vector_store.add_documents for each chunk
        }
        
        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_ext in [".docx", ".doc"]:
            loader = Docx2txtLoader(file_path)
        elif file_ext == ".csv":
            loader = CSVLoader(file_path)
        else:  # Default to text loader for .txt and others
            loader = TextLoader(file_path)
        
        # Add metadata to the loader's document creation process
        original_load = loader.load
        def load_with_metadata():
            docs = original_load()
            for doc in docs:
                doc.metadata.update(doc_metadata)
            return docs
        loader.load = load_with_metadata
        
        return loader

    @staticmethod
    def process_url(url: str, metadata: DocumentInfo) -> List[Document]:
        """Fetch and process content from a URL.
        
        Args:
            url: The URL to process
            metadata: Document metadata to attach to the document
            
        Returns:
            List containing a single Document with the processed URL content
            
        Raises:
            HTTPException: If URL processing fails
            ValueError: If URL format is invalid
        """
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid URL format")
        
        try:
            # Fetch and process content as before
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Use the provided metadata
            doc_metadata = {
                "title": metadata.title,
                "source_type": metadata.source_type,
                "source_path": metadata.source_path,
                "doc_id": metadata.id,
                "split_id": f"{metadata.id}_0"  # Since URL content is one document
            }
            
            return [Document(page_content=text, metadata=doc_metadata)]
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing URL: {str(e)}")

    @staticmethod
    def get_url_title(url: str) -> str:
        """Extract title from URL for better document organization and user experience.
        
        This method serves two main purposes:
        1. User Experience: Provides meaningful titles in the UI instead of raw URLs
           (e.g., "How to Implement RAG" instead of "https://example.com/article/123")
        2. Fallback Mechanism: Automatically generates a title when user doesn't provide one
           during URL submission
        
        Args:
            url: The URL to extract title from
            
        Returns:
            str: Extracted title from meta tags, title tag, h1, or cleaned URL as fallback
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = None
            
            # Try different sources for title in order of preference
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title.get('content')
            
            if not title and soup.title:
                title = soup.title.string.strip()
            
            if not title:
                h1 = soup.find('h1')
                if h1:
                    title = h1.string.strip()
            
            if not title:
                title = url.replace('https://', '').replace('http://', '').split('/')[0]
            
            return title
            
        except Exception as e:
            print(f"Error extracting title from URL: {str(e)}")
            return url.replace('https://', '').replace('http://', '').split('/')[0]

    # ==========================================
    # Metadata Management
    # ==========================================

    @staticmethod
    def _infer_source_type(source_path: str) -> str:
        """Infer the source type from the source path.
        
        Args:
            source_path: Path to the source (file path or URL)
            
        Returns:
            str: One of 'url', 'pdf', 'doc', 'csv', 'text' based on the source
        """
        if source_path.startswith(('http://', 'https://')):
            return 'url'
        
        file_ext = Path(source_path).suffix.lower()
        source_type_map = {
            '.pdf': 'pdf',
            '.doc': 'doc',
            '.docx': 'doc',
            '.csv': 'csv',
            '.txt': 'text',
        }
        
        return source_type_map.get(file_ext, 'text')

    @staticmethod
    def store_document_metadata(metadata: DocumentInfo):
        """Store document metadata in database.
        
        Args:
            metadata: The DocumentInfo object to store
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (id, title, source_type, source_path, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    metadata.id,
                    metadata.title,
                    metadata.source_type,
                    metadata.source_path,
                    metadata.created_at  # Already in string format
                )
            )
            conn.commit()

    @staticmethod
    def get_document_metadata(doc_id: Optional[str] = None) -> List[DocumentInfo]:
        """Retrieve document metadata from database.
        
        Args:
            doc_id: Optional document ID to retrieve specific document
            
        Returns:
            List of DocumentInfo objects, either all documents or a single document if doc_id provided
        """
        with get_db() as conn:
            cursor = get_dict_cursor(conn)
            
            if doc_id:
                cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
                result = cursor.fetchone()
                return [DocumentInfo(**result)] if result else []
            else:
                cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
                results = cursor.fetchall()
                return [DocumentInfo(**row) for row in results]

    # ==========================================
    # Document Deletion
    # ==========================================

    @staticmethod
    def delete_document(doc_id: str) -> bool:
        """Delete a document from the system including database and vector store.
        
        Args:
            doc_id: The unique identifier of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = DocumentService._delete_document_from_database(doc_id)
            if not success:
                return False
            
            vector_store_service = VectorStoreService()
            vector_store_success = vector_store_service.delete_document(doc_id)
            
            if not vector_store_success:
                print(f"Warning: Document deleted from database but not from vector store: {doc_id}")
            
            return True
            
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            print(traceback.format_exc())
            return False

    @staticmethod
    def _delete_document_from_database(doc_id: str) -> bool:
        """Delete document and its metadata from the database.
        
        Also removes the physical file if it exists.
        
        Args:
            doc_id: The document ID to delete
            
        Returns:
            True if successful, False if document not found
        """
        docs = DocumentService.get_document_metadata(doc_id)
        if not docs:
            return False

        doc = docs[0]
        if doc.source_type == "file":
            try:
                file_path = Path(doc.source_path)
                if file_path.exists():
                    file_path.unlink()
                    if file_path.parent.exists() and not any(file_path.parent.iterdir()):
                        file_path.parent.rmdir()
            except Exception as e:
                print(f"Error deleting file: {str(e)}")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        
        return True 