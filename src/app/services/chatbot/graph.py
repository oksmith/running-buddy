import logging
from typing import AsyncIterator, Dict, Optional
from dataclasses import dataclass

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict
from langgraph.types import interrupt

from src.app.services.chatbot.prompts import SYSTEM_INSTRUCTIONS
from src.app.services.chatbot.tools import get_tools
from src.app.utils.logger import setup_logger

logger = setup_logger(name="chat_app", level=logging.INFO, log_file="chat.log")

MODEL_NAME = "gpt-4o-mini"


@dataclass
class InterruptMessage:
    content: str
    tool_call: Optional[Dict] = None  # the tool call that is pending


class State(TypedDict):
    messages: Annotated[list, add_messages]
    interrupt: Optional[InterruptMessage]


class ChatGraph:
    def __init__(self, user_id: str):
        """
        Initialize a chat graph for a specific user.

        Args:
            user_id (str): The ID of the user this graph belongs to
        """
        self.user_id = user_id
        self.tools = get_tools()  # TODO: may need to pass user_id to this one day, so that I fetch the correct StravaClient token
        self.llm = ChatOpenAI(model=MODEL_NAME)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.system_message = SystemMessage(content=SYSTEM_INSTRUCTIONS)
        self.config = {"configurable": {"thread_id": "1"}}
        self.graph = self._build_graph()

    def _chatbot_node(self, state: State) -> Dict:
        """
        Process messages through the chatbot.
        """
        messages = state["messages"]

        # Add system message if it's not present
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            messages = [self.system_message] + messages

        try:
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}

        except Exception as e:
            raise Exception(f"Error in chatbot processing: {str(e)}")

    def _tool_node(self, state: State) -> Dict:
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "update_activity":
                    logger.info(
                        "Detected an update_activity call, interrupting the graph flow!"
                    )
                    state["interrupt"] = {
                        "question": "Would you like to proceed with updating the activity?",
                        "tool_call": tool_call,
                    }
                    response = interrupt(state["interrupt"])
                    logger.info(
                        f"Resuming after human review in _tool_node: {response}"
                    )

                    if response.get("confirmed"):
                        # only continue with the tools if the user confirmed
                        return ToolNode(tools=self.tools).invoke(state)

                    # otherwise, just return current state and continue with the chatbot
                    return {"messages": messages}

        # invoke tools as per usual if no interruption needed
        return ToolNode(tools=self.tools).invoke(state)

    def _select_next_node(self, state: State) -> str:
        """
        Determine the next node in the graph.
        """
        # TODO: is this needed? or can we just use `tool_condition`?
        if state.get("interrupt"):
            logger.info("Interrupt detected, moving to chatbot node")
            return "chatbot"

        if isinstance(state, list):
            ai_message = state[-1]
        elif isinstance(state, dict) and (messages := state.get("messages", [])):
            ai_message = messages[-1]
        elif messages := getattr(state, "messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")

        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
        return "__end__"

    def _build_graph(self) -> StateGraph:
        """
        Build the graph structure.
        """
        graph_builder = StateGraph(State)

        # Add nodes to the graph
        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_node("tools", self._tool_node)

        # Add edges to the graph (there is a conditional edge between chatbot and human/tools
        # but we always go to chatbot from the human/tools nodes)
        graph_builder.add_conditional_edges(
            "chatbot",
            self._select_next_node,
        )
        graph_builder.add_edge("tools", "chatbot")

        # Put it all together
        graph_builder.set_entry_point("chatbot")
        return graph_builder.compile(checkpointer=MemorySaver())

    async def process_message_stream(self, message: str) -> AsyncIterator[Dict]:
        """
        Process a new message through the graph with streaming support.

        Args:
            message (str): The message to process

        Returns:
            AsyncIterator[Dict]: Stream of updates from the graph processing
        """
        try:
            initial_state = {
                "messages": [{"role": "user", "content": message}],
            }

            # Stream both values and LLM messages
            async for chunk in self.graph.astream(
                initial_state, self.config, stream_mode=["values", "messages"]
            ):
                yield chunk

        except Exception as e:
            raise Exception(f"Error processing message stream: {str(e)}")


# Factory function to get or create a chat graph for multiple users
# TODO: actually do this lol
_user_graphs: Dict[str, ChatGraph] = {}


def get_chat_graph(user_id: str) -> ChatGraph:
    """
    Get or create a chat graph for a specific user.

    Args:
        user_id (str): The ID of the user

    Returns:
        ChatGraph: The chat graph instance for this user
    """
    if user_id not in _user_graphs:
        _user_graphs[user_id] = ChatGraph(user_id)
    return _user_graphs[user_id]
