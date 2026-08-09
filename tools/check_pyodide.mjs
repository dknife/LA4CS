// check_pyodide.mjs — 실제 Pyodide 로 tuvis(plotly) 예제가 도는지 확인한다.
//
//   mkdir -p /tmp/pyo && cd /tmp/pyo && npm install pyodide
//   node ~/GitRepos/LA4CS/tools/check_pyodide.mjs
//
// 중요: pyrunner.js 의 모듈 주입 블록을 파일에서 잘라 내 '있는 그대로' 실행한다.
// 예전에 따로 흉내 낸 코드로 검사했다가 tuvis.py 를 심지 않은 버그를 놓쳤다.
// 검사는 반드시 제품 코드를 직접 돌려야 한다.
//
// check_web_run.py 는 CPython 으로 도는 빠른 검사이고, 이쪽은 Pyodide 특유의
// 문제(모듈 주입 누락, js.document, 휠 설치 가능 여부)를 잡는다.
// (모듈을 미리 복사해 두지 않는다 — 워커가 fetch 로 가져오는 것까지 흉내 낸다)
import { loadPyodide } from 'pyodide';
import fs from 'fs';
const H = process.env.HOME + '/GitRepos/LA4CS/docs/book/';
const src = fs.readFileSync(H + 'pyrunner.js', 'utf8');

// fetch 를 파일 읽기로 대체
const realFetch = globalThis.fetch;                 // micropip 은 이걸 써야 한다
globalThis.fetch = async (u, ...rest) => {
  if (typeof u === 'string' && !/^https?:/.test(u)) {   // 워커의 상대 경로만 가로챈다
    const path = H + u;
    const ok = fs.existsSync(path);
    return { ok, status: ok ? 200 : 404, text: async () => fs.readFileSync(path, 'utf8') };
  }
  return realFetch(u, ...rest);
};
const py = await loadPyodide();
py.setStderr({ batched: () => {} });

// pyrunner 의 모듈 주입 블록만 발췌 실행 (실제 파일에서 잘라 온다)
const b0 = src.indexOf('  // 이 책의 시각화 모듈을');
const b1 = src.indexOf('  return py;', b0);
const block = src.slice(b0, b1);
const hook  = src.match(/var PLOTLY_HOOK = \[[\s\S]*?\]\.join\('\\n'\);/)[0];
const post = (t,m) => console.log('[worker]', t, String(m).trim().slice(0,80));
await (new Function('py','post','fetch', `return (async()=>{ ${block} })()`))(py, post, globalThis.fetch);
eval(hook.replace('var PLOTLY_HOOK','globalThis.PLOTLY_HOOK'));
py.runPython(globalThis.PLOTLY_HOOK);

await py.loadPackage('micropip');
await py.runPythonAsync('import micropip\nawait micropip.install("plotly")');

// tuvis 를 쓰는 예제를 여러 장에서 골라 돌린다 (3차원·여러 칸·히트맵을 모두 포함)
const un = s => s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&amp;/g,'&');
const key = s => { let v=5381; for (const c of s){ v=((Math.imul(v,33))^c.codePointAt(0))>>>0; } return v.toString(36); };
const pre = JSON.parse(fs.readFileSync(H+'run-preludes.json','utf8'));
const concept = new Set(JSON.parse(fs.readFileSync(H+'concept-codes.json','utf8')));
const PAGES = ['ch02.html','ch03.html','ch05.html','ch08.html','ch09.html',
               'ch11.html','ch13.html','apxb.html'];
const targets = [];
for (const page of PAGES) {
  const html = fs.readFileSync(H + page, 'utf8');
  const blocks = [...html.matchAll(/<pre class="line-numbers"><code class="language-python">([\s\S]*?)<\/code>/g)].map(m=>un(m[1]));
  const hit = blocks.filter(c => /\bnew_axes3d\(|\bnew_matrix_axes\(|ncols=/.test(c)
                                 && !concept.has(key(c.trim())));
  for (const c of hit.slice(-3)) targets.push([page, c]);   // 장마다 최대 3개
}
console.log('\ntuvis 예제', targets.length, '개\n');
let bad = 0;
for (const [i,[page,code]] of targets.entries()) {
  const ns = py.runPython('dict(__name__="__main__")');
  py.runPython('_algja_plotly_patch()');
  try {
    await py.runPythonAsync((pre[key(code)]||'') + code, { globals: ns });
    py.globals.set('_algja_ns', ns);
    const pj = py.runPython('_algja_plotly_dump(_algja_ns)');
    const list = pj.toJs(); pj.destroy();
    console.log(`${page} 예제 ${i+1}: 그림 ${list.length}개 → ${list.length ? 'OK' : '그림 없음'}`);
  } catch (e) { bad++; console.log(`${page} 예제 ${i+1}: 실패 —`, String(e).split('\n').filter(x=>x.trim()).pop().slice(0,90)); }
  ns.destroy();
}
console.log(bad ? `\n실패 ${bad}개` : '\n전부 통과');
