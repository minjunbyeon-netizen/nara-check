"""
나라장터 공고 SQLite DB 모듈
- 공고번호(bidNtceNo) 기준 중복 없이 누적 저장
- 매 실행마다 새 공고만 추가됨
"""
import sqlite3
import json
import os
from datetime import datetime

# Railway 볼륨: DB_PATH=/data/bids.db  /  로컬 기본: reports/bids.db
DB_PATH = os.environ.get("DB_PATH", os.path.join("reports", "bids.db"))


def _conn():
    os.makedirs("reports", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                bid_no          TEXT PRIMARY KEY,
                bid_ord         TEXT DEFAULT '000',
                bid_nm          TEXT,
                instt_nm        TEXT,
                budget          INTEGER DEFAULT 0,
                ntce_dt         TEXT,
                close_dt        TEXT,
                contract_method TEXT,
                matched_keywords TEXT,
                deadline_alert  INTEGER DEFAULT 0,
                score           INTEGER DEFAULT 0,
                grade           TEXT DEFAULT 'D',
                collected_at    TEXT,
                raw_json        TEXT
            )
        """)
        conn.commit()


def upsert_bids(bids: list[dict]) -> tuple[int, int]:
    """공고 저장. (신규 건수, 중복 건수) 반환."""
    init_db()
    new_count = 0
    dup_count = 0
    with _conn() as conn:
        for bid in bids:
            bid_no = bid.get("bidNtceNo", "")
            if not bid_no:
                continue
            exists = conn.execute(
                "SELECT 1 FROM bids WHERE bid_no = ?", (bid_no,)
            ).fetchone()
            if exists:
                dup_count += 1
                continue

            budget_raw = bid.get("presmptPrce", 0) or 0
            try:
                budget_int = int(str(budget_raw).replace(",", ""))
            except Exception:
                budget_int = 0

            conn.execute("""
                INSERT INTO bids
                    (bid_no, bid_ord, bid_nm, instt_nm, budget, ntce_dt, close_dt,
                     contract_method, matched_keywords, deadline_alert, collected_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bid_no,
                bid.get("bidNtceOrd", "000"),
                bid.get("bidNtceNm", ""),
                bid.get("ntceInsttNm", ""),
                budget_int,
                bid.get("bidNtceDt", ""),
                bid.get("bidClseDt", ""),
                bid.get("cntrctCnclsMthdNm", bid.get("bidMethdNm", "")),
                json.dumps(bid.get("_matched_keywords", []), ensure_ascii=False),
                1 if bid.get("_deadline_alert") else 0,
                datetime.now().isoformat(),
                json.dumps(bid, ensure_ascii=False),
            ))
            new_count += 1
        conn.commit()
    return new_count, dup_count


def load_all_bids(limit: int = 1000) -> list[dict]:
    """DB에서 전체 공고 로드 (수집일 최신순)."""
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT raw_json FROM bids ORDER BY collected_at DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for (raw,) in rows:
        try:
            result.append(json.loads(raw))
        except Exception:
            pass
    return result


def get_stats() -> dict:
    """전체 건수, 오늘 신규 건수 반환."""
    init_db()
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM bids").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM bids WHERE DATE(collected_at) = DATE('now', 'localtime')"
        ).fetchone()[0]
        latest = conn.execute(
            "SELECT MAX(collected_at) FROM bids"
        ).fetchone()[0]
    return {"total": total, "today": today, "latest": latest}
