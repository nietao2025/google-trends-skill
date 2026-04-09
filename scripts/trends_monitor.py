#!/usr/bin/env python3
"""
Google Trends 词根监控 v4
通过 cookie + curl 方式稳定获取 Google Trends 完整数据

功能:
- 关键词时间序列热度 (interest over time)
- 崛起相关查询 (rising queries) — 最有 SEO 价值
- 热门相关查询 (top queries)
- 地域热度分布 (interest by region)
- 关键词联想词 (suggestions)
- 每日热搜 (trending RSS)

用法:
  python3 trends_monitor.py monitor "AI"                    # 完整趋势分析
  python3 trends_monitor.py monitor "AI" --geo US           # 限定地域
  python3 trends_monitor.py monitor "AI,ChatGPT,Claude"     # 多词对比(逗号分隔,最多5个)
  python3 trends_monitor.py monitor "AI" --timeframe "today 12-m"  # 近12个月
  python3 trends_monitor.py trending --geo US               # 今日热搜
  python3 trends_monitor.py suggest "AI"                    # 联想词
"""

import json
import sys
import argparse
import re
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
import time
import random
import os
from datetime import datetime

COOKIE_FILE = "/tmp/gt_cookies.txt"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER_BASE = "https://trends.google.com/trends/explore"


