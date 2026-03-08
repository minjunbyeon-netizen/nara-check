"""
리포트 생성 모듈 - 마크다운 및 HTML 형식의 일일 리포트 작성
"""
import os
import logging
from datetime import datetime
from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def generate_report(analyzed_bids: list[dict], report_date: datetime = None) -> str:
    """분석된 공고 목록으로 마크다운 리포트를 생성하고 파일 경로를 반환한다."""
    if report_date is None:
        report_date = datetime.now()

    date_str = report_date.strftime("%Y-%m-%d")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, f"report_{date_str}.md")

    content = _build_markdown(analyzed_bids, date_str)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"리포트 저장: {filepath}")
    return filepath


def _build_markdown(bids: list[dict], date_str: str) -> str:
    # 마감 임박(D-3 이하) 분리 — 점수 무관하게 별도 섹션
    alert_bids = [b for b in bids if b.get("_deadline_alert")]
    normal_bids = [b for b in bids if not b.get("_deadline_alert")]

    total = len(bids)
    top_bids = [b for b in normal_bids if b.get("score", 0) >= 75]
    mid_bids = [b for b in normal_bids if 50 <= b.get("score", 0) < 75]
    low_bids = [b for b in normal_bids if b.get("score", 0) < 50]

    lines = [
        f"# 나라장터 마케팅 공고 일일 리포트",
        f"",
        f"**날짜**: {date_str}  |  **총 공고수**: {total}건  |  **추천 공고**: {len(top_bids)}건  |  **마감임박 알림**: {len(alert_bids)}건",
        f"",
        f"---",
        f"",
        f"## 요약",
        f"",
        f"| 등급 | 건수 | 비율 |",
        f"|------|------|------|",
        f"| 강력추천 (75점+) | {len(top_bids)}건 | {len(top_bids)/total*100:.0f}% |" if total else "| - | - | - |",
        f"| 검토 (50~74점) | {len(mid_bids)}건 | {len(mid_bids)/total*100:.0f}% |" if total else "| - | - | - |",
        f"| 보류 (50점 미만) | {len(low_bids)}건 | {len(low_bids)/total*100:.0f}% |" if total else "| - | - | - |",
        f"| 마감임박 (D-3↓, 제안불가) | {len(alert_bids)}건 | - |",
        f"",
        f"---",
        f"",
    ]

    if not bids:
        lines.append("오늘은 마케팅 관련 공고가 없습니다.")
        return "\n".join(lines)

    # 마감 임박 알림 섹션 (제안 불가, 참고만)
    if alert_bids:
        lines += [
            f"## ⚠️ 마감 임박 알림 — D-3 이하 (제안서 준비 불가, 참고용)",
            f"",
            f"| 공고명 | 기관 | 예산 | 마감 | AI점수 |",
            f"|--------|------|------|------|--------|",
        ]
        for bid in alert_bids:
            name = bid.get("bidNtceNm", "N/A")[:30]
            org = bid.get("ntceInsttNm", "N/A")[:15]
            budget = bid.get("presmptPrce", "N/A")
            deadline = bid.get("bidClseDt", "N/A")[:10]
            score = bid.get("score", "-")
            lines.append(f"| {name} | {org} | {budget}원 | {deadline} | {score}점 |")
        lines += ["", "---", ""]

    # 강력 추천 공고
    if top_bids:
        lines += [
            f"## 강력 추천 공고 ({len(top_bids)}건)",
            f"",
        ]
        for bid in top_bids:
            lines += _format_bid_section(bid)

    # 검토 공고
    if mid_bids:
        lines += [
            f"## 검토 공고 ({len(mid_bids)}건)",
            f"",
        ]
        for bid in mid_bids:
            lines += _format_bid_section(bid)

    # 보류 공고 (간략히)
    if low_bids:
        lines += [
            f"## 보류 공고 ({len(low_bids)}건)",
            f"",
            f"| 공고명 | 기관 | 예산 | 마감 |",
            f"|--------|------|------|------|",
        ]
        for bid in low_bids:
            name = bid.get("bidNtceNm", "N/A")[:30]
            org = bid.get("ntceInsttNm", "N/A")[:15]
            budget = bid.get("presmptPrce", "N/A")
            deadline = bid.get("bidClseDt", "N/A")[:10]
            lines.append(f"| {name} | {org} | {budget}원 | {deadline} |")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"*리포트 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 나라장터 마케팅 공고 모니터링 시스템*",
    ]

    return "\n".join(lines)


