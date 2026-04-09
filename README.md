# google-trends-skill

Google Trends monitoring skill for [OpenClaw](https://github.com/openclaw/openclaw).

Full Google Trends data: time series, rising queries, geo distribution, keyword suggestions, and daily trending — with zero external dependencies.

## Features

- 📊 **Time Series** — Interest over time with trend direction analysis
- 🚀 **Rising Queries** — Keywords with biggest growth (Breakout detection)
- 🔝 **Top Queries** — Most popular related searches
- 🌍 **Geo Distribution** — Interest by country/region
- 💡 **Suggestions** — Google autocomplete topics
- 🔥 **Daily Trending** — Today's top searches via RSS
- 🔄 **Multi-keyword Compare** — Compare up to 5 keywords side-by-side

## Install

```bash
# Clone into your OpenClaw skills directory
git clone https://github.com/nietao2025/google-trends-skill.git ~/.openclaw/workspace/skills/google-trends
```

## Usage

```bash
# Full keyword analysis
python3 scripts/trends_monitor.py monitor "AI"

# Compare keywords
python3 scripts/trends_monitor.py monitor "ChatGPT,Claude,Gemini" --geo US

# JSON output
python3 scripts/trends_monitor.py monitor "AI" --format json

# Daily trending
python3 scripts/trends_monitor.py trending --geo US
```

## Requirements

- Python 3.8+
- `curl`
- No pip dependencies

## License

MIT
