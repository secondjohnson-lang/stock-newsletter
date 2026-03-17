import yfinance as yf
import os
import requests
import time
import re
import json
import sqlite3
from datetime import date

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "openrouter/hunter-alpha"

def init_db():
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            price REAL,
            day_change REAL,
            momentum_5d REAL,
            safety_from_low REAL,
            vol_ratio REAL,
            score INTEGER,
            signal INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS top_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            price REAL,
            signal INTEGER,
            odds TEXT,
            target TEXT,
            confidence INTEGER,
            story TEXT,
            bear TEXT,
            outcome TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_score(result):
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    display_score = (result['score'] - 50) * 2
    cursor.execute("""
        INSERT INTO daily_scores
        (date, ticker, price, day_change, momentum_5d, safety_from_low, vol_ratio, score, signal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(date.today()),
        result['ticker'],
        result['price'],
        result['day_change'],
        result['momentum_5d'],
        result['safety_from_low'],
        result['vol_ratio'],
        result['score'],
        display_score
    ))
    conn.commit()
    conn.close()

def save_pick(pick, parsed):
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    display_score = (pick['score'] - 50) * 2
    cursor.execute("""
        INSERT INTO top_picks
        (date, ticker, price, signal, odds, target, confidence, story, bear, outcome)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(date.today()),
        pick['ticker'],
        pick['price'],
        display_score,
        parsed.get('ODDS', ''),
        parsed.get('TARGET', ''),
        int(parsed.get('CONFIDENCE', '0') or '0'),
        parsed.get('STORY', ''),
        parsed.get('BEAR', ''),
        'pending'
    ))
    conn.commit()
    conn.close()

def score_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo", auto_adjust=True)
        if hist.empty or len(hist) < 6:
            return None
        price = round(float(hist['Close'].iloc[-1]), 2)
        prev = round(float(hist['Close'].iloc[-2]), 2)
        day_change = round(((price - prev) / prev) * 100, 2)
        week_ago = float(hist['Close'].iloc[-6])
        momentum = round(((price - week_ago) / week_ago) * 100, 2)
        low_52 = float(hist['Close'].min())
        safety = round(((price - low_52) / low_52) * 100, 2)
        avg_vol = float(hist['Volume'].mean())
        today_vol = float(hist['Volume'].iloc[-1])
        vol_ratio = round(today_vol / avg_vol, 2) if avg_vol > 0 else 1.0
        score = 50
        if momentum > 0: score += 15
        if momentum > 5: score += 10
        if safety < 30: score += 15
        if vol_ratio > 1.5: score += 10
        if day_change < -5: score -= 20
        if day_change > 3: score += 10
        score = max(0, min(100, score))
        return {
            "ticker": ticker,
            "price": price,
            "day_change": day_change,
            "momentum_5d": momentum,
            "safety_from_low": safety,
            "vol_ratio": vol_ratio,
            "score": score
        }
    except:
        return None

SYSTEM_PROMPT = """You are a financial newsletter writer and quantitative analyst. You write for curious, intelligent readers who are not finance professionals. Your job is to analyze stock signal data and return structured analysis in a specific format.

You have four hard rules you never break:
1. You always respond in the exact format requested. No preamble, no explanation, no extra text before ODDS.
2. You never recommend a stock with a day change worse than -8% unless the 5-day momentum is strongly positive.
3. You always assign lower confidence when signals contradict each other.
4. Your STORY must always follow this exact five sentence structure:
   - Sentence 1: What the company does in plain english, no jargon
   - Sentence 2: Why this company matters to the US economy or a major trend
   - Sentence 3: One surprising or interesting fact about the company or its sector
   - Sentence 4: What is happening with this stock right now and why
   - Sentence 5: Forward looking — where could this go and why should someone care

You understand moneyline odds:
- +200 means a 20% gain in 60 days is unlikely but possible
- +100 means roughly even odds of hitting the target
- -150 means you expect the target to be hit more often than not

Your confidence score means:
- 5: All signals agree, high conviction
- 4: Most signals agree, minor contradictions
- 3: Mixed signals, proceed with caution
- 2: Signals contradict, low conviction
- 1: Do not recommend, data is too conflicted"""

