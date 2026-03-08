"""
알림 발송 모듈 - 이메일로 일일 리포트 전송
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from config import (
    EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT,
    EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT,
)

logger = logging.getLogger(__name__)


def send_report_email(
    html_filepath: str,
    md_filepath: str,
    analyzed_bids: list[dict],
    report_date: datetime = None,
) -> bool:
    """HTML 리포트를 이메일로 발송한다. 성공 여부를 반환한다."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        logger.warning("이메일 설정이 없습니다. .env 파일을 확인하세요. 파일 저장만 진행합니다.")
        return False

    if report_date is None:
        report_date = datetime.now()

    date_str = report_date.strftime("%Y-%m-%d")
    top_count = len([b for b in analyzed_bids if b.get("score", 0) >= 75])

    subject = f"[나라장터] {date_str} 마케팅 공고 리포트 — 추천 {top_count}건"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT

    # 텍스트 본문 (HTML 미지원 클라이언트용)
    plain_text = f"나라장터 마케팅 공고 일일 리포트 ({date_str})\n총 {len(analyzed_bids)}건 수집, 추천 {top_count}건\n\n첨부 파일을 확인해주세요."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))

    # HTML 본문
    try:
        with open(html_filepath, "r", encoding="utf-8") as f:
            html_content = f.read()
        msg.attach(MIMEText(html_content, "html", "utf-8"))
    except FileNotFoundError:
        logger.error(f"HTML 파일을 찾을 수 없습니다: {html_filepath}")

    # 마크다운 첨부
    try:
        with open(md_filepath, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"report_{date_str}.md",
            )
            msg.attach(attachment)
    except FileNotFoundError:
        logger.warning(f"마크다운 파일을 찾을 수 없습니다: {md_filepath}")

    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        logger.info(f"이메일 발송 성공: {EMAIL_RECIPIENT}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False
