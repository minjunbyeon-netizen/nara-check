# 나라장터 마케팅 공고 모니터링 시스템

조달청 나라장터에서 마케팅/광고 관련 입찰 공고를 매일 자동 수집하고,
Claude AI가 분석하여 입찰 추천 리포트를 이메일로 발송하는 시스템입니다.

---

## 무엇을 해주나요?

- **매일 오전 7시** 자동 실행
- SNS 관리, 홍보영상 제작, 광고물, 온라인광고, 옥외광고 등 40+ 키워드로 공고 필터링
- Claude AI가 각 공고를 분석하여 **점수(0~100점) + 추천 이유** 생성
- 마크다운 + HTML 리포트 파일 저장
- 이메일로 리포트 자동 발송

---

## 설치 방법

### 1단계: Python 패키지 설치

```bash
cd narajangteo-monitor
pip install -r requirements.txt
```

### 2단계: API 키 발급

#### 나라장터 API 키 (필수)
1. [공공데이터포털](https://www.data.go.kr) 회원가입
2. `나라장터 입찰공고정보서비스` 검색 후 활용 신청
3. 승인 후 마이페이지에서 서비스 키 확인 (보통 1~2일 소요)

#### Claude API 키 (필수)
1. [Anthropic Console](https://console.anthropic.com) 접속
2. API Keys 메뉴에서 새 키 생성

#### Gmail 앱 비밀번호 (이메일 발송 원하는 경우)
1. Google 계정 → 보안 → 2단계 인증 활성화
2. 앱 비밀번호 생성 (16자리)

### 3단계: 환경 변수 설정

```bash
copy .env.example .env
```

`.env` 파일을 열어 실제 값으로 수정:

```
NARAJANGTEO_API_KEY=발급받은_서비스_키
ANTHROPIC_API_KEY=sk-ant-...
EMAIL_SENDER=내이메일@gmail.com
EMAIL_PASSWORD=앱비밀번호16자리
EMAIL_RECIPIENT=받을이메일@gmail.com
```

---

## 실행 방법

### 수동 실행 (테스트)

```bash
python main.py
```

실행 후 `reports/` 폴더에 리포트가 생성됩니다.

### 매일 자동 실행 등록 (Windows)

```bash
python setup_scheduler.py
```

또는 직접 작업 스케줄러 등록:
1. Windows 검색 → **작업 스케줄러** 열기
2. **기본 작업 만들기** 클릭
3. 트리거: 매일 / 시작 시간 07:00
4. 동작: 프로그램 시작
5. 프로그램: `python`
6. 인수 추가: `main.py`
7. 시작 위치: `(이 폴더 경로)`

---

## 리포트 확인

- **파일**: `reports/report_YYYY-MM-DD.md` (마크다운)
- **파일**: `reports/report_YYYY-MM-DD.html` (브라우저에서 열기)
- **이메일**: 설정한 수신 주소로 HTML 리포트 발송

### 리포트 샘플

```
# 나라장터 마케팅 공고 일일 리포트
날짜: 2026-03-06 | 총 공고수: 12건 | 추천 공고: 3건

## 강력 추천 공고 (3건)

### ★★★★★ [강력추천] ○○시 SNS 홍보 운영 용역
- 발주기관: ○○광역시청
- 예산: 48,000,000원
- 마감일: 2026-03-20
- AI 점수: 92점

추천 이유: 예산 4800만원 규모의 SNS 운영 공고입니다.
지역 제한 없이 전국 입찰 가능하며, 마감까지 2주 여유가 있습니다...
```

---

## 키워드 커스터마이징

`config.py`의 `MARKETING_KEYWORDS` 목록에 원하는 키워드를 추가하거나 제거할 수 있습니다.

---

## 로그 확인

실행 로그는 `monitor.log` 파일에 저장됩니다.

```bash
type monitor.log
```

---

## 파일 구조

```
narajangteo-monitor/
├── .env                ← API 키 설정 (직접 생성, git 제외)
├── .env.example        ← 설정 템플릿
├── requirements.txt
├── main.py             ← 메인 실행 파일
├── config.py           ← 설정 및 키워드
├── fetcher.py          ← 나라장터 API 호출
├── analyzer.py         ← Claude AI 분석
├── reporter.py         ← 리포트 생성
├── notifier.py         ← 이메일 발송
├── setup_scheduler.py  ← 스케줄러 자동 등록
├── run_daily.bat       ← 배치 실행 파일
├── monitor.log         ← 실행 로그 (자동 생성)
└── reports/            ← 리포트 저장 폴더 (자동 생성)
    ├── report_2026-03-06.md
    └── report_2026-03-06.html
```
