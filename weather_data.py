import sqlite3

import pandas as pd
import streamlit as st

DB_PATH = "DB/weather.db"


@st.cache_data(ttl=300)
def load_weather():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT city, time, temperature, precipitation_probability FROM weather ORDER BY city, time",
        conn,
    )
    conn.close()
    df["time"] = pd.to_datetime(df["time"])
    return df
