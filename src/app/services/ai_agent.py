import json
from typing import Dict, List

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.app.services import gmaps, strava

load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"

# TODO: make all this happen with some user_id injected. This will be based on whoever is using the app
# https://python.langchain.com/docs/how_to/tool_runtime/


class GetActivitiesInput(BaseModel):
    question: str = Field(..., description="Question about activities")
    location: str = Field(
        default="data/activities.json", description="Activity data path"
    )


class SelectActivityInput(BaseModel):
    question: str
    activities_file: str


class UpdateActivityInput(BaseModel):
    question: str
    enriched_activities_file: str


class GetMapInformationInput(BaseModel):
    activity_file: str = Field(
        ..., description="Path to JSON file containing activity data"
    )


def save_activities(activities: List[Dict], location: str) -> None:
    with open(location, "w") as f:
        json.dump(activities, f)


@tool(args_schema=GetActivitiesInput)
def fetch_activities(question: str, location: str = "data/activities.json") -> str:
    """Retrieve a list of the user's past activities from Strava.

    Args:
        question (str): The question or command the user has provided. Extract information like the time period from this.
        location (str, optional): Path to the activity data file. Defaults to "data/activities.json".

    Returns:
        str: A filename containing the activities JSON.
    """

    s = strava.StravaClient(strava.get_access_token())
    activities = s.fetch_activities()
    save_activities(activities, location)
    return location


@tool(args_schema=SelectActivityInput)
def select_activity(question: str, activities_file: str) -> str:
    """Identifies the activity best matching a user query from a list of activities.

    The selection process considers fields such as the name, date, or other metadata of
    the activity.

    Args:
        question (str): A natural language question or query from the user.
            Example: "Tell me about my longest run this week."
        activities_file (str): A file containing the JSON of activities.

    Returns:
        str: A filename containing the relevant activity JSON.

    """
    with open(activities_file, "r") as f:
        activities = json.load(f)

    # TODO: currently this code just selects the latest activity. I should write some custom
    # selection logic, so that if the user says "my run on date X" then it knows to filter only
    # runs and only activities on date X.
    activity = activities[-1]

    # Save selected activity
    activity_file = "data/selected_activity.json"
    with open(activity_file, "w") as f:
        json.dump(activity, f)
    return activity_file


@tool(args_schema=GetMapInformationInput)
def enrich_activity(activity_file: str) -> str:
    """Enriches a selected activity with map data.

    Includes nearby landmarks and street names along the activity's route. This tool
    extracts information from the activity's polyline and location data.

    Args:
        activity_file (str): A file containing activity data, including map information.

    Returns:
        str: A filename containing the activity enriched with map information.
    """
    g = gmaps.GMapsClient()
    with open(activity_file, "r") as f:
        activity = json.load(f)
    return g.fetch_map_details(activity["map"]["summary_polyline"])


tools = [
    fetch_activities,
    select_activity,
    enrich_activity,
    # description_generator, # TODO: write
    # update_activity, # TODO: write
]


# TODO: this is a very well-defined chain. What agency does my bot actually have? Interacting with the user and tweaking the poem, knowing
# which function to use to tweak the poem, are useful things.
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a Strava activity processor. Follow these steps:\n"
                "1. Call get_activities to fetch activities\n"
                "2. Pass the get_activities response along with the question to select_activity\n"
                "3. Pass the select_activity response to get_map_information\n\n"
                "4. Generate a poem using the select_activity response and the get_map_information response"
                "IMPORTANT: If the user asks about generating a poem, use street names and parks as inspiration. Also, keep it short (4-10 lines) and make sure it rhymes."
                "5. If the user asks to modify the poem, generate a new poem using the select_activity response and the get_map_information response using chat history."
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
