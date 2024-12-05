visualcrossing_api = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{start_date}{end_date}?key={api_key}&unitGroup={unitGroup}"

import os
import requests
import json
from datetime import datetime
import time

from dotenv import load_dotenv
load_dotenv()
VisualCrossing_API_Key = os.getenv("VisualCrossing_API_Key")
Redis_Key = os.getenv("Redis_Key")

Redis_Host = os.getenv("Redis_Host")

if not VisualCrossing_API_Key:
    raise ValueError("VisualCrossing_API_Key not found")

import argparse
parser = argparse.ArgumentParser(description="Fetch weather data using various apis")
parser.add_argument("location",
                    type=str,
                    help="""The location of the place, could be partial address
Accepts coordinates in the form latitude,longitude"""
)
parser.add_argument("--start", type=str, default="", help="The start date (YYYY-MM-DD)")
parser.add_argument("--end", type=str, default="", help="The end date (YYYY-MM-DD)")
parser.add_argument("--unit", type=str, default="metric", help="The system of units used for the output data. Supported values are us, uk, metric, base. Default is metric")
parser.add_argument(
    "--no-cache", 
    action="store_true", 
    help="Fetch data directly from the API, ignoring the cache."
)
parser.add_argument("--do-not-cache",
    action="store_false",
    help="Does not store the current request in cache")

# Get data
args = parser.parse_args()

# Check if date format is correct
try:
    if args.start:
        # Try to convert the start date string to a time tuple
        time.strptime(args.start, "%Y-%m-%d")
    if args.end:
        # Try to convert the end date string to a time tuple
        time.strptime(args.end, "%Y-%m-%d")
except ValueError:
    print("Invalid date format! Use YYYY-MM-DD.")
    exit(1)

# Parse data

location = args.location
start_date = args.start
end_date = args.end
unitGroup = args.unit
no_cache = args.no_cache
do_not_cache = args.do_not_cache



request_key = f"{location}:start_{start_date}:end_{end_date}"

response = dict()

# Caching using redit
import redis

cache = redis.Redis(
  host=Redis_Host,
  port=12861,
  password=Redis_Key)

response_code = 0
cache_data = None if no_cache else cache.get(request_key)
cache_content = ""
if cache_data:
    cached_content = json.loads(cache_data)
    data = cached_content["data"]
    cached_timestamp = cached_content["timestamp"]
    print(f"Cache timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cached_timestamp))}")
    response_code = 200
else:
    visualcrossing_url = visualcrossing_api.format(
    location=location,
    start_date=(start_date or "") +"/",
    end_date=end_date,
    api_key=VisualCrossing_API_Key,
    unitGroup=unitGroup  
)
    response['VisualCrossing'] = requests.get(visualcrossing_url)
    data = response['VisualCrossing'].json()
    response_code = response['VisualCrossing'].status_code
    if response_code == 200:
        print("Using API")
        print(do_not_cache)
        if do_not_cache:
            cache_content = {
                "data": data,
                "timestamp": time.time()  # Current time as a UNIX timestamp
            }
            print(json.dumps(cache_content, indent = 4))
            cache.set(request_key,json.dumps(cache_content), ex=600)

weather = dict()

if response_code == 200:
    weather["latitude"] = data.get("latitude")
    weather["longitude"] = data.get("longitude")
    weather["address"] = data.get('resolvedAddress')
    weather["timezone"] = data.get("timezone")
    weather["description"] = data.get("description")
    weather["alerts"] = data.get("alerts")
    weather["current_conditions"] = data.get("currentConditions")
    weather["forecast_days"] = data.get("days", [])

    # Print location and general information

    print(f"\nLocation: {weather.get('address', 'N/A')}")
    print(f"Latitude: {weather.get('latitude', 'N/A')}")
    print(f"Longitude: {weather.get('longitude', 'N/A')}")
    print(f"Timezone: {weather.get('timezone', 'N/A')}")
    print(f"Description: {weather.get('description', 'No description available')}")

    # Print alerts (if any)
    alerts = weather.get("alerts")
    if alerts:
        print("\nWeather Alerts:")
        for alert in alerts:
            print(f"- {alert.get('event', 'Unknown Alert')}: {alert.get('description', 'No details available')}")
    else:
        print("\nNo weather alerts at this time.")

    # Print current conditions
    current_conditions = weather.get("current_conditions")
    if current_conditions:
        print("\nCurrent Conditions:")
        print(f"- Temperature: {current_conditions.get('temp', 'N/A')}°")
        print(f"- Humidity: {current_conditions.get('humidity', 'N/A')}%")
        print(f"- Wind Speed: {current_conditions.get('windspeed', 'N/A')} km/h")
        print(f"- Conditions: {current_conditions.get('conditions', 'N/A')}")
    else:
        print("\nNo current conditions data available.")

    # Print forecast days (tabular format)
    forecast_days = weather.get("forecast_days", [])
    if forecast_days:
        print("\nWeather Forecast:")
        print(f"{'Date':<12}{'Max Temp':<10}{'Min Temp':<10}{'Conditions':<20}")
        print("-" * 50)
        for day in forecast_days:
            date = day.get("datetime", "N/A")
            max_temp = day.get("tempmax", "N/A")
            min_temp = day.get("tempmin", "N/A")
            conditions = day.get("conditions", "N/A")
            print(f"{date:<12}{max_temp:<10}{min_temp:<10}{conditions:<20}")
    else:
        print("\nNo forecast data available.")
else:
    print("Error", response['VisualCrossing'].status_code, response['VisualCrossing'].text)