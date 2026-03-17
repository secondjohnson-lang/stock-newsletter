import sqlite3
from datetime import date

conn = sqlite3.connect("stocks.db")
cursor = conn.cursor()

print("\n====== DATABASE VERIFICATION ======\n")

print(f"--- Daily Scores ({str(date.today())}) ---")
cursor.execute("""
    SELECT ticker, price, signal, day_change
    FROM daily_scores
    WHERE date = ?
    ORDER BY signal DESC
""", (str(date.today()),))
rows = cursor.fetchall()
for row in rows:
    sign = "+" if row[2] >= 0 else ""
    print(f"  {row[0]:<6} ${row[1]:<10} Signal: {sign}{row[2]}  |  Day: {row[3]}%")

print(f"\n  Total stocks scored today: {len(rows)}")

print(f"\n--- Top Picks ({str(date.today())}) ---")
cursor.execute("""
    SELECT ticker, price, signal, odds, target, confidence, outcome
    FROM top_picks
    WHERE date = ?
    ORDER BY signal DESC
""", (str(date.today()),))
rows = cursor.fetchall()
for row in rows:
    sign = "+" if row[2] >= 0 else ""
    print(f"  {row[0]:<6} ${row[1]:<10} Signal: {sign}{row[2]}")
    print(f"         Odds: {row[3]}  Target: {row[4]}  Confidence: {row[5]}/5  Outcome: {row[6]}")

print(f"\n  Total picks saved today: {len(rows)}")

print("\n--- All Time Record ---")
cursor.execute("SELECT COUNT(*) FROM daily_scores")
total_scores = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(DISTINCT date) FROM daily_scores")
total_days = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM top_picks WHERE outcome != 'pending'")
resolved = cursor.fetchone()[0]
print(f"  Total stocks scored all time: {total_scores}")
print(f"  Total days on record: {total_days}")
print(f"  Picks resolved (not pending): {resolved}")

print("\n====================================\n")

conn.close()
