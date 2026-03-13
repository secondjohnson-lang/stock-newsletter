import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import threading
import os
import csv
import json
import requests
import yfinance as yf
import feedparser
from datetime import datetime
from pathlib import Path

api_key = os.getenv("OPENROUTER_API_KEY")

# ═══════════════════════════════════════════════════════════
#  PATHS — All data saved to AI_Projects folder
# ═══════════════════════════════════════════════════════════
BASE_DIR    = Path(__file__).parent
HISTORY_CSV = BASE_DIR / "scan_history.csv"
HISTORY_LOG = BASE_DIR / "scan_log.txt"
PORTFOLIO_F = BASE_DIR / "portfolio.json"

# ═══════════════════════════════════════════════════════════
#  MASTER THESIS
# ═══════════════════════════════════════════════════════════
MASTER_THESIS = """
CATALYST-DRIVEN PORTFOLIO STRATEGY — SOURCE OF TRUTH (March 2026)
Investor: Mechanical Catalyst Strategist
Time Horizon: 3-6 months
Core Principle: MECHANICAL upside only — where market participants are FORCED to buy.
NOT value investing. NOT momentum chasing. FORCED BUYER MECHANICS only.

THE 5-CRITERIA FRAMEWORK (must meet 3 of 5 to qualify):
1. Short Interest > 10% of float
2. Low Float — under 30M shares preferred, under 10M = premium
3. Hard Catalyst Deadline — PDUFA, Phase 3 data, infrastructure rollout, index inclusion
4. Forced Buyer Mechanic — Accelerated Approval, Priority Review, Strategic Investment,
   Index Inclusion, Convertible squeeze, Short thesis collapse event
5. Clean Balance Sheet — no toxic dilution, no ATM offerings, adequate cash runway

ACTIVE ALPHA-5 PORTFOLIO:
- NBIS $800: Nvidia $2B investment March 11 2026, forced re-rating of 20% short interest
- VERA $700: PDUFA July 7 2026, Priority Review + $800M cash removes dilution risk
- VKTX $500: Phase 3 Oral Q3 2026, GLP-1 obesity speculative wave
- CAPR $500: PDUFA Aug 22 2026, micro-cap float binary DMD approval
- RKLB $500: Neutron Qualification Summer 2026, Q4 maiden flight speculative cycle

WATCHLIST (not yet entered):
- IOVA: Blue Sky breakout, 40% SI, entry $4.30-$4.50 wait for 50-day MA pullback
- BLNK: Deep value squeeze if Q4 earnings beats guidance

REJECTED — DO NOT SUGGEST:
- MNMD: catalyst drift, pushed to late 2026
- ARWR: float dilution risk, timeline mismatch
- CRSP: $550M convertible note = SQUEEZE KILLER
- SAVA: Phase 3 failure January 2026, dead catalyst

FORCED BUYER KEYWORDS (positive): Accelerated Approval, Priority Review, Index Inclusion,
Strategic Investment, Short Squeeze, Days to Cover, Partnership, Acquisition Target
NEGATIVE SIGNALS: Convertible Offering, ATM Offering, Dilution, Trial Failure,
Complete Response Letter, Catalyst Drift, Shelf Registration
"""

# ═══════════════════════════════════════════════════════════
#  DEFAULT WATCHLIST
# ═══════════════════════════════════════════════════════════
WATCHLIST = [
    "NBIS","VERA","VKTX","CAPR","RKLB",
    "IOVA","BLNK","ACAD","NVAX","BEAM",
    "EDIT","NTLA","FATE","FFIE","WKHS",
    "PLUG","CHPT","SPWR","CLOV","OPEN",
    "BYND","KOSS","NVAX","MARA","RIOT",
    "IONQ","QBTS","RGTI","SOUN","BBAI"
]

# ═══════════════════════════════════════════════════════════
#  PORTFOLIO MANAGER
# ═══════════════════════════════════════════════════════════
class Portfolio:
    def __init__(self):
        self.holdings = {}
        self._load()

    def _load(self):
        if PORTFOLIO_F.exists():
            try:
                self.holdings = json.loads(PORTFOLIO_F.read_text())
            except:
                self.holdings = {}

    def _save(self):
        PORTFOLIO_F.write_text(json.dumps(self.holdings, indent=2))

    def load_from_schwab_csv(self, filepath):
        imported = []
        try:
            with open(filepath, newline="", encoding="utf-8-sig") as f:
                content = f.read()
            lines = content.split("\n")
            data_lines = []
            in_positions = False
            for line in lines:
                if "Symbol" in line and "Quantity" in line:
                    in_positions = True
                if in_positions and line.strip():
                    data_lines.append(line)
                if in_positions and line.strip() == "":
                    break
            if data_lines:
                reader = csv.DictReader(data_lines)
                for row in reader:
                    symbol = row.get("Symbol","").strip().upper()
                    if symbol and not symbol.startswith("--") and len(symbol) <= 6:
                        qty   = row.get("Quantity","0").replace(",","").strip()
                        cost  = row.get("Average Cost Basis","0").replace("$","").replace(",","").strip()
                        value = row.get("Market Value","0").replace("$","").replace(",","").strip()
                        try:
                            self.holdings[symbol] = {
                                "shares":    float(qty)  if qty  else 0,
                                "cost":      float(cost) if cost else 0,
                                "value":     float(value)if value else 0,
                                "imported":  datetime.now().strftime("%Y-%m-%d")
                            }
                            imported.append(symbol)
                        except:
                            pass
            self._save()
        except Exception as e:
            return [], str(e)
        return imported, None

    def add_manual(self, ticker):
        ticker = ticker.upper().strip()
        if ticker:
            self.holdings[ticker] = {"shares":0,"cost":0,"value":0,
                                     "imported":datetime.now().strftime("%Y-%m-%d")}
            self._save()

    def remove(self, ticker):
        self.holdings.pop(ticker.upper(), None)
        self._save()

    def owns(self, ticker):
        return ticker.upper() in self.holdings

    def tickers(self):
        return list(self.holdings.keys())


