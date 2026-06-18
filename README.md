# 📈 Nifty Signal Dashboard

A clean, two-tab trading signal dashboard built with Streamlit.

| Tab | What it does |
|-----|-------------|
| ⚡ **Intraday** | Live 5m + 15m RSI signals for Nifty 50 — auto-loads on open |
| 📅 **Daily** | 6-month daily RSI signal for any NSE stock you type in |

---

## 🚀 Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Deploy free on Streamlit Cloud

1. Push this folder to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, set main file to `app.py`
4. Hit **Deploy** — you get a public URL instantly

---

## 📊 Signal logic

**CALL** → RSI (14) above RSI MA(20) and above 50
**PUT** → RSI (14) below RSI MA(20) and below 50
**NO TRADE** → conditions not clearly met

Intraday: both 5m AND 15m must agree for a signal
Daily: single timeframe confirmation for swing trade direction

---

## 💡 Pro tip

Use the **Daily tab** to confirm the broader trend direction, then use the **Intraday tab** to time your entry.

---

> ⚠️ For educational purposes only. Not financial advice.
