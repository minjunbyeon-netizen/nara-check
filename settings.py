"""
설정 관리 모듈
- 기본값은 DEFAULT에 정의
- 변경된 설정은 SETTINGS_PATH JSON 파일에 저장
- Railway 볼륨: /data/settings.json  /  로컬: reports/settings.json
"""
import json
import os

SETTINGS_PATH = os.environ.get(
    "SETTINGS_PATH",
    os.path.join("reports", "settings.json")
)

DEFAULT = {
    # 수집 설정
    "collect_days": 7,
    "deadline_alert_days": 3,

    # ── 등급 기준 (S-A-B-C-D) ──────────────────────────────────
    # 기본점수 30점 기준으로 각 가산점 합산 후 등급 결정
    # S: 최상위 (부울경+고예산+협상 등 다수 조건 충족)
    # A: 우수   (고예산 or 협상 + 타겟 카테고리)
    # B: 양호   (중간 예산 + 일반 조건)
    # C: 보통   (저예산 or 조건 미흡)
    # D: 낮음   (거의 가산점 없음)
    "grade_s_min": 90,
    "grade_a_min": 75,
    "grade_b_min": 60,
    "grade_c_min": 45,

    # ── 기본 점수 ────────────────────────────────────────────────
    "base_score": 30,    # 50 → 30 (낮춰야 분별력 생김)

    # ── 예산 점수 (세분화) ───────────────────────────────────────
    "budget_score": [
        {"min": 500_000_000, "pts": 30, "label": "5억 이상"},
        {"min": 200_000_000, "pts": 25, "label": "2억 이상"},
        {"min": 100_000_000, "pts": 20, "label": "1억 이상"},
        {"min":  50_000_000, "pts": 13, "label": "5천만 이상"},
        {"min":  30_000_000, "pts":  8, "label": "3천만 이상"},
        {"min":  10_000_000, "pts":  4, "label": "1천만 이상"},
        {"min":           0, "pts":  0, "label": "1천만 미만"},
    ],

    # ── 계약방식 점수 ────────────────────────────────────────────
    "contract_score": [
        {"keyword": "협상",     "pts": 15},
        {"keyword": "일반경쟁", "pts":  5},
        {"keyword": "제한경쟁", "pts":  3},
        {"keyword": "일반",     "pts":  3},
    ],

    # ── 부울경 가산점 (부산/울산/경남) ────────────────────────────
    "boulgyeong_bonus": 10,    # 15 → 10

    # ── 공동수급 가산점 ───────────────────────────────────────────
    "joint_bid_bonus": 5,      # 10 → 5

    # ── 카테고리별 가산점 ─────────────────────────────────────────
    "category_bonus": {
        "SNS관리":  8,
        "홍보영상": 8,
        "인쇄물":   4,
        "행사용역": 5,
        "마케팅":   2,
    },

    # ── 고부가 키워드 보너스 ──────────────────────────────────────
    "high_value_keywords": [
        "홍보대행", "마케팅대행", "광고대행",
        "디지털마케팅", "SNS운영", "콘텐츠제작"
    ],
    "high_value_bonus": 5,

    # ── 키워드 다양성 최대 점수 ───────────────────────────────────
    "keyword_diversity_max": 8,   # 기존 10 → 8

    # ── 마감 임박 패널티 ──────────────────────────────────────────
    "deadline_penalty": -20,      # -10 → -20 (강화)

    # ── 기본 정렬 ────────────────────────────────────────────────
    "default_sort": "score",
}


def load() -> dict:
    """현재 설정 반환 (저장된 값 + 없는 키는 DEFAULT로 채움)."""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = {**DEFAULT, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULT)


def save(data: dict) -> dict:
    """설정 저장 후 반환."""
    current = load()
    editable = [
        "collect_days", "deadline_alert_days",
        "grade_s_min", "grade_a_min", "grade_b_min", "grade_c_min",
        "default_sort", "high_value_bonus", "deadline_penalty",
        "boulgyeong_bonus", "joint_bid_bonus", "base_score",
    ]
    for key in editable:
        if key in data:
            current[key] = data[key]

    os.makedirs(os.path.dirname(SETTINGS_PATH) or ".", exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current
