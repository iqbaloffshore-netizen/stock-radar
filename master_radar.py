import pandas as pd, datetime, feedparser, requests, os, re, logging, traceback
from nsepython import equity_history
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
from bs4 import BeautifulSoup

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# Telegram Config
TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10)
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

try:
    print("🔄 Starting Iqbal Master Radar...")
    
    stocks = {
        "TATA_STEEL": "TATASTEEL", "JSW_STEEL": "JSWSTEEL", "ACC": "ACC",
        "HDFC_BANK": "HDFCBANK", "ICICI_BANK": "ICICIBANK", "SBIN": "SBIN",
        "TATA_POWER": "TATAPOWER", "JSW_ENERGY": "JSWENERGY", "ADANI_GREEN": "ADANIGREEN",
        "HAL": "HAL", "BEL": "BEL", "L&T": "LT", "RVNL": "RVNL",
        "M&M": "M&M", "CG_POWER": "CGPOWER", "KAYNES_TECH": "KAYNES", 
        "DIXON_TECH": "DIXON", "RELIANCE": "RELIANCE", "TCS": "TCS"
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

    def get_nse_data(symbol):
        try:
            df = equity_history(symbol, period="6m")
            if df is None or (hasattr(df, 'empty') and df.empty): return None
            if len(df) < 20: return None
            current_price = round(float(df['Close'].iloc[-1]), 2)
            sma_20 = round(float(df['Close'].rolling(window=20).mean().iloc[-1]), 2)
            signal = "HOLD"
            if current_price > sma_20: signal = "BUY/ADD"
            elif current_price < sma_20: signal = "SELL/AVOID"
            curr, prev = df.iloc[-1], df.iloc[-2]
            body, range_hl = abs(float(curr['Close']) - float(curr['Open'])), float(curr['High']) - float(curr['Low'])
            pattern = "➡️ NEUTRAL"
            if range_hl > 0 and (body / range_hl) < 0.15: pattern = "⚪ DOJI"
            elif (min(float(curr['Open']), float(curr['Close'])) - float(curr['Low'])) > (2 * body): pattern = "🔨 HAMMER"
            screener = get_screener_data(symbol)
            return {"Name": symbol, "Price": current_price, "SMA20": sma_20, "Signal": signal, "Pattern": pattern, "Promoter": screener["Promoter"], "Debt_Eq": screener["Debt_Eq"]}
        except:
            return None

    market_data = [data for name, symbol in stocks.items() if (data := get_nse_data(symbol))]
    df_stocks = pd.DataFrame(market_data)

    macro_assets = {"GOLD": "GC=F", "CRUDE_OIL": "CL=F", "USD_INR": "USDINR=X", "COPPER": "HG=F", "WHEAT": "ZW=F", "RICE": "RICE=F", "SUGAR": "SB=F", "CORN": "ZC=F", "VEG_OIL": "ZL=F"}
    COMMODITY_STOCK_MAP = {
        "RICE": [("KRBL","KRBL"),("LT FOODS","LTFOODS"),("ITC","ITC"),("TATA CONSUMER","TATACONSUM")],
        "WHEAT": [("ITC","ITC"),("TATA CONSUMER","TATACONSUM"),("DABUR","DABUR")],
        "SUGAR": [("BALRAMCHIN","BALRAMCHIN"),("DALMIASUG","DALMIASUG"),("RENUKA","RENUKA"),("TRIVENI","TRIVENI")],
        "VEG_OIL": [("PATANJALI","PATANJALI"),("ADANI WILMAR","ADANIWILMAR"),("GODREJ AGRO","GODREJAGRO")],
        "CORN": [("UPL","UPL"),("COROMANDEL","COROMANDEL"),("CHAMBLFERT","CHAMBLFERT")]
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
            if name == "CRUDE_OIL":
                if mom_5d < -3: impact_lines.append("🛢️ *TEL GIR RAHA HAI:* Asian Paints, MRF, IndiGo ke liye ACHA. ONGC ke liye BURA.")
                elif mom_5d > 3: impact_lines.append("🛢️ *TEL BADH RAHA HAI:* ONGC ke liye ACHA. Paints/Tyres ke liye BURA.")
            if name == "USD_INR" and mom_5d < -0.5: impact_lines.append("💵 *RUPEE MAZBOOT:* FII buying badhegi (HDFC/ICICI/TCS positive).")
            if name in COMMODITY_STOCK_MAP and mom_5d > 1.5:
                recs = [f"{disp} @ ₹{d['Price']}" for disp, sym in COMMODITY_STOCK_MAP[name] if (d := get_nse_data(sym))]
                if recs:
                    label = "PALM/VEG OIL" if name=="VEG_OIL" else name
                    impact_lines.append(f"🌾 *{label} BADH RAHA HAI ({round(mom_5d,1)}%)* → YE STOCKS LE:\n   " + " | ".join(recs) + f"\n   ⚠️ FMCG (Nestle/Britannia/HUL) se BACH.")
        except: pass

    df_macro = pd.DataFrame(macro_data)

    feeds = [
        "https://pib.gov.in/rssfeed.aspx", "https://www.rbi.org.in/scripts/notifications/rss.xml",
        "https://www.sebi.gov.in/content/sebi_news/rss_sebi.xml", "https://www.finmin.nic.in/rss.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "https://economictimes.indiatimes.com/industry/rssfeeds/1335018.cms",
        "https://www.livemint.com/rss/politics", "https://www.business-standard.com/rss/policy-10233.rss",
        "https://www.moneycontrol.com/rss/marketreports.xml", "https://www.economist.com/india/rss.xml",
        "https://feeds.bloomberg.com/markets/news.rss", "https://feeds.reuters.com/reuters/businessNews",
        "https://www.ft.com/world/asia/india?format=rss", "https://asia.nikkei.com/DAX/RSS/NASIA",
        "https://news.google.com/rss/search?q=India+Budget+OR+PLI+Scheme+OR+Capex+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=RBI+Repo+Rate+OR+Inflation+Data+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Adani+Group+OR+Reliance+Industries+deal+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=BRICS+Summit+OR+G20+India+trade+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Defence+Tender+OR+HAL+Order+OR+BEL+Contract+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=FII+DII+Data+OR+Foreign+Investment+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    ]

    news_alerts, policy_alerts, institutional_alerts, pharma_alerts = [], [], [], []
    def fetch_feed(url):
        try: return feedparser.parse(url).entries[:2]
        except: return []

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_feed, feeds))

    for entries in results:
        for entry in entries:
            title = entry.title.lower()
            if "fii" in title or "dii" in title or "foreign investment" in title: institutional_alerts.append(f"🔵 {entry.title}")
            elif "rbi" in title or "sebi" in title or "budget" in title: policy_alerts.append(f"🏛️ {entry.title}")
            elif any(kw in title for kw in ["usfda", "fda", "nppa", "drug price", "pharma", "medicine", "api"]): pharma_alerts.append(f"💊 {entry.title}")
            else: news_alerts.append(f"📰 {entry.title}")

    news_alerts, policy_alerts, institutional_alerts, pharma_alerts = [list(dict.fromkeys(x))[:6] for x in [news_alerts, policy_alerts, institutional_alerts, pharma_alerts]]

    msg = f"<b>🔥 IQBAL PRO MASTER RADAR</b> ({datetime.datetime.now().strftime('%d-%b %I:%M %p')})\n\n"
    if not df_stocks.empty:
        for label, condition in [("🟢 BUY/ADD", "BUY/ADD"), ("🔴 SELL/AVOID", "SELL/AVOID")]:
            subset = df_stocks[df_stocks["Signal"] == condition]
            if not subset.empty:
                msg += f"<b>{label} (Uptrend/Downtrend):</b>\n"
                for _, row in subset.iterrows():
                    msg += f"• <b>{row['Name']}</b> @ ₹{row['Price']} | {row['Pattern']}\n"
                    msg += f"  👤 Promoter: {row['Promoter']} | ⚖️ Debt/Eq: {row['Debt_Eq']}\n"
                    msg += f"  🔗 <a href='https://www.screener.in/company/{row['Name']}/'>Screener</a> | <a href='https://www.trendlyne.com/equity/{row['Name']}-limited/'>Trendlyne</a>\n\n"
    else:
        msg += "<b>⚠️ NSE Data Fetch Issue:</b> Temporary block. Macro data niche dekhein.\n\n"

    if not df_macro.empty:
        msg += "<b>🌍 MACRO RADAR:</b>\n" + "\n".join([f"• {row['Asset']}: {row['5D %']}% {row['Trend']}" for _, row in df_macro.iterrows()]) + "\n\n"

    if impact_lines:
        msg += "<b>💡 DOST WALI SAMJH:</b>\n" + "\n\n".join(impact_lines) + "\n\n"

    if pharma_alerts:
        msg += "<b>💊 PHARMA RADAR:</b>\n" + "\n".join(pharma_alerts) + "\n"
        msg += "\n💡 <i>Dost ki Salah:</i> " + ("Dollar mehenga hai, Exporters (Sun Pharma, Dr. Reddy) dekho." if usd_trend == "UP" else "Rupee stable hai, Domestic (Cipla, Mankind) dekho.") + "\n\n"

    if policy_alerts: msg += "<b>🏛️ POLICY:</b>\n" + "\n".join(policy_alerts) + "\n\n"
    if news_alerts: msg += "<b>📰 NEWS:</b>\n" + "\n".join(news_alerts) + "\n\n"
    if institutional_alerts: msg += "<b>🔵 FII/DII:</b>\n" + "\n".join(institutional_alerts) + "\n\n"

    msg += "<b>💡 Pro Tip:</b> Links par click karke deep research karo."
    
    # SEND MESSAGE
    send_telegram(msg)
    print("✅ Script completed successfully!")

except Exception as e:
    # MASTER CATCHER: Agar kuch bhi toota, toh Telegram par error bhej do
    error_msg = f"🚨 <b>SCRIPT CRASHED!</b>\n\nError: <code>{str(e)}</code>\n\nTraceback:\n<code>{traceback.format_exc()}</code>"
    print(error_msg)
    send_telegram(error_msg)
