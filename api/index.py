import fiona
import geopandas as gpd
from flask import Flask, render_template, jsonify
import pandas as pd
import json

app = Flask(__name__)

# File paths for each group
file_paths = {
    "group1": "./input/geojson/group1.json",
    "group2": "./input/geojson/group2.json",
    "group3": "./input/geojson/group3.json",
    "group4": "./input/geojson/group4.json",
    "group5": "./input/geojson/group5.json",
}

gdfs = {}

# Function to load geospatial data using fiona (instead of pyproj)
def load_geojson_data(file_path):
    try:
        with fiona.open(file_path, 'r') as src:
            return [feature for feature in src]
    except Exception as e:
        print(f"Error reading the GeoJSON file at {file_path}: {e}")
        return None

# Function to process waypoints into a GeoDataFrame
def process_waypoints(waypoints, participant_name):
    extracted_data = []

    for wp in waypoints:
        position = wp.get('position', {})
        coords = position.get('coords', {})
        interaction = wp.get('interaction', {})

        # Ensure all necessary keys are present
        data_entry = {
            'timestamp': wp.get('timestamp'),
            'latitude': coords.get('latitude'),
            'longitude': coords.get('longitude'),
            'altitude': coords.get('altitude'),
            'speed': coords.get('speed'),
            'heading': coords.get('heading'),
            'accuracy': coords.get('accuracy'),
            'taskNo': wp.get('taskNo'),
            'taskCategory': wp.get('taskCategory'),
            'panCount': interaction.get('panCount'),
            'zoomCount': interaction.get('zoomCount'),
            'rotation': interaction.get('rotation'),
            'participant': participant_name
        }

        # Skip waypoint if latitude or longitude are missing
        if data_entry['latitude'] is None or data_entry['longitude'] is None:
            continue

        extracted_data.append(data_entry)

    return extracted_data

# Function to create the GeoDataFrame from extracted data
def create_geodataframe(extracted_data):
    gdf = gpd.GeoDataFrame(
        extracted_data,
        geometry=[(d['longitude'], d['latitude']) for d in extracted_data],  # Use longitude, latitude directly
        crs="EPSG:4326"  # Set the coordinate reference system (WGS 84)
    )
    gdf['heading_range'] = gdf['heading'].apply(assign_heading_range)
    return gdf

# Function to assign heading ranges based on the heading value
def assign_heading_range(heading):
    if 0 <= heading < 90:
        return "0 - 90"
    elif 90 <= heading < 180:
        return "90 - 180"
    elif 180 <= heading < 270:
        return "180 - 270"
    elif 270 <= heading <= 360:
        return "270 - 360"
    else:
        return None  # Handle invalid heading values

# Main processing function for each group
def process_group(file_path, participant_name):
    data = load_geojson_data(file_path)
    if data is None:
        return None
    
    # Process features and convert to GeoDataFrame
    extracted_data = process_waypoints(data, participant_name)
    
    if not extracted_data:
        print(f"No valid data for group {participant_name}")
        return None
    
    return create_geodataframe(extracted_data)

# Function to load all groups into the gdfs dictionary
def load_all_groups():
    participants = {
        "group1": "Group-1",
        "group2": "Group-2",
        "group3": "Group-3",
        "group4": "Group-4",
        "group5": "Group-5",
    }

    for group, participant_name in participants.items():
        file_path = file_paths.get(group)
        gdf = process_group(file_path, participant_name)
        if gdf is not None:
            gdfs[group] = gdf

# Route to render the homepage
@app.route("/")
def index():
    return render_template("index.html")

# Route to return all data in GeoDataFrames as JSON
@app.route("/data")
def get_data():
    if gdfs:
        # Concatenate all GeoDataFrames into one DataFrame
        data_all = pd.concat(gdfs.values())
        data_all = data_all.to_crs(epsg=3857)  # Convert CRS to Web Mercator
        return data_all.drop(columns='geometry').to_json(orient='records')
    else:
        return jsonify({"error": "No data available"}), 500

# Initialize the loading of all groups on startup
load_all_groups()

def handler(req, res):
    return app(req, res)

if __name__ == "__main__":
    app.run(debug=True)
