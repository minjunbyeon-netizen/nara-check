"""
실데이터 분석 및 dashboard.html 생성 스크립트
"""
import json
import os
import re
from datetime import datetime, timedelta

def score_bid(bid, cfg=None):
    """공고 점수 계산 (100점 만점). cfg 없으면 settings에서 로드."""
    if cfg is None:
        from settings import load as load_settings
        cfg = load_settings()

    score = cfg.get("base_score", 30)

    raw = bid.get("presmptPrce", 0) or 0
    budget = int(str(raw).replace(",", "")) if raw else 0
    method = bid.get("sucsfbidMthdNm", "")
    keywords = bid.get("_matched_keywords", [])
    category = bid.get("_category", "마케팅")

    # 예산 점수
    for tier in cfg.get("budget_score", []):
        if budget >= tier["min"]:
            score += tier["pts"]
            break

    # 계약방식 점수
    for cs in cfg.get("contract_score", []):
        if cs["keyword"] in method:
            score += cs["pts"]
            break

    # 키워드 다양성
    kw_max = cfg.get("keyword_diversity_max", 8)
    score += min(len(keywords) * 2, kw_max)

    # 고부가가치 키워드 보너스
    high_value = cfg.get("high_value_keywords", [])
    hv_bonus = cfg.get("high_value_bonus", 5)
    if any(kw in keywords for kw in high_value):
        score += hv_bonus

    # 부울경(부산/울산/경남) 기관 가산점
    if bid.get("_is_boulgyeong"):
        score += cfg.get("boulgyeong_bonus", 10)

    # 카테고리별 가산점
    category_bonus_map = cfg.get("category_bonus", {})
    score += category_bonus_map.get(category, 0)

    # 공동수급 가능 가산점
    if bid.get("_joint_bid"):
        score += cfg.get("joint_bid_bonus", 5)

    # 마감 임박 패널티
    if bid.get("_deadline_alert"):
        score += cfg.get("deadline_penalty", -20)

    return min(max(score, 0), 100)


def grade(score, cfg=None):
    if cfg is None:
        from settings import load as load_settings
        cfg = load_settings()
    if score >= cfg.get("grade_s_min", 90):
        return "S"
    elif score >= cfg.get("grade_a_min", 75):
        return "A"
    elif score >= cfg.get("grade_b_min", 60):
        return "B"
    elif score >= cfg.get("grade_c_min", 45):
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
    category = bid.get("_category", "")

    if budget >= 100_000_000:
        reasons.append(f"예산 {budget//100000000}억원 이상 대형 사업")
    elif budget >= 50_000_000:
        reasons.append(f"예산 {budget//10000}만원 중형 사업")
    elif budget > 0:
        label = "소규모 OK" if category in ("홍보영상", "SNS관리") else "소형 사업"
        reasons.append(f"예산 {budget//10000}만원 {label}")

    if bid.get("_is_boulgyeong"):
        reasons.append("부울경(부산/울산/경남) 기관 발주 — 우선 타겟 지역")

    if bid.get("_joint_bid"):
        reasons.append("공동수급 가능 — 파트너사와 컨소시엄 참여 검토")

    if category:
        reasons.append(f"타겟 카테고리: {category}")

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
    category = bid.get("_category", "")

    # 홍보영상/SNS는 소규모 OK — 경고 없음
    if budget < 10_000_000 and budget > 0 and category not in ("홍보영상", "SNS관리"):
        warns.append("예산 1천만원 미만 — 수익성 낮음")
    if bid.get("_deadline_alert"):
        warns.append("마감 D-3 이내 — 입찰 제안 불가")
    if not close_dt:
        warns.append("마감일 미정 — 공고 재확인 필요")
    if "제한" in method:
        warns.append("제한경쟁 — 자격 요건 반드시 확인")
    if category == "행사용역" and not bid.get("_joint_bid"):
        warns.append("행사용역 단독 수행 — 공동수급 가능 여부 원문 확인 필요")

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


_REGION_KEYWORDS = [
    ("부산", "부산"), ("울산", "울산"),
    ("경남", "경남"), ("경상남도", "경남"), ("창원", "경남"), ("진주", "경남"),
    ("김해", "경남"), ("거제", "경남"), ("통영", "경남"), ("양산", "경남"),
    ("서울", "서울"), ("경기", "경기"), ("인천", "인천"),
    ("강원", "강원"), ("충북", "충북"), ("충남", "충남"), ("대전", "대전"),
    ("전북", "전북"), ("전남", "전남"), ("광주", "광주"),
    ("경북", "경북"), ("대구", "대구"), ("제주", "제주"),
    ("세종", "세종"),
]

def _extract_region(instt_nm: str) -> str:
    """기관명에서 지역 키워드 추출. 못 찾으면 빈 문자열."""
    for kw, label in _REGION_KEYWORDS:
        if kw in instt_nm:
            return label
    return ""


def _ensure_classification(bid: dict) -> dict:
    """DB 이전 데이터에 _category/_is_boulgyeong/_joint_bid가 없으면 재분류."""
    if "_category" not in bid or not bid.get("_category"):
        try:
            from fetcher import _classify_category, _is_boulgyeong, _has_joint_bid
            bid_nm   = bid.get("bidNtceNm", "")
            ntce     = bid.get("ntceInsttNm", "")
            dminstt  = bid.get("dminsttNm", "")
            prtcpt   = bid.get("prtcptLmtRgn", "")
            s_text   = (bid_nm + " " + ntce + " " + dminstt).lower()
            r_text   = (prtcpt + " " + ntce + " " + dminstt).lower()
            keywords = bid.get("_matched_keywords", [])
            bid["_category"]     = _classify_category(s_text, keywords)
            bid["_is_boulgyeong"] = _is_boulgyeong(r_text)
            bid["_joint_bid"]    = _has_joint_bid(s_text)
        except Exception:
            bid.setdefault("_category", "마케팅")
            bid.setdefault("_is_boulgyeong", False)
            bid.setdefault("_joint_bid", False)
    return bid


