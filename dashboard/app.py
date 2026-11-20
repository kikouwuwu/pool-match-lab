"""Dashboard de partidas: cómo juegas por sesión y cómo evolucionas.

Lee los modelos de dbt en DuckDB. Se abre con `make dashboard`.
"""

import os

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pool_match_lab.vision import BALL_RADIUS, POCKETS_M, TABLE_LENGTH, TABLE_WIDTH

WAREHOUSE = os.environ.get("POOL_WAREHOUSE", "data/warehouse.duckdb")

# Paleta categórica validada, en orden fijo. Las faltas no van en el mapa: la blanca no queda en la mesa
OUTCOME_COLORS = {"emboca": "#2a78d6", "falla": "#eb6834"}
SERIES = "#2a78d6"  # una sola serie: no necesita leyenda
CLOTH, RAIL = "#e7efe6", "#8a8578"
STRENGTH_ORDER = ["suave", "media", "fuerte"]
TABLE_PAD = 0.14  # metros alrededor del paño: las troneras laterales sobresalen ~13 cm

st.set_page_config(page_title="Pool Match Lab", page_icon="🎱", layout="wide")


@st.cache_data(ttl=60)
def query(sql: str, params: list | None = None):
    with duckdb.connect(WAREHOUSE, read_only=True) as con:
        return con.execute(sql, params or []).df()


def base_layout(fig: go.Figure, title: str, height: int = 300) -> go.Figure:
    fig.update_layout(
        title={"text": title, "font": {"size": 15}},
        height=height,
        margin={"l": 10, "r": 10, "t": 45, "b": 10},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "white", "font_color": "#0b0b0b"},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig


def pct(value) -> str:
    return "—" if pd.isna(value) else f"{value:.0%}"


st.title("🎱 Pool Match Lab")
st.caption("Análisis tiro a tiro de partidas grabadas en video.")

sessions = query("select session from agg_sessions order by session")["session"].tolist()
if not sessions:
    st.info("No hay sesiones analizadas. Corre `make demo` o deja un video en `data/videos/`.")
    st.stop()

selected = st.multiselect("Sesiones", sessions, default=sessions)
if not selected:
    st.warning("Elige al menos una sesión.")
    st.stop()

shots = query("select * from fct_shots where session in (select unnest(?))", [selected])
regular = shots[~shots["is_break"]]

# Indicadores del período elegido
cols = st.columns(4)
cols[0].metric("Tiros", len(shots))
cols[1].metric("Acierto", pct(regular["is_successful"].mean()), help="Tiros que embocan sin falta, sin contar quiebres")
cols[2].metric("Faltas", pct(shots["scratch"].mean()), help="Tiros en que la blanca termina embocada")
cols[3].metric("Bolas embocadas", int(shots["n_pocketed"].sum()))

# Evolución por sesión: dos gráficos con su propia escala, nunca doble eje
by_session = query(
    "select * from agg_sessions where session in (select unnest(?)) order by session", [selected]
)
left, right = st.columns(2)
for column, metric, title in (
    (left, "success_rate", "Acierto por sesión"),
    (right, "scratch_rate", "Faltas por sesión"),
):
    fig = go.Figure(
        go.Scatter(
            x=by_session["session"],
            y=by_session[metric],
            mode="lines+markers",
            line={"color": SERIES, "width": 2},
            marker={"size": 9},
            cliponaxis=False,
            customdata=by_session[["n_shots"]],
            hovertemplate="%{x}<br>%{y:.0%} de %{customdata[0]} tiros<extra></extra>",
        )
    )
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    column.plotly_chart(base_layout(fig, title), use_container_width=True)

left, right = st.columns([2, 3])

# ¿Con qué fuerza juegas mejor?
strength = (
    regular.groupby("strength")
    .agg(n=("shot_id", "count"), success=("is_successful", "mean"))
    .reindex(STRENGTH_ORDER)
    .dropna()
    .reset_index()
)
fig = go.Figure(
    go.Bar(
        x=strength["strength"],
        y=strength["success"],
        marker={"color": SERIES, "cornerradius": 4},
        # La muestra va en la etiqueta: con pocos tiros el porcentaje no dice mucho
        text=[f"{s:.0%} · {n} tiros" for s, n in zip(strength["success"], strength["n"], strict=True)],
        textposition="outside",
        customdata=strength[["n"]],
        hovertemplate="%{x}: %{y:.0%} de acierto en %{customdata[0]} tiros<extra></extra>",
    )
)
fig.update_yaxes(tickformat=".0%", rangemode="tozero")
fig.update_layout(bargap=0.45)
left.plotly_chart(base_layout(fig, "Acierto según la fuerza del tiro", 380), use_container_width=True)

# Dónde quedó la blanca después de cada tiro
fig = go.Figure()
fig.add_shape(type="rect", x0=0, y0=0, x1=TABLE_LENGTH, y1=TABLE_WIDTH,
              fillcolor=CLOTH, line={"color": RAIL, "width": 6}, layer="below")
for x, y, radius in POCKETS_M:
    fig.add_shape(type="circle", x0=x - radius, y0=y - radius, x1=x + radius, y1=y + radius,
                  fillcolor=RAIL, line_width=0, layer="below")
ended = regular.dropna(subset=["cue_end_x"])
for outcome, color in OUTCOME_COLORS.items():
    subset = ended[ended["outcome"] == outcome]
    fig.add_trace(go.Scatter(
        x=subset["cue_end_x"],
        y=subset["cue_end_y"],
        mode="markers",
        name=outcome,
        marker={"color": color, "size": BALL_RADIUS * 2 * 330, "line": {"color": "white", "width": 2}},
        customdata=subset[["session", "shot_number", "cue_speed_ms"]],
        hovertemplate="%{customdata[0]} · tiro %{customdata[1]}<br>"
        "velocidad %{customdata[2]:.1f} m/s<extra>" + outcome + "</extra>",
    ))
# Rangos fijos con la proporción real de la mesa; sin esto el gráfico se autoescala mal
fig.update_xaxes(range=[-TABLE_PAD, TABLE_LENGTH + TABLE_PAD], autorange=False, visible=False, constrain="domain")
fig.update_yaxes(range=[TABLE_WIDTH + TABLE_PAD, -TABLE_PAD], autorange=False, visible=False,
                 scaleanchor="x", constrain="domain")
fig.update_layout(legend={"orientation": "h", "y": 1.02, "x": 0, "title_text": "Resultado del tiro: "})
right.plotly_chart(base_layout(fig, "Dónde quedó la blanca", 380), use_container_width=True)
right.caption("Los tiros con falta no aparecen: la blanca terminó en una tronera.")

with st.expander("Todos los tiros"):
    st.dataframe(
        shots[["session", "shot_number", "outcome", "n_pocketed", "strength", "cue_speed_ms", "cue_travel_m"]]
        .rename(columns={
            "session": "Sesión", "shot_number": "Tiro", "outcome": "Resultado",
            "n_pocketed": "Embocadas", "strength": "Fuerza",
            "cue_speed_ms": "Velocidad (m/s)", "cue_travel_m": "Recorrido blanca (m)",
        }),
        hide_index=True,
        use_container_width=True,
    )
