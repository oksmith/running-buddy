from typing import List, Union

from pydantic import BaseModel


class ChatMessage(BaseModel):
    content: str


class ChatResponse(BaseModel):
    message: str
    requires_confirmation: bool


class ChatSession(BaseModel):
    user_id: str
    messages: List[Union[ChatMessage, dict]] = []
    context: dict = {}
