from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from src.app.models.chat import ChatMessage, ChatResponse
from src.app.services.chatbot.graph import get_chat_graph
from typing import AsyncIterator, Dict
import json
from pydantic import BaseModel
import asyncio
from uuid import uuid4

router = APIRouter()

# Store pending confirmations
confirmation_requests: Dict[str, asyncio.Event] = {}
confirmation_responses: Dict[str, bool] = {}


class User(BaseModel):
    id: str


class ConfirmationRequest(BaseModel):
    confirmation_id: str
    confirmed: bool


def get_current_user() -> User:
    """
    TODO: this needs proper filling in if I want to host the app for many users.
    """
    return User(id="test-user-1")


import logging

logging.basicConfig(level=logging.DEBUG)


async def format_stream_response(chunks: AsyncIterator) -> AsyncIterator[str]:
    """Format streaming chunks into SSE format."""
    try:
        async for chunk in chunks:
            logging.debug(f"Raw chunk received: {chunk}")

            if isinstance(chunk, tuple):
                chunk_type, chunk_data = chunk
                logging.debug(
                    f"Processing tuple chunk - type: {chunk_type}, data: {chunk_data}"
                )

                if chunk_type == "messages":
                    # If chunk_data is a tuple, get the first element (the message)
                    message = (
                        chunk_data[0] if isinstance(chunk_data, tuple) else chunk_data
                    )

                    # Check if it's an AIMessage with content
                    if hasattr(message, "content") and message.content:
                        yield (
                            json.dumps({"type": "message", "content": message.content})
                            + "\n"
                        )

                elif chunk_type == "values":
                    # Handle any special values if needed
                    if isinstance(chunk_data, dict) and chunk_data.get("ask_human"):
                        confirmation_id = str(uuid4())
                        yield (
                            json.dumps(
                                {
                                    "type": "confirmation_request",
                                    "confirmation_id": confirmation_id,
                                    "message": "Do you want to proceed with this action?",
                                }
                            )
                            + "\n"
                        )

    except Exception as e:
        logging.error(f"Error in streaming: {str(e)}")
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"
    finally:
        yield json.dumps({"type": "done"}) + "\n"


@router.post("/stream")
async def send_message_stream(
    message: ChatMessage, current_user=Depends(get_current_user)
):
    """Stream the chat response using Server-Sent Events (SSE)."""
    try:
        graph = get_chat_graph(current_user.id)
        chunks = graph.process_message_stream(message.content)
        return StreamingResponse(
            format_stream_response(chunks), media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage, current_user=Depends(get_current_user)):
    """Non-streaming version of the message endpoint."""
    try:
        graph = get_chat_graph(current_user.id)
        final_message = ""
        requires_confirmation = False

        async for chunk in graph.process_message_stream(message.content):
            if isinstance(chunk, tuple):
                stream_type, data = chunk
                if stream_type == "messages":
                    final_message += data[0].content
                elif stream_type == "values":
                    requires_confirmation = data.get("ask_human", False)

        return ChatResponse(
            message=final_message, requires_confirmation=requires_confirmation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_action(
    request: ConfirmationRequest, current_user=Depends(get_current_user)
):
    """Handle user confirmation for actions that require it."""
    if request.confirmation_id in confirmation_requests:
        confirmation_responses[request.confirmation_id] = request.confirmed
        confirmation_requests[request.confirmation_id].set()
        return {"status": "success", "message": "Confirmation received"}
    return {"status": "error", "message": "No pending confirmation found"}
