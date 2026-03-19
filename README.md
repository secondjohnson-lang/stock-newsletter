# Letters to the Betters

A personal stock screening and analysis tool that pulls live market data, scores stocks across multiple sectors, and uses AI to generate plain-English analysis — delivered to your inbox every morning like a real newsletter.

## What it does

Every morning it pulls live price data for a curated watchlist across 5 sectors, scores each stock on momentum, volume, and distance from its 52-week low, then uses an AI model to generate a conviction signal score, 30-day price target, confidence rating, a company story, and a bear case for the top 3 picks of the day. Every result gets written to a local SQLite database so the system builds a track record over time. The newsletter is formatted as a dark-themed HTML email and delivered automatically to your inbox.

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
- smtplib — email delivery via Mailtrap sandbox

## How to run

1. Clone the repo
2. Install dependencies: `pip install yfinance requests python-dotenv`
3. Create a `.env` file with your API keys and mail credentials (see `.env.example` below)
4. Run the scorer and AI analysis: `python newsletter.py`
5. Generate and send the newsletter: `python generate_newsletter.py`
6. Verify database: `python check_db.py`

## Environment variables

Create a `.env` file in the project root. Never commit this file — it is listed in `.gitignore`.
```
OPENROUTER_API_KEY=your_key_here
MAILTRAP_HOST=sandbox.smtp.mailtrap.io
MAILTRAP_PORT=587
MAILTRAP_USER=your_mailtrap_username
MAILTRAP_PASS=your_mailtrap_password
MAIL_FROM=newsletter@letterstothebetters.com
MAIL_TO=your_email@gmail.com
```

## Output format

Each top pick includes:
- Signal score (-100 to +100)
- 30-day price target with projected return on $100
- Confidence rating (1-5)
- Company story — what they do, economy fit, current catalyst, forward outlook
- Bear case and risk factors
- Heat flags for notable daily moves

## Project status

Active development. Stories 1-6 complete. Newsletter scores stocks, generates AI analysis, builds a daily HTML newsletter, and delivers it to inbox automatically.

## Roadmap

- [x] Story 1 — Context management and prompt guardrails
- [x] Story 2 — JSON watchlist config
- [x] Story 3 — AI story generation with structured output
- [x] Story 4 — SQLite persistent memory
- [x] Story 5 — HTML newsletter generation
- [x] Story 6 — Email delivery via Mailtrap sandbox
- [ ] Story 7 — Windows Task Scheduler automation
- [ ] Story 8 — Performance tracking and hit rate analysis

## Note

This is a learning project built story by story. Nothing here is financial advice.