import os
from typing import List

import googlemaps
import polyline
from dotenv import load_dotenv

load_dotenv()

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

def fetch_map_details(map_data: dict, landmarks: bool = True) -> str:
    """
    Fetch nearby street names and landmarks based on the map data.
    Args:
        map_data (dict): The input map data containing summary_polyline and start/end_latlng.
    Returns:
        str: A formatted string with street names and landmarks.
    """
    # Decode the polyline into a list of coordinates
    coordinates = polyline.decode(map_data['polyline'])
    coordinates = select_equidistant_elements(coordinates, 10) # select 10 equally spaced coordinates from the map
    
    results = []
    
    # Fetch information for each coordinate
    for lat, lng in coordinates:
        reverse_geocode = gmaps.reverse_geocode((lat, lng))
        if reverse_geocode:
            # Extract street names
            address = reverse_geocode[0].get("formatted_address", "Unknown Location")
            results.append(f"{address}")

        if landmarks:
            # Optionally fetch landmarks. TODO: make this better. It should recognise if I ran around a local park
            places = gmaps.places_nearby(location=(lat, lng), radius=200, keyword=None, type="tourist_attraction")
            places = [x for x in places["results"] if "park" in x["types"] and "tourist_attraction" in x["types"]]
            if places:
                places = [p["name"] for p in places]
                results.append(f"{places[:3]}")

    return "\n".join(results)

def select_equidistant_elements(data: List, n: int = 10) -> List:
    N = len(data)
    if N <= 10:
        return data
    step = N / n
    indices = [int(i * step) for i in range(n)]
    return [data[i] for i in indices]

# Example Usage
# map_data = {
#     "polyline": "wehyHrfPI_@Ee@KcFCgBCOOUaAsB[SGBCCAWKSGIUMGQGIc@OSOe@Aa@I}@{AYo@}@sAs@mA]YYk@_@c@w@cAe@gA]oAYs@EY_@s@Y}@c@q@a@iAWe@?a@F}@Jm@Fs@@c@KyDYiE?k@IwACgAE}@Ge@S{D?i@I}A@k@CEGCE?EE?EEAGSDm@M{ADs@O_DGa@M}A[eBHs@Cs@LiAVgBXuALmAToAF{CFs@HWD_AGuB]wBGgBO}AEiAUsCAm@EW?w@_@aEEwCM[AIKyAEkBIm@I_A?QDQZo@FY@WGuAScBCk@KqAAc@Dm@FMNI\\Kb@QXGJ?p@Rn@^h@f@bAjATFXA\\]PMJQTQ`ByB\\]x@eA\\Yb@UHIXi@L[v@kA\\w@VaADiAIyAKs@I_BAe@Bw@HyAHu@|@eDDAFJBdALr@d@l@`@\\p@x@~@z@J@VEbA@T?RG^HJFFLNn@VxB?x@g@`DSd@M^EXFRTd@r@z@\\RBDDPCP[p@Up@MPIV_@n@Ff@Rd@L\\Fd@Rr@T^JJFNG\\Un@CTWj@IVCPFP@TEVe@nAWd@a@jAAHBb@?RFHLjAHJTVNbACj@O`@UfE@VAD?PH|AAx@Db@D~BAvAMhAAb@?PHZMf@?t@]dHCt@W|CKv@El@I`@?b@KlB@j@ETP`GH|@HbBB~A_@tBWr@o@|@AP?PFJVRxBnADL@^R\\hA`Ab@RlBjBjBvADR?HGP}@nBm@~AWh@@f@If@Sf@m@lAe@t@Ur@_@r@Kd@a@nA_@r@Uj@e@jBIn@OjB?nAGnA@bABRBDPRJ?NEJDNAJDDHA\\Ul@YZMV_@d@MFONYj@[\\ELe@h@Qf@@^FXj@hANb@Zh@BR?dAFfADjB@jBLr@",
#     "start_latlng": [51.492029, -0.094478],
#     "end_latlng": [51.491859, -0.094864]
# }

# details = fetch_map_details(map_data)
# details = gmaps.places("Southwark Park")
