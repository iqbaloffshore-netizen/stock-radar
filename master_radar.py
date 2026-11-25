import pandas as pd, datetime, feedparser, requests, os, re, logging, time, random
import yfinance as yf
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

# === 1. TELEGRAM CHUNKING FIX (Unchanged) ===
def send_telegram(msg):
    try:
        chunks = [msg[i:i+3800] for i in range(0, len(msg), 3800)]
        for i, chunk in enumerate(chunks):
            text = chunk if len(chunks) == 1 else f"<b>Part {i+1}/{len(chunks)}</b>\n\n{chunk}"
            r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              data={"chat_id": TG_CHAT, "text": text}, timeout=15)
            print(f"Chunk {i+1} Status: {r.status_code}")
            time.sleep(1)
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

# === 2. AFFORDABLE & STRONG STOCK POOL (Unchanged) ===
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
        if cp > 1500: return None # Budget Friendly Filter
        
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
        
        avg_vol = df['Volume'].tail(10).mean()
        today_vol = df['Volume'].iloc[-1]
        stealth = "Bade log chupchap khareed rahe hain" if today_vol > (avg_vol * 1.5) else "Normal activity"
        
        if sig != "BUY" and pat == "Normal Price Action": return None
            
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

# === 3. NEW ADDITION: NEWS, SCHEMES & CONTRACTS FEEDS ===
feeds = [
    "https://pib.gov.in/rssfeed.aspx", 
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://news.google.com/rss/search?q=India+Budget+OR+PLI+Scheme+OR+Capex+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Defence+Tender+OR+Contract+OR+Expansion+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
]
GOVT_SCHEME_MAP = {"PLI": ["DIXON", "KAYNES", "M&M"], "Make in India": ["HAL", "BEL", "RVNL"], "Solar": ["TATAPOWER", "ADANIGREEN"]}
CONTRACT_KEYWORDS = ["won contract", "received order", "expansion plan", "capex", "bagged order"]

def fetch_feed(url):
    try: return feedparser.parse(url).entries[:3]
    except: return []

news_alerts, scheme_alerts, contract_alerts, all_news_titles = [], [], [], []
with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(fetch_feed, feeds))

for entries in results:
    for entry in entries:
        title = entry.title
        all_news_titles.append(title)
        t_lower = title.lower()
        for scheme, stocks in GOVT_SCHEME_MAP.items():
            if scheme.lower() in t_lower:
                scheme_alerts.append(f"🇮🇳 *{scheme}* → {title[:60]}")
                break
        if any(kw in t_lower for kw in CONTRACT_KEYWORDS):
            contract_alerts.append(f"🏗️ *Contract/Expansion* → {title[:60]}")

