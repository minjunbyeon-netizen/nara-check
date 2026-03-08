"""
Windows 작업 스케줄러 자동 등록 스크립트
실행: python setup_scheduler.py
(관리자 권한으로 실행하면 더 안정적)
"""
import os
import sys
import subprocess
from pathlib import Path


def register_task():
    script_dir = Path(__file__).parent.resolve()
    bat_path = script_dir / "run_daily.bat"
    python_exe = sys.executable
    main_py = script_dir / "main.py"

    task_name = "NarajangteoMarketingMonitor"

    # 기존 작업 삭제 후 재등록
    subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True,
    )

    # 매일 자정(00:00) 실행 등록
    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", task_name,
            "/TR", f'"{python_exe}" "{main_py}"',
            "/SC", "DAILY",
            "/ST", "00:00",
            "/F",
            "/RL", "HIGHEST",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"작업 스케줄러 등록 완료!")
        print(f"  작업명: {task_name}")
        print(f"  실행 시각: 매일 자정 00:00 (오전 12시)")
        print(f"  실행 파일: {main_py}")
        print()
        print("확인: 작업 스케줄러 앱 → 작업 스케줄러 라이브러리에서 확인 가능")
    else:
        print(f"등록 실패: {result.stderr}")
        print("수동 등록 방법:")
        print("  1. 작업 스케줄러 앱 열기")
        print("  2. 기본 작업 만들기")
        print(f"  3. 트리거: 매일 00:00")
        print(f"  4. 동작: 프로그램 시작 → {python_exe}")
        print(f"  5. 인수 추가: {main_py}")
        print(f"  6. 시작 위치: {script_dir}")


if __name__ == "__main__":
    register_task()
