import os
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# Optional Gemini integration
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ESGenius AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #f8fafc;
    }

    .hero {
        padding: 2rem 2.2rem;
        border-radius: 18px;
        margin-bottom: 1.5rem;
        background: linear-gradient(
            135deg,
            #0f766e 0%,
            #166534 100%
        );
        color: white;
    }

    .hero h1 {
        font-size: 2.7rem;
        margin-bottom: 0.3rem;
    }

    .hero p {
        font-size: 1.1rem;
        margin-bottom: 0;
        opacity: 0.95;
    }

    .risk-card {
        padding: 0.9rem 1rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        background: white;
        margin-bottom: 0.7rem;
    }

    .small-muted {
        color: #64748b;
        font-size: 0.9rem;
    }

    .insight-card {
        padding: 1rem 1.2rem;
        border-radius: 12px;
        background: white;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.8rem;
    }

    .section-label {
        color: #0f766e;
        font-weight: 700;
        letter-spacing: 0.03em;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "df" not in st.session_state:
    st.session_state.df = None

if "filename" not in st.session_state:
    st.session_state.filename = None

if "ai_insights" not in st.session_state:
    st.session_state.ai_insights = None

if "report" not in st.session_state:
    st.session_state.report = None


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_columns(df):
    """Clean column names while preserving readability."""
    df = df.copy()

    cleaned = []

    for col in df.columns:
        name = str(col).strip()
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^\w\-]", "", name)
        cleaned.append(name.lower())

    df.columns = cleaned

    return df


def numeric_columns(df):
    """Return numeric columns."""
    return list(
        df.select_dtypes(include="number").columns
    )


def find_column(df, keywords):
    """Find the first column whose name contains one of the keywords."""

    for col in df.columns:

        col_lower = str(col).lower()

        for keyword in keywords:

            if keyword.lower() in col_lower:
                return col

    return None


def safe_mean(series):
    """Calculate a safe numeric mean."""

    values = pd.to_numeric(
        series,
        errors="coerce"
    ).dropna()

    if values.empty:
        return None

    return float(values.mean())


def clamp(value, minimum=0, maximum=100):
    return max(
        minimum,
        min(maximum, value)
    )


# ============================================================
# ESG SCORING ENGINE
# ============================================================

def calculate_esg_score(df):
    """
    Estimate ESG pillar scores from recognizable indicators.

    This is a transparent prototype scoring model.
    It is not a certified ESG methodology.
    """

    if df is None or df.empty:
        return {}, None

    environment_score = 70.0
    social_score = 70.0
    governance_score = 70.0

    # ---------------- ENVIRONMENT ----------------

    emissions_col = find_column(
        df,
        [
            "emission",
            "carbon",
            "co2",
            "ghg",
        ]
    )

    renewable_col = find_column(
        df,
        [
            "renewable",
            "clean_energy",
        ]
    )

    waste_col = find_column(
        df,
        [
            "waste",
            "recycling",
        ]
    )

    if emissions_col:
        avg = safe_mean(df[emissions_col])

        if avg is not None:

            # Lower emissions generally indicate better performance.
            if avg <= 500:
                environment_score += 20
            elif avg <= 1000:
                environment_score += 10
            elif avg >= 3000:
                environment_score -= 20
            elif avg >= 1500:
                environment_score -= 10

    if renewable_col:
        avg = safe_mean(df[renewable_col])

        if avg is not None:

            # Handle either 0-1 or 0-100 formats.
            if avg <= 1:
                avg *= 100

            environment_score += (
                (clamp(avg) - 50) * 0.30
            )

    if waste_col:
        avg = safe_mean(df[waste_col])

        if avg is not None:

            if avg < 100:
                environment_score += 5
            elif avg > 1000:
                environment_score -= 8

    # ---------------- SOCIAL ----------------

    diversity_col = find_column(
        df,
        [
            "diversity",
            "female",
            "inclusion",
        ]
    )

    safety_col = find_column(
        df,
        [
            "safety",
            "incident",
            "injury",
        ]
    )

    employee_col = find_column(
        df,
        [
            "employee",
            "workforce",
            "staff",
        ]
    )

    if diversity_col:

        avg = safe_mean(df[diversity_col])

        if avg is not None:

            if avg <= 1:
                avg *= 100

            social_score += (
                (clamp(avg) - 50) * 0.35
            )

    if safety_col:

        avg = safe_mean(df[safety_col])

        if avg is not None:

            # Incident counts are treated as a risk signal.
            if avg <= 2:
                social_score += 12
            elif avg <= 5:
                social_score += 5
            elif avg >= 20:
                social_score -= 15
            elif avg >= 10:
                social_score -= 8

    if employee_col:

        social_score += 3

    # ---------------- GOVERNANCE ----------------

    governance_col = find_column(
        df,
        [
            "governance",
            "compliance",
            "audit",
            "ethics",
            "risk",
        ]
    )

    if governance_col:

        avg = safe_mean(df[governance_col])

        if avg is not None:

            if avg <= 1:
                avg *= 100

            governance_score += (
                (clamp(avg) - 50) * 0.30
            )

    scores = {
        "Environment": clamp(environment_score),
        "Social": clamp(social_score),
        "Governance": clamp(governance_score),
    }

    overall = sum(scores.values()) / len(scores)

    return scores, overall


