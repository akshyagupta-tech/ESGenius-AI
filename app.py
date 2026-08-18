import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="ESGenius AI",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 ESGenius AI")
st.subheader("AI-Powered ESG Reporting & Sustainability Intelligence")

st.write(
    "Transform ESG data into meaningful insights, visualizations, "
    "and sustainability recommendations."
)

st.divider()

# Sidebar
st.sidebar.title("ESGenius AI")
st.sidebar.write("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "ESG Data",
        "AI Insights",
        "Report Generator"
    ]
)

# ---------------- DASHBOARD ----------------
if page == "Dashboard":

    st.header("📊 ESG Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("ESG Score", "78/100", "+5%")
    col2.metric("Carbon Emissions", "1,240 tCO₂e", "-8%")
    col3.metric("Renewable Energy", "64%", "+12%")
    col4.metric("Employee Diversity", "58%", "+4%")

    st.divider()

    data = pd.DataFrame({
        "Category": [
            "Environment",
            "Social",
            "Governance"
        ],
        "Score": [
            82,
            74,
            79
        ]
    })

    fig = px.bar(
        data,
        x="Category",
        y="Score",
        title="ESG Performance by Category",
        range_y=[0, 100]
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------- ESG DATA ----------------
elif page == "ESG Data":

    st.header("📁 ESG Data Management")

    st.write("Upload your ESG dataset in CSV format.")

    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"]
    )

    if uploaded_file is not None:

        df = pd.read_csv(uploaded_file)

        st.success("CSV uploaded successfully!")

        st.write("### Preview")
        st.dataframe(df, width="stretch")

        st.write("### Dataset Information")

        col1, col2 = st.columns(2)

        col1.metric("Rows", len(df))
        col2.metric("Columns", len(df.columns))

# ---------------- AI INSIGHTS ----------------
elif page == "AI Insights":

    st.header("🤖 AI ESG Insights")

    st.info(
        "AI analysis will identify ESG risks, anomalies, "
        "trends and improvement opportunities."
    )

    if st.button("Generate AI Insights"):

        st.success("AI analysis initiated.")

        st.write("### 🔎 Preliminary Insights")

        st.write("• Environmental performance is showing positive progress.")

        st.write("• Carbon emissions should be monitored closely.")

        st.write("• Renewable energy adoption is improving.")

        st.write("• Governance indicators require continuous monitoring.")

# ---------------- REPORT GENERATOR ----------------
elif page == "Report Generator":

    st.header("📄 ESG Report Generator")

    company = st.text_input(
        "Company Name",
        placeholder="Enter company name"
    )

    framework = st.selectbox(
        "Select ESG Framework",
        [
            "GRI",
            "SASB",
            "TCFD",
            "CSRD",
            "ISSB"
        ]
    )

    if st.button("Generate ESG Report"):

        if company:

            st.success("Report generated successfully!")

            st.write(f"### ESG Report — {company}")

            st.write(
                f"This ESG report has been prepared using the "
                f"{framework} framework."
            )

            st.write("#### Environment")
            st.write(
                "The organization should continue reducing carbon "
                "emissions and increasing renewable energy adoption."
            )

            st.write("#### Social")
            st.write(
                "Employee diversity, workplace safety and employee "
                "well-being should be continuously monitored."
            )

            st.write("#### Governance")
            st.write(
                "Strong governance, transparency and compliance "
                "mechanisms should be maintained."
            )

        else:
            st.warning("Please enter the company name.")