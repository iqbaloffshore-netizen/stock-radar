import pandas as pd, datetime, feedparser, requests, os, re, logging, traceback, time
from nsepython import equity_history
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
from bs4 import BeautifulSoup

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

def send_telegram(msg):
    try:
        chunks = [msg[i:i+3500] for i in range(0, len(msg), 3500)]
        for i, chunk in enumerate(chunks):
            text = chunk if len(chunks) == 1 else f"<b>Part {i+1}/{len(chunks)}</b>\n\n{chunk}"
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"}, timeout=15)
            time.sleep(1)
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

def get_sentiment(title):
    pos = ["buy", "upgrade", "growth", "profit", "approval", "hike", "positive", "bullish", "surge", "gain", "won", "secured"]
    neg = ["sell", "downgrade", "loss", "ban", "warning", "crash", "negative", "bearish", "fraud", "scam", "fall", "probe"]
    t = title.lower()
    score = sum(1 for w in pos if w in t) - sum(1 for w in neg if w in t)
    return "🟢" if score > 0 else ("🔴" if score < 0 else "⚪")

try:
    print("🔄 Starting Ultimate Desi DTrader...")
    is_weekend = datetime.datetime.now().weekday() >= 5

    # === 1. CORE & DYNAMIC WATCHLIST ===
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
        "POLYCAB": "POLYCAB", "KEC": "KEC"
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
        except: return {"Promoter": "N/A", "Debt_Eq": "N/A"}

    def get_nse_data(symbol, retries=2):
        for attempt in range(retries):
            try:
                time.sleep(0.3)
                df = equity_history(symbol, period="6m")
                if df is None or (hasattr(df, 'empty') and df.empty): 
                    if attempt < retries-1: continue
                    return None
                if len(df) < 20: return None
                
                current_price = round(float(df['Close'].iloc[-1]), 2)
                sma_20 = round(float(df['Close'].rolling(window=20).mean().iloc[-1]), 2)
                sma_50 = round(float(df['Close'].rolling(window=50).mean().iloc[-1]), 2)
                
                tr = abs(df['High'] - df['Low']).tail(14).mean()
                atr = float(tr) if not pd.isna(tr) else current_price * 0.02
                sl = round(current_price - (2 * atr), 2)
                target = round(current_price + (3 * atr), 2)
                
                signal = "HOLD"
                if current_price > sma_20 > sma_50: signal = "BUY/ADD"
                elif current_price < sma_20: signal = "SELL/AVOID"
                
                curr = df.iloc[-1]
                body = abs(float(curr['Close']) - float(curr['Open']))
                range_hl = float(curr['High']) - float(curr['Low'])
                pattern = "➡️ NEUTRAL"
                if range_hl > 0 and (body / range_hl) < 0.15: pattern = "⚪ DOJI"
                elif (min(float(curr['Open']), float(curr['Close'])) - float(curr['Low'])) > (2 * body): pattern = "🔨 HAMMER"
                
                # Smart Money / Stealth Check
                avg_vol = df['TOTAL_TRADED_QUANTITY'].tail(10).mean()
                today_vol = df['TOTAL_TRADED_QUANTITY'].iloc[-1]
                delivery_pct = df['DELIVERY_QUANTITY'].iloc[-1] / today_vol if today_vol > 0 else 0
                
                stealth = "✅ Smart Money" if (today_vol > avg_vol * 1.5 and delivery_pct > 0.55) else "Normal"
                
                screener = get_screener_data(symbol)
                
                return {"Name": symbol, "Price": current_price, "SMA20": sma_20, "Signal": signal, 
                        "Pattern": pattern, "SL": sl, "Target": target, "Stealth": stealth,
                        "Promoter": screener["Promoter"], "Debt_Eq": screener["Debt_Eq"],
                        "High": float(curr['High']), "Low": float(curr['Low']), "Delivery": round(delivery_pct*100, 1)}
            except:
                if attempt == retries-1: return None
        return None

    market_data = [data for name, symbol in base_stocks.items() if (data := get_nse_data(symbol))]
    df_stocks = pd.DataFrame(market_data)

    # === 2. COMMODITY OCEAN (Silver, Steel, Agri) ===
    macro_assets = {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE_OIL": "CL=F", "USD_INR": "USDINR=X", 
                    "COPPER": "HG=F", "STEEL": "STEEL=F", "WHEAT": "ZW=F", "RICE": "RICE=F", 
                    "SUGAR": "SB=F", "CORN": "ZC=F", "VEG_OIL": "ZL=F"}
    
    COMMODITY_STOCK_MAP = {
        "SILVER_UP": [("HINDALCO","HINDALCO"),("VEDL","VEDL"),("TATA STEEL","TATASTEEL")],
        "SILVER_DOWN": [("TITAN","TITAN"),("KALYAN JEW","KALYANKJIL"),("SENCO","SENCO")],
        "STEEL_UP": [("TATASTEEL","TATASTEEL"),("JSW_STEEL","JSWSTEEL"),("SAIL","SAIL"),("NMDC","NMDC")],
        "STEEL_DOWN": [("TATA MOTORS","TATAMOTORS"),("M&M","M&M"),("L&T","LT")],
        "MILD_STEEL_UP": [("APOLLO PIPES","APOLLOPIPE"),("RATNAMANI","RATNAMANI")],
        "CRUDE_OIL_UP": [("ONGC","ONGC"),("OIL INDIA","OIL"),("GAIL","GAIL")],
        "CRUDE_OIL_DOWN": [("ASIAN PAINTS","ASIANPAINT"),("MRF","MRF"),("INDIGO","INDIGO")],
        "VEG_OIL_UP": [("PATANJALI","PATANJALI"),("ADANI WILMAR","ADANIWILMAR")],
        "VEG_OIL_DOWN": [("HUL","HINDUNILVR"),("MARICO","MARICO"),("NESTLE","NESTLEIND")],
        "SUGAR_CORN_UP": [("BALRAMCHIN","BALRAMCHIN"),("RENUKA","RENUKA"),("UPL","UPL")],
        "RICE_WHEAT_UP": [("KRBL","KRBL"),("LT FOODS","LTFOODS"),("ITC","ITC")],
        "GOLD_UP": [("TITAN","TITAN"),("KALYAN JEW","KALYANKJIL"),("RAJESH EXPORT","RAJESHEXPO")]
    }

    macro_data, impact_lines, usd_trend = [], [], "STABLE"
    for name, ticker in macro_assets.items():
        try:
            hist = yf.download(ticker, period="1mo", progress=False)["Close"]
            close = hist.iloc[:, 0] if isinstance(hist, pd.DataFrame) else hist
            mom_5d = ((float(close.iloc[-1])/float(close.iloc[-5]))-1)*100
            trend = "📈 UP" if mom_5d > 0 else "📉 DOWN"
            macro_data.append({"Asset": name, "5D %": round(mom_5d, 1), "Trend": trend})
            
            if name == "USD_INR" and mom_5d > 0.5: usd_trend = "UP"
            
            if name == "CRUDE_OIL": key = "CRUDE_OIL_UP" if mom_5d > 3 else ("CRUDE_OIL_DOWN" if mom_5d < -3 else None)
            elif name == "VEG_OIL": key = "VEG_OIL_UP" if mom_5d > 1.5 else ("VEG_OIL_DOWN" if mom_5d < -1.5 else None)
            elif name in ["SUGAR", "CORN"]: key = "SUGAR_CORN_UP" if mom_5d > 1.5 else None
            elif name in ["WHEAT", "RICE"]: key = "RICE_WHEAT_UP" if mom_5d > 1.5 else None
            elif name == "GOLD": key = "GOLD_UP" if mom_5d > 2 else None
            elif name == "SILVER": key = "SILVER_UP" if mom_5d > 2 else ("SILVER_DOWN" if mom_5d < -2 else None)
            elif name == "STEEL": key = "STEEL_UP" if mom_5d > 2 else ("STEEL_DOWN" if mom_5d < -2 else None)
            else: key = None

            if key and key in COMMODITY_STOCK_MAP:
                recs = [f"{d} @ ₹{x['Price']}" for d,s in COMMODITY_STOCK_MAP[key][:3] if (x := get_nse_data(s))]
                if recs:
                    label = key.replace("_UP", " BADH RAHA HAI").replace("_DOWN", " GIR RAHA HAI").replace("_", " ")
                    impact_lines.append(f"🌊 *{label} ({round(mom_5d,1)}%)* → {' | '.join(recs)}")
        except: pass

    df_macro = pd.DataFrame(macro_data)

    # === 3. NEWS, SCHEMES & CONTRACTS ===
    feeds = [
        "https://pib.gov.in/rssfeed.aspx", "https://www.rbi.org.in/scripts/notifications/rss.xml",
        "https://www.sebi.gov.in/content/sebi_news/rss_sebi.xml", "https://www.finmin.nic.in/rss.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", 
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://news.google.com/rss/search?q=India+Budget+OR+PLI+Scheme+OR+Capex+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=RBI+Repo+Rate+OR+Inflation+Data+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Defence+Tender+OR+HAL+Order+OR+BEL+Contract+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=FII+DII+Data+OR+Foreign+Investment+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=PLI+Scheme+OR+PM-KISAN+OR+Ayushman+Bharat+OR+Make+in+India+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Solar+Mission+OR+Green+Hydrogen+OR+Semiconductor+Mission+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=PM+Gati+Shakti+OR+National+Infrastructure+OR+Bharatmala+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=EV+Policy+FAME+OR+Digital+India+OR+UPI+OR+PM+Awas+when:7d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=won+contract+OR+received+order+OR+bagged+order+OR+expansion+plan+OR+new+plant+OR+capex+when:3d&hl=en-IN&gl=IN&ceid=IN:en"
    ]

    news_alerts, policy_alerts, institutional_alerts, pharma_alerts, scheme_alerts, contract_alerts = [], [], [], [], [], []
    
    GOVT_SCHEME_MAP = {
        "PLI": [("Dixon","DIXON"),("Kaynes","KAYNES"),("Sun Pharma","SUNPHARMA"),("M&M","M&M")],
        "PM-KISAN": [("UPL","UPL"),("Coromandel","COROMANDEL"),("Chambal","CHAMBLFERT")],
        "Ayushman": [("Max Healthcare","MAXHEALTH"),("Apollo","APOLLOHOSP"),("Narayana","NARAYANA")],
        "Make in India": [("HAL","HAL"),("BEL","BEL"),("BDL","BDL"),("Mazagon","MAZDOCK")],
        "Gati Shakti": [("L&T","LT"),("IRB","IRB"),("RVNL","RVNL"),("IRCON","IRCON")],
        "Solar": [("Tata Power","TATAPOWER"),("Adani Green","ADANIGREEN"),("Waaree","WAAREEENER")],
        "Green Hydrogen": [("Reliance","RELIANCE"),("NTPC","NTPC"),("IOCL","IOC")],
        "PM Awas": [("ACC","ACC"),("UltraTech","ULTRACEMCO"),("Pidilite","PIDILITIND")],
        "Digital India": [("TCS","TCS"),("Infosys","INFY"),("CDSL","CDSL")],
        "FAME": [("Tata Motors","TATAMOTORS"),("Exide","EXIDEIND"),("Amara Raja","AMARAJABAT")]
    }

    CONTRACT_KEYWORDS = ["won contract", "received order", "bagged order", "secures deal", "expansion plan", "new plant", "capex", "loI received"]

    def fetch_feed(url):
        try: return feedparser.parse(url).entries[:3]
        except: return []

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_feed, feeds))

    for entries in results:
        for entry in entries:
            title = entry.title.lower()
            sent = get_sentiment(entry.title)
            
            if "fii" in title or "dii" in title or "foreign investment" in title: institutional_alerts.append(f"🔵 {sent} {entry.title}")
            elif "rbi" in title or "sebi" in title or "budget" in title: policy_alerts.append(f"🏛️ {sent} {entry.title}")
            elif any(kw in title for kw in ["usfda", "fda", "nppa", "drug price", "pharma", "medicine"]): pharma_alerts.append(f"💊 {sent} {entry.title}")
            else: news_alerts.append(f"📰 {sent} {entry.title}")

            # Scheme Detector
            for scheme, stock_list in GOVT_SCHEME_MAP.items():
                if scheme.lower() in title:
                    recs = [f"{d} @ ₹{x['Price']}" for d,s in stock_list[:2] if (x := get_nse_data(s))]
                    if recs:
                        scheme_alerts.append(f"🇮🇳 *{scheme.upper()}* → {entry.title[:50]}...\n   {' | '.join(recs)}")
                    break

            # Contract/Expansion Detector
            if any(kw in title for kw in CONTRACT_KEYWORDS):
                for name, symbol in base_stocks.items():
                    if name.lower().replace("_"," ") in title or symbol.lower() in title:
                        data = get_nse_data(symbol)
                        if data:
                            contract_alerts.append(f"🏗️ *{name}* → {entry.title[:60]}...\n   Price: ₹{data['Price']} | Signal: {data['Signal']}")
                        break

    news_alerts, policy_alerts, institutional_alerts, pharma_alerts, scheme_alerts, contract_alerts = [list(dict.fromkeys(x))[:4] for x in [news_alerts, policy_alerts, institutional_alerts, pharma_alerts, scheme_alerts, contract_alerts]]

    # === 4. OVERNIGHT SWING SCANNER ===
    overnight_picks = []
    if not is_weekend:
        for _, row in df_stocks.iterrows():
            if row['Signal'] == 'BUY/ADD' and row['Delivery'] > 50 and row['Price'] > (row['High'] * 0.95):
                overnight_picks.append(f"• <b>{row['Name']}</b> @ ₹{row['Price']} | Del: {row['Delivery']}% | SL: ₹{row['SL']}")

    # === 5. FORMAT TELEGRAM MESSAGE ===
    header = "📅 WEEKEND BRIEFING" if is_weekend else "🔥 ULTIMATE DESI DTRADER"
    msg = f"<b>{header}</b> ({datetime.datetime.now().strftime('%d-%b %I:%M %p')})\n\n"
    
    if not df_stocks.empty:
        for label, condition in [("🟢 BUY/ADD (Chadhta Suraj)", "BUY/ADD"), ("🔴 SELL/AVOID", "SELL/AVOID")]:
            subset = df_stocks[df_stocks["Signal"] == condition]
            if not subset.empty:
                msg += f"<b>{label}:</b>\n"
                for _, row in subset.iterrows():
                    msg += f"• <b>{row['Name']}</b> @ ₹{row['Price']} | {row['Pattern']} | {row['Stealth']}\n"
                    msg += f"  🎯 T: ₹{row['Target']} | 🛑 SL: ₹{row['SL']} | 👤 P: {row['Promoter']}\n\n"
    else:
        msg += "<b>⚠️ NSE Data Fetch Issue:</b> Temporary block. Macro/Scheme data niche dekhein.\n\n"

    if overnight_picks:
        msg += "<b>🌙 OVERNIGHT SWING PICKS (Buy Today CNC, Sell Tomorrow 9:30 AM):</b>\n" + "\n".join(overnight_picks[:3]) + "\n\n"

    if not df_macro.empty:
        msg += "<b>🌍 MACRO & COMMODITY OCEAN:</b>\n" + "\n".join([f"• {row['Asset']}: {row['5D %']}% {row['Trend']}" for _, row in df_macro.iterrows()]) + "\n\n"

    if impact_lines: msg += "<b>🌊 COMMODITY IMPACT:</b>\n" + "\n\n".join(impact_lines) + "\n\n"
    if contract_alerts: msg += "<b>🏗️ CONTRACT/EXPANSION ALERTS:</b>\n" + "\n\n".join(contract_alerts) + "\n\n"
    if scheme_alerts: msg += "<b>🇮🇳 GOVT SCHEME RADAR:</b>\n" + "\n\n".join(scheme_alerts) + "\n\n"
    if pharma_alerts: msg += "<b>💊 PHARMA RADAR:</b>\n" + "\n".join(pharma_alerts) + "\n\n"
    if policy_alerts: msg += "<b>🏛️ POLICY:</b>\n" + "\n".join(policy_alerts) + "\n\n"
    if news_alerts: msg += "<b>📰 NEWS:</b>\n" + "\n".join(news_alerts) + "\n\n"
    if institutional_alerts: msg += "<b>🔵 FII/DII:</b>\n" + "\n".join(institutional_alerts) + "\n\n"

    msg += "<b>💡 Pro Tip:</b> 100% Free, Indian Market Optimized, Govt Scheme Deep Dive."
    
    send_telegram(msg)
    print("✅ Ultimate Desi DTrader completed successfully!")

except Exception as e:
    error_msg = f"🚨 <b>SYSTEM CRASHED!</b>\n\nError: <code>{str(e)}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>"
    print(error_msg)
    send_telegram(error_msg)
