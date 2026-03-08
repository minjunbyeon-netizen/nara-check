"""7일치 마케팅 공고 수집 후 바탕화면에 저장"""
import requests, json, os, time
from datetime import datetime, timedelta

api_key = '30f7a77c16e51f0299460ae4ee97d08023889bdb36e9475a77e786a10e22fcfb'

MARKETING_KEYWORDS = [
    'SNS', '소셜미디어', '인스타그램', '페이스북',
    '유튜브', '틱톡', 'SNS운영',
    '홍보영상', '영상제작', '동영상제작', '영상편집', '숏폼', '릴스',
    '광고물', '인쇄물', '현수막', '배너', '리플렛', '브로슈어', '포스터',
    '온라인광고', '디지털마케팅', '검색광고', '퍼포먼스마케팅', '디지털광고',
    '옥외광고', '전광판', '버스광고', '지하철광고', '교통광고',
    '홍보대행', '마케팅대행', '광고대행', '홍보기획',
    '홍보', '마케팅', '브랜딩', '캠페인', '브랜드',
    '콘텐츠제작', '홍보콘텐츠',
]

end_date = datetime.now()
start_date = end_date - timedelta(days=7)
start_str = start_date.strftime('%Y%m%d') + '0000'
end_str = end_date.strftime('%Y%m%d') + '2359'

print(f'수집 기간: {start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}')

all_bids = []
for page in range(1, 51):
    url = (
        'https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc'
        f'?serviceKey={api_key}&type=json&inqryDiv=1'
        f'&inqryBgnDt={start_str}&inqryEndDt={end_str}'
        f'&pageNo={page}&numOfRows=100'
    )
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f'  페이지 {page}: HTTP {resp.status_code}, 중단')
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
    all_bids.extend(items)
    print(f'  페이지 {page}: {len(items)}건 (누적 {len(all_bids)}/{total}건)')
    if len(all_bids) >= total:
        break
    time.sleep(0.3)

print(f'\n총 수집: {len(all_bids)}건')

# 마케팅 필터링
filtered = []
for bid in all_bids:
    name = bid.get('bidNtceNm', '')
    org = bid.get('ntceInsttNm', '')
    text = name + ' ' + org
    matched = [kw for kw in MARKETING_KEYWORDS if kw in text]
    if matched:
        bid['_matched_keywords'] = matched
        filtered.append(bid)

print(f'마케팅 필터 후: {len(filtered)}건')
for b in filtered[:30]:
    print(f'  [{",".join(b["_matched_keywords"][:2])}] {b["bidNtceNm"][:60]}')

# 바탕화면에 저장
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
today_str = datetime.now().strftime('%Y%m%d')

# JSON 저장
out_json = os.path.join(desktop, f'나라장터_마케팅공고_{today_str}.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump({
        'generated_at': datetime.now().isoformat(),
        'period': f'{start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}',
        'total_fetched': len(all_bids),
        'marketing_count': len(filtered),
        'bids': filtered,
    }, f, ensure_ascii=False, indent=2)

# 텍스트 요약 저장
out_txt = os.path.join(desktop, f'나라장터_마케팅공고_{today_str}.txt')
with open(out_txt, 'w', encoding='utf-8') as f:
    f.write('=' * 60 + '\n')
    f.write('나라장터 마케팅 공고 수집 결과\n')
    f.write('=' * 60 + '\n')
    f.write(f'수집기간: {start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}\n')
    f.write(f'전체 수집: {len(all_bids)}건 | 마케팅 공고: {len(filtered)}건\n')
    f.write(f'생성시각: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    f.write('=' * 60 + '\n\n')
    for i, b in enumerate(filtered, 1):
        bid_no = b.get('bidNtceNo', '')
        bid_ord = b.get('bidNtceOrd', '000')
        f.write(f'[{i}] {b.get("bidNtceNm", "N/A")}\n')
        f.write(f'    공고번호: {bid_no}\n')
        f.write(f'    발주기관: {b.get("ntceInsttNm", "")}\n')
        f.write(f'    예산: {b.get("presmptPrce", "N/A")}원\n')
        f.write(f'    공고일: {b.get("bidNtceDt", "N/A")}\n')
        f.write(f'    마감: {b.get("bidClseDt", "N/A")}\n')
        f.write(f'    키워드: {", ".join(b.get("_matched_keywords", [])[:5])}\n')
        g2b_url = f'https://www.g2b.go.kr/pn/pnp/pnpe/bidPbancInfo/getBidPbancDtlInfo.do?bidPbancNo={bid_no}&bidPbancOrd={bid_ord}'
        f.write(f'    URL: {g2b_url}\n')
        f.write('\n')

print(f'\n=== 저장 완료 ===')
print(f'JSON: {out_json}')
print(f'TXT:  {out_txt}')
