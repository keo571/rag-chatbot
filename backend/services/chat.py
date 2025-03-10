from typing import Dict, Any, List
import traceback
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

from config.settings import (
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    LLM_MAX_OUTPUT_TOKENS,
    GOOGLE_API_KEY
)
from services.vector_store import VectorStoreService
from services.document import DocumentService

class ChatService:
    def __init__(self):
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
        
        self.vector_store_service = VectorStoreService()
        
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

    def get_response(self, message: str) -> Dict[str, Any]:
        """Get response for a chat message using RAG."""
        try:
            if not message.strip():
                raise ValueError("Message cannot be empty")

            # Create QA chain with basic configuration
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store_service.get_retriever(),
                return_source_documents=True,
                chain_type_kwargs={"prompt": self.prompt_template}
            )
            
            try:
                # Get response using invoke
                result = qa_chain.invoke({"query": message})
            except Exception as e:
                print(f"Error getting response from model: {str(e)}")
                raise ValueError(f"Error getting response from model: {str(e)}")
            
            if not result or "result" not in result:
                raise ValueError("No response generated from the model")
            
            # Format response with unique sources
            seen_texts = set()  # Track unique source texts
            sources = []
            
            for doc in result.get("source_documents", []):
                # Create a normalized version of the text for comparison
                normalized_text = doc.page_content.strip()
                
                # Skip if we've seen this text before
                if normalized_text in seen_texts:
                    continue
                    
                seen_texts.add(normalized_text)
                
                # Get source information from metadata
                metadata = doc.metadata or {}
                source_info = {
                    "text": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "title": metadata.get("title", "Untitled"),
                    "source_type": metadata.get("source_type", "unknown"),
                    "source_path": metadata.get("source_path", ""),
                    "doc_id": metadata.get("doc_id", ""),
                    "split_id": metadata.get("split_id", "")
                }
                
                # If title is missing, try to get it from the document service
                if source_info["title"] == "Untitled":
                    doc_metadata = DocumentService.get_document_metadata_by_path(source_info["source_path"])
                    if doc_metadata:
                        source_info["title"] = doc_metadata.title
                
                sources.append(source_info)
            
            return {
                "response": result["result"],
                "sources": sources
            }
        except Exception as e:
            # Log the full error traceback
            print(f"Error in get_response: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            raise Exception(f"Error generating response: {str(e)}") 