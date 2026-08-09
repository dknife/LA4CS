// 쓸모 있는 선형대수 — 코드 실행 워커 (Pyodide / CPython WebAssembly)
//
// 메인 스레드가 아니라 워커에서 돌리는 이유:
//   1) 무한 루프를 만들어도 페이지가 얼지 않는다
//   2) terminate()로 실행을 중단할 수 있다 (파이썬 안에서는 멈출 방법이 없다)
//
// input()은 대화형으로 받을 수 없다. 그러려면 SharedArrayBuffer가 필요하고,
// 그건 COOP/COEP 헤더를 요구하는데 GitHub Pages는 헤더를 설정할 수 없다.
// 그래서 실행 전에 '입력값' 상자로 미리 받아 둔 줄을 하나씩 돌려준다.
//
// 이 파일은 반드시 모듈 워커로 띄워야 한다 -- new Worker(url, {type:'module'}).
// Pyodide 314는 클래식 워커를 더 이상 지원하지 않는다
// ("Classic web workers are not supported"). 그래서 importScripts가 아니라
// ESM import를 쓴다.

// 정적 import는 URL에 변수를 못 쓰므로 아래 두 경로를 함께 고쳐야 한다.
import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v314.0.2/full/pyodide.mjs';
var PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v314.0.2/full/';

var py = null;

