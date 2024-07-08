import os 
import re
import sys 
import folium
import polyline
import streamlit as st

from folium import PolyLine, Marker, Icon
from streamlit_folium import st_folium

# Modifying the root path for imports
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config import API_KEY
from API_.route_API import RouteAPI
from functions.places_nearby import PlacesNearby

# Additional functions

def convert_to_tuple(coord_string):
    # Define the regular expression for a valid coordinate string
    coord_pattern = re.compile(r'^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$')
    
    # Match the string against the pattern
    match = coord_pattern.match(coord_string)
    
    if match:
        # Extract the coordinates and convert them to float
        lat, lon = map(float, match.groups())
        return (lat, lon)
    else:
        return coord_string

def convert_duration(duration_seconds):
    """
    Converts a duration from seconds to a human-readable format.
    
    Parameters:
    - duration_seconds: int, duration in seconds
    
    Returns:
    - str, duration in the format "X hours Y mins"
    """
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60

    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} {minutes} min{'s' if minutes != 1 else ''}"
    else:
        return f"{minutes} min{'s' if minutes != 1 else ''}"

def calculate_zoom_level(bounds):
    # Function to calculate zoom level based on bounds
    north_east, south_west = bounds
    lat_diff = abs(north_east[0] - south_west[0])
    lng_diff = abs(north_east[1] - south_west[1])
    
    # Simple heuristic to adjust zoom
    max_diff = max(lat_diff, lng_diff)
    if max_diff < 0.05:
        return 13
    elif max_diff < 0.1:
        return 12
    elif max_diff < 0.5:
        return 11
    elif max_diff < 1:
        return 10
    elif max_diff < 5:
        return 9
    else:
        return 7

# Initialize the RouteAPI
route_API = RouteAPI(API_KEY)

# Initialize the PlacesNearby
places_API = PlacesNearby(API_KEY)

# Streamlit page configuration
st.set_page_config(
    layout='wide'
)

# Streamlit sidebar inputs for origin and destination and time between stops
st.sidebar.title("Route Planner")
top_places = st.sidebar.text_input("Max Places", 3)
top_places = int(top_places)
origin = st.sidebar.text_input("Origin", "47.660738	, -2.971431	")
destination = st.sidebar.text_input("Destination", "48.387598, -4.459093")
drive_between_stops = st.sidebar.slider(
    label='Indicate approximate time between stops',
    min_value=1,
    max_value=8,
    step=1,
    format="%d"
)

# test coords: 47.660738	, -2.971431	
# 48.387598, -4.459093	

# Get route
routes = route_API.get_routes(convert_to_tuple(origin), convert_to_tuple(destination))

# The best route choice
route = routes[0]

# Get stop points within given hours betweens stops
stop_point_begin = route['start_location']
stop_point_end = route['end_location']
stop_points = route_API.get_stop_points(route, distance_between_points= 23.61 * int(drive_between_stops) * 60 * 60)

# st.write(route)
# PLACES EXTRACTION 

# get the list of cafes
cafe_list_at_stops = []

for dict_ in stop_points:
    lat, lon = dict_['lat'], dict_['lng']
    places = places_API.get_places(lat, lon, radius=20_000, types=['cafe'])
    for place in places:
        cafe_list_at_stops.append(place)

cafe_list = cafe_list_at_stops[:top_places] + places_API.get_places(lat=stop_point_begin['lat'], lng=stop_point_begin['lng'], radius=2000, types=['cafe'])[:top_places] + places_API.get_places(lat=stop_point_end['lat'], lng=stop_point_end['lng'], radius=2000, types=['cafe'])[:top_places]

# get the list of parkings
parking_list_at_stops = []

for dict_ in stop_points:
    lat, lon = dict_['lat'], dict_['lng']
    places = places_API.get_places(lat, lon, radius=20_000, types=['parking'])
    for place in places:
        cafe_list_at_stops.append(place)

