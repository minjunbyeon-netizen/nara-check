# 나라장터 마케팅 공고 모니터링

나라장터 공공데이터 API에서 마케팅 관련 공고를 자동 수집·분석하여 웹 대시보드로 제공하는 시스템입니다.

---

## 프로젝트 구조

```
narajangteo-monitor/
├── server.py           # Flask 웹서버 + APScheduler (메인 진입점)
├── fetcher.py          # 나라장터 API 수집 + 카테고리/지역/공동수급 분류
├── analyze_bids.py     # 점수 산정 + 등급 부여 + dashboard.html 생성
├── analyzer.py         # Claude AI 분석 배치 처리
├── db.py               # SQLite DB 관리 (upsert, 조회)
├── settings.py         # 설정 관리 (DEFAULT + reports/settings.json 오버라이드)
├── config.py           # 키워드 상수 (카테고리별 분류 키워드)
├── requirements.txt    # Python 의존성
├── Procfile            # Railway/Render 배포용
├── .env.example        # 환경변수 샘플
├── reports/
│   ├── bids.db         # SQLite DB (공고 누적 저장)
│   ├── settings.json   # 사용자 설정 저장 (자동 생성)
│   └── live_bids_raw.json  # 마지막 수집 원본 JSON
└── log/
    └── YYYY-MM-DD.log  # 작업 로그 (날짜별)
```

---

## 핵심 기능

### 수집 대상
- **SNS 관리**: 1억 내외 (플러스 마이너스) 공고 우선
- **홍보영상**: 금액 무관 전체 수집
- **인쇄물**: 홍보물/현수막/브로슈어 등
- **행사용역**: 공동수급 가능 조건 우선
- **지역**: 부산/울산/경남(부울경) 우선

### 등급 체계 (S-A-B-C-D)

기본 30점 + 아래 가산점 합산:

| 항목 | 점수 |
|------|------|
| 예산 5억 이상 | +30 |
| 예산 2억 이상 | +25 |
| 예산 1억 이상 | +20 |
| 예산 5천만 이상 | +13 |
| 예산 3천만 이상 | +8 |
| 예산 1천만 이상 | +4 |
| 계약방식: 협상 | +15 |
| 계약방식: 일반경쟁 | +5 |
| 부울경(부산/울산/경남) | +10 |
| 공동수급 | +5 |
| SNS관리 / 홍보영상 카테고리 | +8 |
| 행사용역 카테고리 | +5 |
| 인쇄물 카테고리 | +4 |
| 마케팅 카테고리 | +2 |
| 고부가 키워드 포함 | +5 |
| 키워드 다양성 (최대) | +8 |
| 마감 임박 (3일 이내) | -20 |

| 등급 | 기준 |
|------|------|
| S | 90점 이상 |
| A | 75점 이상 |
| B | 60점 이상 |
| C | 45점 이상 |
| D | 45점 미만 |

### 자동 수집 스케줄
- **매주 화요일 / 금요일 오전 09:00** (한국 시간)
- 수동 수집: 대시보드 상단 "데이터 동기화" 버튼

---

## 설치 및 실행

### 환경 설정

```bash
pip install -r requirements.txt
```

`.env` 파일 생성 (`.env.example` 참고):

```
NARA_API_KEY=나라장터_API_키
```

### 로컬 실행

```bash
python server.py
```

브라우저에서 `http://127.0.0.1:5000` 접속

### Windows 독립 실행 (창 유지)

```powershell
Start-Process python -ArgumentList 'server.py' -WorkingDirectory '프로젝트_경로' -WindowStyle Normal
```

---

## 배포 (Railway / Render)

`Procfile`에 실행 명령 정의됨:

```
web: python server.py
```

환경변수 설정:
- `NARA_API_KEY`: 나라장터 공공데이터 API 키
- `PORT`: 포트 (플랫폼 자동 주입)
- `SETTINGS_PATH`: `/data/settings.json` (볼륨 마운트 시)

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 대시보드 HTML |
| GET | `/api/status` | 수집 현황 JSON |
| POST | `/api/refresh` | 즉시 수집 트리거 |
| GET | `/api/settings` | 현재 설정 조회 |
| POST | `/api/settings` | 설정 변경 + 대시보드 재생성 |

---

## 인코딩 주의사항

Windows 환경에서 CMD 창에 한글 로그가 깨질 수 있습니다.

- 기능 동작에는 영향 없음 (파일/DB는 UTF-8로 정상 저장)
- Python 실행 시 환경변수 추가: `set PYTHONIOENCODING=utf-8`
- PowerShell에서 실행하면 일부 개선됨

---

## GitHub

저장소: https://github.com/minjunbyeon-netizen/nara-check
