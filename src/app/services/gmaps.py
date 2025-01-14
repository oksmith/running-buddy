import os
from typing import List

import googlemaps
import polyline
from dotenv import load_dotenv

load_dotenv()


class GMapsClient:
    def __init__(self):
        self.client = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

    def fetch_map_details(self, run_polyline: str, landmarks: bool = True) -> str:
        """
        Fetch nearby street names and landmarks based on the map data.
        Args:
            run_polyline (str): The input map data containing polyline.
        Returns:
            str: A formatted string with street names and landmarks.
        """
        # Decode the polyline into a list of coordinates
        coordinates = polyline.decode(run_polyline)

        # select 10 equally spaced coordinates from the map
        coordinates = select_equidistant_elements(coordinates, 10)

        results = []
        for lat, lng in coordinates:
            reverse_geocode = self.client.reverse_geocode((lat, lng))
            if reverse_geocode:
                # Extract street names
                address = reverse_geocode[0].get(
                    "formatted_address", "Unknown Location"
                )
                results.append(f"{address}")

            if landmarks:
                # Optionally fetch landmarks. TODO: make this better. It should recognise if I ran around a local park
                places = self.client.places_nearby(
                    location=(lat, lng),
                    radius=200,
                    keyword=None,
                    type="tourist_attraction",
                )
                places = [
                    x
                    for x in places["results"]
                    if "park" in x["types"] and "tourist_attraction" in x["types"]
                ]
                if places:
                    _ = [results.append(p["name"]) for p in places[:3]]

        return "\n".join(results)


def select_equidistant_elements(data: List, n: int = 10) -> List:
    N = len(data)
    if N <= 10:
        return data
    step = N / n
    indices = [int(i * step) for i in range(n)]
    return [data[i] for i in indices]
