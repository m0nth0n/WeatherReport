import pandas as pd
import streamlit as st

from weather_data import load_weather

st.set_page_config(page_title="Summary Analytics", layout="wide")

df = load_weather()

st.title("Summary Analytics")
st.caption("Aggregated stats across all 5 cities")

# `weather` can hold more than 7 days of history (each day's run adds a new
# day without deleting the last one that fell out of the window) - restrict
# to the current 7-day forecast window so these numbers match SQL/results.md.
today = pd.Timestamp.now().normalize()
df = df[(df["time"] >= today) & (df["time"] < today + pd.Timedelta(days=7))]

daily = (
    df.assign(day=df["time"].dt.date)
    .groupby(["city", "day"])["temperature"]
    .agg(avg_temp="mean", max_temp="max", min_temp="min")
    .round(2)
    .reset_index()
)

st.subheader("Average / Max / Min temperature per city per day")
st.dataframe(daily, width="stretch")

st.subheader("Widest Temperature Range Per City (7-Day Window)")
range_df = (
    df.groupby("city")["temperature"]
    .agg(lambda s: s.max() - s.min())
    .rename("temp_range")
    .reset_index()
    .sort_values("temp_range", ascending=False)
)
widest = range_df.iloc[0]
st.metric(f"Widest Range: {widest['city']}", f"{widest['temp_range']:.1f} °C")
st.bar_chart(range_df.set_index("city")["temp_range"])

st.subheader("Hour With Highest Rain Chance Per City Per Day")
by_day = df.assign(day=df["time"].dt.date)
peak_idx = by_day.groupby(["city", "day"])["precipitation_probability"].idxmax()
rainiest = by_day.loc[peak_idx, ["city", "day", "time", "precipitation_probability"]].sort_values(
    ["city", "day"]
)
st.dataframe(rainiest, width="stretch")

st.subheader("Day-Over-Day Change in Average Temperature")
daily_sorted = daily.sort_values(["city", "day"])
daily_sorted["diff_from_prev_day"] = daily_sorted.groupby("city")["avg_temp"].diff().round(2)
st.dataframe(daily_sorted, width="stretch")
