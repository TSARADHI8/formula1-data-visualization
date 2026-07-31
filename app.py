"""
Formula 1 Data Visualization — Interactive Streamlit Dashboard
==============================================================

Every dataframe, merge, rename, aggregation, filter and figure in this app is a
direct reproduction of `formula1_analysis.ipynb` (the single source of truth).

Following the project brief, the dashboard presents a *curated subset* of the
notebook's ten analytical figures — the seven that carry the story — rather than
all of them, arranged over four themed tabs.

Curated figures
---------------
Q1  Race calendar growth ................ Overview      (line)
Q5  Countries producing race winners .... Overview      (choropleth)
Q3  Most race wins by driver ............ Drivers       (horizontal bar)
Q10 Points-per-race distribution ........ Drivers       (box)
Q2  Constructor dominance by season ..... Constructors  (area)
Q8  Pole-to-win conversion efficiency ... Constructors  (bubble scatter)
Q6  Circuits hosting the most races ..... Circuits      (lollipop)

Left in the notebook only: Q4 (grid vs finishing position — exploratory in form),
Q7 (average positions gained — a second driver bar chart) and Q9 (constructor
wins by decade — the same story the Q2 area chart already tells).
"""

import inspect
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================
# PAGE CONFIG
# ==============================================================

st.set_page_config(
    page_title="Formula 1 Analytics Dashboard",
    page_icon="🏎️",
    layout="wide",
)

DATA_DIR = Path(__file__).resolve().parent / "data"

F1_RED = "#E10600"
TEMPLATE = "plotly_white"


# --------------------------------------------------------------
# Plotly / Streamlit compatibility
# --------------------------------------------------------------
# Plotly >= 6 serialises numeric arrays as base64 ("bdata"/"dtype") payloads.
# The plotly.js bundled with older Streamlit releases cannot decode them, so the
# traces arrive empty and every figure renders as a blank frame. Emitting plain
# JSON arrays instead is understood by every plotly.js version.
def _disable_plotly_base64_arrays():
    try:
        import plotly.basedatatypes as _basedatatypes

        if hasattr(_basedatatypes, "convert_to_base64"):
            _basedatatypes.convert_to_base64 = lambda obj: obj
    except Exception:  # pragma: no cover - defensive only
        pass


_disable_plotly_base64_arrays()


# ==============================================================
# CHART RENDERING HELPER
# ==============================================================
# Streamlit's plotly_chart signature changed across versions (use_container_width
# -> width, key / theme availability). The helper introspects the installed
# signature so the app runs unmodified on old and new Streamlit releases.
# theme=None keeps Plotly's own template, which is what the notebook figures are
# styled with and avoids Streamlit's theme-injection step.

_PLOTLY_CHART_PARAMS = set(inspect.signature(st.plotly_chart).parameters)


def render_chart(fig, key):
    """Render a Plotly figure full-width, using the figure's own Plotly theme."""
    kwargs = {}

    if "use_container_width" in _PLOTLY_CHART_PARAMS:
        kwargs["use_container_width"] = True
    elif "width" in _PLOTLY_CHART_PARAMS:
        kwargs["width"] = "stretch"

    if "theme" in _PLOTLY_CHART_PARAMS:
        kwargs["theme"] = None

    if "key" in _PLOTLY_CHART_PARAMS:
        kwargs["key"] = key

    st.plotly_chart(fig, **kwargs)


# ==============================================================
# STEP 2 / 5 / 6 / 7 : LOAD, PREPARE, MERGE, RENAME
# ==============================================================


