#!/usr/bin/env python3
"""build_figures.py — 원고 안의 TikZ 그림을 SVG로 뽑아 웹북에 넣는다.

이 책의 그림은 별도 파일이 아니라 본문 .tex 안에 \\begin{tikzpicture} 로
직접 들어 있다. 그것을 하나씩 떼어 내 standalone 문서로 컴파일하고
PDF -> SVG 로 바꿔 docs/book/img/ 에 저장한다.

    python3 tools/build_figures.py            # 전부
    python3 tools/build_figures.py 7 9        # 7장, 9장만

필요한 것: xelatex, pdftocairo(poppler)
결과:
    docs/book/img/chNN/figMM.svg
    tools/fig_manifest.json   (장별 그림 개수 — tex2html.py 가 참조)

원고 위치는 환경변수 LA4CS_TEX 로 바꿀 수 있다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TEX = Path(os.environ.get(
    "LA4CS_TEX",
    "~/Library/CloudStorage/OneDrive-개인/문서/YMKang_Work/저술_원고/선형대수/latex"
)).expanduser()
OUT = REPO / "docs" / "book" / "img"

XELATEX = shutil.which("xelatex") or "xelatex"
PDFTOCAIRO = shutil.which("pdftocairo") or "pdftocairo"

# standalone 문서의 머리말 — 원고 preamble.tex 에서 그림에 필요한 부분만 추렸다.
PREAMBLE = r"""
\documentclass[border=2pt]{standalone}
\usepackage{kotex}
\usepackage{fontspec}
\setmainfont{KoPubBatang}[Scale=0.88]
\setsansfont{KoPubDotum}[Scale=0.88]
\setmonofont{D2Coding}[Scale=0.88]
\setmainhangulfont{KoPubBatang}[Scale=0.88]
\setsanshangulfont{KoPubDotum}[Scale=0.88]
\usepackage{amsmath, amssymb}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usetikzlibrary{arrows.meta, positioning, shapes.geometric, calc, shadows, fit,
                backgrounds, matrix, decorations.pathreplacing, patterns}
