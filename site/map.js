// Land Query map (T-105). Parcels are drawn on the graphics card (WebGL 2) into map tiles at extra resolution with
// edge smoothing, then shrunk with mipmaps, so a zoomed-out view shows each parcel's colour in proportion to its area:
// no dots and no gaps. Tiles are cached; new ones fade in over coarser ones, so zooming shows no jump. Data comes in
// square pieces at three levels of detail (site/build_map.py), downloaded only for the area in view and cut into
// triangles in a background worker (earcut).
(async function(){
'use strict';
const $ = id => document.getElementById(id);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = (v, d=0) => v==null ? '—' : Number(v).toLocaleString('en-NZ',{maximumFractionDigits:d});
// text from the data is always escaped before it goes into the page (T-109)
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const hex = c => { c = c.replace('#',''); return [0,2,4].map(i=>parseInt(c.slice(i,i+2),16)/255); };
const ns = $('natstatus'), say = t => { ns.textContent = t; };

const meta = await fetch('data/meta.json').then(r=>r.json());
const [OX, OY] = meta.origin, M = meta.measures.length, LV = meta.levels;

// council cards and run line
const st = meta.stats, cc = $('councils');
[['k','Kāpiti Coast District','District'],['p','Porirua City','City'],['n','Greater Wellington','National index pilot']].forEach(([c,name,kind])=>{
  const s = st[c]; if(!s) return; const div = document.createElement('div'); div.className='council';
  div.innerHTML = `<div class="label">${kind}</div><h3>${name}</h3>
    <div class="figs"><div class="fig"><b>${fmt(s.parcels)}</b><span>parcels</span></div>
    ${c==='n' ? `<div class="fig"><b>LINZ</b><span>data only, 10 m ground</span></div>` : `<div class="fig"><b>${fmt(s.with_lidar)}</b><span>with LiDAR terrain</span></div>`}
    <div class="fig"><b>${s.median_ground.toFixed(1)} m</b><span>median ground height</span></div></div>`;
  cc.appendChild(div); });
$('runs').textContent = 'Kāpiti results: ' + st.k.run.split(';')[0] + ' · Porirua results: ' + st.p.run.split(';')[0] + ' · Greater Wellington: ' + st.n.run;

// ---- view
const canvas = $('map'), over = $('over'), octx = over.getContext('2d');
const gl = canvas.getContext('webgl2', {antialias:true, alpha:false, depth:false, stencil:false});   // smoothing for the live boundaries
if(!gl){ say('This map needs WebGL 2, which this browser does not offer. Try a current Chrome, Edge, Firefox or Safari.'); return; }
let W = 0, H = 0, dpr = 1, touched = false;
const view = {cx:0, cy:0, s:1};
const [bx0, by0, bx1, by1] = meta.bounds;
function fit(){ view.cx = (bx0+bx1)/2; view.cy = (by0+by1)/2; view.s = Math.min(W/(bx1-bx0-30000), H/(by1-by0-30000)); }
const sx = x => W/2 + (x-view.cx)*view.s, sy = y => H/2 - (y-view.cy)*view.s;
function resize(){ const r = canvas.getBoundingClientRect(); dpr = Math.min(2, window.devicePixelRatio||1); W = r.width; H = r.height;
  for(const c of [canvas, over]){ c.width = Math.round(W*dpr); c.height = Math.round(H*dpr); }
  if(!view.init && W > 0){ fit(); view.init = true; } draw(); }

// ---- colours
let mode = 'ground_mean_m', filter = 'all', gen = 0;   // gen: bumped when colours change, so tiles redraw
const SCALES = {
  ground_mean_m:{m:0, tf:1, lo:0, hi:Math.sqrt(200), label:'Mean ground height (m, square-root scale)', ends:['0','200+']},
  slope_p90_deg:{m:1, tf:0, lo:0, hi:35, label:'90th percentile slope (°)', ends:['0°','35°+']},
  catchment_area_max_m2:{m:2, tf:2, lo:3, hi:8, label:'Upslope catchment (m², log)', ends:['≤1,000','≥100 km²']},
  ww_pipe_year:{m:3, tf:0, lo:1950, hi:2020, label:'Nearest sewer installed (Kāpiti; KCDC records many as 1979 or 1980, likely placeholders)', ends:['≤1950','2020']},
};
function ramp(t){ const a=hex(css('--lowland')), m=hex(css('--accent')), b=hex(css('--highland'));
  const [p,q,u] = t<.5 ? [a,m,t*2] : [m,b,(t-.5)*2]; return 'rgb(' + p.map((v,i)=>Math.round((v+(q[i]-v)*u)*255)).join(',') + ')'; }
function legend(){ const L = $('legend');
  if(mode==='c'){ L.innerHTML = `<div class="label">Council</div><div><span style="color:var(--accent)">●</span> Kāpiti Coast &nbsp; <span style="color:var(--highland)">●</span> Porirua &nbsp; <span style="color:var(--lowland)">●</span> Greater Wellington (national index)</div><div class="keys"><span><i style="background:var(--sea)"></i>Sea, lakes and rivers</span><span><i style="background:var(--land);border:1px solid var(--rule)"></i>Land without a parcel</span></div>`; return; }
  const s = SCALES[mode], g = [0,.25,.5,.75,1].map(ramp).join(',');
  L.innerHTML = `<div class="label">${s.label}</div><div class="bar" style="background:linear-gradient(90deg,${g})"></div><div class="ends"><span>${s.ends[0]}</span><span>${s.ends[1]}</span></div><div class="keys"><span><i style="background:var(--novalue)"></i>No value</span><span><i style="background:var(--sea)"></i>Sea, lakes and rivers</span><span><i style="background:var(--land);border:1px solid var(--rule)"></i>Land without a parcel (roads, railways)</span></div>`; }

// ---- GL programs
function prog(vs, fs){ const p = gl.createProgram();
  for(const [t,src] of [[gl.VERTEX_SHADER,vs],[gl.FRAGMENT_SHADER,fs]]){ const sh = gl.createShader(t); gl.shaderSource(sh, '#version 300 es\nprecision highp float;\n'+src); gl.compileShader(sh);
    if(!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(p, sh); }
  gl.bindAttribLocation(p, 0, 'p'); gl.bindAttribLocation(p, 1, 'vals'); gl.bindAttribLocation(p, 2, 'cc'); gl.bindAttribLocation(p, 3, 'sz');
  gl.linkProgram(p); if(!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for(let i=0;i<n;i++){ const a = gl.getActiveUniform(p, i); u[a.name] = gl.getUniformLocation(p, a.name); }
  return {p, u}; }
const FS = 'in vec4 v; out vec4 o; void main(){ if(v.a < .01) discard; o = v; }';
const PARCEL = prog(`in vec2 p; in vec4 vals; in float cc; uniform vec2 sc, of; uniform int m, filt, tf; uniform float lo, hi;
  uniform vec3 c0, c1, c2, grey, ck, cp, cn, sea; out vec4 v;
  void main(){ gl_Position = vec4(p*sc+of, 0., 1.); int c = int(cc+.5);
    if(c == 3){ v = vec4(sea, 1.); return; }   // rivers and lakes
    if(filt >= 0 && c != filt){ v = vec4(0.); return; }
    if(m == 4){ v = vec4(c==0 ? ck : (c==1 ? cp : cn), 1.); return; }
    float x = m==0 ? vals.x : (m==1 ? vals.y : (m==2 ? vals.z : vals.w));
    if(x < -1e29){ v = vec4(grey, 1.); return; }
    if(tf == 1) x = sqrt(max(x, 0.)); else if(tf == 2) x = log(max(x, 1.)) / log(10.);
    float t = clamp((x-lo)/(hi-lo), 0., 1.);
    v = vec4(t < .5 ? mix(c0, c1, t*2.) : mix(c1, c2, (t-.5)*2.), 1.); }`, FS);
// boundaries, drawn live on screen every frame: each is full strength while its parcel is at least 20 device pixels
// across and fades out by 6, so it changes smoothly with the zoom; none for water
const EDGE = prog(`in vec2 p; in float cc; in float sz; uniform vec2 sc, of, shift; uniform int filt; uniform vec4 col; uniform float pxm; out vec4 v;
  void main(){ gl_Position = vec4(p*sc+of+shift, 0., 1.); int c = int(cc+.5);
    float a = (c == 3 || (filt >= 0 && c != filt)) ? 0. : col.a * clamp((sz*pxm - 6.)/14., 0., 1.); v = vec4(a); }`,
  'in vec4 v; out vec4 o; void main(){ o = v; }');
// boundary coverage layer: copies of the lines are combined by keeping the strongest, not adding, then laid on once
const COVER = prog(`out vec2 uv; void main(){ vec2 c = vec2(float(gl_VertexID & 1), float(gl_VertexID >> 1)); uv = c; gl_Position = vec4(c*2.-1., 0., 1.); }`,
  'in vec2 uv; uniform sampler2D tex; uniform vec3 col; uniform vec4 w; out vec4 o; void main(){ o = vec4(col, clamp(dot(texture(tex, uv), w), 0., 1.)); }');
const edgeTex = gl.createTexture(), edgeFB = gl.createFramebuffer(); let edgeW = 0, edgeH = 0;
function edgeTarget(){ if(edgeW === canvas.width && edgeH === canvas.height) return; edgeW = canvas.width; edgeH = canvas.height;
  gl.bindTexture(gl.TEXTURE_2D, edgeTex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, edgeW, edgeH, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.bindFramebuffer(gl.FRAMEBUFFER, edgeFB); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, edgeTex, 0); gl.bindFramebuffer(gl.FRAMEBUFFER, null); }
// water drawn live over the boundaries, so a river is never covered by the outlines of the land beside it
const WATERP = prog(`in vec2 p; in float cc; uniform vec2 sc, of; uniform vec3 col; out vec4 v;
  void main(){ gl_Position = vec4(p*sc+of, 0., 1.); v = int(cc+.5) == 3 ? vec4(1.) : vec4(0.); }`, 'in vec4 v; out vec4 o; void main(){ if(v.a < .5) discard; o = v; }');
const LAND = prog(`in vec2 p; uniform vec2 sc, of; uniform vec4 col; out vec4 v; void main(){ gl_Position = vec4(p*sc+of, 0., 1.); v = col; }`, FS);
const QUAD = prog(`uniform vec4 rect; uniform vec4 uvr; out vec2 uv;
  void main(){ vec2 c = vec2(float(gl_VertexID & 1), float(gl_VertexID >> 1)); uv = mix(uvr.xy, uvr.zw, c); gl_Position = vec4(mix(rect.xy, rect.zw, c), 0., 1.); }`,
  'in vec2 uv; uniform sampler2D tex; uniform float alpha; out vec4 o; void main(){ o = vec4(texture(tex, uv).rgb, alpha); }');

// ---- land (LINZ coastline), cut into triangles once
const land = (function(){ const pos = [], idx = [];
  for(const poly of meta.land){ const base = pos.length/2, flat = [], holes = [];
    poly.forEach((r, k) => { if(k) holes.push(flat.length/2); for(let j=0;j<r.length;j+=2) flat.push(r[j]-OX, r[j+1]-OY); });
    for(const t of earcut(flat, holes.length ? holes : null, 2)) idx.push(base + t); pos.push(...flat); }
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pos), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const e = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, e); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(idx), gl.STATIC_DRAW);
  gl.bindVertexArray(null); return {vao, n: idx.length}; })();

// ---- pieces: downloaded and cut into triangles in a worker
const workerSrc = `importScripts(${JSON.stringify(new URL('earcut.min.js', location.href).href)});
onmessage = e => { try { work(e.data); } catch(err){ postMessage({key: e.data.key, failed: true}); } };
function work({key, buf, M, OX, OY}){ const dv = new DataView(buf);
  const n = dv.getUint32(4,true), nr = dv.getUint32(8,true), nv = dv.getUint32(12,true); let o = 16;
  const ids = new Int32Array(buf, o, n); o += 4*n; const vals = new Float32Array(buf, o, n*M); o += 4*n*M;
  const rlen = new Uint32Array(buf, o, nr); o += 4*nr; const st = new Int32Array(buf, o, 2*nr); o += 8*nr;
  const rper = new Uint16Array(buf, o, n); o += Math.ceil(2*n/4)*4; const cc = new Uint8Array(buf, o, n); o += Math.ceil(n/4)*4;
  const d = new Int16Array(buf, o, 2*(nv-nr));
  const pos = new Float32Array(2*nv), pv = new Float32Array(4*nv), pc = new Uint8Array(nv), psz = new Float32Array(nv), edge = new Uint32Array(2*nv);
  const rs = new Uint32Array(nr+1), hole = new Uint8Array(nr), hx = new Int32Array(nv), hy = new Int32Array(nv);
  for(let r=0, v=0, q=0; r<nr; r++){ rs[r] = v; hole[r] = rlen[r]>>>31; const len = rlen[r] & 0x7FFFFFFF;
    let x = st[2*r], y = st[2*r+1]; hx[v] = x; hy[v] = y; v++;
    for(let k=1;k<len;k++){ x += d[q++]; y += d[q++]; hx[v] = x; hy[v] = y; v++; } rs[r+1] = v; }
  let tri = new Uint32Array(Math.max(16, 3*nv)), nt = 0, ne = 0;
  const pr0 = new Uint32Array(n+1), bb = new Float32Array(4*n), flat = [];
  for(let i=0, r=0; i<n; i++){ pr0[i] = r; const r1 = r + rper[i]; let a0=Infinity,b0=Infinity,a1=-Infinity,b1=-Infinity;
    for(let k=r; k<r1; k++) for(let v=rs[k]; v<rs[k+1]; v++){
      const x = hx[v]/2 - OX, y = hy[v]/2 - OY; pos[2*v] = x; pos[2*v+1] = y; pc[v] = cc[i];
      for(let m=0;m<4;m++){ const z = m < M ? vals[i*M+m] : NaN; pv[4*v+m] = z === z ? z : -1e30; }
      if(x<a0)a0=x; if(x>a1)a1=x; if(y<b0)b0=y; if(y>b1)b1=y;
      edge[ne++] = v; edge[ne++] = v+1 < rs[k+1] ? v+1 : rs[k]; }
    bb[4*i]=a0; bb[4*i+1]=b0; bb[4*i+2]=a1; bb[4*i+3]=b1;
    const size = Math.max(a1-a0, b1-b0); for(let k=r; k<r1; k++) for(let v=rs[k]; v<rs[k+1]; v++) psz[v] = size;
    for(let k=r; k<r1; ){ let q = k+1; while(q < r1 && hole[q]) q++;
      const base = rs[k], ax = hx[base], ay = hy[base], holes = []; flat.length = 0;
      for(let j=k; j<q; j++){ if(j > k) holes.push(flat.length/2); for(let v=rs[j]; v<rs[j+1]; v++) flat.push(hx[v]-ax, hy[v]-ay); }
      const t = earcut(flat, holes.length ? holes : null, 2);
      if(nt + t.length > tri.length){ const b = new Uint32Array(Math.ceil((nt+t.length)*1.5)); b.set(tri); tri = b; }
      for(let j=0;j<t.length;j++) tri[nt++] = base + t[j]; k = q; }
    r = r1; }
  pr0[n] = nr; tri = tri.slice(0, nt);
  postMessage({key, n, ids: ids.slice(), pos, pv, pc, psz, tri, edge, rs, pr0, bb},
    [pos.buffer, pv.buffer, pc.buffer, psz.buffer, tri.buffer, edge.buffer, rs.buffer, pr0.buffer, bb.buffer]); }`;
const worker = new Worker(URL.createObjectURL(new Blob([workerSrc], {type:'text/javascript'})));
const pieces = new Map();   // "L/key" -> {state, vao, ntri, nedge, cpu (level 0, for picking), used}
let pieceWaiters = [];
worker.onmessage = e => { const d = e.data, P = pieces.get(d.key); if(!P) return;
  if(d.failed){ P.state = 'failed'; pieceWaiters = pieceWaiters.filter(w => !w(P)); draw(); return; }   // a piece that could not be read is skipped
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const ab = (data, loc, size, type, norm=false) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, type, norm, 0, 0); return b; };
  P.bufs = [ab(d.pos, 0, 2, gl.FLOAT), ab(d.pv, 1, 4, gl.FLOAT), ab(d.pc, 2, 1, gl.UNSIGNED_BYTE), ab(d.psz, 3, 1, gl.FLOAT)];
  const t = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, t); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, d.tri, gl.STATIC_DRAW);
  gl.bindVertexArray(null);
  const eb = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, eb); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, d.edge, gl.STATIC_DRAW);
  P.vao = vao; P.tri = t; P.ebuf = eb; P.ntri = d.tri.length; P.nedge = d.edge.length; P.state = 'ready';
  if(P.level === 0) P.cpu = d;   // shapes kept for clicking and outlining
  pieceWaiters = pieceWaiters.filter(w => !w(P)); draw(); };
