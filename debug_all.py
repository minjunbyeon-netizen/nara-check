"""
전체 모듈 디버깅 스크립트
python debug_all.py 로 실행
"""
import json, os, sys, subprocess, traceback, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from datetime import datetime, timedelta

PASS = "[OK]"
FAIL = "[NG]"
WARN = "[WN]"

results = []

def log(tag, name, msg, detail=""):
    results.append((tag, name, msg, detail))
    icon = {"PASS": "[OK]", "FAIL": "[NG]", "WARN": "[WN]"}.get(tag, "[??]")
    print(f"  {icon} {name}: {msg}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"       {line}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ─────────────────────────────────────────────
# 1. 환경 / 패키지
# ─────────────────────────────────────────────
section("1. 환경 & 패키지")

try:
    import requests
    log("PASS", "requests", f"v{requests.__version__}")
except ImportError as e:
    log("FAIL", "requests", "미설치", str(e))

try:
    import dotenv
    ver = getattr(dotenv, "__version__", "설치됨")
    log("PASS", "python-dotenv", f"v{ver}")
except ImportError as e:
    log("FAIL", "python-dotenv", "미설치", str(e))

py_ver = sys.version.split()[0]
if tuple(int(x) for x in py_ver.split(".")[:2]) >= (3, 10):
    log("PASS", "Python 버전", py_ver)
else:
    log("WARN", "Python 버전", f"{py_ver} (3.10+ 권장)")

# ─────────────────────────────────────────────
# 2. config.py
# ─────────────────────────────────────────────
section("2. config.py")

try:
    from config import (
        NARAJANGTEO_API_KEY, NARAJANGTEO_BASE_URL, NARAJANGTEO_SERVICE_ENDPOINT,
        MARKETING_KEYWORDS, MAX_BIDS_PER_ANALYSIS, REPORTS_DIR, DEADLINE_ALERT_DAYS,
        EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT,
    )
    log("PASS", "config import", "정상")
except Exception as e:
    log("FAIL", "config import", str(e))
    sys.exit(1)

if NARAJANGTEO_API_KEY and len(NARAJANGTEO_API_KEY) > 20:
    log("PASS", "API KEY", f"로드됨 ({NARAJANGTEO_API_KEY[:8]}...)")
else:
    log("FAIL", "API KEY", "비어있거나 너무 짧음")

log("PASS", "BASE_URL", NARAJANGTEO_BASE_URL)
log("PASS", "ENDPOINT", NARAJANGTEO_SERVICE_ENDPOINT)
log("PASS", "KEYWORDS 수", f"{len(MARKETING_KEYWORDS)}개")
log("PASS", "REPORTS_DIR", REPORTS_DIR)
log("PASS", "DEADLINE_ALERT_DAYS", str(DEADLINE_ALERT_DAYS))

if EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECIPIENT:
    log("PASS", "이메일 설정", f"{EMAIL_SENDER} → {EMAIL_RECIPIENT}")
else:
    log("WARN", "이메일 설정", "미설정 (이메일 발송 불가, 파일 저장만 됨)")

# ─────────────────────────────────────────────
# 3. fetcher.py
# ─────────────────────────────────────────────
section("3. fetcher.py — API 연결 & 파싱")

try:
    from fetcher import fetch_bids_for_date, filter_marketing_bids, _is_deadline_soon, get_today_marketing_bids, format_bid_summary
    log("PASS", "fetcher import", "정상")
except Exception as e:
    log("FAIL", "fetcher import", str(e))

# 3-1. API 직접 호출 테스트
import requests as req
yesterday = datetime.now() - timedelta(days=1)
date_str = yesterday.strftime("%Y%m%d")
url = NARAJANGTEO_BASE_URL + NARAJANGTEO_SERVICE_ENDPOINT
params = {
    "serviceKey": NARAJANGTEO_API_KEY,
    "type": "json",
    "inqryDiv": "1",
    "inqryBgnDt": date_str + "0000",
    "inqryEndDt": date_str + "2359",
    "pageNo": 1,
    "numOfRows": 5,
}
try:
    resp = req.get(url, params=params, timeout=15)
    if resp.status_code == 200:
        log("PASS", "API HTTP 상태", f"200 OK")
    elif resp.status_code == 401:
        log("FAIL", "API HTTP 상태", f"401 Unauthorized — API 키 오류")
    else:
        log("WARN", "API HTTP 상태", f"{resp.status_code}")
except Exception as e:
    log("FAIL", "API 연결", str(e))

# 3-2. 응답 파싱 테스트
try:
    data = resp.json()
    body = data.get("response", {}).get("body", {})
    total = body.get("totalCount", 0)
    items = body.get("items", [])

    if isinstance(items, list):
        item_list = items
    elif isinstance(items, dict):
        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
    else:
        item_list = []

    log("PASS", "JSON 파싱", f"totalCount={total}, items={len(item_list)}건")

    # 실제 필드 확인
    if item_list:
        sample = item_list[0]
        required_fields = ["bidNtceNo", "bidNtceDt", "bidNtceNm", "ntceInsttNm", "bidClseDt", "presmptPrce"]
        missing = [f for f in required_fields if f not in sample]
        if missing:
            log("WARN", "응답 필드 누락", f"{missing}")
        else:
            log("PASS", "응답 필드", "필수 필드 모두 존재")

        # presmptPrce 타입 확인
        prc = sample.get("presmptPrce", None)
        log("PASS", "presmptPrce 타입", f"'{prc}' (type={type(prc).__name__})")
except Exception as e:
    log("FAIL", "JSON 파싱", str(e), traceback.format_exc())

# 3-3. _is_deadline_soon 테스트
tests = [
    ("20260309", True, "D-1 마감임박"),
    ("20260315", False, "D-7 여유"),
    ("", False, "빈 문자열"),
    ("2026-03-09 17:00:00", True, "datetime 포맷"),
    ("202603091700", True, "나라장터 포맷"),
]
deadline_pass = True
for dt_str, expected, label in tests:
    got = _is_deadline_soon(dt_str)
    ok = got == expected
    if not ok:
        deadline_pass = False
        log("FAIL", f"_is_deadline_soon({label})", f"기대={expected}, 실제={got}")
if deadline_pass:
    log("PASS", "_is_deadline_soon", f"{len(tests)}개 케이스 모두 정상")

# 3-4. filter_marketing_bids 테스트
fake_bids = [
    {"bidNtceNo": "A1", "bidNtceNm": "2026년 SNS 홍보 용역", "ntceInsttNm": "테스트기관", "bidClseDt": "20260315"},
    {"bidNtceNo": "A2", "bidNtceNm": "도로 포장 공사", "ntceInsttNm": "건설청", "bidClseDt": "20260315"},
    {"bidNtceNo": "A3", "bidNtceNm": "마케팅 컨설팅 용역", "ntceInsttNm": "공공기관", "bidClseDt": "20260315"},
]
try:
    filtered = filter_marketing_bids(fake_bids)
    if len(filtered) == 2:
        log("PASS", "filter_marketing_bids", f"3건 → 2건 (정상 필터링)")
    else:
        log("WARN", "filter_marketing_bids", f"3건 → {len(filtered)}건 (예상: 2건)")
except Exception as e:
    log("FAIL", "filter_marketing_bids", str(e))

# 3-5. format_bid_summary 테스트
try:
    summary = format_bid_summary({"bidNtceNo": "TEST001", "bidNtceNm": "테스트 공고", "ntceInsttNm": "테스트기관",
                                   "presmptPrce": 50000000, "bidClseDt": "2026-03-15 18:00", "_matched_keywords": ["홍보"]})
    if "TEST001" in summary and "테스트 공고" in summary:
        log("PASS", "format_bid_summary", "정상 출력")
    else:
        log("WARN", "format_bid_summary", "출력 이상", summary[:200])
except Exception as e:
    log("FAIL", "format_bid_summary", str(e))

# ─────────────────────────────────────────────
# 4. analyze_bids.py (로컬 스코어링)
# ─────────────────────────────────────────────
section("4. analyze_bids.py — 로컬 점수 계산")

try:
    from analyze_bids import score_bid, grade, recommend_reason, cautions, fmt_budget, build_html
    log("PASS", "analyze_bids import", "정상")
except Exception as e:
    log("FAIL", "analyze_bids import", str(e))

# score_bid 테스트 (presmptPrce 타입 체크 — 실제 API는 int로 옴)
test_bids_score = [
    {"presmptPrce": 500000000, "sucsfbidMthdNm": "협상에 의한 계약", "_matched_keywords": ["홍보", "마케팅"], "bidNtceNm": "대형 홍보용역", "bidClseDt": ""},
    {"presmptPrce": 50000000,  "sucsfbidMthdNm": "일반경쟁", "_matched_keywords": ["SNS"], "bidNtceNm": "소형 SNS용역", "bidClseDt": ""},
    {"presmptPrce": 0,         "sucsfbidMthdNm": "", "_matched_keywords": [], "bidNtceNm": "예산 없는 공고", "bidClseDt": ""},
    # 실제 API 반환 타입: presmptPrce가 None인 경우
    {"presmptPrce": None, "sucsfbidMthdNm": "", "_matched_keywords": [], "bidNtceNm": "None 예산", "bidClseDt": ""},
]

score_fail = False
for tb in test_bids_score:
    try:
        sc = score_bid(tb)
        gr = grade(sc)
        if not (0 <= sc <= 100):
            log("FAIL", "score_bid 범위", f"'{tb['bidNtceNm']}': 점수={sc} (0~100 벗어남)")
            score_fail = True
    except Exception as e:
        log("FAIL", "score_bid", f"'{tb['bidNtceNm']}': {e}")
        score_fail = True
if not score_fail:
    log("PASS", "score_bid", "4개 케이스 모두 정상 (None/0 포함)")

# presmptPrce 콤마 포맷 테스트 (demo_analysis.py의 샘플 데이터: "152,000,000")
try:
    comma_bid = {"presmptPrce": "152,000,000", "sucsfbidMthdNm": "협상에 의한 계약", "_matched_keywords": ["홍보"], "bidNtceNm": "콤마포맷", "bidClseDt": ""}
    sc = score_bid(comma_bid)
    if 0 <= sc <= 100:
        log("PASS", "score_bid 콤마포맷", f"콤마 포함 예산 정상 처리 (점수={sc})")
    else:
        log("FAIL", "score_bid 콤마포맷", f"점수 범위 이상: {sc}")
except (ValueError, TypeError) as e:
    log("FAIL", "score_bid 콤마포맷", f"'{e}' — 콤마 포함 예산 int() 변환 실패")

# fmt_budget 테스트
fmt_tests = [
    (100000000, "1.0억원"),
    (50000000, "5,000만원"),
    (0, "미정"),
    (None, "미정"),
    ("", "미정"),
]
fmt_fail = False
for val, expected in fmt_tests:
    try:
        got = fmt_budget(val)
        if got != expected:
            log("WARN", f"fmt_budget({val})", f"기대='{expected}', 실제='{got}'")
            fmt_fail = True
    except Exception as e:
        log("FAIL", f"fmt_budget({val})", str(e))
        fmt_fail = True
if not fmt_fail:
    log("PASS", "fmt_budget", "모든 케이스 정상")

# build_html 최소 테스트
try:
    sample_scored = [{
        "bid": {"bidNtceNo": "T001", "bidNtceOrd": "000", "bidNtceNm": "테스트공고",
                "ntceInsttNm": "테스트기관", "dminsttNm": "테스트기관",
                "bidNtceDt": "2026-03-08", "bidClseDt": "2026-03-15 18:00",
                "presmptPrce": 50000000, "sucsfbidMthdNm": "협상에 의한 계약",
                "_matched_keywords": ["홍보"], "_deadline_alert": False},
        "score": 70, "grade": "B",
        "reasons": ["예산 5,000만원 중형 사업"], "cautions": []
    }]
    html = build_html(sample_scored)
    if "테스트공고" in html and "<!DOCTYPE html>" in html:
        log("PASS", "build_html", "HTML 생성 정상")
    else:
        log("FAIL", "build_html", "HTML 내용 이상")
except Exception as e:
    log("FAIL", "build_html", str(e), traceback.format_exc())

# analyze_bids.main() — live_bids_raw.json 존재 여부 확인
raw_path = os.path.join(REPORTS_DIR, "live_bids_raw.json")
if os.path.exists(raw_path):
    log("PASS", "live_bids_raw.json", f"존재 ({raw_path})")
else:
    log("WARN", "live_bids_raw.json", f"없음 ({raw_path}) — main.py 실행 전 analyze_bids.main() 단독 실행 시 오류")

# ─────────────────────────────────────────────
# 5. analyzer.py (Claude CLI)
# ─────────────────────────────────────────────
section("5. analyzer.py — Claude CLI 연동")

try:
    from analyzer import analyze_bids, _analyze_batch, _fallback_results
    log("PASS", "analyzer import", "정상")
except Exception as e:
    log("FAIL", "analyzer import", str(e))

# claude CLI 경로 탐색
claude_candidates = [
    "claude",
    r"C:\Users\USER\AppData\Roaming\npm\claude.cmd",
    r"C:\Users\USER\AppData\Roaming\npm\claude",
]
claude_ok = False
for cmd in claude_candidates:
    try:
        r = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10,
                           env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"})
        if r.returncode == 0:
            log("PASS", "claude CLI", f"'{cmd}' → {r.stdout.strip()[:50]}")
            claude_ok = True
            break
    except FileNotFoundError:
        continue
    except Exception as e:
        log("WARN", f"claude '{cmd}'", str(e))
if not claude_ok:
    log("FAIL", "claude CLI", "실행 가능한 claude 명령어 없음 — AI 분석 불가 (fallback 사용됨)")

# analyzer.py에서 사용하는 명령어가 'claude'인지 확인
try:
    import ast
    with open("analyzer.py", "r", encoding="utf-8") as f:
        src = f.read()
    if '["claude"' in src or "['claude'" in src:
        cmd_used = "claude"
    else:
        cmd_used = "알 수 없음"
    log("PASS", "analyzer 사용 명령어", f'"{cmd_used}"')
    if not claude_ok:
        log("WARN", "claude 미발견", "analyze_bids() 호출 시 fallback으로 대체됨 (점수=0, 직접확인)")
except Exception as e:
    log("WARN", "analyzer 소스 확인", str(e))

# _fallback_results 정상 동작 확인
try:
    fake = [{"bidNtceNo": "X1", "bidNtceNm": "테스트"}]
    fb = _fallback_results(fake)
    assert len(fb) == 1
    assert fb[0]["score"] == 0
    assert fb[0]["grade"] == "분석실패"
    log("PASS", "_fallback_results", "정상 동작")
except Exception as e:
    log("FAIL", "_fallback_results", str(e))

# ─────────────────────────────────────────────
# 6. reporter.py
# ─────────────────────────────────────────────
section("6. reporter.py — 리포트 생성")

try:
    from reporter import generate_report, generate_html_report
    log("PASS", "reporter import", "정상")
except Exception as e:
    log("FAIL", "reporter import", str(e))

# 마크다운 리포트 생성 테스트
sample_analyzed = [
    {"bidNtceNo": "T001", "bidNtceOrd": "000", "bidNtceNm": "테스트 SNS 홍보 용역",
     "ntceInsttNm": "테스트기관", "presmptPrce": 50000000,
     "bidClseDt": "2026-03-15 18:00", "bidNtceDt": "2026-03-08",
     "_matched_keywords": ["홍보", "SNS"], "_deadline_alert": False,
     "score": 80, "grade": "★★★★", "recommendation": "강력추천",
     "reason": "테스트 추천 이유", "watch_out": "", "category": "SNS관리"},
    {"bidNtceNo": "T002", "bidNtceOrd": "000", "bidNtceNm": "마감임박 공고",
     "ntceInsttNm": "테스트기관2", "presmptPrce": 10000000,
     "bidClseDt": "2026-03-09 17:00", "bidNtceDt": "2026-03-08",
     "_matched_keywords": ["마케팅"], "_deadline_alert": True,
     "score": 40, "grade": "★★", "recommendation": "보류",
     "reason": "마감 임박", "watch_out": "마감 D-1", "category": "홍보기획"},
]

try:
    md_path = generate_report(sample_analyzed)
    if os.path.exists(md_path):
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        if "테스트 SNS 홍보 용역" in content:
            log("PASS", "generate_report (MD)", f"생성됨: {md_path}")
        else:
            log("WARN", "generate_report (MD)", "파일 생성됐으나 내용 이상")
    else:
        log("FAIL", "generate_report (MD)", "파일 미생성")
except Exception as e:
    log("FAIL", "generate_report (MD)", str(e), traceback.format_exc())

try:
    html_path = generate_html_report(sample_analyzed)
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            hcontent = f.read()
        if "테스트 SNS 홍보 용역" in hcontent and "<!DOCTYPE html>" in hcontent:
            log("PASS", "generate_html_report", f"생성됨: {html_path}")
        else:
            log("WARN", "generate_html_report", "파일 생성됐으나 내용 이상")
    else:
        log("FAIL", "generate_html_report", "파일 미생성")
except Exception as e:
    log("FAIL", "generate_html_report", str(e), traceback.format_exc())

# ZeroDivisionError 체크 (빈 bids일 때 summary 테이블)
try:
    empty_path = generate_report([])
    log("PASS", "generate_report 빈 목록", "오류 없이 처리됨")
except ZeroDivisionError:
    log("FAIL", "generate_report 빈 목록", "ZeroDivisionError — total=0 나눗셈 오류 (reporter.py line 50~52)")
except Exception as e:
    log("FAIL", "generate_report 빈 목록", str(e))

# ─────────────────────────────────────────────
# 7. notifier.py
# ─────────────────────────────────────────────
section("7. notifier.py — 이메일 설정 확인")

try:
    from notifier import send_report_email
    log("PASS", "notifier import", "정상")
except Exception as e:
    log("FAIL", "notifier import", str(e))

if not EMAIL_SENDER:
    log("WARN", "EMAIL_SENDER", "미설정 — 이메일 발송 건너뜀 (정상 동작)")
if not EMAIL_PASSWORD:
    log("WARN", "EMAIL_PASSWORD", "미설정")
if not EMAIL_RECIPIENT:
    log("WARN", "EMAIL_RECIPIENT", "미설정")

if EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECIPIENT:
    import smtplib
    from config import EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT
    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, timeout=10) as s:
            s.starttls()
            log("PASS", "SMTP 연결", f"{EMAIL_SMTP_SERVER}:{EMAIL_SMTP_PORT}")
    except Exception as e:
        log("FAIL", "SMTP 연결", str(e))

