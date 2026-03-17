# Stock Newsletter

A personal stock screening and analysis tool that pulls live market data, scores stocks across multiple sectors, and uses AI to generate plain-English analysis formatted like sports betting odds — because risk should be fun to read about.

## What it does

Every morning it pulls live price data for a curated watchlist across 5 sectors, scores each stock on momentum, volume, and distance from its 52-week low, then uses an AI model to generate a conviction odds line, 60-day price target, confidence rating, a five sentence company story, and a bear case for the top 3 picks of the day. Every result gets written to a local SQLite database so the system builds a track record over time.

## Sectors watched

- Technology
- Medical / Biotech
- Minerals / Energy
- Consumables
- Niche / Wildcard

## Built with

- Python 3.11+
- yfinance — live price and volume data
- OpenRouter API — AI analysis via hunter-alpha model
- SQLite — persistent database for scoring history and pick tracking
- JSON — watchlist management separate from code

## How to run

1. Clone the repo
2. Install dependencies: `pip install yfinance requests`
3. Set your OpenRouter API key as an environment variable: `OPENROUTER_API_KEY`
4. Run the newsletter: `python newsletter.py`
5. Verify database: `python Check_db.py`

## Output format

Each top pick includes:
- Signal score (-100 to +100)
- Moneyline odds for a 20% gain within 60 days
- Price target
- Confidence rating (1-5)
- Five sentence company story — what they do, economy fit, interesting fact, current catalyst, forward outlook
- Bear case

## Project status

Active development. Currently on Story 4 of 8 — database memory is live, system writes its own history daily. Next: HTML email newsletter delivered to inbox every morning.

## Roadmap

- [x] Story 1 — Context management and prompt guardrails
- [x] Story 2 — JSON watchlist config
- [x] Story 3 — AI story generation with structured output
- [x] Story 4 — SQLite persistent memory
- [ ] Story 5 — HTML newsletter generation
- [ ] Story 6 — Email delivery
- [ ] Story 7 — Windows Task Scheduler automation
- [ ] Story 8 — Performance tracking and hit rate analysis

## Note

This is a learning project built story by story. Nothing here is financial advice.