function piece(level, key){ const id = level + '/' + key; let P = pieces.get(id);
  if(!P){ P = {id, level, key, state:'loading'}; pieces.set(id, P);
    fetch(`data/L${level}/${key}.bin`).then(r=>{ if(!r.ok) throw new Error(r.status); return r.arrayBuffer(); })
      .then(buf => worker.postMessage({key:id, buf, M, OX, OY}, [buf])).catch(()=>{ P.state = 'failed'; }); }
  P.used = frame; return P; }
function piecesFor(level, x0, y0, x1, y1){ const out = [];
  for(const [key, b] of Object.entries(LV[level].pieces)) if(!(b[0]>x1||b[2]<x0||b[1]>y1||b[3]<y0)) out.push(key);
  return out; }
function trimPieces(){ const l0 = [...pieces.values()].filter(P => P.level===0 && P.state==='ready');
  if(l0.length <= 80) return; l0.sort((a,b)=>a.used-b.used);
  for(const P of l0.slice(0, l0.length-80)){ if(selected && selected.piece===P) continue;
    gl.deleteVertexArray(P.vao); for(const b of P.bufs) gl.deleteBuffer(b); gl.deleteBuffer(P.tri); gl.deleteBuffer(P.ebuf); pieces.delete(P.id); } }

// ---- tiles: rendered at TEX x TEX with 4x edge smoothing, then mipmapped
const TEX = 512, BASE = 262144, ZMAX = 13;
const SAMPLES = Math.min(4, gl.getParameter(gl.MAX_SAMPLES));
const msFB = gl.createFramebuffer(), msRB = gl.createRenderbuffer();
gl.bindRenderbuffer(gl.RENDERBUFFER, msRB); gl.renderbufferStorageMultisample(gl.RENDERBUFFER, SAMPLES, gl.RGBA8, TEX, TEX);
gl.bindFramebuffer(gl.FRAMEBUFFER, msFB); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.RENDERBUFFER, msRB);
const outFB = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
const tiles = new Map();   // "z/i/j" -> {tex, gen, born, used}
// the level whose simplification (0.5, 2, 8, 24 m) stays at or under about half a tile pixel, so switching levels
// moves nothing visibly
const levelFor = z => { const texel = BASE / 2**z / TEX; return texel < 4 ? 0 : texel < 16 ? 1 : texel < 48 ? 2 : 3; };
function renderTile(z, i, j){
  const T = BASE / 2**z, x0 = OX + i*T, y0 = OY + j*T, lvl = levelFor(z);
  const keys = piecesFor(lvl, x0, y0, x0+T, y0+T), ps = keys.map(k => piece(lvl, k));
  if(ps.some(P => P.state === 'loading')) return false;
  gl.bindFramebuffer(gl.FRAMEBUFFER, msFB); gl.viewport(0, 0, TEX, TEX);
  const [sr,sg,sb] = hex(css('--sea')); gl.clearColor(sr, sg, sb, 1); gl.clear(gl.COLOR_BUFFER_BIT);
  const sc = [2/T, 2/T], of = [-(x0-OX)*2/T - 1, -(y0-OY)*2/T - 1];
  gl.useProgram(LAND.p); gl.uniform2fv(LAND.u.sc, sc); gl.uniform2fv(LAND.u.of, of); gl.uniform4f(LAND.u.col, ...hex(css('--land')), 1);
  gl.bindVertexArray(land.vao); gl.drawElements(gl.TRIANGLES, land.n, gl.UNSIGNED_INT, 0);
  const s = SCALES[mode] || {m:4, tf:0, lo:0, hi:1}, filt = filter==='all' ? -1 : meta.councils.indexOf(filter);
  gl.useProgram(PARCEL.p); const u = PARCEL.u;
  gl.uniform2fv(u.sc, sc); gl.uniform2fv(u.of, of); gl.uniform1i(u.m, mode==='c' ? 4 : s.m); gl.uniform1i(u.tf, s.tf);
  gl.uniform1f(u.lo, s.lo); gl.uniform1f(u.hi, s.hi); gl.uniform1i(u.filt, filt);
  gl.uniform3fv(u.c0, hex(css('--lowland'))); gl.uniform3fv(u.c1, hex(css('--accent'))); gl.uniform3fv(u.c2, hex(css('--highland')));
  gl.uniform3fv(u.sea, hex(css('--sea'))); gl.uniform3fv(u.grey, hex(css('--novalue'))); gl.uniform3fv(u.ck, hex(css('--accent'))); gl.uniform3fv(u.cp, hex(css('--highland'))); gl.uniform3fv(u.cn, hex(css('--lowland')));
  for(const P of ps) if(P.state === 'ready'){ gl.bindVertexArray(P.vao); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, P.tri); gl.drawElements(gl.TRIANGLES, P.ntri, gl.UNSIGNED_INT, 0); }
  gl.bindVertexArray(null);
  const key = z+'/'+i+'/'+j; let t = tiles.get(key);
  const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texStorage2D(gl.TEXTURE_2D, Math.log2(TEX)+1, gl.RGBA8, TEX, TEX);
  gl.bindFramebuffer(gl.READ_FRAMEBUFFER, msFB); gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, outFB);
  gl.framebufferTexture2D(gl.DRAW_FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  gl.blitFramebuffer(0, 0, TEX, TEX, 0, 0, TEX, TEX, gl.COLOR_BUFFER_BIT, gl.NEAREST);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  if(t){ gl.deleteTexture(t.tex); t.tex = tex; t.gen = gen; }
  else { t = {z, i, j, tex, gen, born: performance.now()}; tiles.set(key, t); }
  t.used = frame; return true; }
