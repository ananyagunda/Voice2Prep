import pandas as pd
import plotly.express as px
import streamlit as st

from engine.pipeline import run_detection_pipeline


st.set_page_config(
    page_title="FairPlay Radar",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    :root {
        --navy: #071426;
        --panel: #0d1d33;
        --panel-light: #122846;
        --cyan: #22d3ee;
        --muted: #91a4bd;
        --text: #edf6ff;
        --green: #2dd4a0;
        --orange: #f59e0b;
        --red: #fb5b67;
    }

    .stApp {
        background: linear-gradient(135deg, #071426 0%, #091a31 55%, #071426 100%);
        color: var(--text);
    }
    .block-container {
        max-width: 1440px;
        padding: 2rem 3rem 2.5rem;
    }
    [data-testid="stHeader"] {
        background: rgba(7, 20, 38, 0.85);
    }
    h1, h2, h3, p, label, .stMarkdown {
        color: var(--text);
    }
    h1 {
        letter-spacing: 0.08em;
        font-size: clamp(2rem, 4vw, 3.25rem) !important;
        margin-bottom: 0.1rem !important;
    }
    h2 {
        font-size: 1.35rem !important;
        letter-spacing: 0.02em;
    }
    h3 {
        font-size: 1rem !important;
        color: var(--muted) !important;
        font-weight: 500 !important;
    }
    .hero {
        border-bottom: 1px solid rgba(34, 211, 238, 0.25);
        margin-bottom: 1.5rem;
        padding: 0.5rem 0 1.25rem;
    }
    .hero-kicker {
        color: var(--cyan);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        margin-bottom: 0.45rem;
    }
    .hero-subtitle {
        color: #b7c8dd;
        font-size: 1.05rem;
        margin: 0.25rem 0 0.55rem;
    }
    .hero-description {
        color: var(--muted);
        font-size: 0.92rem;
        margin: 0;
        max-width: 760px;
    }
    .section-label {
        color: var(--cyan);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        margin: 1.35rem 0 0.6rem;
        text-transform: uppercase;
    }
    .metric-card {
        background: linear-gradient(145deg, #112846, #0b1c32);
        border: 1px solid rgba(145, 164, 189, 0.18);
        border-radius: 12px;
        min-height: 104px;
        padding: 1rem 1.15rem;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.16);
    }
    .metric-label {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
    }
    .metric-value {
        color: var(--text);
        font-size: 2rem;
        font-weight: 750;
        line-height: 1.25;
        margin-top: 0.35rem;
    }
    .metric-accent {
        color: var(--cyan);
    }
    .metric-alert {
        color: var(--red);
    }
    .metric-warning {
        color: var(--orange);
    }
    .stButton > button, .stDownloadButton > button {
        border: 1px solid rgba(34, 211, 238, 0.45);
        border-radius: 8px;
        font-weight: 650;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0ea5c6, #2563eb);
    }
    [data-testid="stFileUploader"] {
        background: rgba(13, 29, 51, 0.75);
        border: 1px dashed rgba(34, 211, 238, 0.45);
        border-radius: 10px;
        padding: 0.35rem;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(145, 164, 189, 0.18);
        border-radius: 10px;
        overflow: hidden;
    }
    @media (max-width: 800px) {
        .block-container { padding: 1.2rem 1rem 2rem; }
        .metric-card { min-height: 88px; padding: 0.8rem; }
        .metric-value { font-size: 1.6rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def create_sample_data() -> pd.DataFrame:
    """Return representative gameplay data for trying the dashboard."""

    return pd.DataFrame(
        {
            "player_id": [f"p{i}" for i in range(10)],
            "score": [100, 120, 110, 130, 90, 115, 125, 105, 95, 5000],
            "kills": [5, 6, 5, 7, 4, 6, 7, 5, 4, 100],
            "deaths": [2, 3, 2, 3, 2, 2, 3, 2, 2, 1],
            "play_time": [15] * 10,
            "actions": [20, 22, 21, 25, 18, 23, 24, 20, 19, 500],
            "action_interval": [2.5, 2.2, 2.4, 2.1, 2.8, 2.3, 2.0, 2.6, 2.7, 0.1],
        }
    )


def metric_card(label: str, value: int, accent_class: str = "") -> None:
    """Render a compact dashboard metric card."""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {accent_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def highlight_suspicious_rows(row: pd.Series) -> list[str]:
    """Highlight rows requiring review in the player analysis table."""

    if row.get("risk_level") == "high" or row.get("anomaly_label") == -1:
        return ["background-color: rgba(251, 91, 103, 0.18)"] * len(row)
    if row.get("risk_level") == "medium":
        return ["background-color: rgba(245, 158, 11, 0.13)"] * len(row)
    return [""] * len(row)


st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">GAMING INTEGRITY ANALYTICS</div>
        <h1>FAIRPLAY RADAR</h1>
        <p class="hero-subtitle">Explainable Gaming Fraud &amp; Bot Detection</p>
        <p class="hero-description">
            Analyze gameplay behavior, surface statistical anomalies, and
            understand the signals behind every player risk score.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-label">01 / Gameplay data</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Upload your gameplay CSV file",
    type=["csv"],
    label_visibility="collapsed",
)

if uploaded_file is not None:
    try:
        input_data = pd.read_csv(uploaded_file)
        st.success("CSV uploaded successfully.")
    except Exception as error:
        st.error(f"Could not read the CSV file: {error}")
        input_data = None
else:
    st.info("No CSV uploaded. Using the included sample gameplay data.")
    input_data = create_sample_data()

if input_data is not None:
    preview_col, action_col = st.columns([3, 1], gap="large")
    with preview_col:
        st.caption(f"{len(input_data):,} gameplay records ready for analysis")
        st.dataframe(input_data.head(), use_container_width=True, height=190)
    with action_col:
        st.markdown('<div class="section-label">02 / Run analysis</div>', unsafe_allow_html=True)
        if st.button("🚀 Run Detection", type="primary", use_container_width=True):
            try:
                with st.spinner("Analyzing gameplay patterns..."):
                    results = run_detection_pipeline(input_data)
                st.session_state["results"] = results
                st.success("Detection completed successfully.")
            except Exception as error:
                st.error(f"Detection failed: {error}")


if "results" in st.session_state:
    results = st.session_state["results"]
    total_players = len(results)
    suspicious_players = int((results["anomaly_label"] == -1).sum())
    high_risk = int((results["risk_level"] == "high").sum())
    medium_risk = int((results["risk_level"] == "medium").sum())

    st.markdown('<div class="section-label">03 / Detection results</div>', unsafe_allow_html=True)
    metric_columns = st.columns(4, gap="medium")
    with metric_columns[0]:
        metric_card("Total Players", total_players, "metric-accent")
    with metric_columns[1]:
        metric_card("Anomalies Detected", suspicious_players, "metric-alert")
    with metric_columns[2]:
        metric_card("High Risk Players", high_risk, "metric-alert")
    with metric_columns[3]:
        metric_card("Medium Risk Players", medium_risk, "metric-warning")

    chart_col, score_col = st.columns(2, gap="medium")
    risk_colors = {"low": "#2dd4a0", "medium": "#f59e0b", "high": "#fb5b67"}
    with chart_col:
        risk_counts = (
            results["risk_level"]
            .value_counts()
            .reindex(["low", "medium", "high"], fill_value=0)
            .rename_axis("Risk Level")
            .reset_index(name="Players")
        )
        fig_risk = px.pie(
            risk_counts,
            names="Risk Level",
            values="Players",
            hole=0.58,
            color="Risk Level",
            color_discrete_map=risk_colors,
        )
        fig_risk.update_layout(
            title="Risk Distribution",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=55, b=10, l=10, r=10),
            legend_title_text="",
        )
        st.plotly_chart(fig_risk, use_container_width=True)
    with score_col:
        score_data = results.loc[results["risk_score"] > 0].sort_values(
            "risk_score", ascending=False
        )
        if score_data.empty:
            st.info("No players currently have a risk score above 0.")
        else:
            fig_scores = px.bar(
                score_data,
                x="risk_score",
                y="player_id",
                orientation="h",
                text="risk_score",
                color="risk_level",
                color_discrete_map=risk_colors,
                category_orders={
                    "player_id": score_data["player_id"].tolist()
                },
                labels={
                    "player_id": "Player",
                    "risk_score": "Risk Score",
                    "risk_level": "Risk Level",
                },
            )
            fig_scores.update_traces(
                texttemplate="%{text:.0f}",
                textposition="outside",
                cliponaxis=False,
            )
            fig_scores.update_layout(
                title="Player Risk Scores",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=55, b=10, l=10, r=30),
                xaxis=dict(range=[0, 100], gridcolor="rgba(145,164,189,0.15)"),
                yaxis=dict(
                    gridcolor="rgba(0,0,0,0)",
                    categoryorder="array",
                    categoryarray=score_data["player_id"].tolist(),
                    autorange="reversed",
                ),
                legend_title_text="",
            )
            st.plotly_chart(fig_scores, use_container_width=True)

    st.markdown(
        """
        <div style="
            background: rgba(13, 29, 51, 0.72);
            border-left: 3px solid #22d3ee;
            border-radius: 6px;
            color: #b7c8dd;
            font-size: 0.86rem;
            margin: 0.4rem 0 1.2rem;
            padding: 0.7rem 0.9rem;
        ">
            Risk scores are screening indicators, not proof of cheating.
            Flagged players require human review.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">04 / Player analysis</div>', unsafe_allow_html=True)
    table_data = results.sort_values("risk_score", ascending=False)
    st.dataframe(
        table_data.style.apply(highlight_suspicious_rows, axis=1),
        use_container_width=True,
        height=min(520, 125 + len(table_data) * 38),
    )

    st.markdown('<div class="section-label">05 / Export</div>', unsafe_allow_html=True)
    csv_data = results.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Detection Report",
        data=csv_data,
        file_name="fairplay_radar_report.csv",
        mime="text/csv",
    )
    st.caption(
        "FairPlay Radar identifies suspicious gameplay patterns for review. "
        "An anomaly flag is not proof of cheating."
    )
