"""조회 API 서버: uvicorn app.main:app

수집은 여기서 하지 않는다(app.worker가 따로 돈다).
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import router

app = FastAPI(
    title="거기붐벼? API",
    description="서울 주요 121곳의 혼잡도와 '언제 가면 되는지' 답을 돌려준다.",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(router)
