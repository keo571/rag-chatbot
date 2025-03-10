from fastapi import APIRouter, HTTPException
from models.schemas import ChatMessage, ChatResponse
from services.chat import ChatService
import traceback

router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()

@router.post("", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Process a chat message using RAG."""
    try:
        if not message.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
            
        result = chat_service.get_response(message.message)
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the full error traceback
        print(f"Error in chat endpoint: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}") 