import json
from typing import Dict, Tuple

from src.app.services.chatbot import utils
from src.app.services.googlemaps.client import GMapsClient
from src.app.services.strava.client import StravaClient, get_access_token


TOOL_CALL_MESSAGES: Dict = {
    "fetch_activities": "Fetching activities...",
    "select_activity": "Selecting activity...",
    "read_activity": "Reading activity...",
    "enrich_activity": "Enriching activity...",
    "update_activity": "Updating activity...",
}


def fetch_activities(query: str) -> str:
    """Retrieve a list of the user's past activities from Strava.

    Args:
        query (str): A natural language question or query from the user.

    Returns:
        str: A filename containing the activities JSON.
    """
    location = "data/activities.json"
    s = StravaClient(get_access_token())
    activities = s.fetch_activities()
    with open(location, "w") as f:
        json.dump(activities, f)
    return location


def select_activity(query: str, activities_file: str) -> Tuple[bool, str]:
    """Identifies the activity best matching a user query from a list of activities.

    The selection process considers fields such as the name, date, or other metadata of
    the activity.

    Args:
        query (str): A natural language question or query from the user.
        activities_file (str): The filename containing activities data.

    Returns:
        bool: A boolean indicating whether we could find a matching activity or not. If False then the latest activity will be selected.
        str: A filename containing the relevant activity JSON.

    """
    with open(activities_file, "r") as f:
        activities = json.load(f)

    activity_file = "data/selected_activity.json"

    try:
        activity = utils.select_activity_llm(query, activities)
        found_activity = True
        with open(activity_file, "w") as f:
            json.dump(activity, f)
    except Exception:
        # default to the latest activity
        activity = activities[-1]
        found_activity = False
        with open(activity_file, "w") as f:
            json.dump(activity, f)

    return found_activity, activity_file


def read_activity(activity_file: str) -> str:
    """Reads and displays the selected activity, including distance, time, and other data.

    Args:
        activity_file (str): A file containing activity data.

    Returns:
        str: A message containing the activity's details.
    """
    with open(activity_file, "r") as f:
        activity = json.load(f)
    return str(activity)


def enrich_activity(activity_file: str) -> str:
    """Enriches a selected activity with map data such as street names.

    Includes nearby landmarks and street names along the activity's route. This tool
    extracts information from the activity's polyline and location data.

    Args:
        activity_file (str): A file containing activity data, including map information.

    Returns:
        str: A filename containing the activity enriched with map information.
    """
    g = GMapsClient()
    with open(activity_file, "r") as f:
        activity = json.load(f)
    return g.fetch_map_details(activity["map"]["summary_polyline"])


def update_activity(activity_file: str, new_description: str) -> str:
    """Updates the description of a selected activity using the Strava API.

    Args:
        activity_file (str): A file containing activity data.
        new_description (str): The new description to be added to the activity.

    Returns:
        str: A message confirming the activity has been updated.
    """
    with open(activity_file, "r") as f:
        activity = json.load(f)

    s = StravaClient(get_access_token())
    response = s.update_activity(activity["id"], new_description)

    return response


def get_tools():
    return [
        fetch_activities,
        select_activity,
        read_activity,
        enrich_activity,
        update_activity,
    ]