# ─────────────────────────────────────────────
# 8. demo_analysis.py 구조 확인
# ─────────────────────────────────────────────
section("8. demo_analysis.py — 구조 검사")

try:
    with open("demo_analysis.py", "r", encoding="utf-8") as f:
        demo_src = f.read()

    # 하드코딩 경로 체크
    hardcoded_path = r"C:\Users\USER\AppData\Roaming\npm\claude.cmd"
    if hardcoded_path in demo_src:
        if os.path.exists(hardcoded_path):
            log("PASS", "claude.cmd 경로", f"하드코딩, 파일 존재")
        else:
            log("FAIL", "claude.cmd 경로", f"하드코딩됐으나 파일 없음: {hardcoded_path}")
    else:
        log("PASS", "claude.cmd 경로", "하드코딩 없음")

    # 콤마 포맷 예산 값 체크
    if '"152,000,000"' in demo_src or '"84,700,000"' in demo_src:
        log("WARN", "샘플 예산 포맷", '"152,000,000" 형식 (콤마 포함) — analyze_bids.score_bid() int() 변환 실패 가능')
    else:
        log("PASS", "샘플 예산 포맷", "콤마 없음")

except Exception as e:
    log("FAIL", "demo_analysis.py 읽기", str(e))

# ─────────────────────────────────────────────
# 9. main.py 구조 확인
# ─────────────────────────────────────────────
section("9. main.py — 구조 검사")

