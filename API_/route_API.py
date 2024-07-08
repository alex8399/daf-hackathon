import googlemaps
from datetime import datetime
from polyline import decode, encode
from math import sqrt

from typing import Tuple, Dict, List


class RouteAPI:
    __gmaps: googlemaps.Client
    __API_key: str

    __DEFAULT_DISTANCE_BETWEEN_POINTS: int = 50000
    __REGION: str = "NL"
    __MODE: str = "driving"
    
    __METERS_IN_KILOMETERS : int = 1000
    __SECONDS_IN_HOUR : int = 3600
    __SECONDS_IN_MINUTE : int = 60

    def __init__(self, API_key: str):
        self.__API_key = API_key
        self.__gmaps = googlemaps.Client(self.__API_key)

    def get_routes(self, origin: str | Dict | Tuple | List, destination: str | Dict | Tuple | List,
                   alternatives: bool = False, waypoints: List[str | Dict | Tuple | List] = None) -> List[Dict]:
        """
        Get route(s) from origin to destination.
        List of routes can be empty if there is no route between origin and destination.

        Args:
            origin (str | Dict | Tuple | List): The address or latitude/longitude value from which you wish to calculate directions.
            destination (str | Dict | Tuple | List): The address or latitude/longitude value from which you wish to calculate directions.
            alternatives (bool, optional): If True, more than one route may be returned in the response. Defaults to False.
            waypoints (List[str | Dict | Tuple | List]): Specifies an array of waypoints.
            Waypoints alter a route by routing it through the specified location(s). Defaults to None.

        Returns:
            List[Dict]: list of calculated route(s) from origin to destination.
        """

        raw_routes = self.__gmaps.directions(
            origin,
            destination,
            alternatives=alternatives,
            waypoints=waypoints,
            mode=self.__MODE,
            region=self.__REGION)

        routes = [self.__parse_route(raw_route) for raw_route in raw_routes]

        return routes

    def get_duration_and_distance(self, origin: str | Dict | Tuple | List, destination: str | Dict | Tuple | List) -> Dict | None:
        """
        Get duration and distance of route from origin to destination.
        Light version of get_routes for the cases when only duration and distance must be calculated.

        Args:
            origin (str | Dict | Tuple | List): The address or latitude/longitude value from which you wish to calculate directions.
            destination (str | Dict | Tuple | List): The address or latitude/longitude value from which you wish to calculate directions.

        Returns:
            Dict | None: Dictionary with duration (in seconds) and distance (in meters) from origin to destination.
            If there is no route from destination to origin, None is returned.
        """

        raw_routes = self.__gmaps.directions(
            origin,
            destination,
            mode=self.__MODE,
            region=self.__REGION)

        duration_and_distance = None

        if len(raw_routes) > 0:
            leg = raw_routes[0]["legs"][0]

            duration_and_distance = {
                "distance": leg["distance"]["value"],
                "distance_text": leg["distance"]["text"],
                "duration": leg["duration"]["value"],
                "duration_text": leg["duration"]["text"],
            }

        return duration_and_distance

    def get_stop_points(self, route: Dict, distance_between_points: int = __DEFAULT_DISTANCE_BETWEEN_POINTS,
                        traveled_distance: int = 0, only_first: bool = False) -> List[Dict]:
        """
        Calculate points on the route with indicated distance between each other.

        Args:
            route (Dict): Route from origin to destination.
            distance_between_points (int, optional): Distnace between points on the route (in meters).
            Defaults to __DEFAULT_DISTANCE_BETWEEN_POINTS.
            traveled_distance (int, optional): Distance which was passed by driver (in meters). Defaults to 0.
            only_first (bool, optional): If True, method returns only first stop point.
            If False, all stop points on the route are returned. Defaults to False.

        Returns:
            List[Dict]: list of points on the route.
            Point consists of dictionary which contains lattitude, longtitude and distance (in meters) on the route.
            Distance is not entirely precise. Some diviation from reality is possible due to calculatation in floating point numbers.
        """

        points, _, _ = self.__locate_stop_points(
            route, distance_between_points, traveled_distance, only_first)
        return points

    def get_point_on_route(self, route: Dict, coordinate: Dict, distance: int = None, time: int = None,
                           speed: int = None) -> Tuple[Dict | None, bool]:
        """
        Get point on the route in distance or in time (with indicated speed).
        Method receives coordinate of object, defines where it is located on the route and calculates point on the route
        in indicated distance. Instead of distance, method can take speed and time and calculates distance by it.
        Distance or time and speed must be always indicated.

        Args:
            route (Dict): Route.
            coordinate (Dict): Coordinate of object. Dictionary with fields 'lat' and 'lng'.
            distance (int): Distance from coordinate of object to the point (in meters). Defaults to None.
            time (ind): Time in which object will stop (in seconds). Defaults to None.
            speed (int): Speed of object (in meters per seconds). Defaults to None.

        Returns:
            Tuple[Dict | None, bool]: Coordinate of point on the route, indication whether point is an end of the route.
            If True, the end of the route was returned. Otherwise, False.
            If end of the route is closer to the object, than indicated distance, then the end of the route will be returned.
        """
        
        if distance is None:
            distance = int(time * speed)
        else:
            distance = int(distance)
        
        reached_route_end: bool = False
        predicted_point: Dict | None = None
        step_ind: int | None = self.__locate_step(route["steps"], coordinate)

        if step_ind is not None:
            left_step_in_current_step: Dict | None = self.__calculate_left_step(
                route["steps"][step_ind], coordinate)

            left_route = {
                "steps": route["steps"][step_ind + 1:]
            }

            if left_step_in_current_step is not None:
                left_route["steps"].insert(0, left_step_in_current_step)

            predicted_points, full_distance, _ = self.__locate_stop_points(
                left_route, distance, traveled_distance=0, only_first=True)

            if len(predicted_points) > 0:
                predicted_point = predicted_points[0]
            else:
                reached_route_end = True
                predicted_point = {
                    "lat" : route["end_location"]["lat"],
                    "lng" : route["end_location"]["lng"],
                    "distance" : full_distance
                }

        return predicted_point, reached_route_end

    def __locate_stop_points(self, route: Dict, distance_between_points: int = __DEFAULT_DISTANCE_BETWEEN_POINTS,
                             traveled_distance: int = 0, only_first: bool = False) -> Tuple[List[Dict], int, int]:
        
        points : List[Dict] = list()
        full_distance : int = 0
        distance : int = traveled_distance % distance_between_points

        for step in route["steps"]:
            distance += step["distance"]
            full_distance += step["distance"]

            if distance >= distance_between_points:
                new_points, distance = self.__aproximate_stop_points(
                    step, distance, distance_between_points, full_distance, only_first)
                points.extend(new_points)

                if only_first:
                    break

        return points, full_distance, distance

    def __locate_step(self, steps: List[Dict], coordinate: Dict) -> int | None:
        step_ind: int | None = None
        min_length_to_coordinate: float = float("inf")

        for ind, step in enumerate(steps):
            coordinate_ind, length_to_coordinate = self.__locate_coordinate(
                decode(step["polyline"]), coordinate)

            if coordinate_ind is not None and length_to_coordinate < min_length_to_coordinate:
                min_length_to_coordinate = length_to_coordinate
                step_ind = ind

        return step_ind

    def __calculate_left_step(self, step: Dict, coordinate: Dict) -> Dict | None:
        left_step: Dict | None = None
        polyline_coordinates: List[Tuple[float, float]] = decode(
            step["polyline"])
        sector_lengths, polyline_length = self.__calculate_sector_lengths(
            polyline_coordinates)

        coordinate_ind, _ = self.__locate_coordinate(
            polyline_coordinates, coordinate)

        if coordinate_ind is not None and coordinate_ind != len(polyline_coordinates) - 1 and step["distance"] > 0 and polyline_length > 0:
            distance_in_coordinate: float = 0.0
            for ind in range(coordinate_ind, len(sector_lengths)):
                distance_in_coordinate += sector_lengths[ind]

            if distance_in_coordinate > 0.0:
                left_step: Dict = {
                    "start_location": {
                        "lat": polyline_coordinates[coordinate_ind][0],
                        "lng": polyline_coordinates[coordinate_ind][1],
                    },
                    "end_location": {
                        "lat": polyline_coordinates[-1][0],
                        "lng": polyline_coordinates[-1][1],
                    },
                    "polyline": encode(polyline_coordinates[coordinate_ind:]),
                    "distance": int(step["distance"] / polyline_length * distance_in_coordinate),
                    "duration": None,
                }

        return left_step

    @staticmethod
    def __locate_coordinate(coordinates: List[Tuple[float, float]], locating_coordinate: Dict) -> Tuple[int | None, float]:
        closest_coordinate_ind: int | None = None
        smallest_distance: float = float("inf")

        for ind, coordinate in enumerate(coordinates):
            x, y = coordinate
            x_distance: float = locating_coordinate["lat"] - x
            y_distance: float = locating_coordinate["lng"] - y
            distance: float = sqrt(x_distance**2 + y_distance**2)

            if distance < smallest_distance:
                smallest_distance = distance
                closest_coordinate_ind = ind

        return closest_coordinate_ind, smallest_distance

    @staticmethod
    def __calculate_sector_lengths(coordinates: List) -> Tuple[List, float]:
        polyline_length = 0.0
        sector_lengths = list()

        for ind in range(0, len(coordinates) - 1):
            x_sector_length = coordinates[ind][0] - coordinates[ind+1][0]
            y_sector_length = coordinates[ind][1] - coordinates[ind+1][1]
            sector_length = sqrt(x_sector_length**2 + y_sector_length**2)

            sector_lengths.append(sector_length)
            polyline_length += sector_length

        return sector_lengths, polyline_length

    @staticmethod
    def __init_stop_point(lat: float, lng: float, distance: int) -> Dict:
        stop_point = {
            "lat": lat,
            "lng": lng,
            "distance": distance,
        }

        return stop_point

    @classmethod
    def __aproximate_stop_points(cls, step: Dict, distance: int, distance_between_points: int,
                                 full_distance: int, only_first: bool = False) -> Tuple[List[Dict], int]:

        points : List[Dict] = list()
        new_distance : int = 0
        coordinates : List[Tuple[float, float]] = decode(step["polyline"])

        if step["distance"] > 0 and len(coordinates) > 0:
            sector_lengths, polyline_length = cls.__calculate_sector_lengths(
                coordinates)

            first_stop_point_percent : float = abs(
                distance_between_points - (distance - step["distance"])) / step["distance"]
            next_stop_point_percent : float = distance_between_points / \
                step["distance"]

            current_polyline : float = 0.0
            current_percent : float = first_stop_point_percent
            stop_point_on_polyline : float = first_stop_point_percent * polyline_length
            next_stop_point_length : float = next_stop_point_percent * polyline_length

            for ind, sector_length in enumerate(sector_lengths):
                current_polyline += sector_length

                if current_polyline > stop_point_on_polyline:
                    points.append(cls.__init_stop_point(
                        coordinates[ind][0], coordinates[ind][1],
                        full_distance - step["distance"] + int(current_percent * step["distance"])))

                    current_percent += next_stop_point_percent
                    stop_point_on_polyline += next_stop_point_length
                    new_distance = full_distance - points[-1]["distance"]

                    if only_first:
                        break

        if len(points) == 0:
            points.append(
                cls.__init_stop_point(step["end_location"]["lat"], step["end_location"]["lng"], full_distance))

        return points, new_distance

    @classmethod
    def __parse_route(cls, raw_route: Dict) -> Dict:
        route = dict()

        route["bounds"] = raw_route["bounds"]
        
        route["start_address"] = raw_route["legs"][0]["start_address"]
        route["start_location"] = raw_route["legs"][0]["start_location"]
        
        route["end_address"] = raw_route["legs"][-1]["end_address"]
        route["end_location"] = raw_route["legs"][-1]["end_location"]
        
        route["distance"] = 0
        route["duration"] = 0
        route["steps"] = list()
        
        for leg in raw_route["legs"]:

            route["distance"] += leg["distance"]["value"]
            route["duration"] += leg["duration"]["value"]

            for raw_step in leg["steps"]:
                step = dict()

                step["start_location"] = raw_step["start_location"]
                step["end_location"] = raw_step["end_location"]
                step["distance"] = raw_step["distance"]["value"]
                step["duration"] = raw_step["duration"]["value"]
                step["polyline"] = raw_step["polyline"]["points"]

                route["steps"].append(step)
        
        route["distance_text"] = cls.__convert_meters_to_distance_text(route["distance"])
        route["duration_text"] = cls.__convert_seconds_to_duration_text(route["duration"])

        route["polyline"] = raw_route['overview_polyline']["points"]
        route["summary"] = raw_route["summary"]
        route["warnings"] = raw_route["warnings"]
        route["waypoint_order"] = raw_route["waypoint_order"]
        
        return route
    
    
    @classmethod
    def __convert_seconds_to_duration_text(cls, seconds: int) -> str:
        duration_text : str = ""
        
        hours : int = seconds // cls.__SECONDS_IN_HOUR
        seconds %= cls.__SECONDS_IN_HOUR
        minutes : int = seconds // cls.__SECONDS_IN_MINUTE
        
        if hours > 0:
            duration_text += "{} hour".format(hours)
            
            if hours > 1:
                duration_text += "s"
            
            if minutes > 0:
                duration_text += " "
        
        if minutes > 0:
            duration_text += "{} min".format(minutes)
            
            if minutes > 1:
                duration_text += "s"
        
        if hours == 0 and minutes == 0:
            duration_text = "0 mins"
        
        return duration_text
    
    
    @classmethod
    def __convert_meters_to_distance_text(cls, meters: int) -> str:
        distance_text : str = ""
        
        if meters >= 99:
            kilometers : float = meters // cls.__METERS_IN_KILOMETERS
            
            if kilometers < 100:
                distance_text = "{:.1f} km".format(meters / cls.__METERS_IN_KILOMETERS)
            else:
                distance_text = "{} km".format(kilometers)
            
        else:
            distance_text = "{} m".format(meters)
        
        return distance_text