# ═══════════════════════════════════════════════════════════
#  HISTORY LOGGER
# ═══════════════════════════════════════════════════════════
class HistoryLogger:
    def __init__(self):
        if not HISTORY_CSV.exists():
            with open(HISTORY_CSV,"w",newline="") as f:
                w = csv.writer(f)
                w.writerow(["date","ticker","company","score","criteria_met",
                            "short_interest","float_m","volume_spike",
                            "catalyst_detected","conviction","price","verdict"])

    def log_pick(self, data, score, criteria_met, conviction, verdict_line):
        with open(HISTORY_CSV,"a",newline="") as f:
            w = csv.writer(f)
            w.writerow([
                datetime.now().strftime("%Y-%m-%d"),
                data["ticker"], data["company"],
                score, criteria_met,
                f"{data['short_interest']:.1f}",
                f"{data['float_millions']:.1f}",
                f"{data['volume_spike']:.0f}",
                "YES" if data.get("catalyst_hit") else "NO",
                conviction,
                f"{data['current_price']:.3f}",
                verdict_line[:120]
            ])

    def log_session(self, session_text):
        with open(HISTORY_LOG,"a") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"SESSION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*70}\n")
            f.write(session_text)
            f.write("\n")


# ═══════════════════════════════════════════════════════════
#  DATA LAYER
# ═══════════════════════════════════════════════════════════
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info
        cp    = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        pc    = info.get("previousClose", cp)
        chg   = ((cp - pc) / pc * 100) if pc else 0
        av    = info.get("averageVolume", 1)
        vol   = info.get("volume", 0)
        vs    = round(vol/av*100,1) if av > 0 else 0
        sf    = info.get("floatShares", 0)
        so    = info.get("sharesOutstanding", 1)
        fm    = round(sf/1_000_000,2) if sf else 0
        fp    = round(sf/so*100,1)    if so > 0 else 0
        hi52  = info.get("fiftyTwoWeekHigh", 0)
        lo52  = info.get("fiftyTwoWeekLow", 0)
        rng   = hi52 - lo52
        pos   = round((cp-lo52)/rng*100,1) if rng > 0 else 0
        si    = info.get("shortPercentOfFloat",0)*100 if info.get("shortPercentOfFloat") else 0
        dtc   = info.get("shortRatio",0) or 0
        ma50  = info.get("fiftyDayAverage",0)
        ma200 = info.get("twoHundredDayAverage",0)
        tgt   = info.get("targetMeanPrice",0) or 0
        ups   = round((tgt-cp)/cp*100,1) if tgt and cp else 0
        return {
            "ticker":          ticker,
            "company":         info.get("longName", ticker),
            "sector":          info.get("sector","N/A"),
            "industry":        info.get("industry","N/A"),
            "current_price":   cp,
            "day_change_pct":  chg,
            "market_cap":      info.get("marketCap",0) or 0,
            "float_millions":  fm,
            "float_pct":       fp,
            "short_interest":  si,
            "short_ratio":     dtc,
            "volume":          vol,
            "avg_volume":      av,
            "volume_spike":    vs,
            "fifty_two_high":  hi52,
            "fifty_two_low":   lo52,
            "price_position":  pos,
            "ma50":            ma50,
            "ma200":           ma200,
            "above_ma50":      cp > ma50  if ma50  else False,
            "above_ma200":     cp > ma200 if ma200 else False,
            "analyst_target":  tgt,
            "analyst_upside":  ups,
            "recommendation":  info.get("recommendationKey","N/A"),
            "num_analysts":    info.get("numberOfAnalystOpinions",0) or 0,
            "summary":         info.get("longBusinessSummary","N/A"),
            "catalyst_hit":    False,
        }
    except:
        return None

def get_reddit(ticker):
    subs  = ["wallstreetbets","stocks","investing","options","pennystocks"]
    total = 0
    posts = []
    bull  = ["moon","calls","buy","bull","squeeze","long","rocket","catalyst","approval","breakout"]
    bear  = ["puts","short","dump","bear","sell","dilution","fraud","failure","offering","bagholders"]
    bc = bc2 = 0
    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={ticker}&sort=new&limit=10&t=week"
            r   = requests.get(url, headers={"User-Agent":"QuantScanner/3.0"}, timeout=5)
            if r.status_code == 200:
                ch = r.json().get("data",{}).get("children",[])
                total += len(ch)
                for p in ch[:2]:
                    pd = p.get("data",{})
                    t  = pd.get("title","")
                    if t:
                        posts.append({"sub":sub,"title":t[:90],"score":pd.get("score",0)})
                    tl = t.lower()
                    for w in bull:
                        if w in tl: bc  += 1
                    for w in bear:
                        if w in tl: bc2 += 1
        except:
            continue
    tot = bc + bc2
    sent = round(bc/tot*100) if tot > 0 else 50
    return {"total":total,"posts":posts[:3],"bull":bc,"bear":bc2,"sentiment":sent}

def get_news(ticker):
    try:
        url  = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        return [{"title":e.title,"pub":e.get("published","")} for e in feed.entries[:6]]
    except:
        return []