\usepackage{xcolor}
\definecolor{deepblue}{RGB}{22, 56, 100}
\definecolor{skyblue}{RGB}{70, 130, 200}
\definecolor{accentcopper}{RGB}{200, 105, 50}
\definecolor{warmgold}{RGB}{218, 170, 65}
\definecolor{rulegray}{RGB}{210, 214, 220}
\definecolor{inkgray}{RGB}{55, 65, 80}
\definecolor{chapbgcolor}{RGB}{230, 238, 248}
\definecolor{neutralgray}{RGB}{95, 105, 120}
\definecolor{bookorange}{HTML}{D97706}
\definecolor{bookblue}{HTML}{2563EB}
\definecolor{bookgreen}{HTML}{15803D}
\definecolor{bookgray}{HTML}{6B7280}
\definecolor{editorborder}{HTML}{E5E7EB}
\definecolor{cautioncolor}{RGB}{195, 85, 70}
\definecolor{labcolor}{RGB}{40, 140, 125}
\definecolor{notecolor}{RGB}{105, 115, 175}
\definecolor{defcolor}{RGB}{35, 95, 150}
\definecolor{thmcolor}{RGB}{120, 85, 160}
\definecolor{stepcolor}{RGB}{70, 125, 90}
\definecolor{keypointmain}{RGB}{190, 145, 35}
\definecolor{exercisecolor}{RGB}{165, 65, 80}
\definecolor{partgreen}{RGB}{140, 195, 240}
\definecolor{partmagenta}{RGB}{20, 55, 105}
\newcommand{\vv}[1]{\boldsymbol{\mathbf{#1}}}
\newcommand{\mm}[1]{\boldsymbol{\mathbf{#1}}}
\newcommand{\tp}{^{\mathsf{T}}}
\newcommand{\inv}{^{-1}}
\newcommand{\Id}{\mm{I}}
\newcommand{\norm}[1]{\left\lVert #1 \right\rVert}
\newcommand{\abs}[1]{\left\lvert #1 \right\rvert}
\newcommand{\proj}{\operatorname{proj}}
\DeclareMathOperator{\rank}{rank}
\DeclareMathOperator{\trace}{tr}
\DeclareMathOperator{\diag}{diag}
\DeclareMathOperator{\spn}{span}
\DeclareMathOperator{\Col}{Col}
\DeclareMathOperator{\Nul}{Nul}
\DeclareMathOperator{\Row}{Row}
\newcommand{\Rsp}[1]{\mathbb{R}^{#1}}
\newcommand{\Rmat}[2]{\mathbb{R}^{#1 \times #2}}
\newcommand{\pinv}{^{+}}
\newcommand{\zerovec}{\vv{0}}
\newcommand{\mtwo}[4]{\begin{bmatrix}#1 & #2\\ #3 & #4\end{bmatrix}}
\newcommand{\dash}{\,---\,}
\newcommand{\ndash}{--}
\begin{document}
%%BODY%%
\end{document}
"""

TIKZ_RE = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)


def chapter_files(num):
    d = TEX / "chapters" / f"ch{num:02d}"
    return sorted(d.glob("sec*.tex")) + [d / "labs.tex"]


def collect(num):
    """장 안에서 figure 환경에 담긴 tikzpicture 를 등장 순서대로 모은다.

    본문 순서와 그림 번호를 맞추기 위해 chNN.tex 의 \\input 순서를 따른다.
    figure 밖의 tikzpicture(설명용 인라인 도식)도 함께 모은다.
    """
    chfile = TEX / "chapters" / f"ch{num:02d}" / f"ch{num:02d}.tex"
    if not chfile.exists():
        return []
    order = re.findall(r"\\input\{chapters/ch\d\d/([a-z0-9]+)\.tex\}",
                       chfile.read_text(encoding="utf-8"))
    figs = []
    for stem in order:
        f = TEX / "chapters" / f"ch{num:02d}" / f"{stem}.tex"
        if not f.exists():
            continue
        figs += TIKZ_RE.findall(f.read_text(encoding="utf-8"))
    return figs


def build_one(body, dest):
    """tikzpicture 하나를 SVG 로 만든다."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "f.tex").write_text(PREAMBLE.replace("%%BODY%%", body),
                                  encoding="utf-8")
        r = subprocess.run([XELATEX, "-interaction=nonstopmode", "-halt-on-error",
                            "f.tex"], cwd=td, capture_output=True, text=True)
        if not (td / "f.pdf").exists():
            tail = "\n".join(r.stdout.splitlines()[-12:])
            return False, tail
        subprocess.run([PDFTOCAIRO, "-svg", "f.pdf", "f.svg"], cwd=td,
                       capture_output=True)
        if not (td / "f.svg").exists():
            return False, "pdftocairo 실패"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(td / "f.svg", dest)
        return True, ""


def main():
    nums = [int(a) for a in sys.argv[1:]] or list(range(1, 14))
    manifest = {}
    mpath = HERE / "fig_manifest.json"
    if mpath.exists():
        manifest = json.loads(mpath.read_text(encoding="utf-8"))

    for num in nums:
        figs = collect(num)
        if not figs:
            continue
        print(f"ch{num:02d}: 그림 {len(figs)}개")
        ok = 0
        for k, body in enumerate(figs, 1):
            dest = OUT / f"ch{num:02d}" / f"fig{k:02d}.svg"
            good, msg = build_one(body, dest)
            if good:
                ok += 1
            else:
                print(f"   !! fig{k:02d} 실패\n{msg}")
        manifest[str(num)] = len(figs)
        print(f"   -> {ok}/{len(figs)} 성공")

    mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                     encoding="utf-8")
    print("fig_manifest.json 갱신")


if __name__ == "__main__":
    main()
