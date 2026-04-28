from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

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


tab_overview, tab_rankings, tab_drill, tab_validation, tab_weights, tab_method = st.tabs(
    [
        "Executive Overview",
        "Rankings",
        "Restaurant Drill-Down",
        "Validation Flags",
        "KPI Weights",
        "Methodology",
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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

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
        use_container_width=True,
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
        use_container_width=True,
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
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.dataframe(
                breakdown[
                    ["KPI", "Raw Value", "Normalized Score", "Weight", "Weighted Points", "Category", "Direction"]
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Diagnostic BBI Subcategories")
        bbi_cols = ["BBI Food L90D", "BBI Service L90D", "BBI Ambiance L90D", "BBI Value L90D"]
        st.dataframe(
            pd.DataFrame({"Metric": bbi_cols, "Value": [row.get(c, np.nan) for c in bbi_cols]}),
            hide_index=True,
            use_container_width=True,
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
                use_container_width=True,
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
        use_container_width=True,
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
        use_container_width=True,
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
        st.plotly_chart(fig, use_container_width=True)


with tab_weights:
    st.subheader("KPI Weighting Recommendation")

    weights_display = weights.copy()
    weights_display["Weight"] = weights_display["Weight"].map(lambda x: f"{x:.0%}")
    st.dataframe(weights_display, use_container_width=True, hide_index=True)

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
    st.plotly_chart(fig, use_container_width=True)


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