// input() 대체와 matplotlib 그림 수집기를 메인 네임스페이스에 심어 둔다.
var PRELUDE = [
  'import builtins, sys',
  '',
  'def _algja_stdin(text):',
  '    lines = text.split("\\n") if text else []',
  '    while lines and lines[-1] == "":',
  '        lines.pop()',
  '    it = iter(lines)',
  '    def _input(prompt=""):',
  '        try:',
  '            line = next(it)',
  '        except StopIteration:',
  '            raise EOFError(',
  '                "입력값이 모자랍니다. 창의 \'입력값\' 상자에 "',
  '                "필요한 만큼 한 줄에 하나씩 적어 주세요."',
  '            ) from None',
  '        if prompt:',
  '            print(prompt, end="")',
  '        print(line)',
  '        return line',
  '    builtins.input = _input',
  '',
  'def _algja_figs():',
  '    mod = sys.modules.get("matplotlib.pyplot")',
  '    if mod is None:',
  '        return []',
  '    import base64, io',
  '    out = []',
  '    for n in mod.get_fignums():',
  '        buf = io.BytesIO()',
  '        mod.figure(n).savefig(buf, format="png", dpi=110, bbox_inches="tight")',
  '        out.append(base64.b64encode(buf.getvalue()).decode())',
  '    mod.close("all")',
  '    return out',
  '',
  'def _algja_fs_snapshot():',
  '    import os',
  '    snap = {}',
  '    for root, dirs, files in os.walk("."):',
  '        dirs[:] = [d for d in dirs if not d.startswith(".")]',
  '        for f in files:',
  '            p = os.path.normpath(os.path.join(root, f))',
  '            try:',
  '                st = os.stat(p)',
  '                snap[p] = (st.st_mtime_ns, st.st_size)',
  '            except OSError:',
  '                pass',
  '    return snap',
  '',
  '_algja_fs_before = {}',
  '',
  'def _algja_fs_mark():',
  '    global _algja_fs_before',
  '    _algja_fs_before = _algja_fs_snapshot()',
  '',
  'def _algja_fs_diff():',
  '    """실행으로 생성·변경된 파일 목록을 JSON으로 돌려준다."""',
  '    import json, os',
  '    out = []',
  '    now = _algja_fs_snapshot()',
  '    for p in sorted(now):',
  '        if _algja_fs_before.get(p) == now[p]:',
  '            continue',
  '        item = {"name": p}',
  '        size = now[p][1]',
  '        try:',
  '            with open(p, "rb") as f:',
  '                data = f.read(20000)',
  '            text = data.decode("utf-8-sig")',
  '            if size > 20000:',
  '                text += "\\n... (이하 생략 -- 총 %d바이트)" % size',
  '            item["content"] = text',
  '        except UnicodeDecodeError:',
  '            item["binary"] = size',
  '        except OSError as e:',
  '            item["content"] = "(읽기 실패: %s)" % e',
  '        out.append(item)',
  '    return json.dumps(out)',
  '',
  '# ---- Flask 시뮬레이터 ----',
  '# 진짜 서버(소켓)는 브라우저에서 열 수 없다. 대신 Flask.run()을 가로채',
  '# 앱 객체를 보관하고, 미니 브라우저의 요청을 test_client()로 처리한다.',
  'def _algja_flask_patch():',
  '    import flask',
  '    if getattr(flask, "_algja_patched", False):',
  '        return',
  '    _orig_init = flask.Flask.__init__',
  '    def _init(self, *a, **k):',
  '        _orig_init(self, *a, **k)',
  '        flask._algja_app = self',
  '    flask.Flask.__init__ = _init',
  '    def _run(self, *a, **k):',
  '        flask._algja_app = self',
  '        print(" * Serving Flask app %r (시뮬레이터)" % self.name)',
  '        print(" * Running on http://127.0.0.1:5000")',
  '        print("   (아래 미니 브라우저에서 접속해 보세요)")',
  '    flask.Flask.run = _run',
  '    flask._algja_patched = True',
  '',
  'def _algja_flask_reset():',
  '    m = sys.modules.get("flask")',
  '    if m is not None and hasattr(m, "_algja_app"):',
  '        m._algja_app = None',
  '',
  'def _algja_flask_dump():',
  '    import json',
  '    m = sys.modules.get("flask")',
  '    app = getattr(m, "_algja_app", None) if m else None',
  '    if app is None:',
  '        return ""',
  '    routes = []',
  '    for r in app.url_map.iter_rules():',
  '        if r.endpoint == "static":',
  '            continue',
  '        methods = sorted(x for x in r.methods if x not in ("HEAD", "OPTIONS"))',
  '        routes.append({"rule": str(r), "methods": methods})',
  '    routes.sort(key=lambda x: x["rule"])',
  '    return json.dumps({"routes": routes})',
  '',
  'def _algja_flask_request(req_json):',
  '    import json',
  '    m = sys.modules.get("flask")',
  '    app = getattr(m, "_algja_app", None) if m else None',
  '    if app is None:',
  '        return json.dumps({"status": 0, "body":',
  '            "<p>Flask 앱이 없습니다. 먼저 코드를 다시 실행해 주세요.</p>",',
  '            "path": "/"})',
  '    req = json.loads(req_json)',
  '    client = app.test_client()',
  '    method = req.get("method", "GET").upper()',
  '    path = req.get("path", "/") or "/"',
  '    if not path.startswith("/"):',
  '        path = "/" + path',
  '    try:',
  '        if method == "POST":',
  '            res = client.post(path, data=req.get("data") or {},',
  '                              follow_redirects=True)',
  '        else:',
  '            res = client.get(path, follow_redirects=True)',
  '        return json.dumps({"status": res.status_code,',
  '                           "body": res.get_data(as_text=True),',
  '                           "path": res.request.path})',
  '    except Exception as e:',
  '        return json.dumps({"status": 500, "body":',
  '            "<pre>%s</pre>" % str(e), "path": path})',
  '',
  'def _algja_turtle_reset():',
  '    m = sys.modules.get("turtle")',
  '    if m is not None and getattr(m, "_algja", False):',
  '        m._algja_reset()',
  '',
  'def _algja_turtle_dump():',
  '    m = sys.modules.get("turtle")',
  '    if m is not None and getattr(m, "_algja", False):',
  '        return m._algja_dump()',
  '    return ""',
  ''
].join('\n');

