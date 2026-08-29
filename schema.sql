-- schema.sql : Weather ETL schema (SQLite)
-- Safe to run repeatedly; only creates objects that don't already exist.

-- Untransformed API responses, kept for auditing/replay.
-- One row per (city, run_date): re-running the fetch on the same day
-- overwrites that day's raw response instead of accumulating duplicates.
CREATE TABLE IF NOT EXISTS raw_responses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    city          TEXT NOT NULL,
    run_date      TEXT NOT NULL,      -- date (YYYY-MM-DD) this fetch belongs to
    fetched_at    TEXT NOT NULL,      -- ISO8601 UTC timestamp of the actual HTTP request
    url           TEXT NOT NULL,
    status_code   INTEGER NOT NULL,
    response_json TEXT NOT NULL       -- full, untransformed API response body
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_responses_city_rundate
    ON raw_responses(city, run_date);

-- Transformed hourly forecast data.
-- One row per (city, time): re-fetching updates the temperature/precipitation
-- in place instead of inserting a duplicate row.
CREATE TABLE IF NOT EXISTS weather (
    city                      TEXT NOT NULL,
    time                      TEXT NOT NULL,  -- ISO8601 local time (Asia/Bangkok), hourly
    temperature               REAL NOT NULL,
    precipitation_probability REAL            -- % chance of precipitation, 0-100
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_city_time
    ON weather(city, time);
