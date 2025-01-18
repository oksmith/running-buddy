import json
from datetime import datetime
from typing import Dict, List

from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict

from src.app.services.chatbot.prompts import ACTIVITY_SELECTION_INSTRUCTIONS

MODEL_NAME = "gpt-4o-mini"


class Activity(TypedDict):
    """A Strava activity."""
    id: Annotated[int, ..., "The activity ID"]
    name: Annotated[str, ..., "The title of the activity"]
    type: Annotated[str, ..., "The type of the activity"]
    distance: Annotated[float, ..., "The distance (in metres)"]
    moving_time: Annotated[int, ..., "The moving time (in seconds)"]
    elapsed_time: Annotated[int, ..., "The elapsed time (in seconds)"]
    total_elevation_gain: Annotated[float, ..., "The total elevation gain (in metres)"]
    start_date_local: Annotated[str, ..., "The start date in local time of the activity in ISO 8601 standard"]
    kudos_count: Annotated[int, ..., "The count of kudos"]
    photo_count: Annotated[int, ..., "The count of photos"]
    map: Annotated[Dict, ..., "Map information from the activity"]



def select_activity_llm(query: str, activities: List[Dict]) -> Activity:
    llm = ChatOpenAI(model=MODEL_NAME)
    structured_llm = llm.with_structured_output(Activity)
    return structured_llm.invoke(
        f"""
        You are a helpful assistant you searches through a json of activity information,
        finds the activity most related to the query, and returns that selected activity.
        {ACTIVITY_SELECTION_INSTRUCTIONS}
        Today's date: {datetime.now().strftime('%Y-%m-%d')}

        Query: {query}
        Activities: {json.dumps(activities)}
        """
    )
