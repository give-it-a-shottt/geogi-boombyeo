# T-002 Windows에서 alembic.ini를 못 읽음

## 한눈에 보기 (코드 몰라도 OK)
무슨 문제였나: DB 테이블을 만드는 도구(Alembic)의 설정 파일에 한글 주석을 적었더니, Windows에서 그 파일을 읽다가 오류가 났다.
어떻게 해결했나: 설정 파일에는 영문만 쓰기로 하고, 파일 맨 위에 그 이유를 적어 두었다.

## 개발자 상세
- 증상: `UnicodeDecodeError: 'cp949' codec can't decode byte 0xeb in position 68` (alembic `Config`가 `alembic.ini`를 읽을 때)
- 원인: Alembic은 ini 파일을 `encoding="locale"`로 읽는다. 한국어 Windows의 기본 코드 페이지는 cp949라서 UTF-8로 저장한 한글을 해석하지 못한다. 리눅스(도커)에서는 UTF-8이라 문제가 드러나지 않는다.
- 해결: `backend/alembic.ini`를 ASCII만으로 작성. 한글 설명이 필요한 내용은 `alembic/env.py`(파이썬 파일은 UTF-8로 읽힘)에 둔다.
- 재발 방지: `tests/test_seed_and_schema.py::test_migration_creates_the_same_tables_as_models`가 Alembic을 실제로 실행하므로, 다시 한글이 들어가면 Windows에서 바로 실패한다.
- 관련: F-001

최종 수정: 2026-11-23
