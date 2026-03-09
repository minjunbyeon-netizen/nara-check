"""
나라장터 API 호출 모듈 - 마케팅 관련 용역 입찰공고 수집
"""
import requests
import logging
from datetime import datetime, timedelta
from config import (
    NARAJANGTEO_API_KEY,
    NARAJANGTEO_BASE_URL,
    NARAJANGTEO_SERVICE_ENDPOINT,
    MARKETING_KEYWORDS,
    DEADLINE_ALERT_DAYS,
)

logger = logging.getLogger(__name__)


def fetch_bids_for_date(target_date: datetime) -> list[dict]:
    """지정 날짜의 용역 입찰공고를 나라장터 API에서 가져온다."""
    date_str = target_date.strftime("%Y%m%d")
    start_dt = date_str + "0000"
    end_dt = date_str + "2359"

    url = NARAJANGTEO_BASE_URL + NARAJANGTEO_SERVICE_ENDPOINT
    all_bids = []
    page = 1

    while True:
        params = {
            "serviceKey": NARAJANGTEO_API_KEY,
            "type": "json",
            "inqryDiv": "1",          # 1: 공고일시 기준
            "inqryBgnDt": start_dt,
            "inqryEndDt": end_dt,
            "pageNo": page,
            "numOfRows": 100,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"API 호출 오류 (page {page}): {e}")
            break
        except ValueError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            break

        # 응답 구조 파싱
        try:
            body = data.get("response", {}).get("body", {})
            items = body.get("items", [])
            if not items:
                break
            # items가 리스트인 경우 (새 API 포맷) vs 딕셔너리인 경우 (구 포맷)
            if isinstance(items, list):
                item_list = items
            elif isinstance(items, dict):
                item_list = items.get("item", [])
                if isinstance(item_list, dict):
                    item_list = [item_list]
            else:
                item_list = []
            if not item_list:
                break
        except (AttributeError, TypeError) as e:
            logger.error(f"응답 구조 파싱 오류: {e}")
            break

        all_bids.extend(item_list)
        total_count = int(body.get("totalCount", 0))
        logger.info(f"  page {page}: {len(item_list)}건 수신 (전체 {total_count}건)")

        if page * 100 >= total_count:
            break
        page += 1

    logger.info(f"총 {len(all_bids)}건 수신 완료")
    return all_bids


def filter_marketing_bids(bids: list[dict]) -> list[dict]:
    """마케팅/광고 관련 키워드로 공고 필터링."""
    keywords_lower = [kw.lower() for kw in MARKETING_KEYWORDS]
    filtered = []

    for bid in bids:
        bid_nm = bid.get("bidNtceNm", "")        # 입찰공고명
        ntce_instt = bid.get("ntceInsttNm", "")  # 공고기관명

        search_text = (bid_nm + " " + ntce_instt).lower()
        matched_keywords = [kw for kw in MARKETING_KEYWORDS if kw.lower() in search_text]

        if matched_keywords:
            bid["_matched_keywords"] = matched_keywords
            bid["_deadline_alert"] = _is_deadline_soon(bid.get("bidClseDt", ""))
            filtered.append(bid)

    logger.info(f"마케팅 관련 공고 필터링: {len(bids)}건 → {len(filtered)}건")
    alert_count = sum(1 for b in filtered if b.get("_deadline_alert"))
    if alert_count:
        logger.info(f"  마감 D-{DEADLINE_ALERT_DAYS} 이내 알림 공고: {alert_count}건")
    return filtered


def _is_deadline_soon(deadline_str: str) -> bool:
    """마감일이 오늘 기준 DEADLINE_ALERT_DAYS일 이내이면 True."""
    if not deadline_str:
        return False
    # 나라장터 API 날짜 포맷 처리:
    #   "202603151800"  → 12자리 숫자 (YYYYMMDDHHMM)
    #   "2026-03-15 18:00:00" → datetime 문자열
    #   "2026-03-15" → 날짜만
    import re
    digits = re.sub(r"\D", "", deadline_str.strip())  # 숫자만 추출
    date_part = digits[:8]  # 앞 8자리 = YYYYMMDD
    try:
        deadline = datetime.strptime(date_part, "%Y%m%d")
        days_left = (deadline.date() - datetime.now().date()).days
        return days_left <= DEADLINE_ALERT_DAYS
    except ValueError:
        return False


def get_today_marketing_bids(days_back: int = None) -> list[dict]:
    if days_back is None:
        try:
            from settings import load as load_settings
            days_back = load_settings().get("collect_days", 7)
        except Exception:
            days_back = 7
    """최근 N일치 마케팅 공고 수집 (기본 7일, 주말 공백 대응)."""
    today = datetime.now()
    start = today - timedelta(days=days_back - 1)

    logger.info(f"공고 수집 시작: {start.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')} ({days_back}일)")

    bids = []
    for i in range(days_back):
        target_date = today - timedelta(days=i)
        daily_bids = fetch_bids_for_date(target_date)
        bids.extend(daily_bids)

    # 중복 제거 (공고번호 기준)
    seen = set()
    unique_bids = []
    for bid in bids:
        bid_no = bid.get("bidNtceNo", "")
        if bid_no not in seen:
            seen.add(bid_no)
            unique_bids.append(bid)

    logger.info(f"중복 제거 후: {len(unique_bids)}건")
    return filter_marketing_bids(unique_bids)


def format_bid_summary(bid: dict) -> str:
    """공고 딕셔너리를 읽기 쉬운 텍스트로 변환."""
    return (
        f"공고번호: {bid.get('bidNtceNo', 'N/A')}\n"
        f"공고명: {bid.get('bidNtceNm', 'N/A')}\n"
        f"발주기관: {bid.get('ntceInsttNm', 'N/A')}\n"
        f"수요기관: {bid.get('dminsttNm', bid.get('ntceInsttNm', 'N/A'))}\n"
        f"공고일시: {bid.get('bidNtceDt', 'N/A')}\n"
        f"입찰마감일시: {bid.get('bidClseDt', 'N/A')}\n"
        f"예산금액: {bid.get('presmptPrce', 'N/A')}원\n"
        f"계약방법: {bid.get('cntrctMthd', 'N/A')}\n"
        f"참가자격: {bid.get('prtcptLmtRgn', 'N/A')}\n"
        f"매칭 키워드: {', '.join(bid.get('_matched_keywords', []))}\n"
        f"나라장터 URL: https://www.g2b.go.kr/pn/pnp/pnpe/bidPbancInfo/getBidPbancDtlInfo.do?bidPbancNo={bid.get('bidNtceNo', '')}&bidPbancOrd={bid.get('bidNtceOrd', '000')}"
    )