// ---- 터틀 그래픽 시뮬레이터 (기록기) ----
// 진짜 turtle은 tkinter 창이 필요해 브라우저에서 돌 수 없다. 대신 같은 API를
// 가진 가짜 turtle 모듈을 sys.modules에 심어 둔다. 이 모듈은 그리지 않고
// 그리기 명령(선분·채우기·점·글씨)만 기록하며, 실행이 끝나면 메인 스레드가
// 그 명령들을 캔버스에 거북이 애니메이션으로 재생한다.
var TURTLE_SRC = [
  'import math as _math, json as _json',
  '',
  '_cmds = []',
  '_turtles = []',
  '_colormode = 1.0',
  '_default = None',
  '_MAX = 60000',
  '',
  'def _emit(c):',
  '    if len(_cmds) >= _MAX:',
  '        raise RuntimeError(',
  '            "그리기 명령이 6만 개를 넘었습니다. "',
  '            "반복 횟수나 재귀 깊이를 줄여 보세요.")',
  '    _cmds.append(c)',
  '',
  'def _col(c):',
  '    if isinstance(c, (tuple, list)):',
  '        if len(c) == 1:',
  '            return _col(c[0])',
  '        if _colormode == 1.0:',
  '            r, g, b = [max(0, min(255, int(round(float(v) * 255))))',
  '                       for v in c[:3]]',
  '        else:',
  '            r, g, b = [max(0, min(255, int(round(float(v)))))',
  '                       for v in c[:3]]',
  '        return "rgb(%d,%d,%d)" % (r, g, b)',
  '    return str(c)',
  '',
  'def _r(v):',
  '    return round(float(v), 2)',
  '',
  'class Vec2D(tuple):',
  '    def __new__(cls, x, y):',
  '        return tuple.__new__(cls, (x, y))',
  '',
  'class _ScreenClass:',
  '    _inst = None',
  '    def __new__(cls):',
  '        if cls._inst is None:',
  '            cls._inst = object.__new__(cls)',
  '        return cls._inst',
  '    def bgcolor(self, *c):',
  '        if c:',
  '            _emit({"op": "bg", "c": _col(c if len(c) > 1 else c[0])})',
  '    def colormode(self, m=None):',
  '        global _colormode',
  '        if m is None:',
  '            return _colormode',
  '        _colormode = m',
  '    def clear(self):',
  '        _emit({"op": "clear"})',
  '    clearscreen = clear',
  '    reset = clear',
  '    resetscreen = clear',
  '    def setup(self, *a, **k): pass',
  '    def screensize(self, *a, **k): pass',
  '    def title(self, *a, **k): pass',
  '    def tracer(self, *a, **k): pass',
  '    def update(self): pass',
  '    def delay(self, *a, **k): pass',
  '    def listen(self, *a, **k): pass',
  '    def onkey(self, *a, **k): pass',
  '    def onclick(self, *a, **k): pass',
  '    def ontimer(self, *a, **k): pass',
  '    def mainloop(self): pass',
  '    def exitonclick(self): pass',
  '    def bye(self): pass',
  '',
  'def Screen():',
  '    return _ScreenClass()',
  '',
  'class Turtle:',
  '    def __init__(self, shape="classic", undobuffersize=1000, visible=True):',
  '        self._x = 0.0; self._y = 0.0; self._h = 0.0',
  '        self._pen = True',
  '        self._pc = "black"; self._fc = "black"',
  '        self._w = 1',
  '        self._vis = visible',
  '        self._speed = 3',
  '        self._fill = None',
  '        self._fill_from = 0',
  '        _turtles.append(self)',
  '',
  '    def _goto(self, nx, ny):',
  '        _emit({"op": "seg", "x1": _r(self._x), "y1": _r(self._y),',
  '               "x2": _r(nx), "y2": _r(ny),',
  '               "p": 1 if self._pen else 0, "c": self._pc, "w": self._w,',
  '               "v": 1 if self._vis else 0})',
  '        self._x, self._y = float(nx), float(ny)',
  '        if self._fill is not None:',
  '            self._fill.append([_r(nx), _r(ny)])',
  '',
  '    def forward(self, d):',
  '        a = _math.radians(self._h)',
  '        self._goto(self._x + d * _math.cos(a), self._y + d * _math.sin(a))',
  '    fd = forward',
  '    def backward(self, d):',
  '        self.forward(-d)',
  '    bk = back = backward',
  '    def left(self, a):',
  '        self._h = (self._h + a) % 360.0',
  '    lt = left',
  '    def right(self, a):',
  '        self.left(-a)',
  '    rt = right',
  '    def goto(self, x, y=None):',
  '        if y is None:',
  '            x, y = x',
  '        self._goto(x, y)',
  '    setpos = setposition = goto',
  '    def setx(self, x): self._goto(x, self._y)',
  '    def sety(self, y): self._goto(self._x, y)',
  '    def setheading(self, a): self._h = a % 360.0',
  '    seth = setheading',
  '    def home(self):',
  '        self._goto(0, 0)',
  '        self._h = 0.0',
  '    def circle(self, radius, extent=None, steps=None):',
  '        if extent is None:',
  '            extent = 360.0',
  '        if steps is None:',
  '            frac = abs(extent) / 360.0',
  '            steps = 1 + int(min(11.5 + abs(radius) / 6.0, 59.0) * frac)',
  '        w = float(extent) / steps',
  '        w2 = 0.5 * w',
  '        l = 2.0 * radius * _math.sin(_math.radians(w2))',
  '        if radius < 0:',
  '            l, w, w2 = -l, -w, -w2',
  '        self.left(w2)',
  '        for _ in range(steps):',
  '            self.forward(l)',
  '            self.left(w)',
  '        self.left(-w2)',
  '    def dot(self, size=None, *color):',
  '        if size is None:',
  '            size = max(self._w + 4, self._w * 2)',
  '        c = (_col(color if len(color) > 1 else color[0])',
  '             if color else self._pc)',
  '        _emit({"op": "dot", "x": _r(self._x), "y": _r(self._y),',
  '               "s": size, "c": c})',
  '    def stamp(self):',
  '        _emit({"op": "stamp", "x": _r(self._x), "y": _r(self._y),',
  '               "h": _r(self._h), "c": self._pc})',
  '',
  '    def penup(self): self._pen = False',
  '    pu = up = penup',
  '    def pendown(self): self._pen = True',
  '    pd = down = pendown',
  '    def isdown(self): return self._pen',
  '    def pensize(self, w=None):',
  '        if w is None:',
  '            return self._w',
  '        self._w = w',
  '    width = pensize',
  '    def pencolor(self, *c):',
  '        if not c:',
  '            return self._pc',
  '        self._pc = _col(c if len(c) > 1 else c[0])',
  '    def fillcolor(self, *c):',
  '        if not c:',
  '            return self._fc',
  '        self._fc = _col(c if len(c) > 1 else c[0])',
  '    def color(self, *c):',
  '        if not c:',
  '            return (self._pc, self._fc)',
  '        if len(c) == 2:',
  '            self._pc = _col(c[0]); self._fc = _col(c[1])',
  '        else:',
  '            self._pc = self._fc = _col(c if len(c) > 1 else c[0])',
  '    def begin_fill(self):',
  '        self._fill = [[_r(self._x), _r(self._y)]]',
  '        self._fill_from = len(_cmds)',
  '    def end_fill(self):',
  '        if self._fill and len(self._fill) > 2:',
  '            _emit({"op": "fill", "pts": self._fill, "c": self._fc,',
  '                   "f": self._fill_from})',
  '        self._fill = None',
  '    def filling(self): return self._fill is not None',
  '    def write(self, arg, move=False, align="left",',
  '              font=("Arial", 8, "normal")):',
  '        _emit({"op": "write", "x": _r(self._x), "y": _r(self._y),',
  '               "t": str(arg), "c": self._pc, "a": align,',
  '               "f": [str(font[0]),',
  '                     int(font[1]) if len(font) > 1 else 8,',
  '                     str(font[2]) if len(font) > 2 else "normal"]})',
  '    def clear(self):',
  '        _emit({"op": "clear"})',
  '    def reset(self):',
  '        _emit({"op": "clear"})',
  '        self._x = 0.0; self._y = 0.0; self._h = 0.0',
  '        self._pen = True; self._pc = "black"; self._fc = "black"',
  '        self._w = 1; self._vis = True; self._fill = None',
  '',
  '    def hideturtle(self): self._vis = False',
  '    ht = hideturtle',
  '    def showturtle(self): self._vis = True',
  '    st = showturtle',
  '    def isvisible(self): return self._vis',
  '    def speed(self, s=None):',
  '        if s is None:',
  '            return self._speed',
  '        names = {"fastest": 0, "fast": 10, "normal": 6,',
  '                 "slow": 3, "slowest": 1}',
  '        self._speed = int(names.get(s, s))',
  '        _emit({"op": "speed", "v": self._speed})',
  '    def position(self): return Vec2D(self._x, self._y)',
  '    pos = position',
  '    def xcor(self): return self._x',
  '    def ycor(self): return self._y',
  '    def heading(self): return self._h',
  '    def distance(self, x, y=None):',
  '        if y is None:',
  '            x, y = x',
  '        return _math.hypot(x - self._x, y - self._y)',
  '    def towards(self, x, y=None):',
  '        if y is None:',
  '            x, y = x',
  '        return _math.degrees(_math.atan2(y - self._y, x - self._x)) % 360.0',
  '    def shape(self, *a, **k): pass',
  '    def shapesize(self, *a, **k): pass',
  '    turtlesize = shapesize',
  '    def tracer(self, *a, **k): pass',
  '    def undo(self): pass',
  '    def getscreen(self): return Screen()',
  '    def onclick(self, *a, **k): pass',
  '    def ondrag(self, *a, **k): pass',
  '',
  'Pen = Turtle',
  'RawTurtle = Turtle',
  'RawPen = Turtle',
  '',
  'def _default_turtle():',
  '    global _default',
  '    if _default is None:',
  '        _default = Turtle()',
  '    return _default',
  '',
  'def _make(_name):',
  '    def _f(*a, **k):',
  '        return getattr(_default_turtle(), _name)(*a, **k)',
  '    _f.__name__ = _name',
  '    return _f',
  '',
  'for _n in ("forward fd backward bk back left lt right rt goto setpos "',
  '           "setposition setx sety setheading seth home circle dot stamp "',
  '           "penup pu up pendown pd down isdown pensize width pencolor "',
  '           "fillcolor color begin_fill end_fill filling write clear reset "',
  '           "hideturtle ht showturtle st isvisible speed position pos xcor "',
  '           "ycor heading distance towards shape shapesize undo").split():',
  '    globals()[_n] = _make(_n)',
  '',
  'def bgcolor(*c):',
  '    Screen().bgcolor(*c)',
  '',
  'def colormode(m=None):',
  '    return Screen().colormode(m)',
  '',
  'def clearscreen():',
  '    Screen().clear()',
  '',
  'resetscreen = clearscreen',
  '',
  'def getscreen():',
  '    return Screen()',
  '',
  'def setup(*a, **k): pass',
  'def screensize(*a, **k): pass',
  'def title(*a, **k): pass',
  'def tracer(*a, **k): pass',
  'def update(): pass',
  'def delay(*a, **k): pass',
  'def listen(*a, **k): pass',
  'def onkey(*a, **k): pass',
  'def onscreenclick(*a, **k): pass',
  'def ontimer(*a, **k): pass',
  'def done(): pass',
  'def mainloop(): pass',
  'def exitonclick(): pass',
  'def bye(): pass',
  '',
  'def _algja_reset():',
  '    global _cmds, _turtles, _default, _colormode',
  '    _cmds = []',
  '    _turtles = []',
  '    _default = None',
  '    _colormode = 1.0',
  '    _ScreenClass._inst = None',
  '',
  'def _algja_dump():',
  '    if not _cmds:',
  '        return ""',
  '    curs = [{"x": _r(t._x), "y": _r(t._y), "h": _r(t._h), "c": t._pc}',
  '            for t in _turtles if t._vis]',
  '    return _json.dumps({"cmds": _cmds, "cursors": curs})',
  ''
].join('\n');

