from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ChatMessage(BaseModel):
    """Schema for chat messages."""
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    """Schema for chat responses."""
    response: str
    sources: List[Dict[str, Any]] = []

class DocumentInfo(BaseModel):
    """Schema for document information."""
    id: str
    title: str
    source_type: str
    source_path: str
    created_at: str

class URLSubmission(BaseModel):
    """Schema for URL submissions."""
    url: str
    title: Optional[str] = None

class DocumentResponse(BaseModel):
    """Schema for document operation responses."""
    status: str
    message: str 