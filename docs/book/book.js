// 알짜 파이썬 웹 본문 — 인터랙션 (DESIGN.md 기반)
// 1) 스크롤 리빌  2) 그림 클릭 → 별도 창 확대 보기  3) 코드 복사 버튼

// ---- 1) 스크롤 리빌 ----
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var targets = document.querySelectorAll(
    '.content figure.fig, .content .box, .content .listing, ' +
    '.content .table-wrap, .content pre.line-numbers, ' +
    '.content .filecode-wrap, ' +
    '.content pre.pyout, .content pre.termout, .cover-wrap');
  targets.forEach(function (el) { el.classList.add('reveal'); });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -5% 0px' });
  targets.forEach(function (el) { io.observe(el); });
})();

// ---- 1.5) 사이드바 링크 클릭 시 모바일 목차 서랍 닫기 ----
// 절(#anchor) 링크는 페이지 이동이 없어 서랍이 열린 채 본문을 가리는 문제 방지
(function () {
  document.querySelectorAll('.sidebar a').forEach(function (a) {
    a.addEventListener('click', function () {
      document.body.classList.remove('nav-open');
    });
  });
})();

// ---- 1.6) 접힌 박스(details)로의 앵커 이동 시 자동 펼침 ----
// 사이드바에서 "연습문제"를 누르면 접힌 상태로 이동해 보이지 않는 문제 방지
(function () {
  function openTarget() {
    var id = location.hash.replace('#', '');
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === 'DETAILS') el.open = true;
  }
  window.addEventListener('hashchange', openTarget);
  openTarget();
})();

// ---- 2) 그림 클릭 → 별도 창 확대 ----
(function () {
  var imgs = document.querySelectorAll(
    '.content img.tikz, .content img.gfx, .content img.shot, ' +
    '.content img.chapfig, .content img.cover');
  imgs.forEach(function (img) {
    img.classList.add('zoomable');
    img.title = '클릭하면 새 창에서 크게 볼 수 있습니다';
    img.addEventListener('click', function () {
      var src = img.getAttribute('src');
      var w = Math.min(window.screen.availWidth, 1280);
      var h = Math.min(window.screen.availHeight, 900);
      window.open('viewer.html?src=' + encodeURIComponent(src),
        'figviewer', 'width=' + w + ',height=' + h +
        ',menubar=no,toolbar=no,location=no,status=no');
    });
  });
})();

// ---- 3) 코드 복사 · 실행 버튼 ----
(function () {
  var COPY_ICON =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" ' +
    'rx="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 ' +
    '2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
  var OK_ICON =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" ' +
    'stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';

  var RUN_ICON =
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" ' +
    'stroke="none"><polygon points="6 3 21 12 6 21"></polygon></svg>';

  // 파일 소스(pre.filecode: HTML 템플릿 등)는 실행 대상이 아니라 복사만 붙인다
  document.querySelectorAll(
    '.content pre.line-numbers, .content pre.filecode'
  ).forEach(function (pre) {
    var codeEl = pre.querySelector('code');
    if (!codeEl) return;
    var wrap = document.createElement('div');
    wrap.className = 'code-wrap';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);
    var bar = document.createElement('div');
    bar.className = 'code-actions';
    wrap.appendChild(bar);

    if (!pre.classList.contains('filecode')) {
      var runBtn = document.createElement('button');
      runBtn.className = 'copy-btn run-btn';
      runBtn.type = 'button';
      runBtn.title = '이 코드를 창에서 고쳐 가며 실행해 봅니다';
      runBtn.innerHTML = RUN_ICON + '<span>실행</span>';
      bar.appendChild(runBtn);
      runBtn.addEventListener('click', function () {
        window.algjaRunner.open(codeEl.textContent.replace(/\n$/, ''));
      });
    }

    var btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.type = 'button';
    btn.title = '코드 복사 (행번호 제외)';
    btn.innerHTML = COPY_ICON + '<span>복사</span>';
    bar.appendChild(btn);
    btn.addEventListener('click', function () {
      // Prism 토큰만 담긴 code 요소의 textContent에는 행번호가 포함되지 않음
      var text = codeEl.textContent.replace(/\n$/, '');
      function done(ok) {
        btn.innerHTML = ok ? OK_ICON + '<span>복사됨</span>'
                           : COPY_ICON + '<span>실패</span>';
        btn.classList.toggle('ok', ok);
        setTimeout(function () {
          btn.innerHTML = COPY_ICON + '<span>복사</span>';
          btn.classList.remove('ok');
        }, 1600);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { done(true); }, function () { done(false); });
      } else {
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        var ok = false;
        try { ok = document.execCommand('copy'); } catch (e) {}
        document.body.removeChild(ta);
        done(ok);
      }
    });
  });
})();

