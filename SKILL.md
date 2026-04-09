---
name: google-trends
description: Monitor Google Trends for keyword research and SEO insights. Use when user asks about search trends, keyword popularity, trending topics, "what's hot", rising searches, or wants to track keyword performance over time. Supports daily trending topics, keyword suggestions, and multi-region analysis.
---

# Google Trends Monitor

Monitor Google search trends for SEO and keyword research.

## Quick Start

```bash
# Get today's trending searches (US)
python3 scripts/trends_monitor.py trending

# Get keyword suggestions
python3 scripts/trends_monitor.py suggest "AI image generator"

# Full analysis (suggestions + trending)
python3 scripts/trends_monitor.py full "svg converter" --geo US
```

## Commands

| Command | Description |
|---------|-------------|
| `trending` | Today's top searches from Google Trends RSS |
| `suggest <keyword>` | Related keywords and topics |
| `full <keyword>` | Combined analysis |

## Options

- `--geo <code>` — Region: US, GB, JP, CN, DE, FR, etc. (default: US)
- `--format <type>` — Output: `report` (human-readable) or `json`

## Examples

```bash
# Japanese trending topics
python3 scripts/trends_monitor.py trending --geo JP

# SVG-related keywords as JSON
python3 scripts/trends_monitor.py suggest "svg" --format json

# AI tools analysis for global audience
python3 scripts/trends_monitor.py full "AI tools" --geo US --format report
```

## Data Sources

1. **Trending RSS** — `trends.google.com/trending/rss` (stable, no rate limits)
2. **Suggestions API** — `trends.google.com/trends/api/autocomplete` (stable)

## Output Format

### Trending Report
```
## 🔥 Google 今日热搜 (US)
**1. keyword** — 100K+ 搜索量
   - News headline (Source)
```

### Suggestions Report
```
## 💡 关键词分析: keyword
### 相关联想词
- **Related Term** (Topic/Software/etc)
```

## Limitations

- No historical time-series data (Google blocks direct API access)
- For detailed trends data, use SerpAPI with `--serpapi-key`
- Rate limits may apply on suggestions API under heavy use

## Integration Ideas

- Cron job for daily trending reports
- Combine with SEO tools for keyword opportunities
- Monitor competitor brand mentions in trending
