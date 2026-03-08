"""
나라장터 마케팅 공고 웹 대시보드 생성기
- 기사(카드) 형식 UI
- 클릭 시 나라장터 원문 이동
- 설정 패널: 예산/지역/기관/계약방법/카테고리 드롭다운 필터
- 바탕화면에 HTML 파일 저장
"""
import requests, json, os, time, re
from datetime import datetime, timedelta

# ── 설정 ──────────────────────────────────────────────────────
API_KEY = '30f7a77c16e51f0299460ae4ee97d08023889bdb36e9475a77e786a10e22fcfb'
COLLECT_DAYS = 7

MARKETING_KEYWORDS = [
    'SNS', '소셜미디어', '인스타그램', '페이스북', '유튜브', '틱톡', 'SNS운영',
    '홍보영상', '영상제작', '동영상제작', '영상편집', '숏폼', '릴스',
    '광고물', '인쇄물', '현수막', '배너', '리플렛', '브로슈어', '포스터', '옥외광고물',
    '온라인광고', '디지털마케팅', '검색광고', '배너광고',
    '퍼포먼스마케팅', '디지털광고', '인터넷광고',
    '옥외광고', '전광판', '버스광고', '지하철광고', '교통광고',
    '홍보대행', '마케팅대행', '광고대행', '홍보기획',
    '홍보', '마케팅', '브랜딩', '캠페인', '브랜드', '콘텐츠제작', '홍보콘텐츠',
]

CATEGORY_MAP = {
    'SNS/소셜': ['SNS', '소셜미디어', '인스타그램', '페이스북', '유튜브', '틱톡', 'SNS운영'],
    '영상제작': ['홍보영상', '영상제작', '동영상제작', '영상편집', '숏폼', '릴스'],
    '인쇄/광고물': ['광고물', '인쇄물', '현수막', '배너', '리플렛', '브로슈어', '포스터', '옥외광고물'],
    '디지털광고': ['온라인광고', '디지털마케팅', '검색광고', '배너광고', '퍼포먼스마케팅', '디지털광고', '인터넷광고'],
    '옥외광고': ['옥외광고', '전광판', '버스광고', '지하철광고', '교통광고'],
    '홍보대행': ['홍보대행', '마케팅대행', '광고대행', '홍보기획'],
    '브랜딩/캠페인': ['브랜딩', '캠페인', '브랜드', '콘텐츠제작', '홍보콘텐츠'],
    '일반홍보': ['홍보', '마케팅'],
}

REGION_PATTERNS = {
    '서울': ['서울'],
    '경기/인천': ['경기', '인천', '수원', '성남', '안양', '부천', '의정부', '안산', '고양', '용인'],
    '부산/경남': ['부산', '경남', '창원', '진주', '통영', '거제'],
    '대구/경북': ['대구', '경북', '구미', '포항', '안동'],
    '광주/전남': ['광주', '전남', '목포', '여수', '순천'],
    '대전/충청': ['대전', '충남', '충북', '세종', '천안', '청주'],
    '강원': ['강원', '춘천', '원주', '강릉'],
    '전북': ['전북', '전주', '익산', '군산'],
    '제주': ['제주'],
    '전국/기타': [],
}


def fetch_all_bids():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=COLLECT_DAYS)
    start_str = start_date.strftime('%Y%m%d') + '0000'
    end_str = end_date.strftime('%Y%m%d') + '2359'

    print(f'수집 기간: {start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}')

    all_bids = []
    for page in range(1, 100):
        url = (
            'https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc'
            f'?serviceKey={API_KEY}&type=json&inqryDiv=1'
            f'&inqryBgnDt={start_str}&inqryEndDt={end_str}'
            f'&pageNo={page}&numOfRows=100'
        )
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                break
            data = resp.json()
        except Exception as e:
            print(f'  페이지 {page}: 오류 ({e}), 중단')
            break
        body = data.get('response', {}).get('body', {})
        total = int(body.get('totalCount', 0))
        items = body.get('items', [])
        if not items:
            break
        if isinstance(items, list):
            all_bids.extend(items)
        elif isinstance(items, dict):
            item_list = items.get('item', [])
            if isinstance(item_list, dict):
                item_list = [item_list]
            all_bids.extend(item_list)
        print(f'  페이지 {page}: {len(items)}건 (누적 {len(all_bids)}/{total}건)')
        if len(all_bids) >= total:
            break
        time.sleep(0.3)

    print(f'총 수집: {len(all_bids)}건')
    return all_bids


