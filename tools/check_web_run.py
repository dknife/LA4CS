#!/usr/bin/env python3
"""check_web_run.py — 웹에서 실행되는 그대로 모든 코드 블록을 돌려 본다.

    cd docs/book && python3 ../../tools/check_web_run.py

book.js 와 똑같이 `run-preludes.json` 의 준비 코드를 앞에 붙여 실행하고,
concept-codes.json 에 오른 블록(대화형·코랩 전용)은 건너뛴다.
실패가 0이어야 웹북의 [실행] 버튼이 정상 동작한다.
"""
import re, html, json, pathlib, subprocess, sys, tempfile, os
def key(s):
    v=5381
    for c in s: v=((v*33)&0xFFFFFFFF)^ord(c); v&=0xFFFFFFFF
    d="0123456789abcdefghijklmnopqrstuvwxyz"; o=""
    while v: o=d[v%36]+o; v//=36
    return o or "0"
pre = json.loads(pathlib.Path("run-preludes.json").read_text())
concepts = set(json.loads(pathlib.Path("concept-codes.json").read_text()))
HEAD = ("import matplotlib\nmatplotlib.use('Agg')\n"
        "import matplotlib.pyplot as _p\n_p.show=lambda *a,**k:None\n"
        "import sys; sys.path.insert(0,'.')\n")
fails, total = [], 0
for f in sorted(pathlib.Path('.').glob('ch*.html')) + sorted(pathlib.Path('.').glob('apx*.html')):
    for c in [html.unescape(m) for m in re.findall(r'<code class="language-python">(.*?)</code>', f.read_text(), re.S)]:
        k = key(c)
        if k in concepts: continue
        total += 1
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as t:
            t.write(HEAD + pre.get(k, "") + c); path = t.name
        try:
            r = subprocess.run([sys.executable, path], capture_output=True,
                               text=True, cwd='.', timeout=120)
            if r.returncode != 0:
                fails.append((f.name, r.stderr.strip().split('\n')[-1][:90]))
        except subprocess.TimeoutExpired:
            fails.append((f.name, '시간 초과(120초)'))
        os.unlink(path)
print(f"실행 검사 {total}개 → 실패 {len(fails)}개")
for x in fails[:12]: print("  ", x)
