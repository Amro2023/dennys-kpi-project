from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


DATA_DIR = Path(__file__).resolve().parent / "data"


def clean_money(value):
    if pd.isna(value):
        return np.nan
    return (
        str(value)
        .replace("$", "")
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )


def clean_percent(value):
    if pd.isna(value):
        return np.nan
    return str(value).replace("%", "").replace(",", "").strip()

def clean_store(value):
    """
    Creates a consistent store key across all uploaded files.
    Handles uppercase/lowercase differences and extra spaces.
    Example:
    '6140: EDGEWOOD MD' and '6140: Edgewood MD' become the same key.
    """
    if pd.isna(value):
        return np.nan

    value = str(value).strip()
    value = " ".join(value.split())
    return value.upper()

def to_number(series):
    return pd.to_numeric(series, errors="coerce")


@st.cache_data
def load_labor_efficiency_data():
    main = pd.read_csv(DATA_DIR / "Main_Table_Cleaned_For_PowerBI1.csv")
    labor = pd.read_csv(DATA_DIR / "Labor Productivity-Range _ D3R24A2_ Amro Osman (68) 4_1_2025-4_1_2026.csv")
    perf = pd.read_csv(DATA_DIR / "Performance Overview-Range _ D3R24A2_ Amro Osman (68) 4_1_2025-4_1_2026.csv")
    sched = pd.read_csv(DATA_DIR / "Forecast and Sched Analysis-Range _ D3R24A2_ Amro Osman (68) 4_1_2025-4_1_2026.csv")

    # Keep original store name for display, but create a clean merge key
    main["Store Display"] = main["Store"].astype(str).str.strip()

    for df in [main, labor, perf, sched]:
        df["Store Key"] = df["Store"].apply(clean_store)

    # Main KPI table cleanup
    percent_cols = [
        "Comp Sales",
        "Comp Traffic",
        "YoY Off-Prem Sales Growth",
        "Missing & Incorrect %",
        "Ignite % Complete",
    ]

    for col in percent_cols:
        if col in main.columns:
            main[col] = to_number(main[col].apply(clean_percent))

    money_cols_main = ["AUV L12M", "Weekly AUV L12M"]
    for col in money_cols_main:
        if col in main.columns:
            main[col] = to_number(main[col].apply(clean_money))

    # Labor productivity cleanup
    labor_money_cols = [
        "Net Sales",
        "Total Labor Avg Wage",
        "Sales/Primary Hr",
        "Sales/Host Hr",
        "Sales/Server Hr",
        "Sales/Cook Hr",
        "Sales/Srv Assit Hr",
    ]

    for col in labor_money_cols:
        if col in labor.columns:
            labor[col] = to_number(labor[col].apply(clean_money))

    labor_numeric_cols = [
        "Guests",
        "Primary Hours",
        "Guests/ Primary Hr",
        "Host  Hours",
        "Guests/Host Hr",
        "Server  Hours",
        "Guests / Server Hr",
        "Cook Hours",
        "Guests / Cook Hr",
        "Srv Asst Hours",
        "Guests / Srv Asst Hrs",
    ]

    for col in labor_numeric_cols:
        if col in labor.columns:
            labor[col] = to_number(labor[col])

    # Performance overview cleanup
    perf_money_cols = [
        "Primary $",
        "Primary Std $",
        "Variance $",
        "Hrly Mgt $",
        "Training $",
        "Other $",
        "Total Labor $",
        "Overtime $",
    ]

    for col in perf_money_cols:
        if col in perf.columns:
            perf[col] = to_number(perf[col].apply(clean_money))

    perf_percent_cols = [
        "Actual %",
        "Standard %",
        "Variance %",
        "Hrly Mgmt %",
        "Training %",
        "Other %",
        "Total Labor %",
        "Overtime %",
    ]

    for col in perf_percent_cols:
        if col in perf.columns:
            perf[col] = to_number(perf[col].apply(clean_percent))

    # Schedule cleanup
    sched_numeric_cols = [
        "Projected Guests",
        "MGRForecastAdjustmentImpact",
        "Manager Adjusted Projected Guests",
        "MGRAdjustedGuestCountVariance",
        "Total Guest Count",
        "Scheduled Cook Hours",
        "Cook Variance Hours",
        "Scheduled Server Hours",
        "Server Variance Hours",
        "Scheduled Service Assistant Hours",
        "Srv Assist Variance Hours",
        "Scheduled Host Hours",
        "Host Variance Hours",
        "Expediter Variance Hours",
        "ToGo Variance Hours",
        "Guest % vs PY2",
    ]

    for col in sched_numeric_cols:
        if col in sched.columns:
            sched[col] = to_number(sched[col])

    # Merge all data
    df = (
    main.merge(labor, on="Store Key", how="left", suffixes=("", "_labor"))
    .merge(perf, on="Store Key", how="left", suffixes=("", "_perf"))
    .merge(sched, on="Store Key", how="left", suffixes=("", "_sched"))
)

    # Use original main table store name for display
    df["Store"] = df["Store Display"]

    # Labor metrics
    df["Sales per Labor Dollar"] = df["Net Sales"] / df["Total Labor $"]
    df["Guests per Labor Hour"] = df["Guests"] / df["Primary Hours"]
    df["Bubble Net Sales"] = pd.to_numeric(df["Net Sales"], errors="coerce")

    if df["Bubble Net Sales"].notna().any():
        df["Bubble Net Sales"] = df["Bubble Net Sales"].fillna(df["Bubble Net Sales"].median())
    else:
        df["Bubble Net Sales"] = 1

    df["Bubble Net Sales"] = df["Bubble Net Sales"].clip(lower=1)


    # Plotly cannot use NaN values for bubble size.
    # Safe bubble size for Total Labor $ schedule scatter.
    df["Bubble Total Labor $"] = pd.to_numeric(df["Total Labor $"], errors="coerce")

    if df["Bubble Total Labor $"].notna().any():
        df["Bubble Total Labor $"] = df["Bubble Total Labor $"].fillna(df["Bubble Total Labor $"].median())
    else:
        df["Bubble Total Labor $"] = 1

    df["Bubble Total Labor $"] = df["Bubble Total Labor $"].clip(lower=1)

    df["Bubble Net Sales"] = pd.to_numeric(df["Net Sales"], errors="coerce")

    if df["Bubble Net Sales"].notna().any():
        df["Bubble Net Sales"] = df["Bubble Net Sales"].fillna(df["Bubble Net Sales"].median())
    else:
        df["Bubble Net Sales"] = 1

    df["Bubble Net Sales"] = df["Bubble Net Sales"].clip(lower=1)

    variance_cols = [
        "Cook Variance Hours",
        "Server Variance Hours",
        "Srv Assist Variance Hours",
        "Host Variance Hours",
        "Expediter Variance Hours",
        "ToGo Variance Hours",
    ]

    existing_variance_cols = [col for col in variance_cols if col in df.columns]
    df["Total Schedule Variance Hours"] = df[existing_variance_cols].sum(axis=1)

    portfolio_avg_sales_labor = df["Sales per Labor Dollar"].mean()
    portfolio_avg_guests_labor = df["Guests per Labor Hour"].mean()

    df["Labor Efficiency Gap"] = df["Sales per Labor Dollar"] - portfolio_avg_sales_labor

    def labor_diagnostic(row):
        sales_labor = row["Sales per Labor Dollar"]
        guests_labor = row["Guests per Labor Hour"]
        comp_sales = row.get("Comp Sales", np.nan)

        if pd.isna(sales_labor) or pd.isna(guests_labor):
            return "Missing Labor Data"

        if sales_labor >= portfolio_avg_sales_labor and guests_labor >= portfolio_avg_guests_labor:
            return "Efficient Labor Model"

        if sales_labor < portfolio_avg_sales_labor and guests_labor < portfolio_avg_guests_labor:
            return "Labor Productivity Risk"

        if sales_labor < portfolio_avg_sales_labor and comp_sales < 0:
            return "Sales Decline + Labor Pressure"

        if sales_labor >= portfolio_avg_sales_labor and comp_sales < 0:
            return "Labor Efficient / Traffic Issue"

        return "Monitor"

    df["Labor Diagnostic"] = df.apply(labor_diagnostic, axis=1)

    return df

