import pandas as pd, datetime, feedparser, requests, os, re, logging, time
import yfinance as yf
from bs4 import BeautifulSoup

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"
LOG_FILE = "/tmp/trade_journal.csv"

# === 1. TELEGRAM CHUNKING FIX ===
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

def log_trade(data):
    try:
        df = pd.DataFrame([data])
        if not os.path.exists(LOG_FILE): df.to_csv(LOG_FILE, index=False)
        else: df.to_csv(LOG_FILE, mode='a', header=False, index=False)
    except: pass

def get_sentiment(title):
    pos = ["buy", "upgrade", "growth", "profit", "approval", "hike", "positive", "bullish", "surge", "gain", "won", "secured"]
    neg = ["sell", "downgrade", "loss", "ban", "warning", "crash", "negative", "bearish", "fraud", "scam", "fall", "probe"]
    t = title.lower()
    score = sum(1 for w in pos if w in t) - sum(1 for w in neg if w in t)
    return "🟢" if score > 0 else ("🔴" if score < 0 else "⚪")

try:
    print("🔄 Starting Ultimate Desi DTrader (FINAL ALL-IN-ONE)...")
    is_weekend = datetime.datetime.now().weekday() >= 5

    # === 2. EXPANDED STOCK UNIVERSE (30+ Stocks including all Commodity Proxies) ===
    base_stocks = {
        "TATA_STEEL": "TATASTEEL", "JSW_STEEL": "JSWSTEEL", "ACC": "ACC",
        "HDFC_BANK": "HDFCBANK", "ICICI_BANK": "ICICIBANK", "SBIN": "SBIN",
        "TATA_POWER": "TATAPOWER", "JSW_ENERGY": "JSWENERGY", "ADANI_GREEN": "ADANIGREEN",
        "HAL": "HAL", "BEL": "BEL", "L&T": "LT", "RVNL": "RVNL",
        "M&M": "M&M", "CG_POWER": "CGPOWER", "KAYNES_TECH": "KAYNES", 
        "DIXON_TECH": "DIXON", "RELIANCE": "RELIANCE", "TCS": "TCS",
        "HINDALCO": "HINDALCO", "VEDL": "VEDL", "TITAN": "TITAN",
        "SAIL": "SAIL", "NMDC": "NMDC", "TATA_MOTORS": "TATAMOTORS",
        "APOLLO_PIPES": "APOLLOPIPE", "RATNAMANI": "RATNAMANI",
        "BHARAT_FORGE": "BHARATFORG", "SIEMENS": "SIEMENS", "ABB": "ABB",
        "POLYCAB": "POLYCAB", "KEC": "KEC", "ONGC": "ONGC", "OIL_INDIA": "OIL",
        "GAIL": "GAIL", "ASIAN_PAINTS": "ASIANPAINT", "MRF": "MRF", "APOLLO_TYRES": "APOLLOTYRE",
        "INDIGO": "INDIGO", "HUL": "HINDUNILVR", "MARICO": "MARICO", "NESTLE": "NESTLEIND",
        "BRITANNIA": "BRITANNIA", "DALMIASUG": "DALMIASUG", "RENUKA": "RENUKA", "UPL": "UPL",
        "KRBL": "KRBL", "LT_FOODS": "LTFOODS", "DABUR": "DABUR", "SENCO": "SENCO", 
        "RAJESH_EXPORT": "RAJESHEXPO", "PATANJALI": "PATANJALI", "GODREJ_AGRO": "GODREJAGRO",
        "BALRAMCHIN": "BALRAMCHIN", "KALYAN_JEW": "KALYANKJIL"
    }

    def get_screener_data(symbol):
        try:
            url = f"https://www.screener.in/company/{symbol}/"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            promoter, debt = "N/A", "N/A"
            p_tag = soup.find(string=re.compile("Promoter"))
            if p_tag:
                parent = p_tag.find_parent('li') or p_tag.find_parent('div')
                if parent:
                    match = re.search(r'(\d+\.?\d*)\s*%', parent.text)
                    if match: promoter = f"{match.group(1)}%"
            d_tag = soup.find(string=re.compile("Debt to Equity"))
            if d_tag:
                parent = d_tag.find_parent('li') or d_tag.find_parent('div')
                if parent:
                    match = re.search(r'(\d+\.?\d*)', parent.text)
                    if match: debt = match.group(1)
            return {"Promoter": promoter, "Debt_Eq": debt}
        except: 
            return {"Promoter": "N/A", "Debt_Eq": "N/A"}

    def get_stock_data(symbol):
        try:
            time.sleep(0.3)
            # YAHOO FINANCE BYPASS (No NSE Blocking)
            df = yf.download(f"{symbol}.NS", period="6mo", progress=False)
            if df.empty or len(df) < 50: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            cp = round(float(df['Close'].iloc[-1]), 2)
            sma20 = round(float(df['Close'].rolling(20).mean().iloc[-1]), 2)
            sma50 = round(float(df['Close'].rolling(50).mean().iloc[-1]), 2)
            
            tr = abs(df['High'] - df['Low']).tail(14).mean()
            atr = float(tr) if not pd.isna(tr) else cp * 0.02
            sl = round(cp - (2 * atr), 2)
            tgt = round(cp + (3 * atr), 2)
            
            sig = "HOLD"
            if cp > sma20 > sma50: sig = "BUY/ADD"
            elif cp < sma20: sig = "SELL/AVOID"
            
            curr = df.iloc[-1]
            body = abs(float(curr['Close']) - float(curr['Open']))
            rng = float(curr['High']) - float(curr['Low'])
            pat = "➡️ NEUTRAL"
            if rng > 0 and (body / rng) < 0.15: pat = "⚪ DOJI"
            elif (min(float(curr['Open']), float(curr['Close'])) - float(curr['Low'])) > (2 * body): pat = "🔨 HAMMER"
            
            avg_vol = df['Volume'].tail(10).mean()
            today_vol = df['Volume'].iloc[-1]
            stealth = "✅ Smart Money" if today_vol > (avg_vol * 1.5) else "Normal"
            
            scr = get_screener_data(symbol)
            return {"Name": symbol, "Price": cp, "SMA20": sma20, "Signal": sig, "Pattern": pat, 
                    "SL": sl, "Target": tgt, "Stealth": stealth, "Promoter": scr["Promoter"], "Debt_Eq": scr["Debt_Eq"]}
        except:
            return None

    market_data = [d for s in base_stocks.values() if (d := get_stock_data(s))]
    df_stocks = pd.DataFrame(market_data)

    # === 3. EXPANDED COMMODITY OCEAN (UP/DOWN Logic for All) ===
    macro_assets = {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE_OIL": "CL=F", "USD_INR": "USDINR=X", 
                    "COPPER": "HG=F", "STEEL": "STEEL=F", "WHEAT": "ZW=F", "RICE": "RICE=F", 
                    "SUGAR": "SB=F", "CORN": "ZC=F", "VEG_OIL": "ZL=F"}
    
    COMMODITY_MAP = {
        "SILVER_UP": [("HINDALCO","HINDALCO"),("VEDL","VEDL"),("TATA STEEL","TATASTEEL")],
        "SILVER_DOWN": [("TITAN","TITAN"),("KALYAN JEW","KALYANKJIL"),("SENCO","SENCO")],
        "STEEL_UP": [("TATASTEEL","TATASTEEL"),("JSW_STEEL","JSWSTEEL"),("SAIL","SAIL"),("NMDC","NMDC")],
        "STEEL_DOWN": [("TATA MOTORS","TATAMOTORS"),("M&M","M&M"),("L&T","LT")],
        "MILD_STEEL_UP": [("APOLLO PIPES","APOLLOPIPE"),("RATNAMANI","RATNAMANI")],
        "CRUDE_OIL_UP": [("ONGC","ONGC"),("OIL INDIA","OIL"),("GAIL","GAIL"),("RELIANCE","RELIANCE")],
        "CRUDE_OIL_DOWN": [("ASIAN PAINTS","ASIANPAINT"),("MRF","MRF"),("APOLLO TYRES","APOLLOTYRE"),("INDIGO","INDIGO")],
        "VEG_OIL_UP": [("PATANJALI","PATANJALI"),("ADANI WILMAR","ADANIWILMAR"),("GODREJ AGRO","GODREJAGRO")],
        "VEG_OIL_DOWN": [("HUL","HINDUNILVR"),("MARICO","MARICO"),("NESTLE","NESTLEIND"),("BRITANNIA","BRITANNIA")],
        "SUGAR_CORN_UP": [("BALRAMCHIN","BALRAMCHIN"),("DALMIASUG","DALMIASUG"),("RENUKA","RENUKA"),("UPL","UPL")],
        "RICE_WHEAT_UP": [("KRBL","KRBL"),("LT FOODS","LTFOODS"),("ITC","ITC"),("DABUR","DABUR")],
        "GOLD_UP": [("TITAN","TITAN"),("KALYAN JEW","KALYANKJIL"),("SENCO","SENCO"),("RAJESH EXPORT","RAJESHEXPO")]
    }

    macro_data, impact_lines = [], []
    for name, ticker in macro_assets.items():
        try:
            hist = yf.download(ticker, period="1mo", progress=False)["Close"]
            cl = hist.iloc[:, 0] if isinstance(hist, pd.DataFrame) else hist
            mom = ((float(cl.iloc[-1]) / float(cl.iloc[-5])) - 1) * 100
            trend = "📈 UP" if mom > 0 else "📉 DOWN"
            macro_data.append({"Asset": name, "5D%": round(mom, 1), "Trend": trend})
            
            key = None
            if name == "CRUDE_OIL": key = "CRUDE_OIL_UP" if mom > 3 else ("CRUDE_OIL_DOWN" if mom < -3 else None)
            elif name == "VEG_OIL": key = "VEG_OIL_UP" if mom > 1.5 else ("VEG_OIL_DOWN" if mom < -1.5 else None)
            elif name in ["SUGAR", "CORN"]: key = "SUGAR_CORN_UP" if mom > 1.5 else None
            elif name in ["WHEAT", "RICE"]: key = "RICE_WHEAT_UP" if mom > 1.5 else None
            elif name == "GOLD": key = "GOLD_UP" if mom > 2 else None
            elif name == "SILVER": key = "SILVER_UP" if mom > 2 else ("SILVER_DOWN" if mom < -2 else None)
            elif name == "STEEL": key = "STEEL_UP" if mom > 2 else ("STEEL_DOWN" if mom < -2 else None)
            
            if key and key in COMMODITY_MAP:
                recs = [f"{d} @ ₹{get_stock_data(s)['Price']}" for d, s in COMMODITY_MAP[key] if get_stock_data(s)]
                if recs: 
                    label = key.replace("_UP", " BADH RAHA HAI").replace("_DOWN", " GIR RAHA HAI").replace("_", " ")
                    impact_lines.append(f"🌊 *{label} ({round(mom,1)}%)* → {' | '.join(recs)}")
        except: pass

    # === 4. ALL 18+ FEEDS (Including Specific Contract/Expansion Searches) ===
    feeds = [
        "https://pib.gov.in/rssfeed.aspx", "https://www.rbi.org.in/scripts/notifications/rss.xml",
        "https://www.sebi.gov.in/content/sebi_news/rss_sebi.xml", "https://www.finmin.nic.in/rss.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", 
        "https://economictimes.indiatimes.com/industry/rssfeeds/1335018.cms",
        "https://www.livemint.com/rss/politics", "https://www.business-standard.com/rss/policy-10233.rss",
        "https://www.moneycontrol.com/rss/marketreports.xml", "https://www.economist.com/india/rss.xml",
        "https://news.google.com/rss/search?q=India+Budget+OR+PLI+Scheme+OR+Capex+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=RBI+Repo+Rate+OR+Inflation+Data+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Defence+Tender+OR+HAL+Order+OR+BEL+Contract+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=FII+DII+Data+OR+Foreign+Investment+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Solar+Mission+OR+Green+Hydrogen+OR+Semiconductor+Mission+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=PM+Gati+Shakti+OR+National+Infrastructure+OR+Bharatmala+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=EV+Policy+FAME+OR+Digital+India+OR+UPI+OR+PM+Awas+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=won+contract+OR+received+order+OR+bagged+order+OR+expansion+plan+OR+capex+when:3d&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    
    news_alerts, policy_alerts, institutional_alerts, pharma_alerts, scheme_alerts, contract_alerts = [], [], [], [], [], []
    SCHEME_MAP = {"PLI": [("Dixon","DIXON"),("Kaynes","KAYNES")], "Make in India": [("HAL","HAL"),("BEL","BEL")],
                  "Gati Shakti": [("L&T","LT"),("RVNL","RVNL")], "Solar": [("Tata Power","TATAPOWER"),("Adani Green","ADANIGREEN")]}
    CONTRACT_KEYWORDS = ["won contract", "received order", "bagged order", "secures deal", "expansion plan", "new plant", "capex"]

    def fetch_feed(u):
        try: return feedparser.parse(u).entries[:2]
        except: return []

    with ThreadPoolExecutor(max_workers=15) as ex: 
        results = list(ex.map(fetch_feed, feeds))

    for entries in results:
        for e in entries:
            t = e.title.lower()
            sent = get_sentiment(e.title)
            
            if "fii" in t or "dii" in t: institutional_alerts.append(f"🔵 {sent} {e.title}")
            elif "rbi" in t or "sebi" in t or "budget" in t: policy_alerts.append(f"🏛️ {sent} {e.title}")
            elif any(k in t for k in ["usfda","fda","nppa","drug price","pharma"]): pharma_alerts.append(f"💊 {sent} {e.title}")
            else: news_alerts.append(f"📰 {sent} {e.title}")
            
            for sch, stkl in SCHEME_MAP.items():
                if sch.lower() in t:
                    recs = [f"{d} @ ₹{get_stock_data(s)['Price']}" for d, s in stkl[:2] if get_stock_data(s)]
                    if recs: scheme_alerts.append(f"🇮🇳 *{sch.upper()}* → {e.title[:50]}... {' | '.join(recs)}")
                    break
            
            if any(k in t for k in CONTRACT_KEYWORDS):
                for nm, sym in base_stocks.items():
                    if nm.lower() in t or sym.lower() in t:
                        contract_alerts.append(f"🏗️ *{nm}* → {e.title[:60]}...")
                        break

    news_alerts, policy_alerts, institutional_alerts, pharma_alerts, scheme_alerts, contract_alerts = [list(dict.fromkeys(x))[:4] for x in [news_alerts, policy_alerts, institutional_alerts, pharma_alerts, scheme_alerts, contract_alerts]]

    # === 5. FORMAT MESSAGE ===
    header = "📅 WEEKEND BRIEFING" if is_weekend else "🔥 ULTIMATE DESI DTRADER"
    msg = f"<b>{header}</b> ({datetime.datetime.now().strftime('%d-%b %I:%M %p')})\n\n"
    
    if not df_stocks.empty:
        for lbl, cond in [("🟢 BUY/ADD (Chadhta Suraj)", "BUY/ADD"), ("🔴 SELL/AVOID", "SELL/AVOID")]:
            sub = df_stocks[df_stocks["Signal"] == cond]
            if not sub.empty:
                msg += f"<b>{lbl}:</b>\n"
                for _, r in sub.iterrows():
                    msg += f"• <b>{r['Name']}</b> @ ₹{r['Price']} | {r['Pattern']} | {r['Stealth']}\n"
                    msg += f"  🎯 T: ₹{r['Target']} | 🛑 SL: ₹{r['SL']} | 👤 P: {r['Promoter']}\n"
                    msg += f"  🔗 <a href='https://www.screener.in/company/{r['Name']}/'>Screener</a>\n\n"
                    log_trade({"Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "Stock": r['Name'], "Signal": cond, "Price": r['Price']})
    else:
        msg += "<b>⚠️ Data Fetch Issue:</b> Temporary glitch. Macro/Scheme data niche dekhein.\n\n"

    if macro_data: 
        msg += "<b>🌍 MACRO & COMMODITY:</b>\n" + "\n".join([f"• {r['Asset']}: {r['5D%']}% {r['Trend']}" for r in macro_data]) + "\n\n"
    if impact_lines: msg += "<b>🌊 COMMODITY IMPACT:</b>\n" + "\n\n".join(impact_lines) + "\n\n"
    if contract_alerts: msg += "<b>🏗️ CONTRACTS/EXPANSION:</b>\n" + "\n".join(contract_alerts) + "\n\n"
    if scheme_alerts: msg += "<b>🇮🇳 GOVT SCHEMES:</b>\n" + "\n".join(scheme_alerts) + "\n\n"
    if pharma_alerts: msg += "<b>💊 PHARMA:</b>\n" + "\n".join(pharma_alerts) + "\n\n"
    if policy_alerts: msg += "<b>🏛️ POLICY:</b>\n" + "\n".join(policy_alerts) + "\n\n"
    if news_alerts: msg += "<b>📰 NEWS:</b>\n" + "\n".join(news_alerts) + "\n\n"
    if institutional_alerts: msg += "<b>🔵 FII/DII:</b>\n" + "\n".join(institutional_alerts) + "\n\n"
    
    msg += "<b>💡 RULE:</b> Sirf CNC Delivery. Max ₹10k/trade. SL-M Mandatory. No Hope Trading."
    
    send_telegram(msg)
    print("✅ Jail-Cancel Blueprint Executed Successfully!")

except Exception as e:
    error_msg = f"🚨 <b>SYSTEM CRASHED!</b>\n\nError: <code>{str(e)}</code>\n\nTraceback:\n<code>{str(e)}</code>"
    print(error_msg)
    send_telegram(error_msg)
