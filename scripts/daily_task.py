#!/usr/bin/env python3
"""
Google Trends 每日定时任务
由 OpenClaw cron 调用，输出 JSON 供 agent 处理

输出结构:
{
  "status": "ok" | "error",
  "results_file": "path/to/results.json",
  "feishu_report": "markdown report for feishu doc",
  "alert_message": "message for feishu group",
  "summary": "brief summary"
}
"""

import json
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.batch_monitor import run_batch_monitor, format_feishu_report, format_alert_message
from datetime import datetime


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    keywords_file = "config/keywords.json"
    output_file = f"results/{date_str}.json"

    try:
        results = run_batch_monitor(
            keywords_file=keywords_file,
            timeframe="now 7-d",
            geo="",
            output_file=output_file,
        )

        report = format_feishu_report(results)
        alert = format_alert_message(results)

        n_keywords = len(results.get("keyword_trends", {}))
        n_rising = len(results.get("all_rising", []))
        n_breakout = len([q for q in results.get("all_rising", []) if "Breakout" in str(q["value"])])

        output = {
            "status": "ok",
            "date": date_str,
            "results_file": output_file,
            "feishu_report": report,
            "alert_message": alert,
            "summary": f"监控 {n_keywords}/{results['total_keywords']} 词根, 崛起词 {n_rising} 个, Breakout {n_breakout} 个",
            "has_rising": n_rising > 0,
        }
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        output = {
            "status": "error",
            "date": date_str,
            "error": str(e),
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