function trimTiles(keep){ if(tiles.size <= 120) return; const list = [...tiles.entries()].filter(([k]) => !keep.has(k)).sort((a,b)=>a[1].used-b[1].used);
  for(const [k, t] of list.slice(0, tiles.size-120)){ gl.deleteTexture(t.tex); tiles.delete(k); } }

// ---- a frame
let frame = 0, pending = false;
function draw(){ if(pending) return; pending = true; requestAnimationFrame(()=>{ pending = false; try { render(); } catch(e){ say('The map could not be drawn (' + (e && e.message || e) + '). Please report this message.'); } }); }
function quad(t, alpha){ const T = BASE / 2**t.z, x0 = OX + t.i*T, y0 = OY + t.j*T;
  const cx = x => (sx(x)/W)*2-1, cy = y => 1-(sy(y)/H)*2;
  gl.uniform4f(QUAD.u.rect, cx(x0), cy(y0), cx(x0+T), cy(y0+T)); gl.uniform4f(QUAD.u.uvr, 0, 0, 1, 1);
  gl.bindTexture(gl.TEXTURE_2D, t.tex); gl.uniform1f(QUAD.u.alpha, alpha); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); }
// Two adjacent tile levels are always drawn and blended by the exact zoom (t), and so are their boundaries and water:
// nothing ever switches at once, so zooming changes the picture gradually.
function ensureTiles(z, x0, y0, x1, y1, keep, state){ const T = BASE / 2**z;
  const i0 = Math.floor((x0-OX)/T), i1 = Math.floor((x1-OX)/T), j0 = Math.floor((y0-OY)/T), j1 = Math.floor((y1-OY)/T);
  const want = []; for(let j=j0;j<=j1;j++) for(let i=i0;i<=i1;i++) want.push([i, j, Math.hypot(OX+(i+.5)*T-view.cx, OY+(j+.5)*T-view.cy)]);
  want.sort((a,b)=>a[2]-b[2]);
  for(const [i, j] of want){ const k = z+'/'+i+'/'+j, t = tiles.get(k); keep.add(k);
    if(t && t.gen === gen){ t.used = frame; continue; }
    if(state.budget > 0){ if(renderTile(z, i, j)) state.budget--; else state.waiting = true; } else state.waiting = true; }
  return want; }
