import pandas as pd, datetime, feedparser, requests, os, re, logging, time, random
import yfinance as yf
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

# === 1. TELEGRAM CHUNKING FIX ===
def send_telegram(msg):
    try:
        chunks = [msg[i:i+3800] for i in range(0, len(msg), 3800)]
        for i, chunk in enumerate(chunks):
            text = chunk if len(chunks) == 1 else f"<b>Part {i+1}/{len(chunks)}</b>\n\n{chunk}"
            # No HTML parse mode to prevent silent drops on special chars
            r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              data={"chat_id": TG_CHAT, "text": text}, timeout=15)
            print(f"Chunk {i+1} Status: {r.status_code}")
            time.sleep(1)
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

# === 2. AFFORDABLE & STRONG STOCK POOL (Under ₹1500 + High Liquidity) ===
AFFORDABLE_POOL = [
    "ZOMATO", "IRFC", "SUZLON", "NHPC", "TATAPOWER", "YESBANK", "PNB", "BANKBARODA", 
    "CANBK", "UCOBANK", "ITC", "TATAMOTORS", "UPL", "RENUKA", "KRBL", "DALMIASUG", 
    "GAIL", "ONGC", "OIL", "RATNAMANI", "APOLLOPIPE", "KEC", "BALRAMCHIN", "SENCO", 
    "RAJESHEXPO", "KALYANKJIL", "MARICO", "PATANJALI", "VBL", "TATACONSUM", "DIXON", 
    "KAYNES", "CGPOWER", "RVNL", "BEL", "M&M", "SBIN", "ICICIBANK", "HDFCBANK", "ACC", 
    "JSWSTEEL", "TATASTEEL", "VEDL", "HINDALCO", "SAIL", "NMDC", "GODREJAGRO", "LTFOODS"
]

def get_stock_data(symbol):
    try:
        time.sleep(random.uniform(0.3, 0.8))
        df = yf.download(f"{symbol}.NS", period="6mo", progress=False)
        if df.empty or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        cp = round(float(df['Close'].iloc[-1]), 2)
        
        # FILTER 1: Budget Friendly (Max ₹1500)
        if cp > 1500: return None
        
        sma20 = round(float(df['Close'].rolling(20).mean().iloc[-1]), 2)
        sma50 = round(float(df['Close'].rolling(50).mean().iloc[-1]), 2)
        
        tr = abs(df['High'] - df['Low']).tail(14).mean()
        atr = float(tr) if not pd.isna(tr) else cp * 0.02
        sl = round(cp - (2 * atr), 2)
        tgt = round(cp + (3 * atr), 2)
        
        sig = "HOLD"
        if cp > sma20 > sma50: sig = "BUY"
        elif cp < sma20: sig = "AVOID"
        
        curr = df.iloc[-1]
        body = abs(float(curr['Close']) - float(curr['Open']))
        rng = float(curr['High']) - float(curr['Low'])
        pat = "Normal Price Action"
        if rng > 0 and (body / rng) < 0.15: pat = "Market Confused (Doji)"
        elif (min(float(curr['Open']), float(curr['Close'])) - float(curr['Low'])) > (2 * body): pat = "Gira tha, ab uthne wala (Hammer)"
        
        # FILTER 2: Smart Money Check (Volume + Delivery Proxy)
        avg_vol = df['Volume'].tail(10).mean()
        today_vol = df['Volume'].iloc[-1]
        stealth = "Bade log chupchap khareed rahe hain" if today_vol > (avg_vol * 1.5) else "Normal activity"
        
        # FILTER 3: Only show strong setups
        if sig != "BUY" and pat == "Normal Price Action":
            return None
            
        # Position Sizing for ₹2000 Profit
        profit_per_share = tgt - cp
        risk_per_share = cp - sl
        shares_for_target = int(2000 / profit_per_share) if profit_per_share > 0 else 0
        max_loss = int(shares_for_target * risk_per_share) if shares_for_target > 0 else 0
        
        return {
            "Name": symbol, "Price": cp, "Pattern": pat, "Stealth": stealth, 
            "SL": sl, "Target": tgt, "Shares": shares_for_target, "MaxLoss": max_loss
        }
    except:
        return None

try:
    print("🔄 Scanning Market Ocean for Affordable Gems...")
    
    market_data = [d for s in AFFORDABLE_POOL if (d := get_stock_data(s))]
    market_data.sort(key=lambda x: x['Price'])
    top_picks = market_data[:5]
    
    msg = "<b>🌊 SAMUNDAR SE NIKLE HAIN YE HEERE (Affordable & Strong)</b>\n\n"
    msg += "<i>Note: Sirf wo shares dikhaye gaye hain jo ₹1500 se kam ke hain aur jinke upar jaane ke strong chances hain.</i>\n\n"
    
    if not top_picks:
        msg += "<b>⚠️ Aaj koi strong sasta mauka nahi mila.</b>\n"
        msg += "Market thoda weak hai. Cash bacha kar rakho, zabardasti trade mat lo.\n\n"
    else:
        for r in top_picks:
            msg += f"🔥 <b>{r['Name']}</b> (Current Price: ₹{r['Price']})\n"
            msg += f"💡 <b>Kyun?</b> {r['Pattern']} aur {r['Stealth']}.\n"
            msg += f"🎯 <b>Target:</b> ₹{r['Target']} | 🛑 <b>Stop Loss:</b> ₹{r['SL']}\n"
            msg += f"💰 <b>₹2000 Profit ke liye:</b> <b>{r['Shares']}</b> shares lo.\n"
            msg += f"⚠️ <b>Max Nuksan (agar SL hit hua):</b> ₹{r['MaxLoss']}\n"
            msg += f"🔗 <a href='https://www.screener.in/company/{r['Name']}/'>Screener Link</a>\n\n"

    # === ADDING BACK MACRO & NEWS FOR FULL CONTEXT ===
    macro_assets = {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE_OIL": "CL=F", "USD_INR": "USDINR=X"}
    macro_msg = ""
    for name, ticker in macro_assets.items():
        try:
            hist = yf.download(ticker, period="1mo", progress=False)["Close"]
            cl = hist.iloc[:, 0] if isinstance(hist, pd.DataFrame) else hist
            mom = ((float(cl.iloc[-1]) / float(cl.iloc[-5])) - 1) * 100
            trend = "📈 UP" if mom > 0 else "📉 DOWN"
            macro_msg += f"• {name}: {round(mom, 1)}% {trend}\n"
        except: pass
    
    if macro_msg:
        msg += "<b>🌍 GLOBAL CUES:</b>\n" + macro_msg + "\n"

    msg += "<b>💡 DOST KI SALAH:</b>\n"
    msg += "1. Kabhi bhi apne ₹50,000 mein se ek trade mein ₹10,000 se zyada mat lagana.\n"
    msg += "2. Stop Loss (SL) hit hote hi bech dena, 'wapas upar aayega' mat sochna.\n"
    msg += "3. Ye system suggestion hai, final decision tumhara hai. Safe raho!"
    
    send_telegram(msg)
    print("✅ Done! Message sent.")

except Exception as e:
    error_msg = f"🚨 <b>SYSTEM CRASHED!</b>\nError: <code>{str(e)}</code>"
    print(error_msg)
    send_telegram(error_msg)