def build_html(bids_scored: list[dict], db_total: int = 0, db_latest: str = "") -> str:
    """미니멀 표 형식 dashboard.html 생성."""

    rows_data = []
    for b in bids_scored:
        bid  = b["bid"]
        no   = bid.get("bidNtceNo", "")
        ord_ = bid.get("bidNtceOrd", "000")
        dl   = _days_left(bid.get("bidClseDt", ""))
        # 지역 표시: 참가지역제한 → 없으면 기관명에서 도/시 추출
        region_raw = bid.get("prtcptLmtRgn", "") or ""
        region_disp = region_raw.strip() if region_raw.strip() else _extract_region(bid.get("ntceInsttNm", ""))
        rows_data.append({
            "no":         no,
            "ord":        ord_,
            "url":        bid.get("bidNtceDtlUrl") or bid.get("bidNtceUrl") or "",
            "nm":         bid.get("bidNtceNm", ""),
            "instt":      bid.get("ntceInsttNm", ""),
            "region":     region_disp,
            "budget":     (lambda r: int(str(r).replace(",","")) if r else 0)(bid.get("presmptPrce", 0)),
            "budgetFmt":  fmt_budget(bid.get("presmptPrce", "")),
            "ntceDt":     (bid.get("bidNtceDt", "") or "")[:10],
            "closeDt":    (bid.get("bidClseDt", "") or "")[:10],
            "contract":   bid.get("cntrctCnclsMthdNm", bid.get("sucsfbidMthdNm", bid.get("bidMethdNm", ""))),
            "keywords":   bid.get("_matched_keywords", [])[:6],
            "alert":      bool(bid.get("_deadline_alert")),
            "daysLeft":   dl,
            "score":      b["score"],
            "grade":      b["grade"],
            "reasons":    b["reasons"],
            "cautions":   b["cautions"],
            "category":   bid.get("_category", ""),
            "boulgyeong": bool(bid.get("_is_boulgyeong")),
            "jointBid":   bool(bid.get("_joint_bid")),
        })

    data_json  = json.dumps(rows_data, ensure_ascii=False)
    now_str    = datetime.now().strftime("%Y.%m.%d %H:%M")
    total_cnt  = len(bids_scored)
    s_cnt      = sum(1 for b in bids_scored if b["grade"] == "S")
    a_cnt      = sum(1 for b in bids_scored if b["grade"] == "A")
    b_cnt      = sum(1 for b in bids_scored if b["grade"] == "B")
    alert_cnt  = sum(1 for b in bids_scored if b["bid"].get("_deadline_alert"))
    bu_cnt     = sum(1 for b in bids_scored if b["bid"].get("_is_boulgyeong"))
    db_info    = f"누적 {db_total:,}건" if db_total else ""
    latest_str = db_latest[:16].replace("T", " ") if db_latest else now_str

    # SVG 파비콘 (나라장터 느낌 - 검색/공고 아이콘)
    favicon_svg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%231D1D1F'/%3E%3Crect x='7' y='9' width='18' height='2.5' rx='1.2' fill='%23fff'/%3E%3Crect x='7' y='14.5' width='14' height='2.5' rx='1.2' fill='%23fff'/%3E%3Crect x='7' y='20' width='10' height='2.5' rx='1.2' fill='%230071E3'/%3E%3C/svg%3E"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>나라장터 모니터링</title>
<link rel="icon" type="image/svg+xml" href="{favicon_svg}">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
  background: #fff;
  color: #1D1D1F;
  font-size: 14px;
  line-height: 1.5;
}}