# ═══════════════════════════════════════════════════════════
#  SCORING ENGINE
# ═══════════════════════════════════════════════════════════
def score_setup(data, reddit, news):
    score = 0
    cm    = 0
    reasons   = []
    penalties = []
    news_text = " ".join(n["title"].lower() for n in news)

    # Criterion 1 — Short Interest
    si = data["short_interest"]
    if si > 20:
        score += 30; cm += 1
        reasons.append(f"CRIT 1 PASS: Short interest {si:.1f}% — extreme squeeze fuel")
    elif si > 10:
        score += 20; cm += 1
        reasons.append(f"CRIT 1 PASS: Short interest {si:.1f}% — qualifies >10%")
    elif si > 5:
        score += 8
        reasons.append(f"CRIT 1 NEAR: Short interest {si:.1f}% — below 10% threshold")
    else:
        reasons.append(f"CRIT 1 FAIL: Short interest {si:.1f}%")

    # Criterion 2 — Float
    fm = data["float_millions"]
    if fm < 10:
        score += 25; cm += 1
        reasons.append(f"CRIT 2 PASS: Float {fm:.1f}M — micro float premium")
    elif fm < 30:
        score += 18; cm += 1
        reasons.append(f"CRIT 2 PASS: Float {fm:.1f}M — low float qualifies")
    elif fm < 60:
        score += 8
        reasons.append(f"CRIT 2 NEAR: Float {fm:.1f}M — manageable")
    else:
        reasons.append(f"CRIT 2 FAIL: Float {fm:.1f}M — too large")

    # Criterion 3 — Hard Catalyst
    cat_kw = ["pdufa","fda","approval","phase 3","phase iii","trial","clinical",
              "data","catalyst","rollout","launch","earnings","acquisition",
              "partnership","contract","investment","index","inclusion"]
    hits = sum(1 for k in cat_kw if k in news_text)
    if hits >= 3:
        score += 20; cm += 1
        data["catalyst_hit"] = True
        reasons.append(f"CRIT 3 PASS: Hard catalyst — {hits} keyword hits in headlines")
    elif hits >= 1:
        score += 10
        reasons.append(f"CRIT 3 NEAR: Possible catalyst — {hits} keyword hits")
    else:
        reasons.append(f"CRIT 3 FAIL: No hard catalyst in recent news")

    # Criterion 4 — Forced Buyer Mechanic
    forced_kw = ["accelerated approval","priority review","index inclusion",
                 "strategic investment","short squeeze","nvidia","acquisition",
                 "takeover","partnership","forced"]
    neg_kw    = ["dilution","atm offering","convertible note","shelf offering",
                 "trial failure","complete response","rejected","at-the-money"]
    fhits = sum(1 for k in forced_kw if k in news_text)
    nhits = sum(1 for k in neg_kw    if k in news_text)
    if fhits >= 1 and nhits == 0:
        score += 18; cm += 1
        reasons.append(f"CRIT 4 PASS: Forced buyer mechanic detected in news")
    elif nhits >= 1:
        score -= 20
        penalties.append(f"CRIT 4 FAIL: DILUTION/NEGATIVE signal — squeeze killer (-20pts)")
    else:
        reasons.append(f"CRIT 4 UNCONFIRMED: No forced buyer mechanic in news")

    # Criterion 5 — Clean Balance Sheet proxy
    mc = data["market_cap"]
    an = data["num_analysts"]
    if an >= 3 and mc > 50_000_000:
        score += 12; cm += 1
        reasons.append(f"CRIT 5 PASS: {an} analysts, institutional awareness")
    elif mc > 20_000_000:
        score += 6
        reasons.append(f"CRIT 5 NEAR: Limited coverage — verify balance sheet manually")
    else:
        reasons.append(f"CRIT 5 UNVERIFIED: Micro-cap, check cash runway manually")

    # Bonus signals
    vs = data["volume_spike"]
    if vs > 300:
        score += 15
        reasons.append(f"BONUS: Volume {vs:.0f}% of average — ignition signal")
    elif vs > 150:
        score += 8
        reasons.append(f"BONUS: Volume {vs:.0f}% of average")

    dtc = data["short_ratio"]
    if dtc > 7:
        score += 12
        reasons.append(f"BONUS: Days-to-cover {dtc:.1f} — shorts deeply trapped")
    elif dtc > 4:
        score += 6
        reasons.append(f"BONUS: Days-to-cover {dtc:.1f}")

    if reddit["total"] > 15 and reddit["sentiment"] > 60:
        score += 10
        reasons.append(f"BONUS: Reddit {reddit['total']} mentions, {reddit['sentiment']}% bullish")
    elif reddit["total"] > 5:
        score += 5
        reasons.append(f"BONUS: Reddit {reddit['total']} mentions")

    if data["analyst_upside"] > 80:
        score += 8
        reasons.append(f"BONUS: Analyst target +{data['analyst_upside']:.0f}% upside")

    if mc > 5_000_000_000:
        score -= 15
        penalties.append("PENALTY: Large cap (-15pts) — harder to squeeze mechanically")

    score = max(0, min(100, score))
    return score, cm, reasons, penalties

def get_conviction(score, cm):
    if cm >= 4 and score >= 75: return "HIGH",    "3-5% of portfolio",      "high"
    if cm >= 3 and score >= 55: return "MEDIUM",  "1-3% of portfolio",      "medium"
    if cm >= 2 and score >= 35: return "LOW",      "0.5-1% of portfolio",    "low"
    return                             "SPECULATIVE","<0.5% lottery ticket", "spec"


# ═══════════════════════════════════════════════════════════
#  8-AGENT CREW
# ═══════════════════════════════════════════════════════════
MODEL = "openrouter/auto"

def call_ai(prompt, max_tokens=800, retries=3):
    import time
    for attempt in range(retries):
        try:
            time.sleep(2)
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": MODEL,
                      "messages":[{"role":"user","content":prompt}],
                      "max_tokens": max_tokens},
                timeout=30
            )
            data = r.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            elif "error" in data:
                if attempt < retries - 1:
                    time.sleep(6 * (attempt + 1))
                    continue
                return f"[Rate limited — retried {retries}x]"
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            return f"[AI Error: {e}]"
    return "[AI unavailable after retries]"

def build_data_block(data, reddit, news, score, cm, reasons, penalties):
    news_text   = "\n".join(f"- {n['title']}" for n in news[:5]) or "None"
    reddit_text = "\n".join(f"- [{p['sub']}] {p['title']}" for p in reddit["posts"]) or "None"
    reason_text = "\n".join(reasons)
    penalty_text= "\n".join(penalties) or "None"
    return f"""
TICKER: {data['ticker']} | {data['company']}
SECTOR: {data['sector']} | {data['industry']}
PRICE: ${data['current_price']:.3f} | Day: {data['day_change_pct']:+.1f}%
52wk: ${data['fifty_two_low']:.2f}–${data['fifty_two_high']:.2f} | Position: {data['price_position']:.0f}%
MA50/200: ${data['ma50']:.2f} / ${data['ma200']:.2f}
Short Interest: {data['short_interest']:.1f}% | DTC: {data['short_ratio']:.1f} | Float: {data['float_millions']:.1f}M
Volume: {data['volume_spike']:.0f}% of average | Market Cap: ${data['market_cap']:,}
Reddit: {reddit['total']} mentions | {reddit['sentiment']}% bullish | {reddit['bull']} bull / {reddit['bear']} bear
Analyst Target: ${data['analyst_target']:.2f} (+{data['analyst_upside']:.0f}%) | {data['num_analysts']} analysts | {data['recommendation']}
CRITERIA MET: {cm}/5 | SCORE: {score}/100
SCORECARD:\n{reason_text}
PENALTIES:\n{penalty_text}
NEWS:\n{news_text}
REDDIT:\n{reddit_text}
"""

