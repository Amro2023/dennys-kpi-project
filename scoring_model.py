from __future__ import annotations

import re
from typing import Optional, Tuple

import numpy as np
import pandas as pd


REPORT_AS_OF_DATE = "2026-04-01"
REPORT_PERIOD_LABEL = "Rolling 12 Months as of 4/1/2026"


KPI_CONFIG = {
    "Comp Traffic": {
        "weight": 0.15,
        "direction": "positive",
        "category": "Sales / Demand",
        "type": "Lagging",
        "include": True,
        "explanation": "Measures guest traffic momentum. Important, but not allowed to dominate the model.",
    },
    "Comp Sales": {
        "weight": 0.10,
        "direction": "positive",
        "category": "Sales / Demand",
        "type": "Lagging",
        "include": True,
        "explanation": "Measures sales momentum. Lower weight than traffic because price/mix can influence sales.",
    },
    "YoY Off-Prem Sales Growth": {
        "weight": 0.05,
        "direction": "positive",
        "category": "Sales / Demand",
        "type": "Lagging",
        "include": True,
        "explanation": "Useful but volatile. Kept low because off-prem performance can be affected by market/channel mix.",
    },
    "BBI Overall L90D": {
        "weight": 0.15,
        "direction": "positive",
        "category": "Guest Experience",
        "type": "Lagging",
        "include": True,
        "explanation": "Primary guest sentiment KPI from the last 90 days.",
    },
    "Google Rating L90D": {
        "weight": 0.10,
        "direction": "positive",
        "category": "Guest Experience",
        "type": "Lagging",
        "include": True,
        "explanation": "External reputation signal from the last 90 days.",
    },
    "Missing & Incorrect %": {
        "weight": 0.10,
        "direction": "negative",
        "category": "Operational Execution",
        "type": "Leading / Execution",
        "include": True,
        "explanation": "Off-premise missing and incorrect order rate. Lower is better.",
    },
    "Complaint/10k Guest L12M": {
        "weight": 0.10,
        "direction": "negative",
        "category": "Operational Execution",
        "type": "Lagging",
        "include": True,
        "explanation": "Guest complaints normalized by guest count. Lower is better.",
    },
    "Latest RRA Score": {
        "weight": 0.10,
        "direction": "negative",
        "category": "Operational Execution",
        "type": "Leading / Execution",
        "include": True,
        "explanation": "Sanitation / health inspection indicator. Lower is better because a lower RRA risk/issue score means stronger sanitation performance.",
    },
    "Ignite % Complete": {
        "weight": 0.10,
        "direction": "positive",
        "category": "Training / Readiness",
        "type": "Leading",
        "include": True,
        "explanation": "Training completion is a controllable input that supports execution.",
    },
    "Average Daily Hours": {
        "weight": 0.05,
        "direction": "positive",
        "category": "Training / Readiness",
        "type": "Leading / Availability",
        "include": True,
        "explanation": "Reduced hours can signal staffing or operating readiness issues. Kept low to avoid over-penalizing special situations.",
    },
}


NUMERIC_COLUMNS = [
    "Restaurant Count",
    "Weighted Quintile",
    "Overall Rank",
    "Overall Quintile",
    "AUV L12M",
    "Weekly AUV L12M",
    "Comp Sales",
    "Comp Traffic",
    "YoY Off-Prem Sales Growth",
    "Missing & Incorrect %",
    "Google Rating L90D",
    "BBI Overall L90D",
    "BBI Food L90D",
    "BBI Service L90D",
    "BBI Ambiance L90D",
    "BBI Value L90D",
    "Complaint/10k Guest L12M",
    "Latest RRA Score",
    "Ignite % Complete",
    "Diff Certified Managers",
    "Average Daily Hours",
]


def clean_numeric_value(value):
    if pd.isna(value):
        return np.nan

    if isinstance(value, (int, float, np.number)):
        return float(value)

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return np.nan

    text = (
        text.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )

    try:
        return float(text)
    except ValueError:
        return np.nan


