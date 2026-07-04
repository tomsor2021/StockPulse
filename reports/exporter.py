"""复盘报告导出"""
import io
import html
from datetime import date


def export_html_report(user_info, market_data, review_journal):
    """导出复盘报告为 HTML"""
    today = date.today().isoformat()
    review_journal = dict(review_journal) if review_journal else None
    username = html.escape(user_info.get("nickname", user_info.get("username", "用户")))
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>复盘报告 {today}</title>
<style>
  body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
  h1 {{ color: #1976D2; border-bottom: 2px solid #1976D2; padding-bottom: 8px; }}
  h2 {{ color: #555; margin-top: 24px; }}
  .section {{ margin: 16px 0; padding: 12px; background: #f5f5f5; border-radius: 6px; }}
  .meta {{ color: #888; font-size: 14px; }}
  .score {{ font-size: 20px; font-weight: bold; }}
</style></head>
<body>
  <h1>? 股票复盘报告</h1>
  <p class="meta">用户：{username} | 日期：{today}</p>
"""
    if review_journal:
        for key, label in [("market_diagnosis", "大盘诊断"), ("sector_rotation", "板块轮动"),
                            ("limit_up_analysis", "涨停分析"), ("personal_review", "操作回顾"),
                            ("plan_for_tomorrow", "次日计划")]:
            val = review_journal.get(key)
            if val:
                html_content += f'<div class="section"><h2>{label}</h2><p>{html.escape(str(val))}</p></div>\n'
        html_content += f'<p>情绪评分：{review_journal.get("emotion_score", "N/A")}/10 | 纪律评分：{review_journal.get("discipline_score", "N/A")}/10</p>\n'

    html_content += "<hr><p style='color:#999;font-size:12px;'>由 StockPulse 生成</p></body></html>"
    return html_content
