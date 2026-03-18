import sqlite3
from datetime import date
import os

def get_todays_picks():
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticker, price, signal, odds, target, confidence, story, bear
        FROM top_picks
        WHERE date = ?
        ORDER BY signal DESC
    """, (str(date.today()),))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_todays_scores():
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticker, price, signal, day_change
        FROM daily_scores
        WHERE date = ?
        ORDER BY signal DESC
    """, (str(date.today()),))
    rows = cursor.fetchall()
    conn.close()
    return rows

def signal_color(signal):
    if signal >= 60:
        return "#16a34a"
    elif signal >= 1:
        return "#2563eb"
    elif signal == 0:
        return "#6b7280"
    elif signal >= -59:
        return "#ea580c"
    else:
        return "#dc2626"

def confidence_bars(confidence):
    filled = "▰" * confidence
    empty = "▱" * (5 - confidence)
    return filled + empty

def generate_html(picks, scores):
    today = date.today().strftime("%A, %B %d, %Y")
    
    taglines = [
        "3 picks. Real data. Plain english. No noise.",
        "Where the data meets the bet.",
        "Smarter picks. Better odds. Every morning.",
        "Read it. Learn it. Bet smarter.",
        "The morning edge for curious investors."
    ]
    import random
    tagline = random.choice(taglines)

    nav_links = ""
    for i, pick in enumerate(picks, 1):
        nav_links += f'<a href="#pick-{i}" style="display:inline-block;margin:3px;padding:5px 14px;background:#f3f4f6;border-radius:6px;text-decoration:none;color:#111;font-size:13px;font-weight:500;border:1px solid #e5e7eb;">{i}. {pick[0]}</a>'

    picks_html = ""
    for i, pick in enumerate(picks, 1):
        ticker, price, signal, odds, target, confidence, story, bear = pick
        color = signal_color(signal)
        sign = "+" if signal >= 0 else ""
        bars = confidence_bars(confidence)
        arrow = "▲" if signal >= 0 else "▼"

        picks_html += f"""
        <div id="pick-{i}" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;margin-bottom:20px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:16px;margin-bottom:16px;border-bottom:1px solid #f3f4f6;">
                <div>
                    <div style="font-size:11px;color:#9ca3af;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Pick #{i}</div>
                    <div style="font-size:26px;font-weight:600;color:#111;margin-bottom:4px;">{ticker}</div>
                    <div style="font-size:14px;color:#6b7280;">${price} &nbsp;{arrow} today</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:28px;font-weight:600;color:{color};">{sign}{signal}</div>
                    <div style="font-size:11px;color:#9ca3af;letter-spacing:2px;text-transform:uppercase;">Signal</div>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px;">
                <div style="background:#f9fafb;border-radius:8px;padding:12px;">
                    <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Odds</div>
                    <div style="font-size:18px;font-weight:600;color:#111;">{odds}</div>
                    <div style="font-size:11px;color:#9ca3af;margin-top:2px;">for +20% in 60d</div>
                </div>
                <div style="background:#f9fafb;border-radius:8px;padding:12px;">
                    <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">60-Day Target</div>
                    <div style="font-size:18px;font-weight:600;color:#111;">{target}</div>
                    <div style="font-size:11px;color:#9ca3af;margin-top:2px;">price target</div>
                </div>
                <div style="background:#f9fafb;border-radius:8px;padding:12px;">
                    <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Confidence</div>
                    <div style="font-size:18px;font-weight:600;color:#111;">{confidence}/5</div>
                    <div style="font-size:14px;color:{color};margin-top:2px;">{bars}</div>
                </div>
            </div>

            <div style="font-size:14px;line-height:1.9;color:#374151;margin-bottom:16px;">{story}</div>

            <div style="background:#fef2f2;border-radius:8px;padding:12px 16px;font-size:13px;color:#991b1b;">
                <span style="font-weight:600;">Bear case: </span>{bear}
            </div>
        </div>"""

    watchlist_rows = ""
    for row in scores:
        ticker, price, signal, day_change = row
        color = signal_color(signal)
        sign = "+" if signal >= 0 else ""
        arrow = "▲" if day_change >= 0 else "▼"
        day_color = "#16a34a" if day_change >= 0 else "#dc2626"
        watchlist_rows += f"""
            <tr>
                <td style="padding:10px 12px;font-weight:500;color:#111;">{ticker}</td>
                <td style="padding:10px 12px;color:#374151;">${price}</td>
                <td style="padding:10px 12px;color:{day_color};">{arrow} {day_change}%</td>
                <td style="padding:10px 12px;font-weight:600;color:{color};">{sign}{signal}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Letters to the Betters — {today}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

<div style="max-width:640px;margin:0 auto;padding:24px 16px;">

    <div style="background:#111;border-radius:12px;padding:32px;margin-bottom:20px;">
        <div style="font-size:11px;color:#9ca3af;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px;">{today}</div>
        <div style="font-size:28px;font-weight:600;color:#ffffff;margin-bottom:6px;">Letters to the Betters</div>
        <div style="font-size:14px;color:#9ca3af;">{tagline}</div>
    </div>

    <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;margin-bottom:20px;">
        <span style="font-size:12px;color:#9ca3af;margin-right:8px;">JUMP TO:</span>
        {nav_links}
    </div>

    {picks_html}

    <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:20px;">
        <div style="font-size:13px;font-weight:600;color:#111;margin-bottom:14px;letter-spacing:1px;text-transform:uppercase;">Full Watchlist — {today}</div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
                <tr style="border-bottom:1px solid #f3f4f6;">
                    <th style="padding:8px 12px;text-align:left;color:#9ca3af;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Ticker</th>
                    <th style="padding:8px 12px;text-align:left;color:#9ca3af;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Price</th>
                    <th style="padding:8px 12px;text-align:left;color:#9ca3af;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Today</th>
                    <th style="padding:8px 12px;text-align:left;color:#9ca3af;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Signal</th>
                </tr>
            </thead>
            <tbody>
                {watchlist_rows}
            </tbody>
        </table>
    </div>

    <div style="text-align:center;font-size:12px;color:#9ca3af;line-height:2;padding:16px 0;">
        Letters to the Betters is for informational purposes only.<br>
        Nothing here is financial advice. Always do your own research.<br>
        Built with Python, yfinance, and OpenRouter AI.
    </div>

</div>
</body>
</html>"""

    return html

picks = get_todays_picks()
scores = get_todays_scores()

if not picks:
    print("No picks found for today. Run newsletter.py first.")
else:
    html = generate_html(picks, scores)
    filename = f"newsletter_{date.today()}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Newsletter generated: {filename}")
    os.startfile(filename)