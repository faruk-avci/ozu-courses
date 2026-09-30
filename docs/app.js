(() => {
  'use strict';
  const O = 'faruk-avci', R = 'ozu-courses', B = 'main';
  const SITE_BASE = `/${R}/`;
  const API = `https://api.github.com/repos/${O}/${R}/git/trees/${B}?recursive=1`;
  const RAW = `https://raw.githubusercontent.com/${O}/${R}/${B}`;
  const CK = 'ozu_tree_v2', CTL = 10*60*1000;
  const LANGS = { py:'python', cpp:'cpp', c:'c', tex:'latex', ino:'arduino', txt:'plaintext', md:'markdown', asc:'plaintext' };
  const CODE = new Set(Object.keys(LANGS)), IMG = new Set(['png','jpg','jpeg','bmp']);
  const COURSE_NAMES = { 'EE-202':'Circuit Theory Lab', 'EE-350':'Analog Electronics', 'EE-493':'Power Electronics', 'PHYS-325':'Mathematical Methods for Scientists and Engineers', 'PHYS-551':'Computational Physics' };

  // DOM refs
  const $ = id => document.getElementById(id);
  const sbTree=$('sbTree'), content=$('content'), crumbs=$('crumbs'), tabsBar=$('tabsBar');
  const filterInput=$('filterInput'), lightbox=$('lightbox'), lbImg=$('lbImg'), lbClose=$('lbClose');
  const menuBtn=$('menuBtn'), sidebar=$('sidebar'), overlay=$('overlay');

  const cmdOverlay=$('cmdOverlay'), cmdInput=$('cmdInput'), cmdList=$('cmdList'), cmdHint=$('cmdHint');
  const treeLoad=$('treeLoad'), courseGrid=$('courseGrid');

  let tree=null, activeRow=null, tabs=[], activeTabId=null, flatFiles=[];
  let pdfObjectUrl=null, pdfLoadId=0;
  let fc=0, dc=0;

  async function init() {
    bind();
    try {
      tree = await load();
      buildSidebar(tree);
      buildCourseGrid();

      const route = new URLSearchParams(location.search).get('route') || decodeURIComponent(location.pathname.startsWith(SITE_BASE) ? location.pathname.slice(SITE_BASE.length).replace(/\/$/, '') : '');
      if(route) nav(route, true);
      else if(location.hash) nav(decodeURIComponent(location.hash.slice(1)), true);
    } catch(e) {
      treeLoad.innerHTML = `<div class="error-msg">Failed: ${e.message} <button class="dl-btn" onclick="location.reload()" style="margin-top:8px">Retry</button></div>`;
    }
  }

  // === LOAD TREE ===
  async function load() {
    const c = sessionStorage.getItem(CK);
    if(c){ const {d,t}=JSON.parse(c); if(Date.now()-t<CTL){ treeLoad.remove(); return mk(d); }}
    const r = await fetch(API);
    if(!r.ok) throw new Error(r.status===403?'Rate limited. Try again later.':`HTTP ${r.status}`);
    const j = await r.json();
    const items = j.tree.filter(i=>!i.path.startsWith('.git')&&!i.path.startsWith('docs/'));
    sessionStorage.setItem(CK, JSON.stringify({d:items,t:Date.now()}));
    treeLoad.remove();
    return mk(items);
  }

  function mk(items) {
    const root = {name:R, type:'tree', path:'', children:{}, size:0};
    for(const it of items) {
      const pp=it.path.split('/'); let cur=root;
      for(let i=0;i<pp.length;i++) {
        const n=pp[i];
        if(!cur.children[n]) cur.children[n]={name:n, type:i===pp.length-1?it.type:'tree', path:pp.slice(0,i+1).join('/'), size:it.size||0, children:{}};
        if(i===pp.length-1) {
          if(it.type==='blob'){cur.children[n].type='blob';cur.children[n].size=it.size||0;fc++;flatFiles.push(cur.children[n]);}
          else dc++;
        }
        cur=cur.children[n];
      }
    }
    return root;
  }

  // === SIDEBAR TREE ===
  function buildSidebar(t) {
    const ul=document.createElement('ul'); ul.className='tree';
    for(const c of sorted(t)) ul.appendChild(mkN(c,0));
    sbTree.appendChild(ul);
  }

  function sorted(n) {
    const e=Object.values(n.children);
    return [...e.filter(x=>x.type==='tree').sort((a,b)=>a.name.localeCompare(b.name)),
            ...e.filter(x=>x.type==='blob').sort((a,b)=>a.name.localeCompare(b.name))];
  }

  function mkN(node, depth) {
    const li=document.createElement('li');
    const row=document.createElement('div'); row.className='tr'; row.style.setProperty('--d',depth); row.dataset.path=node.path;
    const isDir=node.type==='tree', ext=getExt(node.name);

    if(isDir) {
      const ch=document.createElement('span'); ch.className='tr-chev'; ch.textContent='\u25B6'; row.appendChild(ch);
      const ic=document.createElement('span'); ic.className='tr-icon'; ic.textContent='\u25E1'; row.appendChild(ic);
      const nm=document.createElement('span'); nm.className='tr-name'; nm.textContent=node.name; row.appendChild(nm);
      const cnt=Object.keys(node.children).length;
      if(cnt){const s=document.createElement('span');s.className='tr-cnt';s.textContent=cnt;row.appendChild(s);}
      const cul=document.createElement('ul'); cul.className='tc';
      for(const c of sorted(node)) cul.appendChild(mkN(c,depth+1));
      row.onclick=e=>{e.stopPropagation();ch.classList.toggle('open');cul.classList.toggle('open');nav(node.path);};
      li.appendChild(row); li.appendChild(cul);
    } else {
      const sp=document.createElement('span');sp.className='tr-chev';row.appendChild(sp);
      const ic=document.createElement('span');ic.className='tr-icon';ic.textContent='\u2013';row.appendChild(ic);
      const nm=document.createElement('span');nm.className='tr-name';nm.textContent=node.name;row.appendChild(nm);
      if(ext){const b=document.createElement('span');b.className=`tr-badge ${ext}`;b.textContent=ext;row.appendChild(b);}
      row.onclick=e=>{e.stopPropagation();nav(node.path);closeMobile();};
      li.appendChild(row);
    }
    return li;
  }

  function setActive(el){if(activeRow)activeRow.classList.remove('active');el.classList.add('active');activeRow=el;}

  // === COURSE GRID ===
  function buildCourseGrid() {
    if(!courseGrid||!tree) return;
    const courses = Object.values(tree.children)
      .filter(node => node.type === 'tree' && /^[A-Z]+-\d+$/.test(node.name))
      .sort((a,b) => a.name.localeCompare(b.name));
    for(const course of courses) {
      const code = course.name;
      const name = COURSE_NAMES[code] || code;
      const cnt = countFiles(course);
      const div=document.createElement('div'); div.className='course-card';
      const codeEl=document.createElement('span'); codeEl.className='course-code'; codeEl.textContent=code;
      const nameEl=document.createElement('span'); nameEl.className='course-name'; nameEl.textContent=name;
      const statEl=document.createElement('span'); statEl.className='course-stat'; statEl.textContent=`${cnt} files`;
      div.append(codeEl,nameEl,statEl);
      div.onclick=()=>nav(code);
      courseGrid.appendChild(div);
    }
  }

  function countFiles(node) {
    let c=0;
    for(const ch of Object.values(node.children)){if(ch.type==='blob')c++;else c+=countFiles(ch);}
    return c;
  }

  // === TABS ===
  function openTab(node) {
    const id=node.path;
    let tab=tabs.find(t=>t.id===id);
    if(!tab){tab={id,name:node.name,node};tabs.push(tab);}
    activeTabId=id;
    renderTabs();
    showFile(node);
  }

  function closeTab(id) {
    const idx=tabs.findIndex(t=>t.id===id);
    if(idx===-1)return;
    tabs.splice(idx,1);
    if(activeTabId===id){
      if(tabs.length){activeTabId=tabs[Math.min(idx,tabs.length-1)].id;const t=tabs.find(x=>x.id===activeTabId);nav(t.id,true);}
      else{activeTabId=null;nav('');}
    }
    renderTabs();
  }

  function renderTabs() {
    tabsBar.innerHTML='';
    for(const t of tabs){
      const div=document.createElement('div');div.className='tab'+(t.id===activeTabId?' active':'');
      const ext=getExt(t.name);
      const badge=ext?`<span class="tr-badge ${ext}" style="font-size:0.55rem">${ext}</span>`:'';
      div.innerHTML=`${badge}<span>${t.name}</span>`;
      const x=document.createElement('button');x.className='tab-close';x.textContent='×';
      x.onclick=e=>{e.stopPropagation();closeTab(t.id);};
      div.appendChild(x);
      div.onclick=()=>nav(t.id);
      tabsBar.appendChild(div);
    }
  }

  // === NAVIGATE ===
  function nav(path, replace=false) {
    if(!tree)return;
    if(!path){setRoute('',replace);showWelcome();return;}
    const pp=path.split('/'); let cur=tree;
    for(const p of pp){if(cur.children&&cur.children[p])cur=cur.children[p];else return;}
    setRoute(path,replace);
    expandTo(path);
    if(cur.type==='blob'){const row=sbTree.querySelector(`[data-path="${path}"]`);if(row)setActive(row);openTab(cur);}
    else showFolder(cur);
  }

  function setRoute(path,replace) {
    const url=SITE_BASE+encP(path);
    history[replace?'replaceState':'pushState'](null,'',url);
  }

  function expandTo(path) {
    const row=sbTree.querySelector(`[data-path="${path}"]`);
    if(!row)return;
    let par=row.parentElement;
    while(par&&par!==sbTree){if(par.classList.contains('tc')){par.classList.add('open');const ch=par.previousElementSibling?.querySelector('.tr-chev');if(ch)ch.classList.add('open');}par=par.parentElement;}
  }

  // === SHOW FOLDER ===
  function showFolder(node) {
    releasePDF();
    setCrumbs(node.path);

    const ch=sorted(node);
    let html=`<div class="folder-view"><h2>${node.name}</h2><table class="ftable"><tbody>`;
    for(const c of ch){
      const isDir=c.type==='tree',ext=getExt(c.name),sz=c.size?fmtSz(c.size):'';
      const badge=!isDir&&ext?`<span class="tr-badge ${ext}">${ext}</span>`:'';
      const ic=isDir?'\u25E1':'\u2013';
      const info=isDir?`${Object.keys(c.children).length} items`:sz;
      html+=`<tr data-p="${c.path}"><td class="c-ic">${ic}</td><td class="c-name${isDir?' dir':''}">${c.name}</td><td class="c-ext">${badge}</td><td class="c-size">${info}</td></tr>`;
    }
    html+='</tbody></table></div>';
    content.innerHTML=html;
    content.querySelectorAll('tr[data-p]').forEach(tr=>tr.onclick=()=>nav(tr.dataset.p));
  }

  // === SHOW FILE ===
  function showFile(node) {
    releasePDF();
    const ext=getExt(node.name), url=`${RAW}/${encP(node.path)}`;
    setCrumbs(node.path);
    if(ext==='pdf') return showPDF(url,node.name);
    if(IMG.has(ext)) return showImage(url,node.name);
    if(CODE.has(ext)) return showCode(url,node.name,LANGS[ext]);
    showDL(url,node,ext);
  }

  function showPDF(url,name) {
    const loadId=++pdfLoadId;
    content.innerHTML=`<div class="pdf-view"><div class="pdf-bar"><span class="pdf-title" aria-live="polite"></span><div class="pdf-bar-btns"><a class="pdf-btn pdf-open" target="_blank" rel="noopener">Open in new tab</a><a class="pdf-btn pdf-download">Download</a></div></div><iframe class="pdf-frame"></iframe></div>`;
    const title=content.querySelector('.pdf-title');
    const open=content.querySelector('.pdf-open');
    const download=content.querySelector('.pdf-download');
    const frame=content.querySelector('.pdf-frame');
    title.textContent=`Loading ${name}...`;
    download.href=url;
    download.download=name;
    frame.title=name;
    fetch(url).then(response=>{
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.blob();
    }).then(blob=>{
      if(loadId!==pdfLoadId) return;
      pdfObjectUrl=URL.createObjectURL(new Blob([blob],{type:'application/pdf'}));
      title.textContent=name;
      open.href=pdfObjectUrl;
      frame.src=pdfObjectUrl;
    }).catch(error=>{
      if(loadId!==pdfLoadId) return;
      title.textContent=`Preview unavailable: ${error.message}`;
      open.href=url;
    });
  }

  function releasePDF() {
    pdfLoadId++;
    if(pdfObjectUrl){URL.revokeObjectURL(pdfObjectUrl);pdfObjectUrl=null;}
  }

  function showImage(url,name) {
    content.innerHTML=`<div class="img-view"><img src="${url}" alt="${name}" id="vImg"></div>`;
    $('vImg').onclick=()=>{lbImg.src=url;lbImg.alt=name;lightbox.classList.add('on');};
  }

  async function showCode(url,name,lang) {
    content.innerHTML=`<div class="loading"><div class="spinner"></div>Loading ${name}...</div>`;
    try{
      const r=await fetch(url); if(!r.ok)throw new Error(`HTTP ${r.status}`);
      const t=await r.text();
      content.innerHTML=`<div class="code-view"><pre class="line-numbers"><code class="language-${lang}">${esc(t)}</code></pre></div>`;
      Prism.highlightAll();
    }catch(e){content.innerHTML=`<div class="error-msg">Failed: ${e.message}</div>`;}
  }

  function showDL(url,node,ext) {
    content.innerHTML=`<div class="dl-view"><h3>${node.name}</h3><p>${(ext||'file').toUpperCase()}${node.size?' · '+fmtSz(node.size):''}</p><a href="${url}" download="${node.name}" class="dl-btn">Download file</a></div>`;
  }

  // === BREADCRUMBS ===
  function setCrumbs(path) {
    const pp=path.split('/');
    let h=`<span data-p="">~</span>`;
    pp.forEach((p,i)=>{const fp=pp.slice(0,i+1).join('/');h+=`<span class="sep">/</span>`;h+=i===pp.length-1?`<span class="cur">${p}</span>`:`<span data-p="${fp}">${p}</span>`;});
    crumbs.innerHTML=h;
    crumbs.querySelectorAll('span[data-p]').forEach(s=>s.onclick=()=>nav(s.dataset.p));
  }

  function showWelcome() {
    releasePDF();
    crumbs.innerHTML='';
    if(activeRow){activeRow.classList.remove('active');activeRow=null;}
    content.innerHTML=`<div class="welcome"><h1>Course Repository</h1><p class="sub">Electrical &amp; Electronics Engineering coursework at Özyeğin University. Click a course below or press <kbd class="kbd">Ctrl K</kbd> to search.</p><div class="course-grid" id="courseGrid"></div></div>`;
    buildCourseGrid();
  }

  // === COMMAND PALETTE ===
  function openCmd() {cmdOverlay.classList.add('on');cmdInput.value='';cmdInput.focus();renderCmd('');}
  function closeCmd() {cmdOverlay.classList.remove('on');}

  function renderCmd(q) {
    q=q.toLowerCase().trim();
    const results=q?flatFiles.filter(f=>{const n=f.name.toLowerCase(),p=f.path.toLowerCase();return n.includes(q)||p.includes(q);}):flatFiles.slice(0,30);
    cmdList.innerHTML='';
    for(const f of results.slice(0,40)){
      const d=document.createElement('div');d.className='cmd-item';
      const ext=getExt(f.name);
      const badge=ext?`<span class="tr-badge ${ext}" style="font-size:0.55rem">${ext}</span>`:'';
      d.innerHTML=`${badge}<span>${f.name}</span><span class="cmd-item-path">${f.path}</span>`;
      d.onclick=()=>{closeCmd();nav(f.path);};
      cmdList.appendChild(d);
    }
    if(!results.length) cmdList.innerHTML='<div class="cmd-item" style="color:var(--text-mute)">No results</div>';
  }

  // === FILTER SIDEBAR ===
  function filterTree(q) {
    q=q.toLowerCase().trim();
    const all=sbTree.querySelectorAll('li');
    if(!q){all.forEach(li=>li.style.display='');sbTree.querySelectorAll('.tc').forEach(c=>c.classList.remove('open'));sbTree.querySelectorAll('.tr-chev').forEach(c=>c.classList.remove('open'));return;}
    all.forEach(li=>{
      const row=li.querySelector(':scope>.tr'); if(!row)return;
      const nm=(row.querySelector('.tr-name')?.textContent||'').toLowerCase(), p=(row.dataset.path||'').toLowerCase();
      const m=nm.includes(q)||p.includes(q); li.style.display=m?'':'none';
      if(m){let par=li.parentElement;while(par&&par!==sbTree){if(par.classList.contains('tc')){par.classList.add('open');const ch=par.previousElementSibling?.querySelector('.tr-chev');if(ch)ch.classList.add('open');}if(par.tagName==='LI')par.style.display='';par=par.parentElement;}}
    });
  }

  // === LIGHTBOX ===
  function closeLB(){lightbox.classList.remove('on');setTimeout(()=>lbImg.src='',200);}
  function closeMobile(){sidebar.classList.remove('open');overlay.classList.remove('on');}

  // === EVENTS ===
  function bind() {
    lbClose.onclick=closeLB; lightbox.onclick=e=>{if(e.target===lightbox)closeLB();};
    menuBtn.onclick=()=>{sidebar.classList.toggle('open');overlay.classList.toggle('on');};
    overlay.onclick=closeMobile;
    window.onpopstate=()=>{
      const path=decodeURIComponent(location.pathname.startsWith(SITE_BASE) ? location.pathname.slice(SITE_BASE.length).replace(/\/$/, '') : '');
      if(path) nav(path,true); else showWelcome();
    };
    let ft; filterInput.oninput=()=>{clearTimeout(ft);ft=setTimeout(()=>filterTree(filterInput.value),120);};
    cmdHint.onclick=openCmd;
    cmdOverlay.onclick=e=>{if(e.target===cmdOverlay)closeCmd();};
    let ct; cmdInput.oninput=()=>{clearTimeout(ct);ct=setTimeout(()=>renderCmd(cmdInput.value),80);};
    document.onkeydown=e=>{
      if(e.key==='Escape'){closeLB();closeCmd();}
      if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();cmdOverlay.classList.contains('on')?closeCmd():openCmd();}
    };
  }

  // === UTILS ===
  function getExt(n){const p=n.split('.');return p.length>1?p.pop().toLowerCase():'';}
  function encP(p){return p.split('/').map(encodeURIComponent).join('/');}
  function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
  function fmtSz(b){if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(1)+' MB';}

  init();
})();