def extract_unit(restaurant_name: str) -> Optional[str]:
    if pd.isna(restaurant_name):
        return None
    match = re.match(r"^\s*(\d+)", str(restaurant_name))
    return match.group(1) if match else None


def load_main_table(file) -> pd.DataFrame:
    df = pd.read_csv(file, encoding="utf-8-sig")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    df = df[df["Restaurant Name"].notna()].copy()
    df["Restaurant Name"] = df["Restaurant Name"].astype(str).str.strip()
    df["Owner"] = df["Owner"].astype(str).str.strip()

    is_total = df["Restaurant Name"].str.lower().eq("total")
    is_blank = df["Restaurant Name"].eq("")
    is_filter_note = df["Owner"].str.lower().str.startswith("applied filters", na=False)

    df = df[~is_total & ~is_blank & ~is_filter_note].copy()
    df["Unit"] = df["Restaurant Name"].apply(extract_unit)

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_value)

    df = df[df["Unit"].notna()].copy()
    return df.reset_index(drop=True)


def load_mi_detail(file) -> pd.DataFrame:
    df = pd.read_csv(file, encoding="utf-8-sig")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    df = df[df["Restaurant Name"].notna()].copy()
    df["Restaurant Name"] = df["Restaurant Name"].astype(str).str.strip()
    df = df[df["Restaurant Name"].str.lower() != "total"].copy()
    df["Unit"] = df["Restaurant Name"].apply(extract_unit)
    df = df[df["Unit"].notna()].copy()

    for col in [
        "Average Weekly Sales",
        "Brand",
        "DoorDash",
        "UberEats",
        "GrubHub",
        "Missing & Incorrect %",
        "_RLS Sum Weekly Sales | Rolling 1W 13 Week Window",
        "_RLS % DoorDash Delivery Error | Rolling 1W 13 Week Window",
    ]:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_value)

    return df.reset_index(drop=True)


def normalize_series(series: pd.Series, direction: str) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    p5 = s.quantile(0.05)
    p95 = s.quantile(0.95)

    if pd.isna(p5) or pd.isna(p95) or p95 == p5:
        return pd.Series(np.where(s.notna(), 50, np.nan), index=s.index)

    if direction == "positive":
        score = ((s - p5) / (p95 - p5)) * 100
    elif direction == "negative":
        score = ((p95 - s) / (p95 - p5)) * 100
    else:
        raise ValueError(f"Unknown direction: {direction}")

    return score.clip(0, 100)


