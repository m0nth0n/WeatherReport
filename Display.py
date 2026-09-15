dmport pandas as pd
import streamlit as st

from weather_data import load_weather

st.set_page_config(page_title="Thailand Weather Dashboard", layout="wide")

df = load_weather()

st.title("Thailand Weather Dashboard")
st.caption("7-day hourly forecast for 5 cities, from DB/weather.db")

# --- Current conditions ---
st.subheader("Current Conditions")
now = pd.Timestamp.now()
current = (
    df.assign(time_diff=(df["time"] - now).abs())
    .sort_values("time_diff")
    .groupby("city")
    .first()
    .reset_index()
    .sort_values("city")
)
with st.container(border=True):
    cols = st.columns(len(current))
    for col, (_, row) in zip(cols, current.iterrows()):
        with col:
            st.caption(row["city"])
            st.metric("🌡️ Temp", f"{row['temperature']:.1f} °C")
            st.metric("☔ Rain", f"{row['precipitation_probability']:.0f}%")

# --- City explorer ---
cities = sorted(df["city"].unique())
selected_city = st.selectbox("Choose a City", cities)
city_df = df[df["city"] == selected_city].set_index("time")

st.subheader(f"{selected_city}: Hourly Forecast")
col1, col2 = st.columns(2)
with col1:
    st.caption("Temperature (°C)")
    st.line_chart(city_df["temperature"])
with col2:
    st.caption("Rain chance (%)")
    st.line_chart(city_df["precipitation_probability"])

st.subheader("Raw Hourly Data")
