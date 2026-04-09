---
name: google-trends
description: Monitor Google Trends for keyword research and SEO insights. Use when user asks about search trends, keyword popularity, trending topics, rising searches, breakout keywords, or wants to track keyword performance over time. Supports time-series data, rising/top related queries, geo distribution, keyword suggestions, and daily trending RSS.
---

# Google Trends Monitor

Full Google Trends data via cookie-authenticated API. Zero external dependencies.

## Quick Start

```bash
# Full keyword trend analysis (time series + rising queries + geo + suggestions)
python3 scripts/trends_monitor.py monitor "AI"

# Compare multiple keywords (comma-separated, max 5)
python3 scripts/trends_monitor.py monitor "ChatGPT,Claude,Gemini"

# Specific region and timeframe
python3 scripts/trends_monitor.py monitor "AI tools" --geo US --timeframe "today 12-m"

# Daily trending searches
python3 scripts/trends_monitor.py trending --geo US

# Keyword suggestions
python3 scripts/trends_monitor.py suggest "svg converter"
```

## Commands

| Command | Description |
|---------|-------------|
| `monitor <keyword>` | Full analysis: time series, rising/top queries, geo, suggestions |
| `trending` | Daily trending searches via RSS |
| `suggest <keyword>` | Related keyword suggestions |

## Options

- `--geo <code>` — Region: US, CN, JP, GB, DE, etc. (default: global)
- `--timeframe <range>` — `now 1-H`, `now 7-d`, `today 1-m`, `today 3-m`, `today 12-m`, `today 5-y`
- `--format <type>` — `report` (human-readable) or `json` (machine-parseable)
- `--output <file>` — Save to file instead of stdout

## Output Includes

- **Trend direction**: ⬆️ rising / ➡️ stable / ⬇️ declining with % change
- **Time series**: Daily/weekly interest values (0-100 scale)
- **Rising queries**: Keywords with biggest growth (most valuable for SEO)
- **Top queries**: Most popular related searches
- **Geo distribution**: Interest by country/region
- **Suggestions**: Google's autocomplete topics

## How It Works

Uses `curl` with cookie authentication to access Google Trends internal API endpoints:
1. `/trends/api/explore` — Get widget tokens
2. `/widgetdata/multiline` — Time series data
3. `/widgetdata/relatedsearches` — Related queries
4. `/widgetdata/comparedgeo` — Geographic data
5. `/trends/api/autocomplete` — Suggestions
6. `/trending/rss` — Daily trending (RSS)

## Requirements

- Python 3.8+
- `curl` (pre-installed on most systems)
- No pip dependencies

## Rate Limiting

Google may return 429 errors under heavy use. The script handles this with:
- Cookie-based authentication (more stable than raw requests)
- Random delays between requests (1.5-2.5s)
- Automatic cookie refresh before each session
