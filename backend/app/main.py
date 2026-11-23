"""조회 API 서버: uvicorn app.main:app

수집은 여기서 하지 않는다(app.worker가 따로 돈다).
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import router
from app.config import get_settings


def create_app() -> FastAPI:
    # 문서 화면은 개발할 때만 켠다(ENABLE_DOCS=true). 프론트가 /api 아래를 백엔드로
    # 중계하기 때문에, 켜 두면 사이트 주소에서 API 문서가 그대로 열린다.
    docs_on = get_settings().enable_docs
    api = FastAPI(
        title="거기붐벼? API",
        description="서울 주요 121곳의 혼잡도와 '언제 가면 되는지' 답을 돌려준다.",
        version="0.1.0",
        docs_url="/api/docs" if docs_on else None,
        openapi_url="/api/openapi.json" if docs_on else None,
        redoc_url=None,
    )
    api.include_router(router)
    return api


app = create_app()