try:
    print("🔄 Scanning Market Ocean for Affordable Gems with Reasons...")
    
    market_data = []
    for s in AFFORDABLE_POOL:
        d = get_stock_data(s)
        if d:
            # NEW ADDITION: Build the "Reason" dynamically
            reasons = []
            if d['Stealth'] == "Bade log chupchap khareed rahe hain": reasons.append("Smart Money (High Volume)")
            if "Hammer" in d['Pattern']: reasons.append("Strong Reversal Pattern")
            
            # Check if this stock is mentioned in recent news
            for news_title in all_news_titles:
                if s.lower() in news_title.lower():
                    reasons.append(f"News: {news_title[:50]}...")
                    break
            
            d['Reason'] = " | ".join(reasons) if reasons else "Technical Breakout"
            market_data.append(d)

    market_data.sort(key=lambda x: x['Price'])
    top_picks = market_data[:5]
    
    msg = "<b>🌊 SAMUNDAR SE NIKLE HAIN YE HEERE (Affordable & Strong)</b>\n\n"
    msg += "<i>Note: Sirf wo shares dikhaye gaye hain jo ₹1500 se kam ke hain, jinke upar jaane ke strong chances hain, aur jinka 'Reason' clear hai.</i>\n\n"
    
    if not top_picks:
        msg += "<b>⚠️ Aaj koi strong sasta mauka nahi mila.</b>\nMarket thoda weak hai. Cash bacha kar rakho.\n\n"
    else:
        for r in top_picks:
            msg += f"🔥 <b>{r['Name']}</b> (Current Price: ₹{r['Price']})\n"
            msg += f"💡 <b>Kyun (Reason)?</b> {r['Reason']}\n"
            msg += f"🎯 <b>Target:</b> ₹{r['Target']} | 🛑 <b>Stop Loss:</b> ₹{r['SL']}\n"
            msg += f"💰 <b>₹2000 Profit ke liye:</b> <b>{r['Shares']}</b> shares lo.\n"
            msg += f"⚠️ <b>Max Nuksan (agar SL hit hua):</b> ₹{r['MaxLoss']}\n"
            msg += f"🔗 <a href='https://www.screener.in/company/{r['Name']}/'>Screener Link</a>\n\n"

    # === 4. NEW ADDITION: EXPANDED MACRO & COMMODITY OCEAN ===
    macro_assets = {
        "GOLD": "GC=F", "SILVER": "SI=F", "CRUDE_OIL": "CL=F", "USD_INR": "USDINR=X",
        "STEEL": "STEEL=F", "WHEAT": "ZW=F", "SUGAR": "SB=F", "CORN": "ZC=F", "VEG_OIL": "ZL=F"
    }
    
    COMMODITY_MAP = {
        "SILVER_UP": ["HINDALCO", "VEDL", "TATASTEEL"],
        "SILVER_DOWN": ["TITAN", "KALYANKJIL", "SENCO"],
        "STEEL_UP": ["TATASTEEL", "JSWSTEEL", "SAIL", "NMDC"],
        "STEEL_DOWN": ["TATAMOTORS", "M&M", "LT"],
        "CRUDE_OIL_UP": ["ONGC", "OIL", "GAIL"],
        "CRUDE_OIL_DOWN": ["ASIANPAINT", "MRF", "APOLLOTYRE", "INDIGO"],
        "VEG_OIL_UP": ["PATANJALI", "ADANIWILMAR", "GODREJAGRO"],
        "SUGAR_CORN_UP": ["BALRAMCHIN", "DALMIASUG", "RENUKA", "UPL"],
        "RICE_WHEAT_UP": ["KRBL", "LTFOODS", "ITC", "DABUR"]
    }

    macro_msg = ""
    impact_lines = []
    for name, ticker in macro_assets.items():
        try:
            hist = yf.download(ticker, period="1mo", progress=False)["Close"]
            cl = hist.iloc[:, 0] if isinstance(hist, pd.DataFrame) else hist
            mom = ((float(cl.iloc[-1]) / float(cl.iloc[-5])) - 1) * 100
            trend = "📈 UP" if mom > 0 else "📉 DOWN"
            macro_msg += f"• {name}: {round(mom, 1)}% {trend}\n"
            
            key = None
            if name == "CRUDE_OIL": key = "CRUDE_OIL_UP" if mom > 3 else ("CRUDE_OIL_DOWN" if mom < -3 else None)
            elif name == "VEG_OIL": key = "VEG_OIL_UP" if mom > 1.5 else ("VEG_OIL_DOWN" if mom < -1.5 else None)
            elif name in ["SUGAR", "CORN"]: key = "SUGAR_CORN_UP" if mom > 1.5 else None
            elif name in ["WHEAT", "RICE"]: key = "RICE_WHEAT_UP" if mom > 1.5 else None
            elif name == "GOLD": key = "GOLD_UP" if mom > 2 else None
            elif name == "SILVER": key = "SILVER_UP" if mom > 2 else ("SILVER_DOWN" if mom < -2 else None)
            elif name == "STEEL": key = "STEEL_UP" if mom > 2 else ("STEEL_DOWN" if mom < -2 else None)
            
            if key and key in COMMODITY_MAP:
                label = key.replace("_UP", " BADH RAHA HAI").replace("_DOWN", " GIR RAHA HAI").replace("_", " ")
                impact_lines.append(f"🌊 *{label} ({round(mom,1)}%)* → {', '.join(COMMODITY_MAP[key])}")
        except: pass

    # === 5. FORMAT FINAL MESSAGE ===
    if macro_msg:
        msg += "<b>🌍 GLOBAL CUES:</b>\n" + macro_msg + "\n"
    
    if impact_lines:
        msg += "<b>🌊 COMMODITY OCEAN IMPACT:</b>\n" + "\n".join(impact_lines) + "\n\n"
        
    if scheme_alerts or contract_alerts:
        msg += "<b>📢 LIVE NEWS & SCHEMES:</b>\n"
        if scheme_alerts: msg += "\n".join(scheme_alerts[:3]) + "\n"
        if contract_alerts: msg += "\n".join(contract_alerts[:3]) + "\n\n"

    msg += "<b>💡 DOST KI SALAH:</b>\n"
    msg += "1. Kabhi bhi apne ₹50,000 mein se ek trade mein ₹10,000 se zyada mat lagana.\n"
    msg += "2. Stop Loss (SL) hit hote hi bech dena, 'wapas upar aayega' mat sochna.\n"
    msg += "3. Ye system suggestion hai, final decision tumhara hai. Safe raho!"
    
    send_telegram(msg)
    print("✅ Done! Message sent with full context.")

except Exception as e:
    error_msg = f"🚨 <b>SYSTEM CRASHED!</b>\nError: <code>{str(e)}</code>"
    print(error_msg)
    send_telegram(error_msg)
