# google-trends-skill

Google Trends monitoring skill for [OpenClaw](https://github.com/openclaw/openclaw).

Track trending searches, keyword suggestions, and SEO insights using Google Trends data.

## Features

- 🔥 **Daily Trending** — Top search topics from Google Trends RSS
- 💡 **Keyword Suggestions** — Related keywords and topics
- 🌍 **Multi-region** — Support for US, CN, JP, GB, and more
- 📊 **Report & JSON output** — Human-readable or machine-parseable

## Install

```bash
# Via ClawHub (if published)
clawhub install google-trends

# Or manually: copy this repo into your skills directory
git clone https://github.com/nietao2025/google-trends-skill.git ~/.openclaw/workspace/skills/google-trends
```

## Usage

```bash
# Today's trending topics
python3 scripts/trends_monitor.py trending --geo US

# Keyword suggestions
python3 scripts/trends_monitor.py suggest "AI image generator"

# Full analysis
python3 scripts/trends_monitor.py full "svg converter" --geo US --format report
```

## Requirements

- Python 3.8+
- No external dependencies (uses only stdlib)

## License

MIT
