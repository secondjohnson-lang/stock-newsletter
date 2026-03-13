import os
import requests
import yfinance as yf
import feedparser
from datetime import datetime

api_key = os.getenv("OPENROUTER_API_KEY")

# Your watchlist - add any tickers you want to scan
WATCHLIST = [
    # Biotech/Pharma
    "IOVA", "SAVA", "ACAD", "NVAX", "MRNA",
    "FATE", "BEAM", "CRSP", "EDIT", "NTLA",
    # Small/Mid Cap momentum
    "FFIE", "MULN", "NKLA", "WKHS", "RIDE",
    # Infrastructure/Tech
    "PLUG", "FCEL", "BLNK", "CHPT", "NKLA",
    # Additional speculative
    "SPWR", "SUNW", "IDEX", "CLOV", "WISH"
]

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        avg_volume = info.get("averageVolume", 1)
        volume = info.get("volume", 0)
        volume_spike = round((volume / avg_volume * 100), 1) if avg_volume > 0 else 0
        
        shares_float = info.get("floatShares", 0)
        shares_outstanding = info.get("sharesOutstanding", 1)
        float_pct = round((shares_float / shares_outstanding * 100), 1) if shares_outstanding > 0 else 0
        
        fifty_two_high = info.get("fiftyTwoWeekHigh", 0)
        fifty_two_low = info.get("fiftyTwoWeekLow", 0)
        price_range = fifty_two_high - fifty_two_low
        price_position = round(((current_price - fifty_two_low) / price_range * 100), 1) if price_range > 0 else 0
        
        return {
            "ticker": ticker,
            "company": info.get("longName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "current_price": current_price,
            "market_cap": info.get("marketCap", 0),
            "float_shares": shares_float,
            "float_pct": float_pct,
            "short_interest": info.get("shortPercentOfFloat", 0) * 100 if info.get("shortPercentOfFloat") else 0,
            "short_ratio": info.get("shortRatio", 0),
            "volume": volume,
            "avg_volume": avg_volume,
            "volume_spike": volume_spike,
            "fifty_two_week_high": fifty_two_high,
            "fifty_two_week_low": fifty_two_low,
            "price_position": price_position,
            "analyst_target": info.get("targetMeanPrice", 0),
            "recommendation": info.get("recommendationKey", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "beta": info.get("beta", "N/A"),
        }
    except Exception as e:
        print(f"  ⚠️ Could not fetch {ticker}: {e}")
        return None

def get_reddit_mentions(ticker):
    subreddits = [
        "wallstreetbets",
        "stocks", 
        "investing",
        "options",
        "pennystocks"
    ]
    
    total_mentions = 0
    top_posts = []
    
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={ticker}&sort=new&limit=10&t=week"
            headers = {"User-Agent": "StockScanner/1.0"}
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                total_mentions += len(posts)
                
                for post in posts[:2]:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    score = post_data.get("score", 0)
                    if title:
                        top_posts.append(f"r/{sub}: {title[:80]} (score: {score})")
        except:
            continue
    
    return {
        "total_mentions": total_mentions,
        "top_posts": top_posts[:5]
    }

def get_news(ticker):
    try:
        url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        
        headlines = []
        for entry in feed.entries[:5]:
            headlines.append(entry.title)
        
        return headlines
    except:
        return []

def score_setup(data, reddit, news):
    score = 0
    reasons = []
    
    # Short interest scoring (key catalyst driver)
    if data["short_interest"] > 20:
        score += 30
        reasons.append(f"🔥 Very high short interest: {data['short_interest']:.1f}%")
    elif data["short_interest"] > 10:
        score += 20
        reasons.append(f"⚡ High short interest: {data['short_interest']:.1f}%")
    
    # Float scoring (low float = bigger moves)
    if data["float_pct"] < 10:
        score += 25
        reasons.append(f"🎯 Very low float: {data['float_pct']:.1f}% of shares")
    elif data["float_pct"] < 20:
        score += 15
        reasons.append(f"📊 Low float: {data['float_pct']:.1f}% of shares")
    
    # Volume spike scoring
    if data["volume_spike"] > 300:
        score += 20
        reasons.append(f"📈 Massive volume spike: {data['volume_spike']:.0f}% of average")
    elif data["volume_spike"] > 150:
        score += 10
        reasons.append(f"📊 Above average volume: {data['volume_spike']:.0f}% of average")
    
    # Short ratio (days to cover)
    if data["short_ratio"] and data["short_ratio"] > 5:
        score += 15
        reasons.append(f"⏱️ High days to cover: {data['short_ratio']:.1f} days")
    
    # Reddit buzz
    if reddit["total_mentions"] > 15:
        score += 20
        reasons.append(f"🚀 High Reddit buzz: {reddit['total_mentions']} mentions this week")
    elif reddit["total_mentions"] > 5:
        score += 10
        reasons.append(f"💬 Reddit mentions: {reddit['total_mentions']} this week")
    
    # Price position (near 52 week low = more room to run)
    if data["price_position"] < 20:
        score += 10
        reasons.append(f"📉 Near 52 week low: {data['price_position']:.1f}% up from low")
    
    # Analyst sentiment
    if data["recommendation"] in ["buy", "strongBuy"]:
        score += 10
        reasons.append(f"✅ Analyst rating: {data['recommendation']}")
    
    return score, reasons

def analyze_top_picks(picks):
    picks_text = ""
    for i, pick in enumerate(picks, 1):
        data = pick["data"]
        picks_text += f"""
PICK #{i}: {data['ticker']} - {data['company']}
Score: {pick['score']}/100
Price: ${data['current_price']}
Short Interest: {data['short_interest']:.1f}%
Float: {data['float_pct']:.1f}%
Volume Spike: {data['volume_spike']:.0f}%
Reddit Mentions: {pick['reddit']['total_mentions']}
Key Reasons: {', '.join(pick['reasons'][:3])}
Recent News: {pick['news'][0] if pick['news'] else 'No recent news'}
"""

    prompt = f"""
You are a catalyst-driven quant trader specializing in asymmetric setups.
Analyze these 5 stock picks and provide a brief but powerful analysis for each.

Focus on:
- Why this could be a squeeze candidate
- What catalyst could trigger the move
- Key risk to be aware of
- Your conviction level (Low/Medium/High)

{picks_text}

Format each pick exactly like this:

🎯 PICK #[N]: $[TICKER]
WHY IT WAS CHOSEN: [2 sentences on the setup]
POTENTIAL CATALYST: [What could trigger the move]
KEY RISK: [Biggest downside scenario]
CONVICTION: [Low/Medium/High] — [one line reason]

End with a 2 sentence PORTFOLIO NOTE about how these picks work together.

⚠️ DISCLAIMER: AI-generated research only. Not financial advice. 
Always do your own due diligence before trading.
"""

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "openrouter/auto",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    result = response.json()
    return result["choices"][0]["message"]["content"]

def main():
    print("=" * 60)
    print("   🤖 CATALYST-DRIVEN QUANT SCANNER")
    print("   Personal Motley Fool | Squeeze Setup Finder")
    print("=" * 60)
    print(f"⏰ Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Scanning {len(WATCHLIST)} tickers...")
    print("=" * 60)
    
    scored_picks = []
    
    for ticker in WATCHLIST:
        print(f"  🔍 Analyzing {ticker}...", end=" ")
        
        data = get_stock_data(ticker)
        if not data:
            continue
            
        reddit = get_reddit_mentions(ticker)
        news = get_news(ticker)
        score, reasons = score_setup(data, reddit, news)
        
        if score > 0:
            scored_picks.append({
                "ticker": ticker,
                "score": score,
                "data": data,
                "reddit": reddit,
                "news": news,
                "reasons": reasons
            })
            print(f"Score: {score}/100")
        else:
            print("No setup detected")
    
    # Sort by score and get top 5
    scored_picks.sort(key=lambda x: x["score"], reverse=True)
    top_5 = scored_picks[:5]
    
    print("\n" + "=" * 60)
    print("📊 RAW SCORES — TOP PICKS FOUND:")
    print("=" * 60)
    
    for i, pick in enumerate(top_5, 1):
        data = pick["data"]
        print(f"\n#{i} {data['ticker']} — Score: {pick['score']}/100")
        print(f"   💰 Price: ${data['current_price']}")
        print(f"   📉 Short Interest: {data['short_interest']:.1f}%")
        print(f"   🔢 Float: {data['float_pct']:.1f}%")
        print(f"   📊 Volume: {pick['data']['volume_spike']:.0f}% of average")
        print(f"   💬 Reddit Mentions: {pick['reddit']['total_mentions']}")
        for reason in pick["reasons"]:
            print(f"   {reason}")
    
    print("\n" + "=" * 60)
    print("🧠 AI ANALYSIS — GENERATING REPORT...")
    print("=" * 60)
    
    analysis = analyze_top_picks(top_5)
    print(f"\n{analysis}")
    print("\n" + "=" * 60)
    print(f"✅ Scan Complete: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

main()