import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = "./tokens.json"

# --- Helpers for unit conversions ---
def c_to_f(c):
    return round((c * 9/5) + 32, 1) if c is not None else None

def mm_to_in(mm):
    return round(mm * 0.0393701, 2) if mm is not None else None

def kmh_to_mph(kmh):
    return round(kmh * 0.621371, 1) if kmh is not None else None

def format_unix_time(unix_ts):
    # Converts to HH:MM in your local time
    return datetime.fromtimestamp(unix_ts).strftime("%-I:%M %p")

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)

# --- Get Netatmo access token ---
def get_access_token():
    tokens = load_tokens()

    # Try refresh token if available
    if "refresh_token" in tokens:
        print("🔄 Using refresh token...")
        try:
            response = requests.post("https://api.netatmo.com/oauth2/token", data={
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": os.getenv("NETATMO_CLIENT_ID"),
                "client_secret": os.getenv("NETATMO_CLIENT_SECRET"),
            })
            response.raise_for_status()
            new_tokens = response.json()
            save_tokens(new_tokens)
            return new_tokens["access_token"]
        except requests.HTTPError as e:
            print("⚠️ Refresh token failed, falling back to password grant.")

    # Fallback: Password grant
    print("🔐 Using password login...")
    response = requests.post("https://api.netatmo.com/oauth2/token", data={
        "grant_type": "password",
        "client_id": os.getenv("NETATMO_CLIENT_ID"),
        "client_secret": os.getenv("NETATMO_CLIENT_SECRET"),
        "username": os.getenv("NETATMO_USERNAME"),
        "password": os.getenv("NETATMO_PASSWORD"),
        "scope": "read_station"
    })
    response.raise_for_status()
    new_tokens = response.json()
    save_tokens(new_tokens)
    return new_tokens["access_token"]

def get_air_quality_status(co2):
    if co2 is None:
        return "Unknown"
    elif co2 < 800:
        return "Good"
    elif co2 < 1200:
        return "Moderate"
    else:
        return "Poor"

# --- Get weather data from Netatmo ---
def get_weather_data(token):
    url = "https://api.netatmo.com/api/getstationsdata"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    devices = response.json()["body"]["devices"]

    base = devices[0]
    modules = base["modules"]

    # Identify modules
    outdoor = next((m for m in modules if m["type"] == "NAModule1"), None)
    wind = next((m for m in modules if m["type"] == "NAModule2"), None)
    rain = next((m for m in modules if m["type"] == "NAModule3"), None)

    return {
        # Indoor
        "indoor_temp_c": base["dashboard_data"].get("Temperature"),
        "indoor_humidity": base["dashboard_data"].get("Humidity"),
        "co2": base["dashboard_data"].get("CO2"),
        "pressure": base["dashboard_data"].get("Pressure"),
        "noise": base["dashboard_data"].get("Noise"),

        # Outdoor
        "outdoor_temp_c": outdoor["dashboard_data"].get("Temperature") if outdoor else None,
        "outdoor_humidity": outdoor["dashboard_data"].get("Humidity") if outdoor else None,

        # Rain
        "rain_1h": rain["dashboard_data"].get("sum_rain_1") if rain else None,
        "rain_24h": rain["dashboard_data"].get("sum_rain_24") if rain else None,

        # Wind
        "wind_strength": wind["dashboard_data"].get("WindStrength") if wind else None,
        "gust_strength": wind["dashboard_data"].get("GustStrength") if wind else None,
        "wind_angle": wind["dashboard_data"].get("WindAngle") if wind else None,
        "gust_angle": wind["dashboard_data"].get("GustAngle") if wind else None,
    }

# --- Get OpenWeather Forecast ---

def get_forecast3():
    key = os.getenv("OPENWEATHER_API_KEY")
    lat = os.getenv("LAT")
    lon = os.getenv("LON")

    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "exclude": "minutely,hourly,alerts",
        "units": "imperial",  # use "metric" if needed
        "appid": key
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    today = data["daily"][0]

    return {
        "forecast_high": round(today["temp"]["max"]),
        "forecast_low": round(today["temp"]["min"]),
        "forecast_humidity": today["humidity"],
        "forecast_rain_in": mm_to_in(today.get("rain", 0)),
        "forecast_rain_chance": round(today.get("pop", 0) * 100),
        "sunrise": format_unix_time(today["sunrise"]),
        "sunset": format_unix_time(today["sunset"])
    }


# --- Push data to usetrmnl.com ---
def push_to_terminal(data):
    safe = lambda val, suffix="": f"{val}{suffix}" if val is not None else "—"


    merge_variables = {
        # Converted + formatted
        "indoor_temp": safe(c_to_f(data["indoor_temp_c"]), "°F"),
        "outdoor_temp": safe(c_to_f(data["outdoor_temp_c"]), "°F"),
        "indoor_humidity": safe(data["indoor_humidity"], "%"),
        "outdoor_humidity": safe(data["outdoor_humidity"], "%"),
        "co2": safe(data["co2"], " ppm"),
        "air_quality": get_air_quality_status(data["co2"]),
        "pressure": safe(data["pressure"], " mbar"),
        "noise": safe(data["noise"], " dB"),
        "rain_1h": safe(mm_to_in(data["rain_1h"]), " in"),
        "rain_24h": safe(mm_to_in(data["rain_24h"]), " in"),
        "wind_speed": safe(kmh_to_mph(data["wind_strength"]), " mph"),
        "gust_speed": safe(kmh_to_mph(data["gust_strength"]), " mph"),
        "wind_angle": safe(data["wind_angle"], "°"),
        "gust_angle": safe(data["gust_angle"], "°"),
        "forecast_high": safe(data["forecast_high"], "°F"),
        "forecast_low": safe(data["forecast_low"], "°F"),
        "forecast_humidity": safe(data["forecast_humidity"], "%"),
        "forecast_rain_in": safe(data["forecast_rain_in"], " in"),
        "forecast_rain_chance": safe(data["forecast_rain_chance"],  "%"),
        "sunrise": data["sunrise"],
        "sunset": data["sunset"],


        # Optional: combined message
        "message": (
            f"🌡️ {safe(c_to_f(data['outdoor_temp_c']), '°F')} out / {safe(c_to_f(data['indoor_temp_c']), '°F')} in\n"
            f"💧 {safe(data['outdoor_humidity'], '%')} out / {safe(data['indoor_humidity'], '%')} in\n"
            f"🌬️ {safe(kmh_to_mph(data['wind_strength']), ' mph')} wind, Gusts {safe(kmh_to_mph(data['gust_strength']), ' mph')}\n"
            f"☔ Rain: {safe(mm_to_in(data['rain_1h']), ' in')} (1h), {safe(mm_to_in(data['rain_24h']), ' in')} (24h)"
        )
    }

    webhook_url = os.getenv("TERMINAL_WEBHOOK_URL")
    response = requests.post(webhook_url, json={"merge_variables": merge_variables})
    response.raise_for_status()
    print("✅ Sent to Terminal:", merge_variables)

# --- Main execution ---
if __name__ == "__main__":
    token = get_access_token()
    netatmo = get_weather_data(token)
    forecast = get_forecast3()
    combined = { **netatmo, **forecast }
    push_to_terminal(combined)