"""
나라장터 마케팅 공고 모니터링 시스템 - 설정 파일
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API 설정 ───────────────────────────────────────────────
NARAJANGTEO_API_KEY = os.getenv("NARAJANGTEO_API_KEY", "30f7a77c16e51f0299460ae4ee97d08023889bdb36e9475a77e786a10e22fcfb")

NARAJANGTEO_BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
NARAJANGTEO_SERVICE_ENDPOINT = "/getBidPblancListInfoServc"  # 용역 입찰공고 목록

# ─── 이메일 설정 ─────────────────────────────────────────────
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))

# ─── 카테고리별 키워드 ────────────────────────────────────────

# [1] SNS / 소셜미디어 운영
SNS_KEYWORDS = [
    "SNS", "소셜미디어", "소셜 미디어", "인스타그램", "페이스북",
    "유튜브", "틱톡", "유튜브채널", "SNS운영", "소셜콘텐츠",
    "SNS관리", "소셜네트워크", "온라인채널", "디지털채널",
    "SNS광고", "소셜광고",
]

# [2] 홍보영상 / 영상 제작 — 금액 무관, 전부 수집
VIDEO_KEYWORDS = [
    "홍보영상", "홍보동영상", "영상제작", "동영상제작", "촬영",
    "영상편집", "유튜브영상", "숏폼", "릴스", "영상홍보",
    "영상물", "UCC", "홍보물제작", "홍보영상제작", "다큐멘터리",
    "홍보동영상제작", "동영상홍보", "영상콘텐츠",
]

# [3] 홍보물 / 인쇄물
PRINT_KEYWORDS = [
    "인쇄물", "현수막", "배너", "리플렛", "브로슈어",
    "포스터", "광고물", "팸플릿", "옥외광고물",
    "홍보인쇄물", "인쇄", "홍보책자", "홍보자료", "에드버스",
]

# [4] 행사용역 — 공동수급 가능하면 수집
EVENT_KEYWORDS = [
    "행사", "이벤트", "축제", "행사대행", "행사용역", "행사기획",
    "이벤트대행", "행사진행", "행사운영", "축제운영", "문화행사",
    "공연", "전시", "박람회", "설명회", "기념식", "행사연출",
]

# [5] 일반 마케팅/광고 (공통)
GENERAL_MARKETING_KEYWORDS = [
    "홍보대행", "마케팅대행", "광고대행", "홍보기획", "홍보컨설팅",
    "PR", "공공PR", "홍보", "마케팅",
    "온라인광고", "디지털마케팅", "검색광고", "배너광고",
    "퍼포먼스마케팅", "디지털광고", "인터넷광고",
    "옥외광고", "전광판", "버스광고", "지하철광고", "광고탑",
    "옥외매체", "교통광고",
    "브랜딩", "캠페인", "브랜드", "콘텐츠제작", "콘텐츠 제작",
    "홍보콘텐츠", "크리에이티브",
]

# 전체 키워드 (중복 제거) — API 필터링용
MARKETING_KEYWORDS = list(dict.fromkeys(
    SNS_KEYWORDS + VIDEO_KEYWORDS + PRINT_KEYWORDS + EVENT_KEYWORDS + GENERAL_MARKETING_KEYWORDS
))

# 카테고리 매핑 (분류 우선순위 순)
CATEGORY_KEYWORDS = {
    "SNS관리":   SNS_KEYWORDS,
    "홍보영상":  VIDEO_KEYWORDS,
    "인쇄물":    PRINT_KEYWORDS,
    "행사용역":  EVENT_KEYWORDS,
    "마케팅":    GENERAL_MARKETING_KEYWORDS,
}

# ─── 부울경 지역 키워드 (가산점 적용) ────────────────────────
BOULGYEONG_KEYWORDS = [
    "부산", "울산", "경남", "경상남도",
    "창원", "진주", "김해", "거제", "통영", "사천",
    "밀양", "양산", "고성", "남해", "하동", "산청",
    "함양", "거창", "합천", "창녕", "함안", "의령",
]

# 공동수급 키워드 (행사용역에서 감지)
JOINT_BID_KEYWORDS = [
    "공동수급", "공동이행", "분담이행", "공동계약", "컨소시엄",
]

# ─── 분석 관련 ────────────────────────────────────────────────
MAX_BIDS_PER_ANALYSIS = 30      # claude CLI 1회 호출당 최대 공고 수
REPORTS_DIR = "reports"

# ─── 필터 설정 ───────────────────────────────────────────────
DEADLINE_ALERT_DAYS = 3         # 마감 D-3 이하: 입찰 제안 불가, 알림만 표시
