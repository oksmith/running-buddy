from typing import List, Optional, Union

from pydantic import BaseModel


class ChatMessage(BaseModel):
    content: str


class ChatResponse(BaseModel):
    message: str = ""
    interrupt: bool = False
    tool_status: Optional[str] = None
    error: Optional[str] = None


class ChatSession(BaseModel):
    user_id: str
    messages: List[Union[ChatMessage, dict]] = []
    context: dict = {}
