import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from src.app.models.chat import ChatMessage, ChatResponse
from src.app.services.chatbot.graph import get_chat_graph
from src.app.services.chatbot.tools import TOOL_CALL_MESSAGES
from src.app.utils.logger import setup_logger

logger = setup_logger(name="chat_app", level=logging.INFO, log_file="chat.log")

router = APIRouter()


class User(BaseModel):
    id: str


def get_current_user() -> User:
    """
    TODO: this needs proper filling in if I want to host the app for many users.
    We also need to pass it in loads of different places... frontend needs it, backend needs it, etc.
    """
    return User(id="test-user-1")


@router.post("/message_stream")
async def send_message_stream(
    message: ChatMessage, current_user=Depends(get_current_user)
):
    """
    Streaming version of the message endpoint. Sends incremental updates to the frontend,
    including tool execution status messages.
    """
    try:

        async def generate_response():
            try:
                graph = get_chat_graph(current_user.id)
                current_message = ""

                async for chunk in graph.process_message_stream(message.content):
                    if not isinstance(chunk, tuple):
                        logger.error(f"Unexpected chunk format: {chunk}")
                        continue

                    try:
                        chunk_type, chunk_data = chunk

                        if chunk_type == "messages":
                            logger.debug(
                                f"Processing chunk - type: {chunk_type}, data: {chunk_data}"
                            )
                            if chunk_data and isinstance(chunk_data, list):
                                if chunk_data[0].content:
                                    current_message += chunk_data[0].content
                                    yield (
                                        json.dumps({"message": current_message}) + "\n"
                                    )

                        elif chunk_type == "values":
                            logger.debug(
                                f"Processing chunk - type: {chunk_type}, data: {chunk_data}"
                            )
                            last_message = chunk_data["messages"][-1]
                            if (
                                hasattr(last_message, "tool_calls")
                                and last_message.tool_calls
                            ):
                                tool_name = last_message.tool_calls[0]["name"]
                                logger.info(
                                    f"Tool calls detected in last message [values]: {last_message.tool_calls}"
                                )
                                yield (
                                    json.dumps(
                                        {
                                            "message": current_message,
                                            "tool_status": TOOL_CALL_MESSAGES[
                                                tool_name
                                            ],
                                        }
                                    )
                                    + "\n"
                                )

                            current_message = last_message.content
                            yield json.dumps({"message": current_message}) + "\n"

                    except Exception as e:
                        logger.error(f"Error processing chunk: {chunk}, error: {e}")
                        continue

                # Check for interrupts at the end
                tasks = graph.graph.get_state(graph.config).tasks
                if (
                    len(tasks) > 0
                    and hasattr(tasks[0], "interrupts")
                    and len(tasks[0].interrupts) > 0
                ):
                    interrupt = tasks[0].interrupts[0]
                    yield (
                        json.dumps(
                            {"message": interrupt.value["question"], "interrupt": True}
                        )
                        + "\n"
                    )

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield json.dumps({"error": str(e)}) + "\n"

        return StreamingResponse(generate_response(), media_type="text/event-stream")

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
    logger.info(f"Response from graph, after human confirmation: {latest_message}")
    return ChatResponse(message=latest_message.content, interrupt=False)


# This function is not used in the current implementation. It works in conjunction
# with `static/old_scripts.js`.
@router.post("/message_static", response_model=ChatResponse)
async def send_message_static(
    message: ChatMessage, current_user=Depends(get_current_user)
):
    """
    Non-streaming version of the message endpoint. Only the final message is sent to
    the front-end for user display. This function handles messages sent from the agent
    graph, and works out what messages (ChatResponse) should be sent back to the user.
    """
    try:
        graph = get_chat_graph(current_user.id)
        final_message = ""
        in_progress_message = None

        async for chunk in graph.process_message_stream(message.content):
            if not isinstance(chunk, tuple):
                logger.error(f"Unexpected chunk format: {chunk}")
                continue

            try:
                chunk_type, chunk_data = chunk

                if chunk_type == "messages":
                    logger.debug(
                        f"Processing chunk - type: {chunk_type}, data: {chunk_data}"
                    )
                    if chunk_data and isinstance(chunk_data, list):
                        final_message += chunk_data[0].content

                elif chunk_type == "values":
                    logger.debug(
                        f"Processing chunk - type: {chunk_type}, data: {chunk_data}"
                    )
                    last_message = chunk_data["messages"][-1]
                    final_message = last_message.content
                    if (
                        hasattr(chunk_data["messages"][-1], "tool_calls")
                        and len(chunk_data["messages"][-1].tool_calls) > 0
                    ):
                        in_progress_message = TOOL_CALL_MESSAGES[
                            last_message.tool_calls[0]["name"]
                        ]
                        logger.info(
                            f"Tool calls detected in last message [values]: {last_message.tool_calls} :: {in_progress_message}"
                        )

            except Exception as e:
                logger.error(f"Error processing chunk: {chunk}, error: {e}")

        logger.info(f"Graph state tasks: {graph.graph.get_state(graph.config).tasks}")
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
            logger.error(f"Error getting interrupts: {e}")

        logger.info("Final message: " + final_message)
        return ChatResponse(message=final_message, interrupt=False)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
