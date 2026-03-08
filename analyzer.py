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

분석 기준:
1. 예산 규모 (클수록 좋음)
2. 업무 적합성 (광고대행사가 실제로 할 수 있는 업무인가)
3. 경쟁 강도 (지역 제한, 자격 요건 등으로 경쟁이 적을수록 좋음)
4. 마감 여유 (준비 기간이 충분한가)
5. 기관 신뢰도 (지자체, 공공기관 등)

다음 입찰공고들을 분석해주세요:

{bids_text}

각 공고에 대해 아래 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {{
    "bid_no": "공고번호",
    "score": 85,
    "grade": "★★★★",
    "recommendation": "강력추천",
    "reason": "예산 3천만원 규모의 SNS 운영 공고로, 광고대행사가 즉시 수행 가능한 업무입니다. 지역 제한이 없어 경쟁에 유리하며 마감까지 2주 여유가 있습니다.",
    "watch_out": "실적 증명서 제출 필요 여부 확인 필요",
    "category": "SNS관리"
  }}
]

grade 기준: ★★★★★(90+점), ★★★★(75~89점), ★★★(60~74점), ★★(40~59점), ★(40미만)
recommendation: "강력추천" / "추천" / "검토" / "보류" / "비추천"
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

    # CLAUDECODE 환경변수 제거 → 중첩 실행 방지 우회 (사용자 터미널에서 실행 시 필요)
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

        # JSON 배열 추출
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
        "category": "미분류",
    } for bid in batch]
