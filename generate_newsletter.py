import sqlite3
from datetime import date, datetime
import os
import random
from send_email import send_newsletter

def get_todays_picks():
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.ticker, t.price, t.signal, t.odds, t.target,
               t.confidence, t.story, t.bear, d.day_change
        FROM top_picks t
        LEFT JOIN daily_scores d
            ON t.ticker = d.ticker AND t.date = d.date
        WHERE t.date = ?
        ORDER BY t.signal DESC
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
        return "#2563eb"
    elif signal >= 1:
        return "#0891b2"
    elif signal == 0:
        return "#64748b"
    elif signal >= -59:
        return "#ea580c"
    else:
        return "#dc2626"

def signal_tag(signal):
    if signal >= 80:
        return ("Full Send", "#2563eb", "#eff6ff")
    elif signal >= 60:
        return ("Buy the Dip", "#0891b2", "#ecfeff")
    elif signal >= 40:
        return ("On Watch", "#d97706", "#fffbeb")
    elif signal >= 20:
        return ("Sleeping Giant", "#64748b", "#f8fafc")
    elif signal >= 0:
        return ("Neutral", "#94a3b8", "#f8fafc")
    else:
        return ("Avoid", "#dc2626", "#fef2f2")

def heat_flag(day_change):
    if day_change is None:
        return ("", "")
    if day_change >= 5:
        return ("🔥 Hot Right Now", "#dc2626")
    elif day_change >= 3:
        return ("⚡ Heating Up", "#d97706")
    elif day_change <= -5:
        return ("🧊 Cooling Off", "#0891b2")
    else:
        return ("", "")

def projected_return(price, target):
    try:
        p = float(str(price).replace('$', ''))
        t = float(str(target).replace('$', ''))
        pct = ((t - p) / p) * 100
        dollar = (pct / 100) * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{round(pct, 1)}%", f"{sign}${round(dollar, 2)} per $100", "#16a34a" if pct >= 0 else "#dc2626"
    except:
        return "N/A", "N/A", "#64748b"

def confidence_bars(confidence):
    try:
        c = int(confidence)
        filled = "█" * c
        empty = "░" * (5 - c)
        return filled + empty
    except:
        return "░░░░░"

def market_status():
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    time_decimal = hour + minute / 60
    if weekday >= 5:
        return ("MARKETS CLOSED", "#64748b", "#f1f5f9")
    elif 9.5 <= time_decimal < 16:
        return ("MARKETS OPEN", "#16a34a", "#f0fdf4")
    else:
        return ("MARKETS CLOSED", "#64748b", "#f1f5f9")

def generate_html(picks, scores):
    today = date.today().strftime("%A, %B %d, %Y")
    generated_time = datetime.now().strftime("%I:%M %p")
    market_label, market_color, market_bg = market_status()

    taglines = [
        "Institutional-grade signals. Plain english stories. No noise.",
        "Data first. Story second. Action always.",
        "Three positions. Full analysis. Every morning.",
        "Where quantitative signals meet real world context.",
        "Built for curious investors who want to understand the why."
    ]
    tagline = random.choice(taglines)

    nav_links = ""
    for i, pick in enumerate(picks, 1):
        nav_links += f'<a href="#pick-{i}" style="display:inline-block;margin:3px;padding:5px 14px;background:#f8fafc;border-radius:4px;text-decoration:none;color:#0f172a;font-size:12px;font-weight:600;border:1px solid #e2e8f0;font-family:monospace;letter-spacing:1px;">{pick[0]}</a>'

    picks_html = ""
    for i, pick in enumerate(picks, 1):
        ticker, price, signal, odds, target, confidence, story, bear, day_change = pick
        color = signal_color(signal)
        sign = "+" if signal >= 0 else ""
        bars = confidence_bars(confidence)
        tag, tag_color, tag_bg = signal_tag(signal)
        heat, heat_color = heat_flag(day_change)
        pct_return, dollar_return, return_color = projected_return(price, target)

        if day_change is not None:
            arrow = "▲" if day_change >= 0 else "▼"
            day_display = f"{arrow} {abs(day_change)}%"
            day_color = "#16a34a" if day_change >= 0 else "#dc2626"
        else:
            day_display = ""
            day_color = "#64748b"

        heat_html = f'<span style="font-size:12px;font-weight:600;color:{heat_color};margin-left:10px;">{heat}</span>' if heat else ''

        picks_html += f"""
        <div id="pick-{i}" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:20px;overflow:hidden;">

            <div style="background:#0f172a;padding:16px 24px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:10px;color:#64748b;letter-spacing:3px;text-transform:uppercase;margin-bottom:4px;font-family:monospace;">POSITION 0{i}</div>
                    <div style="font-size:28px;font-weight:700;color:#ffffff;font-family:monospace;letter-spacing:2px;">{ticker}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:32px;font-weight:700;color:{color};font-family:monospace;">{sign}{signal}</div>
                    <div style="display:inline-block;background:{tag_bg};color:{tag_color};font-size:11px;font-weight:600;padding:3px 10px;border-radius:4px;letter-spacing:1px;text-transform:uppercase;margin-top:4px;">{tag}</div>
                </div>
            </div>

            <div style="padding:16px 24px;background:#f8fafc;border-bottom:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <span style="font-size:22px;font-weight:600;color:#0f172a;font-family:monospace;">${price}</span>
                    <span style="font-size:14px;font-weight:600;color:{day_color};margin-left:10px;">{day_display}</span>
                    {heat_html}
                </div>
                <div style="font-size:11px;color:#94a3b8;font-family:monospace;">SIGNAL RATING</div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0;border-bottom:1px solid #e2e8f0;">
                <div style="padding:16px 20px;border-right:1px solid #e2e8f0;">
                    <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;font-family:monospace;">PRICE TARGET T+30</div>
                    <div style="font-size:20px;font-weight:700;color:#0f172a;font-family:monospace;">{target}</div>
                    <div style="font-size:12px;color:{return_color};margin-top:4px;font-weight:600;">{pct_return} projected</div>
                </div>
                <div style="padding:16px 20px;border-right:1px solid #e2e8f0;">
                    <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;font-family:monospace;">RETURN ON $100</div>
                    <div style="font-size:20px;font-weight:700;color:{return_color};font-family:monospace;">{dollar_return}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:4px;">if target is hit</div>
                </div>
                <div style="padding:16px 20px;">
                    <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;font-family:monospace;">CONFIDENCE</div>
                    <div style="font-size:20px;font-weight:700;color:#0f172a;font-family:monospace;">{confidence}/5</div>
                    <div style="font-size:13px;color:{color};margin-top:4px;letter-spacing:2px;">{bars}</div>
                </div>
            </div>

            <div style="padding:20px 24px;border-bottom:1px solid #e2e8f0;">
                <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;font-family:monospace;">ANALYSIS</div>
                <div style="font-size:14px;line-height:1.9;color:#334155;">{story}</div>
            </div>

            <div style="padding:16px 24px;background:#fef2f2;border-left:3px solid #dc2626;">
                <div style="font-size:10px;color:#dc2626;text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;font-family:monospace;">RISK FACTORS</div>
                <div style="font-size:13px;color:#7f1d1d;line-height:1.7;">{bear}</div>
            </div>

        </div>"""

    watchlist_rows = ""
    for row in scores:
        ticker, price, signal, day_change = row
        color = signal_color(signal)
        sign = "+" if signal >= 0 else ""
        arrow = "▲" if day_change >= 0 else "▼"
        day_color = "#16a34a" if day_change >= 0 else "#dc2626"
        heat, heat_color = heat_flag(day_change)
        heat_display = f' {heat}' if heat else ''
        tag, tag_color, tag_bg = signal_tag(signal)
        watchlist_rows += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:10px 12px;font-weight:600;color:#0f172a;font-family:monospace;">{ticker}</td>
                <td style="padding:10px 12px;color:#334155;font-family:monospace;">${price}</td>
                <td style="padding:10px 12px;color:{day_color};font-family:monospace;">{arrow} {day_change}%<span style="font-size:11px;margin-left:6px;">{heat_display}</span></td>
                <td style="padding:10px 12px;">
                    <span style="font-weight:700;color:{color};font-family:monospace;">{sign}{signal}</span>
                </td>
                <td style="padding:10px 12px;">
                    <span style="background:{tag_bg};color:{tag_color};font-size:10px;font-weight:600;padding:2px 8px;border-radius:3px;letter-spacing:1px;text-transform:uppercase;">{tag}</span>
                </td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Letters to the Betters — {today}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

