"""
나라장터 마케팅 공고 모니터링 시스템 - 메인 실행 파일
실행: python main.py
"""
import json
import logging
import os
import sys
from datetime import datetime

from fetcher import get_today_marketing_bids
from analyzer import analyze_bids
from reporter import generate_report, generate_html_report
from notifier import send_report_email
from analyze_bids import main as regenerate_dashboard
from db import upsert_bids, get_stats
from config import REPORTS_DIR

# ─── 로깅 설정 ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"나라장터 마케팅 공고 모니터링 시작: {start_time.strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    # 1단계: 공고 수집
    logger.info("[1/5] 나라장터 API에서 마케팅 공고 수집 중...")
    bids = get_today_marketing_bids()

    if not bids:
        logger.info("오늘 수집된 마케팅 관련 공고가 없습니다.")
        bids = []

    logger.info(f"수집 완료: {len(bids)}건")

    # 수집 원본 저장 (JSON 백업)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    raw_path = os.path.join(REPORTS_DIR, "live_bids_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(bids, f, ensure_ascii=False, indent=2)
    logger.info(f"원본 데이터 저장: {raw_path}")

    # DB 누적 저장
    new_cnt, dup_cnt = upsert_bids(bids)
    db_stats = get_stats()
    logger.info(f"DB 저장: 신규 {new_cnt}건 추가, 중복 {dup_cnt}건 스킵 (DB 전체 {db_stats['total']}건)")

    # 2단계: AI 분석
    logger.info(f"[2/5] Claude AI로 {len(bids)}건 공고 분석 중...")
    analyzed_bids = analyze_bids(bids)
    logger.info("AI 분석 완료")

    # 3단계: 리포트 생성
    logger.info("[3/5] 리포트 생성 중...")
    md_path = generate_report(analyzed_bids)
    html_path = generate_html_report(analyzed_bids)
    logger.info(f"리포트 생성 완료: {md_path}, {html_path}")

    # 4단계: dashboard.html 재생성
    logger.info("[4/5] dashboard.html 재생성 중...")
    try:
        regenerate_dashboard()
        logger.info("dashboard.html 업데이트 완료")
    except Exception as e:
        logger.error(f"dashboard.html 재생성 오류: {e}")

    # 5단계: 이메일 발송
    logger.info("[5/5] 이메일 발송 중...")

    sent = send_report_email(html_path, md_path, analyzed_bids)

    # 완료 요약
    elapsed = (datetime.now() - start_time).seconds
    top_count = len([b for b in analyzed_bids if b.get("score", 0) >= 75])

    logger.info("=" * 60)
    logger.info(f"완료! 소요시간: {elapsed}초")
    logger.info(f"수집: {len(bids)}건 | 추천: {top_count}건")
    logger.info(f"리포트: {md_path}")
    logger.info(f"dashboard.html: 업데이트됨")
    logger.info(f"이메일: {'발송 완료' if sent else '미발송 (파일 저장됨)'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
