from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from src.app.services.ai_agent import agent_executor

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    chat_history: list[dict] = []


class ChatResponse(BaseModel):
    response: str
    chat_history: list[dict]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    try:
        # Build chat history from the request
        chat_history = [
            HumanMessage(content=msg["content"]) if msg["role"] == "human" else AIMessage(content=msg["content"])
            for msg in request.chat_history
        ]

        # Invoke agent, extract the output
        # e.g. result: {'input': "What's the weather like in London today?", 'chat_history': [], 'output': 'Today in London, the ....'}
        print(request.message, chat_history)
        result = agent_executor.invoke(
            {"input": request.message, "chat_history": chat_history}
        )
        output = result["output"]

        if not isinstance(output, str):
            raise ValueError("Unexpected result format from agent: {}".format(type(result)))

        # Add to chat history and return in the response, so that future questions have access to this
        # part of the conversation
        # TODO: am I converting between Message objects and string content too often in this function?
        #       is there a more efficient way to do this?
        chat_history.append(HumanMessage(content=request.message))
        chat_history.append(AIMessage(content=output))
        formatted_chat_history = [
            {"role": "human" if isinstance(msg, HumanMessage) else "ai", "content": msg.content}
            for msg in chat_history
        ]

        return ChatResponse(response=output, chat_history=formatted_chat_history)

    except Exception as e:
        # Print the traceback for debugging purposes
        import traceback
        print("Error occurred:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the request. Exception: {e}")
