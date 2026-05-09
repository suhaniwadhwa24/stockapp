import streamlit as st
import yfinance as yf
import requests
import anthropic
import plotly.graph_objects as go
import json
import pandas as pd

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Narrative vs Fundamentals",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .verdict-box {
        background: #1c1f26;
        border-radius: 12px;
        padding: 24px;
        border-left: 5px solid;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Configuration")
    anthropic_key = st.secrets["ANTHROPIC_API_KEY"]
    news_key = st.secrets["NEWS_API_KEY"]
    st.markdown("---")
    st.markdown("**How it works**")
    st.markdown("""
1. Enter a stock ticker
2. We fetch real news headlines
3. We pull live financial data
4. Anthropic scores both dimensions
5. You see the gap — hype vs reality
""")

st.title("📊 Narrative vs Fundamentals")
st.markdown("*Is the stock driven by hype or by real business performance?*")
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    ticker_input = st.text_input("Enter Stock Ticker", placeholder="e.g. TSLA, NVDA, AAPL", label_visibility="collapsed")
with col2:
    analyze_btn = st.button("🔍 Analyze", use_container_width=True, type="primary")


def fetch_news(ticker, company_name, api_key):
    query = f"{company_name} OR {ticker} stock"
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={requests.utils.quote(query)}"
        f"&language=en"
        f"&sortBy=publishedAt"
        f"&pageSize=20"
        f"&apiKey={api_key}"
    )
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        articles = data.get("articles", [])
        headlines = [
            a["title"] for a in articles
            if a.get("title") and "[Removed]" not in a["title"]
        ]
        return headlines[:15]
    except Exception as e:
        return [f"Error fetching news: {e}"]


def fetch_fundamentals(ticker):
    try:
        t = yf.Ticker(ticker)
        info = dict(t.info)
        rev_growth = None
        financials = t.financials
        if financials is not None and not financials.empty and "Total Revenue" in financials.index:
            revs = financials.loc["Total Revenue"].dropna()
            if len(revs) >= 2:
                rev_growth = float((revs.iloc[0] - revs.iloc[1]) / abs(revs.iloc[1]) * 100)
        return {
            "company_name":     info.get("longName", ticker),
            "sector":           info.get("sector", "N/A"),
            "market_cap_b":     round(info.get("marketCap", 0) / 1e9, 1),
            "pe_ratio":         info.get("trailingPE"),
            "forward_pe":       info.get("forwardPE"),
            "peg_ratio":        info.get("pegRatio"),
            "price_to_book":    info.get("priceToBook"),
            "profit_margin":    round(info.get("profitMargins", 0) * 100, 1) if info.get("profitMargins") else None,
            "operating_margin": round(info.get("operatingMargins", 0) * 100, 1) if info.get("operatingMargins") else None,
            "revenue_growth":   round(rev_growth, 1) if rev_growth else info.get("revenueGrowth"),
            "debt_to_equity":   info.get("debtToEquity"),
            "roe":              round(info.get("returnOnEquity", 0) * 100, 1) if info.get("returnOnEquity") else None,
            "current_ratio":    info.get("currentRatio"),
            "recommendation":   info.get("recommendationKey", "N/A"),
        }
    except Exception as e:
        return {"error": str(e), "company_name": ticker}


def analyze_with_gemini(ticker, headlines, fundamentals, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    headlines_text = "\n".join(f"- {h}" for h in headlines)
    fund_text = json.dumps(fundamentals, indent=2)
    prompt = f"""
You are a quantitative analyst specializing in behavioral finance and equity research.

Analyze the stock {ticker} ({fundamentals.get('company_name', ticker)}) based on:

## Recent News Headlines:
{headlines_text}

## Financial Fundamentals:
{fund_text}

Respond ONLY with valid JSON (no markdown, no backticks, no explanation outside the JSON):

{{
  "narrative_score": <integer 1-10>,
  "fundamentals_score": <integer 1-10>,
  "narrative_summary": "<2-3 sentence summary of what the market narrative is saying>",
  "fundamentals_summary": "<2-3 sentence summary of what the actual numbers show>",
  "gap_analysis": "<2-3 sentence analysis of the divergence between narrative and fundamentals>",
  "verdict": "<one of: STRONGLY HYPE-DRIVEN | HYPE-DRIVEN | BALANCED | FUNDAMENTALS-DRIVEN | STRONGLY FUNDAMENTALS-DRIVEN>",
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "investor_takeaway": "<1 sentence actionable takeaway>"
}}

Scoring:
- narrative_score: 1=very bearish sentiment, 5=neutral, 10=extreme hype
- fundamentals_score: 1=very weak, 5=average, 10=exceptionally strong
"""
    try:
        response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1024, messages=[{"role": "user", "content": prompt}])
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {"error": str(e)}


