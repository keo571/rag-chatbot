from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from typing import List
import chromadb
from pathlib import Path
import traceback

from config.settings import (
    VECTORDB_DIR,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    VECTOR_SEARCH_TOP_K
)

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

    def add_documents(self, documents: List[Document]):
        """Add documents to vector store with metadata.
        
        Args:
            documents: List of documents to add (with metadata already attached)
        """
        # Split documents while preserving metadata
        splits = self.text_splitter.split_documents(documents)
        
        # Update split_id for each chunk
        for i, split in enumerate(splits):
            doc_id = split.metadata["doc_id"]
            split.metadata["split_id"] = f"{doc_id}_{i}"
        
        # Add to vector store
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

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its embeddings from the vector store.
        
        Args:
            document_id: The unique identifier of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Deleting document with ID: {document_id} from vector store")
            collection = self.client.get_collection("documents")
            
            # Query to find all chunks from this document
            results = collection.get(
                where={"doc_id": document_id}
            )
            
            if not results or len(results["ids"]) == 0:
                print(f"No embeddings found for document ID: {document_id}")
                return False
                
            # Delete all chunks associated with this document
            chunk_ids = results["ids"]
            print(f"Found {len(chunk_ids)} chunks to delete for document ID: {document_id}")
            
            collection.delete(
                ids=chunk_ids
            )
            
            print(f"Successfully deleted embeddings for document ID: {document_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting document from vector store: {str(e)}")
            print(traceback.format_exc())
            return False 