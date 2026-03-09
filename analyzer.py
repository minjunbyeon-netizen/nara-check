"""
Claude AI 분석 모듈 - claude CLI를 사용하여 공고별 추천 점수 및 코멘트 생성
별도 API 키 불필요 — Claude Code 설치된 환경에서 자동 동작
"""
import json
import logging
import os
import subprocess
from config import MAX_BIDS_PER_ANALYSIS
from fetcher import format_bid_summary

logger = logging.getLogger(__name__)

FULL_PROMPT_TEMPLATE = """당신은 대한민국 광고대행사 입찰 전략 전문가입니다.
조달청 나라장터에 올라온 마케팅/광고 관련 공고들을 분석하여,
광고대행사 입장에서 입찰 가치가 있는 공고를 추천합니다.

## 우리 회사 입찰 전략 (반드시 이 기준으로 평가)

### 타겟 공고 유형 (3가지)
1. **SNS 관리/운영**: 예산 1억 기준, 이하 금액도 OK (언더 포함). 예산이 작아도 감점 없음.
2. **홍보영상 제작**: 금액 무관, 소규모도 전부 OK. 예산이 적다고 감점 금지.
3. **인쇄물/홍보물 제작**: 관공서 발주 인쇄물, 현수막, 브로슈어 등.

### 지역 우선순위
- **부울경(부산/울산/경남) 기관 발주**: 최우선 대상. 지역 가산점 +15점
- 전국 기관도 수집하되, 부울경이 있으면 상단 배치

### 행사용역 처리
- 행사/이벤트/축제 용역: **공동수급 가능** 표시가 있으면 수집 대상
- 공동수급 불가 단독 행사용역은 낮은 점수 부여

### 예산별 점수 가이드
| 예산 | SNS | 홍보영상 | 인쇄물 |
|------|-----|---------|--------|
| 5억 이상 | +25 | +25 | +25 |
| 1억 이상 | +20 | +15 | +15 |
| 5천만 이상 | +12 | +10 | +10 |
| 1천만 이상 | +5 | +8 | +5 |
| 1천만 미만 | 0 (감점 없음) | +5 (소규모 OK) | 0 |

### 분석 기준 (우선순위 순)
1. 카테고리 적합성 (우리 타겟 3가지인가)
2. 지역 (부울경 우선)
3. 예산 규모 (카테고리별 기준 적용)
4. 경쟁 강도 (지역 제한, 자격 요건 등)
5. 마감 여유 (준비 기간이 충분한가)
6. 기관 신뢰도 (지자체, 공공기관 등 관공서 우선)
7. 공동수급 가능 여부 (행사용역의 경우)

---

다음 입찰공고들을 분석해주세요:

{bids_text}

각 공고에 대해 아래 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {{
    "bid_no": "공고번호",
    "score": 85,
    "grade": "★★★★",
    "recommendation": "강력추천",
    "reason": "부울경 기관 발주의 SNS 운영 공고. 예산 8천만원으로 1억 이하지만 언더도 OK 기준에 부합. 광고대행사가 즉시 수행 가능하며 마감까지 2주 여유.",
    "watch_out": "실적 증명서 제출 필요 여부 확인",
    "category": "SNS관리",
    "budget_note": "1억 이하 언더 OK",
    "region_bonus": true,
    "joint_bid": false
  }}
]

grade 기준: ★★★★★(90+점), ★★★★(75~89점), ★★★(60~74점), ★★(40~59점), ★(40미만)
recommendation: "강력추천" / "추천" / "검토" / "보류" / "비추천"
category: "SNS관리" / "홍보영상" / "인쇄물" / "행사용역" / "마케팅"
region_bonus: 부울경 기관이면 true
joint_bid: 공동수급 가능하면 true
"""


def analyze_bids(bids: list[dict]) -> list[dict]:
    """Claude CLI로 공고 목록을 분석하고 추천 점수를 추가한다."""
    if not bids:
        logger.info("분석할 공고가 없습니다.")
        return []

    analyzed = []
    for i in range(0, len(bids), MAX_BIDS_PER_ANALYSIS):
        batch = bids[i:i + MAX_BIDS_PER_ANALYSIS]
        logger.info(f"배치 분석 중: {i+1}~{i+len(batch)}번 공고 ({len(batch)}건)")
        batch_results = _analyze_batch(batch)
        analyzed.extend(batch_results)

    analyzed.sort(key=lambda x: x.get("score", 0), reverse=True)
    return analyzed


def _analyze_batch(batch: list[dict]) -> list[dict]:
    """단일 배치를 claude CLI로 분석."""
    bids_text = ""
    for j, bid in enumerate(batch, 1):
        bids_text += f"\n[공고 {j}]\n{format_bid_summary(bid)}\n"

    prompt = FULL_PROMPT_TEMPLATE.format(bids_text=bids_text)

    # CLAUDECODE 환경변수 제거 → 중첩 실행 방지 우회
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            logger.error(f"claude CLI 오류: {result.stderr[:200]}")
            return _fallback_results(batch)

        raw_text = result.stdout.strip()

        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        if start == -1 or end == 0:
            logger.error("응답에서 JSON 배열을 찾지 못함")
            return _fallback_results(batch)

        analysis_list = json.loads(raw_text[start:end])
    except subprocess.TimeoutExpired:
        logger.error("claude CLI 응답 시간 초과 (120초)")
        return _fallback_results(batch)
    except Exception as e:
        logger.error(f"분석 오류: {e}")
        return _fallback_results(batch)

    # 원본 bid 데이터와 분석 결과 병합
    analysis_map = {item["bid_no"]: item for item in analysis_list}
    results = []
    for bid in batch:
        bid_no = bid.get("bidNtceNo", "")
        analysis = analysis_map.get(bid_no, {})
        merged = {**bid, **analysis}
        if "bid_no" not in merged:
            merged["bid_no"] = bid_no

        # fetcher에서 감지한 부울경/공동수급 정보가 AI 결과와 다를 경우 병합
        if bid.get("_is_boulgyeong") and not merged.get("region_bonus"):
            merged["region_bonus"] = True
        if bid.get("_joint_bid") and not merged.get("joint_bid"):
            merged["joint_bid"] = True

        results.append(merged)

    return results


def _fallback_results(batch: list[dict]) -> list[dict]:
    """오류 시 기본값으로 채운 결과 반환."""
    return [{
        **bid,
        "bid_no": bid.get("bidNtceNo", ""),
        "score": 0,
        "grade": "분석실패",
        "recommendation": "직접확인",
        "reason": "AI 분석 중 오류가 발생했습니다. 나라장터에서 직접 확인해주세요.",
        "watch_out": "",
        "category": bid.get("_category", "미분류"),
        "region_bonus": bid.get("_is_boulgyeong", False),
        "joint_bid": bid.get("_joint_bid", False),
    } for bid in batch]
