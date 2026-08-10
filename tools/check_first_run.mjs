// check_first_run.mjs — "첫 실행만 실패" 회귀 검사.
//
//   node tools/check_first_run.mjs
//
// 워커가 처음 코드를 돌릴 때의 순서를 그대로 재현한다.
//   PLOTLY_HOOK 실행 → micropip 으로 plotly 설치 → _algja_plotly_patch()
//   → 사용자 코드 실행(fig.show()) → _algja_plotly_dump()
// 이때 show() 가 가로채여야 한다. 예전에는 patch 가 sys.modules 만 보아서
// 아직 import 되지 않은 plotly 를 놓쳤고, 그래서 첫 실행만 오류가 났다.
//
// 판정은 ns 되살리기(fallback)를 쓰지 않고 dump() 에 ns 를 넘기지 않는 것으로 한다.
// show() 가 제대로 가로채였다면 그것만으로 그림이 나와야 한다.
import { loadPyodide } from 'pyodide';
import fs from 'fs';

const H = process.env.HOME + '/GitRepos/LA4CS/docs/book/';
const src = fs.readFileSync(H + 'pyrunner.js', 'utf8');
const hook = src.match(/var PLOTLY_HOOK = \[[\s\S]*?\]\.join\('\\n'\);/)[0];

const py = await loadPyodide();
py.setStderr({ batched: () => {} });
py.setStdout({ batched: () => {} });

eval(hook.replace('var PLOTLY_HOOK', 'globalThis.PLOTLY_HOOK'));
py.runPython(globalThis.PLOTLY_HOOK);

await py.loadPackage(['numpy', 'micropip']);
await py.runPythonAsync('import micropip\nawait micropip.install("plotly")');

// 여기서 plotly 는 "설치만" 된 상태다 — 아직 아무도 import 하지 않았다.
const imported = py.runPython('import sys; "plotly.graph_objects" in sys.modules');
console.log('패치 직전 plotly import 여부 :', imported, '(false 여야 재현이다)');

py.FS.writeFile('tuvis.py', fs.readFileSync(H + 'tuvis.py', 'utf8'));
py.runPython('import os, sys\nif os.getcwd() not in sys.path: sys.path.insert(0, os.getcwd())');

py.runPython('_algja_plotly_patch()');

const code = [
  'import numpy as np',
  'from tuvis import *',
  'fig, ax = new_axes(xlim=(-3, 3), ylim=(-3, 3))',
  'draw_vector(ax, [2, 1], label="v")',
  'fig.show()',
].join('\n');

const ns = py.runPython('dict(__name__="__main__")');
await py.runPythonAsync(code, { globals: ns });
const pj = py.runPython('_algja_plotly_dump()');   // ns 를 넘기지 않는다
const n = pj.toJs().length;
pj.destroy(); ns.destroy();

console.log('첫 실행에서 가로챈 그림 :', n, '개');
if (n === 1) {
  console.log('통과 — 첫 실행부터 fig.show() 가 가로채인다');
} else {
  console.log('실패 — 첫 실행에서 show() 가 가로채이지 않았다');
  process.exit(1);
}
