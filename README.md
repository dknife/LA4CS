# 쓸모 있는 선형대수 with NumPy — 웹북

『쓸모 있는 선형대수 with NumPy』(강영민, 박동규 지음 / (주)생능출판사)의 웹 에디션 저장소.
GitHub Pages로 `docs/`를 서비스한다. → https://dknife.github.io/LA4CS/

    docs/index.html          랜딩 페이지
    docs/book/front.html     표지·머릿말·이 책의 구성
    docs/book/chNN.html      1~13장
    docs/book/apx{a,b,c}.html 부록 A~C

## 구성

```
docs/
  index.html                 랜딩 페이지 (손으로 관리)
  book/
    book.css  book.js        본문 스타일·동작 (손으로 관리)
    pyrunner.js              Pyodide 실행기 (손으로 관리)
    grader.js                연습문제 채점 위젯 (손으로 관리)
    viewer.html              그림 확대 뷰어 (손으로 관리)
    chNN.html apx*.html      tex2html.py 가 생성
    img/chNN/figMM.svg       build_figures.py 가 생성
tools/
  tex2html.py                원고(.tex) -> HTML 변환기
  build_figures.py           본문 TikZ -> SVG 추출기
  fig_manifest.json          장별 그림 개수 (자동 생성)
```

`book.css`·`book.js`·`pyrunner.js`·`grader.js`·`viewer.html`은 **손으로 관리하는 파일**이다.
변환기가 만들지 않으므로 다시 빌드해도 덮어쓰이지 않는다.

## 로컬에서 보기

**`file://` 로 열면 코드 실행이 되지 않는다.** 모듈 워커와 `fetch` 가 `file://`
에서는 막히기 때문이며, `실행기를 불러오지 못했습니다: [object Event]` 오류가 난다.
반드시 HTTP 로 열어야 한다.

```bash
./serve.sh            # http://localhost:8899
./serve.sh 8000       # 포트 지정
```

## 빌드

원고는 이 저장소 밖에 있다. 기본 경로는 아래와 같고 환경변수로 바꿀 수 있다.

```bash
export LA4CS_TEX=~/.../저술_원고/선형대수/latex   # 원고 위치
export LA4CS_REPO=~/GitRepos/LA4CS                # 이 저장소 위치
```

```bash
# 1) 본문에 인라인으로 들어 있는 TikZ 그림을 SVG로 추출 (xelatex + pdftocairo 필요)
python3 tools/build_figures.py            # 전부
python3 tools/build_figures.py 7 9        # 특정 장만

# 2) 원고 -> HTML (시각화 모듈 lautils.py·tuvis.py 도 함께 복사된다)
python3 tools/tex2html.py

# 3) 이어지는 예제의 준비 코드 + 실행 불가 코드 표시
python3 tools/gen_run_preludes.py

# 4) 웹에서 실행되는 그대로 전부 돌려 확인 (실패 0이어야 한다)
cd docs/book && python3 ../../tools/check_web_run.py && cd ../..

# 5) 대화형(plotly) 예제는 실제 Pyodide 로 확인한다
mkdir -p /tmp/pyo && cd /tmp/pyo && npm install pyodide
node ~/GitRepos/LA4CS/tools/check_pyodide.mjs
```

`check_pyodide.mjs` 는 `pyrunner.js` 의 모듈 주입 블록을 **파일에서 잘라 내 그대로**
실행한다. 따로 흉내 낸 코드로 검사하면 제품과 어긋나 버그를 놓친다
(실제로 `tuvis.py` 를 심지 않은 버그를 그렇게 놓쳤다).

**원고를 고쳐도 자동으로 빌드·푸시하지 않는다.** 필요할 때 위 두 명령을 직접 돌린다.
그림이 든 장을 고쳤다면 `build_figures.py`를 먼저 돌려야 SVG 번호가 어긋나지 않는다.

## 이 책만의 처리

- **수식**: MathJax 3로 렌더링한다. 원고의 `\vv`, `\mm`, `\tp`, `\Rsp` 같은 매크로는
  파이썬에서 펼치지 않고 `tex2html.py`의 `MJ_MACROS`로 MathJax에 넘긴다.
  디스플레이 수식(`\[...\]`, `equation`, `align`)과 `bmatrix`가 든 인라인 수식은
  변환 전에 통째로 보호한다(그러지 않으면 `bmatrix`를 문서 환경으로 오인한다).
- **그림**: 이 책의 TikZ는 별도 파일이 아니라 본문에 직접 들어 있다.
  `build_figures.py`가 등장 순서대로 떼어 내 `img/chNN/figMM.svg`로 저장하고,
  `tex2html.py`가 같은 순서로 하나씩 꺼내 쓴다.
- **박스**: 정의(`defbox`)·정리(`thmbox`)·예제(`exbox`)·한 걸음 더(`stepbox`)가
  이 책에서 새로 쓰이며, 대응 CSS는 `book.css` 끝에 덧붙여 두었다.
- **코드 실행**: 본문 예제 대부분이 `from lautils import *` 로 시작한다. 브라우저 안에는
  그 파일이 없으므로 `pyrunner.js` 가 워커를 띄울 때 `lautils.py` 를 받아 파이썬
  파일시스템에 심고 numpy·matplotlib 을 함께 내려받는다.
- **이어지는 예제**: 앞 블록의 변수를 쓰는 코드는 `run-preludes.json` 에 준비 코드를
  담아 둔다(`gen_run_preludes.py` 생성). **코드를 고치면 해시가 바뀌므로 다시 돌려야 한다.**
  `book.js` 는 준비 코드를 `pre + code` 로 **구분자 없이** 이어 붙이므로 준비 코드는
  반드시 빈 줄로 끝나야 한다. 생성기가 그렇게 만들고, 끝에서 실제로 이어 붙여
  문법이 성립하는지 자체 점검한다.
- **대화형 3차원(plotly)도 웹에서 돌아간다.** `interactive=True` 가 든 코드를 만나면
  `pyrunner.js` 가 `micropip` 으로 plotly 를 받고(순수 파이썬 휠, 약 10MB, 처음 한 번),
  `Figure.show()` 를 가로채 두었다가 `to_json()` 으로 뽑아 메인 스레드에 보낸다.
  실제 그리기는 `book.js` 가 CDN 의 plotly.js 로 한다.
- `%%writefile` 같은 주피터 매직과 코랩 전용 코드만 `concept-codes.json` 에 올려
  '설명을 돕는 개념 코드' 안내를 표시한다.
- **주의**: Pyodide 에서는 pyplot 을 import 하기 전에 `matplotlib.use("Agg")` 를 정해야
  한다. 워커에는 DOM 이 없어 기본 백엔드가 `js.document` 를 찾다 실패한다.
  `ensurePyodide()` 가 초기화 때 처리한다.

## 라이선스

원고와 코드의 저작권은 지은이에게 있다.
