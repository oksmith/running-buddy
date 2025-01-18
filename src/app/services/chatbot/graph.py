import logging
from typing import AsyncIterator, Dict

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import (  # TODO: check what tools_condition and ToolNode do again?
    ToolNode,
    tools_condition,
)
from pydantic import BaseModel
from typing_extensions import Annotated, TypedDict

from src.app.services.chatbot.human_confirmation import get_user_confirmation_async
from src.app.services.chatbot.prompts import SYSTEM_INSTRUCTIONS
from src.app.services.chatbot.tools import get_tools

logging.basicConfig(level=logging.DEBUG)

MODEL_NAME = "gpt-4o-mini"


class State(TypedDict):
    messages: Annotated[list, add_messages]
    ask_human: bool


class RequestAssistance(BaseModel):
    """Escalate the conversation to an expert. Use this after generating a poem (to check the expert likes the poem)
    and also before updating an activity (to confirm it's the correct activity).
    """

    request: str


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
        self.llm_with_tools = self.llm.bind_tools(self.tools + [RequestAssistance])
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

            ask_human = False
            if (
                response.tool_calls
                and response.tool_calls[0]["name"] == RequestAssistance.__name__
            ):
                ask_human = True

            logging.debug(f"ask_human: {ask_human}")

            return {"messages": [response], "ask_human": ask_human}

        except Exception as e:
            raise Exception(
                f"Error in chatbot processing: {str(e)}"
            )  # TODO: custom exception

    def _human_node(self, state: State) -> Dict:
        """
        Handle human interaction node.
        """
        new_messages = []
        ai_message = state["messages"][-1]
        logging.debug("CALLING _human_node!")

        # Check if this is a RequestAssistance tool call
        if (
            hasattr(ai_message, "tool_calls")
            and ai_message.tool_calls
            and isinstance(ai_message.tool_calls, list)
            and len(ai_message.tool_calls) > 0
        ):
            tool_call = ai_message.tool_calls[0]
            confirmation_id = tool_call["id"]

            logging.warning(f'Waiting for human confirmation with ID: {confirmation_id}, MESSAGES: {state["messages"]}')

            # TODO: how do I get the button click information from the UI back into
            # this message / graph state?
            user_confirmation = get_user_confirmation_async(confirmation_id)

            new_messages.append(
                ToolMessage(
                    content="Confirmed by user."
                    if user_confirmation
                    else "Cancelled by user.",
                    tool_call_id=tool_call["id"],
                )
            )
        else:
            if not isinstance(ai_message, ToolMessage):
                new_messages.append(
                    ToolMessage(
                        content="No response needed.",
                        tool_call_id=ai_message.tool_calls[0]["id"]
                        if hasattr(ai_message, "tool_calls")
                        else "default_id",
                    )
                )
        
        return {
            "messages": state["messages"] + new_messages,
            "ask_human": False,  # Human input is resolved, loop back to the chatbot
        }


    def _select_next_node(self, state: State) -> str:
        """
        Determine the next node in the graph.
        """
        logging.debug(f"_select_next_node is on state {state}!")
        if state["ask_human"]:
            return "human"
        return tools_condition(state)

    def _build_graph(self) -> StateGraph:
        """
        Build the graph structure.
        """
        graph_builder = StateGraph(State)

        # Add nodes to the graph
        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_node("human", self._human_node)

        # Add edges to the graph (there is a conditional edge between chatbot and human/tools
        # but we always go to chatbot from the human/tools nodes)
        graph_builder.add_conditional_edges(
            "chatbot",
            self._select_next_node,
            {"human": "human", "tools": "tools", "__end__": "__end__"},
        )
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge("human", "chatbot")

        # Put it all together
        graph_builder.set_entry_point("chatbot")
        memory = MemorySaver()
        return graph_builder.compile(
            checkpointer=memory,
            interrupt_before=["human"],
        )

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
                "ask_human": False,
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