<div style="max-width:680px;margin:0 auto;padding:24px 16px;">

    <div style="background:#0f172a;border-radius:8px;padding:32px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;">
            <div style="font-size:10px;color:#475569;letter-spacing:3px;text-transform:uppercase;font-family:monospace;">{today}</div>
            <div style="background:{market_bg};color:{market_color};font-size:10px;font-weight:700;padding:4px 10px;border-radius:3px;letter-spacing:2px;font-family:monospace;">{market_label}</div>
        </div>
        <div style="font-size:30px;font-weight:700;color:#ffffff;margin-bottom:6px;letter-spacing:-0.5px;">Letters to the Betters</div>
        <div style="font-size:13px;color:#64748b;">{tagline}</div>
        <div style="margin-top:16px;padding-top:16px;border-top:1px solid #1e293b;font-size:11px;color:#475569;font-family:monospace;">
            GENERATED {generated_time} &nbsp;·&nbsp; {len(scores)} POSITIONS SCANNED &nbsp;·&nbsp; TOP 3 SELECTED
        </div>
    </div>

    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:14px 20px;margin-bottom:20px;display:flex;align-items:center;">
        <span style="font-size:10px;color:#94a3b8;margin-right:12px;font-family:monospace;letter-spacing:2px;text-transform:uppercase;">Navigate:</span>
        {nav_links}
    </div>

    {picks_html}

    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:20px;">
        <div style="background:#0f172a;padding:12px 20px;">
            <div style="font-size:10px;color:#64748b;letter-spacing:3px;text-transform:uppercase;font-family:monospace;">FULL WATCHLIST — {today}</div>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
                <tr style="border-bottom:1px solid #e2e8f0;background:#f8fafc;">
                    <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:2px;font-family:monospace;">Ticker</th>
                    <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:2px;font-family:monospace;">Price</th>
                    <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:2px;font-family:monospace;">Today</th>
                    <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:2px;font-family:monospace;">Signal</th>
                    <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:2px;font-family:monospace;">Rating</th>
                </tr>
            </thead>
            <tbody>
                {watchlist_rows}
            </tbody>
        </table>
    </div>

    <div style="text-align:center;font-size:11px;color:#94a3b8;line-height:2;padding:16px 0;font-family:monospace;">
        LETTERS TO THE BETTERS &nbsp;·&nbsp; FOR INFORMATIONAL PURPOSES ONLY<br>
        NOT FINANCIAL ADVICE &nbsp;·&nbsp; ALWAYS DO YOUR OWN RESEARCH<br>
        POWERED BY PYTHON · YFINANCE · OPENROUTER AI
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
    send_newsletter(html)