import streamlit as st
import ccxt
import pandas as pd
import sqlite3
import time
import json
import os
from datetime import datetime, timezone

st.set_page_config(page_title="AI Sniper Trading", layout="wide")
st.title("AI SNIPER TRADING")
st.caption("Control Room - MEXC Futures")

@st.cache_resource
def get_ex():
    return ccxt.mexc({"enableRateLimit": True, "options": {"defaultType": "swap"}})

ex = get_ex()

# Load closed trades
try:
    conn = sqlite3.connect("data/trades.db")
    trades = pd.read_sql("SELECT * FROM trades ORDER BY id DESC", conn)
    conn.close()
    total = len(trades)
    pnl = trades["net_pnl"].sum() if total else 0
    wins = len(trades[trades["net_pnl"] > 0]) if total else 0
    wr = (wins / total * 100) if total else 0
    fees_paid = trades["fees"].sum() if total else 0
except Exception as e:
    st.error(str(e))
    total = pnl = wr = fees_paid = 0
    trades = pd.DataFrame()

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Equity", f"${10000 + pnl:,.2f}")
c2.metric("Net PnL", f"${pnl:,.2f}")
c3.metric("Trades", total)
c4.metric("Win Rate", f"{wr:.1f}%")

st.divider()

# Live Open Positions
st.subheader("Open Positions")
open_file = "data/open_positions.json"
if os.path.exists(open_file):
    try:
        with open(open_file) as f:
            open_pos = json.load(f)
        if open_pos:
            op_df = pd.DataFrame(open_pos)
            cols = [c for c in ["symbol", "direction", "size", "entry_price", "stop_price", "highest_favorable"] if c in op_df.columns]
            st.dataframe(op_df[cols], width='stretch', hide_index=True)
        else:
            st.info("No open positions")
    except Exception as e:
        st.warning(f"Could not read open positions: {e}")
else:
    st.info("No open positions file yet")

st.divider()

# Agents
st.subheader("Agents")
a1, a2, a3, a4, a5 = st.columns(5)
a1.metric("Scout", "Active")
a2.metric("Oracle", "Active")
a3.metric("Risk", "Active")
a4.metric("Decision", "Active")
a5.metric("StopMonitor", "Active")

st.divider()

# Top Movers
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
            st.dataframe(df.head(5), width='stretch', hide_index=True)
        with col2:
            st.write("Losers")
            st.dataframe(df.tail(5).iloc[::-1], width='stretch', hide_index=True)
except Exception as e:
    st.warning(str(e)[:80])

st.divider()

# Equity Curve
st.subheader("Equity Curve")
if total > 0 and "net_pnl" in trades.columns and "exit_time" in trades.columns:
    eq = trades.sort_values("exit_time").copy()
    eq["equity"] = 10000 + eq["net_pnl"].cumsum()
    st.line_chart(eq.set_index("exit_time")["equity"])
    current = eq["equity"].iloc[-1]
    color = "green" if current >= 10000 else "red"
    st.markdown(f"**Current Equity:** <span style='color:{color}'>${current:,.2f}</span>", unsafe_allow_html=True)
else:
    st.info("No trades yet for equity curve")

# Fees
if total > 0:
    st.metric("Fees Paid", f"${fees_paid:,.2f}")
    st.metric("Net Capital", f"${10000 + pnl:,.2f}")

st.divider()

# Trade History
st.subheader("Trade History")
if total > 0:
    cols = [c for c in ["symbol", "direction", "entry_price", "exit_price", "net_pnl", "fees"] if c in trades.columns]
    st.dataframe(trades[cols].head(20), width='stretch', hide_index=True)
else:
    st.info("No closed trades yet")

st.caption(datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))

time.sleep(8)
st.rerun()
