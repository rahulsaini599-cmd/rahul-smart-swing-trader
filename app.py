import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json, os
from datetime import datetime, date

st.set_page_config(page_title="Rahul Smart Swing Trader", page_icon="📈", layout="wide")

CAPITAL = 10000.0
RISK_PER_TRADE = 50.0
MAX_POSITION_VALUE = 2500.0
MAX_POSITIONS = 2
DAILY_LOSS_LIMIT = 100.0
WEEKLY_LOSS_LIMIT = 250.0
STATE_FILE = "paper_state.json"

# Nifty 50 Yahoo Finance symbols. Review/update this list periodically as index constituents change.
NIFTY50 = [
    "ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK",
    "BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL",
    "CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL",
    "GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO",
    "HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY",
    "ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT",
    "M&M","MARUTI","NESTLEIND","NTPC","ONGC",
    "POWERGRID","RELIANCE","SBILIFE","SBIN","SHRIRAMFIN",
    "SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS",
    "TECHM","TITAN","TRENT","ULTRACEMCO","WIPRO"
]
TICKERS = [s + ".NS" for s in NIFTY50]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cash": CAPITAL, "positions": {}, "trades": [], "realized_pnl": 0.0, "start_date": str(date.today())}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def calc_indicators(df):
    df = df.copy().dropna()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["VOL20"] = df["Volume"].rolling(20).mean()
    df["VOL_RATIO"] = df["Volume"] / df["VOL20"]
    df["EMA50_UP"] = df["EMA50"] > df["EMA50"].shift(5)
    df["BUY_SIGNAL"] = (
        (df["Close"] > df["EMA20"]) &
        (df["EMA20"] > df["EMA50"]) &
        (df["RSI"].between(55, 68)) &
        (df["VOL_RATIO"] > 1.0) &
        (df["EMA50_UP"])
    )
    return df

@st.cache_data(ttl=900, show_spinner=False)
def fetch_data(period="1y"):
    raw = yf.download(TICKERS, period=period, interval="1d", group_by="ticker",
                      auto_adjust=False, progress=False, threads=True)
    data = {}
    if raw is None or raw.empty:
        return data
    for sym in NIFTY50:
        ticker = sym + ".NS"
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                d = raw[ticker].copy()
            else:
                if len(NIFTY50) == 1:
                    d = raw.copy()
                else:
                    continue
            d = d.dropna(subset=["Close"])
            if len(d) >= 60:
                data[sym] = calc_indicators(d)
        except Exception:
            continue
    return data

def current_pnl(state, prices):
    total = 0.0
    for sym, p in state["positions"].items():
        px = prices.get(sym, p["entry"])
        total += (px - p["entry"]) * p["qty"]
    return total

st.title("📈 Rahul Smart Swing Trader")
st.caption("Nifty 50 • Fully automatic PAPER trading • Groww live orders disabled")
st.warning("यह लोकल पेपर-ट्रेडिंग प्रोटोटाइप है। Yahoo Finance डेटा अनौपचारिक/विलंबित हो सकता है; यह Groww से कनेक्ट नहीं है और कोई वास्तविक ऑर्डर नहीं भेजता।")

state = load_state()
with st.sidebar:
    st.header("सेटिंग्स")
    st.metric("शुरुआती वर्चुअल पूंजी", "₹10,000")
    st.metric("प्रति ट्रेड अधिकतम जोखिम", "₹50")
    st.metric("अधिकतम पोजीशन", "2")
    st.metric("प्रति शेयर अधिकतम निवेश", "₹2,500")
    period = st.selectbox("डेटा अवधि", ["1y", "2y"], index=0)
    refresh = st.button("🔄 डेटा रीफ्रेश करें")
    if refresh:
        fetch_data.clear()

if "market_data" not in st.session_state or refresh:
    with st.spinner("Nifty 50 का दैनिक डेटा डाउनलोड हो रहा है..."):
        st.session_state.market_data = fetch_data(period)