def make_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 16, "color": "white"}},
        number={"font": {"size": 40, "color": "white"}},
        gauge={
            "axis": {"range": [0, 10], "tickcolor": "white", "tickfont": {"color": "white"}},
            "bar": {"color": color},
            "bgcolor": "#1c1f26",
            "bordercolor": "#2e3140",
            "steps": [
                {"range": [0, 3],  "color": "#1a1d24"},
                {"range": [3, 7],  "color": "#1e2130"},
                {"range": [7, 10], "color": "#1c2240"},
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"}, height=250,
        margin=dict(t=60, b=20, l=20, r=20)
    )
    return fig


if analyze_btn and ticker_input:
    ticker = ticker_input.strip().upper()

    if not anthropic_key or not news_key:
        st.error("API keys missing from secrets.toml")
        st.stop()

    with st.spinner(f"Fetching fundamentals for {ticker}..."):
        fundamentals = fetch_fundamentals(ticker)

    if "error" in fundamentals:
        st.error(f"Could not fetch data for '{ticker}'. Check the ticker symbol.")
        st.stop()

    company_name = fundamentals.get("company_name", ticker)
    st.subheader(f"Analysis: {company_name} ({ticker})")

    with st.spinner("Fetching news headlines..."):
        headlines = fetch_news(ticker, company_name, news_key)

    with st.spinner("Running Anthropic AI analysis..."):
        result = analyze_with_gemini(ticker, headlines, fundamentals, anthropic_key)

    if "error" in result:
        st.error(f"AI analysis failed: {result['error']}")
        st.stop()

    n_score = result.get("narrative_score", 5)
    f_score = result.get("fundamentals_score", 5)
    gap     = n_score - f_score

    col1, col2, col3 = st.columns(3)
    with col1:
        st.plotly_chart(make_gauge(n_score, "📰 Narrative Score", "#f0a500"), use_container_width=True)
    with col2:
        st.plotly_chart(make_gauge(f_score, "📈 Fundamentals Score", "#00b4d8"), use_container_width=True)
    with col3:
        gap_color = "#ff4b4b" if gap > 2 else ("#2ecc71" if gap < -2 else "#aaaaaa")
        gap_label = "Narrative > Fundamentals" if gap > 0 else ("Fundamentals > Narrative" if gap < 0 else "Balanced")
        fig_gap = go.Figure(go.Indicator(
            mode="number+delta",
            value=n_score,
            delta={"reference": f_score, "valueformat": "+.0f",
                   "increasing": {"color": "#ff4b4b"}, "decreasing": {"color": "#2ecc71"}},
            title={"text": f"⚡ Gap Score<br><span style='font-size:12px;color:#aaa'>{gap_label}</span>",
                   "font": {"size": 16, "color": "white"}},
            number={"font": {"size": 40, "color": gap_color}},
        ))
        fig_gap.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "white"}, height=250,
            margin=dict(t=60, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_gap, use_container_width=True)

    verdict = result.get("verdict", "BALANCED")
    verdict_colors = {
        "STRONGLY HYPE-DRIVEN":         "#ff4b4b",
        "HYPE-DRIVEN":                  "#ff8c42",
        "BALANCED":                     "#aaaaaa",
        "FUNDAMENTALS-DRIVEN":          "#00b4d8",
        "STRONGLY FUNDAMENTALS-DRIVEN": "#2ecc71",
    }
    verdict_emoji = {
        "STRONGLY HYPE-DRIVEN":         "🔥",
        "HYPE-DRIVEN":                  "⚠️",
        "BALANCED":                     "⚖️",
        "FUNDAMENTALS-DRIVEN":          "✅",
        "STRONGLY FUNDAMENTALS-DRIVEN": "💎",
    }
    vcolor = verdict_colors.get(verdict, "#aaaaaa")
    vemoji = verdict_emoji.get(verdict, "📊")

    st.markdown(f"""
<div class="verdict-box" style="border-left-color: {vcolor};">
    <h2 style="color: {vcolor}; margin:0">{vemoji} {verdict}</h2>
    <p style="color:#ccc; margin-top:8px">{result.get('investor_takeaway', '')}</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📰 The Narrative")
        st.info(result.get("narrative_summary", ""))
        st.markdown("**Key Strengths**")
        for s in result.get("key_strengths", []):
            st.markdown(f"✅ {s}")
    with col2:
        st.markdown("### 📈 The Fundamentals")
        st.info(result.get("fundamentals_summary", ""))
        st.markdown("**Key Risks**")
        for r in result.get("key_risks", []):
            st.markdown(f"⚠️ {r}")

    st.markdown("### ⚡ Gap Analysis")
    st.warning(result.get("gap_analysis", ""))

    with st.expander("📋 Raw Fundamentals Data"):
        display_keys = {
            "sector": "Sector", "market_cap_b": "Market Cap ($B)",
            "pe_ratio": "P/E Ratio (TTM)", "forward_pe": "Forward P/E",
            "peg_ratio": "PEG Ratio", "price_to_book": "Price/Book",
            "profit_margin": "Profit Margin (%)", "operating_margin": "Operating Margin (%)",
            "revenue_growth": "Revenue Growth (%)", "debt_to_equity": "Debt/Equity",
            "roe": "Return on Equity (%)", "current_ratio": "Current Ratio",
            "recommendation": "Analyst Recommendation",
        }
        rows = [(v, fundamentals.get(k, "N/A")) for k, v in display_keys.items()]
        df = pd.DataFrame(rows, columns=["Metric", "Value"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("📰 News Headlines Analyzed"):
        for h in headlines:
            st.markdown(f"- {h}")

elif analyze_btn and not ticker_input:
    st.warning("Please enter a ticker symbol.")