# Agent 1 — Scout
def agent_scout(data, reddit, news, score, cm, owned_tickers):
    db = build_data_block(data, reddit, news, score, cm, [], [])
    owned_str = ", ".join(owned_tickers[:20]) if owned_tickers else "None loaded"
    return call_ai(f"""{MASTER_THESIS}

AGENT 1 — SCOUT
Your job: Determine if this ticker is worth investigating further.
Check: Is it in the portfolio already? Does it pass the basic smell test?
Portfolio already owned: {owned_str}

{db}

Respond in exactly 2 sentences:
Sentence 1: Is this worth investigating? (Yes/No and why in plain English)
Sentence 2: One sentence on what makes this interesting OR why to skip it.
Be brutal. Most tickers should be rejected at this stage.""", 200)

# Agent 2 — Quant
def agent_quant(data, reddit, news, score, cm, reasons, penalties):
    db = build_data_block(data, reddit, news, score, cm, reasons, penalties)
    return call_ai(f"""{MASTER_THESIS}

AGENT 2 — QUANT ANALYST
Your job: Evaluate the mechanical squeeze setup using the 3-of-5 framework.
Focus purely on the numbers. No narrative. No hope. Just mechanics.

{db}

Respond in this format:
CRITERIA ASSESSMENT: [Which of the 5 criteria are confirmed, which are not — one line each]
MECHANICAL EDGE: [What is the actual forced buyer mechanic here, if any — one sentence]
QUANT VERDICT: [Pass/Fail the 3-of-5 test and why — one sentence]""", 300)

# Agent 3 — Bull
def agent_bull(data, reddit, news, score, cm):
    db = build_data_block(data, reddit, news, score, cm, [], [])
    return call_ai(f"""{MASTER_THESIS}

AGENT 3 — BULL ADVOCATE
Your job: Make the STRONGEST possible case for buying this stock RIGHT NOW.
Anchor every argument in forced buyer mechanics, not hope or narrative.
If you cannot find 3 strong mechanical reasons, say so honestly.

{db}

Format:
BULL ARGUMENT 1: [Specific mechanical reason to buy]
BULL ARGUMENT 2: [Specific mechanical reason to buy]
BULL ARGUMENT 3: [Specific mechanical reason to buy]
BULL CATALYST: [The single event that could trigger the move]""", 350)

# Agent 4 — Bear
def agent_bear(data, reddit, news, score, cm):
    db = build_data_block(data, reddit, news, score, cm, [], [])
    return call_ai(f"""{MASTER_THESIS}

AGENT 4 — BEAR ADVOCATE
Your job: Destroy the bull case. Find every reason this trade fails.
Look for: dilution risk, catalyst drift, crowded trade, weak balance sheet,
failed setups, regulatory risk, competitive threats.

{db}

Format:
BEAR ARGUMENT 1: [Specific reason this trade fails]
BEAR ARGUMENT 2: [Specific reason this trade fails]
BEAR ARGUMENT 3: [Specific reason this trade fails]
BEAR KILL SWITCH: [The single event that would make this a zero]""", 350)

# Agent 5 — Catalyst Tracker
def agent_catalyst(data, news):
    news_text = "\n".join(f"- {n['title']}" for n in news[:6]) or "None"
    return call_ai(f"""{MASTER_THESIS}

AGENT 5 — CATALYST TRACKER
Your job: Identify specific upcoming catalysts for this ticker.
Look for hard dates: PDUFA, earnings, trial readouts, index rebalancing,
product launches, regulatory decisions, contract announcements.

TICKER: {data['ticker']} | {data['company']}
SECTOR: {data['sector']}
NEWS:\n{news_text}

Format:
CATALYST 1: [Event] — [Estimated date or timeframe]
CATALYST 2: [Event] — [Estimated date or timeframe]  
CATALYST 3: [Event] — [Estimated date or timeframe]
MOST CRITICAL: [The one catalyst that matters most and why]
CATALYST STATUS: [Are catalysts upcoming, imminent, or already passed?]""", 300)

# Agent 6 — Risk Manager
def agent_risk(data, reddit, news, score, cm, conviction):
    db = build_data_block(data, reddit, news, score, cm, [], [])
    conv, alloc, _ = conviction
    return call_ai(f"""{MASTER_THESIS}

AGENT 6 — RISK MANAGER
Your job: Size the bet correctly and flag concentration risk.
Conviction level from scoring: {conv} | Suggested allocation: {alloc}

{db}

Format:
POSITION SIZE: [Confirm or adjust the suggested allocation and why]
STOP LOSS: [Specific price level or condition to exit — no vague answers]
MAX LOSS: [If this goes wrong what is realistic downside %]
CONCENTRATION RISK: [Does adding this create sector or thesis concentration?]
RISK VERDICT: [One sentence — is the risk/reward worth it at current price?]""", 300)

# Agent 7 — Judge
def agent_judge(ticker, scout, quant, bull, bear, catalyst, risk, score, cm):
    return call_ai(f"""{MASTER_THESIS}

AGENT 7 — JUDGE
You have received analysis from 6 specialized agents on {ticker}.
Your job: Read all 6 reports and make the final verdict.
Be decisive. Traders need clear direction, not more analysis paralysis.

AGENT 1 SCOUT:\n{scout}

AGENT 2 QUANT:\n{quant}

AGENT 3 BULL:\n{bull}

AGENT 4 BEAR:\n{bear}

AGENT 5 CATALYST:\n{catalyst}

AGENT 6 RISK:\n{risk}

CRITERIA MET: {cm}/5 | SCORE: {score}/100

Respond in this EXACT format:

JUDGE VERDICT: [ADD / WATCH / AVOID]
THESIS ALIGNMENT: [Does this fit the Master Thesis? Yes/Partial/No]
ONE SENTENCE WHY: [The single most important reason for your verdict]
ENTRY CONDITION: [Specific price or event that would trigger entry]
EXIT CONDITION: [Specific price or event that triggers exit]
FINAL CALL: [One punchy sentence a trader can act on immediately]

⚠️ AI research only. Not financial advice.""", 400)

