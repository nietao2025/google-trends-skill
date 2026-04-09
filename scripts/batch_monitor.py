#!/usr/bin/env python3
"""
Google Trends 批量词根监控
每次查5个词的 rising queries，所有词跑完后：
1. 生成完整报告（写入飞书文档）
2. 提取崛起词摘要（用于消息推送）

用法:
  python3 batch_monitor.py --keywords config/keywords.json --output results/YYYY-MM-DD.json
"""

import json
import sys
import os
import re
import subprocess
import urllib.parse
import time
import random
import argparse
from datetime import datetime

COOKIE_FILE = "/tmp/gt_cookies.txt"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def curl_get(url):
    """Fetch URL via curl with cookies."""
    cmd = [
        "curl", "-s", "-b", COOKIE_FILE,
        "-H", f"User-Agent: {UA}",
        "-H", f"Referer: https://trends.google.com/trends/explore",
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


def explore_batch(keywords, timeframe="now 7-d", geo=""):
    """Get explore widgets for a batch of keywords (max 5)."""
    comparison = [
        {"keyword": kw, "geo": geo, "time": timeframe}
        for kw in keywords[:5]
    ]
    req_data = json.dumps({
        "comparisonItem": comparison,
        "category": 0,
        "property": ""
    })
    url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=-480&req={urllib.parse.quote(req_data)}"
    return curl_get(url)


def fetch_timeseries(widget, keywords):
    """Fetch time series data."""
    if not widget:
        return {}
    token = widget["token"]
    req = json.dumps(widget["request"])
    url = f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=-480&req={urllib.parse.quote(req)}&token={token}"
    data = curl_get(url)
    if not data:
        return {}

    timeline = data.get("default", {}).get("timelineData", [])
    result = {}
    for ki, kw in enumerate(keywords):
        values = []
        for point in timeline:
            vals = point.get("value", [])
            if ki < len(vals):
                values.append(vals[ki])

        if len(values) >= 4:
            split = max(1, len(values) * 3 // 4)
            avg_e = sum(values[:split]) / len(values[:split])
            avg_r = sum(values[split:]) / len(values[split:])
            change = ((avg_r - avg_e) / avg_e * 100) if avg_e else (100 if avg_r > 0 else 0)
            result[kw] = {
                "current": values[-1] if values else 0,
                "peak": max(values) if values else 0,
                "trough": min(values) if values else 0,
                "avg_earlier": round(avg_e, 1),
                "avg_recent": round(avg_r, 1),
                "change_pct": round(change, 1),
            }
    return result


def fetch_related_queries(widget):
    """Fetch rising + top queries."""
    if not widget:
        return {"top": [], "rising": []}
    token = widget["token"]
    req = json.dumps(widget["request"])
    url = f"https://trends.google.com/trends/api/widgetdata/relatedsearches?hl=en-US&tz=-480&req={urllib.parse.quote(req)}&token={token}"
    data = curl_get(url)
    if not data:
        return {"top": [], "rising": []}

    result = {}
    ranked = data.get("default", {}).get("rankedList", [])
    for i, rlist in enumerate(ranked):
        label = "top" if i == 0 else "rising"
        items = []
        for kw in rlist.get("rankedKeyword", [])[:20]:
            items.append({
                "query": kw.get("query", ""),
                "value": kw.get("formattedValue", str(kw.get("value", 0))),
            })
        result[label] = items
    return result


def process_batch(keywords, timeframe="now 7-d", geo=""):
    """Process one batch of up to 5 keywords."""
    data = explore_batch(keywords, timeframe, geo)
    if not data:
        return None

    widgets = {w["id"]: w for w in data.get("widgets", [])}

    # Time series
    time.sleep(random.uniform(1.5, 2.5))
    trend_data = fetch_timeseries(widgets.get("TIMESERIES"), keywords)

    # Related queries (only available for first keyword in batch)
    time.sleep(random.uniform(1.5, 2.5))
    related = fetch_related_queries(widgets.get("RELATED_QUERIES"))

    return {
        "keywords": keywords,
        "trends": trend_data,
        "related_queries": related,
    }


def fetch_single_rising(keyword, timeframe="now 7-d", geo=""):
    """Get rising queries for a single keyword."""
    data = explore_batch([keyword], timeframe, geo)
    if not data:
        return {"top": [], "rising": []}
    widgets = {w["id"]: w for w in data.get("widgets", [])}
    time.sleep(random.uniform(1.0, 2.0))
    return fetch_related_queries(widgets.get("RELATED_QUERIES"))


def run_batch_monitor(keywords_file, timeframe="now 7-d", geo="", output_file=None):
    """Run monitoring: Phase 1 = batch trends (5 per batch), Phase 2 = individual rising queries."""
    with open(keywords_file, "r") as f:
        all_keywords = json.load(f)

    print(f"[INFO] Monitoring {len(all_keywords)} keywords...", file=sys.stderr)
    print(f"[INFO] Timeframe: {timeframe}, Geo: {geo or 'global'}", file=sys.stderr)

    all_results = {
        "timestamp": datetime.now().isoformat(),
        "timeframe": timeframe,
        "geo": geo or "global",
        "total_keywords": len(all_keywords),
        "keyword_trends": {},
        "rising_queries": {},
        "all_rising": [],
        "errors": [],
    }

    # === Phase 1: Batch trend direction (5 per batch) ===
    batches = [all_keywords[i:i+5] for i in range(0, len(all_keywords), 5)]
    print(f"[INFO] Phase 1: {len(batches)} batches for trend direction", file=sys.stderr)

    for bi, batch in enumerate(batches):
        print(f"[INFO] Phase1 batch {bi+1}/{len(batches)}: {', '.join(batch)}", file=sys.stderr)

        if bi % 5 == 0:
            refresh_cookies()

        try:
            data = explore_batch(batch, timeframe, geo)
            if data:
                widgets = {w["id"]: w for w in data.get("widgets", [])}
                time.sleep(random.uniform(1.5, 2.5))
                trend_data = fetch_timeseries(widgets.get("TIMESERIES"), batch)
                for kw, trend in trend_data.items():
                    all_results["keyword_trends"][kw] = trend
            else:
                all_results["errors"].append(f"Phase1 batch {bi+1} failed: {', '.join(batch)}")
                print(f"[WARN] Phase1 batch {bi+1} no data", file=sys.stderr)
                time.sleep(random.uniform(10, 15))
        except Exception as e:
            all_results["errors"].append(f"Phase1 batch {bi+1}: {str(e)}")
            print(f"[ERROR] Phase1 batch {bi+1}: {e}", file=sys.stderr)

        time.sleep(random.uniform(3, 5))

    # === Phase 2: Individual rising queries for each keyword ===
    print(f"[INFO] Phase 2: Fetching rising queries for {len(all_keywords)} keywords individually", file=sys.stderr)

    for ki, keyword in enumerate(all_keywords):
        print(f"[INFO] Phase2 [{ki+1}/{len(all_keywords)}]: {keyword}", file=sys.stderr)

        if ki % 8 == 0:
            refresh_cookies()

        try:
            queries = fetch_single_rising(keyword, timeframe, geo)
            if queries and (queries.get("rising") or queries.get("top")):
                all_results["rising_queries"][keyword] = queries
                for q in queries.get("rising", []):
                    all_results["all_rising"].append({
                        "query": q["query"],
                        "value": q["value"],
                        "source_keyword": keyword,
                    })
            # Small chance of no data — not an error
        except Exception as e:
            all_results["errors"].append(f"Phase2 {keyword}: {str(e)}")
            print(f"[ERROR] Phase2 {keyword}: {e}", file=sys.stderr)

        time.sleep(random.uniform(3, 5))

    # Sort rising queries by value (Breakout first, then by percentage)
    def sort_key(item):
        val = item["value"]
        if "Breakout" in str(val):
            return 999999
        try:
            return int(str(val).replace("+", "").replace("%", "").replace(",", ""))
        except:
            return 0

    all_results["all_rising"].sort(key=sort_key, reverse=True)

    # Sort keyword trends by change
    all_results["top_risers"] = sorted(
        [{"keyword": k, **v} for k, v in all_results["keyword_trends"].items()],
        key=lambda x: x["change_pct"],
        reverse=True
    )[:20]

    all_results["top_decliners"] = sorted(
        [{"keyword": k, **v} for k, v in all_results["keyword_trends"].items()],
        key=lambda x: x["change_pct"],
    )[:10]

    # Save
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"[OK] Results saved to {output_file}", file=sys.stderr)

    return all_results


def format_feishu_report(results):
    """Format results as a report suitable for Feishu document."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Google Trends 词根监控日报 {date_str}",
        "",
        f"- 监控词根数: {results['total_keywords']}",
        f"- 时间范围: {results['timeframe']}",
        f"- 地域: {results['geo']}",
        f"- 数据源: Google Trends",
        "",
    ]

    # Top risers
    if results.get("top_risers"):
        lines.append("## 📈 词根热度上升 Top 20")
        lines.append("")
        for item in results["top_risers"]:
            pct = item["change_pct"]
            if pct > 50:
                emoji = "🔥"
            elif pct > 20:
                emoji = "📈"
            elif pct > 0:
                emoji = "⬆️"
            else:
                emoji = "➡️"
            lines.append(f"- {emoji} **{item['keyword']}** — {pct:+.1f}% (当前:{item['current']} 峰值:{item['peak']})")
        lines.append("")

    # Top decliners
    if results.get("top_decliners"):
        lines.append("## 📉 词根热度下降 Top 10")
        lines.append("")
        for item in results["top_decliners"]:
            if item["change_pct"] < 0:
                lines.append(f"- 📉 **{item['keyword']}** — {item['change_pct']:+.1f}% (当前:{item['current']})")
        lines.append("")

    # Rising queries (most valuable)
    if results.get("all_rising"):
        lines.append("## 🚀 崛起搜索词 (Rising Queries)")
        lines.append("")
        breakouts = [q for q in results["all_rising"] if "Breakout" in str(q["value"])]
        risers = [q for q in results["all_rising"] if "Breakout" not in str(q["value"])]

        if breakouts:
            lines.append("### 🔥 Breakout (爆发词)")
            lines.append("")
            for q in breakouts[:20]:
                lines.append(f"- **{q['query']}** — Breakout! (来源词根: {q['source_keyword']})")
            lines.append("")

        if risers:
            lines.append("### 📈 高增长词")
            lines.append("")
            for q in risers[:30]:
                lines.append(f"- **{q['query']}** — {q['value']} (来源: {q['source_keyword']})")
            lines.append("")

    # Errors
    if results.get("errors"):
        lines.append("## ⚠️ 错误记录")
        lines.append("")
        for e in results["errors"]:
            lines.append(f"- {e}")
        lines.append("")

    return "\n".join(lines)


def format_alert_message(results):
    """Format rising queries alert for messaging."""
    lines = ["📊 **Google Trends 词根日报**", ""]

    # Top 5 rising keywords
    if results.get("top_risers"):
        lines.append("**📈 热度上升词根 Top 5:**")
        for item in results["top_risers"][:5]:
            pct = item["change_pct"]
            emoji = "🔥" if pct > 50 else "📈"
            lines.append(f"{emoji} {item['keyword']}: {pct:+.1f}%")
        lines.append("")

    # Breakout queries
    breakouts = [q for q in results.get("all_rising", []) if "Breakout" in str(q["value"])]
    if breakouts:
        lines.append(f"**🔥 Breakout 爆发词 ({len(breakouts)}个):**")
        for q in breakouts[:10]:
            lines.append(f"🔥 {q['query']} (← {q['source_keyword']})")
        if len(breakouts) > 10:
            lines.append(f"...还有 {len(breakouts)-10} 个")
        lines.append("")

    # Top rising queries
    risers = [q for q in results.get("all_rising", []) if "Breakout" not in str(q["value"])]
    if risers:
        lines.append(f"**🚀 高增长词 Top 10:**")
        for q in risers[:10]:
            lines.append(f"📈 {q['query']}: {q['value']} (← {q['source_keyword']})")
        lines.append("")

    if not breakouts and not risers:
        lines.append("今日无显著崛起词。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Batch Google Trends Monitor")
    parser.add_argument("--keywords", default="config/keywords.json", help="Keywords JSON file")
    parser.add_argument("--timeframe", default="now 7-d", help="Time range")
    parser.add_argument("--geo", default="", help="Region")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--report", action="store_true", help="Print Feishu report to stdout")
    parser.add_argument("--alert", action="store_true", help="Print alert message to stdout")

    args = parser.parse_args()

    if not args.output:
        date_str = datetime.now().strftime("%Y-%m-%d")
        args.output = f"results/{date_str}.json"

    results = run_batch_monitor(args.keywords, args.timeframe, args.geo, args.output)

    if args.report:
        print(format_feishu_report(results))
    elif args.alert:
        print(format_alert_message(results))
    else:
        # Default: print summary
        n_keywords = len(results.get("keyword_trends", {}))
        n_rising = len(results.get("all_rising", []))
        n_breakout = len([q for q in results.get("all_rising", []) if "Breakout" in str(q["value"])])
        n_errors = len(results.get("errors", []))
        print(f"✅ 监控完成: {n_keywords}/{results['total_keywords']} 词根成功")
        print(f"🚀 崛起词: {n_rising} 个 (其中 Breakout: {n_breakout} 个)")
        if n_errors:
            print(f"⚠️ 错误: {n_errors} 个批次失败")


if __name__ == "__main__":
    main()
