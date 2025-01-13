import json
from typing import Dict, List

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.app.utils import maps

load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"

# TODO: make all this happen with some user_id injected. This will be based on whoever is using the app
# https://python.langchain.com/docs/how_to/tool_runtime/


class GetActivitiesInput(BaseModel):
    question: str = Field(..., description="Question about activities")
    n_days: int = Field(default=7, description="Days to look back")
    location: str = Field(
        default="data/activities.json", description="Activity data path"
    )


class SelectActivityInput(BaseModel):
    question: str
    activities_file: str


class GetMapInformationInput(BaseModel):
    activity_file: str = Field(
        ..., description="Path to JSON file containing activity data"
    )


@tool(args_schema=GetActivitiesInput)
def get_activities(
    question: str, n_days: int = 7, location: str = "data/activities.json"
) -> Dict:
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
    location = "data/activities.json"
    # TODO: replace this fixed JSON loading with an actual call to the Strava API.
    with open(location, "r") as f:
        activities = json.load(f)

    # Save activities to filename
    save_activities(activities, location)
    return location


def save_activities(activities: List[Dict], location: str) -> None:
    with open(location, "w") as f:
        json.dump(activities, f)


@tool(args_schema=SelectActivityInput)
def select_activity(question: str, activities_file: str) -> str:
    """
    Identifies the activity that best matches the user's query from a list of activities. The selection process
    considers fields such as the name, date, or other metadata of the activity.

    Args:
        question (str): A natural language question or query from the user.
                        Example: "Tell me about my longest run this week."
        activities_file (str): A file containing the json of activities.

    Returns:
        Dict: A dictionary representing the most relevant activity based on the query. If no activity matches the query,
              the most recent activity is returned as a fallback.

    When to use:
        Use this tool to identify the specific activity that aligns with the user's query before enriching it with additional data.
    """
    with open(activities_file, "r") as f:
        activities = json.load(f)
    activity = activities[-1]  # Your selection logic here

    # Save selected activity
    activity_file = "data/selected_activity.json"
    with open(activity_file, "w") as f:
        json.dump(activity, f)
    return activity_file


@tool(args_schema=GetMapInformationInput)
def get_map_information(activity_file: str) -> str:
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
    with open(activity_file, "r") as f:
        activity = json.load(f)
    return maps.fetch_map_details(activity["map"]["summary_polyline"])


tools = [get_activities, select_activity, get_map_information]


# # TODO: narrow the scope of the project. It is an agent which does one thing and one thing only.
# # Asking the tool to update an activity's description: Use get_activities followed by get_relevant_activity followed by get_map_info followed by create_description
# "You are a helpful assistant. "
# # "Strictly use the `duckduckgo_search` tool for weather-related questions only. Be precise when describing temperature and times. "
# "Strictly use the `get_activities` tool for questions about running activities. "
# # "To answer questions about a particular activity, you must first run `get_activities` tool to get the relevant information "
# # "and then pass the user's question along with the data from `get_activities` to the `select_activity` tool to select an activity followed by the "
# # "`get_map_info` tool to enrich that activity with map data and return nearby street names and landmarks."
# Common issues arise when:
# The LLM doesn't preserve complete data structures
# Schema validation fails due to missing required fields
# The prompt doesn't clearly specify data dependencies
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a Strava activity processor. Follow these steps:\n"
                "1. Call get_activities to fetch activities\n"
                "2. Pass the FULL activities response along with the question to select_activity\n"
                "3. Pass the ENTIRE selected activity object to get_map_information\n\n"
                "IMPORTANT: When passing data between tools, preserve the complete data structure. Do not send empty objects or partial data."
                "IMPORTANT: If the user asks about generating a poem, use street names and parks as inspiration. Also, keep it short (4-10 lines) and make sure it rhymes."
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