from scoring_model import REPORT_PERIOD_LABEL, KPI_CONFIG, score_main_file


APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "dennys_logo.png"


st.set_page_config(
    page_title="Denny's Restaurant Health Scorecard",
    page_icon="🍳",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main .block-container {padding-top: 1.5rem;}
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e7e7e7;
        padding: 12px;
        border-radius: 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,.04);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_uploaded_data(main_file, mi_file):
    return score_main_file(main_file, mi_file)


header_left, header_right = st.columns([1, 5])
with header_left:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=150)
with header_right:
    st.title("Denny's Restaurant Health Scorecard")
    st.caption(
        "Balanced model for identifying restaurants that need support — not just low sales or unusual volume."
    )

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=160)
    st.header("Upload Files")
    main_file = st.file_uploader(
        "Upload Main Table CSV",
        type=["csv"],
        help="The app automatically removes Total rows, blank rows, and filter-note rows.",
    )
    mi_file = st.file_uploader(
        "Optional: Upload Off-Prem M&I CSV",
        type=["csv"],
        help="Used as a detail/validation layer for Missing & Incorrect off-premise orders.",
    )

    st.divider()
    st.header("Model Notes")
    st.write(f"**Period:** {REPORT_PERIOD_LABEL}")
    st.write("**Quintile 1:** strongest")
    st.write("**Quintile 5:** highest support need")
    st.write("Raw AUV and Weekly AUV are context only, not scoring KPIs.")


