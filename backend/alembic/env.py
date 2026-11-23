"""Alembic 실행 환경. DB 주소는 환경변수(DATABASE_URL)에서만 읽는다."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401  (테이블 정의를 메타데이터에 올린다)
from app.config import get_settings
from app.db import Base, make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations() -> None:
    url = config.get_main_option("sqlalchemy.url") or get_settings().sqlalchemy_url
    engine = make_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
