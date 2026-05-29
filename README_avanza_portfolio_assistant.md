
# Avanza Portfolio Assistant

A simple Streamlit dashboard for reviewing an Avanza portfolio export.

## What it does

- Uploads a CSV file
- Calculates portfolio weights
- Shows top holdings
- Flags concentration risk
- Shows sector and country allocation if those columns exist
- Generates a plain-English portfolio summary

## How to run

1. Install Python
2. Install requirements:

```bash
pip install streamlit pandas matplotlib
```

3. Run the app:

```bash
streamlit run avanza_portfolio_app.py
```

## Required CSV columns

Your file needs at least:

- Name
- Market Value

The app also tries to recognize Swedish column names such as:

- Namn
- Värdepapper
- Marknadsvärde
- Värde
- Antal
- Sektor
- Land

## Important

This tool is for portfolio analysis only. It does not connect to Avanza, does not place trades, and does not provide personalized financial advice.