if main_file is None:
    st.info("Upload the Main Table CSV to begin.")
    st.stop()


scored, mi, weights = load_uploaded_data(main_file, mi_file)

with st.sidebar:
    st.divider()
    st.header("Filters")

    owners = sorted(scored["Owner"].dropna().unique().tolist())
    selected_owners = st.multiselect("Owner / Franchise Group", owners)

    quintiles = sorted(scored["Revised Quintile"].dropna().unique().tolist())
    selected_quintiles = st.multiselect("Revised Quintile", quintiles)

    categories = sorted(scored["Support Category"].dropna().unique().tolist())
    selected_categories = st.multiselect("Support Category", categories)


filtered = scored.copy()
if selected_owners:
    filtered = filtered[filtered["Owner"].isin(selected_owners)]
if selected_quintiles:
    filtered = filtered[filtered["Revised Quintile"].isin(selected_quintiles)]
if selected_categories:
    filtered = filtered[filtered["Support Category"].isin(selected_categories)]


tab_overview, tab_rankings, tab_drill, tab_validation, tab_weights, tab_method, tab_labor = st.tabs(
    [
        "Executive Overview",
        "Rankings",
        "Restaurant Drill-Down",
        "Validation Flags",
        "KPI Weights",
        "Methodology",
        "Labor Efficiency",
    ]
)


