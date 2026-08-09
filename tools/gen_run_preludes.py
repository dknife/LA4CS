#!/usr/bin/env python3
"""gen_run_preludes.py — 이어지는 예제의 '준비 코드'를 만들어 둔다.

이 책의 코드 블록은 앞 블록에서 만든 변수를 이어 쓰는 경우가 많다.
(예: 9장에서 A, w, V 를 만들고 다음 블록에서 그대로 쓴다)
웹에서는 블록 하나만 따로 실행하므로, 그런 블록은 앞의 블록들을 먼저
돌려 주어야 한다. 그 대응표가 run-preludes.json 이다.

    코드의 djb2-xor 해시(book.js 의 codeKey 와 같은 방식) -> 앞 블록들을 이어 붙인 코드

같은 .tex 파일 안의 앞선 pycode 블록 전부를 준비 코드로 삼는다.
원고 검증(verify_outputs.py)이 바로 이 방식으로 실행해 통과했으므로 안전하다.

    python3 tools/gen_run_preludes.py

plotly 를 쓰는 tuvis 예제는 이 실행기에서 돌릴 수 없으므로
concept-codes.json 에 넣어 '설명을 돕는 개념 코드'로 표시한다.
"""
import ast
import builtins
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TEX = Path(os.environ.get(
    "LA4CS_TEX",
    "~/Library/CloudStorage/OneDrive-개인/문서/YMKang_Work/저술_원고/선형대수/latex"
)).expanduser()
OUT = REPO / "docs" / "book"

PYCODE = re.compile(r"\\begin\{pycode\}\n(.*?)\\end\{pycode\}", re.S)

# 준비 코드와 이번에 실행할 코드의 경계.
# pyrunner.js 가 이 줄을 찾아 앞부분은 조용히 돌리고(출력·그림을 버린다)
# 뒷부분만 결과를 보여 준다. 독자에게도 어디까지가 준비 코드인지 알려 준다.
PRELUDE_MARK = "# ─────────── 여기까지는 앞 예제의 준비 코드입니다 ───────────"

# `from lautils import *` 로 들어오는 이름들
LAUTILS_NAMES = set()
_lau = TEX / "code" / "lautils.py"
if _lau.exists():
    LAUTILS_NAMES = {m for m in re.findall(r"^(?:def |)([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|\()",
                                           _lau.read_text(encoding="utf-8"), re.M)
                     if not m.startswith("_")}


def code_key(s: str) -> str:
    """book.js 의 codeKey 와 같은 djb2-xor 해시 (32비트, 36진수)."""
    h = 5381
    for chunk in s:
        h = ((h * 33) & 0xFFFFFFFF) ^ ord(chunk)
        h &= 0xFFFFFFFF
    # 36진수 문자열
    if h == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while h:
        out = digits[h % 36] + out
        h //= 36
    return out


def source_files():
    """원고의 본문 파일을 장 순서대로 돌려준다."""
    files = []
    for n in range(1, 14):
        d = TEX / "chapters" / f"ch{n:02d}"
        chfile = d / f"ch{n:02d}.tex"
        if not chfile.exists():
            continue
        order = re.findall(r"\\input\{chapters/ch\d\d/([a-z0-9]+)\.tex\}",
                           chfile.read_text(encoding="utf-8"))
        files += [d / f"{stem}.tex" for stem in order]
    files += [TEX / "backmatter" / f"{n}.tex" for n in
              ("appendix_a_setup", "appendix_b_lautils", "appendix_c_reference")]
    return [f for f in files if f.exists()]


def not_runnable(body: str) -> bool:
    """이 실행기에서 돌릴 수 없는 코드인가?

    주피터 매직(%%writefile)과 코랩 전용 코드.
    준비 코드에 섞이면 뒤따르는 블록까지 문법 오류가 나므로 함께 걸러 낸다.
    """
    # 대화형(plotly) 그림은 실행할 수 있다 — pyrunner 가 micropip 으로 설치하고
    # 결과를 plotly.js 로 그린다. 여기서 거르는 것은 정말 못 돌리는 것뿐이다.
    return (body.lstrip().startswith("%%")        # 주피터 매직
            or "google.colab" in body)            # 코랩 전용