@st.cache_data(show_spinner="Loading Formula 1 data…")
def load_data():
    """Reproduce the notebook's loading, preparation, merge and rename steps."""

    # ---- Step 2: Load the datasets -------------------------------------
    circuits = pd.read_csv(DATA_DIR / "circuits.csv")
    constructor_results = pd.read_csv(DATA_DIR / "constructor_results.csv")
    constructor_standings = pd.read_csv(DATA_DIR / "constructor_standings.csv")
    constructors = pd.read_csv(DATA_DIR / "constructors.csv")
    driver_standings = pd.read_csv(DATA_DIR / "driver_standings.csv")
    drivers = pd.read_csv(DATA_DIR / "drivers.csv")
    lap_times = pd.read_csv(DATA_DIR / "lap_times.csv")
    pit_stops = pd.read_csv(DATA_DIR / "pit_stops.csv")
    qualifying = pd.read_csv(DATA_DIR / "qualifying.csv")
    races = pd.read_csv(DATA_DIR / "races.csv")
    results = pd.read_csv(DATA_DIR / "results.csv")
    seasons = pd.read_csv(DATA_DIR / "seasons.csv")
    sprint_results = pd.read_csv(DATA_DIR / "sprint_results.csv")
    status = pd.read_csv(DATA_DIR / "status.csv")

    # ---- Step 5: Data preparation — readable driver name ----------------
    drivers["driver_name"] = drivers["forename"] + " " + drivers["surname"]

    # ---- Step 6: Build the master dataset -------------------------------
    f1 = (
        results
        .merge(
            drivers[["driverId", "driver_name", "nationality"]],
            on="driverId",
            how="left",
        )
        .merge(
            constructors[["constructorId", "name", "nationality"]],
            on="constructorId",
            how="left",
            suffixes=("", "_constructor"),
        )
        .merge(
            races[["raceId", "year", "round", "name", "date", "circuitId"]],
            on="raceId",
            how="left",
            suffixes=("", "_race"),
        )
        .merge(
            circuits[["circuitId", "name", "location", "country"]],
            on="circuitId",
            how="left",
            suffixes=("", "_circuit"),
        )
        .merge(
            status,
            on="statusId",
            how="left",
        )
    )

    # ---- Step 7: Rename columns for readability -------------------------
    f1.rename(
        columns={
            "name": "constructor_name",
            "name_race": "race_name",
            "name_circuit": "circuit_name",
            "country": "circuit_country",
            "nationality": "driver_nationality",
            "nationality_constructor": "constructor_nationality",
        },
        inplace=True,
    )

    datasets = {
        "circuits": circuits,
        "constructor_results": constructor_results,
        "constructor_standings": constructor_standings,
        "constructors": constructors,
        "driver_standings": driver_standings,
        "drivers": drivers,
        "lap_times": lap_times,
        "pit_stops": pit_stops,
        "qualifying": qualifying,
        "races": races,
        "results": results,
        "seasons": seasons,
        "sprint_results": sprint_results,
        "status": status,
        "f1": f1,
    }

    return datasets


DATA = load_data()

f1 = DATA["f1"]
races = DATA["races"]
circuits = DATA["circuits"]
constructors = DATA["constructors"]
drivers = DATA["drivers"]
results = DATA["results"]
status = DATA["status"]

# Nationality -> country mapping used by Analytical Question 5 (notebook verbatim)
NATIONALITY_MAP = {
    "British": "United Kingdom",
    "German": "Germany",
    "Brazilian": "Brazil",
    "French": "France",
    "Italian": "Italy",
    "Spanish": "Spain",
    "Dutch": "Netherlands",
    "Australian": "Australia",
    "Finnish": "Finland",
    "Austrian": "Austria",
    "Canadian": "Canada",
    "Mexican": "Mexico",
    "Argentine": "Argentina",
    "Belgian": "Belgium",
    "Swiss": "Switzerland",
    "Swedish": "Sweden",
    "New Zealander": "New Zealand",
    "Japanese": "Japan",
    "South African": "South Africa",
    "American": "United States",
    "Colombian": "Colombia",
    "Polish": "Poland",
    "Monégasque": "Monaco",
    "Monegasque": "Monaco",
    "Irish": "Ireland",
    "Danish": "Denmark",
    "Portuguese": "Portugal",
    "Russian": "Russia",
    "Thai": "Thailand",
    "Indian": "India",
    "Venezuelan": "Venezuela",
}


# ==============================================================
# SIDEBAR — FILTERS
# ==============================================================

st.sidebar.title("🏁 Filters")

YEAR_MIN = int(f1["year"].min())
YEAR_MAX = int(f1["year"].max())

year_range = st.sidebar.slider(
    "Season range",
    min_value=YEAR_MIN,
    max_value=YEAR_MAX,
    value=(YEAR_MIN, YEAR_MAX),
    step=1,
    help="Restricts every chart to the selected seasons.",
)

driver_options = sorted(f1["driver_name"].dropna().unique().tolist())
constructor_options = sorted(f1["constructor_name"].dropna().unique().tolist())
circuit_options = sorted(f1["circuit_name"].dropna().unique().tolist())

selected_drivers = st.sidebar.multiselect(
    "Driver",
    options=driver_options,
    default=[],
    help="Leave empty to include every driver.",
)

selected_constructors = st.sidebar.multiselect(
    "Constructor",
    options=constructor_options,
    default=[],
    help="Leave empty to include every constructor.",
)

