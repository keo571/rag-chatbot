from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from typing import List
import chromadb
from pathlib import Path

from config.settings import (
    VECTORDB_DIR,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    VECTOR_SEARCH_TOP_K
)
from services.document import DocumentService

class VectorStoreService:
    def __init__(self):
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME
        )
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=str(VECTORDB_DIR))
        
        # Create or get the collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.vector_store = Chroma(
            client=self.client,
            collection_name="documents",
            embedding_function=self.embedding_model
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )

    def add_documents(self, documents: List[Document], source_path: str):
        """Add documents to vector store with metadata."""
        splits = self.text_splitter.split_documents(documents)
        
        # Get document metadata
        doc_metadata = DocumentService.get_document_metadata_by_path(source_path)
        if doc_metadata:
            # Add metadata to each split
            for i, split in enumerate(splits):
                # Create unique ID for each split
                split_id = f"{doc_metadata.id}_{i}"
                
                # Prepare metadata for ChromaDB
                metadata = {
                    "title": doc_metadata.title,
                    "source_type": doc_metadata.source_type,
                    "source_path": doc_metadata.source_path,
                    "doc_id": doc_metadata.id,
                    "split_id": split_id
                }
                
                # Update split metadata
                split.metadata = metadata
        
        # Add documents to vector store
        self.vector_store.add_documents(splits)

    def get_retriever(self):
        """Get retriever for similarity search."""
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": VECTOR_SEARCH_TOP_K
            }
        )

    def similarity_search(self, query: str):
        """Perform similarity search."""
        return self.vector_store.similarity_search(
            query,
            k=VECTOR_SEARCH_TOP_K
        ) 