// ---- 4) 코드 실행 창 (Pyodide 워커) ----
// 브라우저는 방문자 PC의 파이썬을 실행할 수 없다(샌드박스). 대신 CPython을
// WebAssembly로 포팅한 Pyodide를 워커에서 돌린다. 설치가 필요 없고 결과는
// 실제 CPython 3.14와 같다. 다만 화면·서버가 필요한 모듈은 쓸 수 없다.
// turtle은 예외 -- 워커의 가짜 turtle 모듈이 그리기 명령을 기록해 보내면
// 여기서 캔버스에 거북이 애니메이션으로 재생한다(시뮬레이터).
window.algjaRunner = (function () {
  var RUN_TIMEOUT_MS = 20000;
  // Flask는 처음 실행 때 휠을 내려받아 준비 시간이 더 걸리므로 별도 상한을 둔다
  var FLASK_TIMEOUT_MS = 45000;
  var FLASK_RE = /^\s*(?:from|import)\s+flask\b/mi;
  var UNSUPPORTED = [
    [/^\s*(?:import|from)\s+tkinter\b/m, 'tkinter',
     'tkinter GUI는 운영체제의 창이 필요해 브라우저 안에서는 동작하지 않습니다.']
  ];

  // ---- 가상 파일 ----
  // 파일을 읽는 예제는 실제 파일이 없어 브라우저에서 실패한다. 코드가 읽는
  // 파일 이름을 찾아 '가상 파일' 상자를 보여 주고, 실행 전에 그 내용을
  // Pyodide의 메모리 파일시스템에 만들어 둔다. 아래는 책 예제가 읽는
  // 파일들의 기본 내용 -- 본문에 실린 데이터와 일치시킨다.
  var VFILE_DEFAULTS = {
    'hello.txt': 'Hello World!\nPython file I/O\n',
    'numbers.txt': '10\n20\n30\n40\n50\n',
    'members_raw.txt':
      'Hong Gildong / 010-1234-5678 / hong@email.com / Seoul\n' +
      'Kim Yusin 010.9876.5432 kim_ys@company.co.kr Busan\n' +
      'Lee Sunsin, 010 1111 2222, lee@navy.kr, Yeosu\n' +
      ' Kang Gamchan (010)3333-4444 kang@goryeo.com Kaesong\n' +
      'Jang Yeongshil / 010-5555-6666 / jang@joseon.kr / Seoul\n' +
      'Yulgok 010.7777.8888 yulgok@edu.kr Paju\n' +
      'Shin Saimdang, 01022223333, shin@art.com, Gangneung\n' +
      'Sejong 010-9999-0000 sejong@hangul.kr Seoul\n',
    'log.txt':
      '2026-07-24 09:12:01 INFO  Server started\n' +
      '2026-07-24 09:12:35 ERROR Connection lost\n' +
      '2026-07-24 09:13:02 INFO  Retry attempt 1\n' +
      '2026-07-24 09:13:40 ERROR Disk full\n' +
      '2026-07-24 09:14:11 INFO  Service recovered\n',
    // Flask render_template() 예제가 읽는 HTML 템플릿 (본문 filecode와 동일)
    'templates/index.html':
      '<!DOCTYPE html>\n<html>\n<head><title>To-Do List</title></head>\n' +
      '<body>\n    <h1>To-Do List</h1>\n    <ul>\n' +
      '        {% for task in tasks %}\n        <li>{{ task }}</li>\n' +
      '        {% endfor %}\n    </ul>\n</body>\n</html>\n',
    'templates/todo.html':
      '<!DOCTYPE html>\n<html>\n<head><title>To-Do App</title></head>\n' +
      '<body>\n    <h1>To-Do List ({{ tasks|length }} items)</h1>\n' +
      '    <form action="/add" method="post">\n' +
      '        <input type="text" name="task" placeholder="Enter a task">\n' +
      '        <button type="submit">Add</button>\n    </form>\n    <ul>\n' +
      '        {% for task in tasks %}\n        <li>{{ task }}\n' +
      '            <a href="/delete/{{ loop.index0 }}">[X]</a>\n' +
      '        </li>\n        {% endfor %}\n    </ul>\n</body>\n</html>\n'
  };

  // 코드에서 "미리 만들어 둘 파일" 이름을 찾는다.
  //  - 일부러 없는 파일을 여는 오류 예제(nonexistent 등)는 제외
  //  - 예제가 스스로 먼저 쓰는(w/a) 파일은 만들 필요가 없어 제외
  //  - 그 밖에는 기본 내용이 있거나 open()으로 직접 여는 파일만 포함
  function detectVFiles(code) {
    var out = [], seen = {};
    var re = /['"]([\w.\-]+\.(?:txt|csv|json|log|dat|md))['"]/g;
    var m;
    while ((m = re.exec(code))) {
      var name = m[1];
      if (seen[name]) continue;
      seen[name] = true;
      if (/nonexist|no_such|not_found/i.test(name)) continue;
      var q = name.replace(/\./g, '\\.');
      var anyOpen = code.search(
        new RegExp("open\\(\\s*['\"]" + q + "['\"]\\s*[,)]"));
      var writeOpen = code.search(
        new RegExp("open\\(\\s*['\"]" + q + "['\"]\\s*,\\s*['\"][wax]"));
      if (writeOpen !== -1 && writeOpen <= anyOpen) continue;
      if (!(name in VFILE_DEFAULTS) && anyOpen === -1) continue;
      out.push(name);
    }
    // Flask render_template('X.html') → templates/X.html 을 함께 제공한다
    var tre = /render_template\(\s*['"]([\w.\-]+\.html)['"]/g;
    while ((m = tre.exec(code))) {
      var tpath = 'templates/' + m[1];
      if (seen[tpath] || !(tpath in VFILE_DEFAULTS)) continue;
      seen[tpath] = true;
      out.push(tpath);
    }
    return out;
  }

  // ---- 예시 입력값 ----
  // input() 예제는 대화형 입력이 불가능해 '입력값' 상자로 미리 받는다.
  // 예제마다 어울리는 예시 입력을 stdin-defaults.json(코드 해시 → 입력값,
  // WebBook/gen_stdin_defaults.py로 생성)에서 읽어 상자를 미리 채워 준다.
  var stdinDefaults = null;
  fetch('stdin-defaults.json')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { stdinDefaults = d; })
    .catch(function () { /* 없으면 빈 상자로 동작 */ });

  // ---- 실행 준비 코드 ----
  // 앞 리스팅에 이어지는 연속 예제(예: 코드 4.7)는 단독으로 돌 수 없다.
  // run-preludes.json(코드 해시 → 준비 코드, WebBook/gen_run_preludes.py로
  // 생성)에서 찾아, 실행 창을 열 때 준비 코드를 앞에 붙여 보여 준다.
  var runPreludes = null;
  fetch('run-preludes.json')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { runPreludes = d; })
    .catch(function () { /* 없으면 원본 코드 그대로 동작 */ });

  // 문법 틀·의사코드 블록(코드 4.1, 7.1 등)의 해시 목록.
  // 실행하면 개념 코드라는 안내만 출력한다. 코드를 고치면 정상 실행된다.
  var conceptCodes = null;
  fetch('concept-codes.json')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { conceptCodes = d; })
    .catch(function () { /* 없으면 일반 코드처럼 실행을 시도한다 */ });

  // google.colab import 없이 코랩 환경(마운트된 드라이브 등)에 의존하는
  // 연속 블록의 해시 → 책에 제시된 출력. 실행 대신 그 출력을 보여 준다.
  var colabCodes = null;
  fetch('colab-codes.json')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { colabCodes = d; })
    .catch(function () { /* 없으면 일반 코드처럼 실행을 시도한다 */ });

  // stdin-defaults.json의 키와 같은 djb2-xor 해시 (gen_stdin_defaults.py 참고)
  function codeKey(s) {
    var h = 5381;
    for (var i = 0; i < s.length; i++) {
      h = (Math.imul(h, 33) ^ s.charCodeAt(i)) >>> 0;
    }
    return h.toString(36);
  }

  var dlg = null, ui = {}, worker = null, timer = null, original = '';
  // 워커는 창을 닫아도 살려 둔다 -- 파이썬을 한 번만 올리기 위해서다.
  // ready: 파이썬이 이미 올라와 있는가, busy: 지금 실행 중인가
  var ready = false, busy = false, startedAt = 0;

  function build() {
    dlg = document.createElement('dialog');
    dlg.className = 'runner';
    dlg.setAttribute('aria-label', '코드 실행');
    dlg.innerHTML =
      '<div class="runner-head">' +
        '<span class="runner-title">코드 실행</span>' +
        '<span class="runner-hint">Ctrl+Enter 실행 · Esc 닫기</span>' +
        '<button type="button" class="runner-close" aria-label="닫기">&#10005;</button>' +
      '</div>' +
      '<textarea class="runner-code" spellcheck="false" ' +
        'aria-label="파이썬 코드"></textarea>' +
      '<div class="runner-stdin-wrap" hidden>' +
        '<label class="runner-label" for="algja-stdin">입력값' +
        '<span> — input() 이 읽어 갈 값을 한 줄에 하나씩</span></label>' +
        '<textarea id="algja-stdin" class="runner-stdin" rows="2" ' +
          'spellcheck="false"></textarea>' +
      '</div>' +
      '<div class="runner-files-wrap" hidden>' +
        '<label class="runner-label">가상 파일' +
        '<span> — 코드가 읽을 파일을 실행 전에 만들어 둡니다. ' +
        '내용은 고쳐도 됩니다</span></label>' +
        '<div class="runner-files"></div>' +
      '</div>' +
      '<div class="runner-bar">' +
        '<button type="button" class="runner-run">실행</button>' +
        '<button type="button" class="runner-stop" hidden>중지</button>' +
        '<button type="button" class="runner-reset">원래 코드로</button>' +
        '<span class="runner-status"></span>' +
      '</div>' +
      '<pre class="runner-out" aria-live="polite"></pre>' +
      '<div class="runner-figs"></div>' +
      '<div class="runner-web" hidden>' +
        '<div class="runner-web-head">' +
          '<span class="web-dot"></span><span class="web-dot"></span>' +
          '<span class="web-dot"></span>' +
          '<form class="web-addr-form">' +
            '<span class="web-host">127.0.0.1:5000</span>' +
            '<input class="web-addr" spellcheck="false" value="/" ' +
              'aria-label="접속 경로">' +
            '<button type="submit" class="web-go">이동</button>' +
          '</form>' +
        '</div>' +
        '<div class="web-routes"></div>' +
        // allow-scripts로 가로채기 스크립트만 돌린다. allow-same-origin·allow-forms는
        // 주지 않아 iframe이 부모·쿠키에 접근하거나 폼을 실제 전송할 수 없다(안전).
        // 링크·폼은 renderFlaskResponse에서 data-*로 바꿔 navigation을 제거한다.
        '<iframe class="web-view" sandbox="allow-scripts" ' +
          'title="Flask 앱 미리 보기"></iframe>' +
        '<div class="web-note">미니 브라우저 — 실제 서버가 아니라 ' +
          '시뮬레이터입니다. 내 컴퓨터의 파이썬에서는 별도의 웹 서버가 뜹니다.' +
        '</div>' +
      '</div>';
    document.body.appendChild(dlg);

    ui.code = dlg.querySelector('.runner-code');
    ui.stdinWrap = dlg.querySelector('.runner-stdin-wrap');
    ui.stdin = dlg.querySelector('.runner-stdin');
    ui.filesWrap = dlg.querySelector('.runner-files-wrap');
    ui.files = dlg.querySelector('.runner-files');
    ui.run = dlg.querySelector('.runner-run');
    ui.stop = dlg.querySelector('.runner-stop');
    ui.reset = dlg.querySelector('.runner-reset');
    ui.status = dlg.querySelector('.runner-status');
    ui.out = dlg.querySelector('.runner-out');
    ui.figs = dlg.querySelector('.runner-figs');
    ui.web = dlg.querySelector('.runner-web');
    ui.webForm = dlg.querySelector('.web-addr-form');
    ui.webAddr = dlg.querySelector('.web-addr');
    ui.webRoutes = dlg.querySelector('.web-routes');
    ui.webView = dlg.querySelector('.web-view');

    ui.webForm.addEventListener('submit', function (e) {
      e.preventDefault();
      flaskNavigate({ method: 'GET', path: ui.webAddr.value.trim() || '/' });
    });

    dlg.querySelector('.runner-close').addEventListener('click', close);
    // 창을 닫을 때는 돌고 있는 것만 끊는다. 놀고 있는 워커는 그대로 두어야
    // 다음에 열었을 때 파이썬을 다시 내려받지 않는다.
    dlg.addEventListener('close', function () {
      if (busy) abortRun();
      stopTurtle();
      stopFlask();
    });
    ui.run.addEventListener('click', run);
    ui.stop.addEventListener('click', function () {
      abortRun();
      setStatus('중지했습니다.');
    });
    ui.reset.addEventListener('click', function () {
      ui.code.value = original;
      syncStdinBox();
      syncFilesBox();
      ui.code.focus();
    });

    // 파이썬 책이니 Tab은 4칸 들여쓰기로 넣는다 (포커스 이동이 아니라)
    ui.code.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') {
        e.preventDefault();
        var s = ui.code.selectionStart, t = ui.code.selectionEnd;
        ui.code.value = ui.code.value.slice(0, s) + '    ' + ui.code.value.slice(t);
        ui.code.selectionStart = ui.code.selectionEnd = s + 4;
      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        run();
      }
    });
    ui.code.addEventListener('input', function () {
      syncStdinBox();
      syncFilesBox();
    });
  }

  function syncStdinBox() {
    ui.stdinWrap.hidden = !/\binput\s*\(/.test(ui.code.value);
  }

  // 감지된 파일 목록에 맞춰 항목을 더하고 빼되,
  // 이미 있는 항목은 그대로 두어 사용자가 고친 내용을 지킨다
  function syncFilesBox() {
    var names = detectVFiles(ui.code.value);
    var have = {};
    ui.files.querySelectorAll('.vfile').forEach(function (el) {
      var n = el.getAttribute('data-name');
      if (names.indexOf(n) === -1) el.remove();
      else have[n] = true;
    });
    names.forEach(function (n) {
      if (have[n]) return;
      var item = document.createElement('div');
      item.className = 'vfile';
      item.setAttribute('data-name', n);
      var label = document.createElement('div');
      label.className = 'vfile-name';
      label.textContent = n;
      var ta = document.createElement('textarea');
      ta.className = 'vfile-body';
      ta.rows = 3;
      ta.spellcheck = false;
      ta.value = VFILE_DEFAULTS[n] || '';
      item.appendChild(label);
      item.appendChild(ta);
      ui.files.appendChild(item);
    });
    ui.filesWrap.hidden = !names.length;
  }

  function collectVFiles() {
    var out = [];
    ui.files.querySelectorAll('.vfile').forEach(function (el) {
      out.push({
        name: el.getAttribute('data-name'),
        content: el.querySelector('textarea').value
      });
    });
    return out;
  }

  function setStatus(msg) { ui.status.textContent = msg || ''; }

  // ---- 실행으로 생성·변경된 파일 표시 ----
  // 워커가 실행 전후 파일시스템 스냅샷을 비교해 보낸 목록을
  // 실행 결과 아래에 파일명 + 내용으로 보여 준다.
  function renderGenFiles(json) {
    var list;
    try { list = JSON.parse(json); } catch (e) { return; }
    if (!list.length) return;
    var wrap = document.createElement('div');
    wrap.className = 'gen-files';
    var head = document.createElement('div');
    head.className = 'gen-files-head';
    head.textContent = '실행으로 생성·변경된 파일';
    wrap.appendChild(head);
    list.forEach(function (f) {
      var item = document.createElement('div');
      item.className = 'gen-file';
      var label = document.createElement('div');
      label.className = 'vfile-name';
      label.textContent = f.name;
      item.appendChild(label);
      var pre = document.createElement('pre');
      pre.className = 'gen-file-body';
      pre.textContent = f.binary !== undefined
        ? '(텍스트가 아닌 파일 — ' + f.binary + '바이트)'
        : f.content;
      item.appendChild(pre);
      wrap.appendChild(item);
    });
    ui.figs.appendChild(wrap);
  }

  // ---- Flask 미니 브라우저 ----
  // 워커가 앱을 잡아 두면, 여기서 경로를 입력받아 test_client로 요청을 보내고
  // 돌아온 HTML을 샌드박스 iframe에 렌더링한다. 실제 서버·포트는 없다.
  var flaskReady = false;

  function showFlask(json) {
    var data;
    try { data = JSON.parse(json); } catch (e) { return; }
    var routes = data.routes || [];
    flaskReady = true;
    ui.web.hidden = false;

    // 라우트 목록을 클릭 가능한 칩으로 (동적 인자 <name>은 예시값으로 치환)
    ui.webRoutes.innerHTML = '';
    var lead = document.createElement('span');
    lead.className = 'web-routes-lead';
    lead.textContent = '경로:';
    ui.webRoutes.appendChild(lead);
    routes.forEach(function (r) {
      if (r.methods.indexOf('GET') === -1) return;
      var demo = r.rule.replace(/<[^>]*?([^:>]+)>/g, function (_, name) {
        return name === 'name' ? 'Python' : '1';
      });
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'web-route';
      chip.textContent = demo;
      chip.addEventListener('click', function () {
        ui.webAddr.value = demo;
        flaskNavigate({ method: 'GET', path: demo });
      });
      ui.webRoutes.appendChild(chip);
    });
    flaskNavigate({ method: 'GET', path: ui.webAddr.value.trim() || '/' });
    // 미니 브라우저가 창 아래쪽에 생기므로, 보이도록 스크롤해 준다
    if (ui.web.scrollIntoView) {
      ui.web.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function flaskNavigate(req) {
    if (!flaskReady || !worker) return;
    setStatus('요청 중… ' + (req.method || 'GET') + ' ' + req.path);
    worker.postMessage({ flaskReq: req });
  }

  function renderFlaskResponse(json) {
    var res;
    try { res = JSON.parse(json); } catch (e) { return; }
    if (res.path) ui.webAddr.value = res.path;

    // 돌아온 HTML에서 링크·폼의 네비게이션을 없앤다. 샌드박스 iframe은
    // href/action이 남아 있으면 우리 핸들러를 거치지 않고 곧장 이동해 버려
    // 화면이 갱신되지 않는다. 목적지를 data-*로 옮기고 클릭만 가로채
    // 부모(→워커)로 넘긴다.
    var doc = new DOMParser().parseFromString(res.body || '', 'text/html');
    doc.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href');
      if (/^(https?:|mailto:|#)/i.test(href)) { a.setAttribute('target', '_blank'); return; }
      a.setAttribute('data-href', href);
      a.removeAttribute('href');
    });
    doc.querySelectorAll('form').forEach(function (f) {
      f.setAttribute('data-action', f.getAttribute('action') || res.path || '/');
      f.setAttribute('data-method', (f.getAttribute('method') || 'GET').toUpperCase());
      f.removeAttribute('action');
      f.removeAttribute('method');
    });
    var bodyHtml = doc.body ? doc.body.innerHTML : (res.body || '');

    var head =
      '<style>body{font-family:system-ui,-apple-system,sans-serif;' +
      'margin:14px;color:#222;line-height:1.5}a[data-href]{color:#c85f32;' +
      'cursor:pointer;text-decoration:underline}button,input{font:inherit}</style>';
    // 링크·폼 버튼 클릭과 Enter 키를 잡아 요청을 부모로 보낸다 (navigation 없음)
    var bridge =
      '<scr' + 'ipt>' +
      'function send(m,p,d){parent.postMessage({algjaFlask:{method:m,path:p,' +
      'data:d||{}}},"*");}' +
      'function sub(f){var d={};new FormData(f).forEach(function(v,k){d[k]=v;});' +
      'send(f.getAttribute("data-method")||"GET",f.getAttribute("data-action")||"/",d);}' +
      'document.addEventListener("click",function(e){' +
      'var a=e.target.closest("[data-href]");' +
      'if(a){e.preventDefault();send("GET",a.getAttribute("data-href"));return;}' +
      'var b=e.target.closest("button,input[type=submit]");' +
      'if(b&&b.type!=="reset"){var f=b.closest("form");' +
      'if(f){e.preventDefault();sub(f);}}' +
      '});' +
      'document.addEventListener("keydown",function(e){' +
      'if(e.key==="Enter"&&e.target.form){e.preventDefault();sub(e.target.form);}' +
      '});' +
      '</scr' + 'ipt>';
    ui.webView.srcdoc = head + bodyHtml + bridge;
    setStatus('완료 — ' + (res.status || 200) + ' ' + (res.path || ''));
  }

  // iframe 안에서 올라오는 링크·폼 메시지를 받아 다시 요청으로 넘긴다
  window.addEventListener('message', function (e) {
    if (e.data && e.data.algjaFlask && dlg && dlg.open) {
      flaskNavigate(e.data.algjaFlask);
    }
  });

  function stopFlask() {
    flaskReady = false;
    if (ui.web) {
      ui.web.hidden = true;
      ui.webView.srcdoc = '';
      ui.webRoutes.innerHTML = '';
      ui.webAddr.value = '/';
    }
  }

  // ---- 터틀 그래픽 시뮬레이터 (재생기) ----
  // 워커가 보낸 그리기 명령을 캔버스 두 장(그림 + 거북이 커서)에 재생한다.
  var turtleAnim = null;

  function stopTurtle() {
    if (turtleAnim) { cancelAnimationFrame(turtleAnim.raf); turtleAnim = null; }
  }

  // 대화형 3차원 그림 (plotly)
  // 워커는 그림의 JSON 만 보내온다. 실제 그리기는 여기서 plotly.js 로 한다.
  var plotlyReady = null;
  function loadPlotly() {
    if (plotlyReady) return plotlyReady;
    plotlyReady = new Promise(function (resolve, reject) {
      if (window.Plotly) return resolve();
      var sc = document.createElement('script');
      sc.src = 'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js';
      sc.onload = function () { resolve(); };
      sc.onerror = function () { reject(new Error('plotly.js 로드 실패')); };
      document.head.appendChild(sc);
    });
    return plotlyReady;
  }

  function renderPlotly(list) {
    loadPlotly().then(function () {
      (list || []).forEach(function (json) {
        var spec;
        try { spec = JSON.parse(json); }
        catch (e) { append('err', '그림을 읽지 못했습니다\n'); return; }
        var div = document.createElement('div');
        div.className = 'runner-plotly';
        ui.figs.appendChild(div);
        var layout = spec.layout || {};
        layout.autosize = true;
        delete layout.width;                 // 창 너비에 맞춘다
        window.Plotly.newPlot(div, spec.data || [], layout,
                              { responsive: true, displaylogo: false });
      });
    }).catch(function (e) {
      append('err', (e.message || e) + '\n');
    });
  }

  function renderTurtle(json) {
    var data;
    try { data = JSON.parse(json); } catch (e) { return; }
    var cmds = data.cmds || [];
    var cursors = data.cursors || [];
    if (!cmds.length) return;
    stopTurtle();

    // 잉크가 닿는 영역을 재서 캔버스에 맞게 축척·중심을 정한다
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    function grow(x, y, pad) {
      if (x - pad < minX) minX = x - pad;
      if (x + pad > maxX) maxX = x + pad;
      if (y - pad < minY) minY = y - pad;
      if (y + pad > maxY) maxY = y + pad;
    }
    cmds.forEach(function (c) {
      if (c.op === 'seg' && c.p) { grow(c.x1, c.y1, c.w); grow(c.x2, c.y2, c.w); }
      else if (c.op === 'dot') grow(c.x, c.y, c.s / 2);
      else if (c.op === 'stamp') grow(c.x, c.y, 12);
      else if (c.op === 'write') grow(c.x, c.y, 30);
      else if (c.op === 'fill') {
        c.pts.forEach(function (p) { grow(p[0], p[1], 0); });
      }
    });
    cursors.forEach(function (c) { grow(c.x, c.y, 14); });
    if (minX > maxX) { minX = minY = -100; maxX = maxY = 100; }

    var W = 560;
    var bw = Math.max(maxX - minX, 10), bh = Math.max(maxY - minY, 10);
    var H = Math.max(240, Math.min(460, Math.round(W * bh / bw)));
    var MARGIN = 24;
    var scale = Math.min(1, (W - MARGIN * 2) / bw, (H - MARGIN * 2) / bh);
    var cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    function tx(x) { return W / 2 + (x - cx) * scale; }
    function ty(y) { return H / 2 - (y - cy) * scale; }  // 터틀 y축은 위가 +

    var wrap = document.createElement('div');
    wrap.className = 'turtle-wrap';
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var scene = document.createElement('canvas');
    var over = document.createElement('canvas');
    over.className = 'turtle-over';
    [scene, over].forEach(function (cv) {
      cv.width = Math.round(W * dpr);
      cv.height = Math.round(H * dpr);
    });
    wrap.appendChild(scene);
    wrap.appendChild(over);
    var note = document.createElement('div');
    note.className = 'turtle-note';
    note.textContent =
      '터틀 그래픽 시뮬레이터 — 내 컴퓨터의 파이썬에서는 별도의 창이 열립니다';
    ui.figs.appendChild(wrap);
    ui.figs.appendChild(note);

    var ctx = scene.getContext('2d');
    var octx = over.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    octx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var bg = '#ffffff';
    var speed = 3;

    function paintBg() {
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);
    }

    function drawSeg(c) {
      if (!c.p || (c.x1 === c.x2 && c.y1 === c.y2)) return;
      ctx.beginPath();
      ctx.moveTo(tx(c.x1), ty(c.y1));
      ctx.lineTo(tx(c.x2), ty(c.y2));
      ctx.strokeStyle = c.c;
      ctx.lineWidth = Math.max(1, c.w * scale);
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    // 거북이 커서(작은 화살촉). 터틀 각도는 반시계 +이고 화면 y는 아래가 +
    function drawShape(g, x, y, h, color) {
      g.save();
      g.translate(tx(x), ty(y));
      g.rotate(-h * Math.PI / 180);
      g.beginPath();
      g.moveTo(11, 0); g.lineTo(-5, 6); g.lineTo(-2, 0); g.lineTo(-5, -6);
      g.closePath();
      g.globalAlpha = 0.9;
      g.fillStyle = color || '#222';
      g.fill();
      g.restore();
    }

    function applyOp(c, idx) {
      if (c.op === 'bg') { bg = c.c; redraw(idx); }
      else if (c.op === 'clear') { paintBg(); }
      else if (c.op === 'speed') { speed = c.v; }
      else if (c.op === 'dot') {
        ctx.beginPath();
        ctx.arc(tx(c.x), ty(c.y), Math.max(1, c.s * scale / 2), 0, Math.PI * 2);
        ctx.fillStyle = c.c;
        ctx.fill();
      } else if (c.op === 'fill') {
        ctx.beginPath();
        c.pts.forEach(function (p, i) {
          if (i) ctx.lineTo(tx(p[0]), ty(p[1]));
          else ctx.moveTo(tx(p[0]), ty(p[1]));
        });
        ctx.closePath();
        ctx.fillStyle = c.c;
        ctx.fill();
        // 채우기가 이미 그린 윤곽선을 덮으므로 윤곽선을 한 번 더 그린다
        for (var i = c.f; i < idx; i++) {
          if (cmds[i].op === 'seg') drawSeg(cmds[i]);
        }
      } else if (c.op === 'write') {
        var style = /italic/.test(c.f[2]) ? 'italic ' : '';
        if (/bold/.test(c.f[2])) style += 'bold ';
        ctx.font = style + Math.max(7, Math.round(c.f[1] * scale * 1.33)) +
          'px "' + c.f[0] + '", sans-serif';
        ctx.textAlign = c.a === 'center' ? 'center'
          : (c.a === 'right' ? 'right' : 'left');
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = c.c;
        ctx.fillText(c.t, tx(c.x), ty(c.y));
      } else if (c.op === 'stamp') {
        drawShape(ctx, c.x, c.y, c.h, c.c);
      }
    }

    // 배경색이 중간에 바뀌면 새 배경 위에 지금까지의 그림을 다시 그린다
    function redraw(upto) {
      paintBg();
      var start = 0, i;
      for (i = 0; i < upto; i++) if (cmds[i].op === 'clear') start = i + 1;
      for (i = start; i < upto; i++) {
        var c = cmds[i];
        if (c.op === 'seg') drawSeg(c);
        else if (c.op !== 'bg' && c.op !== 'clear') applyOp(c, i);
      }
    }

    // 선분 하나에 쓸 시간(ms). speed(0)=최고 속도. 그림이 작으면 과정이
    // 보이게 조금 늦추고, 아무리 느린 speed라도 전체 15초는 넘기지 않는다.
    var segTotal = 0;
    cmds.forEach(function (c) { if (c.op === 'seg') segTotal++; });
    var minPace = Math.min(200, 900 / Math.max(segTotal, 1));
    function segCost() {
      var base = speed === 0 ? 0.4 : 260 / speed;
      base = Math.min(base, 15000 / Math.max(segTotal, 1));
      return Math.max(base, minPace);
    }

    var idx = 0, pending = 0, last = 0, cur = null;
    paintBg();
    turtleAnim = { raf: 0 };
    function frame(now) {
      if (!last) last = now;
      pending += Math.min(now - last, 100);
      last = now;
      var guard = 20000;
      while (idx < cmds.length && guard--) {
        var c = cmds[idx];
        if (c.op === 'seg') {
          if (pending < segCost()) break;
          pending -= segCost();
          drawSeg(c);
          var dx = c.x2 - c.x1, dy = c.y2 - c.y1;
          cur = {
            x: c.x2, y: c.y2, v: c.v, c: c.c,
            h: (dx || dy) ? Math.atan2(dy, dx) * 180 / Math.PI
                          : (cur ? cur.h : 0)
          };
        } else {
          applyOp(c, idx);
        }
        idx++;
      }
      octx.clearRect(0, 0, W, H);
      if (idx < cmds.length) {
        if (cur && cur.v) drawShape(octx, cur.x, cur.y, cur.h, cur.c);
        turtleAnim.raf = requestAnimationFrame(frame);
      } else {
        cursors.forEach(function (c) { drawShape(octx, c.x, c.y, c.h, c.c); });
        turtleAnim = null;
      }
    }
    turtleAnim.raf = requestAnimationFrame(frame);
  }

  function append(cls, text) {
    var span = document.createElement('span');
    if (cls) span.className = cls;
    span.textContent = text;
    ui.out.appendChild(span);
    ui.out.scrollTop = ui.out.scrollHeight;
  }

  // 실행 하나가 끝났을 때 -- UI만 되돌리고 워커는 살려 둔다.
  // 워커를 죽이면 다음 실행 때 파이썬을 처음부터 다시 올려야 한다.
  function endRun() {
    if (timer) { clearTimeout(timer); timer = null; }
    busy = false;
    ui.run.disabled = false;
    ui.stop.hidden = true;
  }

  // 중지·시간 초과 -- 돌고 있는 파이썬을 멈출 방법은 워커를 죽이는 것뿐이다.
  // 이 경우에만 다음 실행이 다시 준비 과정을 거친다.
  function abortRun() {
    if (worker) { worker.terminate(); worker = null; }
    ready = false;
    flaskReady = false;   // 워커가 죽으면 잡아 둔 Flask 앱도 사라진다
    endRun();
  }


  function ensureWorker() {
    if (worker) return worker;
    // Pyodide 314는 모듈 워커만 지원한다 (클래식 워커 불가)
    worker = new Worker('pyrunner.js', { type: 'module' });
    worker.onmessage = function (ev) {
      var t = ev.data.t, m = ev.data.m;
      if (t === 'ack') { /* 수신 확인 신호 -- 따로 할 일은 없다 */ }
      else if (t === 'status') { setStatus(m); }
      else if (t === 'out') { append(null, m); }
      else if (t === 'err') { append('err', m); }
      else if (t === 'figs') {
        (m || []).forEach(function (b64) {
          var img = document.createElement('img');
          img.src = 'data:image/png;base64,' + b64;
          img.alt = '실행 결과 그래프';
          ui.figs.appendChild(img);
        });
      } else if (t === 'plotly') {
        renderPlotly(m);
      } else if (t === 'turtle') {
        renderTurtle(m);
      } else if (t === 'gfiles') {
        renderGenFiles(m);
      } else if (t === 'flask') {
        showFlask(m);
      } else if (t === 'flaskres') {
        renderFlaskResponse(m);
      } else if (t === 'done') {
        var secs = ((Date.now() - startedAt) / 1000).toFixed(1);
        ready = true;
        endRun();
        if (!ui.out.textContent && !ui.figs.childNodes.length && ui.web.hidden) {
          append('muted', '(출력 없음)\n');
        }
        setStatus('완료 — ' + secs + '초');
      }
    };
    worker.onerror = function (e) {
      append('err', '실행기를 불러오지 못했습니다: ' + (e.message || e) + '\n');
      abortRun();
      setStatus('오류');
    };
    return worker;
  }

  function run() {
    if (busy) return;
    var code = ui.code.value;
    stopTurtle();
    stopFlask();
    ui.out.textContent = '';
    ui.figs.innerHTML = '';

    // 문법 틀·의사코드 -- 실행 대상이 아닌 개념 코드는 안내만 출력한다
    if (conceptCodes && conceptCodes.indexOf(codeKey(code)) !== -1) {
      append('warn',
        '이 코드는 실행을 위한 것이 아니라, 설명을 돕는 개념 코드입니다. ' +
        '실행되지 않습니다.\n');
      setStatus('설명용 개념 코드');
      return;
    }

    // 코랩 전용 코드(드라이브 마운트, 마운트된 드라이브를 읽는 연속 예제) --
    // 브라우저에서는 돌 수 없다. 실행 대신 책에 제시된 출력을 그대로 보여 준다.
    var colabOut = colabCodes ? colabCodes[codeKey(code)] : undefined;
    if (colabOut !== undefined ||
        /^\s*(?:from|import)\s+google\.colab\b/m.test(code)) {
      append(null, (colabOut !== undefined
        ? colabOut : 'Mounted at /content/drive') + '\n');
      append('warn',
        '\n이 코드는 코랩에서 실행되는 코드로, 변경하여 테스트하는 것이 ' +
        '지원되지 않습니다.\n');
      setStatus('코랩 전용 코드 — 제시된 출력 표시');
      return;
    }

    for (var i = 0; i < UNSUPPORTED.length; i++) {
      if (UNSUPPORTED[i][0].test(code)) {
        append('warn',
          UNSUPPORTED[i][1] + ' — ' + UNSUPPORTED[i][2] + '\n\n' +
          '이 코드는 [복사] 버튼으로 가져가 내 컴퓨터에 설치한 파이썬에서 ' +
          '실행해 주세요.\n');
        setStatus('브라우저에서 실행할 수 없는 코드입니다.');
        return;
      }
    }

    busy = true;
    ui.run.disabled = true;
    ui.stop.hidden = false;
    setStatus(ready ? '실행 중…' : '준비 중…');

    startedAt = Date.now();
    ensureWorker().postMessage({
      code: code, stdin: ui.stdin.value, files: collectVFiles()
    });

    var limit = FLASK_RE.test(code) ? FLASK_TIMEOUT_MS : RUN_TIMEOUT_MS;
    timer = setTimeout(function () {
      abortRun();
      append('warn',
        '\n실행이 ' + (limit / 1000) + '초를 넘겨 중지했습니다. ' +
        '끝나지 않는 반복문이 있는지 확인해 보세요.\n' +
        '(멈추려면 파이썬을 내려야 해서 다음 실행은 준비 시간이 다시 걸립니다)\n');
      setStatus('시간 초과로 중지');
    }, limit);
  }

  function open(code) {
    if (!dlg) build();
    if (busy) abortRun();
    stopTurtle();
    stopFlask();
    // 연속 예제면 앞 리스팅의 준비 코드를 붙여서 연다
    var pre = runPreludes && runPreludes[codeKey(code)];
    if (pre) code = pre + code;
    original = code;
    ui.code.value = code;
    ui.out.textContent = '';
    ui.figs.innerHTML = '';
    setStatus('');
    // 이 예제에 맞는 예시 입력이 있으면 미리 채워 바로 실행할 수 있게 한다
    ui.stdin.value = (stdinDefaults && stdinDefaults[codeKey(code)]) || '';
    syncStdinBox();
    ui.files.innerHTML = '';   // 새 코드를 열 때는 가상 파일도 기본값부터
    syncFilesBox();
    dlg.showModal();
    ui.code.focus();
    ui.code.setSelectionRange(0, 0);
  }

  function close() { if (dlg && dlg.open) dlg.close(); }

  return { open: open, close: close };
})();
