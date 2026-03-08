"""
실데이터 분석 및 dashboard.html 생성 스크립트
"""
import json
import os
import re
from datetime import datetime, timedelta

def score_bid(bid):
    """공고 점수 계산 (100점 만점)"""
    score = 50  # 기본 점수

    raw = bid.get("presmptPrce", 0) or 0
    budget = int(str(raw).replace(",", "")) if raw else 0
    method = bid.get("sucsfbidMthdNm", "")
    keywords = bid.get("_matched_keywords", [])
    close_dt = bid.get("bidClseDt", "")
    nm = bid.get("bidNtceNm", "")

    # 예산 점수 (최대 +25)
    if budget >= 500_000_000:
        score += 25
    elif budget >= 100_000_000:
        score += 20
    elif budget >= 50_000_000:
        score += 15
    elif budget >= 10_000_000:
        score += 5
    else:
        score -= 5

    # 계약방식 점수 (협상 > 일반경쟁 > 제한경쟁)
    if "협상" in method:
        score += 15
    elif "일반경쟁" in method or "일반" in method:
        score += 5

    # 키워드 다양성 (+최대 10)
    score += min(len(keywords) * 2, 10)

    # 고부가가치 키워드
    high_value = ["홍보대행", "마케팅대행", "광고대행", "디지털마케팅", "SNS운영", "콘텐츠제작"]
    for kw in high_value:
        if kw in keywords:
            score += 5
            break

    # 마감 임박 패널티
    if bid.get("_deadline_alert"):
        score -= 10

    return min(max(score, 0), 100)


def grade(score):
    if score >= 80:
        return "A"
    elif score >= 65:
        return "B"
    elif score >= 50:
        return "C"
    else:
        return "D"


def recommend_reason(bid, score):
    """추천 이유 생성"""
    reasons = []
    raw = bid.get("presmptPrce", 0) or 0
    budget = int(str(raw).replace(",", "")) if raw else 0
    method = bid.get("sucsfbidMthdNm", "")
    keywords = bid.get("_matched_keywords", [])

    if budget >= 100_000_000:
        reasons.append(f"예산 {budget//100000000}억원 이상 대형 사업")
    elif budget >= 50_000_000:
        reasons.append(f"예산 {budget//10000}만원 중형 사업")
    elif budget > 0:
        reasons.append(f"예산 {budget//10000}만원 소형 사업")

    if "협상" in method:
        reasons.append("협상에 의한 계약 — 기획력/창의성으로 차별화 가능")

    if keywords:
        reasons.append(f"전문 키워드 매칭: {', '.join(keywords[:3])}")

    if bid.get("_deadline_alert"):
        reasons.append("마감 D-3 이내 — 참여 불가, 모니터링만")

    if score >= 80:
        reasons.append("강력 추천 — 역량에 맞는 최우선 사업")
    elif score >= 65:
        reasons.append("추천 — 적극 검토 권고")
    elif score >= 50:
        reasons.append("검토 — 조건 확인 후 판단")
    else:
        reasons.append("참고 — 낮은 우선순위")

    return reasons


def cautions(bid):
    warns = []
    raw = bid.get("presmptPrce", 0) or 0
    budget = int(str(raw).replace(",", "")) if raw else 0
    method = bid.get("sucsfbidMthdNm", "")
    close_dt = bid.get("bidClseDt", "")

    if budget < 10_000_000 and budget > 0:
        warns.append("예산 1천만원 미만 — 수익성 낮음")
    if bid.get("_deadline_alert"):
        warns.append("마감 D-3 이내 — 입찰 제안 불가")
    if not close_dt:
        warns.append("마감일 미정 — 공고 재확인 필요")
    if "제한" in method:
        warns.append("제한경쟁 — 자격 요건 반드시 확인")

    return warns


