"""
Nifty 50 Signal Dashboard — Final Version
==========================================
Tab 1: Intraday  — 5m + 15m RSI signals  (Nifty 50 auto-loaded)
Tab 2: Daily     — 6-month daily RSI      (any NSE stock)

Run locally:  streamlit run app.py
Deploy:       Push to GitHub → share.streamlit.io
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty Signal Dashboard",
    page_icon="📈",
    layout="centered",
)

# ──────────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0b0f1a; }
[data-testid="stHeader"]           { background: #0b0f1a; }
html, body, [class*="css"]         { font-family: 'Inter', sans-serif; color: #e2e8f0; }

/* metric cards */
[data-testid="metric-container"] {
    background: #111827 !important;
    border: 1px solid #1f2d45 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
}
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem !important; }
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: .72rem !important; letter-spacing: .08em; text-transform: uppercase; }

/* tabs */
[data-testid="stTabs"] button {
    font-size: .82rem !important;
    font-weight: 600 !important;
    letter-spacing: .04em !important;
    color: #64748b !important;
}
[data-testid="stTabs"] button[aria-selected="true"] { color: #e2e8f0 !important; }

/* signal box */
.sig-box {
    padding: 24px;
    border-radius: 14px;
    text-align: center;
    margin: 4px 0 20px;
}
.sig-call    { background: rgba(34,197,94,.12);  border: 2px solid #22c55e; }
.sig-put     { background: rgba(239,68,68,.12);  border: 2px solid #ef4444; }
.sig-neutral { background: rgba(245,158,11,.10); border: 2px solid #f59e0b; }

.sig-label { font-size: .68rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #64748b; margin-bottom: 6px; }
.sig-value { font-size: 2rem; font-weight: 700; }
.sig-call    .sig-value { color: #22c55e; }
.sig-put     .sig-value { color: #ef4444; }
.sig-neutral .sig-value { color: #f59e0b; }
.sig-sub { font-size: .78rem; color: #64748b; margin-top: 6px; }

/* section divider label */
.sec-label {
    font-size: .68rem; font-weight: 700; letter-spacing: .14em;
    text-transform: uppercase; color: #475569;
    border-bottom: 1px solid #1f2d45;
    padding-bottom: 8px; margin-bottom: 14px;
}

/* condition check box */
.cond-box {
    background: #111827; border: 1px solid #1f2d45;
    border-radius: 10px; padding: 12px 16px;
    font-size: .78rem; color: #94a3b8; line-height: 2;
    margin-top: 10px;
}

/* pill */
.pill { display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: .7rem; font-weight: 600; }
.pill-call    { background: rgba(34,197,94,.15);  color: #22c55e; border: 1px solid #22c55e; }
.pill-put     { background: rgba(239,68,68,.15);  color: #ef4444; border: 1px solid #ef4444; }
.pill-neutral { background: rgba(245,158,11,.12); color: #f59e0b; border: 1px solid #f59e0b; }

/* timestamp */
.ts { font-size: .7rem; color: #475569; text-align: right; }

/* legend */
.legend {
    background: #111827; border: 1px solid #1f2d45;
    border-radius: 12px; padding: 16px 20px;
    font-size: .78rem; color: #94a3b8; line-height: 1.8;
}
.legend strong { color: #e2e8f0; }

hr { border-color: #1f2d45 !important; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SHARED HELPERS
# ──────────────────────────────────────────────
def safe_float(x):
    """Convert any value to float safely — returns None on failure."""
    try:
        return float(x)
    except Exception:
        return None


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Standard RSI formula:
      gains/losses → rolling average → RS → 100 − 100/(1+RS)
    """
    delta    = close.diff()
    gain     = delta.where(delta > 0, 0)
    loss     = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def pill_html(call: bool, put: bool) -> str:
    if call: return '<span class="pill pill-call">🟢 CALL</span>'
    if put:  return '<span class="pill pill-put">🔴 PUT</span>'
    return '<span class="pill pill-neutral">🟡 NO TRADE</span>'


