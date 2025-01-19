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
from langgraph.types import interrupt, Command

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
        self.config = {"configurable": {"thread_id": "1"}}
        self.graph = self._build_graph()

    def _chatbot_node(self, state: State) -> Dict:
        """
        Process messages through the chatbot.
        """
        logging.debug(f"DEBUGGING: state in _chatbot_node: {state}")

        messages = state["messages"]

        # Add system message if it's not present
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            messages = [self.system_message] + messages

        try:
            response = self.llm_with_tools.invoke(messages)
            logging.debug(f"Tool calls in _chatbot_node: {response.tool_calls}")
            return {"messages": [response]}

        except Exception as e:
            raise Exception(f"Error in chatbot processing: {str(e)}")

    def _tool_node(self, state: State) -> Dict:
        logging.debug(f"DEBUGGING: state in _tool_node: {state}")
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "update_activity":
                    logging.debug("DETECTED update_activity CALL")
                    state["interrupt"] = {
                        "question": "Would you like to proceed with updating the activity?",
                        "tool_call": tool_call,
                    }
                    response = interrupt(state["interrupt"])
                    logging.debug(
                        f"DEBUGGING: resuming after human review in _tool_node: {response}"
                    )

                    if response.get("confirmed"):
                        return ToolNode(tools=self.tools).invoke(state)
                    return {"messages": messages}

        return ToolNode(tools=self.tools).invoke(state)

    # def _tool_node(self, state: State) -> Dict:
    #     logging.debug(f"DEBUGGING: state in _tool_node: {state}")

    #     """
    #     {'messages': [AIMessage(content='', additional_kwargs={'tool_calls': [{'index': 0, 'id': 'call_Sz2pyDFAImbXvRUolb2gs8Wy', 'function': {'arguments': '{"query":"this morning"}', 'name': 'fetch_activities'}, 'type': 'function'}]}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_72ed7ab54c'}, id='run-2a31061d-b244-40ae-ae58-522b13e4998b', tool_calls=[{'name': 'fetch_activities', 'args': {'query': 'this morning'}, 'id': 'call_Sz2pyDFAImbXvRUolb2gs8Wy', 'type': 'tool_call'}])]}
    #     """

    #     messages = state["messages"]
    #     last_message = messages[-1]
    #     if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
    #         tool_calls = last_message.tool_calls
    #         for tool_call in tool_calls:
    #             if tool_call["name"] == "update_activity":
    #                 # Store the pending tool call in state
    #                 state["pending_tool_call"] = tool_call

    #                 # Interrupt the flow to confirm the tool call
    #                 logging.debug("DETECTED update_activity CALL")
    #                 human_review = interrupt(
    #                     {
    #                         "question": "Would you like to proceed with updating the activity?",
    #                         "tool_call": tool_call,
    #                     }
    #                 )
    #                 logging.debug(
    #                     f"DEBUGGING: human_review in _tool_node: {human_review}"
    #                 )

    #                 return Command(
    #                     goto="interrupted",  # Set to a custom state for interruptions
    #                     update={"interrupt_message": human_review},
    #                 )
    #                 # # Route based on human input
    #                 # if human_review.get("action") == "approve":
    #                 #     # Continue with the original tool call
    #                 #     return Command(goto="run_tool")
    #                 # elif human_review.get("action") == "modify":
    #                 #     # Update the tool call with human modifications
    #                 #     updated_tool_call = human_review.get("updated_tool_call")
    #                 #     return Command(
    #                 #         goto="run_tool",
    #                 #         update={"messages": [updated_tool_call]},
    #                 #     )
    #                 # elif human_review.get("action") == "feedback":
    #                 #     # Provide feedback for adjustment
    #                 #     feedback_message = human_review.get("feedback_message")
    #                 #     return Command(
    #                 #         goto="call_llm",
    #                 #         update={"messages": [feedback_message]},
    #                 #     )
    #                 # else:
    #                 #     # If no clear action, return to the previous state or take a fallback path
    #                 #     return Command(goto="previous_node")

    #     # If no interruption needed, proceed with ToolNode invocation
    #     return ToolNode(tools=self.tools).invoke(state)

    def _select_next_node(self, state: State) -> str:
        """
        Determine the next node in the graph.
        """
        if state.get("interrupt"):
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
