/* OZU Courses — shared engine.
 * A theme supplies the page chrome (#view, optional #tree, [data-action] buttons),
 * its stylesheet, and optionally window.OZU_THEME.renderHome(data, h).
 */
(() => {
  'use strict';

  const CFG = Object.assign({
    owner: 'faruk-avci', repo: 'ozu-courses', branch: 'main',
    treeUrl: null, commitsUrl: null,
  }, window.OZU_CONFIG || {});
  const THEME = window.OZU_THEME || {};

  const API = `https://api.github.com/repos/${CFG.owner}/${CFG.repo}`;
  const RAW = `https://raw.githubusercontent.com/${CFG.owner}/${CFG.repo}/${CFG.branch}`;
  const PATH_MODE = location.hostname.endsWith('github.io');
  const BASE = PATH_MODE ? `/${CFG.repo}/` : location.pathname;
  const SITE = 'OZU Courses';

  const COURSES = {
    'EE-202':   { title: 'Circuit Theory Lab', term: 'Spring 2025' },
    'EE-350':   { title: 'Electronics II', term: 'Spring 2026', instructor: 'Dr. Umut Başaran' },
    'EE-493':   { title: 'Power Electronics', term: 'Spring 2026', instructor: 'Dr. Umut Başaran' },
    'PHYS-325': { title: 'Mathematical Methods for Scientists and Engineers', term: 'Fall 2026', instructor: 'Prof. Dr. Taylan Akdoğan', current: true },
    'PHYS-551': { title: 'Advanced Monte Carlo Methods', term: 'Spring 2026', instructor: 'Prof. Dr. Taylan Akdoğan' },
  };

  const LANGS = {
    py: 'python', cpp: 'cpp', c: 'c', h: 'c', tex: 'latex', ino: 'arduino', md: 'markdown',
    sh: 'bash', json: 'json', geojson: 'json', html: 'markup', csv: 'none', txt: 'none',
    asc: 'none', lib: 'none', asy: 'none',
  };
  const IMG = new Set(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'svg', 'webp']);
  const MAX_TEXT = 600 * 1024;
  const MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];

  // ---------- utils ----------
  const $ = (s, r = document) => r.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const extOf = n => { const i = n.lastIndexOf('.'); return i > 0 ? n.slice(i + 1).toLowerCase() : ''; };
  const encP = p => p.split('/').map(encodeURIComponent).join('/');
  const rawUrl = p => `${RAW}/${encP(p)}`;
  const fmtSize = b => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1048576).toFixed(1)} MB`;
  const isCompact = () => matchMedia('(max-width: 860px), (pointer: coarse)').matches;

  function kindOf(name) {
    const e = extOf(name);
    if (e === 'pdf') return 'pdf';
    if (IMG.has(e)) return 'img';
    if (e === 'md') return 'md';
    if (e in LANGS) return 'code';
    return 'file';
  }
  const tagOf = name => (extOf(name) || 'file').toUpperCase();

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = src; s.onload = res; s.onerror = () => rej(new Error(`Could not load ${src}`));
      document.head.appendChild(s);
    });
  }

  async function cached(key, ttl, fn) {
    try {
      const c = JSON.parse(sessionStorage.getItem(key));
      if (c && Date.now() - c.t < ttl) return c.d;
    } catch { /* storage unavailable */ }
    const d = await fn();
    try { sessionStorage.setItem(key, JSON.stringify({ d, t: Date.now() })); } catch { /* ignore */ }
    return d;
  }

  // ---------- data ----------
  let root = null;
  const files = [];

  async function loadTree() {
    const url = CFG.treeUrl || `${API}/git/trees/${CFG.branch}?recursive=1`;
    const items = await cached(`ozu:tree:${url}`, 10 * 60e3, async () => {
      const r = await fetch(url);
      if (!r.ok) throw new Error(r.status === 403 ? 'GitHub rate limit reached. Try again in a few minutes.' : `HTTP ${r.status}`);
      const j = await r.json();
      return j.tree
        .filter(i => !/^(docs|preview)(\/|$)/.test(i.path) && !i.path.split('/').some(s => s.startsWith('.')))
        .map(i => ({ p: i.path, t: i.type, s: i.size || 0 }));
    });
    root = { name: '', path: '', dir: true, children: new Map(), parent: null };
    for (const it of items) {
      const parts = it.p.split('/');
      let cur = root;
      parts.forEach((name, i) => {
        let n = cur.children.get(name);
        if (!n) {
          n = { name, path: parts.slice(0, i + 1).join('/'), dir: true, children: new Map(), parent: cur, size: 0 };
          cur.children.set(name, n);
        }
        if (i === parts.length - 1 && it.t === 'blob') { n.dir = false; n.size = it.s; files.push(n); }
        cur = n;
      });
    }
    (function count(n) {
      if (!n.dir) return 1;
      let c = 0;
      for (const ch of n.children.values()) c += count(ch);
      return (n.count = c);
    })(root);
  }

  async function loadRecent() {
    const url = CFG.commitsUrl || `${API}/commits?per_page=30`;
    try {
      const list = await cached(`ozu:commits:${url}`, 10 * 60e3, async () => {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()).map(c => ({ m: c.commit.message.split('\n')[0], d: c.commit.author.date, u: c.html_url }));
      });
      return list.map(c => {
        const m = c.m.match(/^([A-Z]+-\d+):\s*(.+)$/);
        return m && COURSES[m[1]] ? { course: m[1], text: m[2], date: new Date(c.d), url: c.u } : null;
      }).filter(Boolean).slice(0, 6);
    } catch { return []; }
  }

  function weekKey(name) {
    const m = name.match(/^(\d{1,2}) ([A-Za-z]+) -/);
    if (!m) return null;
    const mi = MONTHS.indexOf(m[2].toLowerCase());
    return mi < 0 ? null : mi * 100 + +m[1];
  }

  function kids(n) {
    return [...n.children.values()].sort((a, b) => {
      if (a.dir !== b.dir) return a.dir ? -1 : 1;
      const wa = weekKey(a.name), wb = weekKey(b.name);
      if (wa !== null && wb !== null) return wa - wb;
      return a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' });
    });
  }

  function find(path) {
    if (!path) return root;
    let cur = root;
    for (const p of path.split('/')) {
      cur = cur.children.get(p);
      if (!cur) return null;
    }
    return cur;
  }

  function kindCounts(n, acc = { pdf: 0, code: 0, img: 0, other: 0 }) {
    for (const ch of n.children.values()) {
      if (ch.dir) kindCounts(ch, acc);
      else { const k = kindOf(ch.name); acc[k === 'md' ? 'code' : k === 'file' ? 'other' : k]++; }
    }
    return acc;
  }

  const termKey = t => { const [s, y] = (t || '').split(' '); return +y * 10 + ({ Spring: 1, Summer: 2, Fall: 3 }[s] || 0); };

  function courseList() {
    return [...root.children.values()]
      .filter(n => n.dir && /^[A-Z]+-\d+$/.test(n.name))
      .map(n => {
        const meta = COURSES[n.name] || { title: n.name };
        return {
          code: n.name, ...meta, count: n.count, kinds: kindCounts(n), path: n.path,
          sections: kids(n).filter(c => c.dir).map(c => ({ name: c.name, count: c.count, path: c.path })),
        };
      })
      .sort((a, b) => termKey(b.term) - termKey(a.term) || a.code.localeCompare(b.code));
  }

  // ---------- routing ----------
  function urlFor(path) {
    if (PATH_MODE) return BASE + encP(path);
    return path ? `${BASE}?p=${encP(path)}` : BASE;
  }
  const link = path => `href="${esc(urlFor(path))}" data-nav="${esc(path)}"`;

  function readRoute() {
    const q = new URLSearchParams(location.search);
    if (q.has('route')) return q.get('route');
    if (q.has('p')) return q.get('p');
    if (PATH_MODE && location.pathname.startsWith(BASE)) {
      return decodeURIComponent(location.pathname.slice(BASE.length)).replace(/\/$/, '');
    }
    return '';
  }

  function go(path, replace = false) {
    history[replace ? 'replaceState' : 'pushState'](null, '', urlFor(path));
    render(path);
  }

  // ---------- views ----------
  const view = $('#view');
  const treeEl = $('#tree');
  let cleanup = null;
  let currentPath = null;

  function crumbs(node) {
    const chain = [];
    for (let n = node; n && n !== root; n = n.parent) chain.unshift(n);
    const parts = chain.map((n, i) => i === chain.length - 1
      ? `<span class="crumb is-current" aria-current="page">${esc(n.name)}</span>`
      : `<a class="crumb" ${link(n.path)}>${esc(n.name)}</a>`);
    return `<nav class="crumbs" aria-label="Breadcrumb"><a class="crumb crumb-home" ${link('')}>Courses</a>${parts.map(p => `<span class="crumb-sep" aria-hidden="true">/</span>${p}`).join('')}</nav>`;
  }

  function rowHtml(c) {
    if (c.dir) {
      return `<li><a class="row is-dir" ${link(c.path)}><span class="row-tag t-dir">DIR</span><span class="row-name">${esc(c.name)}</span><span class="row-meta">${c.count} file${c.count === 1 ? '' : 's'}</span></a></li>`;
    }
    const k = kindOf(c.name);
    return `<li><a class="row is-file" ${link(c.path)}><span class="row-tag t-${k}">${esc(tagOf(c.name))}</span><span class="row-name">${esc(c.name)}</span><span class="row-meta">${fmtSize(c.size)}</span></a></li>`;
  }

  function renderHome() {
    const data = { courses: courseList(), recent: recentCache, totals: { files: files.length, courses: 0 } };
    data.totals.courses = data.courses.length;
    const helpers = { link, esc, fmtSize };
    view.innerHTML = THEME.renderHome ? THEME.renderHome(data, helpers) : defaultHome(data);
  }

  function defaultHome(data) {
    return `<section class="home"><h1>Courses</h1><ul class="list">${data.courses.map(c =>
      `<li><a class="row is-dir" ${link(c.path)}><span class="row-tag t-dir">${esc(c.code)}</span><span class="row-name">${esc(c.title)}</span><span class="row-meta">${esc(c.term || '')}</span></a></li>`).join('')}</ul></section>`;
  }

  function renderDir(node) {
    const isCourse = node.parent === root && COURSES[node.name];
    let head;
    if (isCourse) {
      const m = COURSES[node.name];
      const facts = [m.term, m.instructor].filter(Boolean).map(esc).join('<span class="dot"> · </span>');
      head = `<header class="course-head">
        <p class="course-code">${esc(node.name)}${m.current ? '<span class="badge-now">In progress</span>' : ''}</p>
        <h1 class="course-title">${esc(m.title)}</h1>
        <p class="course-facts">${facts}</p>
      </header>`;
    } else {
      head = `<header class="dir-head"><h1 class="dir-title">${esc(node.name)}</h1><p class="dir-meta">${node.count} files</p></header>`;
    }
    view.innerHTML = `<section class="dir">${crumbs(node)}${head}<ul class="list">${kids(node).map(rowHtml).join('')}</ul></section>`;
  }

  function renderFile(node) {
    const k = kindOf(node.name);
    const sibs = kids(node.parent).filter(c => !c.dir);
    const i = sibs.indexOf(node), prev = sibs[i - 1], next = sibs[i + 1];
    const url = rawUrl(node.path);
    view.innerHTML = `<section class="file" data-kind="${k}">
      ${crumbs(node)}
      <header class="file-head">
        <div class="file-id"><span class="row-tag t-${k}">${esc(tagOf(node.name))}</span><h1 class="file-title">${esc(node.name)}</h1><span class="file-size">${fmtSize(node.size)}</span></div>
        <div class="file-actions">
          ${prev ? `<a class="btn btn-step" ${link(prev.path)} title="${esc(prev.name)}" aria-label="Previous file">‹ Prev</a>` : ''}
          ${next ? `<a class="btn btn-step" ${link(next.path)} title="${esc(next.name)}" aria-label="Next file">Next ›</a>` : ''}
          <a class="btn" href="${esc(url)}" target="_blank" rel="noopener">Raw</a>
          <button class="btn btn-primary" type="button" data-action="download">Download</button>
        </div>
      </header>
      <div class="file-body" id="fileBody"><div class="loading"><span class="spinner"></span>Loading…</div></div>
    </section>`;
    $('[data-action="download"]', view).onclick = () => download(url, node.name);
    const body = $('#fileBody');
    const token = {};
    cleanup = () => { token.dead = true; token.dispose && token.dispose(); };
    const fail = e => { if (!token.dead) body.innerHTML = `<div class="error">Couldn't load this file: ${esc(e.message)}</div>`; };
    if (k === 'pdf') showPdf(body, url, node.name, token).catch(fail);
    else if (k === 'img') showImg(body, url, node.name);
    else if ((k === 'code' || k === 'md') && node.size <= MAX_TEXT) showText(body, url, node.name, k, token).catch(fail);
    else {
      body.innerHTML = `<div class="dl-card"><p>No preview for this file type${node.size > MAX_TEXT ? ' (file too large)' : ''}.</p><button class="btn btn-primary" type="button">Download ${esc(fmtSize(node.size))}</button></div>`;
      $('.dl-card button', body).onclick = () => download(url, node.name);
    }
  }

  async function fetchBlob(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.blob();
  }

  async function download(url, name) {
    try {
      const blob = await fetchBlob(url);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch { window.open(url, '_blank', 'noopener'); }
  }

  async function showPdf(body, url, name, token) {
    const blob = await fetchBlob(url);
    if (token.dead) return;
    if (!isCompact()) {
      const obj = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      token.dispose = () => URL.revokeObjectURL(obj);
      body.innerHTML = `<iframe class="pdf-frame" title="${esc(name)}" src="${obj}"></iframe>`;
      return;
    }
    if (!window.pdfjsLib) {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js');
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }
    const doc = await window.pdfjsLib.getDocument({ data: await blob.arrayBuffer() }).promise;
    if (token.dead) { doc.destroy(); return; }
    const vp1 = (await doc.getPage(1)).getViewport({ scale: 1 });
    body.innerHTML = `<div class="pdf-pages"></div><div class="pdf-counter" aria-live="polite">1 / ${doc.numPages}</div>`;
    const pages = $('.pdf-pages', body), counter = $('.pdf-counter', body);
    for (let n = 1; n <= doc.numPages; n++) {
      const d = document.createElement('div');
      d.className = 'pdf-page'; d.dataset.n = n;
      d.style.aspectRatio = `${vp1.width} / ${vp1.height}`;
      pages.appendChild(d);
    }
    const draw = async el => {
      const page = await doc.getPage(+el.dataset.n);
      if (token.dead) return;
      const base = page.getViewport({ scale: 1 });
      el.style.aspectRatio = `${base.width} / ${base.height}`;
      const scale = (el.clientWidth * Math.min(window.devicePixelRatio || 1, 2.5)) / base.width;
      const vp = page.getViewport({ scale });
      const c = document.createElement('canvas');
      c.width = Math.floor(vp.width); c.height = Math.floor(vp.height);
      await page.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
      if (!token.dead) el.appendChild(c);
    };
    const loader = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting && !e.target.dataset.done) { e.target.dataset.done = '1'; draw(e.target); }
    }), { rootMargin: '1200px 0px' });
    const tracker = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) counter.textContent = `${e.target.dataset.n} / ${doc.numPages}`;
    }), { rootMargin: '-50% 0px -50% 0px' });
    pages.querySelectorAll('.pdf-page').forEach(p => { loader.observe(p); tracker.observe(p); });
    token.dispose = () => { loader.disconnect(); tracker.disconnect(); doc.destroy(); };
  }

  function showImg(body, url, name) {
    body.innerHTML = `<figure class="img-frame"><img src="${esc(url)}" alt="${esc(name)}"></figure>`;
    $('img', body).onclick = () => openLightbox(url, name);
  }

  async function showText(body, url, name, kind, token) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const text = await r.text();
    if (token.dead) return;
    if (kind === 'md') {
      if (!window.marked) await loadScript('https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js');
      const tmp = document.createElement('div');
      tmp.innerHTML = window.marked.parse(text);
      tmp.querySelectorAll('script,iframe,object,embed').forEach(e => e.remove());
      tmp.querySelectorAll('*').forEach(e => [...e.attributes].forEach(a => { if (/^on/i.test(a.name)) e.removeAttribute(a.name); }));
      body.innerHTML = `<article class="prose">${tmp.innerHTML}</article>`;
      return;
    }
    const lang = LANGS[extOf(name)] || 'none';
    body.innerHTML = `<div class="code"><pre class="line-numbers"><code class="language-${lang}">${esc(text)}</code></pre></div>`;
    if (window.Prism && lang !== 'none') {
      const needs = { cpp: ['c'], arduino: ['c', 'cpp'] }[lang] || [];
      for (const l of [...needs, lang]) {
        if (window.Prism.languages[l]) continue;
        try { await loadScript(`https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-${l}.min.js`); } catch { break; }
      }
      if (token.dead) return;
      window.Prism.highlightAllUnder(body);
    } else if (window.Prism) window.Prism.highlightAllUnder(body);
  }

  function renderMissing(path) {
    view.innerHTML = `<section class="missing"><h1>Not found</h1><p><code>${esc(path)}</code> isn't in the repository.</p><p><a class="btn" ${link('')}>Back to courses</a></p></section>`;
  }

  function render(path) {
    currentPath = path;
    if (cleanup) { cleanup(); cleanup = null; }
    const node = find(path);
    document.body.dataset.view = !node ? 'missing' : node === root ? 'home' : node.dir ? 'dir' : 'file';
    if (!node) renderMissing(path);
    else if (node === root) renderHome();
    else if (node.dir) renderDir(node);
    else renderFile(node);
    document.title = node && node !== root ? `${node.name} · ${SITE}` : `${SITE} · Ömer Faruk Avcı`;
    syncTree(node);
    const cr = $('.crumbs', view);
    if (cr) cr.scrollLeft = cr.scrollWidth;
    window.scrollTo(0, 0);
    if (THEME.afterRender) THEME.afterRender(document.body.dataset.view, node);
  }

  // ---------- sidebar tree ----------
  function buildTree() {
    if (!treeEl) return;
    const walk = n => `<ul>${kids(n).map(c => c.dir
      ? `<li><details data-path="${esc(c.path)}"><summary><a ${link(c.path)}>${esc(c.name)}</a></summary>${walk(c)}</details></li>`
      : `<li><a class="leaf" data-kind="${kindOf(c.name)}" ${link(c.path)}>${esc(c.name)}</a></li>`).join('')}</ul>`;
    treeEl.innerHTML = `<div class="tree-inner">${walk(root)}</div>`;
    // Clicking the folder name navigates; the marker area toggles.
    treeEl.addEventListener('click', e => {
      const a = e.target.closest('summary a');
      if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault(); e.stopPropagation();
      const d = a.closest('details');
      // Phone drawer: folder names only expand/collapse.
      // Desktop: first click opens the folder page, clicking it again collapses it.
      if (isDrawer() || (d.open && currentPath === a.dataset.nav)) { d.open = !d.open; return; }
      d.open = true;
      go(a.dataset.nav);
    }, true);
  }

  function syncTree(node) {
    if (!treeEl) return;
    treeEl.querySelectorAll('.is-active').forEach(e => e.classList.remove('is-active'));
    if (!node || node === root) return;
    for (let n = node.dir ? node : node.parent; n && n !== root; n = n.parent) {
      const d = treeEl.querySelector(`details[data-path="${CSS.escape(n.path)}"]`);
      if (d) d.open = true;
    }
    const a = treeEl.querySelector(`a[data-nav="${CSS.escape(node.path)}"]`);
    if (a) {
      a.classList.add('is-active');
      const r = a.getBoundingClientRect(), tr = treeEl.getBoundingClientRect();
      if (r.top < tr.top || r.bottom > tr.bottom) a.scrollIntoView({ block: 'center' });
    }
  }

  // ---------- tree drawer (narrow screens) ----------
  const isDrawer = () => matchMedia('(max-width: 1023px)').matches;
  function setDrawer(open) {
    if (!treeEl) return;
    document.body.classList.toggle('tree-open', open);
    document.body.classList.toggle('no-scroll', open);
    document.querySelectorAll('[data-action="tree"]').forEach(b => b.setAttribute('aria-expanded', open));
  }

  // ---------- lightbox ----------
  let lb;
  function openLightbox(url, name) {
    if (!lb) {
      lb = document.createElement('div');
      lb.className = 'lightbox';
      lb.innerHTML = '<button class="lightbox-x" type="button" aria-label="Close">×</button><img alt="">';
      lb.onclick = e => { if (e.target !== lb.querySelector('img')) lb.classList.remove('is-open'); };
      document.body.appendChild(lb);
    }
    const img = $('img', lb); img.src = url; img.alt = name;
    lb.classList.add('is-open');
  }

  // ---------- search ----------
  let sEl, sInput, sList, sel = 0, results = [];
  function buildSearch() {
    sEl = document.createElement('div');
    sEl.className = 'search'; sEl.hidden = true;
    sEl.innerHTML = `<div class="search-panel" role="dialog" aria-label="Search files">
      <div class="search-field"><input type="search" placeholder="Search ${files.length} files…" autocomplete="off" spellcheck="false" aria-label="Search files"><button class="search-close" type="button">Close</button></div>
      <ul class="search-results" role="listbox"></ul></div>`;
    document.body.appendChild(sEl);
    sInput = $('input', sEl); sList = $('.search-results', sEl);
    sEl.addEventListener('click', e => { if (e.target === sEl || e.target.closest('.search-close')) closeSearch(); });
    sInput.addEventListener('input', () => { sel = 0; runSearch(); });
    sInput.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        sel = Math.max(0, Math.min(results.length - 1, sel + (e.key === 'ArrowDown' ? 1 : -1)));
        paintSel();
      } else if (e.key === 'Enter' && results[sel]) { closeSearch(); go(results[sel].path); }
    });
  }
  function openSearch() { sEl.hidden = false; document.body.classList.add('no-scroll'); sInput.value = ''; sel = 0; runSearch(); setTimeout(() => sInput.focus(), 0); }
  function closeSearch() { sEl.hidden = true; document.body.classList.remove('no-scroll'); }
  function runSearch() {
    const q = sInput.value.toLocaleLowerCase('tr').trim();
    const toks = q.split(/\s+/).filter(Boolean);
    results = !toks.length ? [] : files
      .map(f => {
        const p = f.path.toLocaleLowerCase('tr'), n = f.name.toLocaleLowerCase('tr');
        if (!toks.every(t => p.includes(t))) return null;
        return { f, score: toks.reduce((s, t) => s + (n.includes(t) ? 2 : 0) + (n.startsWith(t) ? 1 : 0), 0) };
      })
      .filter(Boolean).sort((a, b) => b.score - a.score || a.f.path.length - b.f.path.length)
      .slice(0, 60).map(r => r.f);
    sList.innerHTML = !toks.length
      ? '<li class="search-hint">Try “lab 3”, “hw5 py”, “lecture”, “syllabus”…</li>'
      : results.length ? results.map((f, i) => `<li role="option"><a class="search-item" data-i="${i}" ${link(f.path)}><span class="row-tag t-${kindOf(f.name)}">${esc(tagOf(f.name))}</span><span class="search-name">${esc(f.name)}</span><span class="search-path">${esc(f.parent.path)}</span></a></li>`).join('')
      : '<li class="search-hint">No matching files.</li>';
    paintSel();
  }
  function paintSel() {
    sList.querySelectorAll('.search-item').forEach((a, i) => {
      a.classList.toggle('is-sel', i === sel);
      if (i === sel) a.scrollIntoView({ block: 'nearest' });
    });
  }

  // ---------- boot ----------
  let recentCache = [];

  function bind() {
    document.addEventListener('click', e => {
      const act = e.target.closest('[data-action]');
      if (act && act.dataset.action === 'search') { e.preventDefault(); setDrawer(false); openSearch(); return; }
      if (act && act.dataset.action === 'tree') { e.preventDefault(); setDrawer(!document.body.classList.contains('tree-open')); return; }
      if (e.target.classList.contains('tree-scrim')) { setDrawer(false); return; }
      const a = e.target.closest('a[data-nav]');
      if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      if (sEl && !sEl.hidden) closeSearch();
      if (lb) lb.classList.remove('is-open');
      setDrawer(false);
      go(a.dataset.nav);
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') { if (sEl && !sEl.hidden) closeSearch(); if (lb) lb.classList.remove('is-open'); setDrawer(false); }
      const typing = /input|textarea/i.test(document.activeElement?.tagName || '');
      if (((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') || (e.key === '/' && !typing)) {
        e.preventDefault();
        sEl && (sEl.hidden ? openSearch() : closeSearch());
      }
    });
    window.addEventListener('popstate', () => { setDrawer(false); render(readRoute()); });
    if (treeEl) {
      const scrim = document.createElement('div');
      scrim.className = 'tree-scrim';
      document.body.appendChild(scrim);
      matchMedia('(max-width: 1023px)').addEventListener('change', () => setDrawer(false));
    }
  }

  async function init() {
    bind();
    view.innerHTML = '<div class="loading boot"><span class="spinner"></span>Loading courses…</div>';
    try {
      const [, recent] = await Promise.all([loadTree(), loadRecent()]);
      recentCache = recent;
    } catch (e) {
      view.innerHTML = `<div class="error">Couldn't load the repository: ${esc(e.message)}<br><button class="btn" type="button" onclick="location.reload()">Retry</button></div>`;
      return;
    }
    if (THEME.setup) THEME.setup({ courses: courseList(), recent: recentCache });
    buildTree();
    buildSearch();
    const route = readRoute();
    if (new URLSearchParams(location.search).has('route')) history.replaceState(null, '', urlFor(route));
    render(route);
  }

  init();
})();