def _format_bid_section(bid: dict) -> list[str]:
    bid_no = bid.get("bidNtceNo", "N/A")
    bid_ord = bid.get("bidNtceOrd", "000")
    bid_nm = bid.get("bidNtceNm", "N/A")
    org = bid.get("ntceInsttNm", "N/A")
    budget = bid.get("presmptPrce", "N/A")
    deadline = bid.get("bidClseDt", "N/A")
    score = bid.get("score", 0)
    grade = bid.get("grade", "-")
    reason = bid.get("reason", "")
    watch_out = bid.get("watch_out", "")
    category = bid.get("category", "")
    recommendation = bid.get("recommendation", "")
    keywords = ", ".join(bid.get("_matched_keywords", []))
    url = f"https://www.g2b.go.kr/pn/pnp/pnpe/bidPbancInfo/getBidPbancDtlInfo.do?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}"

    lines = [
        f"### {grade} [{recommendation}] {bid_nm}",
        f"",
        f"- **공고번호**: {bid_no}",
        f"- **발주기관**: {org}",
        f"- **예산**: {budget}원",
        f"- **마감일**: {deadline}",
        f"- **분류**: {category}",
        f"- **매칭 키워드**: {keywords}",
        f"- **AI 점수**: {score}점",
        f"",
        f"**추천 이유**: {reason}",
        f"",
    ]
    if watch_out:
        lines += [f"**주의사항**: {watch_out}", f""]
    lines += [f"[공고 바로가기]({url})", f"", f"---", f""]
    return lines


def generate_html_report(analyzed_bids: list[dict], report_date: datetime = None) -> str:
    """HTML 형식의 이메일용 리포트를 생성하고 파일 경로를 반환한다."""
    if report_date is None:
        report_date = datetime.now()

    date_str = report_date.strftime("%Y-%m-%d")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, f"report_{date_str}.html")

    content = _build_html(analyzed_bids, date_str)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"HTML 리포트 저장: {filepath}")
    return filepath


