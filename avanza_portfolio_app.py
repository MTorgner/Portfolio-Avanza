
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Avanza Portfolio Assistant", layout="wide")

st.title("Avanza Portfolio Assistant")
st.write(
    "Upload your Avanza CSV to review allocation, concentration risk, and portfolio health. "
    "This is an analysis tool only and does not place trades."
)

uploaded_file = st.file_uploader("Upload your Avanza CSV file", type=["csv"])

def read_avanza_csv(file):
    """Reads Avanza CSV files that usually use semicolons."""
    try:
        return pd.read_csv(file, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, sep=";", encoding="latin1")

def clean_numeric(series):
    """Converts Swedish-style numbers like 12 345,67 SEK into floats."""
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

if uploaded_file is not None:
    df = read_avanza_csv(uploaded_file)

    # Remove duplicate columns from the original CSV
    df = df.loc[:, ~df.columns.duplicated()]

    st.subheader("Uploaded Data Preview")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("Columns Detected")
    st.write(list(df.columns))

    # Choose only ONE column for each needed field to avoid duplicate renamed columns
    name_col = find_first_existing_column(
        df,
        ["Namn", "Kortnamn", "Värdepapper", "Instrument", "Security", "Name"]
    )

    value_col = find_first_existing_column(
        df,
        ["Marknadsvärde", "Marknadsvarde", "Värde", "Varde", "Value", "Market Value", "Belopp"]
    )

    sector_col = find_first_existing_column(df, ["Sektor", "Sector"])
    country_col = find_first_existing_column(df, ["Land", "Country"])

    if name_col is None or value_col is None:
        st.error(
            "I could not find the required columns. Your file needs a holding name column "
            "and a market value column. Look at 'Columns Detected' above and rename the right columns "
            "to 'Name' and 'Market Value' if needed."
        )
        st.stop()

    # Build a clean portfolio table with no duplicate column names
    portfolio = pd.DataFrame()
    portfolio["Name"] = df[name_col].astype(str)
    portfolio["Market Value"] = clean_numeric(df[value_col])

    if sector_col is not None:
        portfolio["Sector"] = df[sector_col].astype(str)

    if country_col is not None:
        portfolio["Country"] = df[country_col].astype(str)

    portfolio = portfolio.dropna(subset=["Name", "Market Value"])
    portfolio = portfolio[portfolio["Market Value"] > 0]

    if portfolio.empty:
        st.error("No valid holdings were found after cleaning the file.")
        st.stop()

    total_value = portfolio["Market Value"].sum()
    portfolio["Weight"] = portfolio["Market Value"] / total_value

    top_holdings = portfolio.sort_values("Weight", ascending=False)
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
    if len(portfolio) < 8:
        score -= 15

    score = max(score, 0)
    st.metric("Portfolio Score", f"{score}/100")

    if score >= 80:
        st.success("Strong diversification profile.")
    elif score >= 60:
        st.warning("Moderate risk. Some concentration issues to review.")
    else:
        st.error("High concentration risk. Portfolio needs closer review.")

    st.subheader("Clean Portfolio Table")
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
    if len(portfolio) < 8:
        flags.append("You have fewer than 8 holdings, which may mean limited diversification.")

    if flags:
        for flag in flags:
            st.warning(flag)
    else:
        st.success("No major concentration flags found based on the basic rules.")

    st.subheader("Top 10 Holdings by Weight")
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
        ], ignore_index=True)

    fig2, ax2 = plt.subplots()
    ax2.pie(pie_data["Market Value"], labels=pie_data["Name"], autopct="%1.1f%%")
    ax2.set_title("Portfolio Allocation")
    st.pyplot(fig2)

    if "Sector" in portfolio.columns:
        st.subheader("Sector Allocation")
        sector_df = portfolio.groupby("Sector", as_index=False)["Market Value"].sum()
        sector_df["Weight"] = sector_df["Market Value"] / total_value
        st.dataframe(sector_df.sort_values("Weight", ascending=False), use_container_width=True)

    if "Country" in portfolio.columns:
        st.subheader("Country Allocation")
        country_df = portfolio.groupby("Country", as_index=False)["Market Value"].sum()
        country_df["Weight"] = country_df["Market Value"] / total_value
        st.dataframe(country_df.sort_values("Weight", ascending=False), use_container_width=True)

    st.subheader("Portfolio Commentary")

    commentary = [
        f"Your largest holding is {largest_holding['Name']} at {largest_holding['Weight']:.1%} of the portfolio."
    ]

    if top_3_weight > 0.50:
        commentary.append("Your top 3 holdings make up more than half of your portfolio, which suggests concentration risk.")
    else:
        commentary.append("Your top 3 holdings are not overly concentrated based on the 50% rule.")

    if top_5_weight > 0.70:
        commentary.append("Your top 5 holdings represent a large share of the portfolio, so performance may depend heavily on only a few positions.")
    else:
        commentary.append("Your top 5 holdings do not appear extremely concentrated based on the 70% rule.")

    if len(portfolio) < 8:
        commentary.append("You have a relatively small number of holdings, so diversification may be limited.")
    else:
        commentary.append("You have a reasonable number of holdings for basic diversification.")

    commentary.append("This tool does not give buy or sell recommendations, but it helps identify areas worth reviewing.")

    for line in commentary:
        st.write("- " + line)

    st.info(
        "Important: This app is not financial advice. It does not recommend specific trades."
    )

else:
    st.info("Upload a CSV file to begin.")


