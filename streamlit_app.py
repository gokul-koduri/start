"""Streamlit Dashboard — Opportunity Intelligence Platform.

Run:
    pip install streamlit plotly pandas
    streamlit run streamlit_app.py

Features:
    - Executive KPI overview with live DB stats
    - Failed startup explorer with filters & sorting
    - Risk score distribution & top riskiest startups
    - Sector failure analysis (bar/pie/treemap charts)
    - Geographic distribution & country-level insights
    - BLS survival rate trends
    - News intelligence feed
    - Knowledge graph browser (entity search + relationship table)
    - Revival opportunity matrix
    - AI Analyst chat (via Ollama)
    - LLM pricing & benchmark tracker
    - Pipeline health monitor
"""

import json
import logging
import os
import sys
from contextlib import closing
from datetime import datetime

# ── DB Connection ────────────────────────────────────────────
# Streamlit hot-reloads modules, so we handle import failures gracefully.

_db_available = True
try:
    import pymysql
    from pymysql.cursors import DictCursor

    def get_db():
        return pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", ""),
            database=os.environ.get("MYSQL_DATABASE", "startup_research"),
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=5,
            autocommit=False,
        )
except ImportError:
    _db_available = False

    def get_db():
        return None


def query_db(sql, params=None):
    """Execute a query and return list of dicts. Returns [] on failure."""
    if not _db_available:
        return []
    try:
        with closing(get_db()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()
    except Exception as e:
        logging.warning("DB query failed: %s", e)
        return []


# ── Streamlit Imports ────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Opportunity Intelligence Platform",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme & CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .stMetricValue { font-size: 2rem; font-weight: 700; }
    .risk-critical { color: #dc3545; font-weight: bold; }
    .risk-high { color: #fd7e14; font-weight: bold; }
    .risk-moderate { color: #ffc107; font-weight: bold; }
    .risk-low { color: #198754; font-weight: bold; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1117 0%, #161b22 100%); }
    div[data-testid="stSidebar"] * { color: #e6edf3 !important; }
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border-radius: 12px; padding: 20px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/briefcase.png", width=64)
    st.title("🔬 Opportunity Intelligence")
    st.caption("Startup Failure & Revival Analytics")

    page = st.radio(
        "Navigate",
        ["📊 Overview", "🏢 Startup Explorer", "⚠️ Risk Scores",
         "📈 Sector Analysis", "🌍 Geographic Insights", "📰 News Feed",
         "🔗 Knowledge Graph", "🔄 Revival Opportunities", "💬 AI Analyst",
         "💰 LLM Pricing", "🩺 Pipeline Health", "🎭 Sentiment Analysis"],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Last load: {datetime.now().strftime('%H:%M:%S')}")

    # DB status indicator
    db_check = query_db("SELECT 1 as ok")
    status_color = "🟢" if db_check else "🔴"
    st.caption(f"{status_color} Database {'connected' if db_check else 'unavailable'}")

    st.divider()
    st.caption(" tiers: Free / Pro ($49) / Enterprise ($1000)")

# ── Cache Data Loaders ──────────────────────────────────────

@st.cache_data(ttl=300)
def load_startups():
    return query_db("""
        SELECT s.*, r.risk_score, r.risk_level, r.recommendation
        FROM failed_startups s
        LEFT JOIN startup_risk_scores r ON r.startup_id = s.id
        ORDER BY s.year_shutdown DESC, s.name
    """)

@st.cache_data(ttl=300)
def load_stats():
    rows = query_db("""
        SELECT
            (SELECT COUNT(*) FROM failed_startups) as total_startups,
            (SELECT COUNT(*) FROM failed_startups WHERE manufacturing_sub_sector IS NOT NULL) as mfg_startups,
            (SELECT COUNT(*) FROM news_articles) as total_articles,
            (SELECT COUNT(*) FROM news_articles WHERE is_manufacturing = 1) as mfg_articles,
            (SELECT COUNT(DISTINCT sector) FROM failed_startups) as sectors,
            (SELECT COUNT(DISTINCT country) FROM failed_startups) as countries,
            (SELECT COUNT(*) FROM startup_risk_scores WHERE risk_level = 'critical') as critical_count,
            (SELECT COUNT(*) FROM startup_risk_scores WHERE risk_level = 'high') as high_risk_count,
            (SELECT MAX(collected_at) FROM failed_startups) as last_collection
    """)
    return rows[0] if rows else {}

@st.cache_data(ttl=300)
def load_news(limit=100):
    return query_db("""
        SELECT title, url, source_name, published_at, summary,
               is_manufacturing, mentions_failure, startup_name_extracted
        FROM news_articles ORDER BY collected_at DESC LIMIT %s
    """, (limit,))

@st.cache_data(ttl=300)
def load_risk_scores():
    return query_db("""
        SELECT s.name, s.sector, s.country, s.funding_raised_usd,
               s.year_founded, s.year_shutdown, s.failure_category,
               r.risk_score, r.risk_level, r.recommendation, r.factors_json
        FROM startup_risk_scores r
        JOIN failed_startups s ON s.id = r.startup_id
        ORDER BY r.risk_score DESC
    """)

@st.cache_data(ttl=300)
def load_survival_rates():
    return query_db("""
        SELECT naics_code, industry_name, year, quarter,
               age_1_yr_survival, age_2_yr_survival,
               age_3_yr_survival, age_5_yr_survival,
               establishment_count
        FROM bls_survival_rates
        ORDER BY year DESC, naics_code
    """)

@st.cache_data(ttl=300)
def load_kg_entities(limit=200):
    return query_db("""
        SELECT e.id, e.name, t.type_name as type, e.mention_count as mentions
        FROM kg_entities e, kg_entity_types t
        WHERE e.entity_type_id = t.id
        ORDER BY e.mention_count DESC LIMIT %s
    """, (limit,))

@st.cache_data(ttl=300)
def load_kg_relationships(limit=500):
    return query_db("""
        SELECT r.source_entity_id, r.target_entity_id,
               r.relationship_type, r.weight,
               s.name as source_name, t.name as target_name
        FROM kg_relationships r
        JOIN kg_entities s ON s.id = r.source_entity_id
        JOIN kg_entities t ON t.id = r.target_entity_id
        ORDER BY r.weight DESC LIMIT %s
    """, (limit,))

@st.cache_data(ttl=300)
def load_revival_opportunities():
    return query_db("SELECT * FROM revival_industries ORDER BY industry")

@st.cache_data(ttl=300)
def load_pipeline_runs(limit=50):
    return query_db("""
        SELECT id, pipeline_name, agent_name, started_at, completed_at,
               status, records_affected, error_message, trigger_type
        FROM agent_runs ORDER BY started_at DESC LIMIT %s
    """, (limit,))

@st.cache_data(ttl=300)
def load_llm_pricing():
    return query_db("""
        SELECT provider, model_name, input_price_per_1m, output_price_per_1m,
               context_window, modality, pricing_tier
        FROM llm_pricing
        ORDER BY input_price_per_1m
    """)

@st.cache_data(ttl=300)
def load_llm_benchmarks():
    return query_db("""
        SELECT provider, model_name, benchmark_name, benchmark_score,
               benchmark_category, speed_tokens_per_sec
        FROM llm_benchmarks
        ORDER BY benchmark_category, benchmark_score DESC
    """)


# ══════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════

# ── Overview ─────────────────────────────────────────────────
if page == "📊 Overview":
    st.title("📊 Executive Overview")
    stats = load_stats()

    if not stats:
        st.warning("No database connection. Run the pipeline first or check MySQL settings.")
        st.code("python run_agent.py --pipeline collect-only")
        st.stop()

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Startups", f"{stats.get('total_startups', 0):,}")
    col2.metric("Manufacturing", f"{stats.get('mfg_startups', 0):,}")
    col3.metric("News Articles", f"{stats.get('total_articles', 0):,}")
    col4.metric("Sectors Tracked", f"{stats.get('sectors', 0):,}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Countries", f"{stats.get('countries', 0):,}")
    col2.metric("Mfg Articles", f"{stats.get('mfg_articles', 0):,}")
    col3.metric("🔴 Critical Risk", f"{stats.get('critical_count', 0):,}")
    col4.metric("🟠 High Risk", f"{stats.get('high_risk_count', 0):,}")

    st.divider()

    # Recent failures
    startups = load_startups()
    if startups:
        st.subheader("🕐 Recent Failures")
        df = pd.DataFrame(startups)
        recent = df.nlargest(10, "year_shutdown")[["name", "sector", "country", "year_shutdown", "failure_category"]]
        st.dataframe(recent, use_container_width=True, hide_index=True)

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Failure Categories")
            cat_counts = df["failure_category"].value_counts().head(10)
            fig = px.pie(values=cat_counts.values, names=cat_counts.index,
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("Failures by Year")
            year_counts = df["year_shutdown"].value_counts().sort_index()
            fig2 = px.bar(x=year_counts.index, y=year_counts.values,
                          labels={"x": "Year", "y": "Failures"},
                          color=year_counts.values,
                          color_continuous_scale="Reds")
            fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # Collection freshness
    lc = stats.get("last_collection")
    if lc:
        st.divider()
        st.caption(f"📅 Last data collection: {lc}")


# ── Startup Explorer ─────────────────────────────────────────
elif page == "🏢 Startup Explorer":
    st.title("🏢 Startup Explorer")

    startups = load_startups()
    if not startups:
        st.info("No startup data available. Run the collection pipeline first.")
        st.stop()

    df = pd.DataFrame(startups)

    # Filters
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        sectors = sorted(df["sector"].dropna().unique())
        selected_sectors = col1.multiselect("Sector", sectors, default=sectors[:5])

        countries = sorted(df["country"].dropna().unique())
        selected_countries = col2.multiselect("Country", countries, default=countries)

        categories = sorted(df["failure_category"].dropna().unique())
        selected_cats = col3.multiselect("Failure Category", categories, default=categories)

        year_range = col4.slider("Shutdown Year", int(df["year_shutdown"].min()),
                                 int(df["year_shutdown"].max()),
                                 (int(df["year_shutdown"].min()), int(df["year_shutdown"].max())))

    # Apply filters
    mask = pd.Series([True] * len(df))
    if selected_sectors:
        mask &= df["sector"].isin(selected_sectors)
    if selected_countries:
        mask &= df["country"].isin(selected_countries)
    if selected_cats:
        mask &= df["failure_category"].isin(selected_cats)
    mask &= df["year_shutdown"].between(year_range[0], year_range[1])
    filtered = df[mask]

    st.metric("Matching Startups", f"{len(filtered):,}")
    st.dataframe(
        filtered[["name", "sector", "country", "year_founded", "year_shutdown",
                   "funding_raised_usd", "failure_category", "failure_reason", "risk_level"]],
        use_container_width=True, hide_index=True, height=500,
    )

    # Detail view
    st.divider()
    st.subheader("🔎 Startup Detail")
    startup_names = filtered["name"].tolist()
    if startup_names:
        selected = st.selectbox("Select a startup", startup_names)
        row = filtered[filtered["name"] == selected].iloc[0]

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"### {row['name']}")
            st.markdown(f"**Sector:** {row.get('sector', 'N/A')}")
            st.markdown(f"**Country:** {row.get('country', 'N/A')} | **Region:** {row.get('region', 'N/A')}")
            st.markdown(f"**Founded:** {row.get('year_founded', 'N/A')} → **Shutdown:** {row.get('year_shutdown', 'N/A')}")
            funding = row.get("funding_raised_usd")
            st.markdown(f"**Funding:** ${funding:,.0f}" if funding else "**Funding:** Unknown")
            st.markdown(f"**Failure Category:** {row.get('failure_category', 'N/A')}")
            st.markdown(f"**Failure Reason:** {row.get('failure_reason', 'N/A')}")

        with col_b:
            if pd.notna(row.get("risk_score")):
                risk = row["risk_score"]
                level = row.get("risk_level", "")
                color = {"critical": "🔴", "high": "🟠", "moderate": "🟡", "low": "🟢"}.get(level, "⚪")
                st.metric("Risk Score", f"{risk:.2f}", delta=f"{color} {level.title()}")
                if pd.notna(row.get("recommendation")):
                    st.info(f"💡 {row['recommendation']}")
            else:
                st.info("No risk score calculated")


# ── Risk Scores ──────────────────────────────────────────────
elif page == "⚠️ Risk Scores":
    st.title("⚠️ Failure Risk Analysis")

    risk_data = load_risk_scores()
    if not risk_data:
        st.info("No risk scores available. Run: `python run_agent.py --pipeline analysis`")
        st.stop()

    df = pd.DataFrame(risk_data)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Distribution")
        level_counts = df["risk_level"].value_counts()
        colors = {"critical": "#dc3545", "high": "#fd7e14", "moderate": "#ffc107", "low": "#198754"}
        fig = px.pie(values=level_counts.values, names=level_counts.index,
                     color=level_counts.index, color_discrete_map=colors,
                     hole=0.45)
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Risk Score Histogram")
        fig2 = px.histogram(df, x="risk_score", nbins=20,
                            color_discrete_sequence=["#6f42c1"],
                            labels={"risk_score": "Risk Score", "count": "Startups"})
        fig2.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("🔴 Top 20 Riskiest Startups")
    top_risk = df.head(20)
    st.dataframe(
        top_risk[["name", "sector", "country", "risk_score", "risk_level", "recommendation"]],
        use_container_width=True, hide_index=True,
    )

    # Risk by sector
    st.subheader("Average Risk by Sector")
    sector_risk = df.groupby("sector")["risk_score"].mean().sort_values(ascending=False).head(15)
    fig3 = px.bar(x=sector_risk.values, y=sector_risk.index, orientation="h",
                  color=sector_risk.values, color_continuous_scale="RdYlGn_r",
                  labels={"x": "Avg Risk Score", "y": ""})
    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)


# ── Sector Analysis ──────────────────────────────────────────
elif page == "📈 Sector Analysis":
    st.title("📈 Sector Failure Analysis")

    startups = load_startups()
    if not startups:
        st.info("No data available.")
        st.stop()

    df = pd.DataFrame(startups)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Failures by Sector")
        sector_counts = df["sector"].value_counts().head(20)
        fig = px.bar(x=sector_counts.values, y=sector_counts.index, orientation="h",
                     color=sector_counts.values, color_continuous_scale="Viridis",
                     labels={"x": "Count", "y": ""})
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Sector Treemap")
        sector_data = df.groupby(["sector", "failure_category"]).size().reset_index(name="count")
        fig2 = px.treemap(sector_data, path=["sector", "failure_category"], values="count",
                          color="count", color_continuous_scale="Blues")
        fig2.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # Sector timeline
    st.subheader("Sector Failure Timeline")
    top_sectors = df["sector"].value_counts().head(8).index.tolist()
    timeline = df[df["sector"].isin(top_sectors)].groupby(["year_shutdown", "sector"]).size().reset_index(name="count")
    fig3 = px.line(timeline, x="year_shutdown", y="count", color="sector",
                   markers=True, labels={"year_shutdown": "Year", "count": "Failures"})
    fig3.update_layout(height=400)
    st.plotly_chart(fig3, use_container_width=True)

    # BLS Survival Rates
    st.divider()
    st.subheader("📉 BLS Survival Rates")
    bls = load_survival_rates()
    if bls:
        bls_df = pd.DataFrame(bls)
        industries = sorted(bls_df["industry_name"].unique())
        selected_ind = st.selectbox("Industry", industries, index=0)
        ind_data = bls_df[bls_df["industry_name"] == selected_ind].sort_values("year")

        if not ind_data.empty:
            fig4 = go.Figure()
            for col_name, label in [("age_1_yr_survival", "1-Year"), ("age_2_yr_survival", "2-Year"),
                                     ("age_3_yr_survival", "3-Year"), ("age_5_yr_survival", "5-Year")]:
                if col_name in ind_data.columns:
                    fig4.add_trace(go.Scatter(x=ind_data["year"], y=ind_data[col_name],
                                              mode="lines+markers", name=label))
            fig4.update_layout(title=f"Survival Rates: {selected_ind}",
                               yaxis_title="Survival Rate (%)", xaxis_title="Year",
                               height=400)
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No BLS survival rate data. Run the BLS collector.")


# ── Geographic Insights ──────────────────────────────────────
elif page == "🌍 Geographic Insights":
    st.title("🌍 Geographic Distribution")

    startups = load_startups()
    if not startups:
        st.info("No data available.")
        st.stop()

    df = pd.DataFrame(startups)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Failures by Country")
        country_counts = df["country"].value_counts().head(15)
        fig = px.bar(x=country_counts.values, y=country_counts.index, orientation="h",
                     color=country_counts.values, color_continuous_scale="Plasma",
                     labels={"x": "Count", "y": ""})
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Failures by Region")
        region_counts = df["region"].value_counts().head(10)
        fig2 = px.pie(values=region_counts.values, names=region_counts.index,
                      hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # Country × Sector heatmap
    st.divider()
    st.subheader("Country × Sector Heatmap")
    top_countries = df["country"].value_counts().head(10).index.tolist()
    top_sectors = df["sector"].value_counts().head(10).index.tolist()
    heat = df[df["country"].isin(top_countries) & df["sector"].isin(top_sectors)]
    pivot = heat.groupby(["country", "sector"]).size().reset_index(name="count")
    fig3 = px.density_heatmap(pivot, x="sector", y="country", z="count",
                               color_continuous_scale="YlOrRd")
    fig3.update_layout(height=450)
    st.plotly_chart(fig3, use_container_width=True)

    # Country funding
    st.subheader("Average Funding by Country")
    funding_by_country = df[df["funding_raised_usd"] > 0].groupby("country")["funding_raised_usd"].mean().sort_values(ascending=False).head(15)
    fig4 = px.bar(x=funding_by_country.values, y=funding_by_country.index, orientation="h",
                  labels={"x": "Avg Funding (USD)", "y": ""},
                  color=funding_by_country.values, color_continuous_scale="Greens")
    fig4.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)


# ── News Feed ────────────────────────────────────────────────
elif page == "📰 News Feed":
    st.title("📰 News Intelligence Feed")

    news = load_news(200)
    if not news:
        st.info("No news articles. Run the collection pipeline.")
        st.stop()

    df = pd.DataFrame(news)

    col1, col2 = st.columns([3, 1])
    with col2:
        st.metric("Total Articles", f"{len(df):,}")
        st.metric("Manufacturing", f"{df['is_manufacturing'].sum():,}")
        st.metric("Failure Mentions", f"{df['mentions_failure'].sum():,}")

        sources = df["source_name"].value_counts()
        st.subheader("Sources")
        st.dataframe(sources, height=200)

    with col1:
        # Filter
        mfg_only = st.checkbox("Manufacturing only", value=False)
        failure_only = st.checkbox("Failure mentions only", value=False)
        search = st.text_input("🔍 Search", placeholder="Filter by title...")

        filtered = df.copy()
        if mfg_only:
            filtered = filtered[filtered["is_manufacturing"] == 1]
        if failure_only:
            filtered = filtered[filtered["mentions_failure"] == 1]
        if search:
            filtered = filtered[filtered["title"].str.contains(search, case=False, na=False)]

        for _, row in filtered.head(30).iterrows():
            with st.container():
                icons = []
                if row["is_manufacturing"]:
                    icons.append("🏭")
                if row["mentions_failure"]:
                    icons.append("⚠️")
                icon_str = " ".join(icons)

                title = row["title"] or "No title"
                url = row.get("url", "")
                if url:
                    st.markdown(f"### {icon_str} [{title}]({url})")
                else:
                    st.markdown(f"### {icon_str} {title}")

                meta = f"*{row.get('source_name', 'Unknown')}*"
                if row.get("published_at"):
                    meta += f" · {row['published_at']}"
                if row.get("startup_name_extracted"):
                    meta += f" · 🏢 {row['startup_name_extracted']}"
                st.caption(meta)

                if row.get("summary"):
                    st.write(row["summary"][:300])
                st.divider()


# ── Knowledge Graph ──────────────────────────────────────────
elif page == "🔗 Knowledge Graph":
    st.title("🔗 Knowledge Graph Browser")

    entities = load_kg_entities(500)
    relationships = load_kg_relationships(1000)

    if not entities:
        st.info("No knowledge graph data. Run: `python run_agent.py --pipeline analysis`")
        st.stop()

    ent_df = pd.DataFrame(entities)
    rel_df = pd.DataFrame(relationships)

    col1, col2, col3 = st.columns(3)
    col1.metric("Entities", f"{len(ent_df):,}")
    col2.metric("Relationships", f"{len(rel_df):,}")
    col3.metric("Entity Types", f"{ent_df['type'].nunique()}")

    # Entity type breakdown
    st.subheader("Entity Types")
    type_counts = ent_df["type"].value_counts()
    fig = px.bar(x=type_counts.values, y=type_counts.index, orientation="h",
                 color=type_counts.values, color_continuous_scale="Teal",
                 labels={"x": "Count", "y": ""})
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # Entity search
    st.subheader("🔍 Entity Search")
    entity_search = st.text_input("Search entities...", placeholder="e.g. Uber, EV, Sequoia")
    if entity_search:
        results = ent_df[ent_df["name"].str.contains(entity_search, case=False)]
        st.dataframe(results, use_container_width=True, hide_index=True)

        # Show relationships for first match
        if not results.empty:
            ent_id = results.iloc[0]["id"]
            rels = rel_df[(rel_df["source_entity_id"] == ent_id) | (rel_df["target_entity_id"] == ent_id)]
            if not rels.empty:
                st.subheader(f"Relationships: {results.iloc[0]['name']}")
                st.dataframe(rels[["source_name", "relationship_type", "target_name", "weight"]],
                             use_container_width=True, hide_index=True)

    # Top relationships
    st.divider()
    st.subheader("Top Relationships by Weight")
    st.dataframe(
        rel_df[["source_name", "relationship_type", "target_name", "weight"]].head(50),
        use_container_width=True, hide_index=True,
    )

    # Interactive network (simplified)
    st.subheader("Network Visualization")
    top_ents = ent_df.head(30)
    top_ent_ids = set(top_ents["id"].tolist())
    top_rels = rel_df[rel_df["source_entity_id"].isin(top_ent_ids) & rel_df["target_entity_id"].isin(top_ent_ids)]

    if not top_rels.empty:
        # Build nodes and edges for plotly
        node_names = {}
        for _, e in top_ents.iterrows():
            node_names[e["id"]] = e["name"]

        fig = px.scatter(top_ents, x="mentions", y="type", size="mentions",
                         hover_name="name", color="type",
                         size_max=40, title="Top Entities by Mention Count")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No relationships between top entities.")


# ── Revival Opportunities ────────────────────────────────────
elif page == "🔄 Revival Opportunities":
    st.title("🔄 Revival Opportunity Matrix")

    revival = load_revival_opportunities()
    if not revival:
        st.info("No revival data. Run: `python run_agent.py --pipeline analysis`")
        st.stop()

    df = pd.DataFrame(revival)

    for _, row in df.iterrows():
        with st.expander(f"🔄 {row['industry']}", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Why it's returning:**")
                st.write(row.get("why_returning", "N/A"))
                st.markdown("**Market Fit:**")
                st.write(row.get("market_fit", "N/A"))
            with col_b:
                st.markdown("**Died Period:**")
                st.write(row.get("died_period", "N/A"))
                st.markdown("**Market Size 2030:**")
                st.write(row.get("market_size_2030", "N/A"))
                if row.get("key_investors"):
                    st.markdown("**Key Investors:**")
                    st.write(row["key_investors"])

    st.divider()
    st.subheader("📋 All Revival Industries")
    st.dataframe(df[["industry", "died_period", "why_returning", "market_fit"]],
                 use_container_width=True, hide_index=True)


# ── AI Analyst ───────────────────────────────────────────────
elif page == "💬 AI Analyst":
    st.title("💬 AI Analyst")
    st.caption("Ask questions about startup failures, trends, and opportunities.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about startup failures, trends, opportunities..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Try to use Ollama for response
            response_placeholder = st.empty()
            answer = ""

            try:
                import urllib.request
                import json as json_mod

                # Build context from DB
                startups = load_startups()
                context = f"You are an AI analyst for a startup failure research platform. We track {len(startups)} failed startups. Answer concisely with data-driven insights.\n\nUser question: {prompt}"

                if startups:
                    sectors = pd.DataFrame(startups)["sector"].value_counts().head(5)
                    context += f"\nTop failure sectors: {sectors.to_dict()}"
                    countries = pd.DataFrame(startups)["country"].value_counts().head(5)
                    context += f"\nTop failure countries: {countries.to_dict()}"

                payload = json_mod.dumps({
                    "model": "llama3",
                    "messages": [{"role": "user", "content": context}],
                    "stream": False,
                }).encode()

                req = urllib.request.Request(
                    "http://localhost:11434/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )

                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json_mod.loads(resp.read().decode())
                    answer = result.get("message", {}).get("content", "")

            except Exception as e:
                answer = f"⚠️ Ollama not available ({type(e).__name__}). Make sure Ollama is running with `ollama serve` and llama3 model pulled."

            response_placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

    # Quick questions
    st.divider()
    st.subheader("💡 Quick Questions")
    quick_qs = [
        "What are the top 5 failure reasons?",
        "Which sectors have the most manufacturing failures?",
        "What is the average lifespan of failed startups?",
        "Which countries have the highest startup failure rates?",
        "What are the best revival opportunities?",
    ]
    cols = st.columns(len(quick_qs))
    for i, q in enumerate(quick_qs):
        if cols[i].button(q, key=f"qq_{i}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()


# ── LLM Pricing ──────────────────────────────────────────────
elif page == "💰 LLM Pricing":
    st.title("💰 LLM Pricing & Benchmarks")

    pricing = load_llm_pricing()
    benchmarks = load_llm_benchmarks()

    tab1, tab2, tab3 = st.tabs(["📊 Pricing Comparison", "🏆 Benchmarks", "📉 Price Trends"])

    with tab1:
        if pricing:
            df = pd.DataFrame(pricing)
            st.dataframe(df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.scatter(df, x="input_price_per_1m", y="output_price_per_1m",
                                 color="provider", hover_name="model_name",
                                 size="context_window",
                                 labels={"input_price_per_1m": "Input $/1M tokens",
                                         "output_price_per_1m": "Output $/1M tokens"},
                                 title="Price vs Context Window")
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                avg_by_provider = df.groupby("provider").agg({
                    "input_price_per_1m": "mean",
                    "output_price_per_1m": "mean",
                }).reset_index()
                fig2 = px.bar(avg_by_provider, x="provider",
                              y=["input_price_per_1m", "output_price_per_1m"],
                              barmode="group", title="Avg Price by Provider")
                fig2.update_layout(height=450)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No LLM pricing data. Run: `python run_agent.py --pipeline weekly`")

    with tab2:
        if benchmarks:
            bdf = pd.DataFrame(benchmarks)
            categories = bdf["benchmark_category"].dropna().unique()
            selected_cat = st.selectbox("Category", categories)
            cat_data = bdf[bdf["benchmark_category"] == selected_cat]

            fig = px.bar(cat_data, x="benchmark_score", y="model_name",
                         color="provider", orientation="h",
                         title=f"Benchmark: {selected_cat}",
                         labels={"benchmark_score": "Score", "model_name": ""})
            fig.update_layout(height=max(400, len(cat_data) * 30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No benchmark data. Run: `python run_agent.py --pipeline weekly`")

    with tab3:
        price_changes = query_db("""
            SELECT provider, model_name, old_input_price, new_input_price,
                   old_output_price, new_output_price, input_change_pct, detected_at
            FROM llm_price_changes ORDER BY detected_at DESC LIMIT 50
        """)
        if price_changes:
            st.dataframe(pd.DataFrame(price_changes), use_container_width=True, hide_index=True)
        else:
            st.info("No price changes detected yet.")


# ── Pipeline Health ──────────────────────────────────────────
elif page == "🩺 Pipeline Health":
    st.title("🩺 Pipeline Health Monitor")

    runs = load_pipeline_runs(100)
    if not runs:
        st.info("No pipeline runs recorded.")
        st.stop()

    df = pd.DataFrame(runs)

    # Status counts
    col1, col2, col3, col4 = st.columns(4)
    status_counts = df["status"].value_counts()
    col1.metric("Total Runs", f"{len(df):,}")
    col2.metric("✅ Success", f"{status_counts.get('success', 0):,}")
    col3.metric("⚠️ Partial", f"{status_counts.get('partial', 0):,}")
    col4.metric("❌ Failed", f"{status_counts.get('failed', 0):,}")

    # Recent runs table
    st.subheader("Recent Pipeline Runs")
    display_cols = ["pipeline_name", "agent_name", "started_at", "completed_at",
                    "status", "records_affected", "trigger_type"]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=400)

    # Status pie
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(values=status_counts.values, names=status_counts.index,
                     color=status_counts.index,
                     color_discrete_map={"success": "#198754", "partial": "#ffc107",
                                         "failed": "#dc3545", "running": "#0d6efd"},
                     hole=0.4, title="Run Status Distribution")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Errors
        errors = df[df["status"] == "failed"]
        if not errors.empty:
            st.subheader("Recent Errors")
            for _, row in errors.head(10).iterrows():
                st.error(f"**{row['agent_name']}** ({row['started_at']}): {row.get('error_message', 'Unknown')}")
        else:
            st.success("No recent errors! 🎉")

    # Span monitoring
    st.divider()
    st.subheader("📊 Span Monitor (Performance)")
    spans = query_db("""
        SELECT pipeline_name, agent_name, duration_seconds, records_affected,
               status, anomaly_detected, anomaly_type, snapshot_at
        FROM span_snapshots ORDER BY snapshot_at DESC LIMIT 50
    """)
    if spans:
        sp_df = pd.DataFrame(spans)
        fig2 = px.scatter(sp_df, x="snapshot_at", y="duration_seconds",
                          color="agent_name", size="records_affected",
                          title="Agent Duration Over Time",
                          labels={"duration_seconds": "Duration (s)", "snapshot_at": ""})
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)

        anomalies = sp_df[sp_df["anomaly_detected"] == 1]
        if not anomalies.empty:
            st.warning(f"⚠️ {len(anomalies)} anomalies detected!")
            st.dataframe(anomalies[["agent_name", "duration_seconds", "anomaly_type", "anomaly_detail"]],
                         use_container_width=True, hide_index=True)
    else:
        st.info("No span monitoring data.")


# ── Sentiment Analysis Page ──────────────────────────────────

elif page == "🎭 Sentiment Analysis":
    st.title("🎭 Sentiment Analysis")
    st.caption("News article sentiment scoring and trend analysis")

    # KPI cards
    total_articles = query_db("SELECT COUNT(*) as cnt FROM news_articles")
    scored = query_db(
        """SELECT sentiment_label, COUNT(*) as cnt, AVG(sentiment_score) as avg_score
           FROM news_articles WHERE sentiment_score IS NOT NULL GROUP BY sentiment_label"""
    )
    total = total_articles[0]["cnt"] if total_articles else 0
    scored_count = sum(r["cnt"] for r in scored) if scored else 0
    coverage = round(scored_count / max(total, 1) * 100, 1)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Articles", f"{total:,}")
    col2.metric("Scored", f"{scored_count:,}")
    col3.metric("Coverage", f"{coverage}%")
    avg_score = query_db("SELECT AVG(sentiment_score) as avg FROM news_articles WHERE sentiment_score IS NOT NULL")
    avg_val = avg_score[0]["avg"] if avg_score and avg_score[0]["avg"] else 0
    col4.metric("Avg Sentiment", f"{avg_val:.3f}")

    if scored_count == 0:
        st.info("No articles scored yet. Run the sentiment agent: `python run_agent.py --pipeline analysis`")
    else:
        st.divider()

        # Distribution pie chart
        st.subheader("Sentiment Distribution")
        dist_df = pd.DataFrame(scored)
        fig_dist = px.pie(dist_df, values="cnt", names="sentiment_label",
                           color="sentiment_label",
                           color_discrete_map={"positive": "#22c55e", "negative": "#ef4444", "neutral": "#6366f1"},
                           hole=0.4, title="Sentiment Labels")
        st.plotly_chart(fig_dist, use_container_width=True)

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("📈 Sentiment Timeline")
            timeline = query_db(
                """SELECT DATE(sentiment_analyzed_at) as day,
                          AVG(sentiment_score) as avg_score,
                          COUNT(*) as cnt
                   FROM news_articles
                   WHERE sentiment_score IS NOT NULL
                   GROUP BY day ORDER BY day DESC LIMIT 30"""
            )
            if timeline:
                tl_df = pd.DataFrame(timeline)
                fig_tl = px.line(tl_df, x="day", y="avg_score",
                                 title="Average Sentiment Over Time",
                                 labels={"day": "", "avg_score": "Avg Sentiment"})
                fig_tl.add_hrect(y0=0.05, y1=1, fillcolor="green", opacity=0.05)
                fig_tl.add_hrect(y0=-1, y1=-0.05, fillcolor="red", opacity=0.05)
                fig_tl.update_layout(height=350)
                st.plotly_chart(fig_tl, use_container_width=True)

        with col_right:
            st.subheader("📡 Sentiment by Source")
            by_source = query_db(
                """SELECT source_name, sentiment_label, COUNT(*) as cnt
                   FROM news_articles
                   WHERE sentiment_score IS NOT NULL
                   GROUP BY source_name, sentiment_label"""
            )
            if by_source:
                src_df = pd.DataFrame(by_source)
                fig_src = px.bar(src_df, x="source_name", y="cnt", color="sentiment_label",
                                 barmode="group",
                                 color_discrete_map={"positive": "#22c55e", "negative": "#ef4444", "neutral": "#6366f1"},
                                 title="Articles by Source and Sentiment")
                fig_src.update_layout(height=350, xaxis_tickangle=-30)
                st.plotly_chart(fig_src, use_container_width=True)

        # Top positive/negative articles
        st.divider()
        pos, neg = st.columns(2)

        with pos:
            st.subheader("👍 Most Positive")
            positive = query_db(
                """SELECT title, source_name, sentiment_score, published_at
                   FROM news_articles
                   WHERE sentiment_score > 0
                   ORDER BY sentiment_score DESC LIMIT 10"""
            )
            if positive:
                st.dataframe(pd.DataFrame(positive), use_container_width=True, hide_index=True)
            else:
                st.caption("No positive articles scored yet.")

        with neg:
            st.subheader("👎 Most Negative")
            negative = query_db(
                """SELECT title, source_name, sentiment_score, published_at
                   FROM news_articles
                   WHERE sentiment_score < 0
                   ORDER BY sentiment_score ASC LIMIT 10"""
            )
            if negative:
                st.dataframe(pd.DataFrame(negative), use_container_width=True, hide_index=True)
            else:
                st.caption("No negative articles scored yet.")

        # Model info
        st.divider()
        models_used = query_db(
            """SELECT sentiment_model, COUNT(*) as cnt, MIN(sentiment_analyzed_at) as first_used
               FROM news_articles WHERE sentiment_model IS NOT NULL GROUP BY sentiment_model"""
        )
        if models_used:
            st.subheader("🤖 Model Usage")
            st.dataframe(pd.DataFrame(models_used), use_container_width=True, hide_index=True)

