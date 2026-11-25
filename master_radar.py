import pandas as pd, datetime, feedparser, requests, os, re, logging, time, random
import yfinance as yf

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

def send_telegram(msg):
    try:
        # Plain text, NO HTML tags to prevent <b> from showing up
        chunks = [msg[i:i+3800] for i in range(0, len(msg), 3800)]
        for i, chunk in enumerate(chunks):
            text = chunk if len(chunks) == 1 else f"Part {i+1}/{len(chunks)}\n\n{chunk}"
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_CHAT, "text": text}, timeout=15)
            time.sleep(1)
        print("✅ Message sent")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

# STRICT FILTER: Only affordable, high-liquidity stocks (Under ₹1500)
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
        
        # STRICT PRICE FILTER: Reject anything above ₹1500
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
        
        avg_vol = df['Volume'].tail(10).mean()
        today_vol = df['Volume'].iloc[-1]
        stealth = "Smart Money Buying (High Volume)" if today_vol > (avg_vol * 1.5) else "Normal Activity"
        
        # Only show if it's a BUY signal OR a strong reversal pattern
        if sig != "BUY" and pat == "Normal Price Action":
            return None
            
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

def get_reason(symbol, data, news_titles):
    reasons = []
    if data['Stealth'] == "Smart Money Buying (High Volume)":
        reasons.append("Smart Money Buying")
    if "Hammer" in data['Pattern']:
        reasons.append("Strong Reversal Pattern")
    elif "Doji" in data['Pattern']:
        reasons.append("Consolidation Breakout")
    
    # Check if this stock is mentioned in recent public news
    for news in news_titles:
        if symbol.lower() in news.lower():
            reasons.append(f"News: {news[:50]}...")
            break
            
    if not reasons:
        reasons.append("Technical Uptrend")
    return " | ".join(reasons)

try:
    print("🔄 Scanning Market for Affordable Gems with Reasons...")
    
    # Fetch public news first to build context (Legal News Synthesis)
    feeds = [
        "https://pib.gov.in/rssfeed.aspx",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://news.google.com/rss/search?q=PLI+Scheme+OR+Contract+OR+Expansion+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    all_news = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:3]:
                all_news.append(entry.title)
        except: pass

    market_data = []
    for s in AFFORDABLE_POOL:
        d = get_stock_data(s)
        if d:
            d['Reason'] = get_reason(s, d, all_news)
            market_data.append(d)

    # Sort by price and take ONLY TOP 5 to avoid spam
    market_data.sort(key=lambda x: x['Price'])
    top_picks = market_data[:5] 
    
    msg = "🌊 SAMUNDAR SE NIKLE HAIN YE HEERE (Affordable & Strong)\n\n"
    msg += "Note: Sirf wo shares dikhaye gaye hain jo ₹1500 se kam ke hain aur jinke upar jaane ke strong chances hain.\n\n"
    
    if not top_picks:
        msg += "⚠️ Aaj koi strong sasta mauka nahi mila.\nMarket thoda weak hai. Cash bacha kar rakho.\n\n"
    else:
        for r in top_picks:
            msg += f"🔥 {r['Name']} (Price: ₹{r['Price']})\n"
            msg += f"💡 KYUN BUY? {r['Reason']}\n"
            msg += f"🎯 Target: ₹{r['Target']} | 🛑 Stop Loss: ₹{r['SL']}\n"
            msg += f"💰 ₹2000 Profit ke liye: {r['Shares']} shares lo.\n"
            msg += f"⚠️ Max Nuksan (agar SL hit hua): ₹{r['MaxLoss']}\n"
            msg += f"🔗 Screener: https://www.screener.in/company/{r['Name']}/\n\n"

    # Macro Cues
    macro_assets = {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE_OIL": "CL=F", "USD_INR": "USDINR=X"}
    macro_msg = ""
    for name, ticker in macro_assets.items():
        try:
            hist = yf.download(ticker, period="1mo", progress=False)["Close"]
            cl = hist.iloc[:, 0] if isinstance(hist, pd.DataFrame) else hist
            mom = ((float(cl.iloc[-1]) / float(cl.iloc[-5])) - 1) * 100
            trend = "UP" if mom > 0 else "DOWN"
            macro_msg += f"• {name}: {round(mom, 1)}% {trend}\n"
        except: pass
    
    if macro_msg:
        msg += "🌍 GLOBAL CUES:\n" + macro_msg + "\n"

    msg += "💡 DOST KI SALAH:\n"
    msg += "1. Kabhi bhi apne ₹50,000 mein se ek trade mein ₹10,000 se zyada mat lagana.\n"
    msg += "2. Stop Loss (SL) hit hote hi bech dena, 'wapas upar aayega' mat sochna.\n"
    msg += "3. Ye system suggestion hai, final decision tumhara hai. Safe raho!"
    
    send_telegram(msg)
    print("✅ Done! Message sent.")

except Exception as e:
    error_msg = f"🚨 SYSTEM CRASHED!\nError: {str(e)}"
    print(error_msg)
    send_telegram(error_msg)