def _build_html(bids: list[dict], date_str: str) -> str:
    alert_bids = [b for b in bids if b.get("_deadline_alert")]
    normal_bids = [b for b in bids if not b.get("_deadline_alert")]
    top_bids = [b for b in normal_bids if b.get("score", 0) >= 75]
    mid_bids = [b for b in normal_bids if 50 <= b.get("score", 0) < 75]
    low_bids = [b for b in normal_bids if b.get("score", 0) < 50]

    def _url(bid):
        no = bid.get("bidNtceNo", "")
        ord_ = bid.get("bidNtceOrd", "000")
        return f"https://www.g2b.go.kr/pn/pnp/pnpe/bidPbancInfo/getBidPbancDtlInfo.do?bidPbancNo={no}&bidPbancOrd={ord_}"

    def score_badge(bid):
        s = bid.get("score", 0)
        color = "#2d6a4f" if s >= 75 else "#457b9d" if s >= 50 else "#aaa"
        return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">{s}점</span>'

    # ── 요약 테이블 행 생성 ──
    def summary_row(bid, idx, row_style=""):
        url = _url(bid)
        nm = bid.get("bidNtceNm", "N/A")
        org = bid.get("ntceInsttNm", "N/A")
        budget = bid.get("presmptPrce", "N/A")
        deadline = bid.get("bidClseDt", "N/A")[:10]
        rec = bid.get("recommendation", "")
        return (f'<tr style="{row_style}">'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;">{idx}</td>'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;"><a href="{url}" target="_blank" style="color:#1d3557;text-decoration:none;font-weight:600;">{nm}</a></td>'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;">{org}</td>'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;">{budget}원</td>'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;">{deadline}</td>'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;">{score_badge(bid)}</td>'
                f'<td style="padding:7px 8px;border-bottom:1px solid #f0f0f0;font-size:11px;">{rec}</td>'
                f'</tr>')

    # ── 상세 카드 생성 ──
    def detail_card(bid, border_color, bg_color):
        url = _url(bid)
        nm = bid.get("bidNtceNm", "N/A")
        org = bid.get("ntceInsttNm", "N/A")
        budget = bid.get("presmptPrce", "N/A")
        deadline = bid.get("bidClseDt", "N/A")
        reason = bid.get("reason", "")
        watch = bid.get("watch_out", "")
        grade = bid.get("grade", "")
        rec = bid.get("recommendation", "")
        s = bid.get("score", 0)
        watch_html = f'<p style="font-size:12px;color:#c0392b;background:#fff5f5;padding:6px 10px;border-radius:4px;margin:6px 0 0;">{watch}</p>' if watch else ""
        return f"""
        <div style="border-left:4px solid {border_color};background:{bg_color};padding:16px;margin:10px 0;border-radius:6px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;">
            <a href="{url}" target="_blank" style="font-size:14px;font-weight:700;color:#1d3557;text-decoration:none;">{grade}&nbsp;{nm}</a>
            <span style="background:{border_color};color:#fff;padding:2px 9px;border-radius:12px;font-size:11px;font-weight:700;white-space:nowrap;">{s}점 · {rec}</span>
          </div>
          <div style="font-size:12px;color:#666;margin-bottom:8px;">
            기관: <b>{org}</b> &nbsp;|&nbsp; 예산: <b>{budget}원</b> &nbsp;|&nbsp; 마감: <b>{deadline[:10]}</b>
          </div>
          <p style="font-size:12px;color:#333;line-height:1.7;background:#f8f9fa;padding:10px 12px;border-radius:4px;margin:0;">{reason}</p>
          {watch_html}
          <div style="margin-top:8px;">
            <a href="{url}" target="_blank" style="font-size:12px;color:{border_color};border:1px solid {border_color};padding:3px 10px;border-radius:4px;text-decoration:none;">나라장터 공고 원문 보기</a>
          </div>
        </div>"""

    # 각 섹션 생성
    idx = 1
    summary_rows = ""
    for b in top_bids:
        summary_rows += summary_row(b, idx, "background:#f0faf3;")
        idx += 1
    for b in mid_bids:
        summary_rows += summary_row(b, idx, "background:#f0f6fb;")
        idx += 1
    for b in low_bids:
        summary_rows += summary_row(b, idx, "background:#fafafa;color:#888;")
        idx += 1
    for b in alert_bids:
        summary_rows += summary_row(b, idx, "background:#fff3f3;")
        idx += 1

    top_cards = "".join(detail_card(b, "#2d6a4f", "#f0faf3") for b in top_bids)
    mid_cards = "".join(detail_card(b, "#457b9d", "#f0f6fb") for b in mid_bids)
    alert_cards = "".join(detail_card(b, "#e63946", "#fef8f8") for b in alert_bids)

    low_rows = ""
    for b in low_bids:
        url = _url(b)
        nm = b.get("bidNtceNm", "N/A")
        org = b.get("ntceInsttNm", "N/A")
        budget = b.get("presmptPrce", "N/A")
        deadline = b.get("bidClseDt", "N/A")[:10]
        rec = b.get("recommendation", "")
        low_rows += (f'<tr><td style="padding:7px;border-bottom:1px solid #f0f0f0;">'
                     f'<a href="{url}" target="_blank" style="color:#888;text-decoration:none;">{nm}</a></td>'
                     f'<td style="padding:7px;border-bottom:1px solid #f0f0f0;color:#888;">{org}</td>'
                     f'<td style="padding:7px;border-bottom:1px solid #f0f0f0;color:#888;">{budget}원</td>'
                     f'<td style="padding:7px;border-bottom:1px solid #f0f0f0;color:#888;">{deadline}</td>'
                     f'<td style="padding:7px;border-bottom:1px solid #f0f0f0;">{score_badge(b)}</td>'
                     f'<td style="padding:7px;border-bottom:1px solid #f0f0f0;font-size:11px;color:#888;">{rec}</td></tr>')

    low_section = f"""
    <h2 style="font-size:14px;color:#888;margin:20px 0 8px;">보류 / 비추천 공고 ({len(low_bids)}건)</h2>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <tr style="background:#f5f5f5;">
        <th style="padding:7px;text-align:left;">공고명</th><th style="padding:7px;">기관</th>
        <th style="padding:7px;">예산</th><th style="padding:7px;">마감</th>
        <th style="padding:7px;">점수</th><th style="padding:7px;">비고</th>
      </tr>
      {low_rows}
    </table>""" if low_bids else ""

    alert_section = f"""
    <div style="background:#fff3f3;border:1px solid #e63946;border-radius:6px;padding:14px;margin:16px 0;">
      <h2 style="color:#e63946;font-size:14px;margin:0 0 4px;">마감 임박 알림 — D-3 이하 ({len(alert_bids)}건)</h2>
      <p style="font-size:11px;color:#888;margin:0 0 10px;">제안서 준비 불가 — 참고용으로만 확인하세요</p>
      {alert_cards}
    </div>""" if alert_bids else ""

    th_style = "padding:8px;background:#1d3557;color:#fff;text-align:left;font-size:12px;"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>나라장터 마케팅 공고 리포트 {date_str}</title></head>
