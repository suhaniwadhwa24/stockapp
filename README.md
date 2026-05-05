# 📊 Narrative vs Fundamentals — Stock Analysis App

> Is the stock driven by hype or by real business performance?

A Streamlit web app that compares the media narrative around a stock against its actual financial fundamentals, powered by Claude AI, live news via NewsAPI, and real-time data via yfinance.

🔗 Live App: https://suhaniwadhwa24-stockapp-app-cqepq9.streamlit.app/

---

## What It Does

Enter any stock ticker (e.g. TSLA, NVDA, AAPL) and the app:

1. Fetches the 15 most recent news headlines about the company
2. Pulls live financial metrics (P/E ratio, margins, revenue growth, debt, etc.)
3. Sends both to Claude AI for analysis
4. Returns a Narrative Score (1–10) and a Fundamentals Score (1–10)
5. Computes a Gap Score showing divergence between hype and reality
6. Delivers a verdict: from STRONGLY HYPE-DRIVEN to STRONGLY FUNDAMENTALS-DRIVEN

---

## Tech Stack

- Frontend: Streamlit
- AI Analysis: Anthropic Claude (claude-haiku)
- Stock Data: yfinance
- News Headlines: NewsAPI
- Charts: Plotly
- Data: Pandas

---

## How to Run Locally

1. Clone the repo
   git clone https://github.com/suhaniwadhwa24/stockapp.git

2. Install dependencies
   pip install streamlit yfinance requests anthropic plotly pandas

3. Create a .streamlit/secrets.toml file and add:
   ANTHROPIC_API_KEY = "your-key-here"
   NEWS_API_KEY = "your-key-here"

4. Run:
   streamlit run app.py

---

## Scoring Logic

- Narrative Score (1–10): 1 = very bearish, 5 = neutral, 10 = extreme hype
- Fundamentals Score (1–10): 1 = weak financials, 10 = exceptionally strong
- Gap Score: Narrative minus Fundamentals — positive means overhyped, negative means potentially undervalued

## Verdicts

- STRONGLY HYPE-DRIVEN
- HYPE-DRIVEN
- BALANCED
- FUNDAMENTALS-DRIVEN
- STRONGLY FUNDAMENTALS-DRIVEN
