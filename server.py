"""
나라장터 마케팅 공고 모니터링 — 웹 서버
- GET  /           : 대시보드 HTML 서빙
- GET  /api/status : 수집 현황 JSON
- POST /api/refresh: 즉시 수집 트리거 (수동)
- 6시간마다 자동 수집 (APScheduler)

실행: python server.py
배포: Railway / Render (Procfile 참조)
"""
import json
import logging
import os
import threading
from datetime import datetime

from flask import Flask, jsonify, make_response, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler

# ─── 로깅 ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ─── 수집 상태 ──────────────────────────────────────────────
_lock = threading.Lock()
_status = {"running": False, "last_ok": None, "last_count": 0, "error": None}


def run_collection():
    """수집 → DB 저장 → dashboard.html 재생성."""
    if not _lock.acquire(blocking=False):
        logger.info("수집 이미 진행 중 — 스킵")
        return
    _status["running"] = True
    _status["error"] = None
    try:
        logger.info("=== 수집 시작 ===")
        from fetcher import get_today_marketing_bids
        from db import upsert_bids
        from analyze_bids import main as regen

        bids = get_today_marketing_bids()
        logger.info(f"수집: {len(bids)}건")

        os.makedirs("reports", exist_ok=True)
        with open("reports/live_bids_raw.json", "w", encoding="utf-8") as f:
            json.dump(bids, f, ensure_ascii=False, indent=2)

        new_cnt, dup_cnt = upsert_bids(bids)
        logger.info(f"DB: 신규 {new_cnt}건 저장, 중복 {dup_cnt}건 스킵")

        regen()

        _status["last_ok"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _status["last_count"] = len(bids)
        logger.info(f"=== 완료: dashboard.html 갱신 ({len(bids)}건) ===")

    except Exception as e:
        _status["error"] = str(e)
        logger.error(f"수집 오류: {e}", exc_info=True)
    finally:
        _status["running"] = False
        _lock.release()


# ─── 라우트 ──────────────────────────────────────────────────

@app.route("/")
def dashboard():
    html_path = "dashboard.html"
    if not os.path.exists(html_path):
        return (
            "<html><body style='font-family:sans-serif;padding:40px'>"
            "<h2>데이터 준비 중입니다</h2>"
            "<p>첫 수집이 진행 중입니다. 1~2분 후 새로고침하세요.</p>"
            "<script>setTimeout(()=>location.reload(), 30000)</script>"
            "</body></html>",
            503,
        )
    resp = make_response(send_file(html_path))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.route("/api/status")
def status():
    try:
        from db import get_stats
        db = get_stats()
    except Exception:
        db = {}
    return jsonify({
        "running": _status["running"],
        "last_ok": _status["last_ok"],
        "last_count": _status["last_count"],
        "error": _status["error"],
        "db": db,
        "dashboard_exists": os.path.exists("dashboard.html"),
    })


@app.route("/api/settings", methods=["GET"])
def get_settings():
    from settings import load as load_settings
    return jsonify(load_settings())


@app.route("/api/settings", methods=["POST"])
def post_settings():
    from settings import save as save_settings
    from analyze_bids import main as regen
    data = request.get_json(force=True) or {}
    updated = save_settings(data)
    # 설정 변경 후 대시보드 즉시 재생성
    try:
        regen()
    except Exception as e:
        logger.error(f"설정 변경 후 대시보드 재생성 오류: {e}")
    return jsonify({"status": "ok", "settings": updated})


@app.route("/api/refresh", methods=["GET", "POST"])
def refresh():
    if _status["running"]:
        return jsonify({"status": "already_running", "message": "수집이 이미 진행 중입니다."}), 409
    threading.Thread(target=run_collection, daemon=True).start()
    return jsonify({"status": "started", "message": "수집을 시작했습니다. 30초 후 새로고침하세요."})


# ─── 메인 ────────────────────────────────────────────────────

if __name__ == "__main__":
    # 첫 실행 시 dashboard.html 없으면 즉시 수집
    if not os.path.exists("dashboard.html"):
        logger.info("초기 실행: dashboard.html 없음 → 즉시 수집")
        threading.Thread(target=run_collection, daemon=True).start()

    # 매주 화요일/금요일 오전 9시 자동 수집 (한국 시간 기준)
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        run_collection, "cron",
        day_of_week="tue,fri", hour=9, minute=0,
        id="weekly_tue_fri"
    )
    scheduler.start()
    logger.info("스케줄러 시작: 매주 화요일/금요일 09:00 자동 수집")

    port = int(os.environ.get("PORT", 5000))
    logger.info(f"서버 시작: http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