<body style="font-family:'Noto Sans KR',Arial,sans-serif;max-width:760px;margin:auto;padding:16px;background:#f0f2f5;">
  <div style="background:#1d3557;color:#fff;padding:18px 24px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;font-size:18px;">나라장터 마케팅 공고 일일 리포트</h1>
    <p style="margin:4px 0 0;opacity:0.8;font-size:12px;">{date_str} &nbsp;|&nbsp; 총 {len(bids)}건 &nbsp;|&nbsp; 강력추천 {len(top_bids)}건 &nbsp;|&nbsp; 마감임박 {len(alert_bids)}건</p>
  </div>
  <div style="background:#fff;padding:20px;border-radius:0 0 8px 8px;box-shadow:0 2px 8px rgba(0,0,0,.1);">

    <h2 style="font-size:14px;color:#1d3557;border-bottom:2px solid #1d3557;padding-bottom:6px;margin:0 0 12px;">전체 공고 요약</h2>
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <tr>
          <th style="{th_style}width:28px;">#</th>
          <th style="{th_style}">공고명</th>
          <th style="{th_style}">기관</th>
          <th style="{th_style}">예산</th>
          <th style="{th_style}">마감</th>
          <th style="{th_style}">AI 점수</th>
          <th style="{th_style}">비고</th>
        </tr>
        {summary_rows if summary_rows else '<tr><td colspan="7" style="padding:12px;text-align:center;color:#999;">오늘은 마케팅 관련 공고가 없습니다.</td></tr>'}
      </table>
    </div>

    <hr style="border:none;border-top:1px dashed #ddd;margin:20px 0;">

    {'<h2 style="font-size:14px;color:#2d6a4f;margin:0 0 8px;">강력 추천 공고 (' + str(len(top_bids)) + '건)</h2>' + top_cards if top_bids else ""}
    {'<h2 style="font-size:14px;color:#457b9d;margin:16px 0 8px;">검토 공고 (' + str(len(mid_bids)) + '건)</h2>' + mid_cards if mid_bids else ""}
    {low_section}
    {alert_section}

    <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
    <p style="font-size:11px;color:#999;text-align:center;">나라장터 마케팅 공고 모니터링 시스템 | {date_str}</p>
  </div>
</body></html>"""