function post(t, m) {
  self.postMessage({ t: t, m: m });
}

// 대화형(plotly) 그림을 모으는 코드.
// 워커에는 화면이 없어 fig.show() 가 아무것도 못 하므로, show 를 가로채 두었다가
// 실행이 끝난 뒤 to_json() 으로 뽑아 메인 스레드에서 plotly.js 로 그린다.
var PLOTLY_HOOK = [
  'import sys',
  '_algja_plotly = []',
  'def _algja_plotly_patch():',
  '    go = sys.modules.get("plotly.graph_objects")',
  '    if go is None or getattr(go.Figure, "_algja", False):',
  '        return',
  '    _orig = go.Figure.show',
  '    def show(self, *a, **k):',
  '        _algja_plotly.append(self)',
  '    show._algja = True',
  '    go.Figure.show = show',
  '    go.Figure._algja = True',
  'def _algja_plotly_dump(ns=None):',
  '    go = sys.modules.get("plotly.graph_objects")',
  '    if go is None:',
  '        return []',
  '    figs = list(_algja_plotly)',
  '    if not figs and ns:',            // show() 를 부르지 않은 예제도 살린다
  '        for v in ns.values():',
  '            if isinstance(v, go.Figure) and v not in figs:',
  '                figs.append(v)',
  '    out = [f.to_json() for f in figs]',
  '    _algja_plotly.clear()',
  '    return out',
  'def _algja_reset_figs():',
  '    mod = sys.modules.get("matplotlib.pyplot")',
  '    if mod is not None:',
  '        mod.close("all")',
  '    _algja_plotly.clear()'
].join('\n');

