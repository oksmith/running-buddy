import logging
from typing import AsyncIterator, Dict, Optional
from dataclasses import dataclass

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import (  # TODO: check what tools_condition and ToolNode do again?
    ToolNode,
    tools_condition,
)
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
        """
        Process messages through the chatbot.
        """
        messages = state["messages"]

        # Add system message if it's not present
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            messages = [self.system_message] + messages

        try:
            response = self.llm_with_tools.invoke(messages)
            logging.debug(f"Tool calls in _chatbot_node: {response.tool_calls}")
            return {"messages": [response]}

        except Exception as e:
            raise Exception(
                f"Error in chatbot processing: {str(e)}"
            )  # TODO: custom exception

    def _select_next_node(self, state: State) -> str:
        """
        Determine the next node in the graph.
        """
        return tools_condition(state)

    def _build_graph(self) -> StateGraph:
        """
        Build the graph structure.
        """
        graph_builder = StateGraph(State)

        # Add nodes to the graph
        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))

        # Add edges to the graph (there is a conditional edge between chatbot and human/tools
        # but we always go to chatbot from the human/tools nodes)
        graph_builder.add_conditional_edges(
            "chatbot",
            self._select_next_node,
        )
        graph_builder.add_edge("tools", "chatbot")

        # Put it all together
        graph_builder.set_entry_point("chatbot")
        memory = MemorySaver()
        return graph_builder.compile(checkpointer=memory)

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
            config = {"configurable": {"thread_id": "1"}}

            # Stream both values and LLM messages
            async for chunk in self.graph.astream(
                initial_state, config, stream_mode=["values", "messages"]
            ):
                yield chunk

        except Exception as e:
            raise Exception(f"Error processing message stream: {str(e)}")


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
