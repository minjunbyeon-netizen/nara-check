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
    "collect_days": 7,              # 몇 일치 공고 수집
    "deadline_alert_days": 3,       # 마감 D-몇 이내를 임박으로 표시

    # 등급 기준 (점수)
    "grade_a_min": 80,              # A등급 최소 점수
    "grade_b_min": 65,              # B등급 최소 점수
    "grade_c_min": 50,              # C등급 최소 점수

    # 예산 점수 기준
    "budget_score": [
        {"min": 500_000_000, "pts": 25, "label": "5억 이상"},
        {"min": 100_000_000, "pts": 20, "label": "1억 이상"},
        {"min":  50_000_000, "pts": 15, "label": "5천만 이상"},
        {"min":  10_000_000, "pts":  5, "label": "1천만 이상"},
        {"min":           0, "pts": -5, "label": "1천만 미만"},
    ],

    # 계약방식 점수
    "contract_score": [
        {"keyword": "협상", "pts": 15},
        {"keyword": "일반경쟁", "pts": 5},
        {"keyword": "일반",    "pts": 5},
    ],

    # 고부가 키워드 보너스
    "high_value_keywords": [
        "홍보대행", "마케팅대행", "광고대행",
        "디지털마케팅", "SNS운영", "콘텐츠제작"
    ],
    "high_value_bonus": 5,

    # 마감 임박 패널티
    "deadline_penalty": -10,

    # 기본 정렬
    "default_sort": "score",        # score / budget / deadline
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
    # 허용된 키만 업데이트
    editable = [
        "collect_days", "deadline_alert_days",
        "grade_a_min", "grade_b_min", "grade_c_min",
        "default_sort", "high_value_bonus", "deadline_penalty",
    ]
    for key in editable:
        if key in data:
            current[key] = data[key]

    os.makedirs(os.path.dirname(SETTINGS_PATH) or ".", exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current
