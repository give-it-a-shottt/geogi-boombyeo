# T-001 httpx 로그에 인증키가 찍힘

## 한눈에 보기 (코드 몰라도 OK)
무슨 문제였나: 서울시 API는 인증키를 주소 안에 넣어 부른다. 그런데 통신 라이브러리(httpx)가 부른 주소를 기본으로 로그에 찍어서, 인증키가 로그에 그대로 남았다.
어떻게 해결했나: 수집 코드를 불러오는 순간 httpx의 로그 수준을 올려 주소가 찍히지 않게 했다. 테스트가 로그에 키가 없는지 계속 확인한다.

## 개발자 상세
- 증상: `tests/test_collector.py::test_collect_once_one_place_failing_does_not_stop_others` 실패. 캡처된 로그에 `HTTP Request: GET http://seoul.test/(인증키)/json/citydata_ppltn/...` 줄이 있었다.
- 원인: httpx는 요청마다 INFO 수준으로 전체 주소를 찍는다. 처음에는 워커의 `setup_logging()`에서만 껐는데, 그러면 워커가 아닌 경로(테스트, 스크립트, 다른 진입점)에서는 그대로 찍힌다.
- 해결: `backend/app/collector/client.py`를 불러올 때 `httpx` · `httpcore` 로거를 WARNING으로 올린다. 이 모듈을 거치지 않고는 서울시 API를 부를 수 없으므로 빠지는 경로가 없다.
- 재발 방지: 위 테스트가 `caplog`에 인증키 문자열이 없는지 검사한다. 예외 메시지 쪽은 `test_fetch_gives_up_after_retries_without_leaking_key`가 검사한다.
- 관련: F-001, D-008

최종 수정: 2026-11-23