# ============================================================
# RISK DETECTION
# ============================================================

def generate_risks(df):

    risks = []

    if df is None or df.empty:
        return risks

    # --------------------------------------------------------
    # DATA QUALITY RISK
    # --------------------------------------------------------

    missing = int(
        df.isna().sum().sum()
    )

    total_cells = (
        len(df) * len(df.columns)
    )

    missing_percentage = (
        missing / total_cells * 100
        if total_cells
        else 0
    )

    if missing_percentage >= 20:

        risks.append(
            (
                "High",
                "🔴",
                "Data completeness",
                f"{missing_percentage:.1f}% of dataset cells "
                "are missing."
            )
        )

    elif missing_percentage >= 5:

        risks.append(
            (
                "Medium",
                "🟠",
                "Data completeness",
                f"{missing_percentage:.1f}% of dataset cells "
                "are missing."
            )
        )

    else:

        risks.append(
            (
                "Low",
                "🟢",
                "Data completeness",
                "The uploaded dataset has relatively low "
                "missing-data exposure."
            )
        )

    # --------------------------------------------------------
    # EMISSIONS
    # --------------------------------------------------------

    emissions_col = find_column(
        df,
        [
            "emission",
            "carbon",
            "co2",
            "ghg",
        ]
    )

    if emissions_col:

        avg = safe_mean(
            df[emissions_col]
        )

        if avg is not None:

            if avg >= 3000:

                risks.append(
                    (
                        "High",
                        "🔴",
                        "Carbon emissions",
                        f"Average reported value in "
                        f"{emissions_col} is {avg:.1f}, "
                        "indicating a potential emissions priority."
                    )
                )

            elif avg >= 1500:

                risks.append(
                    (
                        "Medium",
                        "🟠",
                        "Carbon emissions",
                        f"Average reported value in "
                        f"{emissions_col} is {avg:.1f}. "
                        "Further reduction opportunities should be assessed."
                    )
                )

            else:

                risks.append(
                    (
                        "Low",
                        "🟢",
                        "Carbon emissions",
                        "No immediate high-severity emissions "
                        "signal was detected."
                    )
                )

    # --------------------------------------------------------
    # RENEWABLE ENERGY
    # --------------------------------------------------------

    renewable_col = find_column(
        df,
        [
            "renewable",
            "clean_energy",
        ]
    )

    if renewable_col:

        avg = safe_mean(
            df[renewable_col]
        )

        if avg is not None:

            if avg <= 1:
                avg *= 100

            if avg < 30:

                risks.append(
                    (
                        "High",
                        "🔴",
                        "Renewable energy adoption",
                        f"Renewable-energy share is approximately "
                        f"{avg:.1f}%."
                    )
                )

            elif avg < 50:

                risks.append(
                    (
                        "Medium",
                        "🟠",
                        "Renewable energy adoption",
                        f"Renewable-energy share is approximately "
                        f"{avg:.1f}%."
                    )
                )

            else:

                risks.append(
                    (
                        "Low",
                        "🟢",
                        "Renewable energy adoption",
                        f"Renewable-energy share is approximately "
                        f"{avg:.1f}%."
                    )
                )

    # --------------------------------------------------------
    # DEFAULT GOVERNANCE CHECK
    # --------------------------------------------------------

    governance_col = find_column(
        df,
        [
            "governance",
            "compliance",
            "audit",
            "ethics",
        ]
    )

    if governance_col is None:

        risks.append(
            (
                "Medium",
                "🟠",
                "Governance visibility",
                "No clearly recognizable governance indicator "
                "was detected in the uploaded dataset."
            )
        )

    # Keep dashboard concise.
    return risks[:6]


