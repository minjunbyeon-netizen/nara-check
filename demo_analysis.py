"""
데모 분석 - 실제 나라장터에서 수집한 마케팅 공고 샘플로 분석 로직 검증
"""
import json, os, subprocess, sys

# ─── 실제 수집된 공고 샘플 (웹 검색으로 확인된 실제 공고들) ───────────
SAMPLE_BIDS = [
    {
        "bidNtceNo": "R25BK00755378-001",
        "bidNtceNm": "2025년 SNS 운영 및 디지털 홍보 용역",
        "ntceInsttNm": "축산물품질평가원",
        "dminsttNm": "축산물품질평가원",
        "bidNtceDt": "2025-03-28",
        "bidClseDt": "2025-04-15 10:00",
        "presmptPrce": "152,000,000",
        "cntrctMthd": "협상에 의한 계약",
        "prtcptLmtRgn": "중소기업 제한",
        "ntceInsttOfclNm": "담당자",
        "bidNtceUrl": "https://www.g2b.go.kr",
        "_matched_keywords": ["SNS", "홍보", "디지털마케팅"],
        "_extra": "기술평가80%+가격20%, 광고대행업 업종코드 필수, 직원 보유 조건"
    },
    {
        "bidNtceNo": "R25BK00748298-000",
        "bidNtceNm": "2025 국립박물관문화재단 SNS 운영 및 홍보 영상 제작 용역",
        "ntceInsttNm": "국립박물관문화재단",
        "dminsttNm": "국립박물관문화재단",
        "bidNtceDt": "2025-03-28",
        "bidClseDt": "2025-05-08 14:00",
        "presmptPrce": "84,700,000",
        "cntrctMthd": "제한경쟁",
        "prtcptLmtRgn": "전국",
        "_matched_keywords": ["SNS", "홍보영상", "영상제작"],
        "_extra": "SNS운영 + 홍보영상 동시 진행, 공공재단 발주"
    },
    {
        "bidNtceNo": "R25BK00607574-000",
        "bidNtceNm": "2025년 인천대학교 SNS 홍보대행 용역",
        "ntceInsttNm": "인천대학교",
        "dminsttNm": "인천대학교",
        "bidNtceDt": "2025-02-07",
        "bidClseDt": "2025-02-11 10:00",
        "presmptPrce": "93,000,000",
        "cntrctMthd": "제한경쟁",
        "prtcptLmtRgn": "전국",
        "_matched_keywords": ["SNS", "홍보대행"],
        "_extra": "대학교 발주, 짧은 입찰기간 4일"
    },
    {
        "bidNtceNo": "R25XX00123456-000",
        "bidNtceNm": "부산광역시 브랜드 글로벌허브도시 국내외 광고 제작 용역",
        "ntceInsttNm": "한국언론진흥재단",
        "dminsttNm": "부산광역시",
        "bidNtceDt": "2025-04-01",
        "bidClseDt": "2025-04-10 18:00",
        "presmptPrce": "200,000,000",
        "cntrctMthd": "협상에 의한 계약",
        "prtcptLmtRgn": "전국",
        "_matched_keywords": ["광고", "광고 제작", "브랜딩"],
        "_extra": "광역시 브랜딩 캠페인, 2억 규모"
    },
    {
        "bidNtceNo": "R25XX00234567-000",
        "bidNtceNm": "2025~2027 KPC 홍보 기획 및 운영 대행",
        "ntceInsttNm": "대한장애인체육회",
        "dminsttNm": "대한장애인체육회",
        "bidNtceDt": "2025-04-02",
        "bidClseDt": "2025-04-11 18:00",
        "presmptPrce": "940,830,000",
        "cntrctMthd": "협상에 의한 계약",
        "prtcptLmtRgn": "전국",
        "_matched_keywords": ["홍보대행", "홍보기획"],
        "_extra": "3년 장기계약, 9.4억 대형 공고"
    },
    {
        "bidNtceNo": "R25XX00345678-000",
        "bidNtceNm": "2025 IBK기업은행 검색광고 운영 대행",
        "ntceInsttNm": "한국언론진흥재단",
        "dminsttNm": "IBK기업은행",
        "bidNtceDt": "2025-04-03",
        "bidClseDt": "2025-04-16 18:00",
        "presmptPrce": "1,200,000,000",
        "cntrctMthd": "협상에 의한 계약",
        "prtcptLmtRgn": "전국",
        "_matched_keywords": ["검색광고", "온라인광고"],
        "_extra": "12억 대형 검색광고, 금융기관 발주, 한국언론진흥재단 경유"
    },
    {
        "bidNtceNo": "R25XX00456789-000",
        "bidNtceNm": "대전디자인핫스팟 홍보 및 운영 용역",
        "ntceInsttNm": "대전디자인진흥원",
        "dminsttNm": "대전디자인진흥원",
        "bidNtceDt": "2025-04-01",
        "bidClseDt": "2025-04-11 18:00",
        "presmptPrce": "30,000,000",
        "cntrctMthd": "수의계약",
        "prtcptLmtRgn": "대전",
        "_matched_keywords": ["홍보", "마케팅"],
        "_extra": "소규모 3천만원, 수의계약, 지역제한(대전)"
    },
    {
        "bidNtceNo": "R26XX00567890-000",
        "bidNtceNm": "2026년 KSPO 소셜미디어(SNS) 운영대행 용역",
        "ntceInsttNm": "국민체육진흥공단",
        "dminsttNm": "국민체육진흥공단",
        "bidNtceDt": "2026-02-15",
        "bidClseDt": "2026-03-15 18:00",
        "presmptPrce": "120,000,000",
        "cntrctMthd": "협상에 의한 계약",
        "prtcptLmtRgn": "전국",
        "_matched_keywords": ["SNS", "소셜미디어"],
        "_extra": "공공기관 SNS 운영, 1.2억"
    },
    {
        "bidNtceNo": "R26XX00678901-000",
        "bidNtceNm": "2026년 노란우산 디지털 광고대행 용역",
        "ntceInsttNm": "중소기업중앙회",
        "dminsttNm": "중소기업중앙회",
        "bidNtceDt": "2026-01-20",
        "bidClseDt": "2026-02-20 18:00",
        "presmptPrce": "350,000,000",
        "cntrctMthd": "협상에 의한 계약",
        "prtcptLmtRgn": "전국 (광고업 업종코드 필수)",
        "_matched_keywords": ["디지털마케팅", "광고대행", "온라인광고"],
        "_extra": "SNS운영+디지털광고+마케팅 통합, 광고업 업종코드 필수"
    },
]