function render(){
  if(!(W > 0 && H > 0)) return; frame++;
  const zf = Math.max(0, Math.min(ZMAX, Math.log2(BASE * view.s * dpr / TEX))), za = Math.min(ZMAX-1, Math.floor(zf)), zb = za + 1, t = Math.min(1, zf - za);
  const vx0 = view.cx - W/2/view.s, vx1 = view.cx + W/2/view.s, vy0 = view.cy - H/2/view.s, vy1 = view.cy + H/2/view.s;
  const keep = new Set(), state = {budget: 4, waiting: false};
  // the nearer level first, so it is ready first
  const order = t < .5 ? [za, zb] : [zb, za], wants = {};
  for(const z of order) wants[z] = ensureTiles(z, vx0, vy0, vx1, vy1, keep, state);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, canvas.width, canvas.height);
  gl.clearColor(...hex(css('--sea')), 1); gl.clear(gl.COLOR_BUFFER_BIT);
  gl.useProgram(QUAD.p); gl.uniform1i(QUAD.u.tex, 0); gl.activeTexture(gl.TEXTURE0); gl.bindVertexArray(null);
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  const now = performance.now(); let fading = false;
  const inView = q => { const TT = BASE / 2**q.z, x0 = OX+q.i*TT, y0 = OY+q.j*TT; return !(x0>vx1||x0+TT<vx0||y0>vy1||y0+TT<vy0); };
  // tiles of other levels already made cover the view while these arrive
  const others = [...tiles.values()].filter(q => q.z !== za && q.z !== zb && Math.abs(q.z - zf) <= 3 && inView(q)).sort((a,b)=>a.z-b.z);
  for(const q of others){ quad(q, 1); keep.add(q.z+'/'+q.i+'/'+q.j); q.used = frame; }
  // level a at full strength, level b over it at strength t (each also fading in when first made)
  for(const [z, w] of [[za, 1], [zb, t]]) for(const [i, j] of wants[z]){ const q = tiles.get(z+'/'+i+'/'+j); if(!q) continue;
    const a = Math.min(1, (now - q.born) / 220); if(a < 1) fading = true; if(w*a > 0.002) quad(q, w*a); }
  // boundaries and water from both levels' pieces into one coverage layer (red, green: boundaries of a and b; blue,
  // alpha: water of a and b), combined by keeping the strongest, then laid on blended by t
  const la = levelFor(za), lb = levelFor(zb), filt = filter==='all' ? -1 : meta.councils.indexOf(filter);
  const ready = l => piecesFor(l, vx0, vy0, vx1, vy1).map(k => piece(l, k)).filter(P => P.state === 'ready');
  const pa = ready(la), pb = lb === la ? pa : ready(lb);
  if(pa.length || pb.length){ gl.disable(gl.BLEND); edgeTarget(); gl.bindFramebuffer(gl.FRAMEBUFFER, edgeFB); gl.viewport(0, 0, edgeW, edgeH);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); gl.enable(gl.BLEND); gl.blendEquation(gl.MAX);
    const s = view.s, sc = [2*s/W, 2*s/H], of = [(OX-view.cx)*2*s/W, (OY-view.cy)*2*s/H];
    // thickness and strength follow the zoom: about 1.5 screen points at full strength from 0.3 pixels per metre in,
    // easing to one device pixel at 60% by 0.05 and out
    const k = Math.max(0, Math.min(1, (s - 0.05) / 0.25)), n = Math.max(1, Math.round(1 + (1.5*dpr - 1) * k));
    gl.useProgram(EDGE.p); gl.uniform2fv(EDGE.u.sc, sc); gl.uniform2fv(EDGE.u.of, of);
    gl.uniform1i(EDGE.u.filt, filt); gl.uniform4f(EDGE.u.col, 1, 1, 1, 0.6 + 0.4*k); gl.uniform1f(EDGE.u.pxm, s*dpr);
    for(const [ps, mask] of [[pa, [true,false,false,false]], [pb, [false,true,false,false]]]){ gl.colorMask(...mask);
      for(let a=0; a<n; a++) for(let b=0; b<n; b++){ gl.uniform2f(EDGE.u.shift, a*.75*2/canvas.width, b*.75*2/canvas.height);
        for(const P of ps){ gl.bindVertexArray(P.vao); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, P.ebuf); gl.drawElements(gl.LINES, P.nedge, gl.UNSIGNED_INT, 0); } } }
    gl.useProgram(WATERP.p); gl.uniform2fv(WATERP.u.sc, sc); gl.uniform2fv(WATERP.u.of, of); gl.uniform3f(WATERP.u.col, 1, 1, 1);
    for(const [ps, mask] of [[pa, [false,false,true,false]], [pb, [false,false,false,true]]]){ gl.colorMask(...mask);
      for(const P of ps){ gl.bindVertexArray(P.vao); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, P.tri); gl.drawElements(gl.TRIANGLES, P.ntri, gl.UNSIGNED_INT, 0); } }
    gl.colorMask(true, true, true, true); gl.bindVertexArray(null); gl.blendEquation(gl.FUNC_ADD);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, canvas.width, canvas.height); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    // a level whose pieces are not loaded yet takes the other's
    const wa = pb.length ? 1 - t : 1, wb = pa.length ? t : 1;
    gl.useProgram(COVER.p); gl.uniform1i(COVER.u.tex, 0); gl.bindTexture(gl.TEXTURE_2D, edgeTex);
    gl.uniform3fv(COVER.u.col, hex(css('--sheet'))); gl.uniform4f(COVER.u.w, wa, wb, 0, 0); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.uniform3fv(COVER.u.col, hex(css('--sea'))); gl.uniform4f(COVER.u.w, 0, 0, wa, wb); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); }
  const waiting = state.waiting;
  gl.disable(gl.BLEND);
  overlay();
  trimTiles(keep); trimPieces();
  if(waiting || fading) draw();
  if(waiting && !loadedOnce) say('Loading parcels for this area…'); else if(!waiting && !loadedOnce){ loadedOnce = true; say(status()); }
}
let loadedOnce = false;
const status = () => `Showing ${fmt(meta.parcels)} parcels. Search by legal description or address; select a parcel for its values.`;

