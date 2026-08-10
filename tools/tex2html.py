# -*- coding: utf-8 -*-
"""알짜 선형대수 LaTeX -> HTML converter (web edition).

Reads ExpressLaTeX/chapters/chNN, emits docs/book/chNN.html with a fixed
left-sidebar TOC and a rendered content pane. Verbatim code environments
(pycode/pycodecap/pyout) are protected first; termout is LaTeX-escaped text.
"""
import html
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 원고(.tex) 위치 — 환경변수 LA4CS_TEX 로 덮어쓸 수 있다
TEX = Path(os.environ.get(
    "LA4CS_TEX",
    "~/Library/CloudStorage/OneDrive-개인/문서/YMKang_Work/저술_원고/선형대수/latex"
)).expanduser()
# 웹 에디션 저장소(dknife/PythonExpress) 클론 위치.
# 클론 위치는 기기마다 다르므로 홈 기준 상대 경로를 쓰고, 환경변수로 재정의할 수 있다.
REPO = Path(os.environ.get("LA4CS_REPO", "~/GitRepos/LA4CS")).expanduser()
OUT = REPO / "docs" / "book"
_mp = Path(__file__).resolve().parent / "fig_manifest.json"
MANIFEST = json.loads(_mp.read_text(encoding="utf-8")) if _mp.exists() else {}

CHAPTERS = {
    1: "선형대수와 도구", 2: "대규모 배열을 다루는 고성능 넘파이",
    3: "선형대수의 기본 자료: 스칼라, 벡터, 행렬", 4: "벡터를 다루는 기본적인 연산",
    5: "행렬을 다루는 기본적인 연산", 6: "역행렬: 되돌리는 변환",
    7: "행렬식과 선형변환", 8: "선형방정식의 풀이",
    9: "고유값과 고유벡터", 10: "행렬의 대각화",
    11: "특이값 분해", 12: "다양한 행렬 분해의 활용",
    13: "선형대수의 응용",
}
# 이 책은 파트를 나누지 않는다 (부록만 따로 묶인다)
PARTS = {}

# MathJax 가 직접 펼칠 수식 매크로 — 원고 preamble.tex 와 같은 정의
MJ_MACROS = r"""{
  vv: ['{\\boldsymbol{\\mathbf{#1}}}', 1],
  mm: ['{\\boldsymbol{\\mathbf{#1}}}', 1],
  tp: '{^{\\mathsf{T}}}',
  inv: '{^{-1}}',
  pinv: '{^{+}}',
  Id: '{\\boldsymbol{\\mathbf{I}}}',
  zerovec: '{\\boldsymbol{\\mathbf{0}}}',
  Real: '{\\mathbb{R}}',
  Rsp: ['{\\mathbb{R}^{#1}}', 1],
  Rmat: ['{\\mathbb{R}^{#1 \\times #2}}', 2],
  norm: ['{\\left\\lVert #1 \\right\\rVert}', 1],
  abs: ['{\\left\\lvert #1 \\right\\rvert}', 1],
  sca: ['{#1}', 1],
  rank: '{\\operatorname{rank}}',
  trace: '{\\operatorname{tr}}',
  diag: '{\\operatorname{diag}}',
  spn: '{\\operatorname{span}}',
  proj: '{\\operatorname{proj}}',
  Col: '{\\operatorname{Col}}',
  Nul: '{\\operatorname{Nul}}',
  Row: '{\\operatorname{Row}}',
  adj: '{\\operatorname{adj}}',
  argmin: '{\\operatorname*{arg\\,min}}',
  argmax: '{\\operatorname*{arg\\,max}}',
  mtwo: ['{\\begin{bmatrix}#1 & #2\\\\ #3 & #4\\end{bmatrix}}', 4],
  vtwo: ['{\\begin{bmatrix}#1\\\\ #2\\end{bmatrix}}', 2],
  vthree: ['{\\begin{bmatrix}#1\\\\ #2\\\\ #3\\end{bmatrix}}', 3],
  dash: '{\\;\\unicode{x2014}\\;}',
  ndash: '{\\unicode{x2013}}'
}"""

unknown = set()


# ---------------------------------------------------------------- utilities
def find_env(text, env, start=0):
    """Return (begin_idx, content_start, content_end, end_idx) of first env."""
    btag = f"\\begin{{{env}}}"
    etag = f"\\end{{{env}}}"
    i = text.find(btag, start)
    if i < 0:
        return None
    depth = 0
    j = i
    while True:
        nb = text.find(btag, j + 1)
        ne = text.find(etag, j + 1)
        if ne < 0:
            raise ValueError(f"unclosed {env}")
        if nb != -1 and nb < ne:
            depth += 1
            j = nb
        else:
            if depth == 0:
                return (i, i + len(btag), ne, ne + len(etag))
            depth -= 1
            j = ne


def grab_group(text, i):
    """text[i] == '{' -> return (content, next_index)."""
    assert text[i] == "{", text[i:i+30]
    depth = 0
    for k in range(i, len(text)):
        if text[k] == "{" and (k == 0 or text[k-1] != "\\"):
            depth += 1
        elif text[k] == "}" and text[k-1] != "\\":
            depth -= 1
            if depth == 0:
                return text[i+1:k], k + 1
    raise ValueError("unbalanced group")


def grab_opt(text, i):
    """Optional [..] at i -> (opt or None, next_index)."""
    if i < len(text) and text[i] == "[":
        k = text.find("]", i)
        return text[i+1:k], k + 1
    return None, i


# ---------------------------------------------------------------- converter
APPENDICES = [
    ("A", "실습 환경 준비", "appendix_a_setup"),
    ("B", "시각화 모듈 전체 소스", "appendix_b_tuvis"),
    ("C", "넘파이 선형대수 레퍼런스", "appendix_c_reference"),
]


class Chapter:
    def __init__(self, num, title=None, label=None):
        self.num = num
        self.title = title or CHAPTERS.get(num, "")
        self.label = label or str(num)
        self.secs = []          # [(anchor, "2.1 제목")]
        self.fig_n = 0
        self.tab_n = 0
        self.code_n = 0
        self.labels = {}        # label -> display number
        self.img_n = 0
        self.def_n = 0          # 정의 N.M
        self.thm_n = 0          # 정리 N.M
        self.exm_n = 0          # 예제 N.M
        self.fig_svg = 0        # 이 장에서 소비한 TikZ 그림 수
        self.protected = {}
        self.pid = 0

    # ---- protection of verbatim blocks
    def protect(self, key, htmlblock):
        self.pid += 1
        token = f"\x01{key}{self.pid}\x02"
        self.protected[token] = htmlblock
        return token

    def restore(self, text):
        for tok, blk in self.protected.items():
            text = text.replace(tok, blk)
        return text

    # ---- images
    def copy_image(self, latex_path):
        """Resolve via graphicspath, copy into OUT/img/chNN, return rel path."""
        cands = [TEX / latex_path, TEX / "figures" / latex_path,
                 TEX / "images" / latex_path]
        src = next((c for c in cands if c.exists()), None)
        if src is None:
            print(f"  !! image not found: {latex_path}")
            return ""
        self.img_n += 1
        ext = src.suffix.lower()
        dest_dir = OUT / "img" / f"ch{self.num:02d}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        name = f"ch{self.num:02d}_img{self.img_n:02d}{ext}"
        shutil.copyfile(src, dest_dir / name)
        return f"img/ch{self.num:02d}/{name}"