data = st.session_state.market_data
if not data:
    st.error("डेटा नहीं मिला। इंटरनेट कनेक्शन जांचें और फिर डेटा रीफ्रेश करें। Yahoo Finance कभी-कभी अनुरोध सीमित कर सकता है।")
    st.stop()

latest_prices = {}
rows = []
for sym, df in data.items():
    last = df.iloc[-1]
    latest_prices[sym] = float(last["Close"])
    rows.append({
        "Symbol": sym, "Close": round(float(last["Close"]), 2),
        "EMA20": round(float(last["EMA20"]), 2), "EMA50": round(float(last["EMA50"]), 2),
        "RSI": round(float(last["RSI"]), 1),
        "Volume Ratio": round(float(last["VOL_RATIO"]), 2) if pd.notna(last["VOL_RATIO"]) else np.nan,
        "Signal": "BUY" if bool(last["BUY_SIGNAL"]) else "WAIT",
        "Date": str(df.index[-1].date())
    })
scan = pd.DataFrame(rows).sort_values(["Signal", "RSI"], ascending=[True, False])
open_pnl = current_pnl(state, latest_prices)
equity = state["cash"] + sum(p["qty"] * latest_prices.get(s, p["entry"]) for s,p in state["positions"].items())
c1,c2,c3,c4 = st.columns(4)
c1.metric("वर्चुअल इक्विटी", f"₹{equity:,.2f}")
c2.metric("उपलब्ध कैश", f"₹{state['cash']:,.2f}")
c3.metric("ओपन पोजीशन", f"{len(state['positions'])}/2")
c4.metric("ओपन P/L", f"₹{open_pnl:,.2f}")

st.subheader("1. Nifty 50 Scanner")
st.caption("BUY = सभी तकनीकी शर्तें पास। यह खरीदने की गारंटी या सलाह नहीं है।")
buy_rows = scan[scan["Signal"] == "BUY"]
st.dataframe(scan, use_container_width=True, hide_index=True)
st.write(f"**आज के तकनीकी BUY संकेत: {len(buy_rows)}**")