# Agent 8 — Improvement Scout
def agent_improvement(session_picks, session_gaps, watchlist_size, portfolio_size):
    picks_text = "\n".join(f"- {p['ticker']}: score {p['score']}, criteria {p['cm']}/5, verdict: {p.get('verdict','N/A')[:60]}" for p in session_picks)
    gaps_text  = "\n".join(f"- {g}" for g in session_gaps) if session_gaps else "None noted"
    return call_ai(f"""{MASTER_THESIS}

AGENT 8 — IMPROVEMENT SCOUT
You just completed a full scan session. Your job: identify gaps, weaknesses,
and improvements in the scanning process. Output specific prompts the user
can bring to their developer (Claude) to improve the tool next week.

SESSION STATS:
- Tickers scanned: {watchlist_size}
- Portfolio filtered: {portfolio_size} owned tickers excluded
- New discoveries analyzed: {len(session_picks)}

TOP PICKS THIS SESSION:
{picks_text}

GAPS NOTED DURING SESSION:
{gaps_text}

Respond in this EXACT format:

━━━ WEEKLY IMPROVEMENT REPORT ━━━
Session: {datetime.now().strftime('%Y-%m-%d')}

DATA GAPS FOUND:
[List 2-3 specific pieces of data the tool couldn't find but needed]

SCORING IMPROVEMENTS:
[List 1-2 specific changes to the scoring logic that would improve accuracy]

NEW FEATURES NEEDED:
[List 2-3 specific features that would make next week's session better]

PROMPTS FOR YOUR DEVELOPER:
[List 3-5 copy-paste ready prompts the user can bring to Claude next week
 to improve the tool. Make them specific and actionable.]

OVERALL ASSESSMENT:
[One paragraph honest assessment of how well the tool performed this session
 and what would have the highest impact on improving it]""", 600)


# ═══════════════════════════════════════════════════════════
#  GUI — Clean Black on White
# ═══════════════════════════════════════════════════════════
BG      = "#FFFFFF"
BG2     = "#F5F5F5"
BG3     = "#EEEEEE"
FG      = "#111111"
FG_DIM  = "#777777"
ACCENT  = "#1a1aff"
SIGNAL  = "#cc0000"
BORDER  = "#CCCCCC"
FONT    = "Courier New"