def esc(s):
    return html.escape(s, quote=False)


TT_UNESCAPE = [("\\#", "#"), ("\\%", "%"), ("\\_", "_"), ("\\&", "&"),
               ("\\$", "$"), ("\\{", "{"), ("\\}", "}"),
               ("\\,", " "), ("\\ ", " "), ("~", " "), ("--", "–")]

# \texttt{} 안에 쓰이는 문자 매크로 — 뒤따르는 빈 인수 {} 또는 공백까지 함께 삼킨다
TT_MACRO = {
    "textbackslash": "\\", "textasciitilde": "~", "textasciicircum": "^",
    "ldots": "…", "dots": "…", "ndash": "–", "dash": "—",
    "allowbreak": "", "^": "^",
}
TT_MACRO_RE = re.compile(
    r"\\(textbackslash|textasciitilde|textasciicircum|ldots|dots"
    r"|ndash|dash|allowbreak|\^)(?:\{\}|[ ])?")


# 매크로가 만들어 낸 글자(~ \ 등)가 뒤이은 escape 해제에 다시 걸리지 않도록
# 사설 영역 문자로 잠시 치환해 둔다
_TT_SLOT = {k: chr(0xE000 + n) for n, k in enumerate(TT_MACRO)}


def expand_tt_macros(s):
    """\\texttt{} 인수를 PDF와 같은 문자열로 펼친다."""
    # 1) 문자 매크로 — 결과가 다시 치환되지 않도록 자리표시자로 바꾼다
    s = TT_MACRO_RE.sub(lambda m: _TT_SLOT[m.group(1)], s)
    # 2) ligature 방지용 그룹 괄호(\texttt{>{>}>})는 PDF에서도 보이지 않으므로 지운다.
    #    \{ \} 로 escape 된 진짜 중괄호는 남긴다.
    s = re.sub(r"(?<!\\)[{}]", "", s)
    # 3) escape 해제
    for a, b in TT_UNESCAPE:
        s = s.replace(a, b)
    # 4) 자리표시자 되돌리기
    for k, slot in _TT_SLOT.items():
        s = s.replace(slot, TT_MACRO[k])
    return s


def tt_content(s):
    return esc(expand_tt_macros(s))


#  \texttt{>{>}>} 처럼 한 겹 중첩된 인수까지 벗겨 내기 위한 패턴
_ARG1 = r"\{((?:[^{}]|\{[^{}]*\})*)\}"


def latex_text(s):
    """Plain-text unescape for captions used inside attributes."""
    s = re.sub(r"\\texttt" + _ARG1, r"\1", s)
    s = re.sub(r"\\textbf" + _ARG1, r"\1", s)
    return expand_tt_macros(s)


INLINE_CMDS = {
    "textbf": ("<strong>", "</strong>"),
    "textit": ("<em>", "</em>"),
    "emph": ("<em>", "</em>"),
    "underline": ("<u>", "</u>"),
}


