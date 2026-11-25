
CREATE TABLE IF NOT EXISTS dim_city (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(50) UNIQUE NOT NULL,
    state VARCHAR(50) NOT NULL,
    latitude DECIMAL(8, 5) NOT NULL,
    longitude DECIMAL(8, 5) NOT NULL,
    region VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fct_hourly_environment (
    city_id INT REFERENCES dim_city(city_id),
    recorded_at TIMESTAMP NOT NULL,
    pm2_5 DECIMAL(6, 2),
    pm10 DECIMAL(6, 2),
    nitrogen_dioxide DECIMAL(6, 2),
    european_aqi INT,
    temperature_c DECIMAL(5, 2),
    relative_humidity DECIMAL(5, 2),
    wind_speed_kmh DECIMAL(5, 2),
    aqi_category VARCHAR(25),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (city_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_fct_recorded_at ON fct_hourly_environment(recorded_at);