// 준비 코드와 이번에 실행할 코드의 경계 (gen_run_preludes.py 가 넣는다)
var PRELUDE_MARK = '# ─────────── 여기까지는 앞 예제의 준비 코드입니다 ───────────';


async function ensurePyodide() {
  if (py) return py;
  post('status', '파이썬을 내려받는 중입니다 — 처음 한 번만 걸립니다');
  py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.setStdout({ batched: function (s) { post('out', s + '\n'); } });
  py.setStderr({ batched: function (s) { post('err', s + '\n'); } });
  await py.runPythonAsync(PRELUDE);
  py.runPython(PLOTLY_HOOK);
  // 가짜 turtle 모듈 등록 -- import turtle이 이 기록기를 가져가게 된다
  py.globals.set('_ALGJA_TURTLE_SRC', TURTLE_SRC);
  py.runPython([
    'import types as _types',
    '_m = _types.ModuleType("turtle")',
    '_m._algja = True',
    'exec(_ALGJA_TURTLE_SRC, _m.__dict__)',
    'sys.modules["turtle"] = _m'
  ].join('\n'));

  // 이 책의 시각화 모듈을 파이썬 파일시스템에 심어 둔다.
  // 본문 예제 대부분이 `from tuvis import *` 로 시작하는데, 브라우저 안에는
  // 그 파일이 없으므로 미리 넣어 주지 않으면 ModuleNotFoundError 가 난다.
  // (numpy·matplotlib 은 loadPackagesFromImports 가 알아서 받아 온다)
  try {
    var mods = ['tuvis.py'];
    for (var mi = 0; mi < mods.length; mi++) {
      var r = await fetch(mods[mi]);
      if (r.ok) {
        py.FS.writeFile(mods[mi], await r.text());
      } else {
        post('err', mods[mi] + ' 를 불러오지 못했습니다 (HTTP ' + r.status + ')\n');
      }
    }
    py.runPython([
      'import os, sys',
      'if os.getcwd() not in sys.path:',
      '    sys.path.insert(0, os.getcwd())'
    ].join('\n'));
    // Pyodide 에는 화면이 없다. pyplot 을 불러오기 전에 Agg 로 정해 두어야
    // 기본 백엔드가 js.document 를 찾다 실패하는 일이 없다.
    await py.loadPackage(['numpy', 'matplotlib']);
    py.runPython('import matplotlib\nmatplotlib.use("Agg")');
  } catch (e) {
    post('err', '시각화 모듈 준비 실패: ' + (e.message || e) + '\n');
  }

  return py;
}

