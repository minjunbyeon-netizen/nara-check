"""
나라장터 마케팅 공고 모니터링 시스템 - 설정 파일
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API 설정 ───────────────────────────────────────────────
NARAJANGTEO_API_KEY = os.getenv("NARAJANGTEO_API_KEY", "30f7a77c16e51f0299460ae4ee97d08023889bdb36e9475a77e786a10e22fcfb")
# Claude 분석은 claude CLI 사용 (별도 API 키 불필요)

NARAJANGTEO_BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
NARAJANGTEO_SERVICE_ENDPOINT = "/getBidPblancListInfoServc"  # 용역 입찰공고 목록

# ─── 이메일 설정 ─────────────────────────────────────────────
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))

# ─── 마케팅 관련 키워드 ──────────────────────────────────────
MARKETING_KEYWORDS = [
    # SNS / 소셜미디어
    "SNS", "소셜미디어", "소셜 미디어", "인스타그램", "페이스북",
    "유튜브", "틱톡", "유튜브채널", "SNS운영", "소셜콘텐츠",
    # 영상 제작
    "홍보영상", "홍보동영상", "영상제작", "동영상제작", "촬영",
    "영상편집", "유튜브영상", "숏폼", "릴스", "영상홍보",
    # 광고물 / 인쇄물
    "광고물", "인쇄물", "현수막", "배너", "리플렛", "브로슈어",
    "포스터", "옥외광고물", "에드버스",
    # 온라인 광고
    "온라인광고", "디지털마케팅", "검색광고", "배너광고",
    "퍼포먼스마케팅", "디지털광고", "인터넷광고",
    # 옥외 광고
    "옥외광고", "전광판", "버스광고", "지하철광고", "광고탑",
    "옥외매체", "교통광고",
    # 홍보대행 / 마케팅
    "홍보대행", "마케팅대행", "광고대행", "홍보기획", "홍보컨설팅",
    "PR", "공공PR", "홍보", "마케팅",
    # 브랜딩 / 캠페인
    "브랜딩", "캠페인", "브랜드", "콘텐츠제작", "콘텐츠 제작",
    "홍보콘텐츠", "크리에이티브",
]

# ─── 분석 관련 ────────────────────────────────────────────────
MAX_BIDS_PER_ANALYSIS = 30      # claude CLI 1회 호출당 최대 공고 수
REPORTS_DIR = "reports"

# ─── 필터 설정 ───────────────────────────────────────────────
# 예산 필터 없음 — 금액 무관하게 전부 수집, 점수로만 구분
DEADLINE_ALERT_DAYS = 3         # 마감 D-3 이하: 입찰 제안 불가, 알림만 표시
