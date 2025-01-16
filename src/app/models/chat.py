from pydantic import BaseModel
from typing import List, Union


class ChatMessage(BaseModel):
    content: str


class ChatResponse(BaseModel):
    message: str
    requires_confirmation: bool = False


class ChatSession(BaseModel):
    user_id: str
    messages: List[Union[ChatMessage, dict]] = []
    context: dict = {}
