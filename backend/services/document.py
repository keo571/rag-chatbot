import uuid
from pathlib import Path
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException, UploadFile

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredURLLoader,
    CSVLoader
)

from config.database import get_db, get_dict_cursor
from config.settings import UPLOAD_DIR
from models.schemas import DocumentInfo

class DocumentService:
    @staticmethod
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

    @staticmethod
    def process_url(url: str):
        """Fetch and process content from a URL."""
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid URL format")
        
        try:
            # Fetch content with proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Create a document with the extracted text
            from langchain.docstore.document import Document
            return [Document(page_content=text, metadata={"source": url})]
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing URL: {str(e)}")

    @staticmethod
    def get_url_title(url: str) -> str:
        """Extract title from URL."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to get title from various sources
            title = None
            
            # 1. Try meta title
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title.get('content')
            
            # 2. Try regular title tag
            if not title and soup.title:
                title = soup.title.string.strip()
            
            # 3. Try h1 tag
            if not title:
                h1 = soup.find('h1')
                if h1:
                    title = h1.string.strip()
            
            # 4. If no title found, use URL
            if not title:
                # Clean up URL for display
                title = url.replace('https://', '').replace('http://', '').split('/')[0]
            
            return title
        except Exception as e:
            print(f"Error extracting title from URL: {str(e)}")
            # Clean up URL for display
            return url.replace('https://', '').replace('http://', '').split('/')[0]

    @staticmethod
    def store_document_metadata(doc_id: str, title: str, source_type: str, source_path: str):
        """Store document metadata in database."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (id, title, source_type, source_path) VALUES (?, ?, ?, ?)",
                (doc_id, title, source_type, source_path)
            )
            conn.commit()

    @staticmethod
    def get_document_metadata(doc_id: Optional[str] = None) -> List[DocumentInfo]:
        """Retrieve document metadata from database."""
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

    @staticmethod
    def get_document_metadata_by_path(source_path: str) -> Optional[DocumentInfo]:
        """Retrieve document metadata by source path."""
        with get_db() as conn:
            cursor = get_dict_cursor(conn)
            cursor.execute("SELECT * FROM documents WHERE source_path = ?", (source_path,))
            result = cursor.fetchone()
            return DocumentInfo(**result) if result else None

    @staticmethod
    def delete_document(doc_id: str) -> bool:
        """Delete document and its metadata."""
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