def inline(ch, s):
    """Convert inline LaTeX prose to HTML."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\x01":                       # protected token
            j = s.find("\x02", i)
            if j < 0:
                i += 1; continue
            out.append(s[i:j+1]); i = j + 1; continue
        if c == "%":                          # comment to EOL
            j = s.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if c == "$":                          # inline math
            j = s.find("$", i + 1)
            if j < 0:
                out.append("$"); i += 1; continue
            out.append(r"\(" + s[i+1:j] + r"\)")
            i = j + 1; continue
        if s.startswith("\\[", i):
            j = s.find("\\]", i)
            if j < 0:                      # 짝이 없으면 그대로 흘려보낸다
                out.append(esc("\\[")); i += 2; continue
            out.append(s[i:j+2]); i = j + 2; continue
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)\*?", s[i:])
            if not m:
                # escaped char or \\ or \, etc.
                nxt = s[i+1] if i + 1 < n else ""
                if nxt in "#%&_${}":
                    out.append(esc(nxt)); i += 2; continue
                if nxt == "\\":
                    out.append("<br>"); i += 2
                    m2 = re.match(r"\[[^\]]*\]", s[i:])
                    if m2: i += m2.end()
                    continue
                if nxt in ",;: ":
                    out.append(" "); i += 2; continue
                out.append(esc(nxt)); i += 2; continue
            cmd = m.group(1)
            i += m.end()
            # commands with one mandatory argument we render
            if cmd in INLINE_CMDS and i < n and s[i] == "{":
                arg, i = grab_group(s, i)
                o, cl = INLINE_CMDS[cmd]
                out.append(o + inline(ch, arg) + cl); continue
            if cmd == "texttt":
                arg, i = grab_group(s, i)
                out.append("<code>" + tt_content(arg) + "</code>"); continue
            if cmd == "textsuperscript":
                arg, i = grab_group(s, i)
                out.append('<sup class="term">' + esc(latex_text(arg)) + "</sup>"); continue
            if cmd == "checkmark":
                out.append(" ✓"); continue
            if cmd == "eqref":                     # 식 번호 참조 -> MathJax 에 맡긴다
                arg, i = grab_group(s, i)
                out.append("\\(\\eqref{" + arg + "}\\)"); continue
            if cmd == "nterm":                     # 용어 + 색인 (색인은 웹에서 무시)
                ko, i = grab_group(s, i)
                en, i = grab_group(s, i)
                out.append('<strong class="term-ko">' + inline(ch, ko) + "</strong>"
                           '<sup class="term">' + esc(latex_text(en)) + "</sup>"); continue
            if cmd == "np":                        # 넘파이 함수 이름
                arg, i = grab_group(s, i)
                out.append("<code>" + tt_content(arg) + "</code>"); continue
            if cmd == "solution":
                out.append('<div class="solution-label">풀이</div>'); continue
            if cmd == "chapmotif":                 # 챕터 도입 장식 — 웹에서는 생략
                for _ in range(4):
                    if i < n and s[i] == "{":
                        _, i = grab_group(s, i)
                continue
            if cmd == "appendixpart":
                continue
            if cmd == "term":
                ko, i = grab_group(s, i)
                en, i = grab_group(s, i)
                out.append('<strong class="term-ko">' + inline(ch, ko) + "</strong>"
                           '<sup class="term">' + esc(latex_text(en)) + "</sup>"); continue
            if cmd in ("index", "label", "phantomsection", "addcontentsline",
                       "vspace", "hspace", "nopagebreak", "enlargethispage",
                       "pagestyle", "thispagestyle", "captionsetup"):
                if cmd == "label" and i < n and s[i] == "{":
                    arg, i = grab_group(s, i)
                    continue
                # swallow arguments
                while i < n and s[i] in "{[":
                    if s[i] == "{": _, i = grab_group(s, i)
                    else: _, i = grab_opt(s, i)
                continue
            if cmd in ("ref", "pageref"):
                arg, i = grab_group(s, i)
                out.append(f"\x01REF:{arg}\x02"); continue
            if cmd == "url":
                arg, i = grab_group(s, i)
                out.append(f'<a href="{arg}" target="_blank">{esc(arg)}</a>'); continue
            if cmd in ("webfn", "webfns", "footnote"):
                arg, i = grab_group(s, i)
                out.append(' <span class="fn">(' + inline(ch, arg) + ")</span>"); continue
            if cmd == "dash":
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                out.append(" — "); continue
            if cmd == "ndash":
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                out.append("–"); continue
            if cmd == "thechapter":
                out.append(str(ch.num)); continue
            if cmd == "item":
                opt, i = grab_opt(s, i)
                out.append("\x01ITEM\x02"); continue
            if cmd == "diffitem":
                arg, i = grab_group(s, i)
                stars = {"1": '<span class="d1">★</span>',
                         "2": '<span class="d2">★★</span>',
                         "3": '<span class="d3">★★★</span>'}[arg.strip()]
                ch.ex_n = getattr(ch, "ex_n", 0) + 1
                out.append(f"\x01ITEM\x02\x01EX:{ch.ex_n}\x02"
                           f"<span class=\"diff\">{stars}</span> "); continue
            if cmd == "captionof":
                t, i = grab_group(s, i)
                cap, i = grab_group(s, i)
                if t == "codelisting":
                    out.append(f'<div class="listing-caption">코드 {ch.label}.\x01CN\x02: '
                               + inline(ch, cap) + "</div>")
                continue
            if cmd == "caption":
                cap, i = grab_group(s, i)
                out.append(f"\x01CAPTION:{cap}\x02"); continue
            if cmd == "tikzfig":
                _, i = grab_opt(s, i)
                arg, i = grab_group(s, i)
                rel = MANIFEST.get(arg) or MANIFEST.get(arg + ".tex")
                if rel is None:
                    key = arg[:-4] if arg.endswith(".tex") else arg
                    rel = MANIFEST.get(key)
                if rel is None:
                    print(f"  !! no svg for {arg}")
                    continue
                out.append(f'<img class="tikz" src="{rel}" alt="figure">'); continue
            if cmd in ("includegraphics", "figimg"):
                opt, i = grab_opt(s, i)
                arg, i = grab_group(s, i)
                rel = ch.copy_image(arg)
                cls = "shot" if cmd == "figimg" else "gfx"
                if rel:
                    out.append(f'<img class="{cls}" src="{rel}" alt="figure">')
                continue
            if cmd == "chapfig":
                opt, i = grab_opt(s, i)
                arg, i = grab_group(s, i)
                rel = ch.copy_image(arg)
                if rel:
                    out.append(f'<img class="chapfig" src="{rel}" alt="chapter art">')
                continue
            if cmd == "textbackslash":
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                out.append("\\"); continue
            if cmd in ("ldots", "cdots", "times", "to", "geq", "leq",
                       "textasciitilde", "rightarrow"):
                sym = {"ldots": "…", "cdots": "⋯", "times": "×", "to": "→",
                       "geq": "≥", "leq": "≤", "textasciitilde": "~",
                       "rightarrow": "→"}[cmd]
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                out.append(sym); continue
            if cmd in ("clearpage", "newpage", "cleardoublepage", "noindent",
                       "centering", "raggedright", "raggedleft", "small", "footnotesize",
                       "normalsize", "large", "Large", "scriptsize", "sffamily",
                       "rmfamily", "bfseries", "itshape", "ttfamily", "par",
                       "FloatBarrier", "hfill", "hline", "toprule", "midrule",
                       "bottomrule", "origquote", "arraystretch",
                       "selectfont", "linespread", "medskip", "smallskip", "bigskip"):
                continue
            if cmd == "textsf":
                arg, i = grab_group(s, i)
                out.append(inline(ch, arg)); continue
            if cmd in ("mbox", "text"):
                arg, i = grab_group(s, i)
                out.append(inline(ch, arg)); continue
            if cmd == "color":
                _, i = grab_group(s, i); continue
            if cmd == "rule":
                _, i = grab_opt(s, i)
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                continue
            if cmd == "fontsize":
                _, i = grab_group(s, i); _, i = grab_group(s, i); continue
            if cmd in ("renewcommand", "setlength", "setcounter"):
                for _ in range(2):
                    if i < n and s[i] == "{": _, i = grab_group(s, i)
                continue
            if cmd in ("enspace", "quad", "qquad", "hspace*"):
                if i < n and s[i] == "{": _, i = grab_group(s, i)
                out.append(" "); continue
            if cmd == "boxchip":
                colr, i = grab_group(s, i)
                txt, i = grab_group(s, i)
                hexmap = {"accentcopper": "#c86932", "cautioncolor": "#c35546",
                          "notecolor": "#6973af", "labcolor": "#288c7d",
                          "keypointmain": "#be9123", "deepblue": "#1a3a5c"}
                out.append(f'<span class="chipdemo" style="background:{hexmap.get(colr, "#888")}">'
                           + inline(ch, txt) + "</span>"); continue
            if cmd == "boxchipwithtitle":
                colr, i = grab_group(s, i)
                txt, i = grab_group(s, i)
                ttl, i = grab_group(s, i)
                hexmap = {"notecolor": "#6973af"}
                out.append(f'<span class="chipdemo" style="background:{hexmap.get(colr, "#888")}">'
                           + inline(ch, txt) + "</span> <strong>" + inline(ch, ttl) + "</strong>")
                continue
            unknown.add(cmd)
            # swallow a single brace group if present, render its content
            if i < n and s[i] == "{":
                arg, i = grab_group(s, i)
                out.append(inline(ch, arg))
            continue
        if c == "`":
            if s.startswith("``", i):
                out.append("“"); i += 2
            else:
                out.append("‘"); i += 1
            continue
        if c == "'":
            if s.startswith("''", i):
                out.append("”"); i += 2
            else:
                out.append("’"); i += 1
            continue
        if c == "~":
            out.append(" "); i += 1; continue
        if c in "{}":
            i += 1; continue          # bare grouping braces are invisible
        if c in "&<>":
            out.append(esc(c)); i += 1; continue
        out.append(c); i += 1
    return "".join(out)


def paragraphs(htmltext):
    """Split converted prose into <p> blocks, respecting block-level tokens."""
    blocks = re.split(r"\n\s*\n", htmltext)
    outp = []
    for b in blocks:
        t = b.strip()
        if not t:
            continue
        if t.startswith("\x01") and t.endswith("\x02") and t.count("\x01") == 1:
            outp.append(t)
        elif re.match(r"^<(h\d|div|figure|table|ul|ol|pre|img|details)", t):
            outp.append(t)
        else:
            outp.append(f"<p>{t}</p>")
    return "\n".join(outp)


def conv_list(ch, inner, ordered, opt):
    body = conv_body(ch, inner)
    # split on ITEM tokens
    parts = body.split("\x01ITEM\x02")
    items = [p.strip() for p in parts[1:] if p.strip()]
    lis_parts = []
    for p in items:
        m = re.match(r"\x01EX:(\d+)\x02", p)
        if m:
            # 연습문제 항목: 채점 위젯(grader.js)이 매달릴 수 있게 ID 부여
            p = p[m.end():]
            lis_parts.append(f'<li class="ex-item" data-ex="{m.group(1)}">{p}</li>')
        else:
            lis_parts.append(f"<li>{p}</li>")
    lis = "\n".join(lis_parts)
    if ordered:
        typ = ""
        if opt and "alph" in opt: typ = ' type="a"'
        return f"<ol{typ}>\n{lis}\n</ol>"
    return f"<ul>\n{lis}\n</ul>"


def conv_table(ch, inner, caption):
    # find tabular-ish env
    for tenv in ("tabularx", "tabular*", "tabular"):
        f = find_env(inner, tenv)
        if f:
            break
    if not f:
        return ""
    tb = inner[f[1]:f[2]]
    # drop width/colspec args at start
    k = 0
    groups = 0
    while k < len(tb) and groups < 2:
        if tb[k] == "{":
            _, k = grab_group(tb, k); groups += 1
        elif tb[k] in " \n":
            k += 1
        else:
            break
    tb = tb[k:]
    tb = re.sub(r"\\(toprule|midrule|bottomrule|hline)", "", tb)
    rows = [r.strip() for r in re.split(r"\\\\", tb) if r.strip()]
    html_rows = []
    for ri, row in enumerate(rows):
        cells = re.split(r"(?<!\\)&", row)
        tag = "th" if ri == 0 else "td"
        html_rows.append("<tr>" + "".join(
            f"<{tag}>{inline(ch, c.strip())}</{tag}>" for c in cells) + "</tr>")
    cap_html = ""
    if caption:
        ch.tab_n += 1
        cap_html = (f'<div class="table-caption">표 {ch.label}.{ch.tab_n}: '
                    + inline(ch, caption) + "</div>")
    return (f'<div class="table-wrap">{cap_html}<table>'
            + "".join(html_rows) + "</table></div>")


BOXES = {
    "keypoint": ("box keypoint", "요점", None),
    "caution": ("box caution", "주의", None),
}
# 제목 인수를 하나 받는 박스: 환경 이름 -> (css class, chip 라벨)
TITLED_BOXES = {
    "notebox": ("box note", "잠깐"),
    "stepbox": ("box step", "한 걸음 더"),
}
# 번호가 붙는 박스: 환경 이름 -> (css class, 라벨, Chapter 속성명)
NUMBERED_BOXES = {
    "defbox": ("box defbox", "정의", "def_n"),
    "thmbox": ("box thmbox", "정리", "thm_n"),
    "exbox": ("box exbox", "예제", "exm_n"),
}


def conv_body(ch, text):
    """Convert a body of LaTeX (may contain environments) to HTML."""
    out = []
    pos = 0
    env_re = re.compile(r"\\begin\{([a-zA-Z*]+)\}")
    while True:
        m = env_re.search(text, pos)
        if not m:
            out.append(inline(ch, text[pos:]))
            break
        env = m.group(1)
        f = find_env(text, env, m.start())
        b, cs, ce, e = f
        out.append(inline(ch, text[pos:b]))
        inner = text[cs:ce]
        i2 = 0
        # options / args after \begin{env}
        opt, i2 = grab_opt(inner, 0)
        if env in ("itemize", "enumerate"):
            out.append(conv_list(ch, inner[i2:], env == "enumerate", opt))
        elif env in BOXES:
            cls, chip, _ = BOXES[env]
            out.append(f'<div class="{cls}"><span class="chip">{chip}</span>'
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div>")
        elif env in TITLED_BOXES:
            cls, chip = TITLED_BOXES[env]
            title, i2 = grab_group(inner, i2)
            out.append(f'<div class="{cls}"><span class="chip">{chip}</span>'
                       f'<span class="box-title">{inline(ch, title)}</span>'
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div>")
        elif env in NUMBERED_BOXES:
            cls, lab, attr = NUMBERED_BOXES[env]
            setattr(ch, attr, getattr(ch, attr) + 1)
            no = f"{ch.label}.{getattr(ch, attr)}"
            title, i2 = grab_group(inner, i2)
            out.append(f'<div class="{cls}">'
                       f'<span class="chip">{lab} {no}</span>'
                       f'<span class="box-title">{inline(ch, title)}</span>'
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div>")
        elif env == "labbox":
            title, i2 = grab_group(inner, i2)
            out.append('<div class="box lab"><div class="lab-title">'
                       + inline(ch, title) + "</div>"
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div>")
        elif env == "summary":
            ch.secs.append((f"summary", f"{ch.num}장 요약"))
            # 기본은 접힌 상태 — 제목 줄을 눌러 펼친다 (연습문제와 같은 패턴)
            out.append(f'<details class="box summary" id="summary">'
                       f'<summary class="box-head">{ch.num}장 요약</summary>'
                       f'<div class="sum-body">'
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div></details>")
        elif env == "exercisebox":
            ch.secs.append((f"exercises", "연습문제"))
            # 기본은 접힌 상태 — 제목 줄을 눌러 펼친다 (goals 박스와 같은 details 패턴)
            out.append(f'<details class="box exercise" id="exercises">'
                       f'<summary class="box-head">{ch.num}장 연습문제</summary>'
                       f'<div class="ex-body">'
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div></details>")
        elif env == "chapterintro":
            body = re.sub(r"^\s*\{[^\n]*이 장을 마치면\}\\par(\\vspace\{[^{}]*\})?",
                          "", inner[i2:].strip())
            # 학습 목표는 접어 두고 독자가 펼쳐 보게 한다 (<details>는 JS가 필요 없다)
            out.append('<details class="box goals">'
                       '<summary class="box-head">이 장을 마치면</summary>'
                       '<div class="goals-body">'
                       + paragraphs(conv_body(ch, body)) + "</div></details>")
        elif env == "tikzpicture":
            # 원고의 TikZ 그림은 build_figures.py 가 미리 SVG 로 만들어 둔다.
            # 등장 순서가 같으므로 순서대로 하나씩 꺼내 쓴다.
            ch.fig_svg += 1
            rel = f"img/ch{ch.num:02d}/fig{ch.fig_svg:02d}.svg"
            if (OUT / rel).exists():
                out.append(f'<img class="tikz" src="{rel}" alt="figure">')
            else:
                print(f"  !! svg 없음: {rel}")
        elif env == "chapterquote":
            pass  # print-only panel
        elif env in ("figure", "figure*"):
            capm = re.search(r"\\caption\{", inner)
            caption = None
            rest = inner
            if capm:
                caption, k = grab_group(inner, capm.end() - 1)
                rest = inner[:capm.start()] + inner[k:]
            labm = re.search(r"\\label\{([^{}]+)\}", rest)
            label = labm.group(1) if labm else None
            rest = re.sub(r"\\label\{[^{}]+\}", "", rest)
            ch.fig_n += 1
            num = f"{ch.label}.{ch.fig_n}"
            if label:
                ch.labels[label] = num
            body = conv_body(ch, rest[grab_opt(rest, 0)[1]:] if rest.startswith("[") else rest)
            caph = (f'<figcaption>그림 {num}: ' + inline(ch, caption) + "</figcaption>") if caption else ""
            out.append(f'<figure class="fig">{body}{caph}</figure>')
        elif env in ("table", "table*"):
            capm = re.search(r"\\caption\{", inner)
            caption = None
            if capm:
                caption, _ = grab_group(inner, capm.end() - 1)
            labm = re.search(r"\\label\{([^{}]+)\}", inner)
            if labm:
                ch.labels[labm.group(1)] = f"{ch.label}.{ch.tab_n + 1}"
            out.append(conv_table(ch, inner, caption))
        elif env in ("tabularx", "tabular"):
            out.append(conv_table(ch, text[b:e], None))
        elif env == "center":
            out.append('<div class="center">'
                       + paragraphs(conv_body(ch, inner)) + "</div>")
        elif env == "minipage":
            _, i3 = grab_group(inner, i2)
            out.append(paragraphs(conv_body(ch, inner[i3:])))
        elif env == "termout":
            body = inner
            # 줄 끝 `\\`는 그 자체가 줄바꿈이다. 원본에 실제 개행이 뒤따르면
            # 개행이 두 번 생겨 빈 줄이 되므로 하나로 합친다.
            body = re.sub(r"\\\\(\[[^\]]*\])?[ \t]*\n", "\n", body)
            body = re.sub(r"\\\\(\[[^\]]*\])?", "\n", body)
            body = re.sub(r"\\texttt\{([^{}]*)\}", r"\1", body)
            for a, bb in TT_UNESCAPE[:-1]:
                body = body.replace(a, bb)
            lines = []
            for ln in body.splitlines():
                # 들여쓰기(~~~~)는 살리고 오른쪽 공백만 정리한다
                ln = ln.rstrip()
                # unwrap LaTeX grouping braces protecting lines starting with [
                m2 = re.match(r"^(\s*)\{(\[.*\])\}$", ln)
                if m2:
                    ln = m2.group(1) + m2.group(2)
                lines.append(ln)
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()
            # 빈 줄이 남으면 paragraphs()가 블록을 쪼개 <p>를 끼워 넣는다.
            # (그 <p>는 어두운 본문 색을 물려받아 검은 배경에서 안 보인다)
            text_block = "\n".join(lines)
            text_block = re.sub(r"\n[ \t]*\n+", "\n\n", text_block)
            out.append('<pre class="termout">'
                       + esc(text_block).replace("\n\n", "\n&#160;\n")
                       + "</pre>")
        elif env == "bodyquote":
            out.append('<blockquote class="bodyquote">'
                       + paragraphs(conv_body(ch, inner)) + "</blockquote>")
        elif env == "tcolorbox":
            out.append('<div class="box construct">'
                       + paragraphs(conv_body(ch, inner[i2:])) + "</div>")
        elif env in ("subfigure",):
            _, i3 = grab_group(inner, i2) if inner[i2:i2+1] == "{" else (None, i2)
            out.append(conv_body(ch, inner[i3:]))
        else:
            unknown.add("env:" + env)
            out.append(conv_body(ch, inner))
        pos = e
    return "".join(out)


def protect_code(ch, text):
    """Replace pycode/pycodecap/filecode/pyout/pyerr blocks with placeholders."""
    for env in ("pycodecap", "filecode", "pyfile", "pycode", "pyout", "pyerr"):
        while True:
            f = find_env(text, env)
            if not f:
                break
            b, cs, ce, e = f
            inner = text[cs:ce]
            if env == "pyfile":
                # 독자가 직접 만들어 저장하는 파이썬 파일
                fname, k = grab_group(inner, inner.find("{"))
                code = inner[k:]
                block = ('<div class="filecode-wrap"><div class="file-label">'
                         + esc(latex_text(fname)) + '</div>'
                         '<pre class="filecode"><code class="language-python">'
                         + esc(code.strip("\n")) + "</code></pre></div>")
            elif env == "filecode":
                # 파일 소스(HTML 템플릿 등): 파일명 라벨 + html 하이라이트,
                # 실행 버튼은 없음 (book.js가 filecode 클래스로 구분)
                fname, k = grab_group(inner, inner.find("{"))
                code = inner[k:]
                block = ('<div class="filecode-wrap"><div class="file-label">'
                         + esc(fname) + '</div>'
                         '<pre class="filecode"><code class="language-html">'
                         + esc(code.strip("\n")) + "</code></pre></div>")
            elif env == "pycodecap":
                cap, k = grab_group(inner, inner.find("{"))
                code = inner[k:]
                block = ('<div class="listing"><pre class="line-numbers"><code class="language-python">'
                         + esc(code.strip("\n")) + "</code></pre>"
                         f'<div class="listing-caption">코드 {ch.label}.\x01CN\x02: '
                         + inline(ch, cap) + "</div></div>")
            elif env == "pycode":
                block = ('<pre class="line-numbers"><code class="language-python">'
                         + esc(inner.strip("\n")) + "</code></pre>")
            else:
                cls = "pyout pyerr" if env == "pyerr" else "pyout"
                block = f'<pre class="{cls}">' + esc(inner.strip("\n")) + "</pre>"
            text = text[:b] + ch.protect(env, block) + text[e:]
    return text


MATH_ENVS = ("equation", "equation*", "align", "align*",
             "gather", "gather*", "multline", "multline*")


def protect_math(ch, text):
    r"""디스플레이 수식을 통째로 보호한다.

    \[ ... \] 안에는 bmatrix, cases 같은 환경이 들어 있는데, 보호하지 않으면
    conv_body 가 그것을 문서 환경으로 오인해 수식을 쪼개 버린다(그리고 짝이
    맞지 않는 \[ 때문에 무한 루프에 빠진다). 그래서 코드와 같은 방식으로
    먼저 자리표시자로 바꿔 둔다. 실제 렌더링은 MathJax 가 한다.
    """
    # (1) \[ ... \]
    i = 0
    while True:
        b = text.find("\\[", i)
        if b < 0:
            break
        # 줄바꿈 \\[6pt] 의 일부인 `\[` 는 수식이 아니다
        if b > 0 and text[b - 1] == "\\":
            i = b + 2
            continue
        e = text.find("\\]", b + 2)
        if e < 0:                       # 짝이 없으면 건드리지 않는다
            i = b + 2
            continue
        body = text[b + 2:e]
        tok = ch.protect("math", '<div class="mathblock">\\[' + body + '\\]</div>')
        text = text[:b] + tok + text[e + 2:]
        i = b + len(tok)
    # (2) $ ... $  — 인라인 수식 안에도 bmatrix 같은 환경이 들어간다.
    #     보호하지 않으면 conv_body 가 그것을 문서 환경으로 오인해 수식을 쪼갠다.
    i = 0
    while True:
        b = text.find("$", i)
        if b < 0:
            break
        if b > 0 and text[b - 1] == "\\":      # \$ 는 달러 기호
            i = b + 1
            continue
        e = b + 1
        while True:
            e = text.find("$", e)
            if e < 0 or text[e - 1] != "\\":
                break
            e += 1
        if e < 0:
            break
        body = text[b + 1:e]
        if "\\begin{" in body:                  # 환경이 든 것만 보호하면 충분하다
            tok = ch.protect("imath", "\\(" + body + "\\)")
            text = text[:b] + tok + text[e + 1:]
            i = b + len(tok)
        else:
            i = e + 1

    # (3) equation / align / gather ...
    for env in MATH_ENVS:
        while True:
            f = find_env(text, env)
            if not f:
                break
            b, cs, ce, e = f
            body = text[cs:ce]
            src = "\\begin{" + env + "}" + body + "\\end{" + env + "}"
            tok = ch.protect("math", '<div class="mathblock">' + src + "</div>")
            text = text[:b] + tok + text[e:]
    return text


def convert_chapter(num):
    ch = Chapter(num)
    chdir = TEX / "chapters" / f"ch{num:02d}"
    main = (chdir / f"ch{num:02d}.tex").read_text(encoding="utf-8")

    # inline the \input files
    def repl_input(m):
        p = TEX / (m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex")
        return "\n" + p.read_text(encoding="utf-8") + "\n"
    src = re.sub(r"\\input\{([^{}]+)\}", repl_input, main)
    src = re.sub(r"^%.*$", "", src, flags=re.M)
    src = src.replace("\\char`\\\\", "\\textbackslash{}")
    src = re.sub(r"\\char`\\(.)", r"\1", src)
    src = re.sub(r"\\partbanner\{[^{}]*\}\{[^{}]*\}", "", src)
    src = re.sub(r"\\rowcolor\{[^{}]*\}", "", src)   # 표 머리행 배경색은 웹에선 CSS th가 담당
    src = re.sub(r"\\chapter\{([^{}]*)\}", "", src)

    # sections -> headings with anchors (before code protection is fine)
    def repl_section(m):
        title = m.group(1)
        sn = len([s for s in ch.secs if s[0].startswith("sec")]) + 1
        anchor = f"sec{sn}"
        ch.secs.append((anchor, f"{num}.{sn} {latex_text(title)}"))
        return f'\n\n\x01H2:{anchor}:{num}.{sn} {title}\x02\n\n'
    NEST = r"((?:[^{}]|\{[^{}]*\})*)"
    src = re.sub(r"\\section\{" + NEST + r"\}", repl_section, src)
    src = re.sub(r"\\subsection\*?\{" + NEST + r"\}",
                 lambda m: f"\n\n\x01H3:{m.group(1)}\x02\n\n", src)
    src = re.sub(r"\\subsubsection\*?\{" + NEST + r"\}",
                 lambda m: f"\n\n\x01H4:{m.group(1)}\x02\n\n", src)

    src = protect_code(ch, src)
    src = protect_math(ch, src)
    # labs anchor
    src = src.replace("\\begin{labbox}", "\x01ANCHOR:labs\x02\\begin{labbox}", 1)
    if "\\begin{labbox}" in src:
        ch.secs.append(("labs", f"실습을 통한 개념 정리"))
        # keep secs order: move labs before summary/exercises later (they append in order anyway)

    body = conv_body(ch, src)
    body = paragraphs(body)
    body = ch.restore(body)

    # heading tokens
    body = re.sub(r"\x01H2:([^:]+):([^\x02]+)\x02",
                  lambda m: f'<h2 id="{m.group(1)}">{inline(ch, m.group(2))}</h2>', body)
    body = re.sub(r"\x01H3:([^\x02]+)\x02",
                  lambda m: f"<h3>{inline(ch, m.group(1))}</h3>", body)
    body = re.sub(r"\x01H4:([^\x02]+)\x02",
                  lambda m: f"<h4>{inline(ch, m.group(1))}</h4>", body)
    body = body.replace("\x01ANCHOR:labs\x02", '<span id="labs"></span>')
    # sequential code-listing numbers in final document order
    cn = [0]
    def next_cn(m):
        cn[0] += 1
        return str(cn[0])
    body = re.sub("\x01CN\x02", next_cn, body)
    # refs
    body = re.sub(r"\x01REF:([^\x02]+)\x02",
                  lambda m: ch.labels.get(m.group(1), "?"), body)
    # leftover caption tokens (tables handled separately)
    body = re.sub(r"\x01CAPTION:[^\x02]*\x02", "", body)
    body = re.sub(r"\x01ITEM\x02", "", body)
    body = re.sub(r"\x01EX:\d+\x02", "", body)
    # fix secs ordering: labs appended at protect time may be out of order; rebuild
    ordered = [s for s in ch.secs if s[0].startswith("sec")]
    for key in ("labs", "summary", "exercises"):
        for s in ch.secs:
            if s[0] == key and s not in ordered:
                ordered.append(s)
    ch.secs = ordered
    return ch, body


# ---------------------------------------------------------------- rendering
def sidebar_html(all_meta, current):
    parts_html = []
    tail = ['<div class="nav-part">부록</div>']
    for letter, title, _fn in APPENDICES:
        cur = " current" if current == letter else ""
        tail.append(
            f'<div class="nav-ch{cur}">'
            f'<a class="nav-ch-link" href="apx{letter.lower()}.html">'
            f'<span class="nav-num">{letter}</span> {title}</a>')
        if current == letter and letter in all_meta:
            items = "".join(
                f'<a class="nav-sec" href="apx{letter.lower()}.html#{a}">{t}</a>'
                for a, t in all_meta[letter][0])
            tail.append(f'<div class="nav-secs">{items}</div>')
        tail.append("</div>")
    for n in range(1, 14):
        secs, title = all_meta[n]
        if n in PARTS:
            parts_html.append(f'<div class="nav-part">Part {PARTS[n]}</div>')
        cur = " current" if n == current else ""
        if n == 1:
            fcur = " current" if current == 0 else ""
            parts_html.insert(0,
                f'<div class="nav-ch{fcur}"><a class="nav-ch-link" href="front.html">'
                f'<span class="nav-num">&#128214;</span> 표지·머릿말</a></div>')
        parts_html.append(
            f'<div class="nav-ch{cur}">'
            f'<a class="nav-ch-link" href="ch{n:02d}.html">'
            f'<span class="nav-num">{n:02d}</span> {title}</a>')
        if n == current:
            items = "".join(
                f'<a class="nav-sec" href="ch{n:02d}.html#{a}">{t}</a>'
                for a, t in secs)
            parts_html.append(f'<div class="nav-secs">{items}</div>')
        parts_html.append("</div>")
    return "\n".join(parts_html + tail)


def render_page(ch, body, all_meta):
    prev_link = (f'<a class="pager prev" href="ch{ch.num-1:02d}.html">&larr; '
                 f'{ch.num-1}장</a>') if ch.num > 1 else \
        '<a class="pager prev" href="front.html">&larr; 표지·머릿말</a>'
    next_link = (f'<a class="pager next" href="ch{ch.num+1:02d}.html">'
                 f'{ch.num+1}장 &rarr;</a>') if ch.num < 12 else \
        '<a class="pager next" href="apxa.html">부록 A &rarr;</a>'
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ch.num}장 {ch.title} — 알짜 선형대수</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700;800&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<link rel="stylesheet" href="book.css">
<script>MathJax = {{tex: {{inlineMath: [['\\\\(', '\\\\)']], macros: MJ_MACROS, tags: 'ams'}}, svg: {{fontCache: 'global'}}}};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/line-numbers/prism-line-numbers.min.css">
</head>
<body>
<header class="topbar">
  <a class="home" href="../index.html">&#8962; 홈</a>
  <span class="book-title">알짜 선형대수</span>
  <span class="ch-indicator">{ch.num}장 {ch.title}</span>
  <button class="nav-toggle" onclick="document.body.classList.toggle('nav-open')">목차</button>
</header>
<div class="layout">
<nav class="sidebar">
{sidebar_html(all_meta, ch.num)}
</nav>
<main class="content">
<div class="chapter-head">
  <div class="ch-label">CHAPTER {ch.num:02d}</div>
  <h1>{ch.title}</h1>
</div>
{body}
<div class="pager-row">{prev_link}{next_link}</div>
</main>
</div>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/line-numbers/prism-line-numbers.min.js"></script>
<script src="book.js"></script>
<script src="grader.js"></script>
</body>
</html>
"""


def convert_appendix(idx):
    """Convert one appendix (idx 0..2) to (ch, body_html)."""
    letter, title, fname = APPENDICES[idx]
    ch = Chapter(13 + idx, title=title, label=letter)
    src = (TEX / "backmatter" / f"{fname}.tex").read_text(encoding="utf-8")
    src = re.sub(r"^%.*$", "", src, flags=re.M)
    src = src.replace("\\char`\\\\", "\\textbackslash{}")
    src = re.sub(r"\\char`\\(.)", r"\1", src)
    src = re.sub(r"\\chapter\{((?:[^{}]|\{[^{}]*\})*)\}", "", src)

    NEST = r"((?:[^{}]|\{[^{}]*\})*)"
    def repl_asec(m):
        t = m.group(1)
        sn = len(ch.secs) + 1
        anchor = f"sec{sn}"
        ch.secs.append((anchor, latex_text(t)))
        return f"\n\n\x01H2:{anchor}:{t}\x02\n\n"
    src = re.sub(r"\\section\*?\{" + NEST + r"\}", repl_asec, src)
    src = re.sub(r"\\subsection\*?\{" + NEST + r"\}",
                 lambda m: f"\n\n\x01H3:{m.group(1)}\x02\n\n", src)
    src = re.sub(r"\\subsubsection\*?\{" + NEST + r"\}",
                 lambda m: f"\n\n\x01H4:{m.group(1)}\x02\n\n", src)

    src = protect_code(ch, src)
    src = protect_math(ch, src)
    body = paragraphs(conv_body(ch, src))
    body = ch.restore(body)
    body = re.sub(r"\x01H2:([^:]+):([^\x02]+)\x02",
                  lambda m: f'<h2 id="{m.group(1)}">{inline(ch, m.group(2))}</h2>', body)
    body = re.sub(r"\x01H3:([^\x02]+)\x02",
                  lambda m: f"<h3>{inline(ch, m.group(1))}</h3>", body)
    body = re.sub(r"\x01H4:([^\x02]+)\x02",
                  lambda m: f"<h4>{inline(ch, m.group(1))}</h4>", body)
    body = re.sub(r"\x01REF:([^\x02]+)\x02",
                  lambda m: ch.labels.get(m.group(1), "?"), body)
    body = re.sub(r"\x01CAPTION:[^\x02]*\x02", "", body)
    body = re.sub(r"\x01ITEM\x02", "", body)
    body = re.sub(r"\x01EX:\d+\x02", "", body)
    cn = [0]
    body = re.sub("\x01CN\x02", lambda m: (cn.__setitem__(0, cn[0] + 1), str(cn[0]))[1], body)
    return ch, body


def render_appendix(idx, ch, body, all_meta):
    letter = APPENDICES[idx][0]
    if idx == 0:
        prev_link = '<a class="pager prev" href="ch12.html">&larr; 12장</a>'
    else:
        pl = APPENDICES[idx - 1][0]
        prev_link = f'<a class="pager prev" href="apx{pl.lower()}.html">&larr; 부록 {pl}</a>'
    if idx < len(APPENDICES) - 1:
        nl = APPENDICES[idx + 1][0]
        next_link = f'<a class="pager next" href="apx{nl.lower()}.html">부록 {nl} &rarr;</a>'
    else:
        next_link = "<span></span>"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>부록 {letter} {ch.title} — 알짜 선형대수</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700;800&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<link rel="stylesheet" href="book.css">
<script>MathJax = {{tex: {{inlineMath: [['\\\\(', '\\\\)']], macros: MJ_MACROS, tags: 'ams'}}, svg: {{fontCache: 'global'}}}};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/line-numbers/prism-line-numbers.min.css">
</head>
<body>
<header class="topbar">
  <a class="home" href="../index.html">&#8962; 홈</a>
  <span class="book-title">알짜 선형대수</span>
  <span class="ch-indicator">부록 {letter} {ch.title}</span>
  <button class="nav-toggle" onclick="document.body.classList.toggle('nav-open')">목차</button>
</header>
<div class="layout">
<nav class="sidebar">
{sidebar_html(all_meta, letter)}
</nav>
<main class="content">
<div class="chapter-head">
  <div class="ch-label">APPENDIX {letter}</div>
  <h1>{ch.title}</h1>
</div>
{body}
<div class="pager-row">{prev_link}{next_link}</div>
</main>
</div>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/line-numbers/prism-line-numbers.min.js"></script>
<script src="book.js"></script>
</body>
</html>
"""


def convert_preface():
    """Convert frontmatter/preface.tex into the front page body."""
    ch = Chapter(1)          # dummy context for inline conversion
    ch.num = 0
    src = (TEX / "frontmatter" / "preface.tex").read_text(encoding="utf-8")
    src = re.sub(r"^%.*$", "", src, flags=re.M)
    src = re.sub(r"\\prefacebegin|\\prefaceend|\\chapter\{[^{}]*\}", "", src)
    src = src.replace("\\hfill 저자 일동", "\x01SIGNOFF\x02")
    # split at \clearpage: part 1 = 머릿말, part 2 = 이 책의 구성
    parts = re.split(r"\\clearpage", src, maxsplit=1)
    preface_html = paragraphs(conv_body(ch, parts[0]))
    preface_html = preface_html.replace(
        "<p>\x01SIGNOFF\x02</p>", '<p class="signoff">저자 일동</p>').replace(
        "\x01SIGNOFF\x02", '<p class="signoff">저자 일동</p>')
    구성 = parts[1] if len(parts) > 1 else ""
    구성 = 구성.replace("이 책의 구성\\par", "\x01H2X\x02")
    # 소제목 라인: \noindent{\fontsize... 제목} → h3 token
    구성 = re.sub(
        r"\\noindent\{\\fontsize\{[^{}]*\}\{[^{}]*\}\\selectfont\\sffamily\\bfseries ([^{}]*)\}",
        lambda m: f"\n\n\x01H3:{m.group(1)}\x02\n\n", 구성)
    구성_html = paragraphs(conv_body(ch, 구성))
    구성_html = 구성_html.replace("\x01H2X\x02", "")
    구성_html = re.sub(r"\x01H3:([^\x02]+)\x02",
                     lambda m: f"<h3>{m.group(1)}</h3>", 구성_html)
    구성_html = re.sub(r"\x01ITEM\x02", "", 구성_html)
    return preface_html, 구성_html


def render_front(preface_html, 구성_html, all_meta):
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>표지·머릿말 — 알짜 선형대수</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700;800&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<link rel="stylesheet" href="book.css">
<script>MathJax = {{tex: {{inlineMath: [['\\\\(', '\\\\)']], macros: MJ_MACROS, tags: 'ams'}}, svg: {{fontCache: 'global'}}}};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
</head>
<body>
<header class="topbar">
  <a class="home" href="../index.html">&#8962; 홈</a>
  <span class="book-title">알짜 선형대수</span>
  <span class="ch-indicator">표지·머릿말</span>
  <button class="nav-toggle" onclick="document.body.classList.toggle('nav-open')">목차</button>
</header>
<div class="layout">
<nav class="sidebar">
{sidebar_html(all_meta, 0)}
</nav>
<main class="content">
<div class="cover-wrap">
  <img class="cover" src="img/cover.png" alt="알짜 선형대수 표지">
</div>
<div class="chapter-head">
  <div class="ch-label">PREFACE</div>
  <h1>머릿말</h1>
</div>
{preface_html}
<h2>이 책의 구성</h2>
{구성_html}
<div class="pager-row"><span></span>
<a class="pager next" href="ch01.html">1장 &rarr;</a></div>
</main>
</div>
<script src="book.js"></script>
</body>
</html>
"""


def build_cover():
    """Render page 1 of the compiled book PDF as the cover image."""
    import subprocess
    pdf = TEX / "main.pdf"
    if not pdf.exists():
        print("  !! main.pdf not found; cover skipped")
        return
    tmp = OUT / "img" / "coverpage"
    try:
        # 컴파일 중이라 main.pdf가 미완성이면 표지만 건너뛴다 (본문은 이미 생성됨)
        subprocess.run(["pdftoppm", "-png", "-r", "140", "-f", "1", "-l", "1",
                        str(pdf), str(tmp)], check=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print("  !! cover render failed; kept previous cover.png (%s)" % e)
        return
    made = list(OUT.glob("img/coverpage-*.png")) + list(OUT.glob("img/coverpage-*.PNG"))
    if made:
        dest = OUT / "img" / "cover.png"
        if dest.exists():
            dest.unlink()
        made[0].rename(dest)
        print("cover ->", dest)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    meta = {}
    for n in range(1, 14):
        print(f"ch{n:02d}...")
        ch, body = convert_chapter(n)
        results[n] = (ch, body)
        meta[n] = (ch.secs, ch.title)
    for n, (ch, body) in results.items():
        (OUT / f"ch{n:02d}.html").write_text(
            render_page(ch, body, meta), encoding="utf-8")
    for idx in range(len(APPENDICES)):
        letter = APPENDICES[idx][0]
        print(f"apx{letter}...")
        ach, abody = convert_appendix(idx)
        meta[letter] = (ach.secs, ach.title)
        results[letter] = (idx, ach, abody)
    for letter, _t, _f in APPENDICES:
        idx, ach, abody = results[letter]
        (OUT / f"apx{letter.lower()}.html").write_text(
            render_appendix(idx, ach, abody, meta), encoding="utf-8")
    # 웹 실행기(Pyodide)가 파이썬 파일시스템에 심을 시각화 모듈
    for name in ("tuvis.py",):
        src = TEX / "code" / name
        if src.exists():
            shutil.copyfile(src, OUT / name)
    print("tuvis.py 복사 (웹 실행기용)")

    build_cover()
    pre, gu = convert_preface()
    (OUT / "front.html").write_text(render_front(pre, gu, meta), encoding="utf-8")

    # 페이지 템플릿에는 매크로 정의를 이름으로만 적어 두었다 -> 실제 정의로 바꾼다
    fixed = 0
    for f in OUT.glob("*.html"):
        t = f.read_text(encoding="utf-8")
        if "macros: MJ_MACROS" in t:
            f.write_text(t.replace("macros: MJ_MACROS", "macros: " + MJ_MACROS),
                         encoding="utf-8")
            fixed += 1
    print(f"MathJax 매크로 주입: {fixed}개 페이지")
    print("unknown commands:", sorted(unknown))


if __name__ == "__main__":
    main()
