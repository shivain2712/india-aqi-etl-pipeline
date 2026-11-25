import logging
import os
import time
from config.cities import CITIES
from src.extract import fetch_city_data
from src.transform import transform_city_data
from src.load import get_db_connection, upsert_cities, upsert_hourly_data

#make sure we have the log directory already in place
os.makedirs("logs", exist_ok=True)

#send logs to both file (permanent) and vs code terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s -%(name)s - %(levelname)s - %(message)s",
                    handlers=[
                        logging.FileHandler("logs/pipeline.log"),
                        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_pipeline(past_days: int = 30):
    """
    runs the entire etl pipeline for all the cities in the config/cities.py file
    """
    start_time = time.time()
    total_rows = 0
    logger.info(f"===== Starting India Weather & AQI ETL Pipeline (past_days={past_days}) =====")
    
    conn = get_db_connection()
    try:
        #sync dim_city and get {city_name: city_id}
        city_map = upsert_cities(conn, CITIES)
        
        #loop through all cities and run the etl for all of them
        for city in CITIES:
            city_name = city["city_name"]
            try:
                aqi_json, weather_json = fetch_city_data(city, past_days=past_days)
                clean_df = transform_city_data(city_name, aqi_json, weather_json)
                inserted_rows = upsert_hourly_data(conn, city_map[city_name], clean_df)
                total_rows += inserted_rows
            except Exception:
                #log error for the city and continue with next
                logger.exception(f"Pipeline failed for {city_name}. Continuing with next city...")
                conn.rollback()
    finally: 
        conn.close()
        
        
    elapsed = time.time() - start_time
    logger.info(f"===== Pipeline completed in {elapsed} seconds. Total rows upserted = {total_rows} =====")
    
if __name__ == "__main__":
    run_pipeline(past_days=2)