def classify_category(keywords):
    for cat, kws in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in kws:
                return cat
    return '일반홍보'


def detect_region(instt_nm, bid_nm):
    text = instt_nm + ' ' + bid_nm
    for region, patterns in REGION_PATTERNS.items():
        if region == '전국/기타':
            continue
        for p in patterns:
            if p in text:
                return region
    return '전국/기타'


def deadline_days_left(deadline_str):
    if not deadline_str:
        return 999
    digits = re.sub(r'\D', '', deadline_str.strip())
    date_part = digits[:8]
    try:
        deadline = datetime.strptime(date_part, '%Y%m%d')
        return (deadline.date() - datetime.now().date()).days
    except ValueError:
        return 999


def fmt_budget(val):
    try:
        v = int(str(val).replace(',', '')) if val else 0
        if v == 0:
            return '미정'
        if v >= 100_000_000:
            return f'{v/100_000_000:.1f}억원'
        return f'{v//10000:,}만원'
    except Exception:
        return str(val) if val else '미정'


def filter_and_enrich(all_bids):
    # 중복 제거
    seen = set()
    unique = []
    for bid in all_bids:
        no = bid.get('bidNtceNo', '')
        if no not in seen:
            seen.add(no)
            unique.append(bid)

    filtered = []
    for bid in unique:
        name = bid.get('bidNtceNm', '')
        org = bid.get('ntceInsttNm', '')
        text = name + ' ' + org
        matched = [kw for kw in MARKETING_KEYWORDS if kw in text]
        if not matched:
            continue

        budget_raw = bid.get('presmptPrce', 0) or 0
        try:
            budget_int = int(str(budget_raw).replace(',', ''))
        except Exception:
            budget_int = 0

        days_left = deadline_days_left(bid.get('bidClseDt', ''))
        category = classify_category(matched)
        region = detect_region(org, name)
        contract = bid.get('cntrctCnclsMthdNm', bid.get('bidMethdNm', '기타'))

        bid['_matched_keywords'] = matched
        bid['_deadline_alert'] = days_left <= 3
        bid['_days_left'] = days_left
        bid['_budget_int'] = budget_int
        bid['_budget_fmt'] = fmt_budget(budget_raw)
        bid['_category'] = category
        bid['_region'] = region
        bid['_contract'] = contract
        filtered.append(bid)

    filtered.sort(key=lambda b: (-b['_budget_int'], b['_days_left']))
    print(f'마케팅 필터 후: {len(filtered)}건')
    return filtered


def build_html(bids, generated_at):
    today_str = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
    period_str = f'{(datetime.now()-timedelta(days=COLLECT_DAYS)).strftime("%Y.%m.%d")} ~ {datetime.now().strftime("%Y.%m.%d")}'

    # 필터 옵션 추출
    all_categories = sorted(set(b['_category'] for b in bids))
    all_regions = sorted(set(b['_region'] for b in bids))
    all_contracts = sorted(set(b['_contract'] for b in bids if b['_contract']))

    # 예산 구간 옵션
    budget_opts = [
        ('all', '전체 금액'),
        ('0', '미정/무예산'),
        ('10000000', '1천만원 이상'),
        ('30000000', '3천만원 이상'),
        ('50000000', '5천만원 이상'),
        ('100000000', '1억원 이상'),
        ('300000000', '3억원 이상'),
        ('500000000', '5억원 이상'),
    ]

    # 마감 옵션
    deadline_opts = [
        ('all', '전체'),
        ('exclude_alert', 'D-3 이내 제외'),
        ('alert_only', 'D-3 이내만'),
        ('week', '1주일 이내'),
        ('month', '1개월 이내'),
    ]

    # JSON 데이터 직렬화 (HTML에 임베드)
    bids_json = json.dumps(bids, ensure_ascii=False)

    # 카테고리/지역 드롭다운 옵션 HTML
    def opts_html(items, val_key='_value'):
        return '\n'.join(f'<option value="{v}">{v}</option>' for v in items)

    cat_opts = '\n'.join(f'<option value="{c}">{c}</option>' for c in all_categories)
    region_opts = '\n'.join(f'<option value="{r}">{r}</option>' for r in all_regions)
    contract_opts = '\n'.join(f'<option value="{c}">{c}</option>' for c in all_contracts)
    budget_opts_html = '\n'.join(f'<option value="{v}">{label}</option>' for v, label in budget_opts)
    deadline_opts_html = '\n'.join(f'<option value="{v}">{label}</option>' for v, label in deadline_opts)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>나라장터 마케팅 공고 모니터링</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; background: #f0f2f5; color: #222; }}

