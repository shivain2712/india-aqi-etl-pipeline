import pandas as pd
import logging
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

#load .env file and load key-value pairs into memory
load_dotenv()

def get_db_connection():
    """
    Opens and returns a connection to the local postegresql database
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
def upsert_cities(conn, cities: list[dict]) -> dict[str, int]:
    """
    Inserts cities into dim_city (skipping any which already exist)
    and returns a {city_name: city_id} lookup dictionary
    """
    insert_query = """
    INSERT INTO dim_city(city_name, state, latitude, longitude, region)
    VALUES %s
    ON CONFLICT (city_name) DO NOTHING
    """
    
    #convert list of dicts into list of tuples for execute_values matching the sql column order
    city_tuples = [
        (c["city_name"], c["state_name"], c["latitude"], c["longitude"], c["region"])
                   for c in cities
    ]
    
    with conn.cursor() as cur:
        execute_values(cur, insert_query, city_tuples)
        cur.execute("SELECT city_name, city_id FROM dim_city")
        city_map = {row[0]: row[1] for row in cur.fetchall()}
    
    conn.commit()
    logger.info(f"dim_city synced. Active cities in warehouse : {len(city_map)}")
    
    return city_map


def upsert_hourly_data(conn, city_id: int, df: pd.DataFrame) -> int:
    if df.empty:
        logger.warning(f"No data to insert for city_id {city_id}")
        return 0
    
    clean_df = df.where(pd.notna(df), None)
    
    records = [
        (
            city_id,
            row.recorded_at.to_pydatetime(),
            row.pm2_5,
            row.pm10,
            row.temperature_c,
            row.relative_humidity,
            row.wind_speed_kmh,
            row.aqi_category 
        )
        for row in clean_df.itertuples(index=False)
    ]    

    upsert_query = """
    INSERT INTO fct_hourly_environment (
        city_id, recorded_at, pm2_5, pm10, temperature_c, relative_humidity, wind_speed_kmh, aqi_category
        )
        VALUES %s
        ON CONFLICT (city_id, recorded_at)
        DO UPDATE SET
            pm2_5 = EXCLUDED.pm2_5,
            pm10 = EXCLUDED.pm10,
            temperature_c = EXCLUDED.temperature_c,
            relative_humidity = EXCLUDED.relative_humidity,
            wind_speed_kmh = EXCLUDED.wind_speed_kmh,
            aqi_category = EXCLUDED.aqi_category,
            ingested_at = CURRENT_TIMESTAMP;
        """
    
    with conn.cursor() as cur:
        execute_values(cur, upsert_query, records)
        
    conn.commit()
    logger.info(f"Upserted {len(records)} rows of hourly data for city_id = {city_id}")
    return len(records)
    
    
if __name__ == "__main__":
    
    from src.extract import fetch_city_data
    from src.transform import transform_city_data
    from config.cities import CITIES
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    conn =  get_db_connection()
    try :
        city_map = upsert_cities(conn, CITIES)
        pune=CITIES[0]
        
        aqi_json, weather_json = fetch_city_data(pune, past_days=2)
        clean_df = transform_city_data(pune["city_name"], aqi_json, weather_json)
        upsert_hourly_data(conn, city_map[pune["city_name"]], clean_df)
    finally:
        conn.close()   