
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Avanza Portfolio Assistant", layout="wide")

st.title("Avanza Portfolio Assistant")
st.write(
    "Upload your Avanza portfolio CSV to review allocation, concentration, cash exposure, "
    "and basic portfolio risk flags. This tool is for analysis only and does not place trades."
)

uploaded_file = st.file_uploader("Upload your Avanza CSV file", type=["csv"])

def normalize_columns(df):
    """Try to map common Avanza/English/Swedish column names into standard names."""
    column_map = {}

    possible_name_cols = ["Name", "Namn", "Kortnamn", "Värdepapper", "Instrument", "Security"]
    possible_value_cols = ["Market Value", "Marknadsvärde", "Värde", "Value", "Belopp", "Marknadsvarde"]
    possible_qty_cols = ["Quantity", "Antal", "Volym", "Qty"]
    possible_sector_cols = ["Sector", "Sektor"]
    possible_country_cols = ["Country", "Land"]
    possible_type_cols = ["Type", "Typ", "Instrumenttyp"]

    for col in df.columns:
        clean_col = col.strip()
        if clean_col in possible_name_cols:
            column_map[col] = "Name"
        elif clean_col in possible_value_cols:
            column_map[col] = "Market Value"
        elif clean_col in possible_qty_cols:
            column_map[col] = "Quantity"
        elif clean_col in possible_sector_cols:
            column_map[col] = "Sector"
        elif clean_col in possible_country_cols:
            column_map[col] = "Country"
        elif clean_col in possible_type_cols:
            column_map[col] = "Type"

    return df.rename(columns=column_map)

