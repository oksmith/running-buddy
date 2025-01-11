import json
from typing import Dict

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"


class ActivityInput(BaseModel):
    question: str = Field(..., description="A question about the user's activities.")


def get_activities(n_days: int = 7, location: str = "data/activities.json") -> Dict:
    """Retrieve activities from Strava."""
    # TODO: replace this fixed JSON loading with an actual call to the Strava API.
    with open(location, "r") as f:
        activities = json.load(f)
    return activities


async def aget_activities(n_days: int = 7, location: str = "data/activities.json") -> Dict:
    """Async version of retrieving activities."""
    return get_activities(n_days, location)


tools = [
    # TODO: maybe I need a specific weather retriever from BBC weather directly? This isn't that reliable
    DuckDuckGoSearchRun(
        api_wrapper=DuckDuckGoSearchAPIWrapper(max_results=5, region="uk-en")
    ),
    Tool(
        name="get_activities",
        func=get_activities,
        description=(
            "Retrieve information about the user's activities. Use for questions related to runs, "
            "such as 'How far did I run on 10th January?'."
        ),
        args_schema=ActivityInput,
        coroutine=aget_activities,
    ),
]

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a helpful assistant. "
                "Strictly use the `duckduckgo_search` tool for weather-related questions only. Be precise when describing temperature and times. "
                "Strictly use the `get_activities` tool for questions about running activities."
            ),
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

llm = ChatOpenAI(model=OPENAI_MODEL)

agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
