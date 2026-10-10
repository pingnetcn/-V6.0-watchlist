"""
DuckDB table freshness + coverage stats + maintenance triggers.
"""
import pandas as pd
from datetime import date, timedelta
from lib.db import table_freshness, coverage_stats
from lib.paths import DB_PATH

SCHEMA_VERSION = 1


def compute_full_health() -> dict:
    tf = table_freshness()
    today = date.today()
    green, yellow, red = 0, 0, 0
    for _, row in tf.iterrows():
        if row["max_date"] is None:
            red += 1
        elif isinstance(row["max_date"], (date, pd.Timestamp)):
            days = (today - pd.Timestamp(row["max_date"]).date()).days
            if days <= 1:
                green += 1
            elif days <= 3:
                yellow += 1
            else:
                red += 1
    return {
        "table_freshness": tf,
        "global_health": {"green": green, "yellow": yellow, "red": red},
    }


MAINTENANCE_ACTIONS = {
    "trigger_a_share_daily_update": {
        "label": "▶ 触发 A 股 daily_update 部分段",
        "command": ["python", "-m", "scripts.daily_update", "--a-only"],
        "warning": "将暂时占用主 DuckDB 写连接,8905 写入会等待",
    },
    "trigger_hk_kline_fill": {
        "label": "▶ 触发 港股 K 线补空洞",
        "command": ["python", "-m", "scripts.daily_update", "--hk-only"],
        "warning": "将调用腾讯 K 线 API,可能触发限流",
    },
    "trigger_watchlist_revaluation": {
        "label": "▶ 触发 自选股估值回灌",
        "command": ["python", "-m", "scripts.batch_valuation", "--watchlist"],
        "warning": "会消耗 LLM 配额,与 8905 抢资源",
    },
    "view_recent_logs": {
        "label": "▶ 查看最近 7 天日志 (只读)",
        "command": None,
        "warning": None,
        "readonly": True,
    },
}