#!/usr/bin/env bash
# Google Trends 每日词根监控 cron 任务
# 功能: 跑批量监控 → 写飞书文档 → 推送崛起词到飞书群

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="/root/.openclaw/workspace/skills/google-trends"
DATE=$(date +%Y-%m-%d)

echo "[$(date)] Starting daily Google Trends monitor..."

# Step 1: 运行批量监控
cd "$WORKSPACE"
python3 scripts/batch_monitor.py \
  --keywords config/keywords.json \
  --timeframe "now 7-d" \
  --output "results/${DATE}.json"

echo "[$(date)] Batch monitoring complete."

# Step 2: 生成飞书报告
REPORT=$(python3 scripts/batch_monitor.py \
  --keywords config/keywords.json \
  --timeframe "now 7-d" \
  --output "results/${DATE}.json" \
  --report 2>/dev/null || python3 -c "
import json
with open('results/${DATE}.json') as f:
    data = json.load(f)
# Just use the saved data
from scripts.batch_monitor import format_feishu_report
print(format_feishu_report(data))
")

# Step 3: 生成推送消息
ALERT=$(python3 -c "
import json
import sys
sys.path.insert(0, '.')
from scripts.batch_monitor import format_alert_message
with open('results/${DATE}.json') as f:
    data = json.load(f)
print(format_alert_message(data))
" 2>/dev/null || echo "⚠️ 报告生成失败，请检查 results/${DATE}.json")

echo "[$(date)] Report generated. Alert message:"
echo "$ALERT"
echo "---"
echo "FEISHU_REPORT_READY"
echo "FEISHU_ALERT_READY"
