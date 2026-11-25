import logging
import requests

logger = logging.getLogger(__name__)

AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_city_data(city: dict, past_days: int = 30) -> tuple[dict, dict]:
    """
    Fetches hourly air quality and weather JSON data for a single city
    from the Open-Meteo REST APIs.
    """
    city_name = city["city_name"]
    logger.info(f"Extracting {past_days} days of AQI & weather data for {city_name}...")

    aqi_params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": "pm2_5,pm10,nitrogen_dioxide,european_aqi",
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }
    
    weather_params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }
    
    aqi_response = requests.get(AQI_URL, params=aqi_params, timeout=15)
    aqi_response.raise_for_status()
    
    weather_response = requests.get(WEATHER_URL, params=weather_params, timeout=15)
    weather_response.raise_for_status()
    
    logger.info(f"Successfully extracted data for {city_name}.")
    return aqi_response.json(), weather_response.json()


#Sample Test Block

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    test_city = {"city_name": "Pune", "latitude": 18.5204, "longitude": 73.8567}
    aqi_json, weather_json = fetch_city_data(test_city, past_days=2)

    print("Sample AQI timestamps:", aqi_json["hourly"]["time"][:3])
    print("Sample PM2.5 values:", aqi_json["hourly"]["pm2_5"][:3])
    print("Sample Temp (°C):", weather_json["hourly"]["temperature_2m"][:3])