self.onmessage = async function (ev) {
  // 미니 브라우저의 Flask 요청 -- 코드 실행이 아니라 보관된 앱에 요청을 넣는다
  if (ev.data.flaskReq) {
    try {
      var pf = await ensurePyodide();
      pf.globals.set('_algja_req_json', JSON.stringify(ev.data.flaskReq));
      post('flaskres', pf.runPython('_algja_flask_request(_algja_req_json)'));
    } catch (e) {
      post('flaskres', JSON.stringify({
        status: 500, body: '<pre>' + (e.message || e) + '</pre>', path: '/'
      }));
    }
    return;
  }

  var code = ev.data.code || '';
  var stdin = ev.data.stdin || '';
  var files = ev.data.files || [];
  var ns = null;
  // 메시지를 받았다는 신호. 이게 안 오면 창 쪽에서 워커를 되살린다.
  post('ack', '');
  try {
    var p = await ensurePyodide();

    post('status', '필요한 패키지를 확인하는 중…');
    await p.loadPackagesFromImports(code);

    // 대화형 3차원 그림(tuvis/plotly)이 필요한 코드인지 본다.
    // plotly 는 Pyodide 기본 배포에 없으므로 micropip 으로 받는다(순수 파이썬, 약 10MB).
    if (/\btuvis\b|\bplotly\b/.test(code)) {
      if (!p._algjaPlotly) {
        post('status', '대화형 3차원 그림 준비 중입니다 — 처음 한 번만 걸립니다');
        await p.loadPackage('micropip');
        await p.runPythonAsync([
          'import micropip',
          'await micropip.install("plotly")'
        ].join('\n'));
        p._algjaPlotly = true;
      }
      p.runPython('_algja_plotly_patch()');
    }

    // Flask는 순수 파이썬이라 브라우저에서도 import된다. 배포판에 없으면
    // micropip으로 PyPI에서 받아 온 뒤, run()을 가로채는 패치를 적용한다.
    if (/^\s*(?:from|import)\s+flask\b/mi.test(code)) {
      post('status', 'Flask를 준비하는 중…');
      try {
        await p.loadPackage('micropip');
        await p.runPythonAsync([
          'import importlib.util',
          'if importlib.util.find_spec("flask") is None:',
          '    import micropip',
          '    await micropip.install("flask")'
        ].join('\n'));
        p.runPython('_algja_flask_patch()');
      } catch (e) {
        post('err', 'Flask 준비 실패: ' + (e.message || e) + '\n');
      }
    }

    // matplotlib은 화면이 없으므로 Agg로 그린 뒤 PNG로 뽑아 보여 준다.
    // (plt.show()는 Agg에서 아무 일도 하지 않는다)
    //
    // 여기서 runPythonAsync를 쓰면 안 된다. import를 만나면 패키지를 자동으로
    // 받으러 가는데, 그 경로를 실행마다 타면 이따금 응답이 돌아오지 않는다.
    // 실제로 matplotlib을 쓰는 코드에서만, 동기 runPython으로 처리한다.
    if (/\bmatplotlib\b|\bpyplot\b|\bplt\b/.test(code)) {
      try {
        p.runPython('import matplotlib\nmatplotlib.use("Agg")');
      } catch (e) {
        post('err', 'matplotlib 준비 실패: ' + (e.message || e) + '\n');
      }
    }

    p.globals.set('_algja_stdin_text', stdin);
    p.runPython('_algja_stdin(_algja_stdin_text)');
    p.runPython('_algja_turtle_reset()');
    p.runPython('_algja_flask_reset()');

    // 가상 파일 -- 코드가 읽을 파일을 메모리 파일시스템에 만들어 둔다.
    // 문자열은 UTF-8로 기록되며, 파일은 워커가 사는 동안 유지된다.
    files.forEach(function (f) {
      try {
        // templates/index.html 처럼 하위 폴더가 있으면 먼저 만든다
        var parts = f.name.split('/');
        for (var i = 1; i < parts.length; i++) {
          var dir = parts.slice(0, i).join('/');
          try { p.FS.mkdir(dir); } catch (e) { /* 이미 있으면 무시 */ }
        }
        p.FS.writeFile(f.name, f.content);
      } catch (e) {
        post('err', '가상 파일 ' + f.name + ' 생성 실패: ' +
          (e.message || e) + '\n');
      }
    });
    // 실행 전 파일시스템 스냅샷 -- 실행 후 생성·변경 파일을 찾기 위함
    p.runPython('_algja_fs_mark()');

    // 실행할 때마다 빈 이름공간을 준다.
    // __name__을 "__main__"으로 두어야 if __name__ == "__main__": 블록이 돈다.
    ns = p.runPython('dict(__name__="__main__")');

    // 이어지는 예제라면 앞부분(준비 코드)은 조용히 돌린다.
    // 그러지 않으면 앞 예제의 출력과 그림까지 함께 나와 누적된 것처럼 보인다.
    var body = code;
    var mi = code.lastIndexOf(PRELUDE_MARK);
    if (mi >= 0) {
      var head = code.slice(0, mi);
      body = code.slice(mi + PRELUDE_MARK.length);
      if (head.trim()) {
        post('status', '앞 예제의 준비 코드를 먼저 실행합니다…');
        p.setStdout({ batched: function () {} });      // 출력 감추기
        p.setStderr({ batched: function () {} });
        try {
          await p.runPythonAsync(head, { globals: ns });
        } finally {
          p.setStdout({ batched: function (t) { post('out', t + '\n'); } });
          p.setStderr({ batched: function (t) { post('err', t + '\n'); } });
        }
        p.runPython('_algja_reset_figs()');            // 준비 코드의 그림도 버린다
      }
    }

    post('status', '실행 중…');
    await p.runPythonAsync(body, { globals: ns });

    var figs = p.runPython('_algja_figs()');
    var list = figs && figs.toJs ? figs.toJs() : [];
    if (figs && figs.destroy) figs.destroy();

    post('figs', list);

    // 대화형 그림 (plotly)
    try {
      p.globals.set('_algja_ns', ns);
      var pj = p.runPython('_algja_plotly_dump(_algja_ns)');
      var plist = pj && pj.toJs ? pj.toJs() : [];
      if (pj && pj.destroy) pj.destroy();
      if (plist.length) post('plotly', plist);
    } catch (e) { /* plotly 를 안 쓴 코드면 그냥 넘어간다 */ }
    var tj = p.runPython('_algja_turtle_dump()');
    if (tj) post('turtle', tj);
    var gf = p.runPython('_algja_fs_diff()');
    if (gf && gf !== '[]') post('gfiles', gf);
    var fk = p.runPython('_algja_flask_dump()');
    if (fk) post('flask', fk);
    post('done', '');
  } catch (err) {
    post('err', (err && err.message ? err.message : String(err)) + '\n');
    // 오류가 났어도 그 전까지 그린 터틀 그림·생성된 파일은 보여 준다
    try {
      if (py) {
        var tj2 = py.runPython('_algja_turtle_dump()');
        if (tj2) post('turtle', tj2);
        var gf2 = py.runPython('_algja_fs_diff()');
        if (gf2 && gf2 !== '[]') post('gfiles', gf2);
      }
    } catch (e2) {}
    post('done', '');
  } finally {
    if (ns && ns.destroy) ns.destroy();
  }
};
