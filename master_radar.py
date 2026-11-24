import pandas as pd, datetime, feedparser, requests, os, re, logging, time
import yfinance as yf
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

def send_telegram(msg):
    try:
        chunks = [msg[i:i+3800] for i in range(0, len(msg), 3800)]
        for i, chunk in enumerate(chunks):
            text = chunk if len(chunks) == 1 else f"<b>Part {i+1}/{len(chunks)}</b>\n\n{chunk}"
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"}, timeout=15)
            time.sleep(1)
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

try:
    print("🔄 Starting Simplified Test...")
    
    # SIRF 10 STOCKS FOR TESTING
    stocks = {
        "TATA_STEEL": "TATASTEEL", "JSW_STEEL": "JSWSTEEL", "ACC": "ACC",
        "HDFC_BANK": "HDFCBANK", "HAL": "HAL", "L&T": "LT",
        "M&M": "M&M", "RELIANCE": "RELIANCE", "TCS": "TCS", "SBI": "SBIN"
    }
    
    def get_stock_data(symbol):
        try:
            time.sleep(0.3)
            df = yf.download(f"{symbol}.NS", period="3mo", progress=False)
            if df.empty or len(df) < 20: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            cp = round(float(df['Close'].iloc[-1]), 2)
            sma20 = round(float(df['Close'].rolling(20).mean().iloc[-1]), 2)
            
            sig = "BUY/ADD" if cp > sma20 else "SELL/AVOID"
            
            return {"Name": symbol, "Price": cp, "Signal": sig}
        except Exception as e:
            print(f"❌ Error for {symbol}: {str(e)[:50]}")
            return None
    
    market_data = [d for n, s in stocks.items() if (d := get_stock_data(s))]
    df_stocks = pd.DataFrame(market_data)
    
    # SIMPLE MESSAGE
    msg = f"<b>🔥 TEST RADAR</b> ({datetime.datetime.now().strftime('%d-%b %I:%M %p')})\n\n"
    
    if not df_stocks.empty:
        msg += "<b>🟢 BUY/ADD:</b>\n"
        for _, r in df_stocks[df_stocks["Signal"] == "BUY/ADD"].iterrows():
            msg += f"• <b>{r['Name']}</b> @ ₹{r['Price']}\n"
        
        msg += "\n<b>🔴 SELL/AVOID:</b>\n"
        for _, r in df_stocks[df_stocks["Signal"] == "SELL/AVOID"].iterrows():
            msg += f"• <b>{r['Name']}</b> @ ₹{r['Price']}\n"
    else:
        msg += "<b>⚠️ No Data Fetched</b>\n"
    
    msg += "\n<b>✅ Test Complete</b>"
    
    send_telegram(msg)
    print("✅ Script completed successfully!")

except Exception as e:
    error_msg = f"🚨 <b>SYSTEM CRASHED!</b>\n\nError: <code>{str(e)}</code>"
    print(error_msg)
    send_telegram(error_msg)