parking_list = parking_list_at_stops[:top_places] + places_API.get_places(lat=stop_point_begin['lat'], lng=stop_point_begin['lng'], radius=2000, types=['parking'])[:top_places] + places_API.get_places(lat=stop_point_end['lat'], lng=stop_point_end['lng'], radius=2000, types=['parking'])[:top_places]


# Remove steps from the route dictionary
route.pop("steps")

# Decode the polyline string
polyline_str = str(route['polyline'])
coordinates = polyline.decode(polyline_str)

bounds = [[route['bounds']['northeast']['lat'], route['bounds']['northeast']['lng']],
          [route['bounds']['southwest']['lat'], route['bounds']['southwest']['lng']]]

zoom_level = calculate_zoom_level(bounds)
map_center = [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2]
map_ = folium.Map(location=map_center, zoom_start=zoom_level)

# Add the polyline to the map
polyline_layer = PolyLine(locations=coordinates, color='blue', weight=5)
map_.add_child(polyline_layer)

# MARKS ADDITION #

# Add markers for each cafe
for cafe in cafe_list:
    cafe_name = cafe['name']
    cafe_location = cafe['location']
    lat = cafe_location['lat']
    lng = cafe_location['lng']
    
    # Create a marker with a custom icon
    marker = Marker(
        location=[lat, lng],
        popup=cafe_name,
        icon=Icon(icon='coffee', prefix='fa', color='red')  # Customize the icon here
    )
    map_.add_child(marker)

# Add markers for each cafe
for parking in parking_list:
    parking_name = parking['name']
    parking_location = parking['location']
    lat = parking_location['lat']
    lng = parking_location['lng']
    
    # Create a marker with a custom icon
    marker = Marker(
        location=[lat, lng],
        popup=parking_name,
        icon=Icon(icon='square-parking', prefix='fa', color='blue')  # Customize the icon here
    )
    map_.add_child(marker)

# Add markers for each cafe
for stop in stop_points:
    stop_name = 'Take some rest at this point :)'
    lat = stop['lat']
    lng = stop['lng']
    
    # Create a marker with a custom icon
    marker = Marker(
        location=[lat, lng],
        popup=stop_name,
        icon=Icon(icon='pause', prefix='fa', color='orange')  # Customize the icon here
    )
    map_.add_child(marker)

# DISPLAYING THE STUFF

# Display the map in Streamlit
st.title("Route Map")

# Display the map 
output = st_folium(map_, width=1200, height=750)

# Handle the click event
# st.write(output)
if output['last_object_clicked']:
    clicked_lat = output['last_object_clicked']['lat']
    clicked_lng = output['last_object_clicked']['lng']
    st.write(f"You clicked on the marker at: {clicked_lat}, {clicked_lng}, {output['last_object_clicked_popup']}")

# display information about route

# prepare the time data
route_time = route['duration']
stops_time = len(stop_points) * 60 * 60

sleep_time = 0

total_time = route_time + stops_time + sleep_time

# Create columns
col1, col2 = st.columns(2)

# First column with route information
with col1:
    st.header("Route", divider='rainbow')
    st.markdown(f"""
        <p style='font-size:20px;'>From <strong style='color:blue;'>{route['start_address']}</strong> to <strong style='color:blue;'>{route['end_address']}</strong></p>
        <p style='font-size:20px;'>The estimated total time: <strong style='color:blue;'>{convert_duration(total_time)}</strong></p>
        <p style='font-size:20px;'>The estimated distance: <strong style='color:blue;'>{route['distance_text']}</strong></p>
    """, unsafe_allow_html=True)

# Second column with stop information
with col2:
    st.header("Stops", divider='rainbow')
    st.markdown(f"""
        <p style='font-size:20px;'>Number of Stops: <strong style='color:blue;'>{len(stop_points)}</strong></p>
        <p style='font-size:20px;'>Time spent at stops: <strong style='color:blue;'>{convert_duration(stops_time)}</strong></p>
        <p style='font-size:20px;'>Time spent at driving: <strong style='color:blue;'>{convert_duration(route_time)}</strong></p>
    """, unsafe_allow_html=True)