selected_circuits = st.sidebar.multiselect(
    "Circuit",
    options=circuit_options,
    default=[],
    help="Leave empty to include every circuit.",
)

with st.sidebar.expander("Thresholds & chart depth", expanded=False):
    min_races = st.slider(
        "Minimum races per driver",
        min_value=1,
        max_value=200,
        value=50,
        step=1,
        help="Used by the points-per-race analysis (notebook default: 50).",
    )

    min_poles = st.slider(
        "Minimum pole positions per constructor",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
        help="Used by the pole-to-win conversion analysis (notebook default: 10).",
    )

    top_driver_wins_n = st.slider("Top N — driver wins", 5, 30, 10, 1)
    top_driver_points_n = st.slider("Top N — points per race", 5, 30, 15, 1)
    top_constructors_area_n = st.slider("Top N — constructors (era chart)", 3, 20, 8, 1)
    top_circuits_n = st.slider("Top N — circuits", 5, 30, 15, 1)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: Ergast Formula 1 dataset (1950–2024). Every figure reproduces the "
    "analysis notebook exactly; the filters above are applied before each "
    "aggregation."
)


# ---- Apply the filters -------------------------------------------------

df = f1[(f1["year"] >= year_range[0]) & (f1["year"] <= year_range[1])].copy()

if selected_drivers:
    df = df[df["driver_name"].isin(selected_drivers)]

if selected_constructors:
    df = df[df["constructor_name"].isin(selected_constructors)]

if selected_circuits:
    df = df[df["circuit_name"].isin(selected_circuits)]

# `races` is used directly by Q1 and Q6 in the notebook, so it is filtered with
# the same criteria: season range always, plus the race set that survives the
# driver / constructor / circuit selection.
races_df = races[
    (races["year"] >= year_range[0]) & (races["year"] <= year_range[1])
].copy()

if selected_drivers or selected_constructors or selected_circuits:
    races_df = races_df[races_df["raceId"].isin(df["raceId"].unique())]

FILTERS_ACTIVE = bool(selected_drivers or selected_constructors or selected_circuits)


# ==============================================================
# HEADER + KEY METRICS
# ==============================================================

st.title("🏎️ Formula 1 Analytics Dashboard")
st.markdown(
    "An interactive tour through 75 seasons of Formula 1 — calendar growth, "
    "driver excellence, constructor eras and the circuits that shaped the sport. "
    "The tabs below present a curated selection of the analysis; the full set of "
    "ten analytical questions lives in the accompanying notebook."
)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Seasons", int(df["year"].nunique()))
kpi2.metric("Grands Prix", int(df["raceId"].nunique()))
kpi3.metric("Drivers", int(df["driver_name"].nunique()))
kpi4.metric("Constructors", int(df["constructor_name"].nunique()))
kpi5.metric("Circuits", int(df["circuit_name"].nunique()))

if df.empty:
    st.error(
        "No race results match the current filter combination. "
        "Widen the season range or clear a selection in the sidebar."
    )
    st.stop()

st.markdown("---")

tab_overview, tab_drivers, tab_constructors, tab_circuits = st.tabs(
    ["🏁 Overview", "🏎️ Drivers", "🔧 Constructors", "📍 Circuits"]
)


# ==============================================================
# TAB 1 — OVERVIEW
# ==============================================================

