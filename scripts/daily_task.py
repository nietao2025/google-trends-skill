#!/usr/bin/env python3
"""
Google Trends 每日定时任务
由 OpenClaw cron 调用，输出 JSON 供 agent 处理

用法:
  python3 daily_task.py                                         # 默认用 keywords.json
  python3 daily_task.py --keywords config/keywords-ai.json --label ai
  python3 daily_task.py --keywords config/keywords-base.json --label base
"""

import json
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.batch_monitor import run_batch_monitor, format_feishu_report, format_alert_message
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", default="config/keywords.json", help="Keywords JSON file")
    parser.add_argument("--label", default="", help="Label for output file (e.g. ai, base)")
    parser.add_argument("--timeframe", default="now 7-d")
    parser.add_argument("--geo", default="")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    suffix = f"-{args.label}" if args.label else ""
    output_file = f"results/{date_str}{suffix}.json"

    try:
        results = run_batch_monitor(
            keywords_file=args.keywords,
            timeframe=args.timeframe,
            geo=args.geo,
            output_file=output_file,
        )

        report = format_feishu_report(results)
        alert = format_alert_message(results)

        n_keywords = len(results.get("keyword_trends", {}))
        n_rising = len(results.get("all_rising", []))
        n_breakout = len([q for q in results.get("all_rising", []) if "Breakout" in str(q["value"])])

        label_text = f" [{args.label}]" if args.label else ""
        output = {
            "status": "ok",
            "date": date_str,
            "label": args.label,
            "results_file": output_file,
            "feishu_report": report,
            "alert_message": alert,
            "summary": f"{label_text}监控 {n_keywords}/{results['total_keywords']} 词根, 崛起词 {n_rising} 个, Breakout {n_breakout} 个",
            "has_rising": n_rising > 0,
        }
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        output = {
            "status": "error",
            "date": date_str,
            "label": args.label,
            "error": str(e),
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