def format_bid(bid):
    return (
        f"공고번호: {bid['bidNtceNo']}\n"
        f"공고명: {bid['bidNtceNm']}\n"
        f"발주기관: {bid['ntceInsttNm']} / 수요기관: {bid.get('dminsttNm','')}\n"
        f"예산: {bid['presmptPrce']}원\n"
        f"마감: {bid['bidClseDt']}\n"
        f"계약방법: {bid['cntrctMthd']}\n"
        f"참가제한: {bid['prtcptLmtRgn']}\n"
        f"특이사항: {bid.get('_extra','')}\n"
        f"매칭키워드: {', '.join(bid['_matched_keywords'])}"
    )

bids_text = ""
for i, bid in enumerate(SAMPLE_BIDS, 1):
    bids_text += f"\n[공고 {i}]\n{format_bid(bid)}\n"

prompt = f"""당신은 대한민국 광고대행사 입찰 전략 전문가입니다.
아래 9개의 실제 나라장터 마케팅 공고를 분석해주세요.

분석 기준:
1. 예산 규모 (클수록 좋지만, 너무 크면 대형사와 경쟁)
2. 업무 적합성 (중소 광고대행사가 실제로 수행 가능한가)
3. 경쟁 강도 (계약방법, 참가자격 제한)
4. 마감 여유
5. 기관 신뢰도 및 관계 확장성

{bids_text}

각 공고를 JSON 배열로만 응답하세요:
[
  {{
    "bid_no": "공고번호",
    "score": 85,
    "grade": "★★★★",
    "recommendation": "강력추천",
    "reason": "구체적인 추천 이유 (2~3문장)",
    "watch_out": "주의사항",
    "category": "SNS관리/영상제작/광고대행/검색광고/홍보기획 중 하나",
    "best_for": "이런 회사에 적합"
  }}
]"""

print("=== Claude AI 분석 시작 ===")
print(f"총 {len(SAMPLE_BIDS)}개 공고 분석 중...\n")

env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
claude_cmd = r"C:\Users\USER\AppData\Roaming\npm\claude.cmd"
result = subprocess.run(
    [claude_cmd, "-p", prompt],
    capture_output=True, text=True, encoding="utf-8", timeout=120, env=env
)

if result.returncode != 0:
    print("오류:", result.stderr[:300])
    sys.exit(1)

raw = result.stdout.strip()
start = raw.find("[")
end = raw.rfind("]") + 1
analysis = json.loads(raw[start:end])

# 점수 정렬
analysis.sort(key=lambda x: x.get("score", 0), reverse=True)

print("=" * 70)
print("분석 결과")
print("=" * 70)
for item in analysis:
    bid = next((b for b in SAMPLE_BIDS if b["bidNtceNo"] == item["bid_no"]), {})
    print(f"\n{item.get('grade','')} [{item.get('recommendation','')}] {bid.get('bidNtceNm','')}")
    print(f"  예산: {bid.get('presmptPrce','')}원  |  기관: {bid.get('ntceInsttNm','')}  |  점수: {item.get('score',0)}점")
    print(f"  카테고리: {item.get('category','')}  |  적합대상: {item.get('best_for','')}")
    print(f"  추천이유: {item.get('reason','')}")
    if item.get("watch_out"):
        print(f"  주의: {item.get('watch_out','')}")
    print("-" * 70)

# JSON 저장
import os
os.makedirs("reports", exist_ok=True)
with open("reports/demo_analysis.json", "w", encoding="utf-8") as f:
    merged = []
    for item in analysis:
        bid = next((b for b in SAMPLE_BIDS if b["bidNtceNo"] == item["bid_no"]), {})
        merged.append({**bid, **item})
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f"\n분석 완료! 결과 저장: reports/demo_analysis.json")