// ---- overlay: selected parcel, scale bar
function niceLen(m){ const p = 10**Math.floor(Math.log10(m)); for(const k of [1,2,5,10]) if(k*p >= m) return k*p; return 10*p; }
function overlay(){ const c = octx; c.setTransform(1,0,0,1,0,0); c.clearRect(0,0,over.width,over.height); c.setTransform(dpr,0,0,dpr,0,0);
  if(selected){ c.strokeStyle = css('--mark'); c.lineWidth = 2.5; c.beginPath(); const d = selected.cpu;
    for(let r=d.pr0[selected.k]; r<d.pr0[selected.k+1]; r++){ const a = d.rs[r], e = d.rs[r+1];
      c.moveTo(sx(d.pos[2*a]+OX), sy(d.pos[2*a+1]+OY)); for(let v=a+1; v<e; v++) c.lineTo(sx(d.pos[2*v]+OX), sy(d.pos[2*v+1]+OY)); c.closePath(); }
    c.stroke();
    const b = selected.cpu.bb, k = selected.k; if((b[4*k+2]-b[4*k])*view.s < 6){ c.beginPath(); c.arc(sx(selected.x), sy(selected.y), 9, 0, Math.PI*2); c.stroke(); } }
  const m = niceLen(120/view.s), px = m*view.s; c.fillStyle = css('--land'); c.fillRect(W-px-20, 8, px+12, 28);
  c.font = '10px ' + css('--mono'); c.fillStyle = css('--ink'); c.fillRect(W-px-14, 14, px, 3); c.fillText(m >= 1000 ? (m/1000)+' km' : m+' m', W-px-14, 30); }