def fmt_budget(val):
    try:
        v = int(str(val).replace(",", "")) if val else 0
        if v == 0:
            return "미정"
        if v >= 100_000_000:
            return f"{v/100_000_000:.1f}억원"
        return f"{v//10000:,}만원"
    except:
        return "미정"


def _days_left(close_dt: str) -> int:
    """마감일까지 남은 일수. 미정이면 999."""
    if not close_dt:
        return 999
    digits = re.sub(r"\D", "", close_dt.strip())
    try:
        deadline = datetime.strptime(digits[:8], "%Y%m%d")
        return (deadline.date() - datetime.now().date()).days
    except Exception:
        return 999


def build_html(bids_scored: list[dict], db_total: int = 0, db_latest: str = "") -> str:
    """새 디자인 dashboard.html 생성. JSON 임베드 후 JS 동적 렌더링."""

    # JS에 넘길 데이터 구성
    cards_data = []
    for b in bids_scored:
        bid = b["bid"]
        no  = bid.get("bidNtceNo", "")
        ord_ = bid.get("bidNtceOrd", "000")
        dl  = _days_left(bid.get("bidClseDt", ""))
        cards_data.append({
            "no":       no,
            "ord":      ord_,
            "url":      bid.get("bidNtceDtlUrl") or bid.get("bidNtceUrl") or "",
            "nm":       bid.get("bidNtceNm", ""),
            "instt":    bid.get("ntceInsttNm", ""),
            "budget":   b["bid"].get("_budget_int", 0) or (lambda r: int(str(r).replace(",","")) if r else 0)(bid.get("presmptPrce", 0)),
            "budgetFmt": fmt_budget(bid.get("presmptPrce", "")),
            "ntceDt":   (bid.get("bidNtceDt", "") or "")[:10],
            "closeDt":  (bid.get("bidClseDt", "") or "")[:10],
            "contract": bid.get("cntrctCnclsMthdNm", bid.get("sucsfbidMthdNm", bid.get("bidMethdNm", ""))),
            "keywords": bid.get("_matched_keywords", [])[:6],
            "alert":    bool(bid.get("_deadline_alert")),
            "daysLeft": dl,
            "score":    b["score"],
            "grade":    b["grade"],
            "reasons":  b["reasons"],
            "cautions": b["cautions"],
        })

    data_json = json.dumps(cards_data, ensure_ascii=False)

    now_str    = datetime.now().strftime("%Y.%m.%d %H:%M")
    total_cnt  = len(bids_scored)
    a_cnt      = sum(1 for b in bids_scored if b["grade"] == "A")
    b_cnt      = sum(1 for b in bids_scored if b["grade"] == "B")
    alert_cnt  = sum(1 for b in bids_scored if b["bid"].get("_deadline_alert"))
    db_info    = f"DB 누적 {db_total:,}건" if db_total else ""
    latest_str = db_latest[:16].replace("T", " ") if db_latest else now_str

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>나라장터 마케팅 공고 모니터링</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
  background: #F5F5F7;
  color: #1D1D1F;
  font-size: 15px;
  line-height: 1.5;
}}