def build_prompt(pick):
    contradictions = []
    if pick['day_change'] < -3 and pick['momentum_5d'] > 3:
        contradictions.append("down today but positive weekly momentum")
    if pick['score'] > 70 and pick['day_change'] < -5:
        contradictions.append("high score but significant daily drop")
    if pick['vol_ratio'] < 0.5 and pick['score'] > 70:
        contradictions.append("high score but very low volume")
    contradiction_note = ""
    if contradictions:
        contradiction_note = f"\nWARNING - Contradicting signals detected: {', '.join(contradictions)}"
    return f"""Analyze this stock and respond in EXACTLY this format, no other text:

ODDS: [moneyline number only, e.g. +150 or -110]
TARGET: $[dollar amount only, e.g. $184.20]
CONFIDENCE: [single number 1-5 only]
STORY: [exactly 5 sentences following the structure in your instructions]
BEAR: [exactly 1 sentence about the biggest risk to this trade]

Stock data:
TICKER: {pick['ticker']}
PRICE: ${pick['price']}
DAY_CHANGE: {pick['day_change']}%
MOMENTUM_5D: {pick['momentum_5d']}%
SAFETY_FROM_LOW: {pick['safety_from_low']}%
VOLUME_RATIO: {pick['vol_ratio']}x
SCORE: {pick['score']}/100{contradiction_note}"""

def validate_response(text):
    required = ["ODDS:", "TARGET:", "CONFIDENCE:", "STORY:", "BEAR:"]
    for field in required:
        if field not in text:
            return False, f"Missing field: {field}"
    odds_match = re.search(r'ODDS:\s*([+-]\d+)', text)
    if not odds_match:
        return False, "ODDS not in correct format"
    target_match = re.search(r'TARGET:\s*\$[\d.]+', text)
    if not target_match:
        return False, "TARGET not in correct format"
    confidence_match = re.search(r'CONFIDENCE:\s*([1-5])', text)
    if not confidence_match:
        return False, "CONFIDENCE must be a number 1-5"
    return True, "OK"

def get_analysis(pick):
    prompt = build_prompt(pick)
    for attempt in range(3):
        try:
            time.sleep(3)
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 400,
                    "temperature": 0.3
                }
            )
            data = response.json()
            if 'choices' not in data:
                if attempt < 2:
                    time.sleep(5)
                    continue
                return None, f"API error: {data.get('error', {}).get('message', 'unknown')}"
            content = data['choices'][0]['message'].get('content', '')
            if not content:
                continue
            is_valid, reason = validate_response(content)
            if is_valid:
                return content.strip(), None
            else:
                if attempt < 2:
                    continue
                return None, f"Invalid format after 3 attempts: {reason}"
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
                continue
            return None, f"Exception: {e}"
    return None, "Max retries exceeded"

def parse_analysis(text):
    lines = {}
    current_key = None
    current_value = []
    for line in text.strip().split('\n'):
        if ':' in line:
            first_word = line.split(':')[0].strip()
            if first_word in ['ODDS', 'TARGET', 'CONFIDENCE', 'STORY', 'BEAR']:
                if current_key:
                    lines[current_key] = ' '.join(current_value).strip()
                current_key = first_word
                current_value = [line.partition(':')[2].strip()]
            else:
                if current_key:
                    current_value.append(line.strip())
        else:
            if current_key:
                current_value.append(line.strip())
    if current_key:
        lines[current_key] = ' '.join(current_value).strip()
    return lines

init_db()

print("\n====== YOUR MORNING WATCHLIST ======\n")

all_picks = []

for sector, tickers in watchlist.items():
    print(f"--- {sector} ---")
    for ticker in tickers:
        result = score_stock(ticker)
        if result:
            arrow = "▲" if result['day_change'] > 0 else "▼"
            display_score = (result['score'] - 50) * 2
            sign = "+" if display_score >= 0 else ""
            print(f"  {result['ticker']:<6} ${result['price']:<10} {arrow} {result['day_change']}%  |  Signal: {sign}{display_score}")
            save_score(result)
            all_picks.append(result)
        else:
            print(f"  {ticker:<6} data unavailable")
    print()

top3 = sorted(all_picks, key=lambda x: x['score'], reverse=True)[:3]

print("====== TOP 3 PICKS TODAY ======\n")
for i, pick in enumerate(top3, 1):
    display_score = (pick['score'] - 50) * 2
    sign = "+" if display_score >= 0 else ""
    print(f"{i}. {pick['ticker']} — Signal {sign}{display_score} | ${pick['price']}")
    analysis, error = get_analysis(pick)
    if analysis:
        parsed = parse_analysis(analysis)
        confidence = int(parsed.get('CONFIDENCE', '0') or '0')
        confidence_bar = "█" * confidence + "░" * (5 - confidence)
        print(f"   ODDS:       {parsed.get('ODDS', 'N/A')}")
        print(f"   TARGET:     {parsed.get('TARGET', 'N/A')}")
        print(f"   CONFIDENCE: {confidence_bar} {confidence}/5")
        print(f"   STORY:")
        story = parsed.get('STORY', 'N/A')
        words = story.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 80:
                print(f"      {line}")
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            print(f"      {line}")
        print(f"   BEAR:       {parsed.get('BEAR', 'N/A')}")
        save_pick(pick, parsed)
    else:
        print(f"   Analysis unavailable: {error}")
    print()

print("====================================\n")
print(f"Data saved to stocks.db — {str(date.today())}")