# ============================================================
# TREND ANALYSIS
# ============================================================

def create_trend_chart(df):

    if df is None or df.empty:
        return None

    year_col = find_column(
        df,
        [
            "year",
            "date",
            "period",
        ]
    )

    numeric = numeric_columns(df)

    if year_col is None or not numeric:
        return None

    selected = numeric[:4]

    trend_df = df.copy()

    try:
        trend_df[year_col] = pd.to_numeric(
            trend_df[year_col],
            errors="coerce"
        )

        trend_df = trend_df.dropna(
            subset=[year_col]
        )

        if trend_df.empty:
            return None

        chart_df = trend_df[
            [year_col] + selected
        ].copy()

        chart_df = chart_df.sort_values(
            year_col
        )

        long_df = chart_df.melt(
            id_vars=[year_col],
            var_name="Indicator",
            value_name="Value"
        )

        fig = px.line(
            long_df,
            x=year_col,
            y="Value",
            color="Indicator",
            markers=True,
            title="Indicator Trends Over Time",
        )

        fig.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20
            )
        )

        return fig

    except Exception:
        return None


# ============================================================
# GEMINI AI
# ============================================================

def generate_ai_insights(df, company):
    """
    Generate AI-powered ESG analysis using Google Gemini.

    The function automatically discovers an available Gemini
    model that supports text generation, making the application
    more resilient to model availability changes.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return (
            None,
            "GEMINI_API_KEY is not configured. "
            "Add your Gemini API key to the .env file."
        )

    if api_key.strip() in {
        "YOUR_API_KEY_HERE",
        "PASTE_YOUR_REAL_KEY_HERE",
    }:
        return (
            None,
            "A real Gemini API key is required. "
            "Update GEMINI_API_KEY in .env."
        )

    try:
        from google import genai

        client = genai.Client(
            api_key=api_key.strip()
        )

        # ----------------------------------------------------
        # FIND A WORKING GEMINI MODEL
        # ----------------------------------------------------

        preferred_models = [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
        ]

        available_models = []

        try:
            for model_info in client.models.list():

                model_name = getattr(
                    model_info,
                    "name",
                    ""
                )

                if not model_name:
                    continue

                # Convert models/gemini-x to gemini-x
                clean_name = model_name.replace(
                    "models/",
                    ""
                )

                available_models.append(
                    clean_name
                )

        except Exception:
            # If model listing is unavailable,
            # try the known stable models directly.
            available_models = []

        selected_model = None

        # First preference:
        # choose from models actually available
        for preferred in preferred_models:

            if preferred in available_models:

                selected_model = preferred
                break

        # Fallback:
        # choose any available Gemini text model
        if selected_model is None:

            for model_name in available_models:

                if (
                    model_name.startswith("gemini-")
                    and "image" not in model_name.lower()
                    and "tts" not in model_name.lower()
                    and "live" not in model_name.lower()
                ):

                    selected_model = model_name
                    break

        # Final fallback
        if selected_model is None:

            selected_model = "gemini-2.5-flash"

        # ----------------------------------------------------
        # PREPARE DATA SUMMARY
        # ----------------------------------------------------

        numeric_df = df.select_dtypes(
            include="number"
        )

        summary_parts = []

        summary_parts.append(
            f"Organization: {company}"
        )

        summary_parts.append(
            f"Records analyzed: {len(df)}"
        )

        summary_parts.append(
            f"Indicators/columns: {len(df.columns)}"
        )

        summary_parts.append(
            f"Missing cells: "
            f"{int(df.isna().sum().sum())}"
        )

        summary_parts.append(
            f"Columns: {', '.join(df.columns.astype(str))}"
        )

        if not numeric_df.empty:

            stats = numeric_df.describe().round(2)

            summary_parts.append(
                "Numeric summary:\n"
                + stats.to_string()
            )

        data_summary = "\n\n".join(
            summary_parts
        )

        # Limit the prompt size so very large CSV files
        # don't unnecessarily consume API tokens.
        preview = df.head(30).to_csv(
            index=False
        )

        # ----------------------------------------------------
        # ESG ANALYSIS PROMPT
        # ----------------------------------------------------

        prompt = f"""
