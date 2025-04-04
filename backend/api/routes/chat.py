from fastapi import APIRouter, HTTPException
from models.schemas import ChatMessage, ChatResponse
from services.chat import ChatService
import traceback

router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()

@router.post("", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Process a chat message and return a response."""
    try:
        # Validate input
        if not message.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Message content cannot be empty"
            )

        # Get response from chat service
        response = chat_service.get_response(message.message)
        
        # Validate response
        if not response or "response" not in response:
            raise HTTPException(
                status_code=500,
                detail="Invalid response from chat service"
            )

        return ChatResponse(
            response=response["response"],
            sources=response.get("sources", [])
        )

    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        
        # Return a more graceful error response
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        ) 