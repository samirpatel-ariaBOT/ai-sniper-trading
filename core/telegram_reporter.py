import requests
import sqlite3
from datetime import datetime

class TelegramReporter:
    def __init__(self):
        self.token = "8838588478:AAHixs1qXPPT0wb5y-GswXxBcO96oSbjJKI"
        self.chat_id = "851603753"
        self.offset = 0

    def send(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
        except Exception as e:
            print(f"Telegram send error: {e}")

    def check_commands(self, db_path):
        try:
            url = f"https://api.telegram.org/bot{self.token}/getUpdates"
            r = requests.get(url, params={"offset": self.offset, "timeout": 1}, timeout=5)
            data = r.json()
            if not data.get("ok"):
                return
            for update in data.get("result", []):
                self.offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                if text in ["/pnl", "/pln"]:
                    self._send_pnl(db_path)
        except Exception as e:
            print(f"Telegram command error: {e}")

    def _send_pnl(self, db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) FROM trades")
            total, pnl, wins = cur.fetchone()
            total = total or 0
            pnl = pnl or 0
            wins = wins or 0
            losses = total - wins
            wr = (wins / total * 100) if total else 0
            conn.close()
            equity = 10000 + pnl
            msg = (
                f"📊 PnL Report\n"
                f"Equity: ${equity:,.2f}\n"
                f"Total PnL: ${pnl:,.2f}\n"
                f"Trades: {total}\n"
                f"Wins: {wins} | Losses: {losses}\n"
                f"Win Rate: {wr:.1f}%"
            )
            self.send(msg)
        except Exception as e:
            self.send(f"Error reading PnL: {e}")
