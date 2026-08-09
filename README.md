# 쓸모 있는 선형대수 with NumPy — 웹북

『쓸모 있는 선형대수 with NumPy』(강영민)의 웹 에디션 저장소.
GitHub Pages로 `docs/`를 서비스한다.

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

# 2) 원고 -> HTML
python3 tools/tex2html.py
```

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

## 라이선스

원고와 코드의 저작권은 지은이에게 있다.