def clean_numeric(series):
    """Handle numbers with commas, spaces, Swedish formatting, and currency symbols."""
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

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=";")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding="latin1", sep=";")

    df = normalize_columns(df)

    st.subheader("Uploaded Data Preview")
    st.dataframe(df.head(20), use_container_width=True)

    if "Name" not in df.columns or "Market Value" not in df.columns:
        st.error(
            "I could not find the required columns. Your file needs a name column and a market value column. "
            "Rename them to 'Name' and 'Market Value', then upload again."
        )
        st.stop()

    df["Market Value"] = clean_numeric(df["Market Value"])
    df = df.dropna(subset=["Name", "Market Value"])
    df = df[df["Market Value"] > 0]

    total_value = df["Market Value"].sum()
    df["Weight"] = df["Market Value"] / total_value

    top_holdings = df.sort_values("Weight", ascending=False)
    top_3_weight = top_holdings.head(3)["Weight"].sum()
    top_5_weight = top_holdings.head(5)["Weight"].sum()
    largest_holding = top_holdings.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Portfolio Value", f"{total_value:,.0f}")
    col2.metric("Largest Holding", f"{largest_holding['Weight']:.1%}")
    col3.metric("Top 3 Weight", f"{top_3_weight:.1%}")
    col4.metric("Top 5 Weight", f"{top_5_weight:.1%}")

    st.subheader("Portfolio Health Score")

    score = 100

    if largest_holding["Weight"] > 0.25:
        score -= 20
    if top_3_weight > 0.50:
        score -= 20
    if top_5_weight > 0.70:
        score -= 15
    if len(df) < 8:
        score -= 15

    score = max(score, 0)

    st.metric("Portfolio Score", f"{score}/100")

    if score >= 80:
        st.success("Strong diversification profile.")
    elif score >= 60:
        st.warning("Moderate risk. Some concentration issues to review.")
    else:
        st.error("High concentration risk. Portfolio needs closer review.")

    st.subheader("Top Holdings")
    display_df = top_holdings.copy()
    display_df["Weight"] = display_df["Weight"].map(lambda x: f"{x:.2%}")
    st.dataframe(display_df, use_container_width=True)

    st.subheader("Risk Flags")
    flags = []

    if largest_holding["Weight"] > 0.25:
        flags.append(f"Your largest holding, {largest_holding['Name']}, is above 25% of the portfolio.")
    if top_3_weight > 0.50:
        flags.append("Your top 3 holdings make up more than 50% of the portfolio.")
    if top_5_weight > 0.70:
        flags.append("Your top 5 holdings make up more than 70% of the portfolio.")
    if len(df) < 8:
        flags.append("You have fewer than 8 holdings, which may mean limited diversification.")

    if flags:
        for flag in flags:
            st.warning(flag)
    else:
        st.success("No major concentration flags found based on the basic rules.")

    st.subheader("Portfolio Weight Chart")
    chart_data = top_holdings.head(10).copy()
    fig, ax = plt.subplots()
    ax.bar(chart_data["Name"], chart_data["Weight"])
    ax.set_ylabel("Portfolio Weight")
    ax.set_xlabel("Holding")
    ax.set_title("Top 10 Holdings by Weight")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)

    st.subheader("Portfolio Allocation")
    pie_data = top_holdings.head(8).copy()
    other_value = top_holdings.iloc[8:]["Market Value"].sum()

    if other_value > 0:
        pie_data = pd.concat([
            pie_data,
            pd.DataFrame([{"Name": "Other", "Market Value": other_value}])
        ])

    fig2, ax2 = plt.subplots()
    ax2.pie(pie_data["Market Value"], labels=pie_data["Name"], autopct="%1.1f%%")
    ax2.set_title("Portfolio Allocation")
    st.pyplot(fig2)

    if "Sector" in df.columns:
        st.subheader("Sector Allocation")
        sector_df = df.groupby("Sector", as_index=False)["Market Value"].sum()
        sector_df["Weight"] = sector_df["Market Value"] / total_value
        st.dataframe(sector_df.sort_values("Weight", ascending=False), use_container_width=True)

    if "Country" in df.columns:
        st.subheader("Country Allocation")
        country_df = df.groupby("Country", as_index=False)["Market Value"].sum()
        country_df["Weight"] = country_df["Market Value"] / total_value
        st.dataframe(country_df.sort_values("Weight", ascending=False), use_container_width=True)

    st.subheader("Portfolio Commentary")

    commentary = []

    commentary.append(
        f"Your largest holding is {largest_holding['Name']} at {largest_holding['Weight']:.1%} of the portfolio."
    )

    if top_3_weight > 0.50:
        commentary.append("Your top 3 holdings make up more than half of your portfolio, which suggests concentration risk.")
    else:
        commentary.append("Your top 3 holdings are not overly concentrated based on the 50% rule.")

    if top_5_weight > 0.70:
        commentary.append("Your top 5 holdings represent a large share of the portfolio, so performance may depend heavily on only a few positions.")
    else:
        commentary.append("Your top 5 holdings do not appear extremely concentrated based on the 70% rule.")

    if len(df) < 8:
        commentary.append("You have a relatively small number of holdings, so diversification may be limited.")
    else:
        commentary.append("You have a reasonable number of holdings for basic diversification.")

    commentary.append(
        "This tool does not give buy or sell recommendations, but it helps you identify areas worth reviewing."
    )

    for line in commentary:
        st.write("- " + line)

    st.subheader("Plain-English Portfolio Summary")
    summary = f"""
    Your portfolio is worth approximately {total_value:,.0f}. Your largest holding is {largest_holding['Name']},
    representing {largest_holding['Weight']:.1%} of the portfolio. Your top 3 holdings represent {top_3_weight:.1%},
    and your top 5 holdings represent {top_5_weight:.1%}. 
    """

    if flags:
        summary += "The main issue to review is concentration risk. This does not automatically mean you should sell, but it is worth checking whether the portfolio still matches your risk tolerance and goals."
    else:
        summary += "Based on the basic concentration rules, the portfolio appears reasonably diversified."

    st.write(summary)

    st.info(
        "Important: This app is not financial advice. It does not recommend specific trades. "
        "Use it as a review tool before making your own decisions."
    )

else:
    st.info("Upload a CSV file to begin.")

