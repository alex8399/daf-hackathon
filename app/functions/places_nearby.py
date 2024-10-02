import os
import sys
import googlemaps # library for Google Maps API. Use 'pip install googlemaps' to install

# Modifying the root path for imports
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import API_.route_API as route_API # file with class RouteAPI
from geopy.distance import geodesic


class PlacesNearby:
    """Class for interacting with Google Maps API 
    to get places nearby given coordinates, radius and types of places."""

    def __init__(self, api_key: str):
        """Initializes the class with the API key."""
        self.gmaps = googlemaps.Client(key=api_key)
        self.places = []
        self.shortlist = []
        self.route_object = route_API.RouteAPI(API_key=api_key)


    def get_places(self, lat: float, lng: float, radius: int, types: list[str]) -> list[dict]:
        """Given coordinates, radius and types, retrieves objects within a certain radius
         :param lat: latitude
         :param lng: longitude
         :param radius: radius
         :param types: list of types of places (fast_food_restaurant, coffee_shop and so on)
         :return: list of dictionaries with keys 'distance', 'name', 'rating', 'vicinity' and 'location'
         A full list of supported types: 
         https://developers.google.com/maps/documentation/places/web-service/place-types"""

        places = []

        for place_type in types:
            query_result = self.gmaps.places_nearby(
                location=(lat, lng),
                radius=radius,
                #max_price=4,
                type=place_type)

            for place in query_result.get('results', []):
                place_info = {
                    'name' : place.get('name', 'No name'), 
                    'rating' : place.get('rating', 'No rating'), 
                    'vicinity' : place.get('vicinity', 'No vicinity'), # address
                    'location' : place.get('geometry', {}).get('location', 'No location'), # dict with keys 'lat' and 'lng'
                    'distance' : self.route_object.get_duration_and_distance(
                        (lat, lng), (place.get('geometry', {}).get('location', 'No location')))['distance'],
                    'price_level' : place.get('price_level', 'No price level')
                }
                places.append(place_info) # places is a list of dictionaries

        # remove duplicates
        unique_places = {f"{place['name']} | {place['location']['lat']} | {place['location']['lng']}": place for place in places} 
        
        self.places = list(unique_places.values())

        # remove places that are further than radius
        self.places = [place for place in self.places if geodesic(
            (lat, lng), (place['location']['lat'], place['location']['lng'])).meters <= radius]
        
        # removes places with price level higher than 2
        self.places = [place for place in self.places 
                       if (isinstance(place['price_level'], int) and place['price_level'] <= 2) 
                       or place['price_level'] == 'No price level']

        return self.places
    

    def make_shortlist(self) -> list[dict]:
        """Given a list of places, returns a shortlist of the 3 closest places.
        :param places: list of dictionaries with keys 'name', 'rating', 'vicinity' and 'location'
        :return: list of dictionaries with keys 'distance', 'name', 'rating', 'vicinity' and 'location'"""

        closest_places = sorted(self.places, key=lambda x: x['distance'])[:3]

        return closest_places