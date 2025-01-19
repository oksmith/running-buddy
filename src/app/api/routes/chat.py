import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel

from src.app.models.chat import ChatMessage, ChatResponse
from src.app.services.chatbot.graph import get_chat_graph

logging.basicConfig(level=logging.DEBUG)

router = APIRouter()

class User(BaseModel):
    id: str


def get_current_user() -> User:
    """
    TODO: this needs proper filling in if I want to host the app for many users.
    """
    return User(id="test-user-1")


@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage, current_user=Depends(get_current_user)):
    """Non-streaming version of the message endpoint."""
    try:
        graph = get_chat_graph(current_user.id)
        final_message = ""

        async for chunk in graph.process_message_stream(message.content):
            if not isinstance(chunk, tuple):
                logging.error(f"Unexpected chunk format: {chunk}")
                continue

            try:
                chunk_type, chunk_data = chunk

                if chunk_type == "messages":
                    if chunk_data and isinstance(chunk_data, list):
                        final_message += chunk_data[0].content
                elif chunk_type == "values":
                    logging.debug(f"Processing chunk - type: {chunk_type}, data: {chunk_data}")
                    last_message = chunk_data["messages"][-1]
                    final_message = last_message.content
            except Exception as e:
                logging.error(f"Error processing chunk: {chunk}, error: {e}")

        return ChatResponse(
            message=final_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