def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    scored = df.copy()
    included_kpis = [k for k, cfg in KPI_CONFIG.items() if cfg["include"]]

    for kpi in included_kpis:
        cfg = KPI_CONFIG[kpi]
        score_col = f"{kpi} Score"

        if kpi not in scored.columns:
            scored[score_col] = np.nan
            continue

        scored[score_col] = normalize_series(scored[kpi], cfg["direction"])

    weighted_sum = pd.Series(0.0, index=scored.index)
    available_weight = pd.Series(0.0, index=scored.index)

    for kpi in included_kpis:
        score_col = f"{kpi} Score"
        weight = KPI_CONFIG[kpi]["weight"]

        weighted_sum = weighted_sum + scored[score_col].fillna(0) * weight
        available_weight = available_weight + scored[score_col].notna().astype(float) * weight

    scored["Available Weight"] = available_weight
    scored["Restaurant Health Score"] = np.where(
        available_weight > 0,
        weighted_sum / available_weight,
        np.nan,
    )
    scored["Restaurant Health Score"] = scored["Restaurant Health Score"].round(2)

    scored["Revised Rank"] = scored["Restaurant Health Score"].rank(
        ascending=False,
        method="dense",
    )

    n = scored["Restaurant Health Score"].notna().sum()
    pct_rank = scored["Revised Rank"].astype(float) / float(n)

    scored["Revised Quintile"] = np.select(
        [
            pct_rank <= 0.20,
            pct_rank <= 0.40,
            pct_rank <= 0.60,
            pct_rank <= 0.80,
            pct_rank <= 1.00,
        ],
        [1, 2, 3, 4, 5],
        default=np.nan,
    )

    scored["Revised Rank"] = scored["Revised Rank"].astype("Int64")
    scored["Revised Quintile"] = scored["Revised Quintile"].astype("Int64")

    scored["Sales Pressure Flag"] = (
        (scored["Comp Sales"] < scored["Comp Sales"].quantile(0.25))
        | (scored["Comp Traffic"] < scored["Comp Traffic"].quantile(0.25))
    )

    scored["Execution Concern Flag"] = (
        (scored["Missing & Incorrect %"] > scored["Missing & Incorrect %"].quantile(0.75))
        | (scored["Complaint/10k Guest L12M"] > scored["Complaint/10k Guest L12M"].quantile(0.75))
        | (scored["Latest RRA Score"] > scored["Latest RRA Score"].quantile(0.75))
        | (scored["Ignite % Complete"] < scored["Ignite % Complete"].quantile(0.25))
    )

    scored["Guest Concern Flag"] = (
        (scored["BBI Overall L90D"] < scored["BBI Overall L90D"].quantile(0.25))
        | (scored["Google Rating L90D"] < scored["Google Rating L90D"].quantile(0.25))
    )

    scored["Potential False Positive"] = (
        (scored["Overall Quintile"] == 5)
        & (scored["Revised Quintile"] <= 3)
    )

    scored["Potential False Negative"] = (
        (scored["Overall Quintile"] <= 3)
        & (scored["Revised Quintile"] >= 4)
    )

    priority_intervention = (
        scored["Revised Quintile"].eq(5)
        & scored["Execution Concern Flag"]
        & scored["Guest Concern Flag"]
    ).fillna(False).to_numpy(dtype=bool)

    support_needed = scored["Revised Quintile"].eq(5).fillna(False).to_numpy(dtype=bool)
    watchlist = scored["Revised Quintile"].eq(4).fillna(False).to_numpy(dtype=bool)
    stable_monitor = scored["Revised Quintile"].eq(3).fillna(False).to_numpy(dtype=bool)
    healthy = scored["Revised Quintile"].le(2).fillna(False).to_numpy(dtype=bool)

    scored["Support Category"] = np.select(
        [
            priority_intervention,
            support_needed,
            watchlist,
            stable_monitor,
            healthy,
        ],
        [
            "Priority Intervention",
            "Support Needed",
            "Watchlist",
            "Stable / Monitor",
            "Healthy",
        ],
        default="Review",
    )

    return scored


def kpi_weighting_table() -> pd.DataFrame:
    rows = []
    for kpi, cfg in KPI_CONFIG.items():
        rows.append(
            {
                "KPI": kpi,
                "Include": "Yes" if cfg["include"] else "No",
                "Weight": cfg["weight"],
                "Direction": cfg["direction"].title(),
                "Type": cfg["type"],
                "Category": cfg["category"],
                "Explanation": cfg["explanation"],
            }
        )
    return pd.DataFrame(rows)


def score_main_file(main_file, mi_file=None) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame]:
    main = load_main_table(main_file)
    scored = calculate_scores(main)

    mi = None
    if mi_file is not None:
        mi = load_mi_detail(mi_file)

        mi_cols = [
            "Unit",
            "Average Weekly Sales",
            "DoorDash",
            "UberEats",
            "GrubHub",
            "Missing & Incorrect %",
        ]
        available_mi_cols = [c for c in mi_cols if c in mi.columns]
        mi_small = mi[available_mi_cols].copy()
        mi_small = mi_small.rename(
            columns={
                "Average Weekly Sales": "Off-Prem Avg Weekly Sales",
                "Missing & Incorrect %": "Off-Prem M&I Detail %",
            }
        )

        scored = scored.merge(mi_small, on="Unit", how="left")

    weights = kpi_weighting_table()
    return scored, mi, weights
