import json

import requests


# TODO: improve user token storage. Also make it so that it handles multiple
# users. Maybe via cookies?
def get_access_token() -> str:
    with open("token_storage.json", "r") as f:
        return json.load(f)["access_token"]


class StravaClient:
    def __init__(self, access_token: str):
        """
        Initializes the StravaAPI with the user's access token.

        Args:
            access_token (str): The OAuth access token for the Strava API.
        """
        self.base_url = "https://www.strava.com/api/v3"
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def fetch_activities(self, per_page: int = 30, page: int = 1) -> list:
        """
        Fetches a list of activities from the Strava API.

        Args:
            per_page (int): The number of activities to fetch per page. Default is 30.
            page (int): The page number to fetch. Default is 1.

        Returns:
            list: A list of activities in JSON format.
        """
        url = f"{self.base_url}/athlete/activities"
        params = {"per_page": per_page, "page": page}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    # def update_activity(self, activity_id: int, description: str) -> dict:
    #     """
    #     Updates the description of an existing activity.

    #     Args:
    #         activity_id (int): The ID of the activity to update.
    #         description (str): The new description for the activity.

    #     Returns:
    #         dict: The updated activity details in JSON format.
    #     """
    #     url = f"{self.base_url}/activities/{activity_id}"
    #     data = {"description": description}
    #     response = requests.put(url, headers=self.headers, data=data)

    #     if response.status_code == 200:
    #         return response.json()
    #     else:
    #         response.raise_for_status()