// ---- selecting a parcel: the full-detail shapes under the point, then its values
let selected = null;
function ensure(level, key){ const P = piece(level, key); if(P.state === 'ready') return Promise.resolve(P);
  return new Promise(res => pieceWaiters.push(Q => { if(Q === P){ res(P); return true; } return false; })); }
function insideRing(d, a, e, x, y){ let c = false; for(let v=a, w=e-1; v<e; w=v++){ const xi=d.pos[2*v], yi=d.pos[2*v+1], xj=d.pos[2*w], yj=d.pos[2*w+1];
  if(((yi>y)!==(yj>y)) && (x < (xj-xi)*(y-yi)/(yj-yi)+xi)) c = !c; } return c; }
async function pickAt(wx, wy, wantId){ const x = wx-OX, y = wy-OY;
  const keys = piecesFor(0, wx, wy, wx, wy); const ps = await Promise.all(keys.map(k => ensure(0, k)));
  for(const P of ps){ const d = P.cpu; if(!d) continue;
    for(let k=0;k<d.n;k++){ if(d.ids[k] < 0 || (wantId != null && d.ids[k] !== wantId)) continue;   // -1: water
      if(wantId == null && (x<d.bb[4*k]||x>d.bb[4*k+2]||y<d.bb[4*k+1]||y>d.bb[4*k+3])) continue;
      let inside = wantId != null; if(!inside) for(let r=d.pr0[k]; r<d.pr0[k+1]; r++) if(insideRing(d, d.rs[r], d.rs[r+1], x, y)) inside = !inside;
      if(inside) return {piece:P, cpu:d, k, id:d.ids[k], x:wx, y:wy}; } }
  return null; }
