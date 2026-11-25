import pandas as pd
import logging

logger = logging.getLogger(__name__)

def classify_cpcb_aqi(pm25: float) -> str:
    """
    Maps the PM2.5 concentration to official Indian CPCB AQI categories
    """
    if pd.isna(pm25):
        return "Unknown"
    elif pm25 <= 30:
        return "Good"
    elif pm25 <= 60:
        return "Satisfactory"
    elif pm25 <= 90:
        return "Moderate"
    elif pm25 <=120:
        return "Poor"
    elif pm25 <= 250:
        return "Very Poor"
    else:
        return "Severe"

def transform_city_data(city_name : str, aqi_json : dict, weather_json : dict) -> pd.DataFrame :
    """
    Flattens raw AQI and weather JSON into Pandas DataFrame, merges them on timestamp, applies
    data quality checks and enriches them with Indian CPCB AQI categories.
    """
    logger.info(f"Transforming weather and AQI data for {city_name}")
    
    #flatten json in dataframes
    aqi_df = pd.DataFrame(aqi_json["hourly"])
    weather_df = pd.DataFrame(weather_json["hourly"])
    
    #rename columns to match postgres table schema
    aqi_df = aqi_df.rename(columns={"time" : "recorded_at"})
    weather_df = weather_df.rename(
        columns={
        "time" : "recorded_at",
        "temperature_2m" : "temperature_c",
        "relative_humidity_2m" : "relative_humidity",
        "wind_speed_10m" : "wind_speed_kmh"
        }
    )
    
    #merge aqi and weather on timestamp
    df = pd.merge(aqi_df, weather_df, on="recorded_at", how="inner")
        
    #proper datetime format
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
        
    initial_rows = len(df)
    
    #data quality checks
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    df = df[
        df["recorded_at"].notna() &
        (df["recorded_at"] <= now) & #drop future forecast hours
        (df["pm2_5"].notna() | (df["pm2_5"] >= 0)) &
        (df["pm10"].notna() | (df["pm10"] >= 0)) &
        (df["relative_humidity"].notna() | (df["relative_humidity"].between(0,100)))
    ].copy()   
    
    dropped_rows = initial_rows - len(df)
    if dropped_rows > 0:
        logger.info(f"Filtered out {dropped_rows} rows of invalid data/future forecast hours for {city_name}.")
        
    #enrich with CPCB AQI categories
    df = df.rename(columns={"cpcb_aqi_category" : "aqi_category"})
    df["aqi_category"] = df["pm2_5"].apply(classify_cpcb_aqi)
    
    logger.info(f"Transformation complete for {city_name} : {len(df)} rows of valid data.")
    
    return df

if __name__ == "__main__":
    from src.extract import fetch_city_data
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    test_city = {"city_name": "Pune", "latitude": 18.5204, "longitude": 73.8567}
    
    aqi_raw, weather_raw = fetch_city_data(test_city, past_days=2)
    clean_df = transform_city_data(test_city["city_name"], aqi_raw, weather_raw)
    
    print("\n ----- Clean DataFrame preview -----")
    print(clean_df)
    print("\n ----- AQI Category breakdown -----")
    print(clean_df["aqi_category"].value_counts())
    
        
