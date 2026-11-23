"""환경변수로 받는 설정. 비밀값은 코드와 문서에 적지 않는다."""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # SecretStr: 설정 객체를 실수로 로그에 찍어도 값이 '**********'로만 나온다.
    seoul_api_key: SecretStr = SecretStr("")
    # API 문서 화면(/api/docs). 프론트의 /api 중계를 타고 밖에 보이지 않게 기본은 끈다.
    enable_docs: bool = False
    seoul_api_base_url: str = "http://openapi.seoul.go.kr:8088"
    database_url: str = "sqlite:///./local.db"

    collect_interval_seconds: int = 300
    collect_concurrency: int = 10
    collect_timeout_seconds: float = 10.0
    collect_retries: int = 2

    # 관측 시각이 이보다 오래되면 "업데이트가 늦어지고 있어요"로 보여 준다.
    stale_after_minutes: int = 60

    @property
    def sqlalchemy_url(self) -> str:
        """postgres:// 계열 주소를 psycopg 3 드라이버 주소로 맞춘다."""
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