/* ── 헤더 ── */
.header {{
  background: #1D1D1F;
  color: #fff;
  position: sticky; top: 0; z-index: 100;
  border-bottom: 1px solid #333;
}}
.header-inner {{
  max-width: 1400px; margin: 0 auto;
  padding: 12px 24px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
}}
.header-left {{ display: flex; align-items: center; gap: 20px; }}
.header-title {{ font-size: 15px; font-weight: 700; letter-spacing: -0.2px; white-space: nowrap; }}
.header-meta {{ font-size: 12px; color: #86868B; white-space: nowrap; }}
.stat-chips {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.chip {{
  display: inline-flex; align-items: center; gap: 4px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 11px; color: #ccc;
  white-space: nowrap;
}}
.chip strong {{ color: #fff; font-weight: 700; }}
.chip-a  {{ border-color: rgba(52,199,89,0.4);  color: #34C759; }}
.chip-a strong {{ color: #34C759; }}
.chip-bu {{ border-color: rgba(0,113,227,0.4);  color: #0071E3; }}
.chip-bu strong {{ color: #0071E3; }}
.chip-al {{ border-color: rgba(255,59,48,0.4);  color: #FF6B6B; }}
.chip-al strong {{ color: #FF6B6B; }}

.btn-sync {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  background: #fff; color: #1D1D1F;
  border: none; border-radius: 6px;
  font-size: 12px; font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}}
.btn-sync:hover {{ background: #E8E8ED; }}
.btn-sync:disabled {{ opacity: 0.5; cursor: not-allowed; }}
.btn-sync .spin {{
  width: 12px; height: 12px;
  border: 2px solid #ccc; border-top-color: #333;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: none;
}}
.btn-sync.loading .spin {{ display: block; }}
.btn-sync.loading .sync-lbl {{ display: none; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}

/* ── 툴바 ── */
.toolbar {{
  background: #FAFAFA;
  border-bottom: 1px solid #E8E8E8;
  position: sticky; top: 49px; z-index: 90;
}}
.toolbar-inner {{
  max-width: 1400px; margin: 0 auto;
  padding: 10px 24px;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}}
.search-wrap {{
  position: relative; flex: 1; min-width: 180px; max-width: 320px;
}}
.search-wrap input {{
  width: 100%;
  padding: 7px 10px 7px 32px;
  border: 1px solid #E0E0E0;
  border-radius: 6px;
  font-size: 13px; color: #1D1D1F;
  background: #fff;
  outline: none; transition: border-color 0.15s;
}}
.search-wrap input:focus {{
  border-color: #1D1D1F;
  box-shadow: 0 0 0 2px rgba(0,0,0,0.06);
}}
.search-icon {{
  position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  pointer-events: none;
}}
.sel {{
  padding: 7px 10px;
  border: 1px solid #E0E0E0; border-radius: 6px;
  font-size: 12px; color: #1D1D1F;
  background: #fff; outline: none; cursor: pointer;
  transition: border-color 0.15s;
}}
.sel:focus {{ border-color: #1D1D1F; }}
.grade-btns {{ display: flex; gap: 4px; }}
.gb {{
  padding: 5px 12px;
  border: 1px solid #E0E0E0; border-radius: 4px;
  font-size: 11px; font-weight: 700;
  background: #fff; cursor: pointer; color: #555;
  transition: all 0.12s;
}}
.gb.on {{ background: #1D1D1F; border-color: #1D1D1F; color: #fff; }}
.gb[data-g="S"].on {{ background: #6B21A8; border-color: #6B21A8; }}
.gb[data-g="A"].on {{ background: #1A7A37; border-color: #1A7A37; }}
.gb[data-g="B"].on {{ background: #0071E3; border-color: #0071E3; }}
.gb[data-g="C"].on {{ background: #9A6700; border-color: #9A6700; }}
.gb[data-g="D"].on {{ background: #CC3333; border-color: #CC3333; }}
.result-info {{ font-size: 12px; color: #86868B; margin-left: auto; white-space: nowrap; }}

/* ── 테이블 래퍼 ── */
/* tbl-outer: 수평 스크롤 담당 (overflow-x만) */
.tbl-outer {{
  max-width: 1400px; margin: 0 auto;
  padding: 0 24px 0;
}}
/* tbl-scroll: 수직 스크롤 + thead sticky 담당 */
.tbl-scroll {{
  overflow-x: auto;
  overflow-y: auto;
  height: calc(100vh - var(--tbl-top, 97px));
}}

/* ── 테이블 ── */
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
thead th {{
  padding: 10px 12px;
  text-align: left;
  font-size: 11px; font-weight: 700; color: #86868B;
  text-transform: uppercase; letter-spacing: 0.3px;
  border-bottom: 2px solid #E8E8E8;
  white-space: nowrap;
  background: #fff;
  position: sticky; top: 0; z-index: 10;
}}
tbody tr {{
  border-bottom: 1px solid #F0F0F0;
  cursor: pointer;
  transition: background 0.1s;
}}
tbody tr:hover {{ background: #F8F8F8; }}
tbody tr.expanded {{ background: #F4F8FF; }}
tbody tr.detail-row {{ background: #F4F8FF; cursor: default; }}
tbody tr.detail-row:hover {{ background: #F4F8FF; }}
td {{
  padding: 11px 12px;
  vertical-align: middle;
}}

/* ── 등급 배지 ── */
.grade {{
  display: inline-flex; flex-direction: column; align-items: center;
  min-width: 36px;
}}
.grade-letter {{
  font-size: 13px; font-weight: 800; line-height: 1;
}}
.grade-score {{
  font-size: 10px; color: #86868B; font-weight: 500;
}}
.g-S .grade-letter {{ color: #6B21A8; }}
.g-A .grade-letter {{ color: #1A7A37; }}
.g-B .grade-letter {{ color: #0071E3; }}
.g-C .grade-letter {{ color: #9A6700; }}
.g-D .grade-letter {{ color: #CC3333; }}

/* ── 태그 ── */
.tag {{
  display: inline-block;
  padding: 2px 6px; border-radius: 3px;
  font-size: 10px; font-weight: 600;
  white-space: nowrap;
}}
.tag-cat  {{ background: #F0F0F0; color: #555; }}
.tag-bu   {{ background: #E8F4FD; color: #0071E3; }}
.tag-joint {{ background: #F0FFF4; color: #1A7A37; }}

/* ── 공고명 셀 ── */
.nm-cell {{ min-width: 260px; max-width: 400px; }}
.nm-title {{
  font-weight: 600; color: #1D1D1F;
  font-size: 13px; line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}}
.nm-sub {{ font-size: 11px; color: #86868B; margin-top: 2px; }}

/* ── 마감 셀 ── */
.dl-badge {{
  display: inline-block;
  padding: 2px 7px; border-radius: 3px;
  font-size: 11px; font-weight: 700; white-space: nowrap;
}}
.dl-over  {{ background: #FFE5E5; color: #CC0000; }}
.dl-hot   {{ background: #FFE5E5; color: #FF3B30; }}
.dl-soon  {{ background: #FFF3D6; color: #9A6700; }}
.dl-ok    {{ background: #E8F5EC; color: #1A7A37; }}
.dl-na    {{ background: #F0F0F0; color: #86868B; }}
.dl-date  {{ font-size: 11px; color: #86868B; margin-top: 2px; }}

/* ── 예산 ── */
.budget-cell {{ white-space: nowrap; font-weight: 600; color: #1D1D1F; text-align: right; }}

/* ── 링크 버튼 ── */
.btn-link {{
  display: inline-block;
  padding: 5px 12px;
  background: #1D1D1F; color: #fff;
  border-radius: 4px;
  font-size: 11px; font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.12s;
}}
.btn-link:hover {{ background: #0071E3; }}

/* ── 상세 행 ── */
.detail-inner {{
  padding: 16px 12px 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}}
.detail-block h5 {{
  font-size: 10px; font-weight: 700; color: #86868B;
  text-transform: uppercase; letter-spacing: 0.4px;
  margin-bottom: 6px;
}}
.detail-block ul {{
  list-style: none; padding: 0;
}}
.detail-block li {{
  font-size: 12px; color: #333;
  padding: 3px 0;
  border-bottom: 1px solid #E8E8E8;
  display: flex; align-items: flex-start; gap: 6px;
}}
.detail-block li:last-child {{ border-bottom: none; }}
.detail-block li::before {{ content: "•"; color: #86868B; flex-shrink: 0; }}
.warn li::before {{ content: "!"; color: #FF3B30; font-weight: 700; flex-shrink: 0; }}
.kw-list {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.kw {{
  background: #F0F0F0; color: #555;
  border-radius: 3px; padding: 2px 6px;
  font-size: 11px;
}}
.detail-meta {{ font-size: 12px; color: #555; line-height: 1.8; }}
.detail-meta span {{ color: #86868B; margin-right: 4px; }}

/* ── 빈 결과 ── */
.empty {{
  text-align: center; padding: 60px 24px;
  color: #86868B; font-size: 14px;
}}

/* ── 토스트 ── */
.toast {{
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #1D1D1F; color: #fff;
  padding: 9px 18px; border-radius: 6px;
  font-size: 12px; font-weight: 500;
  opacity: 0; transition: opacity 0.2s;
  pointer-events: none; z-index: 999;
  white-space: nowrap;
}}
.toast.show {{ opacity: 1; }}

/* ── 설정 패널 ── */
.cfg-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.35); z-index: 300;
}}
.cfg-overlay.open {{ display: block; }}
.cfg-panel {{
  position: fixed; top: 0; right: -460px; width: 440px; height: 100vh;
  background: #fff; z-index: 301;
  box-shadow: -2px 0 16px rgba(0,0,0,0.1);
  transition: right 0.18s ease;
  display: flex; flex-direction: column;
}}
.cfg-overlay.open .cfg-panel {{ right: 0; }}
.cfg-head {{
  background: #1D1D1F; color: #fff;
  padding: 14px 20px;
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;
}}
.cfg-head h2 {{ font-size: 14px; font-weight: 700; }}
.cfg-close {{
  background: none; border: none; color: #fff;
  font-size: 16px; cursor: pointer;
  width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 4px; transition: background 0.12s;
}}
.cfg-close:hover {{ background: rgba(255,255,255,0.15); }}
.cfg-body {{ flex: 1; overflow-y: auto; padding: 16px 20px; }}
.cfg-section {{ margin-bottom: 20px; }}
.cfg-stitle {{
  font-size: 10px; font-weight: 700; color: #86868B;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 1px solid #F0F0F0;
}}
.cfg-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid #F5F5F5; gap: 12px;
}}
.cfg-row:last-child {{ border-bottom: none; }}
.cfg-lbl {{ font-size: 12px; color: #1D1D1F; font-weight: 500; }}
.cfg-desc {{ font-size: 11px; color: #86868B; }}
.cfg-sel {{
  padding: 5px 8px; border: 1px solid #E0E0E0; border-radius: 4px;
  font-size: 12px; color: #1D1D1F; background: #fff;
  cursor: pointer; outline: none; min-width: 100px;
}}
.cfg-sel:focus {{ border-color: #1D1D1F; }}
.score-tbl {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 4px; }}
.score-tbl th {{
  text-align: left; padding: 5px 8px;
  background: #F5F5F5; color: #86868B;
  font-size: 10px; font-weight: 700; text-transform: uppercase;
}}
.score-tbl td {{ padding: 6px 8px; border-bottom: 1px solid #F5F5F5; color: #333; }}
.score-tbl tr:last-child td {{ border-bottom: none; }}
.pts-p {{ color: #1A7A37; font-weight: 700; }}
.pts-m {{ color: #CC3333; font-weight: 700; }}
.pts-0 {{ color: #86868B; font-weight: 700; }}
.cfg-foot {{
  padding: 14px 20px; border-top: 1px solid #E8E8E8;
  display: flex; gap: 8px; flex-shrink: 0;
}}
.cfg-btn-r {{
  flex: 1; padding: 9px; border: 1px solid #E0E0E0;
  border-radius: 6px; background: #fff;
  font-size: 12px; color: #333; cursor: pointer;
}}
.cfg-btn-r:hover {{ background: #F5F5F5; }}
.cfg-btn-s {{
  flex: 2; padding: 9px; border: none;
  border-radius: 6px; background: #1D1D1F;
  color: #fff; font-size: 12px; font-weight: 700; cursor: pointer;
}}
.cfg-btn-s:hover {{ background: #0071E3; }}
</style>
</head>
<body>

<!-- 헤더 -->
<header class="header">
  <div class="header-inner">
    <div class="header-left">
      <div>
        <div class="header-title">나라장터 마케팅 모니터링</div>
        <div class="header-meta">{latest_str} &nbsp;·&nbsp; {db_info}</div>
      </div>
      <div class="stat-chips">
        <div class="chip"><strong>{total_cnt}</strong> 건</div>
        <div class="chip" style="border-color:rgba(107,33,168,0.4);color:#9333EA"><strong style="color:#9333EA">{s_cnt}</strong> S등급</div>
        <div class="chip chip-a"><strong>{a_cnt}</strong> A등급</div>
        <div class="chip"><strong>{b_cnt}</strong> B등급</div>
        <div class="chip chip-bu"><strong>{bu_cnt}</strong> 부울경</div>
        <div class="chip chip-al"><strong>{alert_cnt}</strong> 마감임박</div>
      </div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
      <button class="btn-sync" id="syncBtn" onclick="syncData()">
        <svg class="sync-icon" width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M10.5 6A4.5 4.5 0 1 1 6 1.5" stroke="#1D1D1F" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M8.5 1.5H10.5V3.5" stroke="#1D1D1F" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div class="spin"></div>
        <span class="sync-lbl">동기화</span>
      </button>
      <button onclick="openCfg()" style="padding:6px 12px;border:1px solid rgba(255,255,255,0.2);border-radius:6px;background:transparent;color:#ccc;font-size:12px;cursor:pointer;white-space:nowrap;">설정</button>
    </div>
  </div>
</header>

<!-- 툴바 -->
<div class="toolbar">
  <div class="toolbar-inner">
    <div class="search-wrap">
      <svg class="search-icon" width="13" height="13" viewBox="0 0 13 13" fill="none">
        <circle cx="5.5" cy="5.5" r="4" stroke="#999" stroke-width="1.4"/>
        <path d="M9 9L12 12" stroke="#999" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
      <input type="text" id="sInput" placeholder="공고명, 기관명 검색..." oninput="render()">
    </div>
    <select class="sel" id="fCat" onchange="render()">
      <option value="all">전체 유형</option>
      <option value="SNS관리">SNS</option>
      <option value="홍보영상">홍보영상</option>
      <option value="인쇄물">인쇄물</option>
      <option value="행사용역">행사용역</option>
      <option value="마케팅">마케팅</option>
    </select>
    <select class="sel" id="fRegion" onchange="render()">
      <option value="all">전체 지역</option>
      <option value="bu">부울경만</option>
    </select>
    <select class="sel" id="fBudget" onchange="render()">
      <option value="0">전체 예산</option>
      <option value="10000000">1천만 이상</option>
      <option value="50000000">5천만 이상</option>
      <option value="100000000">1억 이상</option>
    </select>
    <select class="sel" id="fDl" onchange="render()">
      <option value="all">전체 마감</option>
      <option value="week">1주 이내</option>
      <option value="month">1개월 이내</option>
      <option value="no_al">임박 제외</option>
    </select>
    <select class="sel" id="fSort" onchange="render()">
      <option value="score">점수순</option>
      <option value="budget">예산순</option>
      <option value="deadline">마감순</option>
    </select>
    <div class="grade-btns">
      <button class="gb on" data-g="ALL" onclick="toggleGrade(this)">전체</button>
      <button class="gb" data-g="S" onclick="toggleGrade(this)">S</button>
      <button class="gb" data-g="A" onclick="toggleGrade(this)">A</button>
      <button class="gb" data-g="B" onclick="toggleGrade(this)">B</button>
      <button class="gb" data-g="C" onclick="toggleGrade(this)">C</button>
      <button class="gb" data-g="D" onclick="toggleGrade(this)">D</button>
    </div>
    <div class="result-info" id="rInfo"></div>
  </div>
</div>

<!-- 테이블 -->
<div class="tbl-outer">
<div class="tbl-scroll" id="tblScroll">
  <table id="tbl">
    <thead>
      <tr>
        <th style="width:54px">등급</th>
        <th style="width:110px">유형</th>
        <th>공고명</th>
        <th style="width:150px">기관</th>
        <th style="width:72px">지역</th>
        <th style="width:88px;text-align:right">예산</th>
        <th style="width:96px">마감</th>
        <th style="width:110px">계약방법</th>
        <th style="width:56px"></th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="empty" id="empty" style="display:none">검색 결과가 없습니다.</div>
</div><!-- tbl-scroll -->
</div><!-- tbl-outer -->

<!-- 토스트 -->
<div class="toast" id="toast"></div>

<!-- 설정 패널 -->
<div class="cfg-overlay" id="cfgOverlay" onclick="closeCfgOut(event)">
  <div class="cfg-panel" id="cfgPanel">
    <div class="cfg-head">
      <h2>설정 및 채점 기준</h2>
      <button class="cfg-close" onclick="closeCfg()">&#10005;</button>
    </div>
    <div class="cfg-body" id="cfgBody">
      <div id="cfgLoading" style="text-align:center;padding:30px;color:#86868B;font-size:13px;">불러오는 중...</div>
      <div id="cfgContent" style="display:none;">
        <div class="cfg-section">
          <div class="cfg-stitle">예산 점수 기준 (기본 30점)</div>
          <table class="score-tbl">
            <thead><tr><th>구간</th><th>점수</th><th>비고</th></tr></thead>
            <tbody>
              <tr><td>5억 이상</td><td><span class="pts-p">+30</span></td><td></td></tr>
              <tr><td>2억 이상</td><td><span class="pts-p">+25</span></td><td></td></tr>
              <tr><td>1억 이상</td><td><span class="pts-p">+20</span></td><td>SNS 기준선</td></tr>
              <tr><td>5천만 이상</td><td><span class="pts-p">+13</span></td><td></td></tr>
              <tr><td>3천만 이상</td><td><span class="pts-p">+8</span></td><td></td></tr>
              <tr><td>1천만 이상</td><td><span class="pts-p">+4</span></td><td></td></tr>
              <tr><td>1천만 미만</td><td><span class="pts-0">0</span></td><td>영상/SNS OK</td></tr>
            </tbody>
          </table>
        </div>
        <div class="cfg-section">
          <div class="cfg-stitle">가산점 항목</div>
          <table class="score-tbl">
            <thead><tr><th>항목</th><th>점수</th></tr></thead>
            <tbody>
              <tr><td>협상에 의한 계약</td><td><span class="pts-p">+15</span></td></tr>
              <tr><td>부울경(부산/울산/경남) 기관</td><td><span class="pts-p">+10</span></td></tr>
              <tr><td>SNS관리 카테고리</td><td><span class="pts-p">+8</span></td></tr>
              <tr><td>홍보영상 카테고리</td><td><span class="pts-p">+8</span></td></tr>
              <tr><td>행사용역 카테고리</td><td><span class="pts-p">+5</span></td></tr>
              <tr><td>공동수급 가능</td><td><span class="pts-p">+5</span></td></tr>
              <tr><td>고부가 키워드 매칭</td><td><span class="pts-p" id="cfgHVPts">+5</span></td></tr>
              <tr><td>키워드 다양성 (최대)</td><td><span class="pts-p">+8</span></td></tr>
              <tr><td>일반/제한경쟁</td><td><span class="pts-p">+3~5</span></td></tr>
              <tr><td>마감 D-3 이내</td><td><span class="pts-m" id="cfgDlPts">-20</span></td></tr>
            </tbody>
          </table>
        </div>
        <div class="cfg-section">
          <div class="cfg-stitle">등급 기준 (S-A-B-C-D)</div>
          <table class="score-tbl">
            <thead><tr><th>등급</th><th>범위</th><th>의미</th></tr></thead>
            <tbody>
              <tr><td style="color:#6B21A8;font-weight:800;">S</td><td id="gSRow">90점 이상</td><td style="color:#86868B;font-size:10px;">최우선 입찰</td></tr>
              <tr><td style="color:#1A7A37;font-weight:700;">A</td><td id="gARow">75~89점</td><td style="color:#86868B;font-size:10px;">강력 추천</td></tr>
              <tr><td style="color:#0071E3;font-weight:700;">B</td><td id="gBRow">60~74점</td><td style="color:#86868B;font-size:10px;">추천</td></tr>
              <tr><td style="color:#9A6700;font-weight:700;">C</td><td id="gCRow">45~59점</td><td style="color:#86868B;font-size:10px;">검토</td></tr>
              <tr><td style="color:#CC3333;font-weight:700;">D</td><td>45점 미만</td><td style="color:#86868B;font-size:10px;">보류</td></tr>
            </tbody>
          </table>
        </div>
        <div class="cfg-section">
          <div class="cfg-stitle">수집 설정</div>
          <div class="cfg-row">
            <div><div class="cfg-lbl">수집 기간</div><div class="cfg-desc">최근 N일치 공고</div></div>
            <select class="cfg-sel" id="cfgCD">
              <option value="3">3일</option><option value="5">5일</option>
              <option value="7">7일</option><option value="14">14일</option><option value="30">30일</option>
            </select>
          </div>
          <div class="cfg-row">
            <div><div class="cfg-lbl">마감 임박 기준</div><div class="cfg-desc">D-N 이내 경고</div></div>
            <select class="cfg-sel" id="cfgDA">
              <option value="1">D-1</option><option value="3">D-3</option>
              <option value="5">D-5</option><option value="7">D-7</option>
            </select>
          </div>
        </div>
        <div class="cfg-section">
          <div class="cfg-stitle">등급 점수 조정</div>
          <div class="cfg-row">
            <div><div class="cfg-lbl">A등급 최소 점수</div></div>
            <select class="cfg-sel" id="cfgGA">
              <option value="70">70</option><option value="75">75</option><option value="80">80</option>
              <option value="85">85</option><option value="90">90</option>
            </select>
          </div>
          <div class="cfg-row">
            <div><div class="cfg-lbl">B등급 최소 점수</div></div>
            <select class="cfg-sel" id="cfgGB">
              <option value="55">55</option><option value="60">60</option><option value="65">65</option>
              <option value="70">70</option>
            </select>
          </div>
          <div class="cfg-row">
            <div><div class="cfg-lbl">C등급 최소 점수</div></div>
            <select class="cfg-sel" id="cfgGC">
              <option value="40">40</option><option value="45">45</option><option value="50">50</option>
              <option value="55">55</option>
            </select>
          </div>
        </div>
        <div class="cfg-section">
          <div class="cfg-stitle">기본 정렬</div>
          <div class="cfg-row">
            <div><div class="cfg-lbl">페이지 로드 시 정렬</div></div>
            <select class="cfg-sel" id="cfgSort">
              <option value="score">점수순</option>
              <option value="budget">예산순</option>
              <option value="deadline">마감순</option>
            </select>
          </div>
        </div>
      </div>
    </div>
    <div class="cfg-foot">
      <button class="cfg-btn-r" onclick="resetCfg()">기본값</button>
      <button class="cfg-btn-s" onclick="saveCfg()">저장 및 적용</button>
    </div>
  </div>
</div>

<script>
const DATA = {data_json};
let activeGrade = "ALL";
let openNo = null;

function g2bUrl(d) {{
  return d.url || `https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=${{d.no}}&bidPbancOrd=${{d.ord}}`;
}}

function dlBadge(d) {{
  if (d.daysLeft <= 0)   return `<div class="dl-badge dl-over">마감됨</div>`;
  if (d.daysLeft <= 3)   return `<div class="dl-badge dl-hot">D-${{d.daysLeft}} 임박</div>`;
  if (d.daysLeft <= 7)   return `<div class="dl-badge dl-soon">D-${{d.daysLeft}}</div>`;
  if (d.daysLeft === 999) return `<div class="dl-badge dl-na">미정</div>`;
  return `<div class="dl-badge dl-ok">D-${{d.daysLeft}}</div>`;
}}

function toggleGrade(btn) {{
  document.querySelectorAll('.gb').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  activeGrade = btn.dataset.g;
  render();
}}

function getFiltered() {{
  const q   = document.getElementById('sInput').value.toLowerCase();
  const cat = document.getElementById('fCat').value;
  const reg = document.getElementById('fRegion').value;
  const minB = parseInt(document.getElementById('fBudget').value) || 0;
  const dl  = document.getElementById('fDl').value;
  const srt = document.getElementById('fSort').value;

  let list = DATA.filter(d => {{
    if (activeGrade !== "ALL" && d.grade !== activeGrade) return false;
    if (cat !== "all" && d.category !== cat) return false;
    if (reg === "bu" && !d.boulgyeong) return false;
    if (minB > 0 && d.budget < minB) return false;
    if (dl === 'week'  && (d.daysLeft > 7  || d.daysLeft < 0)) return false;
    if (dl === 'month' && (d.daysLeft > 30 || d.daysLeft < 0)) return false;
    if (dl === 'no_al' && d.alert) return false;
    if (q && !d.nm.toLowerCase().includes(q) && !d.instt.toLowerCase().includes(q) &&
        !d.keywords.some(k => k.toLowerCase().includes(q))) return false;
    return true;
  }});

  if (srt === 'score')    list.sort((a,b) => b.score - a.score);
  else if (srt === 'budget')   list.sort((a,b) => b.budget - a.budget);
  else if (srt === 'deadline') list.sort((a,b) => a.daysLeft - b.daysLeft);
  return list;
}}

function makeRow(d, isOpen) {{
  const url     = g2bUrl(d);
  const gCls    = `g-${{d.grade}}`;
  const catTag  = d.category ? `<span class="tag tag-cat">${{d.category}}</span>` : '';
  const buTag   = d.boulgyeong ? `<span class="tag tag-bu">부울경</span>` : '';
  const jtTag   = d.jointBid  ? `<span class="tag tag-joint">공동수급</span>` : '';
  const tags    = [catTag, buTag, jtTag].filter(Boolean).join(' ');
  const alertBg = d.alert ? 'style="background:#FFF8F8"' : '';

  // 지역 배지 색상
  const isBu = d.boulgyeong;
  const regionStyle = isBu
    ? 'font-size:11px;font-weight:700;color:#0071E3;'
    : 'font-size:11px;color:#86868B;';

  return `<tr data-no="${{d.no}}" class="${{isOpen ? 'expanded' : ''}}" onclick="toggleRow('${{d.no}}')" ${{alertBg}}>
    <td>
      <div class="grade ${{gCls}}">
        <div class="grade-letter">${{d.grade}}</div>
        <div class="grade-score">${{d.score}}점</div>
      </div>
    </td>
    <td><div style="display:flex;flex-wrap:wrap;gap:3px;">${{tags}}</div></td>
    <td class="nm-cell">
      <div class="nm-title">${{d.nm}}</div>
    </td>
    <td><div style="font-size:12px;color:#444;line-height:1.4;">${{d.instt}}</div></td>
    <td><div style="${{regionStyle}}">${{d.region || '-'}}</div></td>
    <td class="budget-cell">${{d.budgetFmt}}</td>
    <td>
      ${{dlBadge(d)}}
      <div class="dl-date">${{d.closeDt || ''}}</div>
    </td>
    <td style="font-size:11px;color:#555;white-space:nowrap;">${{(d.contract||'-').replace('에 의한 계약','').replace('에의한계약','').trim()}}</td>
    <td><a class="btn-link" href="${{url}}" target="_blank" rel="noopener" onclick="event.stopPropagation()">원문</a></td>
  </tr>`;
}}

function makeDetailRow(d) {{
  const reasonsHtml = d.reasons.length
    ? d.reasons.map(r => `<li>${{r}}</li>`).join('')
    : '<li>해당 없음</li>';
  const cautionsHtml = d.cautions.length
    ? d.cautions.map(c => `<li>${{c}}</li>`).join('')
    : '<li>특이사항 없음</li>';
  const kwHtml = d.keywords.map(k => `<span class="kw">${{k}}</span>`).join('');

  return `<tr class="detail-row" data-detail="${{d.no}}">
    <td colspan="9">
      <div class="detail-inner">
        <div class="detail-block">
          <h5>추천 이유</h5>
          <ul>${{reasonsHtml}}</ul>
        </div>
        <div class="detail-block warn">
          <h5>주의사항</h5>
          <ul>${{cautionsHtml}}</ul>
        </div>
        <div class="detail-block" style="grid-column:1/-1">
          <h5>매칭 키워드</h5>
          <div class="kw-list">${{kwHtml}}</div>
        </div>
      </div>
    </td>
  </tr>`;
}}

function toggleRow(no) {{
  if (openNo === no) {{
    openNo = null;
  }} else {{
    openNo = no;
  }}
  render();
}}

function render() {{
  const list  = getFiltered();
  const tbody = document.getElementById('tbody');
  const empty = document.getElementById('empty');
  document.getElementById('rInfo').textContent = `${{list.length}}건`;

  if (list.length === 0) {{
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }}
  empty.style.display = 'none';

  let html = '';
  list.forEach(d => {{
    const isOpen = d.no === openNo;
    html += makeRow(d, isOpen);
    if (isOpen) html += makeDetailRow(d);
  }});
  tbody.innerHTML = html;
}}

// ── 토스트 ──
function showToast(msg, dur=3000) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), dur);
}}

// ── 동기화 ──
function syncData() {{
  const btn = document.getElementById('syncBtn');
  btn.classList.add('loading');
  btn.disabled = true;
  fetch('/api/refresh', {{method:'POST'}})
    .then(r => r.json())
    .then(data => {{
      if (data.status === 'already_running') {{
        showToast('이미 수집 중입니다.');
        btn.classList.remove('loading'); btn.disabled = false;
        return;
      }}
      showToast('수집 중... 완료 후 자동 새로고침', 90000);
      pollUntilDone();
    }})
    .catch(() => {{
      showToast('서버 연결 오류');
      btn.classList.remove('loading'); btn.disabled = false;
    }});
}}
function pollUntilDone() {{
  const iv = setInterval(() => {{
    fetch('/api/status').then(r => r.json()).then(d => {{
      if (!d.running) {{
        clearInterval(iv);
        showToast('동기화 완료!', 2000);
        setTimeout(() => location.reload(), 1500);
      }}
    }}).catch(() => clearInterval(iv));
  }}, 3000);
}}

// ── 설정 패널 ──
function openCfg() {{
  document.getElementById('cfgOverlay').classList.add('open');
  loadCfg();
}}
function closeCfg() {{ document.getElementById('cfgOverlay').classList.remove('open'); }}
function closeCfgOut(e) {{ if (e.target === document.getElementById('cfgOverlay')) closeCfg(); }}

function loadCfg() {{
  document.getElementById('cfgLoading').style.display = 'block';
  document.getElementById('cfgContent').style.display = 'none';
  fetch('/api/settings').then(r => r.json()).then(cfg => {{
    setSel('cfgCD',  String(cfg.collect_days || 7));
    setSel('cfgDA',  String(cfg.deadline_alert_days || 3));
    setSel('cfgGA',  String(cfg.grade_a_min || 80));
    setSel('cfgGB',  String(cfg.grade_b_min || 65));
    setSel('cfgGC',  String(cfg.grade_c_min || 50));
    setSel('cfgSort', cfg.default_sort || 'score');
    const hp = cfg.high_value_bonus || 5;
    const dp = cfg.deadline_penalty || -10;
    document.getElementById('cfgHVPts').textContent = (hp>=0?'+':'')+hp;
    document.getElementById('cfgDlPts').textContent  = (dp>=0?'+':'')+dp;
    const s = cfg.grade_s_min || 90, a = cfg.grade_a_min || 75, b = cfg.grade_b_min || 60, c = cfg.grade_c_min || 45;
    document.getElementById('gSRow').textContent = s+'점 이상';
    document.getElementById('gARow').textContent = a+'~'+(s-1)+'점';
    document.getElementById('gBRow').textContent = b+'~'+(a-1)+'점';
    document.getElementById('gCRow').textContent = c+'~'+(b-1)+'점';
    document.getElementById('cfgLoading').style.display = 'none';
    document.getElementById('cfgContent').style.display = 'block';
  }}).catch(() => {{
    document.getElementById('cfgLoading').textContent = '불러오기 실패';
  }});
}}
function setSel(id, val) {{
  const el = document.getElementById(id);
  if (!el) return;
  const opt = el.querySelector(`option[value="${{val}}"]`);
  if (opt) el.value = val;
}}
function saveCfg() {{
  const payload = {{
    collect_days:        parseInt(document.getElementById('cfgCD').value),
    deadline_alert_days: parseInt(document.getElementById('cfgDA').value),
    grade_a_min:         parseInt(document.getElementById('cfgGA').value),
    grade_b_min:         parseInt(document.getElementById('cfgGB').value),
    grade_c_min:         parseInt(document.getElementById('cfgGC').value),
    default_sort:        document.getElementById('cfgSort').value,
  }};
  fetch('/api/settings', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(payload)}})
    .then(r => r.json())
    .then(() => {{
      showToast('저장되었습니다. 재생성 중...');
      setTimeout(() => {{ closeCfg(); location.reload(); }}, 2000);
    }})
    .catch(() => showToast('저장 실패'));
}}
function resetCfg() {{
  setSel('cfgCD','7'); setSel('cfgDA','3');
  setSel('cfgGA','80'); setSel('cfgGB','65'); setSel('cfgGC','50');
  setSel('cfgSort','score');
}}

// ── tbl-scroll 높이 동적 계산 (header + toolbar 제외한 나머지 뷰포트) ──
function fixTblHeight() {{
  const header  = document.querySelector('.header');
  const toolbar = document.querySelector('.toolbar');
  const hh = header  ? header.getBoundingClientRect().height  : 0;
  const th = toolbar ? toolbar.getBoundingClientRect().height : 0;
  const offset = Math.round(hh + th);
  document.documentElement.style.setProperty('--tbl-top', offset + 'px');
  const scroll = document.getElementById('tblScroll');
  if (scroll) scroll.style.height = `calc(100vh - ${{offset}}px)`;
}}
window.addEventListener('load',   fixTblHeight);
window.addEventListener('resize', fixTblHeight);

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

    # DB 이전 데이터 재분류 (필드 없는 경우 보완)
    bids = [_ensure_classification(bid) for bid in bids]

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
