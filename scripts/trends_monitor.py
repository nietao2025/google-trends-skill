#!/usr/bin/env python3
"""
Google Trends 监控 v4 - 稳定版
使用 Google Trends RSS feed + 联想词 API

功能:
- 获取每日热门趋势 (RSS feed, 稳定)
- 获取关键词联想词 (API, 稳定)
- 支持多地域 (US, GB, JP, CN, etc)
- 输出 JSON 或格式化报告

用法:
  python3 trends_monitor.py trending [--geo US]    # 今日热门
  python3 trends_monitor.py suggest "keyword"     # 联想词
  python3 trends_monitor.py full "keyword"        # 完整分析（联想词+热门）
"""

import json
import sys
import argparse
import random
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import re
from datetime import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
]

NS = {"ht": "https://trends.google.com/trending/rss"}


def fetch_url(url, retries=2):
    """URL 请求."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt < retries - 1:
                continue
            print(f"[ERROR] {e}", file=sys.stderr)
    return None


def get_trending_rss(geo="US"):
    """获取每日热门趋势 (RSS)."""
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    content = fetch_url(url)
    if not content:
        return []
    
    try:
        root = ET.fromstring(content)
        items = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            traffic = item.findtext("ht:approx_traffic", "", NS)
            pub_date = item.findtext("pubDate", "")
            picture = item.findtext("ht:picture", "", NS)
            
            news_items = []
            for news in item.findall("ht:news_item", NS):
                news_items.append({
                    "title": news.findtext("ht:news_item_title", "", NS),
                    "url": news.findtext("ht:news_item_url", "", NS),
                    "source": news.findtext("ht:news_item_source", "", NS),
                })
            
            items.append({
                "title": title,
                "traffic": traffic,
                "pubDate": pub_date,
                "picture": picture,
                "news": news_items[:3],
            })
        return items
    except Exception as e:
        print(f"[ERROR] parse RSS: {e}", file=sys.stderr)
        return []


def get_suggestions(keyword):
    """获取 Google Trends 联想词."""
    url = f"https://trends.google.com/trends/api/autocomplete/{urllib.parse.quote(keyword)}?hl=en-US"
    content = fetch_url(url)
    if not content:
        return []
    
    content = re.sub(r"^\)\]\}',?\n?", "", content)
    try:
        data = json.loads(content)
        topics = data.get("default", {}).get("topics", [])
        return [
            {
                "title": t.get("title", ""),
                "type": t.get("type", ""),
                "mid": t.get("mid", ""),
            }
            for t in topics[:15]
        ]
    except Exception as e:
        print(f"[ERROR] parse suggestions: {e}", file=sys.stderr)
        return []


def format_trending_report(items, geo):
    """格式化热门趋势报告."""
    lines = [
        f"## 🔥 Google 今日热搜 ({geo})",
        f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    
    for i, item in enumerate(items[:20], 1):
        traffic = item["traffic"]
        title = item["title"]
        lines.append(f"**{i}. {title}** — {traffic} 搜索量")
        
        if item.get("news"):
            for news in item["news"][:2]:
                source = news.get("source", "")
                news_title = news.get("title", "")[:60]
                if source:
                    lines.append(f"   - {news_title} ({source})")
        lines.append("")
    
    return "\n".join(lines)


def format_suggest_report(keyword, suggestions):
    """格式化联想词报告."""
    lines = [
        f"## 💡 关键词分析: {keyword}",
        f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "### 相关联想词",
    ]
    
    for s in suggestions:
        title = s["title"]
        stype = s["type"]
        if stype:
            lines.append(f"- **{title}** ({stype})")
        else:
            lines.append(f"- {title}")
    
    if not suggestions:
        lines.append("- (无联想词)")
    
    return "\n".join(lines)


def cmd_trending(args):
    """今日热门命令."""
    items = get_trending_rss(args.geo)
    
    if args.format == "json":
        result = {
            "geo": args.geo,
            "timestamp": datetime.now().isoformat(),
            "items": items,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_trending_report(items, args.geo))


def cmd_suggest(args):
    """联想词命令."""
    suggestions = get_suggestions(args.keyword)
    
    if args.format == "json":
        result = {
            "keyword": args.keyword,
            "timestamp": datetime.now().isoformat(),
            "suggestions": suggestions,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_suggest_report(args.keyword, suggestions))


def cmd_full(args):
    """完整分析命令."""
    suggestions = get_suggestions(args.keyword)
    trending = get_trending_rss(args.geo)
    
    if args.format == "json":
        result = {
            "keyword": args.keyword,
            "geo": args.geo,
            "timestamp": datetime.now().isoformat(),
            "suggestions": suggestions,
            "trending": trending[:10],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        lines = []
        lines.append(format_suggest_report(args.keyword, suggestions))
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(format_trending_report(trending[:10], args.geo))
        print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Google Trends 监控 v4")
    parser.add_argument("--format", choices=["json", "report"], default="report")
    parser.add_argument("--geo", default="US", help="地域 (US, GB, JP, CN, etc)")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # trending 子命令
    p_trending = subparsers.add_parser("trending", help="今日热门趋势")
    p_trending.set_defaults(func=cmd_trending)
    
    # suggest 子命令
    p_suggest = subparsers.add_parser("suggest", help="关键词联想")
    p_suggest.add_argument("keyword", help="关键词")
    p_suggest.set_defaults(func=cmd_suggest)
    
    # full 子命令
    p_full = subparsers.add_parser("full", help="完整分析")
    p_full.add_argument("keyword", help="关键词")
    p_full.set_defaults(func=cmd_full)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 继承全局参数
    if not hasattr(args, "geo"):
        args.geo = "US"
    if not hasattr(args, "format"):
        args.format = "report"
    
    args.func(args)


if __name__ == "__main__":
    main()