def signal_box(final: str):
    """Render the big coloured signal banner."""
    cfg = {
        "CALL":     ("sig-call",    "🟢 CALL",     "Both timeframes bullish — momentum confirmed"),
        "PUT":      ("sig-put",     "🔴 PUT",      "Both timeframes bearish — momentum confirmed"),
        "NO TRADE": ("sig-neutral", "🟡 NO TRADE", "Timeframes disagree — wait for a cleaner setup"),
    }
    cls, val, sub = cfg[final]
    st.markdown(f"""
    <div class="sig-box {cls}">
      <div class="sig-label">Final Signal</div>
      <div class="sig-value">{val}</div>
      <div class="sig-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def rsi_gauge(rsi: float):
    """Colour-coded progress bar from 0–100."""
    pct = min(max(int(rsi), 0), 100)
    st.progress(pct / 100)


def cond_box(rsi: float, rsi_ma: float):
    """Show which conditions are passing / failing."""
    diff       = rsi - rsi_ma
    above_ma   = "✅" if diff  > 0 else "❌"
    above_50   = "✅" if rsi  > 50 else "❌"
    direction  = "above" if diff > 0 else "below"
    side_50    = "above" if rsi > 50 else "below"
    st.markdown(f"""
    <div class="cond-box">
      {above_ma} RSI is <b>{direction}</b> MA20 &nbsp;
        (<code style='color:#cbd5e1'>{diff:+.2f}</code>)<br>
      {above_50} RSI is <b>{side_50}</b> 50
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# DATA FETCHERS  (cached to avoid re-fetching)
# ──────────────────────────────────────────────
def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance sometimes returns multi-level column headers like ("Close", "RELIANCE.NS").
    This flattens them to single-level ("Close") so the rest of the code works normally.
    Root cause: newer yfinance versions always return MultiIndex when group_by is default.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


@st.cache_data(ttl=60)   # refresh every 60 s
def fetch_intraday(symbol: str, interval: str) -> dict:
    """Download intraday data, compute RSI + MA, return signal dict."""
    df = yf.download(
        symbol,
        period="5d",
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise ValueError(f"No data for {symbol} @ {interval}")

    df = flatten_columns(df)                          # ← fix multi-level columns

    close          = df["Close"].squeeze()
    df["RSI"]      = calculate_rsi(close, 14)
    df["RSI_MA20"] = df["RSI"].rolling(20).mean()

    latest   = df.iloc[-1]
    prev_rsi = safe_float(df["RSI"].iloc[-2]) if len(df) > 1 else safe_float(latest["RSI"])
    rsi      = safe_float(latest["RSI"])
    rsi_ma   = safe_float(latest["RSI_MA20"])

    if rsi is None or rsi_ma is None:
        return {"rsi": None, "rsi_ma20": None, "call": False, "put": False, "delta": 0}

    return {
        "rsi":      round(rsi, 2),
        "rsi_ma20": round(rsi_ma, 2),
        "call":     (rsi > rsi_ma) and (rsi > 50),
        "put":      (rsi < rsi_ma) and (rsi < 50),
        "delta":    round(rsi - prev_rsi, 2) if prev_rsi else 0,
    }


@st.cache_data(ttl=60)
def fetch_daily(symbol: str) -> dict:
    """Download 6 months of daily data, compute RSI + MA."""
    df = yf.download(
        symbol,
        period="6mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        return {"rsi": None, "rsi_ma20": None, "call": False, "put": False, "df": None}

    df = flatten_columns(df)                          # ← fix multi-level columns

    # Fix duplicate timestamps (common NSE bug)
    df = df[~df.index.duplicated(keep="last")]

    close          = df["Close"].squeeze()
    df["RSI"]      = calculate_rsi(close, 14)
    df["RSI_MA20"] = df["RSI"].rolling(20).mean()

    latest = df.iloc[-1]
    rsi    = safe_float(latest["RSI"])
    rsi_ma = safe_float(latest["RSI_MA20"])

    if rsi is None or rsi_ma is None:
        return {"rsi": None, "rsi_ma20": None, "call": False, "put": False, "df": df}

    return {
        "rsi":      round(rsi, 2),
        "rsi_ma20": round(rsi_ma, 2),
        "call":     (rsi > rsi_ma) and (rsi > 50),
        "put":      (rsi < rsi_ma) and (rsi < 50),
        "df":       df,
    }


@st.cache_data(ttl=60)
def fetch_price(symbol: str) -> float | None:
    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")
        return round(float(data["Close"].iloc[-1]), 2) if not data.empty else None
    except Exception:
        return None


# ──────────────────────────────────────────────
# APP HEADER
# ──────────────────────────────────────────────
st.markdown("## 📈 Nifty Signal Dashboard")
st.markdown("<div style='color:#64748b;font-size:.8rem;margin-top:-12px;margin-bottom:20px;'>Live RSI momentum signals · Yahoo Finance · Auto-refreshes every 60 s</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────
tab_intraday, tab_daily = st.tabs(["⚡  Intraday (5m / 15m)", "📅  Daily (6-month)"])


# ══════════════════════════════════════════════
# TAB 1 — INTRADAY
# ══════════════════════════════════════════════
with tab_intraday:

    INTRADAY_SYMBOL = "^NSEI"   # Nifty 50

    col_hdr, col_btn = st.columns([4, 1])
    with col_hdr:
        st.markdown("#### Nifty 50 — ^NSEI")
    with col_btn:
        if st.button("⟳ Refresh", key="ref_intraday", use_container_width=True):
            st.cache_data.clear()

    # Fetch
    with st.spinner("Fetching live intraday data…"):
        try:
            tf5  = fetch_intraday(INTRADAY_SYMBOL, "5m")
            tf15 = fetch_intraday(INTRADAY_SYMBOL, "15m")
            price = fetch_price(INTRADAY_SYMBOL)

            if tf5["call"] and tf15["call"]:
                final = "CALL"
            elif tf5["put"] and tf15["put"]:
                final = "PUT"
            else:
                final = "NO TRADE"

            intraday_error = None
        except Exception as e:
            intraday_error = str(e)

    if intraday_error:
        st.error(f"⚠️ {intraday_error}")
    else:
        # Price + timestamp
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).strftime("%d %b %Y  %I:%M:%S %p IST")

        price_str = f"₹ {price:,.2f}" if price else "—"
        st.metric("Live Price", price_str)
        st.markdown(f"<div class='ts'>Last updated: {now}</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Big signal banner
        signal_box(final)

        # ── Two timeframe cards side by side ──────
        c5, c15 = st.columns(2)

        for col, tf, label in [(c5, tf5, "5-Minute"), (c15, tf15, "15-Minute")]:
            with col:
                st.markdown(f"<div class='sec-label'>{label} &nbsp; {pill_html(tf['call'], tf['put'])}</div>", unsafe_allow_html=True)

                if tf["rsi"] is None:
                    st.warning("RSI unavailable")
                else:
                    st.caption(f"RSI gauge — {tf['rsi']:.2f}  (0 ← 50 → 100)")
                    rsi_gauge(tf["rsi"])

                    m1, m2 = st.columns(2)
                    dc = "normal" if tf["delta"] >= 0 else "inverse"
                    m1.metric("RSI (14)",    f"{tf['rsi']:.2f}",    delta=f"{tf['delta']:+.2f}", delta_color=dc)
                    m2.metric("RSI MA (20)", f"{tf['rsi_ma20']:.2f}")

                    cond_box(tf["rsi"], tf["rsi_ma20"])

        st.markdown("---")
        st.markdown("""
        <div class="legend">
          <strong>Signal logic</strong><br>
          🟢 <strong>CALL</strong> — RSI above MA20 <em>and</em> above 50 on both timeframes<br>
          🔴 <strong>PUT</strong> &nbsp;— RSI below MA20 <em>and</em> below 50 on both timeframes<br>
          🟡 <strong>NO TRADE</strong> — Timeframes disagree or conditions unclear
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 2 — DAILY
# ══════════════════════════════════════════════
with tab_daily:

    st.markdown("#### Daily RSI Signal — Any NSE Stock")
    st.markdown("<div style='color:#64748b;font-size:.8rem;margin-bottom:16px;'>Uses 6 months of daily candles. Good for swing trade direction.</div>", unsafe_allow_html=True)

    # Symbol input
    col_sym, col_run = st.columns([3, 1])
    with col_sym:
        symbol = st.text_input(
            "Stock symbol (Yahoo Finance format)",
            value="RELIANCE.NS",
            placeholder="e.g. TCS.NS, HDFCBANK.NS, ^NSEI",
            label_visibility="collapsed",
        )
    with col_run:
        run = st.button("Analyze", key="run_daily", use_container_width=True)

    # Common NSE shortcuts
    st.caption("Quick picks: `RELIANCE.NS` · `TCS.NS` · `HDFCBANK.NS` · `INFY.NS` · `^NSEI` (Nifty 50)")

    if run and symbol:
        with st.spinner(f"Analyzing {symbol.upper()}…"):
            result = fetch_daily(symbol.upper())

        st.markdown("---")
        st.markdown(f"#### {symbol.upper()} — Daily")

        # Signal banner
        if result["rsi"] is None:
            st.warning("⚠️ RSI not available — not enough data or invalid symbol. Showing NO TRADE.")
            signal_box("NO TRADE")
        else:
            if result["call"]:
                sig = "CALL"
            elif result["put"]:
                sig = "PUT"
            else:
                sig = "NO TRADE"

            signal_box(sig)

            # Metrics
            m1, m2 = st.columns(2)
            m1.metric("RSI (14) — Daily",    f"{result['rsi']:.2f}")
            m2.metric("RSI MA (20) — Daily", f"{result['rsi_ma20']:.2f}")

            cond_box(result["rsi"], result["rsi_ma20"])

        # RSI chart
        if result["df"] is not None:
            st.markdown("---")
            st.markdown("<div class='sec-label'>RSI Trend — Last 6 Months (Daily)</div>", unsafe_allow_html=True)

            # Flatten multi-level columns if present (yfinance quirk)
            chart_df = result["df"][["RSI", "RSI_MA20"]].copy()
            chart_df.columns = ["RSI (14)", "RSI MA (20)"]
            chart_df = chart_df.dropna()

            st.line_chart(chart_df, color=["#3b82f6", "#f59e0b"])

            # Price chart
            st.markdown("<div class='sec-label'>Closing Price — Last 6 Months</div>", unsafe_allow_html=True)
            price_df = result["df"][["Close"]].copy()
            price_df.columns = ["Close Price"]
            price_df = price_df.dropna()
            st.line_chart(price_df, color=["#22c55e"])

        st.markdown("---")
        st.markdown("""
        <div class="legend">
          <strong>Daily signal logic</strong><br>
          🟢 <strong>CALL</strong> — Daily RSI above MA20 <em>and</em> above 50 — bullish trend on daily chart<br>
          🔴 <strong>PUT</strong> &nbsp;— Daily RSI below MA20 <em>and</em> below 50 — bearish trend on daily chart<br>
          🟡 <strong>NO TRADE</strong> — Mixed signals or insufficient data<br><br>
          <span style='color:#475569'>Tip: Use Daily tab to confirm the broader trend, then use Intraday tab to time the entry.</span>
        </div>
        """, unsafe_allow_html=True)