You are an experienced ESG and sustainability analyst
supporting management decision-making.

Analyze the following ESG dataset for:

Organization:
{company}

Dataset summary:
{data_summary}

Representative data:
{preview}

Produce a concise, professional management-level ESG analysis.

Your analysis must include:

## 1. Executive ESG Assessment
Give a short overall assessment of the organization's
ESG position based only on the supplied data.

## 2. Environmental
Identify important environmental trends, strengths,
weaknesses, risks and opportunities.

Pay attention to indicators such as:
- emissions
- energy
- renewable energy
- water
- waste
- environmental performance

## 3. Social
Assess relevant social indicators such as:
- workforce
- diversity
- employee-related metrics
- safety
- inclusion
- social performance

## 4. Governance
Assess relevant governance indicators such as:
- compliance
- governance
- risk
- ethics
- transparency
- controls

## 5. Key ESG Risks
Identify the most important risks.

For each risk provide:
- Risk
- Severity: High / Medium / Low
- Evidence from the dataset
- Why management should care

Do not invent evidence.

## 6. Opportunities
Identify practical opportunities for improvement.

Prioritize actions that are:
- measurable
- realistic
- relevant to management
- supported by the dataset

## 7. Recommended Management Actions
Provide 5 prioritized actions.

For each action include:
- Action
- Priority
- Suggested owner
- Suggested timeframe
- KPI to monitor

## 8. Data Quality
Mention important data limitations,
missing values, unusual values or areas
where additional ESG data would improve confidence.

IMPORTANT RULES:

1. Use only evidence available in the dataset.
2. Do not invent company facts.
3. Do not fabricate ESG metrics.
4. Clearly distinguish observations from recommendations.
5. Use professional but understandable ESG language.
6. Focus on management decision usefulness.
7. Do not claim regulatory compliance unless the data
   actually demonstrates it.
8. Do not present the output as an assured ESG disclosure.
9. Do not claim that AI analysis replaces ESG assurance,
   legal review or professional judgment.
10. Keep the analysis concise enough for management review.
11. Where evidence is insufficient, explicitly say
    "Insufficient data to determine."
