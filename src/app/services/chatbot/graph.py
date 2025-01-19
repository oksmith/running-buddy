import logging
import json
from typing import AsyncIterator, Dict, Optional, Literal
from dataclasses import dataclass

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict


from src.app.services.chatbot.prompts import SYSTEM_INSTRUCTIONS
from src.app.services.chatbot.tools import get_tools

logging.basicConfig(level=logging.DEBUG)

MODEL_NAME = "gpt-4o-mini"


@dataclass
class InterruptMessage:
    content: str
    tool_call: Optional[Dict] = None


class State(TypedDict):
    messages: Annotated[list, add_messages]
    interrupt: Optional[InterruptMessage]
    pending_tool_call: Optional[Dict]


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
        self.graph = self._build_graph()

    def _chatbot_node(self, state: State) -> Dict:
        messages = state["messages"]
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            messages = [self.system_message] + messages

        response = self.llm_with_tools.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_call = response.tool_calls[0]
            if tool_call.function.name == "update_strava_activity":
                args = json.loads(tool_call.function.arguments)
                return {
                    "messages": messages + [response],
                    "interrupt": InterruptMessage(
                        content=f"Would you like to update the Strava activity with this poem?\n\n{args['description']}\n\nReply 'yes' to confirm or 'no' to cancel.",
                        tool_call=tool_call,
                    ),
                    "pending_tool_call": None,
                }

        return {
            "messages": messages + [response],
            "interrupt": None,
            "pending_tool_call": None,
        }

    def _tools_node(self, state: State) -> Dict:
        if state.get("interrupt"):
            # Don't execute tools if we're waiting for confirmation
            return state

        tool_executor = ToolNode(tools=self.tools)
        result = tool_executor.invoke(state)
        return {
            "messages": state["messages"] + [result],
            "interrupt": None,
            "pending_tool_call": None,
        }

    def _select_next(self, state: State) -> Literal["chatbot", "tools"]:
        if state.get("interrupt"):
            return "chatbot"
        last_message = state["messages"][-1]
        return "tools" if hasattr(last_message, "tool_calls") else "chatbot"

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(State)

        graph.add_node("chatbot", self._chatbot_node)
        graph.add_node("tools", self._tools_node)

        graph.add_conditional_edges(
            "chatbot", self._select_next, {"chatbot": "chatbot", "tools": "tools"}
        )
        graph.add_edge("tools", "chatbot")

        graph.set_entry_point("chatbot")
        return graph.compile(checkpointer=MemorySaver())

    async def process_message_stream(self, message: str) -> AsyncIterator[Dict]:
        """
        Process a new message through the graph with streaming support.

        Args:
            message (str): The message to process

        Returns:
            AsyncIterator[Dict]: Stream of updates from the graph processing
        """
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "interrupt": None,
            "pending_tool_call": None,
        }

        async for chunk in self.graph.astream(
            initial_state,
            {"configurable": {"thread_id": "1"}},
            stream_mode=["values", "messages"],
        ):
            yield chunk


# Factory function to get or create a chat graph for multiple users
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
