-- VIEW 1 : Daily City Summary

CREATE OR REPLACE VIEW vw_daily_city_aqi AS
SELECT 
	c.city_id,
	c.city_name,
	c.state,
	c.region,
	DATE(f.recorded_at) AS recorded_date,
	ROUND(AVG(f.pm2_5), 2) AS avg_pm2_5,
	ROUND(MAX(f.pm2_5), 2) AS max_pm2_5,
    ROUND(AVG(f.pm10), 2) AS avg_pm10,
    ROUND(AVG(f.temperature_c), 2) AS avg_temp_c,
    ROUND(AVG(f.relative_humidity), 2) AS avg_humidity,
    ROUND(AVG(f.wind_speed_kmh), 2) AS avg_wind_speed_kmh,
	COUNT(*) FILTER (
		WHERE f.aqi_category IN ('Poor', 'Very Poor', 'Severe')
	) AS unhealthy_hours,
	COUNT(*) AS total_hours_recorded
	
FROM fct_hourly_environment f JOIN dim_city c 
ON c.city_id = f.city_id
GROUP BY c.city_id, c.city_name, c.state, c.region, DATE(f.recorded_at);




-- VIEW 2 : Rolling 7 day Pollution Trends

CREATE OR REPLACE VIEW vw_city_pollution_trends AS
WITH daily_metrics AS (
	SELECT 
		city_id,
		city_name,
		region,
		recorded_date,
		avg_pm2_5,
		LAG(avg_pm2_5) OVER (
				PARTITION BY city_name ORDER BY recorded_date
		) AS prev_day_pm2_5,
		ROUND(
			AVG(avg_pm2_5) OVER (
				PARTITION BY city_name ORDER BY recorded_date
				ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
			), 2
		) AS rolling_7d_pm2_5
	FROM vw_daily_city_aqi
)

SELECT
    city_id,
    city_name,
    region,
    recorded_date,
    avg_pm2_5,
    rolling_7d_pm2_5,
    prev_day_pm2_5,
	ROUND(
		((avg_pm2_5)-(prev_day_pm2_5)) * 100.0 / NULLIF (prev_day_pm2_5, 0), 2
	) AS change_pct
FROM daily_metrics;

-- VIEW 3 : Hourly Pollution Profile & City Rankings
CREATE OR REPLACE VIEW vw_city_hourly_profile AS
WITH hourly_avg AS (
	SELECT
		c.city_id,
	    c.city_name,
	    c.region,
		EXTRACT(HOUR FROM f.recorded_at)::INT as hour_of_day,
		ROUND(AVG(f.pm2_5), 2) AS avg_pm2_5,
	    ROUND(AVG(f.temperature_c), 2) AS avg_temp_c,
	    ROUND(AVG(f.wind_speed_kmh), 2) AS avg_wind_speed_kmh
	FROM fct_hourly_environment f JOIN dim_city c
	ON f.city_id = c.city_id
	GROUP BY c.city_id, c.city_name, c.region, EXTRACT(HOUR FROM f.recorded_at)
)

SELECT 
	city_id,
    city_name,
    region,
    hour_of_day,
    avg_pm2_5,
    avg_temp_c,
    avg_wind_speed_kmh,
	DENSE_RANK() OVER (
		PARTITION BY city_name ORDER BY avg_pm2_5 DESC
	) AS peak_hour_rank,
	DENSE_RANK() OVER (
		PARTITION BY hour_of_day ORDER BY avg_pm2_5 DESC
	) AS city_rank_at_hour
FROM hourly_avg;

-- SELECT * FROM fct_hourly_environment
-- ORDER BY recorded_at DESC;