with tab_overview:

    # ---------- Analytical Question 1 : calendar growth ----------
    st.subheader("How has the Formula 1 calendar evolved over time?")

    races_per_year = (
        races_df.groupby("year")
        .size()
        .reset_index(name="Number of Races")
    )

    if races_per_year.empty:
        st.info("No races match the current filters.")
    else:
        fig_calendar = px.line(
            races_per_year,
            x="year",
            y="Number of Races",
            markers=True,
        )

        fig_calendar.update_traces(
            line=dict(color=F1_RED, width=4),
            marker=dict(size=7),
            hovertemplate="<b>Season:</b> %{x}<br><b>Races:</b> %{y}<extra></extra>",
        )

        # Highlight the latest season
        latest = races_per_year.iloc[-1]

        fig_calendar.add_annotation(
            x=latest["year"],
            y=latest["Number of Races"],
            text="Largest calendar",
            showarrow=True,
            arrowhead=2,
            ax=-60,
            ay=-40,
            font=dict(size=12),
        )

        fig_calendar.update_layout(
            title={
                "text": f"Formula 1 Race Calendar Growth "
                        f"({int(races_per_year['year'].min())}–"
                        f"{int(races_per_year['year'].max())})",
                "x": 0.5,
            },
            template=TEMPLATE,
            height=560,
            font=dict(size=14),
            xaxis=dict(title="Season", showgrid=False, zeroline=False),
            yaxis=dict(
                title="Number of Grand Prix",
                showgrid=True,
                gridcolor="#ECECEC",
                zeroline=False,
            ),
            hovermode="x unified",
        )

        render_chart(fig_calendar, "q1_calendar_growth")

        st.markdown(
            "**Insight —** The number of races per season has increased steadily. "
            "Fewer than ten Grands Prix were held in the early championship years, "
            "and the calendar expanded as Formula 1 entered new international "
            "markets. Recent seasons contain the largest calendars in the history "
            "of the sport."
        )

    st.markdown("---")

    # ---------- Analytical Question 5 : countries producing race winners ----------
    st.subheader("Which countries have produced the greatest number of race winners?")

    race_winners = df[df["positionOrder"] == 1]

    country_wins = (
        race_winners
        .groupby("driver_nationality")
        .size()
        .reset_index(name="Race Wins")
    )

    country_wins["Country"] = country_wins["driver_nationality"].map(NATIONALITY_MAP)
    country_wins = country_wins.dropna()

    if country_wins.empty:
        st.info("No race wins available for the current filters.")
    else:
        fig_map = px.choropleth(
            country_wins,
            locations="Country",
            locationmode="country names",
            color="Race Wins",
            hover_name="Country",
            color_continuous_scale="Reds",
        )

        fig_map.update_layout(
            title={
                "text": "<b>Countries Producing the Greatest Number of "
                        "Formula 1 Race Winners</b>",
                "x": 0.5,
            },
            template=TEMPLATE,
            height=640,
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type="natural earth",
            ),
        )

        render_chart(fig_map, "q5_country_wins_map")

        with st.expander("View race wins by nationality"):
            st.dataframe(
                country_wins.sort_values("Race Wins", ascending=False)
                .rename(columns={"driver_nationality": "Nationality"})
                [["Nationality", "Country", "Race Wins"]]
                .reset_index(drop=True),
                use_container_width=True,
            )

        st.markdown(
            "**Insight —** Race winners are concentrated in a small number of "
            "countries. The United Kingdom has produced the largest number of "
            "winning drivers, followed by Germany, Brazil and Finland — a "
            "distribution that reflects the historical weight of European "
            "motorsport culture."
        )


# ==============================================================
# TAB 2 — DRIVERS
# ==============================================================

with tab_drivers:

    # ---------- Analytical Question 3 : most race wins ----------
    st.subheader("Which drivers have won the most Formula 1 races?")

    driver_wins = (
        df[df["positionOrder"] == 1]
        .groupby("driver_name")
        .size()
        .reset_index(name="Wins")
        .sort_values("Wins", ascending=False)
        .head(top_driver_wins_n)
    )

    if driver_wins.empty:
        st.info("No race wins available for the current filters.")
    else:
        fig_wins = px.bar(
            driver_wins.sort_values("Wins"),
            x="Wins",
            y="driver_name",
            orientation="h",
            text="Wins",
            color="Wins",
            color_continuous_scale="Reds",
        )

        fig_wins.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Wins: %{x}<extra></extra>",
        )

        fig_wins.update_layout(
            title={
                "text": "<b>Lewis Hamilton and Michael Schumacher Lead "
                        "Formula 1 Race Victories</b>",
                "x": 0.5,
            },
            template=TEMPLATE,
            height=600,
            xaxis_title="Number of Race Wins",
            yaxis_title="Driver",
            coloraxis_showscale=False,
        )

        render_chart(fig_wins, "q3_driver_wins")

        st.markdown(
            "**Insight —** Lewis Hamilton and Michael Schumacher lead the list "
            "with exceptional numbers of Grand Prix victories, while Max "
            "Verstappen, Sebastian Vettel, Alain Prost and Ayrton Senna also stand "
            "out. Only a small group of elite drivers has accumulated a large "
            "share of all race wins."
        )

    st.markdown("---")

    # ---------- Analytical Question 10 : points per race ----------
    st.subheader("Which drivers consistently score the most points per race?")

    driver_points = (
        df.groupby("driver_name")
        .agg(
            Total_Points=("points", "sum"),
            Races=("raceId", "count"),
        )
        .reset_index()
    )

    driver_points = driver_points[driver_points["Races"] >= min_races]

    if driver_points.empty:
        st.info(
            f"No driver reaches the minimum of {min_races} races under the current "
            "filters. Lower the threshold in the sidebar or widen the selection."
        )
    else:
        driver_points["Average Points"] = (
            driver_points["Total_Points"] / driver_points["Races"]
        ).round(2)

        driver_points = driver_points.sort_values(
            "Average Points", ascending=False
        ).head(top_driver_points_n)

        fig_points = px.box(
            df[df["driver_name"].isin(driver_points["driver_name"])],
            x="driver_name",
            y="points",
            color="driver_name",
            points="outliers",
        )

        fig_points.update_layout(
            title={
                "text": "<b>Distribution of Championship Points Scored Per Race</b>",
                "x": 0.5,
            },
            template=TEMPLATE,
            height=650,
            xaxis_title="Driver",
            yaxis_title="Points per Race",
            showlegend=False,
        )

        fig_points.update_xaxes(tickangle=-45)

        render_chart(fig_points, "q10_points_distribution")

        with st.expander("View average points per race"):
            st.dataframe(
                driver_points.rename(
                    columns={
                        "driver_name": "Driver",
                        "Total_Points": "Total Points",
                    }
                )[["Driver", "Total Points", "Races", "Average Points"]]
                .reset_index(drop=True),
                use_container_width=True,
            )

        st.markdown(
            "**Insight —** Drivers with higher medians and narrower spreads score "
            "points consistently, while wider distributions reveal variability "
            "caused by retirements, changing team competitiveness or inconsistent "
            "results."
        )


