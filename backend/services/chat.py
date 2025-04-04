from typing import Dict, Any, List, Optional, Tuple
import traceback
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA, LLMChain
from langchain.schema import BaseRetriever, Document

from config.settings import (
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    LLM_MAX_OUTPUT_TOKENS,
    GOOGLE_API_KEY,
    VECTOR_SEARCH_TOP_K
)
from services.vector_store import VectorStoreService
from services.document import DocumentService

# Define constants for readability
SIMILARITY_THRESHOLD = 0.5
EMPTY_SOURCES = []

class PreFilteredRetriever(BaseRetriever):
    """A retriever that returns a predefined set of documents.
    
    This retriever implements the BaseRetriever interface required by LangChain
    and simply returns documents that were filtered earlier in the process.
    """
    
    filtered_docs: List[Document]
        
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Return the pre-filtered documents regardless of query.
        
        Args:
            query: The query string (not used in this implementation)
            
        Returns:
            The pre-filtered documents
        """
        return self.filtered_docs

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version that returns the pre-filtered documents.
        
        Args:
            query: The query string (not used in this implementation)
            
        Returns:
            The pre-filtered documents
        """
        return self.get_relevant_documents(query)


class ChatService:
    """Service for handling chat interactions using RAG or direct LLM responses."""
    
    def __init__(self):
        """Initialize the chat service with LLM, vector store, and prompt templates."""
        self._initialize_llm()
        self.vector_store_service = VectorStoreService()
        self._setup_prompt_templates()
    
    def _initialize_llm(self):
        """Initialize and test the connection to the LLM."""
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in environment variables")
            
        try:
            self.llm = GoogleGenerativeAI(
                model=LLM_MODEL_NAME,
                google_api_key=GOOGLE_API_KEY,
                temperature=LLM_TEMPERATURE,
                top_p=LLM_TOP_P,
                max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
                convert_system_message_to_human=True
            )
            
            # Test the API connection
            self.llm.invoke("test")
            
        except Exception as e:
            print(f"Error initializing Google API: {str(e)}")
            print("Please check your API key and model settings")
            raise ValueError(f"Failed to initialize Google API: {str(e)}")
    
    def _setup_prompt_templates(self):
        """Set up prompt templates for RAG and direct LLM responses."""
        # Template for RAG responses (using retrieved documents)
        self.prompt_template = PromptTemplate(
            template="""
            You are an AI assistant with access to a knowledge base. 
            Use the following context to answer the question.
            
            Context: {context}
            
            Question: {question}
            
            Answer:
            """,
            input_variables=["context", "question"]
        )

        # Template for direct LLM responses (when no relevant docs found)
        self.direct_prompt_template = PromptTemplate(
            template="""
            Welcome to NetBot! I am an AI assistant. I couldn't find relevant information in my knowledge base for your question, 
            so I'll answer based on my general knowledge.

            Question: {question}

            Answer:
            """,
            input_variables=["question"]
        )

    def get_response(self, message: str) -> Dict[str, Any]:
        """Get response for a chat message using RAG or direct LLM if no relevant docs found.
        
        Args:
            message: The user's chat message/question
            
        Returns:
            Dict containing response text and source information
            
        Raises:
            Exception: If there's an error generating the response
        """
        try:
            # Validate input
            if not message.strip():
                raise ValueError("Message cannot be empty")

            # Check for documents in knowledge base
            if not self._has_documents_in_knowledge_base():
                return self._generate_direct_response(
                    message, 
                    prefix="I don't have any documents in my knowledge base yet, but here's what I know:\n\n"
                )

            # Retrieve and filter relevant documents
            relevant_docs = self._retrieve_relevant_documents(message)
            
            # Fall back to direct LLM if no relevant documents found
            if not relevant_docs:
                return self._generate_direct_response(
                    message,
                    prefix="I couldn't find sufficiently relevant information in my knowledge base, but here's what I know:\n\n"
                )

            # Generate RAG response using relevant documents
            return self._generate_rag_response(message, relevant_docs)

        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            raise Exception(f"Error generating response: {str(e)}")
    
    def _has_documents_in_knowledge_base(self) -> bool:
        """Check if there are any documents in the knowledge base.
        
        Returns:
            True if documents exist, False otherwise
        """
        collection = self.vector_store_service.client.get_collection("documents")
        doc_count = collection.count()
        print(f"Document count in knowledge base: {doc_count}")
        return doc_count > 0
    
    def _retrieve_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve documents relevant to the query from the vector store.
        
        Args:
            query: The user's question/message
            
        Returns:
            List of relevant Document objects
        """
        try:
            print(f"Searching for relevant documents for query: {query}")
            docs_and_scores = self.vector_store_service.vector_store.similarity_search_with_score(
                query,
                k=VECTOR_SEARCH_TOP_K
            )
            
            # Log scores for debugging/tuning
            if docs_and_scores:
                scores = [score for _, score in docs_and_scores]
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                print(f"Document scores - Avg: {avg_score:.4f}, Max: {max_score:.4f}")
                for i, (_, score) in enumerate(docs_and_scores):
                    print(f"  Doc {i+1} score: {score:.4f}")
            
            # Filter documents based on similarity threshold
            relevant_docs = [doc for doc, score in docs_and_scores if score >= SIMILARITY_THRESHOLD]
            print(f"Found {len(relevant_docs)}/{len(docs_and_scores)} documents with score >= {SIMILARITY_THRESHOLD}")
            
            return relevant_docs

        except Exception as e:
            print(f"Error retrieving documents: {str(e)}")
            print(traceback.format_exc())
            return []
    
    def _generate_direct_response(self, question: str, prefix: str = "") -> Dict[str, Any]:
        """Generate a response directly from the LLM (no RAG).
        
        Args:
            question: The user's question
            prefix: Optional prefix to add to the response
            
        Returns:
            Dict with response text and empty sources list
        """
        print("Generating direct LLM response (no RAG)")
        direct_chain = LLMChain(llm=self.llm, prompt=self.direct_prompt_template)
        result = direct_chain.invoke({"question": question})
        
        return {
            "response": prefix + result["text"],
            "sources": EMPTY_SOURCES
        }
    
    def _generate_rag_response(self, question: str, relevant_docs: List[Document]) -> Dict[str, Any]:
        """Generate a response using RAG with the given documents.
        
        Args:
            question: The user's question
            relevant_docs: List of relevant documents to use for generating the response
            
        Returns:
            Dict with response text and source information
        """
        print(f"Generating RAG response with {len(relevant_docs)} documents")
        
        # Create retriever from filtered documents
        retriever = PreFilteredRetriever(filtered_docs = relevant_docs)
        
        # Create and invoke QA chain
        try:
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": self.prompt_template}
            )
            
            print("Invoking QA chain")
            result = qa_chain.invoke({"query": question})
            print("QA chain invocation successful")
            
            # Format response with sources
            sources = self._extract_sources_from_result(result)
            
            return {
                "response": result["result"],
                "sources": sources
            }
            
        except Exception as e:
            print(f"Error in RAG response generation: {str(e)}")
            print(traceback.format_exc())
            
            # Fall back to direct response on RAG failure
            return self._generate_direct_response(
                question, 
                prefix="I encountered an error accessing my knowledge base, but here's what I know:\n\n"
            )
    
    def _extract_sources_from_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and format source information from the QA result.
        
        Args:
            result: The result from the QA chain
            
        Returns:
            List of formatted source information dictionaries
        """
        seen_texts = set()
        sources = []
        
        for doc in result.get("source_documents", []):
            normalized_text = doc.page_content.strip()
            
            # Skip duplicate content
            if normalized_text in seen_texts:
                continue
                
            seen_texts.add(normalized_text)
            
            # Format source info using metadata that is guaranteed to be present
            metadata = doc.metadata
            source_info = {
                "text": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "title": metadata.get("title", "untitled Document"),
                "source_type": metadata.get("source_type", "unknown"),
                "source_path": metadata.get("source_path", ""),
                "doc_id": metadata.get("doc_id", ""),
                "split_id": metadata.get("split_id", "")
            }
            
            sources.append(source_info)
        
        return sources 