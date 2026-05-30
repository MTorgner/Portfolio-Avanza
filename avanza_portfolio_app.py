import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import feedparser
from urllib.parse import quote_plus

st.set_page_config(page_title="Avanza Portfolio Intelligence", layout="wide")

st.title("Avanza Portfolio Intelligence")
st.write(
    "Upload your Avanza CSV to analyze allocation, concentration, diversification, "
    "portfolio health, and recent industry/company news."
)

uploaded_file = st.file_uploader("Upload your Avanza CSV file", type=["csv"])

def read_avanza_csv(file):
    try:
        return pd.read_csv(file, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, sep=";", encoding="latin1")

def clean_numeric(series):
    return (
        series.astype(str)
        .str.replace("SEK", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("\u00a0", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.extract(r"([-+]?\d*\.?\d+)")[0]
        .astype(float)
    )

def find_first_existing_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def risk_level(weight):
    if weight >= 0.25:
        return "High"
    if weight >= 0.15:
        return "Medium"
    return "Low"

def diversification_score(largest_weight, top_3_weight, top_5_weight, holdings_count):
    score = 100

    if largest_weight > 0.25:
        score -= 25
    elif largest_weight > 0.15:
        score -= 10

    if top_3_weight > 0.50:
        score -= 25
    elif top_3_weight > 0.35:
        score -= 10

    if top_5_weight > 0.70:
        score -= 20
    elif top_5_weight > 0.55:
        score -= 10

    if holdings_count < 8:
        score -= 20
    elif holdings_count < 12:
        score -= 10

    return max(score, 0)

def get_google_news(query, max_results=5):
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    news_items = []
    for entry in feed.entries[:max_results]:
        news_items.append({
            "Title": entry.get("title", "No title"),
            "Source": entry.get("source", {}).get("title", "Unknown source"),
            "Published": entry.get("published", "Unknown date"),
            "Link": entry.get("link", "")
        })

    return news_items

def display_news_section(title, query, max_results=5):
    st.markdown(f"### {title}")
    news = get_google_news(query, max_results=max_results)

    if not news:
        st.write("No recent news found.")
        return

    for item in news:
        st.markdown(f"**[{item['Title']}]({item['Link']})**")
        st.caption(f"{item['Source']} | {item['Published']}")
        st.write("---")

if uploaded_file is not None:
    df = read_avanza_csv(uploaded_file)
    df = df.loc[:, ~df.columns.duplicated()]

    st.subheader("Uploaded Data Preview")
    st.dataframe(df.head(20), use_container_width=True)

    with st.expander("Columns detected"):
        st.write(list(df.columns))

    name_col = find_first_existing_column(
        df,
        ["Namn", "Kortnamn", "Värdepapper", "Instrument", "Security", "Name"]
    )

    value_col = find_first_existing_column(
        df,
        ["Marknadsvärde", "Marknadsvarde", "Värde", "Varde", "Value", "Market Value", "Belopp"]
    )

    sector_col = find_first_existing_column(df, ["Sektor", "Sector", "Bransch"])
    country_col = find_first_existing_column(df, ["Land", "Country"])
    type_col = find_first_existing_column(df, ["Typ", "Type", "Instrumenttyp"])

    if name_col is None or value_col is None:
        st.error("I could not find the required columns. Your file needs a holding name column and a market value column.")
        st.stop()

    portfolio = pd.DataFrame()
    portfolio["Name"] = df[name_col].astype(str)
    portfolio["Market Value"] = clean_numeric(df[value_col])

    if sector_col is not None:
        portfolio["Sector"] = df[sector_col].astype(str)

    if country_col is not None:
        portfolio["Country"] = df[country_col].astype(str)

    if type_col is not None:
        portfolio["Type"] = df[type_col].astype(str)

    portfolio = portfolio.dropna(subset=["Name", "Market Value"])
    portfolio = portfolio[portfolio["Market Value"] > 0]

    if portfolio.empty:
        st.error("No valid holdings were found after cleaning the file.")
        st.stop()

    total_value = portfolio["Market Value"].sum()
    portfolio["Weight"] = portfolio["Market Value"] / total_value
    portfolio = portfolio.sort_values("Weight", ascending=False)

    largest_holding = portfolio.iloc[0]
    top_3_weight = portfolio.head(3)["Weight"].sum()
    top_5_weight = portfolio.head(5)["Weight"].sum()
    top_10_weight = portfolio.head(10)["Weight"].sum()
    holdings_count = len(portfolio)

    score = diversification_score(
        largest_holding["Weight"],
        top_3_weight,
        top_5_weight,
        holdings_count
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Portfolio Overview",
        "Risk & Allocation",
        "News",
        "Investment Memo"
    ])

    with tab1:
        st.subheader("Executive Dashboard")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Portfolio Value", f"{total_value:,.0f}")
        col2.metric("Holdings", holdings_count)
        col3.metric("Largest Holding", f"{largest_holding['Weight']:.1%}")
        col4.metric("Top 5 Weight", f"{top_5_weight:.1%}")
        col5.metric("Health Score", f"{score}/100")

        if score >= 80:
            st.success("Overall read: strong diversification profile.")
        elif score >= 60:
            st.warning("Overall read: moderate concentration risk.")
        else:
            st.error("Overall read: high concentration risk.")

        st.subheader("Clean Portfolio Table")
        display_df = portfolio.copy()
        display_df["Weight"] = display_df["Weight"].map(lambda x: f"{x:.2%}")
        st.dataframe(display_df, use_container_width=True)

    with tab2:
        st.subheader("Portfolio Health Breakdown")

        breakdown = pd.DataFrame({
            "Metric": [
                "Largest holding",
                "Top 3 concentration",
                "Top 5 concentration",
                "Top 10 concentration",
                "Number of holdings"
            ],
            "Result": [
                f"{largest_holding['Weight']:.1%}",
                f"{top_3_weight:.1%}",
                f"{top_5_weight:.1%}",
                f"{top_10_weight:.1%}",
                str(holdings_count)
            ],
            "Interpretation": [
                "High risk if above 25%",
                "High risk if above 50%",
                "High risk if above 70%",
                "Useful to see if smaller positions matter",
                "Low diversification if fewer than 8"
            ]
        })

        st.dataframe(breakdown, use_container_width=True)

        st.subheader("Position-Level Risk")
        risk_table = portfolio[["Name", "Market Value", "Weight"]].copy()
        risk_table["Risk Level"] = risk_table["Weight"].apply(risk_level)
        risk_table["Weight"] = risk_table["Weight"].map(lambda x: f"{x:.2%}")
        st.dataframe(risk_table, use_container_width=True)

        st.subheader("Top 10 Holdings by Weight")
        chart_data = portfolio.head(10).copy()
        fig, ax = plt.subplots()
        ax.bar(chart_data["Name"], chart_data["Weight"])
        ax.set_ylabel("Portfolio Weight")
        ax.set_xlabel("Holding")
        ax.set_title("Top 10 Holdings by Weight")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig)

        st.subheader("Portfolio Allocation")
        pie_data = portfolio.head(8).copy()
        other_value = portfolio.iloc[8:]["Market Value"].sum()

        if other_value > 0:
            pie_data = pd.concat([
                pie_data,
                pd.DataFrame([{"Name": "Other", "Market Value": other_value}])
            ], ignore_index=True)

        fig2, ax2 = plt.subplots()
        ax2.pie(pie_data["Market Value"], labels=pie_data["Name"], autopct="%1.1f%%")
        ax2.set_title("Portfolio Allocation")
        st.pyplot(fig2)

        if "Sector" in portfolio.columns:
            st.subheader("Sector Allocation")
            sector_df = portfolio.groupby("Sector", as_index=False)["Market Value"].sum()
            sector_df["Weight"] = sector_df["Market Value"] / total_value
            sector_df = sector_df.sort_values("Weight", ascending=False)

            sector_display = sector_df.copy()
            sector_display["Weight"] = sector_display["Weight"].map(lambda x: f"{x:.2%}")
            st.dataframe(sector_display, use_container_width=True)

        if "Country" in portfolio.columns:
            st.subheader("Country Allocation")
            country_df = portfolio.groupby("Country", as_index=False)["Market Value"].sum()
            country_df["Weight"] = country_df["Market Value"] / total_value
            country_df = country_df.sort_values("Weight", ascending=False)

            country_display = country_df.copy()
            country_display["Weight"] = country_display["Weight"].map(lambda x: f"{x:.2%}")
            st.dataframe(country_display, use_container_width=True)

        if "Type" in portfolio.columns:
            st.subheader("Asset Type Allocation")
            type_df = portfolio.groupby("Type", as_index=False)["Market Value"].sum()
            type_df["Weight"] = type_df["Market Value"] / total_value
            type_df = type_df.sort_values("Weight", ascending=False)

            type_display = type_df.copy()
            type_display["Weight"] = type_display["Weight"].map(lambda x: f"{x:.2%}")
            st.dataframe(type_display, use_container_width=True)

    with tab3:
        st.subheader("Portfolio News Feed")
        st.write("This section searches recent Google News headlines for your top holdings and sectors.")

        top_news_count = st.slider("How many top holdings should news cover?", 1, 10, 5)
        headlines_per_holding = st.slider("Headlines per holding", 1, 5, 3)

        st.subheader("Company News for Top Holdings")

        for _, row in portfolio.head(top_news_count).iterrows():
            query = f"{row['Name']} stock earnings company news"
            display_news_section(
                f"{row['Name']} News",
                query,
                max_results=headlines_per_holding
            )

        if "Sector" in portfolio.columns:
            st.subheader("Industry / Sector News")

            top_sectors = (
                portfolio.groupby("Sector", as_index=False)["Market Value"]
                .sum()
                .sort_values("Market Value", ascending=False)
                .head(5)
            )

            for _, row in top_sectors.iterrows():
                query = f"{row['Sector']} sector market news stocks"
                display_news_section(
                    f"{row['Sector']} Industry News",
                    query,
                    max_results=3
                )

        st.subheader("Macro News")
        macro_queries = [
            "Riksbank interest rates Sweden economy",
            "Federal Reserve interest rates stock market",
            "inflation stock market economy",
            "Sweden stock market OMX news"
        ]

        selected_macro = st.selectbox("Choose macro news topic", macro_queries)
        display_news_section("Macro Headlines", selected_macro, max_results=5)

    with tab4:
        st.subheader("Investment Memo")

        memo = f"""
**Portfolio overview:**  
The portfolio has an estimated value of **{total_value:,.0f}** across **{holdings_count} holdings**.

**Concentration:**  
The largest position is **{largest_holding['Name']}**, representing **{largest_holding['Weight']:.1%}** of the portfolio.  
The top 3 holdings represent **{top_3_weight:.1%}**, while the top 5 represent **{top_5_weight:.1%}**.

**Interpretation:**  
"""

        if score >= 80:
            memo += "The portfolio appears reasonably diversified based on the current concentration rules."
        elif score >= 60:
            memo += "The portfolio has moderate concentration risk. Review whether a few holdings are driving too much total performance."
        else:
            memo += "The portfolio appears highly concentrated. Performance may depend heavily on a small number of positions."

        st.markdown(memo)

        st.subheader("Risk Flags")
        flags = []

        if largest_holding["Weight"] > 0.25:
            flags.append(f"{largest_holding['Name']} is above 25% of the portfolio.")
        if top_3_weight > 0.50:
            flags.append("The top 3 holdings make up more than 50% of the portfolio.")
        if top_5_weight > 0.70:
            flags.append("The top 5 holdings make up more than 70% of the portfolio.")
        if holdings_count < 8:
            flags.append("The portfolio has fewer than 8 holdings.")
        if top_10_weight > 0.90 and holdings_count > 10:
            flags.append("The top 10 holdings make up more than 90%, so smaller positions have limited impact.")

        if flags:
            for flag in flags:
                st.warning(flag)
        else:
            st.success("No major concentration flags found based on the basic rules.")

        st.subheader("What To Review Next")

        review_items = []

        if largest_holding["Weight"] > 0.20:
            review_items.append("Check whether your largest holding is intentionally this large.")
        if top_3_weight > 0.40:
            review_items.append("Review if your top 3 holdings match your risk tolerance.")
        if "Sector" not in portfolio.columns:
            review_items.append("Add a Sector column to your CSV so the app can analyze sector exposure.")
        if "Country" not in portfolio.columns:
            review_items.append("Add a Country column to your CSV so the app can analyze geographic exposure.")
        if "Type" not in portfolio.columns:
            review_items.append("Add a Type column such as Stock, Fund, ETF, or Cash.")

        review_items.append("Check the News tab for company-specific headlines before making portfolio decisions.")
        review_items.append("Track the same portfolio monthly so you can measure changes over time.")

        for item in review_items:
            st.write("- " + item)

        st.info("Important: This is not financial advice and does not recommend specific trades.")

else:
    st.info("Upload a CSV file to begin.")