/* ── 헤더 ── */
.header {{
  background: #1D1D1F;
  color: #fff;
  position: sticky; top: 0; z-index: 100;
}}
.header-inner {{
  max-width: 1200px; margin: 0 auto;
  padding: 16px 24px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  flex-wrap: wrap;
}}
.header-title {{ font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }}
.header-meta {{ font-size: 12px; color: #86868B; margin-top: 3px; }}

/* 통계 칩 */
.stat-chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.chip {{
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 980px;
  padding: 4px 12px;
  font-size: 12px; color: #E8E8ED;
  white-space: nowrap;
}}
.chip strong {{ color: #fff; font-weight: 700; }}
.chip.accent {{ background: #0071E3; border-color: #0071E3; }}

/* ── 툴바 ── */
.toolbar {{
  background: #fff;
  border-bottom: 1px solid #E8E8E8;
  position: sticky; top: 57px; z-index: 90;
}}
.toolbar-inner {{
  max-width: 1200px; margin: 0 auto;
  padding: 12px 24px;
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}}
.search-wrap {{
  position: relative; flex: 1; min-width: 200px;
}}
.search-wrap input {{
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #E8E8E8;
  border-radius: 8px;
  font-size: 14px; color: #1D1D1F;
  outline: none; transition: border-color 0.15s;
}}
.search-wrap input:focus {{
  border-color: #000;
  box-shadow: 0 0 0 2px rgba(0,0,0,0.08);
}}
.search-icon {{
  position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
  pointer-events: none; display: block;
}}
.filter-select {{
  padding: 8px 12px;
  border: 1px solid #E8E8E8;
  border-radius: 8px;
  font-size: 13px; color: #1D1D1F;
  background: #fff; outline: none; cursor: pointer;
}}
.filter-select:focus {{ border-color: #000; }}

/* 등급 필터 버튼 */
.grade-filters {{ display: flex; gap: 6px; }}
.gf-btn {{
  padding: 6px 14px;
  border: 1px solid #E8E8E8;
  border-radius: 980px;
  font-size: 12px; font-weight: 700;
  background: #fff; cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  color: #1D1D1F;
}}
.gf-btn.active {{ background: #1D1D1F; border-color: #1D1D1F; color: #fff; }}
.gf-btn[data-g="A"].active {{ background: #1A5C2E; border-color: #1A5C2E; }}
.gf-btn[data-g="B"].active {{ background: #0071E3; border-color: #0071E3; }}
.gf-btn[data-g="C"].active {{ background: #9A6700; border-color: #9A6700; }}
.gf-btn[data-g="D"].active {{ background: #FF3B30; border-color: #FF3B30; }}

.result-count {{ font-size: 13px; color: #86868B; white-space: nowrap; margin-left: auto; }}

/* ── 메인 ── */
.main {{
  max-width: 1200px; margin: 0 auto;
  padding: 24px;
}}

/* ── 카드 그리드 ── */
.grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}}
@media (max-width: 960px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 600px) {{
  .grid {{ grid-template-columns: 1fr; }}
  .toolbar-inner {{ gap: 8px; }}
  .grade-filters {{ display: none; }}
}}

/* ── 카드 ── */
.card {{
  background: #fff;
  border: 1px solid #E8E8E8;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex; flex-direction: column;
  overflow: hidden;
  transition: box-shadow 0.15s, transform 0.15s;
  cursor: pointer;
}}
.card:hover {{
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}}

/* 등급 상단 바 */
.card-bar {{ height: 3px; }}
.bar-A {{ background: #34C759; }}
.bar-B {{ background: #0071E3; }}
.bar-C {{ background: #FF9F0A; }}
.bar-D {{ background: #FF3B30; }}
.bar-alert {{ background: #FF3B30; }}

.card-body {{ padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 10px; }}

/* 카드 상단 행 */
.card-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
.grade-badge {{
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 980px;
  font-size: 11px; font-weight: 700; white-space: nowrap; flex-shrink: 0;
}}
.badge-A {{ background: #E8F5E9; color: #1A5C2E; }}
.badge-B {{ background: #E3F2FD; color: #0D47A1; }}
.badge-C {{ background: #FFF8E1; color: #7A4F00; }}
.badge-D {{ background: #FFEBEE; color: #B71C1C; }}

.deadline-badge {{
  display: inline-block;
  padding: 3px 10px; border-radius: 980px;
  font-size: 11px; font-weight: 700; white-space: nowrap; flex-shrink: 0;
}}
.dl-alert {{ background: #FFEBEE; color: #FF3B30; }}
.dl-soon  {{ background: #FFF8E1; color: #9A6700; }}
.dl-ok    {{ background: #F1F8F1; color: #1A5C2E; }}
.dl-na    {{ background: #F5F5F7; color: #86868B; }}

/* 공고명 */
.card-title {{
  font-size: 14px; font-weight: 700; color: #1D1D1F;
  line-height: 1.45; word-break: keep-all;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}}

/* 발주기관 */
.card-org {{ font-size: 12px; color: #86868B; }}

/* 예산 */
.card-budget {{ font-size: 18px; font-weight: 700; color: #1D1D1F; }}
.card-budget-label {{ font-size: 11px; color: #86868B; font-weight: 400; margin-left: 4px; }}

/* 메타 그리드 */
.card-meta {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px;
}}
.meta-row {{ display: flex; flex-direction: column; gap: 1px; }}
.meta-label {{ font-size: 10px; color: #86868B; text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px; }}
.meta-value {{ font-size: 12px; color: #1D1D1F; font-weight: 500; }}

/* 키워드 */
.card-keywords {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.kw {{
  display: inline-block;
  background: #F5F5F7; color: #3A3A3C;
  border-radius: 4px; padding: 2px 7px;
  font-size: 11px; font-weight: 500;
}}

/* 하단 */
.card-footer {{
  border-top: 1px solid #F5F5F7;
  padding-top: 10px;
  display: flex; justify-content: flex-end;
}}
.link-btn {{
  display: inline-block;
  padding: 6px 16px;
  background: #1D1D1F; color: #fff;
  border-radius: 980px;
  font-size: 12px; font-weight: 700;
  text-decoration: none;
  transition: background 0.15s;
}}
.link-btn:hover {{ background: #0071E3; }}

/* 상세 패널 */
.detail-overlay {{
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 200;
  align-items: center; justify-content: center;
}}
.detail-overlay.open {{ display: flex; }}
.detail-panel {{
  background: #fff; border-radius: 16px;
  width: min(680px, 95vw); max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 8px 40px rgba(0,0,0,0.2);
  padding: 28px;
  position: relative;
}}
.detail-close {{
  position: absolute; top: 16px; right: 16px;
  background: #F5F5F7; border: none;
  width: 28px; height: 28px; border-radius: 50%;
  font-size: 16px; cursor: pointer; color: #1D1D1F;
  display: flex; align-items: center; justify-content: center;
}}
.detail-grade {{ font-size: 13px; font-weight: 700; margin-bottom: 6px; }}
.detail-title {{ font-size: 20px; font-weight: 700; color: #1D1D1F; line-height: 1.4; margin-bottom: 4px; }}
.detail-org {{ font-size: 13px; color: #86868B; margin-bottom: 16px; }}
.detail-budget {{ font-size: 28px; font-weight: 700; color: #1D1D1F; margin-bottom: 16px; }}
.detail-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
  margin-bottom: 20px;
}}
.detail-item {{ display: flex; flex-direction: column; gap: 2px; }}
.detail-lbl {{ font-size: 11px; color: #86868B; text-transform: uppercase; font-weight: 600; }}
.detail-val {{ font-size: 14px; color: #1D1D1F; font-weight: 500; }}
.detail-section {{ margin-bottom: 16px; }}
.detail-section h4 {{ font-size: 12px; font-weight: 700; color: #86868B; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 8px; }}
.detail-section ul {{ padding-left: 16px; font-size: 14px; color: #1D1D1F; }}
.detail-section li {{ margin-bottom: 4px; }}
.detail-kw {{ display: flex; flex-wrap: wrap; gap: 5px; }}
.detail-kw .kw {{ font-size: 12px; }}
.detail-alert-bar {{
  background: #FFEBEE; color: #FF3B30;
  border-radius: 8px; padding: 10px 14px;
  font-size: 13px; font-weight: 700; margin-bottom: 16px;
}}
.detail-link {{
  display: block; text-align: center;
  padding: 12px; background: #1D1D1F; color: #fff;
  border-radius: 980px; text-decoration: none;
  font-size: 14px; font-weight: 700; margin-top: 4px;
  transition: background 0.15s;
}}
.detail-link:hover {{ background: #0071E3; }}

/* 빈 결과 */
.empty {{ text-align: center; padding: 64px 24px; color: #86868B; grid-column: 1/-1; }}
.empty p {{ font-size: 14px; margin-top: 8px; }}
</style>
</head>
<body>

<!-- 헤더 -->
<header class="header">
  <div class="header-inner">
    <div>
      <div class="header-title">나라장터 마케팅 공고 모니터링</div>
      <div class="header-meta">마지막 업데이트: {latest_str} &nbsp;|&nbsp; {db_info}</div>
    </div>
    <div class="stat-chips">
      <div class="chip"><strong>{total_cnt}</strong> 이번 수집</div>
      <div class="chip accent"><strong>{a_cnt}</strong> A등급</div>
      <div class="chip"><strong>{b_cnt}</strong> B등급</div>
      <div class="chip" style="color:#FF9F0A;border-color:rgba(255,159,10,0.4)"><strong style="color:#FF9F0A">{alert_cnt}</strong> 마감임박</div>
    </div>
  </div>
</header>

<!-- 툴바 -->
<div class="toolbar">
  <div class="toolbar-inner">
    <div class="search-wrap">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="6" cy="6" r="4.5" stroke="#86868B" stroke-width="1.5"/><path d="M10 10L13 13" stroke="#86868B" stroke-width="1.5" stroke-linecap="round"/></svg>
      <input type="text" id="searchInput" placeholder="공고명, 기관명, 키워드 검색..." oninput="render()">
    </div>
    <select class="filter-select" id="fBudget" onchange="render()">
      <option value="0">전체 예산</option>
      <option value="10000000">1천만원 이상</option>
      <option value="30000000">3천만원 이상</option>
      <option value="50000000">5천만원 이상</option>
      <option value="100000000">1억원 이상</option>
    </select>
    <select class="filter-select" id="fDeadline" onchange="render()">
      <option value="all">전체 마감</option>
      <option value="week">1주 이내</option>
      <option value="month">1개월 이내</option>
      <option value="no_alert">D-3 제외</option>
    </select>
    <select class="filter-select" id="fSort" onchange="render()">
      <option value="score">점수 높은 순</option>
      <option value="budget">예산 높은 순</option>
      <option value="deadline">마감 임박 순</option>
    </select>
    <div class="grade-filters">
      <button class="gf-btn active" data-g="ALL" onclick="toggleGrade(this)">전체</button>
      <button class="gf-btn" data-g="A" onclick="toggleGrade(this)">A</button>
      <button class="gf-btn" data-g="B" onclick="toggleGrade(this)">B</button>
      <button class="gf-btn" data-g="C" onclick="toggleGrade(this)">C</button>
      <button class="gf-btn" data-g="D" onclick="toggleGrade(this)">D</button>
    </div>
    <div class="result-count" id="resultCount"></div>
  </div>
</div>

<!-- 메인 -->
<main class="main">
  <div class="grid" id="grid"></div>
</main>

<!-- 상세 패널 -->
<div class="detail-overlay" id="overlay" onclick="closeDetail(event)">
  <div class="detail-panel" id="detailPanel"></div>
</div>

<script>
const DATA = {data_json};
let activeGrade = "ALL";

function g2bUrl(d) {{
  return d.url || `https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=${{d.no}}&bidPbancOrd=${{d.ord}}`;
}}

function deadlineBadge(d) {{
  if (d.daysLeft <= 0)  return `<span class="deadline-badge dl-alert">마감됨</span>`;
  if (d.daysLeft <= 3)  return `<span class="deadline-badge dl-alert">D-${{d.daysLeft}} 임박</span>`;
  if (d.daysLeft <= 7)  return `<span class="deadline-badge dl-soon">D-${{d.daysLeft}}</span>`;
  if (d.daysLeft === 999) return `<span class="deadline-badge dl-na">마감 미정</span>`;
  return `<span class="deadline-badge dl-ok">D-${{d.daysLeft}}</span>`;
}}

function toggleGrade(btn) {{
  document.querySelectorAll('.gf-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeGrade = btn.dataset.g;
  render();
}}

function getFiltered() {{
  const q = document.getElementById('searchInput').value.toLowerCase();
  const minB = parseInt(document.getElementById('fBudget').value) || 0;
  const dl = document.getElementById('fDeadline').value;
  const sort = document.getElementById('fSort').value;

  let list = DATA.filter(d => {{
    if (activeGrade !== "ALL" && d.grade !== activeGrade) return false;
    if (minB > 0 && d.budget < minB) return false;
    if (dl === 'week' && (d.daysLeft > 7 || d.daysLeft < 0)) return false;
    if (dl === 'month' && (d.daysLeft > 30 || d.daysLeft < 0)) return false;
    if (dl === 'no_alert' && d.alert) return false;
    if (q && !d.nm.toLowerCase().includes(q) && !d.instt.toLowerCase().includes(q) &&
        !d.keywords.some(k => k.toLowerCase().includes(q))) return false;
    return true;
  }});

  if (sort === 'score')    list.sort((a, b) => b.score - a.score);
  else if (sort === 'budget')   list.sort((a, b) => b.budget - a.budget);
  else if (sort === 'deadline') list.sort((a, b) => a.daysLeft - b.daysLeft);
  return list;
}}

function makeCard(d) {{
  const url = g2bUrl(d);
  const barCls = d.alert ? 'bar-alert' : `bar-${{d.grade}}`;
  const bdgCls = `badge-${{d.grade}}`;
  const kwHtml = d.keywords.map(k => `<span class="kw">${{k}}</span>`).join('');
  const titleId = `card-${{d.no}}`;

  return `
  <div class="card" onclick="openDetail('${{d.no}}')">
    <div class="card-bar ${{barCls}}"></div>
    <div class="card-body">
      <div class="card-top">
        <span class="grade-badge ${{bdgCls}}">${{d.grade}} ${{d.score}}점</span>
        ${{deadlineBadge(d)}}
      </div>
      <div class="card-title">${{d.nm}}</div>
      <div class="card-org">${{d.instt}}</div>
      <div>
        <span class="card-budget">${{d.budgetFmt}}</span>
      </div>
      <div class="card-meta">
        <div class="meta-row">
          <span class="meta-label">공고일</span>
          <span class="meta-value">${{d.ntceDt || "미정"}}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">마감일</span>
          <span class="meta-value">${{d.closeDt || "미정"}}</span>
        </div>
        <div class="meta-row" style="grid-column:1/-1">
          <span class="meta-label">계약방법</span>
          <span class="meta-value">${{d.contract || "미정"}}</span>
        </div>
      </div>
      <div class="card-keywords">${{kwHtml}}</div>
      <div class="card-footer">
        <a class="link-btn" href="${{url}}" target="_blank" rel="noopener" onclick="event.stopPropagation()">원문 보기</a>
      </div>
    </div>
  </div>`;
}}

function openDetail(no) {{
  const d = DATA.find(x => x.no === no);
  if (!d) return;
  const url = g2bUrl(d);
  const kwHtml = d.keywords.map(k => `<span class="kw">${{k}}</span>`).join('');
  const reasonsHtml = d.reasons.length ? d.reasons.map(r => `<li>${{r}}</li>`).join('') : '<li>해당 없음</li>';
  const cautionsHtml = d.cautions.length ? d.cautions.map(c => `<li>${{c}}</li>`).join('') : '<li>특이사항 없음</li>';
  const alertBar = d.alert ? `<div class="detail-alert-bar">마감 D-${{d.daysLeft}} 이내 — 알림 전용, 입찰 제안 불가</div>` : '';

  document.getElementById('detailPanel').innerHTML = `
    <button class="detail-close" onclick="document.getElementById('overlay').classList.remove('open')">&#10005;</button>
    <div class="detail-grade"><span class="grade-badge badge-${{d.grade}}">${{d.grade}} ${{d.score}}점</span></div>
    <div class="detail-title">${{d.nm}}</div>
    <div class="detail-org">${{d.instt}}</div>
    ${{alertBar}}
    <div class="detail-budget">${{d.budgetFmt}}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="detail-lbl">공고번호</span><span class="detail-val">${{d.no}}</span></div>
      <div class="detail-item"><span class="detail-lbl">계약방법</span><span class="detail-val">${{d.contract || "미정"}}</span></div>
      <div class="detail-item"><span class="detail-lbl">공고일</span><span class="detail-val">${{d.ntceDt || "미정"}}</span></div>
      <div class="detail-item"><span class="detail-lbl">마감일</span><span class="detail-val">${{d.closeDt || "미정"}} (${{deadlineBadge(d)}})</span></div>
    </div>
    <div class="detail-section">
      <h4>매칭 키워드</h4>
      <div class="detail-kw">${{kwHtml}}</div>
    </div>
    <div class="detail-section">
      <h4>추천 이유</h4>
      <ul>${{reasonsHtml}}</ul>
    </div>
    <div class="detail-section">
      <h4>주의사항</h4>
      <ul>${{cautionsHtml}}</ul>
    </div>
    <a class="detail-link" href="${{url}}" target="_blank" rel="noopener">나라장터 원문 보기</a>
  `;
  document.getElementById('overlay').classList.add('open');
}}

function closeDetail(e) {{
  if (e.target === document.getElementById('overlay'))
    document.getElementById('overlay').classList.remove('open');
}}

function render() {{
  const list = getFiltered();
  const grid = document.getElementById('grid');
  document.getElementById('resultCount').textContent = `${{list.length}}건`;

  if (list.length === 0) {{
    grid.innerHTML = `<div class="empty"><strong>결과 없음</strong><p>검색 조건을 변경해 보세요.</p></div>`;
    return;
  }}
  grid.innerHTML = list.map(makeCard).join('');
}}

render();
</script>
</body>
</html>"""


def main():
    # DB 우선, 없으면 JSON 폴백
    try:
        from db import load_all_bids, get_stats
        bids = load_all_bids()
        stats = get_stats()
        db_total  = stats["total"]
        db_latest = stats.get("latest", "")
        print(f"DB에서 {len(bids)}건 로드 (전체 누적 {db_total}건)")
    except Exception as e:
        print(f"DB 로드 실패 ({e}), JSON 폴백")
        with open("reports/live_bids_raw.json", "r", encoding="utf-8") as f:
            bids = json.load(f)
        db_total, db_latest = 0, ""

    # 점수 계산
    bids_scored = []
    for bid in bids:
        sc = score_bid(bid)
        gr = grade(sc)
        bids_scored.append({
            "bid": bid,
            "score": sc,
            "grade": gr,
            "reasons": recommend_reason(bid, sc),
            "cautions": cautions(bid),
        })

    # 마감임박은 하단, 나머지 점수 내림차순
    bids_scored.sort(key=lambda x: (x["bid"].get("_deadline_alert", False), -x["score"]))

    html = build_html(bids_scored, db_total=db_total, db_latest=db_latest)

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"dashboard.html 생성 완료 ({len(bids_scored)}건)")
    for i, b in enumerate(bids_scored[:20]):
        alert = " [마감임박]" if b["bid"].get("_deadline_alert") else ""
        print(f"  {i+1:2d}. {b['grade']}({b['score']:3d}) {b['bid'].get('bidNtceNm','')[:35]}{alert}")
    if len(bids_scored) > 20:
        print(f"  ... 외 {len(bids_scored)-20}건")


if __name__ == "__main__":
    main()