st.subheader("2. स्वचालित पेपर ट्रेडिंग")
st.info("सुरक्षित परीक्षण: यह ऐप सिग्नल के दिन के Close पर काल्पनिक एंट्री मानता है। वास्तविक निष्पादन में अगले सत्र का भाव अलग हो सकता है।")
colA, colB = st.columns(2)
with colA:
    if st.button("▶️ BUY संकेतों पर पेपर ट्रेड चलाएं", type="primary"):
        day_key = str(date.today())
        existing_today = {t.get("signal_date") for t in state["trades"] if t.get("side") == "BUY"}
        added = []
        for _, r in buy_rows.iterrows():
            sym = r["Symbol"]
            if len(state["positions"]) >= MAX_POSITIONS:
                break
            if sym in state["positions"] or day_key in existing_today:
                continue
            df = data[sym]
            last = df.iloc[-1]
            entry = float(last["Close"])
            # 2% initial stop; position size is limited by both ₹50 risk and ₹2,500 notional.
            stop = entry * 0.98
            per_share_risk = entry - stop
            qty_risk = int(RISK_PER_TRADE // per_share_risk) if per_share_risk > 0 else 0
            qty_value = int(MAX_POSITION_VALUE // entry)
            qty_cash = int(state["cash"] // entry)
            qty = min(qty_risk, qty_value, qty_cash)
            if qty < 1:
                continue
            cost = qty * entry
            if cost > state["cash"]:
                continue
            state["cash"] -= cost
            state["positions"][sym] = {
                "entry": entry, "stop": stop, "target": entry + 2 * per_share_risk,
                "qty": qty, "entry_date": day_key
            }
            state["trades"].append({
                "date": day_key, "signal_date": day_key, "symbol": sym, "side": "BUY",
                "price": entry, "qty": qty, "stop": stop, "target": entry + 2*per_share_risk,
                "note": "Paper entry at signal-day close"
            })
            added.append(sym)
            existing_today.add(day_key)
        save_state(state)
        st.success(f"पेपर एंट्री: {', '.join(added) if added else 'कोई नई एंट्री नहीं हुई।'}")
        st.rerun()
with colB:
    if st.button("⏹️ सभी ओपन पोजीशन पेपर में बंद करें"):
        for sym, p in list(state["positions"].items()):
            px = latest_prices.get(sym, p["entry"])
            proceeds = p["qty"] * px
            pnl = (px - p["entry"]) * p["qty"]
            state["cash"] += proceeds
            state["realized_pnl"] += pnl
            state["trades"].append({"date": str(date.today()), "symbol": sym, "side": "SELL",
                                    "price": px, "qty": p["qty"], "pnl": pnl, "note": "Manual paper close"})
            del state["positions"][sym]
        save_state(state)
        st.success("सभी पेपर पोजीशन बंद कर दी गईं।")
        st.rerun()

# Check stops/targets using latest daily low/high; if both touched on same candle, assume stop first (conservative).
exits = []
for sym, p in list(state["positions"].items()):
    if sym not in data:
        continue
    last = data[sym].iloc[-1]
    low, high = float(last["Low"]), float(last["High"])
    exit_price, reason = None, None
    if low <= p["stop"]:
        exit_price, reason = p["stop"], "Stop Loss"
    elif high >= p["target"]:
        exit_price, reason = p["target"], "Target"
    if exit_price is not None:
        proceeds = p["qty"] * exit_price
        pnl = (exit_price - p["entry"]) * p["qty"]
        state["cash"] += proceeds
        state["realized_pnl"] += pnl
        state["trades"].append({"date": str(date.today()), "symbol": sym, "side": "SELL",
                                "price": exit_price, "qty": p["qty"], "pnl": pnl, "note": reason})
        del state["positions"][sym]
        exits.append(f"{sym}: {reason} (₹{pnl:.2f})")
if exits:
    save_state(state)
    st.warning("स्वचालित पेपर एग्जिट: " + " | ".join(exits))

st.subheader("3. Open Positions")
if state["positions"]:
    pos_rows = []
    for sym,p in state["positions"].items():
        px = latest_prices.get(sym, p["entry"])
        pos_rows.append({"Symbol":sym, "Qty":p["qty"], "Entry":round(p["entry"],2),
                         "Latest Close":round(px,2), "Stop":round(p["stop"],2),
                         "Target":round(p["target"],2), "Unrealized P/L":round((px-p["entry"])*p["qty"],2)})
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)
else:
    st.write("अभी कोई ओपन पेपर पोजीशन नहीं है।")

st.subheader("4. Trade History")
if state["trades"]:
    hist = pd.DataFrame(state["trades"])
    st.dataframe(hist, use_container_width=True, hide_index=True)
    st.download_button("⬇️ ट्रेड हिस्ट्री CSV डाउनलोड करें", hist.to_csv(index=False).encode("utf-8-sig"),
                       "rahul_swing_trade_history.csv", "text/csv")
else:
    st.write("अभी कोई ट्रेड रिकॉर्ड नहीं है।")

st.subheader("5. Risk & Safety")
st.write(f"- Realized P/L: **₹{state['realized_pnl']:.2f}**")
st.write(f"- Open P/L: **₹{open_pnl:.2f}**")
st.write("- Daily loss stop और weekly loss stop अभी निगरानी/डैशबोर्ड नियम हैं; यह प्रोटोटाइप स्वचालित रूप से पूरे दिन के नए ट्रेड रोकने का पूर्ण नियंत्रण नहीं देता।")
st.write("- ऐप को दिन में कम-से-कम एक बार रीफ्रेश करना होगा; यह लगातार 24×7 बैकग्राउंड में नहीं चलता।")
st.caption("डेटा स्रोत: Yahoo Finance (yfinance). Nifty 50 सूची ऐप में स्थिर रखी गई है; समय-समय पर आधिकारिक सूची से मिलान करें। यह निवेश सलाह नहीं है।")