class QuantDashboard:
    def __init__(self, root):
        self.root       = root
        self.portfolio  = Portfolio()
        self.logger     = HistoryLogger()
        self.scanning   = False
        self.session_picks= []
        self.session_gaps = []
        self.session_log  = ""
        self.root.title("SQUEEZE FINDER v3.0")
        self.root.geometry("1200x860")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self._build_ui()

    def _build_ui(self):
        # ── HEADER ──
        hdr = tk.Frame(self.root, bg=BG2, pady=12, relief="flat")
        hdr.pack(fill="x")
        tk.Label(hdr, text="SQUEEZE FINDER  v3.0",
            font=(FONT, 22, "bold"), fg=FG, bg=BG2).pack()
        tk.Label(hdr,
            text="CATALYST-DRIVEN  ·  FORCED BUYER MECHANICS  ·  8-AGENT CREW  ·  THESIS-AWARE",
            font=(FONT, 10), fg=FG_DIM, bg=BG2).pack()
        tk.Frame(self.root, bg=FG, height=2).pack(fill="x")

        # ── CONTROLS ──
        ctrl = tk.Frame(self.root, bg=BG3, pady=10)
        ctrl.pack(fill="x")
        row1 = tk.Frame(ctrl, bg=BG3)
        row1.pack(padx=20)

        tk.Label(row1, text="TICKER:", font=(FONT,12,"bold"),
            fg=FG, bg=BG3).pack(side="left", padx=(0,6))
        self.ticker_entry = tk.Entry(row1,
            font=(FONT,14,"bold"), width=8,
            bg=BG, fg=FG, insertbackground=FG,
            relief="solid", bd=1)
        self.ticker_entry.pack(side="left", padx=4)
        self.ticker_entry.bind("<Return>", lambda e: self._run_single_thread())

        self._btn(row1,"ANALYZE",    FG,    BG,   self._run_single_thread).pack(side="left",padx=4)
        self._btn(row1,"FULL SCAN",  ACCENT,BG,   self._run_full_scan_thread).pack(side="left",padx=4)
        self._btn(row1,"ALPHA-5",    FG,    BG,   self._run_alpha5_thread).pack(side="left",padx=4)
        self._btn(row1,"LOAD CSV",   FG,    BG,   self._load_csv).pack(side="left",padx=4)
        self._btn(row1,"CLEAR",      FG_DIM,BG,   self.clear_output).pack(side="left",padx=4)

        # Portfolio status
        self.portfolio_lbl = tk.Label(ctrl,
            text=self._portfolio_status(),
            font=(FONT, 9), fg=FG_DIM, bg=BG3)
        self.portfolio_lbl.pack()

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ── STATUS ──
        self.status_var = tk.StringVar(value="READY — Load your Schwab CSV then run a scan")
        self.status_lbl = tk.Label(self.root,
            textvariable=self.status_var,
            font=(FONT, 10), fg=FG, bg=BG2,
            anchor="w", padx=14, pady=5)
        self.status_lbl.pack(fill="x")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ── OUTPUT ──
        out = tk.Frame(self.root, bg=BG)
        out.pack(fill="both", expand=True, padx=0, pady=0)

        self.output = scrolledtext.ScrolledText(
            out,
            font=(FONT, 12),
            bg=BG, fg=FG,
            insertbackground=FG,
            wrap=tk.WORD,
            padx=20, pady=16,
            relief="flat", bd=0,
            spacing1=3, spacing3=3
        )
        self.output.pack(fill="both", expand=True)

        # Text tags — minimal: black, accent blue, red signals, dim gray
        self.output.tag_configure("normal", foreground=FG,     font=(FONT,12))
        self.output.tag_configure("bold",   foreground=FG,     font=(FONT,12,"bold"))
        self.output.tag_configure("header", foreground=FG,     font=(FONT,14,"bold"))
        self.output.tag_configure("title",  foreground=FG,     font=(FONT,16,"bold"))
        self.output.tag_configure("dim",    foreground=FG_DIM, font=(FONT,11))
        self.output.tag_configure("accent", foreground=ACCENT, font=(FONT,12,"bold"))
        self.output.tag_configure("signal", foreground=SIGNAL, font=(FONT,12,"bold"))
        self.output.tag_configure("signal_sm",foreground=SIGNAL,font=(FONT,11))
        self.output.tag_configure("pass",   foreground="#007700",font=(FONT,12))
        self.output.tag_configure("fail",   foreground=SIGNAL,  font=(FONT,12))
        self.output.tag_configure("near",   foreground="#996600",font=(FONT,12))
        self.output.tag_configure("ai",     foreground="#333333",font=(FONT,12))
        self.output.tag_configure("ai_hdr", foreground=FG,      font=(FONT,12,"bold"))
        self.output.tag_configure("rule",   foreground=BORDER,  font=(FONT,11))
        self.output.tag_configure("score_high",foreground="#007700",font=(FONT,15,"bold"))
        self.output.tag_configure("score_med", foreground="#996600",font=(FONT,15,"bold"))
        self.output.tag_configure("score_low", foreground=SIGNAL,   font=(FONT,15,"bold"))

        # ── FOOTER ──
        tk.Label(self.root,
            text="AI-GENERATED RESEARCH ONLY  ·  NOT FINANCIAL ADVICE  ·  ALWAYS DO YOUR OWN DUE DILIGENCE",
            font=(FONT,9), fg=FG_DIM, bg=BG2).pack(pady=4)

        self._welcome()

    def _btn(self, parent, text, fg, bg, cmd):
        return tk.Button(parent, text=text, command=cmd,
            font=(FONT,11,"bold"), fg=fg, bg=bg,
            relief="solid", bd=1, padx=12, pady=4,
            cursor="hand2", activebackground=BG3)

    def _portfolio_status(self):
        n = len(self.portfolio.tickers())
        if n == 0:
            return "No portfolio loaded — load Schwab CSV to filter owned tickers"
        return f"Portfolio loaded: {n} tickers owned  ·  Scan will show NEW discoveries only"

    def _welcome(self):
        self.log("", "dim")
        self.log("  SQUEEZE FINDER v3.0 — 8-AGENT CREW EDITION", "title")
        self.log("  " + "─"*66, "rule")
        self.log("  Built around your Catalyst-Driven Portfolio Strategy.", "dim")
        self.log("  Every analysis runs through your Master Thesis and 3-of-5 Framework.", "dim")
        self.log("  8 specialized agents debate each ticker before delivering a verdict.", "dim")
        self.log("", "dim")
        self.log("  HOW TO USE YOUR WEEKLY SESSION:", "bold")
        self.log("  1.  Load your Schwab CSV  →  filters out tickers you already own", "dim")
        self.log("  2.  Run FULL SCAN         →  finds NEW setups only", "dim")
        self.log("  3.  Review discoveries    →  each shows ticker + one sentence why", "dim")
        self.log("  4.  Click any ticker      →  full 8-agent deep dive on demand", "dim")
        self.log("  5.  End of session        →  Improvement Report saved automatically", "dim")
        self.log("", "dim")
        self.log("  ACTIVE ALPHA-5:", "bold")
        a5 = [("NBIS","Nvidia $2B — March 11"),("VERA","PDUFA July 7"),
              ("VKTX","Phase 3 Q3"),("CAPR","PDUFA Aug 22"),("RKLB","Neutron Summer")]
        for t,c in a5:
            self.log(f"    {t:<6}  {c}", "dim")
        self.log("", "dim")
        self.log("  " + "─"*66, "rule")
        self.log(f"  {datetime.now().strftime('%A  %B %d, %Y   %H:%M')}  ·  {len(WATCHLIST)} tickers in watchlist", "dim")
        self.log("", "dim")

    # ── Output Helpers ───────────────────────────────────────
    def log(self, text, tag="normal"):
        self.output.insert(tk.END, text + "\n", tag)
        self.output.see(tk.END)
        self.session_log += text + "\n"
        self.root.update()

    def clear_output(self):
        self.output.delete(1.0, tk.END)
        self.session_log = ""
        self._welcome()

    def set_status(self, text):
        self.status_var.set(text)
        self.root.update()

    def _score_tag(self, score):
        if score >= 70: return "score_high"
        if score >= 50: return "score_med"
        return "score_low"

    def _score_bar(self, score):
        f = int(score/5)
        return "[" + "█"*f + "·"*(20-f) + f"]  {score}/100"

    # ── CSV Loader ───────────────────────────────────────────
    def _load_csv(self):
        path = filedialog.askopenfilename(
            title="Select Schwab Portfolio CSV",
            filetypes=[("CSV files","*.csv"),("All files","*.*")]
        )
        if not path:
            return
        imported, err = self.portfolio.load_from_schwab_csv(path)
        if err:
            messagebox.showerror("CSV Error", f"Could not parse CSV:\n{err}")
            return
        self.portfolio_lbl.configure(text=self._portfolio_status())
        self.log("", "dim")
        self.log(f"  PORTFOLIO LOADED — {len(imported)} tickers imported from Schwab CSV", "accent")
        self.log(f"  Owned: {', '.join(imported[:15])}{'...' if len(imported)>15 else ''}", "dim")
        self.log("  Full scan will now show ONLY new tickers not in your portfolio.", "dim")
        self.log("", "dim")

    # ── Render card ──────────────────────────────────────────
    def _render_card(self, data, reddit, news, score, cm, reasons, penalties, conviction):
        d   = data
        sep = "─" * 66
        conv, alloc, _ = conviction

        self.log("", "dim")
        owned_tag = "  [IN PORTFOLIO]" if self.portfolio.owns(d["ticker"]) else ""
        self.log(f"  {d['company']}  ({d['ticker']}){owned_tag}", "header")
        self.log(f"  {d['sector']}  ›  {d['industry']}", "dim")
        self.log("", "dim")

        pc  = "pass" if d["day_change_pct"] >= 0 else "signal"
        self.log(f"  Price:         ${d['current_price']:.3f}   {d['day_change_pct']:+.2f}% today", pc)
        self.log(f"  52wk range:    ${d['fifty_two_low']:.2f}  to  ${d['fifty_two_high']:.2f}   ({d['price_position']:.0f}% of range)", "dim")
        self.log(f"  MA50 / MA200:  ${d['ma50']:.2f}  /  ${d['ma200']:.2f}", "dim")
        self.log("", "dim")
        self.log(f"  Short interest:  {d['short_interest']:.1f}%", "bold" if d["short_interest"]>10 else "dim")
        self.log(f"  Days to cover:   {d['short_ratio']:.1f}", "bold" if d["short_ratio"]>4 else "dim")
        self.log(f"  Float:           {d['float_millions']:.1f}M shares", "bold" if d["float_millions"]<30 else "dim")
        self.log(f"  Volume:          {d['volume_spike']:.0f}% of average  ({d['volume']:,} shares)", "bold" if d["volume_spike"]>150 else "dim")
        self.log("", "dim")
        stag = "pass" if reddit["sentiment"]>55 else "signal" if reddit["sentiment"]<45 else "near"
        self.log(f"  Reddit:          {reddit['total']} mentions  ·  {reddit['sentiment']}% bullish", stag)
        if reddit["posts"]:
            self.log(f"  Top post:        [{reddit['posts'][0]['sub']}] {reddit['posts'][0]['title'][:60]}...", "dim")
        if d["analyst_target"]:
            utag = "pass" if d["analyst_upside"]>30 else "dim"
            self.log(f"  Analyst target:  ${d['analyst_target']:.2f}  (+{d['analyst_upside']:.0f}%)  {d['num_analysts']} analysts  [{d['recommendation'].upper()}]", utag)
        self.log("", "dim")
        self.log(f"  {sep}", "rule")
        ctag = "pass" if cm>=3 else "near" if cm==2 else "signal"
        self.log(f"  Criteria met:  {cm}/5  {'— QUALIFIES' if cm>=3 else '— DOES NOT MEET 3-OF-5'}", ctag)
        self.log(f"  Setup score:   {self._score_bar(score)}", self._score_tag(score))
        self.log("", "dim")
        self.log("  Scorecard:", "bold")
        for r in reasons:
            tag = "pass" if "PASS" in r else "fail" if "FAIL" in r else "near"
            self.log(f"    {r}", tag)
        if penalties:
            for p in penalties:
                self.log(f"    {p}", "signal")
        self.log("", "dim")
        conv_map = {"high":"pass","medium":"near","low":"signal_sm","spec":"signal"}
        self.log(f"  Bet sizing:    {conv}  ·  {alloc}", conv_map.get(conviction[2],"dim"))
        self.log(f"  {sep}", "rule")
        if news:
            self.log("", "dim")
            self.log("  Recent news:", "bold")
            for n in news[:4]:
                self.log(f"    ›  {n['title'][:78]}", "dim")

    def _render_agent(self, label, content):
        self.log("", "dim")
        self.log(f"  ── {label} " + "─"*(64-len(label)), "rule")
        for line in content.split("\n"):
            if not line.strip(): continue
            upper = line.upper()
            if any(k in upper for k in ["BULL","CATALYST","VERDICT","FINAL","JUDGE","PASS","ADD"]):
                self.log(f"  {line}", "ai_hdr")
            elif any(k in upper for k in ["BEAR","FAIL","AVOID","KILL","STOP","RISK","PENALTY","NEGATIVE"]):
                self.log(f"  {line}", "signal_sm")
            elif any(k in upper for k in ["WATCH","NEAR","PARTIAL","UNCONFIRMED"]):
                self.log(f"  {line}", "near")
            elif "⚠" in line:
                self.log(f"  {line}", "dim")
            else:
                self.log(f"  {line}", "ai")
        self.log("", "dim")

    # ── Single Ticker ────────────────────────────────────────
    def _run_single_thread(self):
        ticker = self.ticker_entry.get().strip().upper()
        if not ticker or self.scanning: return
        threading.Thread(target=self._analyze_single, args=(ticker,), daemon=True).start()

    def _analyze_single(self, ticker, in_scan=False):
        if not in_scan: self.scanning = True
        self.set_status(f"Fetching data  ·  {ticker}...")

        if not in_scan:
            self.log("", "dim")
            self.log("  " + "═"*66, "rule")
            self.log(f"  ANALYZING: {ticker}", "title")
            self.log("  " + "═"*66, "rule")

        data = get_stock_data(ticker)
        if not data:
            self.log(f"  Could not fetch data for {ticker} — check ticker symbol", "signal")
            if not in_scan: self.scanning = False
            return None

        self.set_status(f"Scanning Reddit + news  ·  {ticker}...")
        reddit = get_reddit(ticker)
        news   = get_news(ticker)
        score, cm, reasons, penalties = score_setup(data, reddit, news)
        conviction = get_conviction(score, cm)

        self._render_card(data, reddit, news, score, cm, reasons, penalties, conviction)

        # Run all 8 agents
        owned = self.portfolio.tickers()

        self.set_status(f"Agent 1 Scout  ·  {ticker}...")
        scout = agent_scout(data, reddit, news, score, cm, owned)
        self._render_agent("AGENT 1 — SCOUT", scout)

        self.set_status(f"Agent 2 Quant  ·  {ticker}...")
        quant = agent_quant(data, reddit, news, score, cm, reasons, penalties)
        self._render_agent("AGENT 2 — QUANT ANALYST", quant)

        self.set_status(f"Agent 3 Bull  ·  {ticker}...")
        bull = agent_bull(data, reddit, news, score, cm)
        self._render_agent("AGENT 3 — BULL ADVOCATE", bull)

        self.set_status(f"Agent 4 Bear  ·  {ticker}...")
        bear = agent_bear(data, reddit, news, score, cm)
        self._render_agent("AGENT 4 — BEAR ADVOCATE", bear)

        self.set_status(f"Agent 5 Catalyst  ·  {ticker}...")
        catalyst = agent_catalyst(data, news)
        self._render_agent("AGENT 5 — CATALYST TRACKER", catalyst)

        self.set_status(f"Agent 6 Risk  ·  {ticker}...")
        risk = agent_risk(data, reddit, news, score, cm, conviction)
        self._render_agent("AGENT 6 — RISK MANAGER", risk)

        self.set_status(f"Agent 7 Judge  ·  {ticker}...")
        judge = agent_judge(ticker, scout, quant, bull, bear, catalyst, risk, score, cm)
        self._render_agent("AGENT 7 — JUDGE  (FINAL VERDICT)", judge)

        # Extract verdict line for logging
        verdict_line = ""
        for line in judge.split("\n"):
            if "FINAL CALL" in line.upper() or "JUDGE VERDICT" in line.upper():
                verdict_line = line.strip()
                break

        # Log to history
        conv_str = conviction[0]
        self.logger.log_pick(data, score, cm, conv_str, verdict_line)

        # Add to session picks
        self.session_picks.append({
            "ticker": ticker, "score": score, "cm": cm,
            "verdict": verdict_line, "conviction": conv_str
        })

        if not in_scan:
            self.set_status(f"Complete  ·  {ticker}  ·  Score:{score}/100  ·  Criteria:{cm}/5")
            self.scanning = False

        return {"ticker":ticker,"score":score,"cm":cm,"data":data,
                "reddit":reddit,"news":news,"reasons":reasons,
                "penalties":penalties,"conviction":conviction,
                "verdict":verdict_line}

    # ── Alpha-5 Monitor ──────────────────────────────────────
    def _run_alpha5_thread(self):
        if self.scanning: return
        threading.Thread(target=self._alpha5_scan, daemon=True).start()

    def _alpha5_scan(self):
        self.scanning = True
        self.clear_output()
        self.log("", "dim")
        self.log("  ALPHA-5 POSITION MONITOR", "title")
        self.log("  " + "─"*66, "rule")
        self.log(f"  Checking 5 active positions  ·  {datetime.now().strftime('%Y-%m-%d  %H:%M')}", "dim")
        self.log("", "dim")
        for i, ticker in enumerate(["NBIS","VERA","VKTX","CAPR","RKLB"], 1):
            self.log(f"  POSITION {i}/5 — {ticker}", "header")
            self._analyze_single(ticker, in_scan=True)
        self._run_improvement_scout()
        self.set_status("Alpha-5 monitor complete")
        self.scanning = False

    # ── Full Scan ────────────────────────────────────────────
    def _run_full_scan_thread(self):
        if self.scanning: return
        threading.Thread(target=self._full_scan, daemon=True).start()

    def _full_scan(self):
        self.scanning = True
        self.session_picks = []
        self.session_gaps  = []
        self.clear_output()

        owned   = self.portfolio.tickers()
        to_scan = [t for t in WATCHLIST if t not in owned]

        self.log("", "dim")
        self.log("  FULL THESIS SCAN — NEW DISCOVERIES ONLY", "title")
        self.log("  " + "─"*66, "rule")
        self.log(f"  {datetime.now().strftime('%Y-%m-%d  %H:%M')}  ·  Scanning {len(to_scan)} tickers", "dim")
        if owned:
            self.log(f"  Filtered out {len(owned)} owned tickers from portfolio", "dim")
        else:
            self.log("  No portfolio loaded — scanning full watchlist", "dim")
        self.log("", "dim")

        # Quick pass — Scout only, build ranked list
        self.log("  DISCOVERY SCAN — ranking all tickers...", "bold")
        self.log("  " + "─"*66, "rule")
        quick_results = []

        for i, ticker in enumerate(to_scan):
            self.set_status(f"Scanning  {ticker}  ·  {i+1}/{len(to_scan)}")
            data = get_stock_data(ticker)
            if not data: continue
            reddit = get_reddit(ticker)
            news   = get_news(ticker)
            score, cm, reasons, penalties = score_setup(data, reddit, news)
            conviction = get_conviction(score, cm)

            # Quick scout sentence
            scout = agent_scout(data, reddit, news, score, cm, owned)
            scout_line = scout.split("\n")[1].strip() if len(scout.split("\n"))>1 else scout[:100]

            quick_results.append({
                "ticker": ticker, "score": score, "cm": cm,
                "data": data, "reddit": reddit, "news": news,
                "reasons": reasons, "penalties": penalties,
                "conviction": conviction, "scout": scout_line
            })

            # Print one-liner
            qual = "QUALIFIES" if cm >= 3 else "watch"
            ctag = "pass" if cm >= 3 else "near" if cm == 2 else "dim"
            self.log(f"  {ticker:<6}  {cm}/5 criteria  ·  {scout_line[:70]}", ctag)

        # Sort: criteria first, then score
        quick_results.sort(key=lambda x: (x["cm"], x["score"]), reverse=True)
        top5 = [r for r in quick_results if r["cm"] >= 3][:5]
        if len(top5) < 5:
            top5 += [r for r in quick_results if r["cm"] < 3][:5-len(top5)]

        # Full 8-agent analysis on top 5
        self.log("", "dim")
        self.log("  " + "═"*66, "rule")
        self.log(f"  TOP {len(top5)} NEW DISCOVERIES — FULL 8-AGENT ANALYSIS", "title")
        self.log("  " + "═"*66, "rule")

        for i, pick in enumerate(top5, 1):
            self.log("", "dim")
            self.log(f"  DISCOVERY #{i} OF {len(top5)}", "accent")
            self._analyze_single(pick["ticker"], in_scan=True)
            self.log("", "dim")
            self.log("  " + "─"*66, "rule")

        # Improvement Scout
        self._run_improvement_scout()

        end = datetime.now().strftime("%H:%M:%S")
        self.log("", "dim")
        self.log(f"  Scan complete  ·  {end}  ·  {len(quick_results)} tickers scanned  ·  {len(top5)} analyzed in depth", "dim")
        self.set_status(f"Scan complete  ·  {end}  ·  {len(quick_results)} scanned  ·  {len(top5)} deep dives")
        self.scanning = False

    # ── Improvement Scout ────────────────────────────────────
    def _run_improvement_scout(self):
        self.set_status("Agent 8 Improvement Scout running...")
        self.log("", "dim")
        self.log("  " + "═"*66, "rule")
        self.log("  AGENT 8 — IMPROVEMENT SCOUT", "title")
        self.log("  " + "─"*66, "rule")
        self.log("  Analyzing this session for gaps and improvements...", "dim")
        self.log("", "dim")

        report = agent_improvement(
            self.session_picks,
            self.session_gaps,
            len(WATCHLIST),
            len(self.portfolio.tickers())
        )

        for line in report.split("\n"):
            if not line.strip(): continue
            if "━" in line or "REPORT" in line or "IMPROVEMENT" in line:
                self.log(f"  {line}", "header")
            elif "PROMPT" in line.upper() or "DEVELOPER" in line.upper():
                self.log(f"  {line}", "accent")
            elif any(k in line.upper() for k in ["GAP","MISSING","FAIL","WEAK"]):
                self.log(f"  {line}", "signal_sm")
            elif any(k in line.upper() for k in ["SUGGEST","IMPROVE","ADD","FEATURE"]):
                self.log(f"  {line}", "ai_hdr")
            else:
                self.log(f"  {line}", "ai")

        # Save improvement report
        self.logger.log_session(self.session_log)
        self.log("", "dim")
        self.log(f"  Session saved to: {HISTORY_LOG.name}", "dim")
        self.log(f"  Pick history saved to: {HISTORY_CSV.name}", "dim")
        self.log("  Bring the PROMPTS FOR YOUR DEVELOPER above to Claude next week.", "bold")
        self.log("", "dim")

# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app  = QuantDashboard(root)
    root.mainloop()