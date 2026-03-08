@echo off
:: 나라장터 마케팅 공고 모니터링 - Windows 매일 자동 실행 배치파일
:: 이 파일을 Windows 작업 스케줄러에 등록하면 매일 오전 7시에 자동 실행됩니다

cd /d "%~dp0"

:: 가상환경이 있는 경우 활성화 (없으면 아래 줄 주석처리)
:: call venv\Scripts\activate.bat

python main.py >> run.log 2>&1