/* ── 헤더 ── */
.header {{
  background: linear-gradient(135deg, #1a2740 0%, #2d4a7a 100%);
  color: white; padding: 0;
  position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
}}
.header-inner {{
  max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px;
}}
.header h1 {{ font-size: 18px; font-weight: 700; }}
.header-sub {{ font-size: 12px; color: #a0b4cc; margin-top: 3px; }}
.btn-settings {{
  background: rgba(255,255,255,0.15); color: white;
  border: 1px solid rgba(255,255,255,0.3);
  padding: 8px 16px; border-radius: 6px; cursor: pointer;
  font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;
  transition: background 0.2s;
}}
.btn-settings:hover {{ background: rgba(255,255,255,0.25); }}
.result-count {{
  font-size: 13px; color: #a0b4cc; margin-left: 16px;
}}

/* ── 설정 패널 (슬라이드) ── */
.settings-overlay {{
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 200;
}}
.settings-overlay.open {{ display: block; }}
.settings-panel {{
  position: fixed; top: 0; right: -420px; width: 400px; height: 100vh;
  background: white; z-index: 201; overflow-y: auto;
  box-shadow: -4px 0 20px rgba(0,0,0,0.2);
  transition: right 0.3s ease;
  display: flex; flex-direction: column;
}}
.settings-overlay.open .settings-panel {{ right: 0; }}
.settings-header {{
  background: #1a2740; color: white; padding: 18px 20px;
  display: flex; justify-content: space-between; align-items: center;
  position: sticky; top: 0;
}}
.settings-header h2 {{ font-size: 16px; }}
.btn-close {{
  background: none; border: none; color: white; font-size: 22px; cursor: pointer; line-height: 1;
}}
.settings-body {{ padding: 20px; flex: 1; }}
.filter-group {{ margin-bottom: 20px; }}
.filter-label {{
  display: block; font-size: 12px; font-weight: 700; color: #555;
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}}
.filter-desc {{ font-size: 11px; color: #999; margin-bottom: 6px; }}
select.filter-select {{
  width: 100%; padding: 9px 12px; border: 1px solid #ddd; border-radius: 6px;
  font-size: 14px; color: #333; background: white; cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23666' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 12px center;
  padding-right: 32px;
}}
select.filter-select:focus {{ outline: none; border-color: #2d4a7a; }}
.settings-footer {{
  padding: 16px 20px; border-top: 1px solid #eee;
  display: flex; gap: 10px;
}}
.btn-reset {{
  flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px;
  background: white; cursor: pointer; font-size: 14px; color: #555;
}}
.btn-apply {{
  flex: 2; padding: 10px; border: none; border-radius: 6px;
  background: #1a2740; color: white; cursor: pointer; font-size: 14px; font-weight: 700;
}}
.btn-apply:hover {{ background: #2d4a7a; }}

/* ── 메인 컨텐츠 ── */
.container {{ max-width: 1280px; margin: 0 auto; padding: 20px 16px; }}

/* ── 통계 바 ── */
.stats-bar {{
  display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;
}}
.stat-chip {{
  background: white; border-radius: 20px; padding: 8px 16px;
  font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex; align-items: center; gap: 6px;
}}
.stat-chip .num {{ font-weight: 700; font-size: 15px; color: #1a2740; }}
.stat-chip.highlight {{ background: #1a2740; color: white; }}
.stat-chip.highlight .num {{ color: #7dd3fc; }}

/* ── 카드 그리드 ── */
.cards-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}}

/* ── 기사 카드 ── */
.article-card {{
  background: white; border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  overflow: hidden; transition: transform 0.15s, box-shadow 0.15s;
  display: flex; flex-direction: column;
  cursor: pointer;
  text-decoration: none; color: inherit;
}}
.article-card:hover {{
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.13);
}}
.card-stripe {{ height: 4px; }}
.stripe-a {{ background: linear-gradient(90deg, #16a34a, #4ade80); }}
.stripe-b {{ background: linear-gradient(90deg, #2563eb, #60a5fa); }}
.stripe-c {{ background: linear-gradient(90deg, #d97706, #fbbf24); }}
.stripe-d {{ background: linear-gradient(90deg, #dc2626, #f87171); }}
.stripe-alert {{ background: repeating-linear-gradient(45deg, #dc2626, #dc2626 4px, #fef2f2 4px, #fef2f2 8px); }}

.card-body-inner {{ padding: 16px; flex: 1; display: flex; flex-direction: column; }}

.card-meta-top {{
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 10px; gap: 8px;
}}
.badge-category {{
  font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;
  background: #e0e7ff; color: #3730a3; white-space: nowrap;
}}
.badge-deadline {{
  font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;
  white-space: nowrap;
}}
.badge-deadline.alert {{ background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; }}
.badge-deadline.ok {{ background: #f0fdf4; color: #16a34a; }}
.badge-deadline.soon {{ background: #fffbeb; color: #d97706; }}

.card-title {{
  font-size: 14px; font-weight: 700; color: #1a2740; line-height: 1.5;
  margin-bottom: 10px; word-break: keep-all;
}}

.card-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; margin-bottom: 12px; }}
.info-item {{ display: flex; flex-direction: column; }}
.info-label {{ font-size: 10px; color: #999; font-weight: 600; text-transform: uppercase; }}
.info-value {{ font-size: 13px; color: #333; font-weight: 500; }}
.info-value.budget {{ font-size: 15px; font-weight: 700; color: #1a2740; }}

.card-keywords {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }}
.kw-tag {{
  font-size: 11px; background: #f1f5f9; color: #475569;
  padding: 2px 7px; border-radius: 3px;
}}

.card-footer {{
  border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: auto;
  display: flex; justify-content: space-between; align-items: center;
}}
.link-text {{
  font-size: 12px; color: #2563eb; font-weight: 600;
  display: flex; align-items: center; gap: 4px;
}}
.org-text {{ font-size: 11px; color: #999; }}

/* ── 빈 결과 ── */
.no-results {{
  text-align: center; padding: 60px 20px; color: #999;
  grid-column: 1 / -1;
}}
.no-results .icon {{ font-size: 48px; margin-bottom: 12px; }}

@media (max-width: 640px) {{
  .cards-grid {{ grid-template-columns: 1fr; }}
  .settings-panel {{ width: 100%; right: -100%; }}
  .header-inner {{ flex-wrap: wrap; gap: 10px; }}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div>
      <h1>나라장터 마케팅 공고 모니터링</h1>
      <div class="header-sub">수집 기간: {period_str} &nbsp;|&nbsp; 생성: {today_str}</div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="result-count" id="resultCount"></span>
      <button class="btn-settings" onclick="openSettings()">
        ⚙ 필터 설정
      </button>
    </div>
  </div>
</div>

<!-- 설정 오버레이 -->
<div class="settings-overlay" id="settingsOverlay" onclick="handleOverlayClick(event)">
  <div class="settings-panel">
    <div class="settings-header">
      <h2>⚙ 필터 설정</h2>
      <button class="btn-close" onclick="closeSettings()">✕</button>
    </div>
    <div class="settings-body">

      <div class="filter-group">
        <label class="filter-label">예산 규모</label>
        <div class="filter-desc">선택한 금액 이상의 공고만 표시합니다</div>
        <select class="filter-select" id="f-budget">
          <option value="all">전체 금액</option>
          {budget_opts_html}
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">마감 여유</label>
        <div class="filter-desc">입찰 마감일 기준으로 필터링합니다</div>
        <select class="filter-select" id="f-deadline">
          {deadline_opts_html}
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">공고 카테고리</label>
        <div class="filter-desc">업무 유형으로 필터링합니다</div>
        <select class="filter-select" id="f-category">
          <option value="all">전체 카테고리</option>
          {cat_opts}
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">지역</label>
        <div class="filter-desc">발주기관 소재지 기준입니다</div>
        <select class="filter-select" id="f-region">
          <option value="all">전국 (전체)</option>
          {region_opts}
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">계약 방법</label>
        <div class="filter-desc">협상에 의한 계약은 기획력 경쟁이 유리합니다</div>
        <select class="filter-select" id="f-contract">
          <option value="all">전체 계약방법</option>
          {contract_opts}
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">정렬 기준</label>
        <select class="filter-select" id="f-sort">
          <option value="budget_desc">예산 높은 순</option>
          <option value="budget_asc">예산 낮은 순</option>
          <option value="deadline_asc">마감 임박 순</option>
          <option value="date_desc">공고일 최신 순</option>
        </select>
      </div>

    </div>
    <div class="settings-footer">
      <button class="btn-reset" onclick="resetFilters()">초기화</button>
      <button class="btn-apply" onclick="applyAndClose()">적용하고 닫기</button>
    </div>
  </div>
</div>

<div class="container">
  <div class="stats-bar" id="statsBar"></div>
  <div class="cards-grid" id="cardsGrid"></div>
</div>

<script>
const BIDS = {bids_json};

function g2bUrl(bid) {{
  return `https://www.g2b.go.kr/pn/pnp/pnpe/bidPbancInfo/getBidPbancDtlInfo.do?bidPbancNo=${{bid.bidNtceNo}}&bidPbancOrd=${{bid.bidNtceOrd || '000'}}`;
}}

function deadlineBadge(bid) {{
  const d = bid._days_left;
  if (d <= 0) return `<span class="badge-deadline alert">마감됨</span>`;
  if (d <= 3) return `<span class="badge-deadline alert">D-${{d}} 임박</span>`;
  if (d <= 7) return `<span class="badge-deadline soon">D-${{d}}</span>`;
  if (d === 999) return `<span class="badge-deadline ok">마감 미정</span>`;
  return `<span class="badge-deadline ok">D-${{d}}</span>`;
}}

function stripeClass(bid) {{
  const b = bid._budget_int;
  if (bid._deadline_alert) return 'stripe-alert';
  if (b >= 300_000_000) return 'stripe-a';
  if (b >= 100_000_000) return 'stripe-b';
  if (b >= 30_000_000) return 'stripe-c';
  return 'stripe-d';
}}

function makeCard(bid) {{
  const url = g2bUrl(bid);
  const nm = bid.bidNtceNm || 'N/A';
  const org = bid.ntceInsttNm || 'N/A';
  const ntceDt = (bid.bidNtceDt || '').substring(0, 10);
  const closeDt = (bid.bidClseDt || '').substring(0, 10) || '미정';
  const budget = bid._budget_fmt || '미정';
  const keywords = (bid._matched_keywords || []).slice(0, 5);
  const category = bid._category || '';
  const region = bid._region || '';
  const contract = bid._contract || '기타';
  const kwHtml = keywords.map(k => `<span class="kw-tag">${{k}}</span>`).join('');

  return `
  <a class="article-card" href="${{url}}" target="_blank" rel="noopener">
    <div class="card-stripe ${{stripeClass(bid)}}"></div>
    <div class="card-body-inner">
      <div class="card-meta-top">
        <span class="badge-category">${{category}}</span>
        ${{deadlineBadge(bid)}}
      </div>
      <div class="card-title">${{nm}}</div>
      <div class="card-info">
        <div class="info-item">
          <span class="info-label">예산</span>
          <span class="info-value budget">${{budget}}</span>
        </div>
        <div class="info-item">
          <span class="info-label">계약방법</span>
          <span class="info-value">${{contract}}</span>
        </div>
        <div class="info-item">
          <span class="info-label">공고일</span>
          <span class="info-value">${{ntceDt}}</span>
        </div>
        <div class="info-item">
          <span class="info-label">마감일</span>
          <span class="info-value">${{closeDt}}</span>
        </div>
        <div class="info-item">
          <span class="info-label">지역</span>
          <span class="info-value">${{region}}</span>
        </div>
        <div class="info-item">
          <span class="info-label">공고번호</span>
          <span class="info-value" style="font-size:11px;color:#999;">${{bid.bidNtceNo}}</span>
        </div>
      </div>
      <div class="card-keywords">${{kwHtml}}</div>
      <div class="card-footer">
        <span class="org-text">${{org}}</span>
        <span class="link-text">나라장터 원문 보기 →</span>
      </div>
    </div>
  </a>`;
}}

function getFilters() {{
  return {{
    budget: document.getElementById('f-budget').value,
    deadline: document.getElementById('f-deadline').value,
    category: document.getElementById('f-category').value,
    region: document.getElementById('f-region').value,
    contract: document.getElementById('f-contract').value,
    sort: document.getElementById('f-sort').value,
  }};
}}

function applyFilters() {{
  const f = getFilters();
  let bids = [...BIDS];

  // 예산 필터
  if (f.budget !== 'all') {{
    const minBudget = parseInt(f.budget);
    if (minBudget === 0) {{
      bids = bids.filter(b => b._budget_int === 0);
    }} else {{
      bids = bids.filter(b => b._budget_int >= minBudget);
    }}
  }}

  // 마감 필터
  if (f.deadline === 'exclude_alert') {{
    bids = bids.filter(b => !b._deadline_alert);
  }} else if (f.deadline === 'alert_only') {{
    bids = bids.filter(b => b._deadline_alert);
  }} else if (f.deadline === 'week') {{
    bids = bids.filter(b => b._days_left <= 7 && b._days_left >= 0);
  }} else if (f.deadline === 'month') {{
    bids = bids.filter(b => b._days_left <= 30 && b._days_left >= 0);
  }}

  // 카테고리 필터
  if (f.category !== 'all') {{
    bids = bids.filter(b => b._category === f.category);
  }}

  // 지역 필터
  if (f.region !== 'all') {{
    bids = bids.filter(b => b._region === f.region);
  }}

  // 계약방법 필터
  if (f.contract !== 'all') {{
    bids = bids.filter(b => b._contract === f.contract);
  }}

  // 정렬
  if (f.sort === 'budget_desc') {{
    bids.sort((a, b) => b._budget_int - a._budget_int);
  }} else if (f.sort === 'budget_asc') {{
    bids.sort((a, b) => a._budget_int - b._budget_int);
  }} else if (f.sort === 'deadline_asc') {{
    bids.sort((a, b) => a._days_left - b._days_left);
  }} else if (f.sort === 'date_desc') {{
    bids.sort((a, b) => (b.bidNtceDt || '').localeCompare(a.bidNtceDt || ''));
  }}

  return bids;
}}

function render() {{
  const bids = applyFilters();
  const grid = document.getElementById('cardsGrid');
  const countEl = document.getElementById('resultCount');
  const statsBar = document.getElementById('statsBar');

  countEl.textContent = `${{bids.length}}건 표시 중`;

  // 통계
  const alertCount = bids.filter(b => b._deadline_alert).length;
  const highBudget = bids.filter(b => b._budget_int >= 100_000_000).length;
  const total = BIDS.length;
  statsBar.innerHTML = `
    <div class="stat-chip highlight"><span class="num">${{bids.length}}</span> 표시 공고</div>
    <div class="stat-chip"><span class="num">${{total}}</span> 전체 수집</div>
    <div class="stat-chip"><span class="num">${{highBudget}}</span> 1억+ 공고</div>
    <div class="stat-chip"><span class="num">${{alertCount}}</span> 마감 D-3 이내</div>
  `;

  if (bids.length === 0) {{
    grid.innerHTML = `
      <div class="no-results">
        <div class="icon">🔍</div>
        <div>필터 조건에 맞는 공고가 없습니다.</div>
        <div style="margin-top:8px;font-size:12px;">설정을 변경해 보세요.</div>
      </div>`;
    return;
  }}

  grid.innerHTML = bids.map(makeCard).join('');
}}

function openSettings() {{
  document.getElementById('settingsOverlay').classList.add('open');
}}
function closeSettings() {{
  document.getElementById('settingsOverlay').classList.remove('open');
}}
function handleOverlayClick(e) {{
  if (e.target === document.getElementById('settingsOverlay')) closeSettings();
}}
function applyAndClose() {{
  render();
  closeSettings();
}}
function resetFilters() {{
  document.getElementById('f-budget').value = 'all';
  document.getElementById('f-deadline').value = 'all';
  document.getElementById('f-category').value = 'all';
  document.getElementById('f-region').value = 'all';
  document.getElementById('f-contract').value = 'all';
  document.getElementById('f-sort').value = 'budget_desc';
}}

// 초기 렌더
render();
</script>
</body>
</html>"""


def main():
    print('=== 나라장터 마케팅 공고 웹 대시보드 생성 ===')

    all_bids = fetch_all_bids()
    filtered = filter_and_enrich(all_bids)

    generated_at = datetime.now().isoformat()
    html = build_html(filtered, generated_at)

    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    today_str = datetime.now().strftime('%Y%m%d')

    out_html = os.path.join(desktop, f'나라장터_마케팅대시보드_{today_str}.html')
    out_json = os.path.join(desktop, f'나라장터_마케팅공고_{today_str}.json')

    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': generated_at,
            'period_days': COLLECT_DAYS,
            'total_fetched': len(all_bids),
            'marketing_count': len(filtered),
            'bids': filtered,
        }, f, ensure_ascii=False, indent=2)

    print(f'\n=== 완료 ===')
    print(f'HTML 대시보드: {out_html}')
    print(f'JSON 데이터:   {out_json}')
    print(f'총 {len(filtered)}건 공고 수록')


if __name__ == '__main__':
    main()