def missing_imports(code: str) -> str:
    """블록이 쓰지만 import 하지 않은 것을 채워 주는 코드를 만든다.

    본문에서는 앞의 설명 흐름상 import 를 생략한 짧은 블록이 있다(주의 박스 등).
    지면에서는 문제가 없지만 웹에서는 그 블록만 따로 실행되므로 이름을 못 찾는다.
    """
    def lacks(use_pat, import_pat):
        """쓰기는 하는데 import 가 없거나 첫 사용보다 뒤에 있는가?"""
        u = re.search(use_pat, code)
        if not u:
            return False
        m = re.search(import_pat, code)
        return m is None or m.start() > u.start()

    need = []
    if lacks(r"\bnp\.", r"import numpy"):
        need.append("import numpy as np")
    if lacks(r"\bplt\.", r"import matplotlib"):
        need.append("import matplotlib.pyplot as plt")
    if lacks(r"\b(draw_\w+|new_axes3?d?|transform|show_matrix"
             r"|UNIT_SQUARE|UNIT_CUBE|PALETTE)\b", r"lautils"):
        need.append("from lautils import *")
    return "\n".join(need) + "\n\n" if need else ""


def unresolved_names(code: str) -> set:
    """코드가 쓰지만 어디에도 정의되지 않은 이름을 찾는다.

    연습문제에는 \"이 코드의 잘못된 점을 찾으시오\" 처럼 앞뒤 맥락이 없는
    발췌가 있다. 그런 블록은 실행할 수 없으므로 미리 걸러 낸다.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    assigned, used = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            (assigned if isinstance(node.ctx, ast.Store) else used).add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assigned.add(node.name)
        elif isinstance(node, ast.arg):
            assigned.add(node.arg)
        elif isinstance(node, ast.alias):
            assigned.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            assigned.add(node.name)
    if "from lautils import *" in code or "from tuvis import *" in code:
        assigned |= LAUTILS_NAMES
    return used - assigned - set(dir(builtins))


def main():
    preludes = {}
    concepts = []
    n_blocks = 0

    for f in source_files():
        blocks = PYCODE.findall(f.read_text(encoding="utf-8"))
        n_blocks += len(blocks)
        for i, code in enumerate(blocks):
            body = code.strip("\n")
            if not_runnable(body):
                concepts.append(code_key(body))
                continue
            earlier = [b.strip("\n") for b in blocks[:i]
                       if not not_runnable(b.strip("\n"))]
            if not earlier:
                # 앞 블록이 없더라도 import 가 빠졌으면 그것만 채워 준다
                fix = missing_imports(body)
                if unresolved_names(fix + body):
                    concepts.append(code_key(body))  # 맥락 없는 발췌
                elif fix:
                    preludes[code_key(body)] = fix + PRELUDE_MARK + "\n\n"
                continue
            # book.js 는 `pre + code` 로 그냥 이어 붙인다. 끝에 빈 줄을 두지 않으면
            # 앞 블록의 마지막 줄과 이 블록의 첫 줄이 한 줄로 붙어 SyntaxError 가 난다.
            prev = "\n\n".join(earlier) + "\n" + PRELUDE_MARK + "\n\n"
            prev = missing_imports(prev) + prev
            # 앞 블록이 정의한 이름을 쓰지 않는 블록에는 준비 코드가 필요 없다.
            # 판단이 어려우므로 앞 블록을 모두 붙인다(원고 검증과 같은 방식).
            preludes[code_key(body)] = prev

    (OUT / "run-preludes.json").write_text(
        json.dumps(preludes, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "concept-codes.json").write_text(
        json.dumps(sorted(set(concepts)), ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"코드 블록 {n_blocks}개")
    print(f"run-preludes.json  : {len(preludes)}개")
    print(f"concept-codes.json : {len(set(concepts))}개 (실행 대상 아님)")

    # 자체 점검 — book.js 는 `pre + code` 로 그냥 이어 붙인다.
    # 실제로 그렇게 붙여 문법이 성립하는지 확인한다.
    bad = 0
    for f in source_files():
        for i, code in enumerate(PYCODE.findall(f.read_text(encoding="utf-8"))):
            body = code.strip("\n")
            k = code_key(body)
            if k in set(concepts):
                continue
            joined = preludes.get(k, "") + body
            try:
                compile(joined, "<web>", "exec")
            except SyntaxError as e:
                bad += 1
                print(f"  !! 문법 오류 {f.name} 블록 {i + 1}: {e}")
    print("자체 점검 :", "통과" if bad == 0 else f"{bad}건 실패")


if __name__ == "__main__":
    main()