"""

        # ----------------------------------------------------
        # GEMINI REQUEST
        # ----------------------------------------------------

        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
        )

        if not response:

            return (
                None,
                "Gemini returned no response."
            )

        response_text = getattr(
            response,
            "text",
            None
        )

        if not response_text:

            return (
                None,
                "Gemini returned an empty response."
            )

        return (
            response_text.strip(),
            None
        )

    # --------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------

    except Exception as exc:

        error_message = str(exc)
        error_lower = error_message.lower()

        if (
            "401" in error_message
            or "403" in error_message
            or "unauthorized" in error_lower
            or "permission" in error_lower
            or "api key" in error_lower
        ):

            return (
                None,
                "Gemini authentication failed. "
                "Check GEMINI_API_KEY in your .env file "
                "and confirm that the API key belongs to "
                "the correct Google AI project."
            )

        if (
            "429" in error_message
            or "resource_exhausted" in error_lower
            or "rate limit" in error_lower
        ):

            return (
                None,
                "Gemini API rate limit reached. "
                "Please wait a moment and try again."
            )

        if (
            "404" in error_message
            or "not_found" in error_lower
            or "not found" in error_lower
        ):

            return (
                None,
                "No compatible Gemini model is available "
                "for this API key/project. "
                "Check the Gemini API access for your "
                "Google AI project."
            )

        return (
            None,
            f"Gemini analysis failed: {error_message}"
        )


# ============================================================
# REPORT GENERATOR
# ============================================================

def build_report(
    company,
    framework,
    df
):

    scores, overall = calculate_esg_score(
        df
    )

    risks = generate_risks(
        df
    )

    missing = int(
        df.isna().sum().sum()
    )

    report = []

    report.append(
        f"# ESG Report — {company}"
    )

    report.append("")

    report.append(
        f"**Reporting context:** {framework}"
    )

    report.append(
        f"**Generated:** "
        f"{datetime.now().strftime('%d %B %Y, %H:%M')}"
    )

    report.append("")

    # --------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------

    report.append(
        "## Executive Summary"
    )

    report.append("")

    if overall is not None:

        report.append(
            f"The calculated ESG performance score is "
            f"**{overall:.1f}/100**, based on recognizable "
            f"indicators within the uploaded dataset."
        )

    else:

        report.append(
            "A complete ESG score could not be calculated "
            "because recognizable ESG indicators were not "
            "available in the uploaded dataset."
        )

    report.append("")

    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    report.append(
        "## ESG Performance"
    )

    report.append("")

    for category, score in scores.items():

        report.append(
            f"- **{category}:** {score:.1f}/100"
        )

    report.append("")

    # --------------------------------------------------------
    # RISK REGISTER
    # --------------------------------------------------------

    report.append(
        "## Risk Register"
    )

    report.append("")

    if risks:

        for (
            severity,
            icon,
            title,
            description
        ) in risks:

            report.append(
                f"- **{severity} — {title}:** "
                f"{description}"
            )

    else:

        report.append(
            "- No automated risk signals were detected."
        )

    report.append("")

    # --------------------------------------------------------
    # ACTION PLAN
    # --------------------------------------------------------

    report.append(
        "## Recommended Management Actions"
    )

    report.append("")

    actions = [
        "Establish measurable ESG targets with clear owners, baselines and review dates.",
        "Monitor material environmental indicators and investigate unfavorable trends.",
        "Strengthen workforce, safety and inclusion metrics where relevant.",
        "Improve ESG data quality, documentation and traceability.",
        "Review performance regularly against the organization's selected reporting context.",
    ]

    for index, action in enumerate(
        actions,
        start=1
    ):

        report.append(
            f"{index}. {action}"
        )

    report.append("")

    # --------------------------------------------------------
    # DATA QUALITY
    # --------------------------------------------------------

    report.append(
        "## Data Quality"
    )

    report.append("")

    report.append(
        f"- Records analyzed: {len(df):,}"
    )

    report.append(
        f"- Indicators available: {len(df.columns):,}"
    )

    report.append(
        f"- Missing cells: {missing:,}"
    )

    report.append("")

    report.append(
        "> Important: This report is a decision-support "
        "prototype. It does not replace ESG assurance, "
        "legal review, regulatory interpretation or "
        "professional judgment."
    )

    return "\n".join(
        report
    )


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>🌱 ESGenius AI</h1>
        <p>
            ESG analytics, risk intelligence and
            AI-assisted sustainability reporting.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🌱 ESGenius AI"
)

st.sidebar.caption(
    "Sustainability Intelligence Platform"
)

page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Dashboard",
        "📁 ESG Data",
        "🤖 AI Insights",
        "📄 Report Generator",
    ],
)

st.sidebar.divider()

st.sidebar.subheader(
    "Platform capabilities"
)

st.sidebar.write(
    "✓ ESG performance scoring"
)

st.sidebar.write(
    "✓ Automated risk detection"
)

st.sidebar.write(
    "✓ Data-quality profiling"
)

st.sidebar.write(
    "✓ Gemini AI analysis"
)

st.sidebar.write(
    "✓ Management recommendations"
)

st.sidebar.write(
    "✓ ESG report generation"
)

st.sidebar.divider()

st.sidebar.caption(
    "Prototype • Decision-support use"
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.header(
        "Executive ESG Dashboard"
    )

    df = st.session_state.df

    if df is None:

        st.info(
            "Upload an ESG CSV dataset from "
            "**ESG Data** to activate the dashboard."
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Data Status",
            "Awaiting Dataset"
        )

        col2.metric(
            "AI Engine",
            "Gemini"
        )

        col3.metric(
            "Reporting",
            "Ready"
        )

        st.divider()

        st.subheader(
            "How ESGenius AI works"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                """
                ### 01 — Upload

                Import structured ESG data
                in CSV format.
                """
            )

        with c2:

            st.markdown(
                """
                ### 02 — Analyze

                Calculate performance,
                identify risks and inspect
                data quality.
                """
            )

        with c3:

            st.markdown(
                """
                ### 03 — Decide

                Generate AI insights,
                recommendations and
                management reports.
                """
            )

    else:

        scores, overall = calculate_esg_score(
            df
        )

        risks = generate_risks(
            df
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Overall ESG Score",
            f"{overall:.1f}/100"
            if overall is not None
            else "N/A"
        )

        col2.metric(
            "Records",
            f"{len(df):,}"
        )

        col3.metric(
            "Indicators",
            f"{len(df.columns):,}"
        )

        missing = int(
            df.isna().sum().sum()
        )

        col4.metric(
            "Missing Cells",
            f"{missing:,}"
        )

        st.divider()

        # ----------------------------------------------------
        # ESG SCORE CHART
        # ----------------------------------------------------

        left, right = st.columns(
            [1.5, 1]
        )

        with left:

            if scores:

                score_df = pd.DataFrame(
                    {
                        "Category": list(
                            scores.keys()
                        ),
                        "Score": list(
                            scores.values()
                        ),
                    }
                )

                fig = px.bar(
                    score_df,
                    x="Category",
                    y="Score",
                    range_y=[0, 100],
                    text_auto=".1f",
                    title="ESG Performance by Pillar",
                )

                fig.update_layout(
                    margin=dict(
                        l=20,
                        r=20,
                        t=60,
                        b=20
                    )
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

        # ----------------------------------------------------
        # RISK MONITOR
        # ----------------------------------------------------

        with right:

            st.subheader(
                "⚠️ Risk Monitor"
            )

            for (
                severity,
                icon,
                title,
                description
            ) in risks:

                st.markdown(
                    f"""
                    <div class="risk-card">
                        <b>{icon} {title}</b><br>
                        <span class="small-muted">
                            {severity} risk · {description}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ----------------------------------------------------
        # TREND
        # ----------------------------------------------------

        trend_fig = create_trend_chart(
            df
        )

        if trend_fig is not None:

            st.divider()

            st.plotly_chart(
                trend_fig,
                width="stretch"
            )

        # ----------------------------------------------------
        # DATA SNAPSHOT
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "Dataset Snapshot"
        )

        st.dataframe(
            df.head(10),
            width="stretch",
            hide_index=True
        )


