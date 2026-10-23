import streamlit as st
import ccxt
import pandas as pd
import sqlite3
import time
from datetime import datetime

st.set_page_config(page_title="AI Sniper Trading", layout="wide")
st.title("AI SNIPER TRADING")
st.caption("Control Room - MEXC Futures")

@st.cache_resource
def get_ex():
    return ccxt.mexc({"enableRateLimit": True, "options": {"defaultType": "swap"}})
ex = get_ex()

try:
    conn = sqlite3.connect("data/trades.db")
    trades = pd.read_sql("SELECT * FROM trades ORDER BY id DESC", conn)
    conn.close()
    total = len(trades)
    pnl = trades["pnl"].sum() if total else 0
    wins = len(trades[trades["pnl"] > 0]) if total else 0
    wr = (wins / total * 100) if total else 0
except:
    total = pnl = wr = 0
    trades = pd.DataFrame()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Equity", f"${10000 + pnl:,.2f}")
c2.metric("PnL", f"${pnl:,.2f}")
c3.metric("Trades", total)
c4.metric("Win Rate", f"{wr:.1f}%")

st.divider()
st.subheader("Agents")
a1, a2, a3, a4, a5 = st.columns(5)
a1.metric("Scout", "Active")
a2.metric("Oracle", "Active")
a3.metric("Risk", "Active")
a4.metric("Decision", "Active")
a5.metric("OrderBook", "Active")

st.divider()
st.subheader("Top Movers")
try:
    tickers = ex.fetch_tickers()
    movers = []
    for s, t in tickers.items():
        if s.endswith(":USDT") and (t.get("quoteVolume") or 0) > 500000:
            movers.append({"Symbol": s, "%": round(t.get("percentage") or 0, 1)})
    if movers:
        df = pd.DataFrame(movers).sort_values("%", ascending=False)
        col1, col2 = st.columns(2)
        with col1:
            st.write("Gainers")
            st.dataframe(df.head(5), use_container_width=True, hide_index=True)
        with col2:
            st.write("Losers")
            st.dataframe(df.tail(5).iloc[::-1], use_container_width=True, hide_index=True)
except Exception as e:
    st.warning(str(e)[:60])

st.divider()
st.subheader("Equity Curve")
if total > 0 and "pnl" in trades.columns:
    eq = trades.sort_values("id").copy()
    eq["equity"] = 10000 + eq["pnl"].cumsum()
    st.line_chart(eq.set_index("id")["equity"])
    current = eq["equity"].iloc[-1]
    color = "green" if current >= 10000 else "red"
    st.markdown(f"**Current Equity:** <span style='color:{color}'>${current:,.2f}</span>", unsafe_allow_html=True)
else:
    st.info("No trades yet for equity curve")

if total > 0 and "size" in trades.columns and "entry_price" in trades.columns:
    fee_rate = 0.0004
    notional = (trades["size"] * trades["entry_price"]).sum()
    est_fees = notional * fee_rate
    st.metric("Est. Fees Paid", f"${est_fees:,.2f}")
    st.metric("Net Capital", f"${10000 + pnl - est_fees:,.2f}")

st.divider()
st.subheader("Trade History")
if total > 0:
    st.dataframe(trades[["symbol","direction","entry_price","exit_price","pnl"]].head(15), use_container_width=True, hide_index=True)
else:
    st.info("No closed trades yet")

st.caption(datetime.utcnow().strftime("%H:%M:%S UTC"))
time.sleep(8)
st.rerun()

