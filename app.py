from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from disaster_app.data_loader import DISASTER_TYPE_CONFIG, LOOKBACK_DAYS, load_events_dataframe

HEATMAP_COLOR_RANGE = [
    [255, 255, 204],
    [255, 237, 160],
    [254, 217, 118],
    [254, 178, 76],
    [253, 141, 60],
    [240, 59, 32],
    [189, 0, 38],
]


def build_map(filtered_data: pd.DataFrame, radius_km: int, extruded: bool) -> pdk.Deck:
    view_state = pdk.ViewState(
        latitude=float(filtered_data["lat"].mean()),
        longitude=float(filtered_data["lon"].mean()),
        zoom=1.2,
        pitch=38 if extruded else 0,
        bearing=0,
    )

    layer = pdk.Layer(
        "HexagonLayer",
        data=filtered_data,
        get_position="[lon, lat]",
        radius=radius_km * 1000,
        coverage=0.95,
        extruded=extruded,
        elevation_scale=90,
        elevation_range=[0, 3000],
        pickable=True,
        auto_highlight=True,
        color_range=HEATMAP_COLOR_RANGE,
    )

    return pdk.Deck(
        map_style="light",
        initial_view_state=view_state,
        layers=[layer],
        tooltip={
            "html": "<b>Hexa előfordulás:</b> {elevationValue}",
            "style": {"color": "white", "backgroundColor": "#111827"},
        },
    )


st.set_page_config(page_title="Globális katasztrófa-gyakoriság térkép", layout="wide")
st.title("Globális természeti katasztrófa-gyakoriság")
st.caption(
    "Adatforrás: NASA EONET historikus események. A lavina kategória EONET oldalon földcsuszamlás/lavina jellegű eseményekkel van közelítve."
)

st.sidebar.header("Adatok")
force_refresh = st.sidebar.button("Adatok frissítése forrásból")

with st.spinner("Katasztrófaadatok betöltése..."):
    data = load_events_dataframe(force_refresh=force_refresh, days=LOOKBACK_DAYS)

if data.empty:
    st.error("Nem sikerült eseményadatokat lekérni.")
    st.stop()

available_labels = list(DISASTER_TYPE_CONFIG.values())
selected_labels = st.sidebar.multiselect(
    "Katasztrófatípusok",
    options=available_labels,
    default=available_labels,
)

year_min = int(data["date"].dt.year.min())
year_max = int(data["date"].dt.year.max())
default_start_year = max(year_min, year_max - 10)
selected_years = st.sidebar.slider(
    "Időintervallum (év)",
    min_value=year_min,
    max_value=year_max,
    value=(default_start_year, year_max),
)

radius_km = st.sidebar.slider("Hexagon sugár (km)", min_value=30, max_value=400, value=140, step=10)
extruded = st.sidebar.toggle("3D megjelenítés", value=True)

filtered = data[data["disaster_label"].isin(selected_labels)].copy()
filtered = filtered[
    (filtered["date"].dt.year >= selected_years[0]) & (filtered["date"].dt.year <= selected_years[1])
].reset_index(drop=True)

if filtered.empty:
    st.warning("A kiválasztott szűrőkkel nincs megjeleníthető esemény.")
    st.stop()

metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Eseménypontok száma", f"{len(filtered):,}".replace(",", " "))
metric_col2.metric("Katasztrófatípusok", f"{filtered['disaster_label'].nunique()}")
metric_col3.metric("Vizsgált időszak", f"{selected_years[0]}–{selected_years[1]}")

st.pydeck_chart(build_map(filtered, radius_km=radius_km, extruded=extruded), use_container_width=True)

summary_col, trend_col = st.columns([1, 2])
with summary_col:
    st.subheader("Előfordulások típusonként")
    type_summary = (
        filtered.groupby("disaster_label", as_index=False)
        .size()
        .rename(columns={"size": "előfordulások"})
        .sort_values("előfordulások", ascending=False)
    )
    st.dataframe(type_summary, hide_index=True, use_container_width=True)

with trend_col:
    st.subheader("Éves trend")
    yearly = (
        filtered.assign(year=filtered["date"].dt.year)
        .groupby(["year", "disaster_label"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    yearly_pivot = yearly.pivot(index="year", columns="disaster_label", values="count").fillna(0)
    st.line_chart(yearly_pivot)

