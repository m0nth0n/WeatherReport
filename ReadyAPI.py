#!/usr/bin/env python3
#Import Library
import json
import logging
import os
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

#Path
DB_PATH = "DB/weather.db"
SCHEMA_PATH = "Schema/schema.sql"
LOG_DIR = "logs"
LOG_PATH = os.path.join(LOG_DIR, "fetch.log")

#Location of City that require
LOCATIONS = {
    "Bangkok":    (13.7563, 100.5018),
    "Chiang Mai": (18.7883, 98.9853),
    "Phuket":     (7.8804, 98.3923),
    "Khon Kaen":  (16.4419, 102.8360),
    "Hat Yai":    (7.0086, 100.4747),
}

FORECAST_DAYS = 7
TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

#Record of Logs
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("weather_etl")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def build_url(lat, lon):
    return (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability"
        f"&forecast_days={FORECAST_DAYS}&timezone=Asia/Bangkok"
    )

#Forecast and Check error
def fetch_forecast(url, city, logger):
    """Fetch a URL with retries on timeout/connection/HTTP errors. Raises on final failure."""
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
                status = resp.getcode()
                body = resp.read().decode("utf-8")
                if status != 200:
                    raise ValueError(f"non-200 status: {status}")
                return status, body
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            last_error = f"connection error: {e.reason}"
        except TimeoutError:
            last_error = "timeout"
        except ValueError as e:
            last_error = str(e)

        if attempt < MAX_ATTEMPTS:
            logger.warning(
                "%s: attempt %d/%d failed (%s), retrying...",
                city, attempt, MAX_ATTEMPTS, last_error,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise RuntimeError(last_error)

#Create tables if needed, migrate in new columns
def apply_schema(conn):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

    #Add precipitation_probability to a weather table created
    cols = [row[1] for row in conn.execute("PRAGMA table_info(weather)").fetchall()]
    if "precipitation_probability" not in cols:
        conn.execute("ALTER TABLE weather ADD COLUMN precipitation_probability REAL")
        conn.commit()

#Setup
def process_city(conn, city, lat, lon, run_date):
    """Fetch, validate, and upsert one city's forecast in a single transaction.
    Raises on any failure; caller is responsible for logging/continuing."""
    url = build_url(lat, lon)
    status, body = fetch_forecast(url, city, logger=logging.getLogger("weather_etl"))

    data = json.loads(body)
    hourly = data.get("hourly")
    required = ("time", "temperature_2m", "precipitation_probability")
    if not hourly or any(field not in hourly for field in required):
        raise ValueError(f"unexpected response shape: missing one of hourly.{required}")

    times = hourly["time"]
    temps = hourly["temperature_2m"]
    precip = hourly["precipitation_probability"]
    if not (len(times) == len(temps) == len(precip)):
        raise ValueError("hourly.time/temperature_2m/precipitation_probability length mismatch")

    rows = [(city, times[i], temps[i], precip[i]) for i in range(len(times))]

    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute(
            """
            INSERT INTO raw_responses (city, run_date, fetched_at, url, status_code, response_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(city, run_date) DO UPDATE SET
                fetched_at=excluded.fetched_at,
                url=excluded.url,
                status_code=excluded.status_code,
                response_json=excluded.response_json
            """,
            (city, run_date, datetime.now(timezone.utc).isoformat(), url, status, body),
        )
        cur.executemany(
            """
            INSERT INTO weather (city, time, temperature, precipitation_probability)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(city, time) DO UPDATE SET
                temperature=excluded.temperature,
                precipitation_probability=excluded.precipitation_probability
            """,
            rows,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return len(rows)

#Run the pipeline for every city and log a summary
def main():
    logger = setup_logging()
    start = time.monotonic()
    run_date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    apply_schema(conn)

    succeeded = []
    failed = []
    total_rows = 0

    for city, (lat, lon) in LOCATIONS.items():
        city_start = time.monotonic()
        try:
            n = process_city(conn, city, lat, lon, run_date)
            total_rows += n
            succeeded.append(city)
            logger.info("%s: OK, %d rows (%.2fs)", city, n, time.monotonic() - city_start)
        except Exception as e:
            failed.append((city, str(e)))
            logger.error("%s: FAILED - %s (%.2fs)", city, e, time.monotonic() - city_start)

    conn.close()

    elapsed = time.monotonic() - start
    logger.info(
        "Run complete: %d/%d cities succeeded, %d rows written, %.2fs elapsed",
        len(succeeded), len(LOCATIONS), total_rows, elapsed,
    )
    if failed:
        for city, err in failed:
            logger.error("  failed: %s (%s)", city, err)

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
