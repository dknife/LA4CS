#!/bin/bash
# 웹북을 로컬에서 확인한다.
#
# file:// 로 열면 실행기가 동작하지 않는다.
# 모듈 워커(new Worker(..., {type:'module'}))와 fetch 가 file:// 에서는
# 보안 정책으로 막히기 때문이다("실행기를 불러오지 못했습니다: [object Event]").
# 반드시 HTTP 로 열어야 한다.
PORT=${1:-8899}
cd "$(dirname "$0")/docs"
echo "http://localhost:$PORT/          (랜딩)"
echo "http://localhost:$PORT/book/ch01.html   (1장)"
python3 -m http.server "$PORT"