# ============================================================
# ESG DATA
# ============================================================

elif page == "📁 ESG Data":

    st.header(
        "ESG Data Management"
    )

    st.write(
        "Upload structured ESG data in CSV format. "
        "The platform automatically profiles the dataset "
        "and prepares it for analysis."
    )

    uploaded_file = st.file_uploader(
        "Upload ESG dataset",
        type=["csv"],
        help="CSV files containing sustainability or ESG indicators."
    )

    if uploaded_file is not None:

        try:

            uploaded_df = pd.read_csv(
                uploaded_file
            )

            if uploaded_df.empty:

                st.error(
                    "The uploaded CSV is empty."
                )

            else:

                cleaned_df = normalize_columns(
                    uploaded_df
                )

                st.session_state.df = cleaned_df

                st.session_state.filename = (
                    uploaded_file.name
                )

                st.session_state.ai_insights = None
                st.session_state.report = None

                st.success(
                    f"Dataset loaded successfully — "
                    f"{len(cleaned_df):,} records."
                )

        except Exception as exc:

            st.error(
                f"Unable to read the CSV: {exc}"
            )

    df = st.session_state.df

    if df is not None:

        st.divider()

        st.subheader(
            "Dataset Overview"
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Rows",
            f"{len(df):,}"
        )

        col2.metric(
            "Columns",
            f"{len(df.columns):,}"
        )

        col3.metric(
            "Numeric Fields",
            f"{len(numeric_columns(df)):,}"
        )

        col4.metric(
            "Missing Cells",
            f"{int(df.isna().sum().sum()):,}"
        )

        if st.session_state.filename:

            st.caption(
                f"Loaded file: {st.session_state.filename}"
            )

        st.divider()

        tab1, tab2, tab3 = st.tabs(
            [
                "Preview",
                "Data Quality",
                "Statistics"
            ]
        )

        with tab1:

            st.dataframe(
                df,
                width="stretch",
                hide_index=True
            )

        with tab2:

            quality = pd.DataFrame(
                {
                    "Column": df.columns,
                    "Data Type": [
                        str(dtype)
                        for dtype in df.dtypes
                    ],
                    "Missing": [
                        int(
                            df[col].isna().sum()
                        )
                        for col in df.columns
                    ],
                    "Missing %": [
                        round(
                            df[col].isna().mean() * 100,
                            2
                        )
                        for col in df.columns
                    ],
                }
            )

            st.dataframe(
                quality,
                width="stretch",
                hide_index=True
            )

        with tab3:

            numeric = df.select_dtypes(
                include="number"
            )

            if numeric.empty:

                st.warning(
                    "No numeric columns were detected."
                )

            else:

                st.dataframe(
                    numeric.describe().T,
                    width="stretch"
                )