const ROWS = [['area_m2','Area','m²',0],['ground_mean_m','Mean ground height','m',1],['slope_p90_deg','Slope, 90th percentile','°',1],
  ['lidar_coverage_pct','LiDAR coverage','%',1],['flow_path_m','Overland flow paths','m',0],['catchment_area_max_m2','Upslope catchment','m²',0],
  ['title_count','Titles','',0],['easements_n','Easement parcels','',0],
  ['ww_pipe_dist_m','Nearest sewer','m',1],['ww_pipe_year','Sewer installed','',0],['ww_pipe_condition_grade','Sewer condition grade (1–5)','',0],['ws_pipe_dist_m','Nearest water main','m',1]];
const NROWS = [['area_m2','Area','m²',0],['ground_mean_m','Mean ground height (10 m grid; one point on very small parcels)','m',1],
  ['catchment_area_max_m2','Upslope catchment (10 m grid; at least, where the catchment runs past the grid)','m²',0],['building_cover_pct','Under building outlines','%',0],['title_count','Titles','',0]];
const COUNCIL = {k:'Kāpiti Coast', p:'Porirua', n:'Greater Wellington, national index'};
const details = new Map();
async function select(hit){ selected = hit; draw(); const det = $('detail');
  if(!hit){ det.className = 'empty'; det.textContent = 'Select a parcel on the plan, or search for a legal description or address.'; return; }
  const key = hit.piece.key; if(!details.has(key)) details.set(key, fetch(`data/detail/${key}.json`).then(r=>r.json()));
  const row = (await details.get(key))[String(hit.id)]; if(!row || selected !== hit) return;
  const r = Object.fromEntries(meta.detail_fields.map((f,i)=>[f, row[i]]));
  const list = r.c === 'n' ? NROWS : ROWS.filter(([k]) => r.c === 'k' || !k.startsWith('w'));
  const val = (k, d) => k === 'ww_pipe_year' ? String(r[k]) + ([1979, 1980].includes(r[k]) ? ' (KCDC records many pipes with this year; it may be a placeholder)' : '') : fmt(r[k], d);
  const items = list.map(([k,l,u,d]) => `<dt>${esc(l)}</dt><dd>${r[k]==null ? '—' : esc(val(k,d))+(u ? ' '+u : '')}</dd>`).join('');
  det.className = '';
  det.innerHTML = `<h3>${esc(r.appellation || 'Parcel ' + hit.id)}</h3>
    <div class="mono" style="font-size:.8rem;color:var(--muted)">${esc(r.c==='n' ? (r.territorial_authority || 'Greater Wellington') : COUNCIL[r.c])} · LINZ id ${esc(hit.id)} · ${esc(r.parcel_intent)}</div>
    ${r.address ? `<div style="margin-top:6px">${esc(r.address)}</div>` : ''}
    <dl>${items}</dl>
    <div style="font-size:.78rem;color:var(--muted)">${r.c==='n' ? 'From the national index pilot: LINZ data only, ground on a 10 m grid. ' : ''}— means no value: not mapped, not measured, or outside the source's coverage.${r.c==='p' ? ' Porirua has no three-waters data here.' : ''}</div>`; }

