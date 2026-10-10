# 陈氏鉴股V6.0 Watchlist Dashboard

独立 Streamlit 应用 (端口 8910),与主 8905 单股分析 UI 并存,实现自选股 CRUD、跨股对比、历史时序、组合推荐。

## 启动
```bash
.venv/Scripts/python.exe -m streamlit run app.py --server.port 8910
```
或 `restart.bat` (Windows)

## 隔离保证
- DuckDB 只读
- 不调用 LLM
- 仅写 `data/watchlist.db`
- 不影响主 8905

详见 spec: `陈氏鉴股V6.0-v697/docs/superpowers/specs/2026-10-10-watchlist-dashboard-design.md`