with tab_overview:
    st.subheader("Executive Overview")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Restaurants Scored", f"{len(filtered):,}")
    c2.metric("Avg Health Score", f"{filtered['Restaurant Health Score'].mean():.1f}")
    c3.metric(
        "Priority / Support",
        f"{filtered['Support Category'].isin(['Priority Intervention', 'Support Needed']).sum():,}",
    )
    c4.metric("False Positive Review", f"{filtered['Potential False Positive'].sum():,}")
    c5.metric("False Negative Review", f"{filtered['Potential False Negative'].sum():,}")

    st.markdown(
        """
        The revised model balances **sales momentum, guest experience, operational execution,
        complaints, training, RRA results, off-premise accuracy, and operating readiness**.
        """
    )

    left, right = st.columns(2)

    with left:
        q_counts = (
            filtered["Revised Quintile"]
            .value_counts()
            .rename_axis("Revised Quintile")
            .reset_index(name="Restaurant Count")
            .sort_values("Revised Quintile")
        )
        fig = px.bar(
            q_counts,
            x="Revised Quintile",
            y="Restaurant Count",
            text="Restaurant Count",
            title="Restaurant Count by Revised Quintile",
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        cat_counts = (
            filtered["Support Category"]
            .value_counts()
            .rename_axis("Support Category")
            .reset_index(name="Restaurant Count")
        )
        fig = px.bar(
            cat_counts,
            x="Restaurant Count",
            y="Support Category",
            orientation="h",
            text="Restaurant Count",
            title="Support Category Distribution",
        )
        st.plotly_chart(fig, width="stretch")

    st.subheader("Bottom 15 Restaurants by Revised Score")
    cols = [
        "Owner",
        "Restaurant Name",
        "Restaurant Health Score",
        "Revised Rank",
        "Revised Quintile",
        "Overall Quintile",
        "Support Category",
        "Comp Sales",
        "Comp Traffic",
        "BBI Overall L90D",
        "Google Rating L90D",
        "Missing & Incorrect %",
        "Complaint/10k Guest L12M",
        "Latest RRA Score",
        "Ignite % Complete",
    ]
    st.dataframe(
        filtered.sort_values("Restaurant Health Score", ascending=True)[cols].head(15),
        width="stretch",
        hide_index=True,
    )

with tab_rankings:
    st.subheader("Restaurant Rankings")

    search = st.text_input("Search restaurant, unit, owner, city, or state")
    ranking_df = filtered.copy()

    if search:
        mask = (
            ranking_df["Restaurant Name"].str.contains(search, case=False, na=False)
            | ranking_df["Owner"].str.contains(search, case=False, na=False)
            | ranking_df["Unit"].astype(str).str.contains(search, case=False, na=False)
        )
        ranking_df = ranking_df[mask]

    display_cols = [
        "Revised Rank",
        "Revised Quintile",
        "Restaurant Health Score",
        "Overall Rank",
        "Overall Quintile",
        "Owner",
        "Restaurant Name",
        "Support Category",
        "AUV L12M",
        "Weekly AUV L12M",
        "Comp Sales",
        "Comp Traffic",
        "YoY Off-Prem Sales Growth",
        "Missing & Incorrect %",
        "Google Rating L90D",
        "BBI Overall L90D",
        "Complaint/10k Guest L12M",
        "Latest RRA Score",
        "Ignite % Complete",
        "Average Daily Hours",
    ]

    st.dataframe(
        ranking_df.sort_values("Revised Rank")[display_cols],
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "Download scored restaurant file",
        ranking_df.to_csv(index=False).encode("utf-8"),
        file_name="dennys_revised_restaurant_scores.csv",
        mime="text/csv",
    )


with tab_drill:
    st.subheader("Restaurant Drill-Down")

    restaurant_options = filtered.sort_values("Revised Rank")["Restaurant Name"].dropna().unique().tolist()

    if not restaurant_options:
        st.warning("No restaurants match the current filters.")
    else:
        selected_restaurant = st.selectbox("Select a restaurant", restaurant_options)
        row = filtered[filtered["Restaurant Name"] == selected_restaurant].iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Health Score", f"{row['Restaurant Health Score']:.1f}")
        c2.metric("Revised Rank", f"{int(row['Revised Rank'])}")
        c3.metric("Revised Quintile", f"{int(row['Revised Quintile'])}")
        c4.metric(
            "Current Overall Quintile",
            "" if pd.isna(row["Overall Quintile"]) else f"{int(row['Overall Quintile'])}",
        )
        c5.metric("Support Category", row["Support Category"])

        st.markdown(f"**Owner:** {row['Owner']}")
        st.markdown(f"**Restaurant:** {row['Restaurant Name']}")

        breakdown = pd.DataFrame(
            {
                "KPI": list(KPI_CONFIG.keys()),
                "Raw Value": [row.get(kpi, np.nan) for kpi in KPI_CONFIG.keys()],
                "Normalized Score": [row.get(f"{kpi} Score", np.nan) for kpi in KPI_CONFIG.keys()],
                "Weight": [KPI_CONFIG[kpi]["weight"] for kpi in KPI_CONFIG.keys()],
                "Category": [KPI_CONFIG[kpi]["category"] for kpi in KPI_CONFIG.keys()],
                "Direction": [KPI_CONFIG[kpi]["direction"] for kpi in KPI_CONFIG.keys()],
            }
        )
        breakdown["Weighted Points"] = breakdown["Normalized Score"] * breakdown["Weight"]

        left, right = st.columns([1.2, 1])

        with left:
            fig = px.bar(
                breakdown.sort_values("Normalized Score"),
                x="Normalized Score",
                y="KPI",
                orientation="h",
                title="Normalized KPI Scores",
                hover_data=["Raw Value", "Weight", "Category", "Direction"],
            )
            st.plotly_chart(fig, width="stretch")

        with right:
            st.dataframe(
                breakdown[
                    ["KPI", "Raw Value", "Normalized Score", "Weight", "Weighted Points", "Category", "Direction"]
                ],
                width="stretch",
                hide_index=True,
            )

        st.subheader("Diagnostic BBI Subcategories")
        bbi_cols = ["BBI Food L90D", "BBI Service L90D", "BBI Ambiance L90D", "BBI Value L90D"]
        st.dataframe(
            pd.DataFrame({"Metric": bbi_cols, "Value": [row.get(c, np.nan) for c in bbi_cols]}),
            hide_index=True,
            width="stretch",
        )

        if "Off-Prem M&I Detail %" in filtered.columns and pd.notna(row.get("Off-Prem M&I Detail %")):
            st.subheader("Off-Premise Missing & Incorrect Detail")
            mi_cols = [
                "Off-Prem Avg Weekly Sales",
                "DoorDash",
                "UberEats",
                "GrubHub",
                "Off-Prem M&I Detail %",
            ]
            available_cols = [c for c in mi_cols if c in filtered.columns]
            st.dataframe(
                pd.DataFrame({"Metric": available_cols, "Value": [row.get(c, np.nan) for c in available_cols]}),
                hide_index=True,
                width="stretch",
            )


with tab_validation:
    st.subheader("Validation Flags")

    st.markdown(
        """
        These flags help leadership review whether the current ranking is over- or under-stating restaurant risk.
        """
    )

    fp = filtered[filtered["Potential False Positive"]].copy()
    fn = filtered[filtered["Potential False Negative"]].copy()

    c1, c2 = st.columns(2)
    c1.metric("Potential False Positives", f"{len(fp):,}")
    c2.metric("Potential False Negatives", f"{len(fn):,}")

    st.markdown("### Potential False Positives")
    st.caption("Currently bottom quintile, but revised model suggests middle or stronger performance.")
    st.dataframe(
        fp.sort_values("Restaurant Health Score", ascending=False)[
            [
                "Owner",
                "Restaurant Name",
                "Restaurant Health Score",
                "Revised Quintile",
                "Overall Quintile",
                "Comp Sales",
                "Comp Traffic",
                "BBI Overall L90D",
                "Google Rating L90D",
                "Missing & Incorrect %",
                "Complaint/10k Guest L12M",
                "Ignite % Complete",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Potential False Negatives")
    st.caption("Current model places these in the middle/top, but revised model sees higher support need.")
    st.dataframe(
        fn.sort_values("Restaurant Health Score", ascending=True)[
            [
                "Owner",
                "Restaurant Name",
                "Restaurant Health Score",
                "Revised Quintile",
                "Overall Quintile",
                "Comp Sales",
                "Comp Traffic",
                "BBI Overall L90D",
                "Google Rating L90D",
                "Missing & Incorrect %",
                "Complaint/10k Guest L12M",
                "Latest RRA Score",
                "Ignite % Complete",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Current Overall Rank vs Revised Score")
    scatter_df = filtered.dropna(subset=["Overall Rank", "Restaurant Health Score"]).copy()
    if not scatter_df.empty:
        fig = px.scatter(
            scatter_df,
            x="Overall Rank",
            y="Restaurant Health Score",
            color="Revised Quintile",
            hover_data=["Restaurant Name", "Owner", "Overall Quintile", "Revised Quintile"],
            title="Current Overall Rank vs Revised Health Score",
        )
        st.plotly_chart(fig, width="stretch")


with tab_weights:
    st.subheader("KPI Weighting Recommendation")

    weights_display = weights.copy()
    weights_display["Weight"] = weights_display["Weight"].map(lambda x: f"{x:.0%}")
    st.dataframe(weights_display, width="stretch", hide_index=True)

    category_weights = (
        weights.assign(WeightPercent=weights["Weight"] * 100)
        .groupby("Category", as_index=False)["WeightPercent"]
        .sum()
        .sort_values("WeightPercent", ascending=False)
    )

    fig = px.bar(
        category_weights,
        x="Category",
        y="WeightPercent",
        text="WeightPercent",
        title="Weight by Category",
    )
    st.plotly_chart(fig, width="stretch")


with tab_method:
    st.subheader("Revised Scoring Methodology")

    st.markdown(
        f"""
        **Report period:** {REPORT_PERIOD_LABEL}

        **Core principle:** The model should identify restaurants that need support based on overall restaurant health,
        not simply low volume or unusual sales patterns.

        ### Cleaning logic
        - Remove rows where `Restaurant Name = Total`
        - Remove blank rows
        - Remove Power BI filter-note rows
        - Extract unit number from the beginning of the restaurant name
        - Convert currency, percent, and numeric text fields into true numeric values

        ### Normalization
        Every KPI is converted to a 0–100 score using 5th and 95th percentile caps.

        For positive KPIs, higher is better:

        `Score = (Value - P5) / (P95 - P5) * 100`

        For negative KPIs, lower is better:

        `Score = (P95 - Value) / (P95 - P5) * 100`

        Scores are capped between 0 and 100.

        ### Final score
        The final score is a weighted average of normalized KPI scores. If a restaurant is missing a KPI,
        the score is reweighted across the available KPIs so the restaurant is not unfairly penalized for missing data.

        ### Quintiles
        Restaurants are ranked by final health score:
        - Quintile 1 = strongest 20%
        - Quintile 5 = bottom 20%, highest support need

        ### Leadership explanation
        This model is not just ranking sales performance. It balances demand momentum, guest experience,
        off-premise execution, complaints, training completion, RRA results, and operating readiness.
        Raw AUV is excluded from the score and used only as context to reduce volume bias.
        """
    )

with tab_labor:
    st.header("Labor Efficiency vs Quintile")
    st.caption(
        "This page shows whether restaurant performance is being impacted by labor productivity, "
        "sales weakness, traffic softness, or scheduling variance."
    )

    df_labor = load_labor_efficiency_data()

    # Sidebar / page filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        owner_options = sorted(df_labor["Owner"].dropna().unique())
        selected_owners = st.multiselect(
            "Filter by Owner",
            owner_options,
            default=owner_options,
        )

    with col_filter2:
        quintile_options = sorted(df_labor["Overall Quintile"].dropna().unique())
        selected_quintiles = st.multiselect(
            "Filter by Overall Quintile",
            quintile_options,
            default=quintile_options,
        )

    with col_filter3:
        diagnostic_options = sorted(df_labor["Labor Diagnostic"].dropna().unique())
        selected_diagnostics = st.multiselect(
            "Filter by Labor Diagnostic",
            diagnostic_options,
            default=diagnostic_options,
        )

    filtered = df_labor[
        df_labor["Owner"].isin(selected_owners)
        & df_labor["Overall Quintile"].isin(selected_quintiles)
        & df_labor["Labor Diagnostic"].isin(selected_diagnostics)
    ].copy()
    # Keep only rows with enough data to plot
    plot_filtered = filtered.dropna(
        subset=[
            "Sales per Labor Dollar",
            "Comp Sales",
            "Bubble Net Sales",
        ]
    ).copy()

    if plot_filtered.empty:
        st.warning(
            "No valid labor efficiency records are available for the selected filters. "
            "Check that Store values match across the main KPI, labor productivity, and performance files."
        )
        st.stop()

    # KPI Cards
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    kpi1.metric(
        "Avg Sales / Labor $",
        f"${filtered['Sales per Labor Dollar'].mean():.2f}"
    )

    kpi2.metric(
        "Avg Guests / Labor Hr",
        f"{filtered['Guests per Labor Hour'].mean():.2f}"
    )

    kpi3.metric(
        "Avg Labor %",
        f"{filtered['Total Labor %'].mean():.1f}%"
    )

    kpi4.metric(
        "Avg Schedule Variance Hrs",
        f"{filtered['Total Schedule Variance Hours'].mean():,.0f}"
    )

    kpi5.metric(
        "Avg Quintile",
        f"{filtered['Overall Quintile'].mean():.2f}"
    )

    st.divider()

    # Main insight text
    avg_sales_labor = filtered["Sales per Labor Dollar"].mean()
    avg_guests_labor = filtered["Guests per Labor Hour"].mean()
    avg_labor_pct = filtered["Total Labor %"].mean()

    st.info(
        f"Labor efficiency view: selected stores average **${avg_sales_labor:.2f} Sales per Labor Dollar**, "
        f"**{avg_guests_labor:.2f} Guests per Labor Hour**, and **{avg_labor_pct:.1f}% Total Labor**. "
        "Stores with low labor efficiency and weak comp sales should be treated as operational priority locations. "
        "Stores with strong labor efficiency but weak sales may need traffic, reputation, or guest experience support."
    )

    # Visual 1: Sales per Labor Dollar vs Comp Sales
    st.subheader("Sales Performance vs Labor Efficiency")

    fig_scatter = px.scatter(
        plot_filtered,
        x="Sales per Labor Dollar",
        y="Comp Sales",
        size="Bubble Net Sales",
        color="Overall Quintile",
        hover_name="Store",
        hover_data=[
            "Owner",
            "Comp Traffic",
            "Total Labor %",
            "Guests per Labor Hour",
            "Total Schedule Variance Hours",
            "Labor Diagnostic",
            "Net Sales",
        ],
        title="Sales per Labor Dollar vs Comp Sales by Store",
    )

    fig_scatter.add_vline(
        x=plot_filtered["Sales per Labor Dollar"].mean(),
        line_dash="dash",
        annotation_text="Avg Sales/Labor $",
    )

    fig_scatter.add_hline(
        y=0,
        line_dash="dash",
        annotation_text="0% Comp Sales",
    )

    st.plotly_chart(fig_scatter, width="stretch")

    st.markdown(
        """
        **How to read this chart:**  
        - **Top right:** strong sales and strong labor efficiency  
        - **Top left:** sales are positive, but labor may be leaking  
        - **Bottom right:** labor is efficient, but traffic or sales are weak  
        - **Bottom left:** highest-risk group because both sales and labor efficiency are weak  
        """
    )

    st.divider()

    # Visual 2 and 3 side-by-side
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Sales Efficiency by Store")

        bar_data = filtered.sort_values("Sales per Labor Dollar", ascending=True)

        fig_bar = px.bar(
            bar_data,
            x="Sales per Labor Dollar",
            y="Store",
            color="Overall Quintile",
            orientation="h",
            hover_data=[
                "Owner",
                "Net Sales",
                "Total Labor $",
                "Total Labor %",
                "Guests per Labor Hour",
                "Labor Diagnostic",
            ],
            title="Sales per Labor Dollar by Store",
        )

        st.plotly_chart(fig_bar, width="stretch")

    with chart_col2:
        st.subheader("Schedule Variance vs Labor Efficiency")
        
        sched_plot = filtered.dropna(
            subset=[
                "Total Schedule Variance Hours",
                "Sales per Labor Dollar",
                "Bubble Total Labor $",
            ]
        ).copy()

        # Ensure Bubble Total Labor $ has no NaN values for Plotly size parameter
        if not sched_plot.empty:
            sched_plot["Bubble Total Labor $"] = sched_plot["Bubble Total Labor $"].fillna(
                sched_plot["Bubble Total Labor $"].median() if sched_plot["Bubble Total Labor $"].notna().any() else 1
            ).clip(lower=1)

        if sched_plot.empty:
            st.warning(
                "Schedule variance chart is not available for the selected filters because labor or schedule data is missing."
            )
        else:
            fig_sched = px.scatter(
                sched_plot,
                x="Total Schedule Variance Hours",
                y="Sales per Labor Dollar",
                size="Bubble Total Labor $",
                color="Overall Quintile",
                hover_name="Store",
                hover_data=[
                    "Owner",
                    "Cook Variance Hours",
                    "Server Variance Hours",
                    "Host Variance Hours",
                    "Guests per Labor Hour",
                    "Total Labor %",
                    "Total Labor $",
                    "Labor Diagnostic",
                ],
                title="Schedule Variance Hours vs Sales per Labor Dollar",
            )

            fig_sched.add_hline(
                y=sched_plot["Sales per Labor Dollar"].mean(),
                line_dash="dash",
                annotation_text="Avg Sales/Labor $",
            )

            fig_sched.add_vline(
                x=0,
                line_dash="dash",
                annotation_text="Zero Variance",
            )

            st.plotly_chart(fig_sched, width="stretch")

            st.divider()

    # Visual 4: Diagnostic table
    st.subheader("Store Labor Diagnostic Table")

    table_cols = [
        "Store",
        "Owner",
        "Overall Quintile",
        "Overall Rank",
        "Comp Sales",
        "Comp Traffic",
        "Net Sales",
        "Sales per Labor Dollar",
        "Guests per Labor Hour",
        "Total Labor %",
        "Total Schedule Variance Hours",
        "Labor Efficiency Gap",
        "Labor Diagnostic",
    ]

    table_cols = [col for col in table_cols if col in filtered.columns]

    diagnostic_table = filtered[table_cols].sort_values(
        ["Overall Quintile", "Sales per Labor Dollar"],
        ascending=[False, True],
    )

    st.dataframe(
        diagnostic_table,
        width="stretch",
        hide_index=True,
        column_config={
            "Net Sales": st.column_config.NumberColumn(
                "Net Sales",
                format="$%d",
            ),
            "Sales per Labor Dollar": st.column_config.NumberColumn(
                "Sales / Labor $",
                format="$%.2f",
            ),
            "Guests per Labor Hour": st.column_config.NumberColumn(
                "Guests / Labor Hr",
                format="%.2f",
            ),
            "Total Labor %": st.column_config.NumberColumn(
                "Total Labor %",
                format="%.1f%%",
            ),
            "Comp Sales": st.column_config.NumberColumn(
                "Comp Sales %",
                format="%.2f%%",
            ),
            "Comp Traffic": st.column_config.NumberColumn(
                "Comp Traffic %",
                format="%.2f%%",
            ),
            "Total Schedule Variance Hours": st.column_config.NumberColumn(
                "Schedule Variance Hrs",
                format="%.0f",
            ),
            "Labor Efficiency Gap": st.column_config.NumberColumn(
                "Labor Efficiency Gap",
                format="$%.2f",
            ),
        },
    )

    st.divider()

    # Bottom insight
    st.subheader("Recommended Use")

    st.markdown(
        """
        This tab should be used as a **diagnostic layer**, not just another ranking page.

        The main question it answers is:

        **Is the store underperforming because of weak sales, weak traffic, poor labor productivity, scheduling variance, or a combination?**

        Recommended coaching logic:

        - **Low Sales per Labor Dollar + Low Guests per Labor Hour:** review deployment, scheduling discipline, and manager forecasting.
        - **Strong labor efficiency + weak comp sales:** focus on traffic recovery, BBI, Google rating, local store marketing, and guest experience.
        - **High schedule variance + weak labor efficiency:** review forecast accuracy and schedule writing by daypart.
        - **High sales + weak labor efficiency:** sales are present, but labor control may be leaking profit.
        """
    )