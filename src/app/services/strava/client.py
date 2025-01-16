import json

import requests
# from src.app.core.exceptions import StravaAPIException # TODO: write a better StravaAPIException?


# TODO: improve user token storage. Also make it so that it handles multiple
# users. Maybe via cookies?
def get_access_token() -> str:
    with open("token_storage.json", "r") as f:
        return json.load(f)["access_token"]


class StravaClient:
    def __init__(self, access_token: str):
        self.base_url = "https://www.strava.com/api/v3"
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def fetch_activities(self, per_page: int = 30, page: int = 1) -> list:
        """
        Fetches a list of activities from the Strava API.

        Args:
            per_page (int): The number of activities to fetch per page. Default is 30.
            page (int): The page number to fetch. Default is 1.

        Returns:
            list: A list of activities in JSON format.
        """
        try:
            response = requests.get(
                f"{self.base_url}/athlete/activities",
                headers=self.headers,
                params={"per_page": per_page, "page": page},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch activities: {str(e)}")

    async def update_activity(self, activity_id: int, description: str) -> dict:
        """
        Updates the description of an existing activity.

        Args:
            activity_id (int): The ID of the activity to update.
            description (str): The new description for the activity.

        Returns:
            dict: The updated activity details in JSON format.
        """
        if not isinstance(activity_id, int) or activity_id <= 0:
            raise ValueError("Activity ID must be a positive integer")

        try:
            response = requests.put(
                f"{self.base_url}/activities/{activity_id}",
                headers=self.headers,
                json={"description": description},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to update activity: {str(e)}")