def curl_get(url, referer=None):
    """Use curl with cookies to fetch Google Trends API."""
    ref = referer or REFERER_BASE
    cmd = [
        "curl", "-s", "-b", COOKIE_FILE,
        "-H", f"User-Agent: {UA}",
        "-H", f"Referer: {ref}",
        url
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    content = re.sub(r"^\)\]\}',?\n?", "", r.stdout)
    if not content.strip():
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def refresh_cookies():
    """Refresh Google Trends cookies."""
    subprocess.run(
        ["curl", "-s", "-c", COOKIE_FILE, "-o", "/dev/null",
         "-H", f"User-Agent: {UA}",
         "https://trends.google.com/trends/?geo=US"],
        capture_output=True, timeout=15
    )
    time.sleep(random.uniform(1, 2))


def get_explore_widgets(keywords, timeframe="today 3-m", geo=""):
    """Get widget tokens from explore endpoint."""
    comparison = [
        {"keyword": kw.strip(), "geo": geo, "time": timeframe}
        for kw in keywords[:5]
    ]
    req_data = json.dumps({
        "comparisonItem": comparison,
        "category": 0,
        "property": ""
    })
    url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=-480&req={urllib.parse.quote(req_data)}"
    referer = f"{REFERER_BASE}?q={urllib.parse.quote(','.join(keywords))}"
    data = curl_get(url, referer)
    if not data:
        return {}
    return {w["id"]: w for w in data.get("widgets", [])}


def fetch_timeseries(widget, keywords):
    """Fetch interest over time data."""
    if not widget:
        return {}, {}
    token = widget["token"]
    req = json.dumps(widget["request"])
    url = f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=-480&req={urllib.parse.quote(req)}&token={token}"
    data = curl_get(url)
    if not data:
        return {}, {}

    timeline = data.get("default", {}).get("timelineData", [])
    time_data = {}
    trend_dirs = {}

    for ki, kw in enumerate(keywords):
        values = []
        ts = {}
        for point in timeline:
            vals = point.get("value", [])
            if ki < len(vals):
                ts[point.get("formattedTime", "")] = vals[ki]
                values.append(vals[ki])
        time_data[kw] = ts

        if len(values) >= 4:
            split = max(1, len(values) * 3 // 4)
            avg_e = sum(values[:split]) / len(values[:split])
            avg_r = sum(values[split:]) / len(values[split:])
            change = ((avg_r - avg_e) / avg_e * 100) if avg_e else (100 if avg_r > 0 else 0)
            if change > 30:
                direction = "rising"
            elif change < -30:
                direction = "declining"
            else:
                direction = "stable"
            trend_dirs[kw] = {
                "direction": direction,
                "change_pct": round(change, 1),
                "current": values[-1],
                "peak": max(values),
                "trough": min(values),
                "avg_earlier": round(avg_e, 1),
                "avg_recent": round(avg_r, 1),
            }

    return time_data, trend_dirs


def fetch_related_queries(widget):
    """Fetch related queries (top + rising)."""
    if not widget:
        return {}
    token = widget["token"]
    req = json.dumps(widget["request"])
    url = f"https://trends.google.com/trends/api/widgetdata/relatedsearches?hl=en-US&tz=-480&req={urllib.parse.quote(req)}&token={token}"
    data = curl_get(url)
    if not data:
        return {}

    result = {}
    ranked = data.get("default", {}).get("rankedList", [])
    for i, rlist in enumerate(ranked):
        label = "top" if i == 0 else "rising"
        items = []
        for kw in rlist.get("rankedKeyword", [])[:15]:
            items.append({
                "query": kw.get("query", ""),
                "value": kw.get("formattedValue", str(kw.get("value", 0))),
            })
        result[label] = items
    return result


def fetch_geo_data(widget):
    """Fetch interest by region."""
    if not widget:
        return []
    token = widget["token"]
    req = json.dumps(widget["request"])
    url = f"https://trends.google.com/trends/api/widgetdata/comparedgeo?hl=en-US&tz=-480&req={urllib.parse.quote(req)}&token={token}"
    data = curl_get(url)
    if not data:
        return []

    geo_list = data.get("default", {}).get("geoMapData", [])
    # Filter out zero values
    results = []
    for g in geo_list:
        val = g.get("value", [0])[0]
        if val > 0:
            results.append({"region": g.get("geoName", ""), "value": val})
    return sorted(results, key=lambda x: x["value"], reverse=True)[:15]


def get_suggestions(keyword):
    """Get keyword suggestions from autocomplete API."""
    url = f"https://trends.google.com/trends/api/autocomplete/{urllib.parse.quote(keyword)}?hl=en-US"
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    try:
        req = urllib.request.Request(url, headers=headers)
        import urllib.request
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
        content = re.sub(r"^\)\]\}',?\n?", "", content)
        data = json.loads(content)
        return [
            {"title": t.get("title", ""), "type": t.get("type", "")}
            for t in data.get("default", {}).get("topics", [])[:10]
        ]
    except:
        return []


def get_trending_rss(geo="US"):
    """Get daily trending searches via RSS."""
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        cmd = ["curl", "-s", "-H", f"User-Agent: {UA}", url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ns = {"ht": "https://trends.google.com/trending/rss"}
        root = ET.fromstring(r.stdout)
        items = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            traffic = item.findtext("ht:approx_traffic", "", ns)
            news = []
            for n in item.findall("ht:news_item", ns):
                news.append({
                    "title": n.findtext("ht:news_item_title", "", ns),
                    "source": n.findtext("ht:news_item_source", "", ns),
                })
            items.append({"title": title, "traffic": traffic, "news": news[:2]})
        return items
    except:
        return []


# === REPORT FORMATTERS ===

def format_monitor_report(keywords, time_data, trend_dirs, related_queries, geo_data, suggestions):
    """Format full monitoring report."""
    lines = [
        f"## 📊 Google Trends 监控报告: {', '.join(keywords)}",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # Trend direction
    for kw, info in trend_dirs.items():
        d = info["direction"]
        pct = info["change_pct"]
        emoji_map = {"rising": "🔥" if pct > 50 else "📈", "declining": "📉", "stable": "➡️"}
        label_map = {"rising": "上升", "declining": "下降", "stable": "平稳"}
        lines.append(f"### {emoji_map.get(d, '❓')} {kw}: {label_map.get(d, '?')} ({pct:+.1f}%)")
        lines.append(f"- 当前热度: **{info['current']}**/100 | 峰值: {info['peak']} | 谷值: {info['trough']}")
        lines.append("")

        # Recent week
        ts = time_data.get(kw, {})
        if ts:
            recent_items = list(ts.items())[-7:]
            lines.append("**近7天:**")
            for date, val in recent_items:
                bar = "█" * (val // 5)
                lines.append(f"  {date}: {val} {bar}")
            lines.append("")

    # Rising queries (most valuable for SEO)
    if related_queries.get("rising"):
        lines.append("### 🚀 崛起相关查询 (Rising)")
        for q in related_queries["rising"]:
            val = q["value"]
            if "Breakout" in str(val):
                lines.append(f"- 🔥 **{q['query']}** — Breakout!")
            else:
                lines.append(f"- **{q['query']}** — {val}")
        lines.append("")

    # Top queries
    if related_queries.get("top"):
        lines.append("### 🔝 热门相关查询 (Top)")
        for q in related_queries["top"]:
            lines.append(f"- {q['query']} — {q['value']}")
        lines.append("")

    # Geo distribution
    if geo_data:
        lines.append("### 🌍 热度地域分布 (Top 10)")
        for g in geo_data[:10]:
            bar = "█" * (g["value"] // 5)
            lines.append(f"- {g['region']}: {g['value']} {bar}")
        lines.append("")

    # Suggestions
    if suggestions:
        lines.append("### 💡 联想词")
        for s in suggestions:
            stype = f" ({s['type']})" if s["type"] else ""
            lines.append(f"- {s['title']}{stype}")
        lines.append("")

    return "\n".join(lines)


def format_trending_report(items, geo):
    """Format trending report."""
    lines = [
        f"## 🔥 Google 今日热搜 ({geo})",
        f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    for i, item in enumerate(items[:20], 1):
        lines.append(f"**{i}. {item['title']}** — {item['traffic']} 搜索量")
        for n in item.get("news", []):
            lines.append(f"   - {n['title'][:60]} ({n['source']})")
        lines.append("")
    return "\n".join(lines)


# === COMMANDS ===

def cmd_monitor(args):
    """Full keyword monitoring."""
    keywords = [k.strip() for k in args.keyword.split(",")][:5]

    refresh_cookies()

    widgets = get_explore_widgets(keywords, args.timeframe, args.geo)
    if not widgets:
        print("ERROR: Failed to get explore data. Google may be rate-limiting.", file=sys.stderr)
        sys.exit(1)

    time.sleep(random.uniform(1.5, 2.5))
    time_data, trend_dirs = fetch_timeseries(widgets.get("TIMESERIES"), keywords)

    time.sleep(random.uniform(1.5, 2.5))
    related_queries = fetch_related_queries(widgets.get("RELATED_QUERIES"))

    time.sleep(random.uniform(1.5, 2.5))
    geo_data = fetch_geo_data(widgets.get("GEO_MAP"))

    suggestions = get_suggestions(keywords[0])

    if args.format == "json":
        result = {
            "keywords": keywords,
            "timeframe": args.timeframe,
            "geo": args.geo or "global",
            "timestamp": datetime.now().isoformat(),
            "trend_direction": trend_dirs,
            "interest_over_time": time_data,
            "related_queries": related_queries,
            "interest_by_region": geo_data,
            "suggestions": suggestions,
        }
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        output = format_monitor_report(keywords, time_data, trend_dirs, related_queries, geo_data, suggestions)

    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[OK] Saved to {args.output}", file=sys.stderr)


def cmd_trending(args):
    """Daily trending searches."""
    items = get_trending_rss(args.geo)
    if args.format == "json":
        print(json.dumps({"geo": args.geo, "timestamp": datetime.now().isoformat(), "items": items}, ensure_ascii=False, indent=2))
    else:
        print(format_trending_report(items, args.geo))


def cmd_suggest(args):
    """Keyword suggestions."""
    suggestions = get_suggestions(args.keyword)
    if args.format == "json":
        print(json.dumps({"keyword": args.keyword, "suggestions": suggestions}, ensure_ascii=False, indent=2))
    else:
        print(f"## 💡 关键词联想: {args.keyword}\n")
        for s in suggestions:
            stype = f" ({s['type']})" if s["type"] else ""
            print(f"- {s['title']}{stype}")


def main():
    parser = argparse.ArgumentParser(description="Google Trends Monitor v4")
    parser.add_argument("--format", choices=["json", "report"], default="report")
    parser.add_argument("--geo", default="", help="Region code (US, CN, JP, etc)")
    parser.add_argument("--output", default="-", help="Output file (default: stdout)")

    sub = parser.add_subparsers(dest="command")

    p_monitor = sub.add_parser("monitor", help="Full keyword trend analysis")
    p_monitor.add_argument("keyword", help="Keyword(s), comma-separated for comparison")
    p_monitor.add_argument("--timeframe", default="today 3-m",
                           help="Time range: now 1-H, now 4-H, now 1-d, now 7-d, today 1-m, today 3-m, today 12-m, today 5-y")

    p_trending = sub.add_parser("trending", help="Daily trending searches")

    p_suggest = sub.add_parser("suggest", help="Keyword suggestions")
    p_suggest.add_argument("keyword", help="Keyword to get suggestions for")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "trending":
        cmd_trending(args)
    elif args.command == "suggest":
        cmd_suggest(args)


if __name__ == "__main__":
    main()
