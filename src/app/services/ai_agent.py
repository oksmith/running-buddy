import json
from typing import Dict, List

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.app import utils

load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"


class GetActivitiesInput(BaseModel):
    question: str = Field(..., description="A question about the user's activities.")

class SelectActivityInput(BaseModel):
    question: str = Field(..., description="A question about the user's activities.")
    activities: List[Dict] = Field(..., description="A list of dictionaries containing activity information.")

class GetMapInformationInput(BaseModel):
    activity: Dict = Field(..., description="A dictionary containing activity information.")

@tool(args_schema=GetActivitiesInput)
def get_activities(question: str, n_days: int = 7, location: str = "data/activities.json") -> Dict:
    """
    Retrieve a list of the user's past activities from the activity database (e.g., running or cycling activities).
    This tool is specifically designed for questions that require details about the user's performance, such as distance,
    time, or date of the activity.

    Inputs:
        n_days (int, optional): The number of days to look back when fetching activities. Defaults to 7.
        location (str, optional): Path to the activity data file (e.g., "data/activities.json").
    Output:
        Returns a list of dictionaries, each representing an activity. Each dictionary contains fields such as name, date, distance, duration, and map (for route details).

    When to Use: Use this tool whenever the user asks about their previous activities, including metrics like distance or time.

    """
    # TODO: replace this fixed JSON loading with an actual call to the Strava API.
    with open(location, "r") as f:
        activities = json.load(f)
    return activities


# async def aget_activities(n_days: int = 7, location: str = "data/activities.json") -> Dict:
#     """Async version of retrieving activities."""
#     return get_activities(n_days, location)

@tool(args_schema=SelectActivityInput)
def select_activity(question: str, activities: Dict) -> Dict:
    """
    Identifies the activity that best matches the user's query from a list of activities. The selection process
    considers fields such as the name, date, or other metadata of the activity.

    Args:
        question (str): A natural language question or query from the user. 
                        Example: "Tell me about my longest run this week."
        activities (List[Dict]): A list of activity dictionaries, each containing fields like name, date, distance, and duration.

    Returns:
        Dict: A dictionary representing the most relevant activity based on the query. If no activity matches the query,
              the most recent activity is returned as a fallback.

    When to use:
        Use this tool to identify the specific activity that aligns with the user's query before enriching it with additional data.
    """
    return activities[-1]


@tool(args_schema=GetMapInformationInput)
def get_map_information(activity: Dict) -> str:
    """
    Enriches a selected activity with geographical data, including nearby landmarks and street names along the activity's
    route. This tool extracts information from the activity's polyline and location data.

    Args:
        activity (Dict): A dictionary containing activity details, including:
            summary_polyline (str): Encoded polyline representing the route.
            start_latlng (List[float]): Latitude and longitude of the start point.
            end_latlng (List[float]): Latitude and longitude of the end point.

    Returns:
        Dict: A dictionary with two main keys:
            - landmarks (List[str]): A list of prominent landmarks (e.g., parks, tourist attractions) near the route.
            - streets (List[str]): A list of street names near the route.

    When to use:
        Use this tool to answer queries about nearby landmarks, streets, or geographical context of an activity after it has been selected as relevant.
    """
    return utils.fetch_map_details(activity["map"]["summary_polyline"], activity["start_latlng"], activity["end_latlng"])


# async def aget_map_information(activity: Dict) -> str:
#     return get_map_information(activity)


tools = [get_activities, select_activity, get_map_information]

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                # TODO: narrow the scope of the project. It is an agent which does one thing and one thing only.
                # Asking the tool to update an activity's description: Use get_activities followed by get_relevant_activity followed by get_map_info followed by create_description
                
                "You are a helpful assistant. "
                # "Strictly use the `duckduckgo_search` tool for weather-related questions only. Be precise when describing temperature and times. "
                "Strictly use the `get_activities` tool for questions about running activities. "
                # "To answer questions about a particular activity, you must first run `get_activities` tool to get the relevant information "
                # "and then pass the user's question along with the data from `get_activities` to the `select_activity` tool to select an activity followed by the "
                # "`get_map_info` tool to enrich that activity with map data and return nearby street names and landmarks."
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