# ==============================================================
# TAB 3 — CONSTRUCTORS
# ==============================================================

with tab_constructors:

    # ---------- Analytical Question 2 : dominance across eras ----------
    st.subheader("Which constructors have dominated Formula 1 across different eras?")

    race_winners_c = df[df["positionOrder"] == 1]

    constructor_yearly = (
        race_winners_c
        .groupby(["year", "constructor_name"])
        .size()
        .reset_index(name="Wins")
    )

    top_constructors = (
        race_winners_c["constructor_name"]
        .value_counts()
        .head(top_constructors_area_n)
        .index
    )

    constructor_yearly = constructor_yearly[
        constructor_yearly["constructor_name"].isin(top_constructors)
    ]

    if constructor_yearly.empty:
        st.info("No constructor wins available for the current filters.")
    else:
        fig_era = px.area(
            constructor_yearly,
            x="year",
            y="Wins",
            color="constructor_name",
            title="<b>Constructor dominance has shifted across different "
                  "Formula 1 eras</b>",
        )

        fig_era.update_layout(
            template=TEMPLATE,
            height=650,
            title_x=0.5,
            xaxis_title="Season",
            yaxis_title="Race Wins",
            legend_title="Constructor",
            hovermode="x unified",
        )

        render_chart(fig_era, "q2_constructor_eras")

        st.markdown(
            "**Insight —** Ferrari sustained success over several decades, while "
            "McLaren and Williams were highly competitive in the late twentieth "
            "century. More recently Red Bull Racing and Mercedes established long "
            "periods of dominance, showing how regulations, technology and team "
            "performance reshape competitive leadership."
        )

    st.markdown("---")

    # ---------- Analytical Question 8 : pole-to-win conversion ----------
    st.subheader("Which constructors convert pole positions into wins most efficiently?")

    pole_positions = (
        df[df["grid"] == 1]
        .groupby("constructor_name")
        .size()
        .reset_index(name="Pole Positions")
    )

    race_wins_c = (
        df[df["positionOrder"] == 1]
        .groupby("constructor_name")
        .size()
        .reset_index(name="Race Wins")
    )

    if pole_positions.empty or race_wins_c.empty:
        constructor_efficiency = pd.DataFrame(
            columns=["constructor_name", "Pole Positions", "Race Wins"]
        )
    else:
        constructor_efficiency = pole_positions.merge(
            race_wins_c,
            on="constructor_name",
            how="inner",
        )

    constructor_efficiency = constructor_efficiency[
        constructor_efficiency["Pole Positions"] >= min_poles
    ]

    if constructor_efficiency.empty:
        st.info(
            f"No constructor reaches the minimum of {min_poles} pole positions "
            "under the current filters. Lower the threshold in the sidebar or "
            "widen the selection."
        )
    else:
        constructor_efficiency["Conversion Rate (%)"] = (
            constructor_efficiency["Race Wins"]
            / constructor_efficiency["Pole Positions"]
            * 100
        ).round(1)

        constructor_efficiency = constructor_efficiency.sort_values(
            "Conversion Rate (%)",
            ascending=False,
        )

        fig_eff = px.scatter(
            constructor_efficiency,
            x="Pole Positions",
            y="Race Wins",
            size="Conversion Rate (%)",
            color="Conversion Rate (%)",
            hover_name="constructor_name",
            text="constructor_name",
            color_continuous_scale="Turbo",
        )

        fig_eff.update_traces(
            textposition="top center",
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Pole Positions: %{x}<br>"
                "Race Wins: %{y}<br>"
                "Conversion Rate: %{marker.size:.1f}%<extra></extra>"
            ),
        )

        fig_eff.update_layout(
            title={
                "text": "<b>Constructor Efficiency in Converting Pole Positions "
                        "into Race Wins</b>",
                "x": 0.5,
            },
            template=TEMPLATE,
            height=700,
            xaxis_title="Pole Positions",
            yaxis_title="Race Wins",
        )

        render_chart(fig_eff, "q8_pole_conversion")

        with st.expander("View conversion table"):
            st.dataframe(
                constructor_efficiency.rename(
                    columns={"constructor_name": "Constructor"}
                ).reset_index(drop=True),
                use_container_width=True,
            )

        st.markdown(
            "**Insight —** Constructors in the upper right combine frequent poles "
            "with many victories, indicating sustained competitiveness. Larger "
            "bubbles mark higher conversion rates — teams that turn qualifying "
            "pace into results through strategy, reliability and execution. Rates "
            "above 100% mean a team won more races than it started from pole."
        )


