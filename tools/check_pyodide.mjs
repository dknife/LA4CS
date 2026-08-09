// check_pyodide.mjs — 실제 Pyodide 로 대화형(plotly) 예제가 도는지 확인한다.
//
//   cd /tmp && mkdir -p pyo && cd pyo
//   npm install pyodide
//   cp ~/GitRepos/LA4CS/docs/book/{lautils.py,tuvis.py} .
//   node ~/GitRepos/LA4CS/tools/check_pyodide.mjs
//
// 브라우저 워커와 같은 조건(Agg 백엔드, micropip 으로 plotly 설치, show() 가로채기)
// 을 재현한다. check_web_run.py 는 CPython 으로 도는 빠른 검사이고, 이쪽은
// Pyodide 특유의 문제(js.document, 휠 설치 가능 여부)를 잡는다.
import { loadPyodide } from 'pyodide';
import fs from 'fs';
const H = process.env.HOME + '/GitRepos/LA4CS/docs/book/';
const py = await loadPyodide();
await py.loadPackage(['numpy','matplotlib','micropip']);
await py.runPythonAsync('import micropip\nawait micropip.install("plotly")');
py.FS.writeFile('lautils.py', fs.readFileSync('lautils.py'));
py.FS.writeFile('tuvis.py', fs.readFileSync('tuvis.py'));
py.runPython('import os,sys\nsys.path.insert(0, os.getcwd())');
py.runPython('import matplotlib\nmatplotlib.use("Agg")');   // pyrunner 초기화와 동일
py.runPython(fs.readFileSync('hook.py','utf8'));

const pre = JSON.parse(fs.readFileSync(H+'run-preludes.json','utf8'));
const un = s => s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&amp;/g,'&');
const key = s => { let v=5381; for (const c of s){ v=((Math.imul(v,33))^c.codePointAt(0))>>>0; } return v.toString(36); };

// 실행 버튼이 붙는 블록만: <pre class="line-numbers"><code class="language-python">
const html = fs.readFileSync(H+'apxb.html','utf8');
const blocks = [...html.matchAll(/<pre class="line-numbers"><code class="language-python">([\s\S]*?)<\/code>/g)].map(m => un(m[1]));
const targets = blocks.filter(c => c.includes('interactive=True'));
console.log('부록 B 대화형 예제:', targets.length, '개\n');

for (const [i, code] of targets.entries()) {
  const full = (pre[key(code)] || '') + code;
  const ns = py.runPython('dict(__name__="__main__")');
  py.runPython('_algja_plotly_patch()');
  try {
    await py.runPythonAsync(full, { globals: ns });
    py.globals.set('_algja_ns', ns);
    const pj = py.runPython('_algja_plotly_dump(_algja_ns)');
    const list = pj.toJs(); pj.destroy();
    const traces = list.length ? JSON.parse(list[0]).data.length : 0;
    console.log(`예제 ${i+1}: 준비코드 ${pre[key(code)] ? '있음' : '없음'}, 그림 ${list.length}개, trace ${traces}개 → ${list.length ? 'OK' : '그림 없음'}`);
  } catch (e) {
    console.log(`예제 ${i+1}: 오류 —`, String(e).split('\n').filter(x=>x.trim()).pop().slice(0,80));
  }
  ns.destroy();
}
