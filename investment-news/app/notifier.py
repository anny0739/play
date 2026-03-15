"""macOS 데스크탑 알림 (osascript)."""

import subprocess
import logging

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "stock_kr": "국내주식",
    "stock_us": "미주식",
    "realestate": "부동산",
    "macro": "거시경제",
}


def send_notification(title: str, body: str):
    """macOS 알림 팝업 발송."""
    script = f'display notification "{body}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, timeout=10)
    except FileNotFoundError:
        logger.warning("osascript를 찾을 수 없습니다. macOS 환경에서만 알림이 가능합니다.")
    except subprocess.CalledProcessError as e:
        logger.error("알림 발송 실패: %s", e)
    except subprocess.TimeoutExpired:
        logger.error("알림 발송 타임아웃.")


def notify_fetch_complete(counts: dict[str, int], market: dict | None = None):
    """
    뉴스 수집 완료 알림.
    counts: {category: 건수}
    market: 지수 데이터 (optional)
    """
    total = sum(counts.values())
    category_parts = " | ".join(
        f"{CATEGORY_LABELS.get(cat, cat)} {n}"
        for cat, n in counts.items()
        if n > 0
    )
    body = f"오늘의 뉴스 {total}건 수집됨\n{category_parts}"

    if market:
        kospi = market.get("kospi")
        usd_krw = market.get("usd_krw")
        if kospi:
            body += f"\nKOSPI {kospi:,.2f}"
        if usd_krw:
            body += f" | USD/KRW {usd_krw:,.1f}"

    send_notification("재테크 뉴스 수집 완료", body)
    logger.info("알림 발송: %s", body)
