"""수집 워커. 웹 서버와 따로 한 개만 띄운다: python -m app.worker

웹 서버(uvicorn) 안에서 돌리면 서버 프로세스 수만큼 중복 수집되므로 분리했다.
--once 를 붙이면 한 바퀴만 돌고 끝난다(확인용).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

from app.collector.service import collect_once
from app.config import get_settings
from app.db import get_session_factory
from app.seed import sync_places

logger = logging.getLogger("app.worker")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # httpx의 요청 주소 로그(인증키 포함)는 app.collector.client가 끈다.


async def run(once: bool) -> int:
    settings = get_settings()
    if not settings.seoul_api_key:
        logger.error("환경변수 SEOUL_API_KEY가 비어 있어요. .env에 인증키를 넣어 주세요.")
        return 1

    session_factory = get_session_factory()
    with session_factory() as session:
        count = sync_places(session)
    logger.info("장소 %d곳 준비됨, 수집 주기 %d초", count, settings.collect_interval_seconds)

    while True:
        started = time.monotonic()
        try:
            await collect_once(settings, session_factory)
        except Exception:
            # 한 바퀴가 통째로 실패해도 워커는 죽지 않고 다음 주기에 다시 시도한다.
            logger.exception("수집 한 바퀴 실패")
            if once:
                return 1
        if once:
            return 0
        elapsed = time.monotonic() - started
        await asyncio.sleep(max(1.0, settings.collect_interval_seconds - elapsed))


def main() -> None:
    parser = argparse.ArgumentParser(description="거기붐벼? 수집 워커")
    parser.add_argument("--once", action="store_true", help="한 바퀴만 수집하고 끝낸다")
    args = parser.parse_args()
    setup_logging()
    try:
        sys.exit(asyncio.run(run(args.once)))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
