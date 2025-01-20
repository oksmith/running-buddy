import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from src.app.models.chat import ChatMessage, ChatResponse
from src.app.services.chatbot.graph import get_chat_graph

logging.basicConfig(level=logging.INFO)

router = APIRouter()


class User(BaseModel):
    id: str


def get_current_user() -> User:
    """
    TODO: this needs proper filling in if I want to host the app for many users.
    We also need to pass it in loads of different places... frontend needs it, backend needs it, etc.
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
                    logging.debug(
                        f"Processing chunk - type: {chunk_type}, data: {chunk_data}"
                    )
                    if chunk_data and isinstance(chunk_data, list):
                        final_message += chunk_data[0].content

                elif chunk_type == "values":
                    logging.debug(
                        f"Processing chunk - type: {chunk_type}, data: {chunk_data}"
                    )
                    last_message = chunk_data["messages"][-1]
                    final_message = last_message.content
            except Exception as e:
                logging.error(f"Error processing chunk: {chunk}, error: {e}")

        logging.info(f"Graph state tasks: {graph.graph.get_state(graph.config).tasks}")
        tasks = graph.graph.get_state(graph.config).tasks
        try:
            if (
                len(tasks) > 0
                and hasattr(tasks[0], "interrupts")
                and len(tasks[0].interrupts) > 0
            ):
                interrupt = tasks[0].interrupts[0]
                # e.g. Interrupt(
                #   value={'question': 'Would you like to proceed with updating the activity?', 'tool_call': {'name': 'update_activity', 'args': { ... }},
                #   resumable=True,
                #   ns=['tools:1913bc93-971a-5dcb-af78-ab4fcf271b48'],
                #   when='during'
                # )
                return ChatResponse(message=interrupt.value["question"], interrupt=True)
        except Exception as e:
            logging.error(f"Error getting interrupts: {e}")

        logging.info("Final message: " + final_message)
        return ChatResponse(message=final_message, interrupt=False)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConfirmationRequest(BaseModel):
    confirmed: bool
    user_id: str


@router.post("/confirm")
async def confirm_tool_call(request: ConfirmationRequest):
    graph = get_chat_graph(request.user_id)
    thread_config = {"configurable": {"thread_id": "1"}}

    # Resume the graph with the confirmation
    response = await graph.graph.ainvoke(
        Command(resume={"confirmed": request.confirmed}), config=thread_config
    )
    latest_message = response["messages"][-1]
    logging.debug(f"Response from graph, after human confirmation: {latest_message}")

    return ChatResponse(message=latest_message.content, interrupt=False)