# ==============================================================
# TAB 4 — CIRCUITS
# ==============================================================

with tab_circuits:

    # ---------- Analytical Question 6 : circuits hosting the most races ----------
    st.subheader("Which circuits have hosted the most Formula 1 races?")

    circuit_counts = (
        races_df.groupby("circuitId")
        .size()
        .reset_index(name="Race Count")
        .merge(
            circuits[["circuitId", "name", "country"]],
            on="circuitId",
        )
        .sort_values("Race Count", ascending=False)
        .head(top_circuits_n)
    )

    if circuit_counts.empty:
        st.info("No races match the current filters.")
    else:
        circuit_table = circuit_counts.copy()

        # Reverse order so the largest value appears at the top
        circuit_counts = circuit_counts.sort_values("Race Count")

        fig_circuits = go.Figure()

        # Lollipop stems
        fig_circuits.add_trace(
            go.Scatter(
                x=circuit_counts["Race Count"],
                y=circuit_counts["name"],
                mode="lines",
                line=dict(color="lightgray", width=2),
                showlegend=False,
            )
        )

        # Lollipop dots
        fig_circuits.add_trace(
            go.Scatter(
                x=circuit_counts["Race Count"],
                y=circuit_counts["name"],
                mode="markers+text",
                marker=dict(size=12, color=F1_RED),
                text=circuit_counts["Race Count"],
                textposition="middle right",
                hovertemplate="<b>%{y}</b><br>Races Hosted: %{x}<extra></extra>",
                showlegend=False,
            )
        )

        fig_circuits.update_layout(
            title={
                "text": "<b>Historic Circuits Continue to Dominate the "
                        "Formula 1 Calendar</b>",
                "x": 0.5,
            },
            template=TEMPLATE,
            height=700,
            xaxis_title="Number of Formula 1 Races",
            yaxis_title="Circuit",
            xaxis=dict(showgrid=True, gridcolor="#ECECEC"),
            yaxis=dict(showgrid=False),
        )

        render_chart(fig_circuits, "q6_circuit_counts")

        with st.expander("View circuit table"):
            st.dataframe(
                circuit_table.rename(
                    columns={"name": "Circuit", "country": "Country"}
                )[["Circuit", "Country", "Race Count"]].reset_index(drop=True),
                use_container_width=True,
            )

        st.markdown(
            "**Insight —** A small group of iconic circuits has hosted a "
            "substantial share of all Formula 1 races. Monza, Monaco, Silverstone "
            "and Spa-Francorchamps have remained central to the championship for "
            "decades, reflecting their historical importance and enduring place on "
            "the calendar."
        )

st.markdown("---")
st.caption(
    "Formula 1 Data Visualization project · a curated selection of the ten "
    "analytical figures in `formula1_analysis.ipynb`, reproduced exactly · "
    "built with Streamlit, Plotly and pandas."
)