// ---- pan and zoom
let drag = null, moved = false, pinch = null;
canvas.addEventListener('pointerdown', e => { touched = true; canvas.setPointerCapture(e.pointerId); drag = {x:e.clientX, y:e.clientY, cx:view.cx, cy:view.cy}; moved = false; });
canvas.addEventListener('pointermove', e => { if(!drag || pinch) return; const dx = e.clientX-drag.x, dy = e.clientY-drag.y; if(Math.abs(dx)+Math.abs(dy) > 3) moved = true;
  view.cx = drag.cx - dx/view.s; view.cy = drag.cy + dy/view.s; draw(); });
canvas.addEventListener('pointerup', async e => { if(drag && !moved){ const r = canvas.getBoundingClientRect(), px = e.clientX-r.left, py = e.clientY-r.top;
  select(await pickAt(view.cx + (px-W/2)/view.s, view.cy - (py-H/2)/view.s)); } drag = null; });
function zoomAt(f, px, py){ touched = true; const wx = view.cx + (px-W/2)/view.s, wy = view.cy - (py-H/2)/view.s; view.s = Math.max(0.002, Math.min(8, view.s*f));
  view.cx = wx - (px-W/2)/view.s; view.cy = wy + (py-H/2)/view.s; draw(); }
canvas.addEventListener('wheel', e => { e.preventDefault(); const r = canvas.getBoundingClientRect(); zoomAt(Math.exp(-e.deltaY*0.0015), e.clientX-r.left, e.clientY-r.top); }, {passive:false});
canvas.addEventListener('touchstart', e => { if(e.touches.length === 2){ const [a,b] = e.touches; pinch = {d: Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY)}; } }, {passive:true});
canvas.addEventListener('touchmove', e => { if(pinch && e.touches.length === 2){ const [a,b] = e.touches, d = Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY);
  const r = canvas.getBoundingClientRect(); zoomAt(d/pinch.d, (a.clientX+b.clientX)/2-r.left, (a.clientY+b.clientY)/2-r.top); pinch.d = d; } }, {passive:true});
canvas.addEventListener('touchend', () => { pinch = null; });
$('zin').onclick = () => zoomAt(1.6, W/2, H/2); $('zout').onclick = () => zoomAt(1/1.6, W/2, H/2); $('zreset').onclick = () => { fit(); draw(); };

// ---- controls and search
const recolour = () => { gen++; legend(); draw(); };
$('colour').onchange = e => { mode = e.target.value; recolour(); };
$('council').onchange = e => { filter = e.target.value; recolour(); };
const res = $('results'); let search = null;
$('search').addEventListener('input', async e => {
  const q = e.target.value.trim().toLowerCase(); res.innerHTML = ''; if(q.length < 3){ res.hidden = true; return; }
  if(!search){ res.hidden = false; res.innerHTML = '<div class="empty" style="padding:5px 6px">Loading the search list…</div>';
    search = fetch('data/search.json').then(r=>r.json()).then(s => (s.lt = s.t.map(t => t.toLowerCase()), s)); }
  const s = await search; if(e.target.value.trim().toLowerCase() !== q) return; res.innerHTML = '';
  // exact matches first (a legal description or address equal to what was typed), then others containing it
  const exact = [], part = [];
  for(let i=0; i<s.id.length; i++){ const t = s.lt[i];   // the whole list, so an exact match late in it is found
    if(String(s.id[i]) === q || t.split('|').includes(q)) exact.push(i); else if(part.length < 40 && t.includes(q)) part.push(i); }
  const hits = exact.concat(part).slice(0, 40);
  res.hidden = false;
  if(!hits.length){ res.innerHTML = '<div class="empty" style="padding:5px 6px">No parcel matches. Try the lot and DP number, for example "Lot 2 DP 12726", or an address.</div>'; return; }
  const SHORT = {k:'Kāpiti', p:'Porirua', n:'Gtr Wellington'};
  for(const i of hits){ const b = document.createElement('button'), [app, addr] = s.t[i].split('|');
    b.innerHTML = `<span>${esc(app || addr)}</span><span class="c">${SHORT[s.c[i]]}</span>`; if(addr) b.title = addr;
    b.onclick = async () => { touched = true; view.cx = s.x[i]; view.cy = s.y[i]; view.s = Math.max(view.s, 1); draw(); select(await pickAt(s.x[i], s.y[i], s.id[i])); };
    res.appendChild(b); } });

window.addEventListener('resize', resize);
if(window.ResizeObserver) new ResizeObserver(() => { const r = canvas.getBoundingClientRect(); if(Math.round(r.width) !== Math.round(W) || Math.round(r.height) !== Math.round(H)) resize(); }).observe(canvas);
if(window.matchMedia) window.matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', recolour);
new MutationObserver(recolour).observe(document.documentElement, {attributes:true, attributeFilter:['data-theme']});
canvas.addEventListener('webglcontextlost', e => { e.preventDefault(); say('The graphics card reset the map. Reload the page to see it again.'); });
window.landqMap = { view, tiles, pieces, get frame(){ return frame; } };   // for checking from the browser console
legend(); resize(); say('Loading parcels…');
})();