try:
    with open("main.py", "r", encoding="utf-8") as f:
        main_src = f.read()

    # 단계 번호 일관성 체크 (모두 /5 이어야 함)
    import re as _re
    step_nums = _re.findall(r'\[(\d+)/(\d+)\]', main_src)
    totals = set(t for _, t in step_nums)
    if len(totals) == 1:
        log("PASS", "단계 로그 번호", f"모두 /{list(totals)[0]} 로 일관됨 ({len(step_nums)}개)")
    elif len(totals) > 1:
        log("WARN", "단계 로그 번호", f"총 단계수 혼재: {totals}")
    else:
        log("WARN", "단계 로그 번호", "단계 표시 없음")

    # REPORTS_DIR makedirs 확인
    if "makedirs" in main_src:
        log("PASS", "REPORTS_DIR 생성", "makedirs 호출 존재")
    else:
        log("WARN", "REPORTS_DIR 생성", "makedirs 미호출")

except Exception as e:
    log("FAIL", "main.py 읽기", str(e))

# ─────────────────────────────────────────────
# 10. 파일/디렉터리 구조
# ─────────────────────────────────────────────
section("10. 파일 & 디렉터리")

required_files = [
    "main.py", "config.py", "fetcher.py", "analyzer.py",
    "reporter.py", "notifier.py", "analyze_bids.py",
    "demo_analysis.py", "run_daily.bat", "requirements.txt", ".env",
]
for f in required_files:
    if os.path.exists(f):
        log("PASS", f, "존재")
    else:
        log("FAIL", f, "없음")

os.makedirs(REPORTS_DIR, exist_ok=True)
log("PASS", "reports/ 디렉터리", "존재 또는 생성됨")

# ─────────────────────────────────────────────
# 최종 요약
# ─────────────────────────────────────────────
section("최종 요약")
passes  = [r for r in results if r[0] == "PASS"]
warns   = [r for r in results if r[0] == "WARN"]
fails   = [r for r in results if r[0] == "FAIL"]

print(f"  ✓ PASS : {len(passes)}개")
print(f"  ⚠ WARN : {len(warns)}개")
print(f"  ✗ FAIL : {len(fails)}개")

if fails:
    print("\n  [수정 필요]")
    for _, name, msg, _ in fails:
        print(f"    ✗ {name}: {msg}")
if warns:
    print("\n  [주의 사항]")
    for _, name, msg, _ in warns:
        print(f"    ⚠ {name}: {msg}")

print()