# ============================================================
# AI INSIGHTS
# ============================================================

elif page == "🤖 AI Insights":

    st.header(
        "AI ESG Intelligence"
    )

    df = st.session_state.df

    if df is None:

        st.warning(
            "Upload an ESG dataset first "
            "from **ESG Data**."
        )

    else:

        scores, overall = calculate_esg_score(
            df
        )

        risks = generate_risks(
            df
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Calculated ESG Score",
                f"{overall:.1f}/100"
                if overall is not None
                else "N/A"
            )

        with col2:

            st.metric(
                "Detected Risk Signals",
                len(risks)
            )

        st.divider()

        st.subheader(
            "Automated Risk Detection"
        )

        for (
            severity,
            icon,
            title,
            description
        ) in risks:

            if severity == "High":

                st.error(
                    f"{icon} **{title}** — {description}"
                )

            elif severity == "Medium":

                st.warning(
                    f"{icon} **{title}** — {description}"
                )

            else:

                st.success(
                    f"{icon} **{title}** — {description}"
                )

        st.divider()

        st.subheader(
            "Gemini AI Analysis"
        )

        company = st.text_input(
            "Organization name",
            value="Your Organization"
        )

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        api_ready = (
            GEMINI_AVAILABLE
            and api_key
            and api_key.strip()
            and api_key != "YOUR_API_KEY_HERE"
            and api_key != "PASTE_YOUR_REAL_KEY_HERE"
        )

        if api_ready:

            st.success(
                "Gemini AI is configured and ready."
            )

        else:

            st.warning(
                "Gemini AI is not configured. "
                "Add GEMINI_API_KEY to your .env file."
            )

        if st.button(
            "✨ Generate AI ESG Analysis",
            type="primary",
            width="stretch"
        ):

            if not api_ready:

                st.error(
                    "Configure GEMINI_API_KEY before "
                    "running AI analysis."
                )

            else:

                with st.spinner(
                    "Gemini is analyzing your ESG dataset..."
                ):

                    insights, error = generate_ai_insights(
                        df,
                        company
                    )

                if insights:

                    st.session_state.ai_insights = (
                        insights
                    )

                    st.success(
                        "AI analysis completed successfully."
                    )

                else:

                    st.error(
                        error
                    )

        if st.session_state.ai_insights:

            st.divider()

            st.markdown(
                st.session_state.ai_insights
            )

            st.info(
                "AI-generated findings are decision-support "
                "outputs. Review the underlying data and "
                "methodology before using them in official "
                "ESG disclosures."
            )


# ============================================================
# REPORT GENERATOR
# ============================================================

elif page == "📄 Report Generator":

    st.header(
        "ESG Report Generator"
    )

    df = st.session_state.df

    if df is None:

        st.warning(
            "Upload an ESG dataset first."
        )

    else:

        company = st.text_input(
            "Company / Organization",
            placeholder="Example: ABC Manufacturing Ltd."
        )

        framework = st.selectbox(
            "Reporting Context",
            [
                "GRI",
                "SASB",
                "TCFD",
                "CSRD",
                "ISSB",
                "Internal ESG Management Report",
            ]
        )

        st.caption(
            "The selected framework provides reporting context. "
            "This prototype does not automatically establish "
            "regulatory compliance."
        )

        if st.button(
            "📄 Generate ESG Report",
            type="primary",
            width="stretch"
        ):

            if not company.strip():

                st.warning(
                    "Please enter the organization name."
                )

            else:

                with st.spinner(
                    "Building ESG report..."
                ):

                    report = build_report(
                        company,
                        framework,
                        df
                    )

                st.session_state.report = report

                st.success(
                    "ESG report generated successfully."
                )

        if st.session_state.report:

            st.divider()

            st.markdown(
                st.session_state.report
            )

            st.download_button(
                label="⬇️ Download ESG Report",
                data=st.session_state.report,
                file_name="esg_report.md",
                mime="text/markdown",
                width="stretch"
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "ESGenius AI • ESG analytics and sustainability decision support • "
    "Prototype for demonstration and evaluation"
)