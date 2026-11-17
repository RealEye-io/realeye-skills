// Hero anatomy probe. Runs in the page at capture time and returns a JSON string:
//   aoi  : first-draft boxes [x1,y1,x2,y2] (CSS px) for announce, header, logo, nav_links, nav_cta, eyebrow, headline,
//          subhead, cta_primary, cta_secondary, form, micro, visual, trust, rating
//   info : texts and facts (headline text/font/lines, subhead, CTA labels and style, nav labels, trust label, theme ...)
//   inv  : inventory of every visible text block, button and media element (used to correct boxes offline, by text)
// Heuristics only: ALWAYS review the overlay sheets and fix wrong boxes with overrides (see resolve.ps1).
(() => {
  const vw = innerWidth, vh = innerHeight;
  const out = { site: window.__AP_SITE || null, file: window.__AP_FILE || null, vw, vh, url: location.href, title: (document.title || '').slice(0, 100), aoi: {}, info: {}, inv: {}, err: [] };
  const step = (name, fn) => { try { fn(); } catch (x) { out.err.push(name + ': ' + String((x && x.message) || x).slice(0, 140)); } };
  const S = e => getComputedStyle(e);
  const T0 = e => (((e.innerText !== undefined && e.innerText !== null) ? e.innerText : e.textContent) || e.value || e.getAttribute('aria-label') || '').toString().trim().replace(/\s+/g, ' ');
  const T = e => { const t = T0(e); const h = t.length >> 1; return (t.length > 5 && t.length % 2 === 1 && t[h] === ' ' && t.slice(0, h) === t.slice(h + 1)) ? t.slice(0, h) : t; };   // "Sign in Sign in" -> "Sign in"
  const R = e => e.getBoundingClientRect();
  const A = b => Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);
  const U = bs => [Math.min(...bs.map(b => b[0])), Math.min(...bs.map(b => b[1])), Math.max(...bs.map(b => b[2])), Math.max(...bs.map(b => b[3]))];
  const hov = (a, b) => Math.min(a[2], b[2]) - Math.max(a[0], b[0]);
  const vov = (a, b) => Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  const inside = (a, b) => A(a) ? (Math.max(0, hov(a, b)) * Math.max(0, vov(a, b))) / A(a) : 0;   // fraction of a that lies inside b
  const rgb = c => ((c || '').match(/[\d.]+/g) || []).map(Number);
  const alpha = c => { const v = rgb(c); return v.length < 3 ? 0 : (v[3] === undefined ? 1 : v[3]); };
  const hex = c => { const v = rgb(c); return v.length < 3 ? null : '#' + v.slice(0, 3).map(x => Math.round(x).toString(16).padStart(2, '0')).join(''); };
  const cd = (a, b) => (!a || !b) ? 999 : Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2);
  const cv = e => { try { return !e.checkVisibility || e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }); } catch (x) { return true; } };
  const quick = e => { const r = R(e); return r.width >= 5 && r.height >= 5 && r.bottom > 3 && r.top < vh - 3 && r.right > 3 && r.left < vw - 3; };
  // box clipped to the viewport and to overflow-hidden ancestors (carousels, cropped mockups)
  const B = e => {
    const r = R(e); let x1 = Math.max(0, r.left), y1 = Math.max(0, r.top), x2 = Math.min(vw, r.right), y2 = Math.min(vh, r.bottom);
    let p = e.parentElement, k = 0;
    while (p && p !== document.documentElement && k++ < 40) {
      const s = S(p);
      if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
        const q = R(p);
        if (s.overflowX !== 'visible') { x1 = Math.max(x1, q.left); x2 = Math.min(x2, q.right); }
        if (s.overflowY !== 'visible') { y1 = Math.max(y1, q.top); y2 = Math.min(y2, q.bottom); }
      }
      if (s.position === 'fixed') break;
      p = p.parentElement;
    }
    return [Math.round(x1), Math.round(y1), Math.round(Math.max(x1, x2)), Math.round(Math.max(y1, y2))];
  };
  const vis = e => { if (!quick(e) || !cv(e)) return false; const b = B(e); return (b[2] - b[0]) >= 5 && (b[3] - b[1]) >= 5; };
  // text-tight box: union of the text line boxes, clipped like B()
  const tight = e => {
    const cb = B(e);
    try {
      const rg = document.createRange(); rg.selectNodeContents(e);
      const rs = [...rg.getClientRects()].filter(r => r.width > 2 && r.height > 4);
      if (rs.length) {
        const o = [Math.round(Math.max(cb[0], Math.min(...rs.map(r => r.left)))), Math.round(Math.max(cb[1], Math.min(...rs.map(r => r.top)))),
                   Math.round(Math.min(cb[2], Math.max(...rs.map(r => r.right)))), Math.round(Math.min(cb[3], Math.max(...rs.map(r => r.bottom))))];
        if (o[2] - o[0] > 3 && o[3] - o[1] > 3) return o;
      }
    } catch (x) {}
    return cb;
  };
  const firstTextEl = e => { const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { if (n.textContent.trim().length > 1) return n.parentElement; } return e; };
  const fontOf = e => parseFloat(S(firstTextEl(e)).fontSize) || 0;
  const effBg = e => { let n = e; while (n && n.nodeType === 1) { const s = S(n); if (alpha(s.backgroundColor) > 0.5) return rgb(s.backgroundColor).slice(0, 3); if (s.backgroundImage && s.backgroundImage !== 'none') return null; n = n.parentElement; } return [255, 255, 255]; };

  let hdr = null, H = null, blocks = [], btns = [], media = [];
  const inHdr = b => !!hdr && b[1] >= hdr[1] - 3 && b[3] <= hdr[3] + 3;

  // ---- header band -------------------------------------------------------------------------------
  step('header', () => {
    const c = [...document.querySelectorAll('header, nav, [role=banner], [role=navigation]')].filter(e => { if (!quick(e)) return false; const r = R(e); return r.top < 150 && r.top > -12 && r.height >= 28 && r.height < 240 && r.width > vw * 0.5 && cv(e); });
    if (c.length) hdr = U(c.map(B));
    else {
      const f = [...document.querySelectorAll('body *')].filter(e => { if (!quick(e)) return false; const r = R(e); if (r.top > 60 || r.height < 36 || r.height > 200 || r.width < vw * 0.8) return false; const p = S(e).position; return (p === 'fixed' || p === 'sticky') && cv(e); });
      if (f.length) hdr = U(f.map(B));
    }
    if (!hdr) {   // no header element: the row of links nearest the top
      const ls = [...document.querySelectorAll('a')].filter(e => { if (!quick(e)) return false; const r = R(e); return r.top < 130 && r.height < 64 && T(e).length >= 2 && T(e).length <= 26 && cv(e); });
      const rows = []; for (const e of ls) { const r = R(e), cy = (r.top + r.bottom) / 2; const row = rows.find(x => Math.abs(x.cy - cy) <= 14); if (row) row.items.push(e); else rows.push({ cy, items: [e] }); }
      const best = rows.sort((a, b) => b.items.length - a.items.length)[0];
      if (best && best.items.length >= 3) { const u = U(best.items.map(B)); hdr = [0, Math.max(0, u[1] - 14), vw, u[3] + 14]; }
    }
  });

  // ---- announcement bar (thin full-width strip at the very top) ---------------------------------------
  step('announce', () => {
    const c = [...document.querySelectorAll('body *')].filter(e => {
      const r = R(e); if (r.top > 8 || r.top < -4 || r.height < 22 || r.height > 92 || r.width < vw * 0.9) return false;
      if (!cv(e)) return false; const t = T(e);
      return t.length >= 18 && t.length <= 280 && e.querySelectorAll('a,button').length <= 4 && !e.querySelector('nav, [role=navigation], input, img[alt*="logo" i]');
    });
    const e = c.sort((a, b) => R(a).bottom - R(b).bottom)[0];
    if (!e) return; const b = B(e);
    if (hdr && b[3] > hdr[3] - 24 && b[1] >= hdr[1] - 2 && (hdr[3] - hdr[1]) < 100) return;   // that IS the header
    out.aoi.announce = b; out.info.announce = T(e).slice(0, 180);
    if (hdr && hdr[1] < b[3] && hdr[3] > b[3] + 20) hdr[1] = b[3];
  });

  // ---- inventory: text blocks ----------------------------------------------------------------------
  step('blocks', () => {
    const set = new Set();
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n, guard = 0;
    while ((n = tw.nextNode()) && guard++ < 30000) {
      if (n.textContent.trim().length < 2) continue;
      let b = n.parentElement; if (!b) continue;
      const tg = b.tagName; if (tg === 'SCRIPT' || tg === 'STYLE' || tg === 'NOSCRIPT' || tg === 'OPTION') continue;
      if (!quick(b) && !(b.parentElement && quick(b.parentElement))) continue;
      let k = 0; while (b && k++ < 8) { const d = S(b).display; if (d !== 'inline' && d !== 'contents') break; b = b.parentElement; }
      if (b && b !== document.body) set.add(b);
    }
    document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, blockquote, label').forEach(e => { if (quick(e) && T(e).length > 1) set.add(e); });
    blocks = [...set].filter(vis).map(e => ({ e, t: T(e) })).filter(x => x.t.length >= 2 && x.t.length <= 520)
      .map(x => ({ e: x.e, t: x.t, b: tight(x.e), f: fontOf(x.e), tag: x.e.tagName.toLowerCase() })).filter(x => A(x.b) > 40);
  });

  // ---- inventory: buttons ---------------------------------------------------------------------------
  const btnInfo = e => {
    const eb = B(e), c0 = e.firstElementChild, c1 = c0 && c0.firstElementChild;
    for (const x of [e, c0, c1]) {
      if (!x || !quick(x)) continue; const s = S(x), xb = B(x), h = xb[3] - xb[1], w = xb[2] - xb[0];
      if (x !== e && A(xb) < 0.45 * A(eb)) continue;
      if (h < 24 || h > 130 || w < 44 || A(xb) > 160000) continue;
      const hasBg = alpha(s.backgroundColor) > 0.5, hasGrad = !!s.backgroundImage && s.backgroundImage.includes('gradient');
      const hasBorder = parseFloat(s.borderTopWidth) >= 1 && s.borderTopStyle !== 'none' && alpha(s.borderTopColor) > 0.3;
      if (!(hasBg || hasGrad || hasBorder)) continue;
      const pad = parseFloat(s.paddingLeft) + parseFloat(s.paddingRight);
      if (pad < 10 && e.tagName !== 'BUTTON' && e.tagName !== 'INPUT') continue;
      const own = hasBg ? rgb(s.backgroundColor).slice(0, 3) : null, par = effBg(x.parentElement);
      const filled = hasGrad || (!!own && cd(own, par) > 45);
      return { filled, outline: !filled && hasBorder, bg: hasGrad ? 'gradient' : (own ? hex(s.backgroundColor) : null), fg: hex(s.color), box: xb };
    }
    return null;
  };
  step('buttons', () => {
    btns = [...document.querySelectorAll('a, button, [role=button], input[type=submit], input[type=button]')].filter(vis)
      .map(e => ({ e, t: T(e), i: btnInfo(e) })).filter(x => x.i && x.t.length >= 2 && x.t.length <= 42);
    btns = btns.filter(x => !btns.some(y => y !== x && x.e.contains(y.e)));               // keep innermost
    for (const x of btns) {                                                               // tab / filter-chip groups are not CTAs
      const sib = btns.filter(y => (y.e.parentElement === x.e.parentElement || (y.e.parentElement && x.e.parentElement && y.e.parentElement.parentElement === x.e.parentElement.parentElement)) && Math.abs((y.i.box[3] - y.i.box[1]) - (x.i.box[3] - x.i.box[1])) <= 4);
      x.chip = sib.length >= 4 && !inHdr(x.i.box);
    }
    const bs = new Set(btns.map(x => x.e));
    for (const k of blocks) { k.isBtn = bs.has(k.e) || [...bs].some(b => b.contains(k.e)); }
  });

  // ---- headline ---------------------------------------------------------------------------------
  step('headline', () => {
    const ok = x => x.t.length >= 3 && x.t.length <= 280 && !inHdr(x.b) && !(out.aoi.announce && x.b[3] <= out.aoi.announce[3] + 2);
    const h1s = [...document.querySelectorAll('h1')].filter(vis).map(e => ({ e, t: T(e), b: tight(e), f: fontOf(e) })).filter(ok);
    let h = h1s.sort((a, b) => A(b.b) - A(a.b))[0] || null;
    const alt = blocks.filter(x => ok(x) && !x.isBtn && x.b[1] < vh * 0.72 && x.t.split(' ').length >= 2 && x.t.length <= 120).sort((a, b) => (b.f - a.f) || (A(b.b) - A(a.b)))[0];
    if (alt && (!h || (alt.f >= h.f * 1.3 && !h.e.contains(alt.e) && !alt.e.contains(h.e)))) { h = alt; out.info.headline_not_h1 = true; }
    if (!h) return;
    // headline split into several same-size lines / elements: merge the adjacent ones
    const parts = [h]; let grew = true;
    while (grew && parts.length < 5) { grew = false; const u = U(parts.map(p => p.b));
      const nx = [...h1s, ...blocks].find(x => !parts.some(p => p.e === x.e || p.e.contains(x.e) || x.e.contains(p.e)) && ok(x) && !x.isBtn && Math.abs(x.f - h.f) <= 2 && hov(x.b, u) > 0 && (Math.abs(x.b[1] - u[3]) <= h.f * 0.7 || Math.abs(u[1] - x.b[3]) <= h.f * 0.7));
      if (nx) { parts.push(nx); grew = true; } }
    if (parts.length > 1) { parts.sort((a, b) => (a.b[1] - b.b[1]) || (a.b[0] - b.b[0])); h = { e: h.e, t: parts.map(p => p.t).join(' '), b: U(parts.map(p => p.b)), f: h.f }; out.info.headline_parts = parts.length; }
    H = h.e; const s = S(firstTextEl(H)); const lh = parseFloat(s.lineHeight) || h.f * 1.2; const cx = (h.b[0] + h.b[2]) / 2;
    out.info.theme_text = hex(s.color);
    out.aoi.headline = h.b;
    out.info.headline = { t: h.t.slice(0, 200), f: +h.f.toFixed(1), weight: s.fontWeight, family: (s.fontFamily || '').split(',')[0].replace(/["']/g, '').trim().slice(0, 30), color: hex(s.color),
      lines: Math.max(1, Math.round((h.b[3] - h.b[1]) / lh)), words: h.t.split(' ').length, chars: h.t.length,
      align: Math.abs(cx - vw / 2) < vw * 0.06 ? 'center' : (cx < vw / 2 ? 'left' : 'right') };
  });
  const rel = x => !!H && x.e !== H && !H.contains(x.e) && !x.e.contains(H) && !(out.aoi.headline && inside(x.b, out.aoi.headline) > 0.8);

  // ---- eyebrow (small line right above the headline) ------------------------------------------------
  step('eyebrow', () => {
    const hb = out.aoi.headline; if (!hb) return; const hf = out.info.headline.f;
    const c = blocks.filter(x => rel(x) && x.b[3] <= hb[1] + 6 && x.b[3] >= hb[1] - 84 && hov(x.b, hb) > 0 && x.f <= hf * 0.72 && x.t.length >= 3 && x.t.length <= 110 && !inHdr(x.b) && !(out.aoi.announce && x.b[3] <= out.aoi.announce[3] + 2))
      .sort((a, b) => b.b[3] - a.b[3]);
    if (!c[0]) return; const line = c.filter(x => Math.abs(x.b[3] - c[0].b[3]) < 16 && !c.some(y => y !== x && y.e.contains(x.e) && Math.abs(y.b[3] - c[0].b[3]) < 16));
    out.aoi.eyebrow = U(line.map(x => x.b)); out.info.eyebrow = [...new Set(line.sort((a, b) => a.b[0] - b.b[0]).map(x => x.t))].join(' ').slice(0, 140);
  });

  // ---- subhead / slogan (first text block under the headline) ---------------------------------------
  step('subhead', () => {
    const hb = out.aoi.headline; if (!hb) return; const hf = out.info.headline.f;
    let c = blocks.filter(x => rel(x) && !x.isBtn && x.b[1] >= hb[3] - 8 && x.b[1] <= hb[3] + 180 && hov(x.b, hb) > 0.3 * Math.min(x.b[2] - x.b[0], hb[2] - hb[0]) && x.f >= 13 && x.f <= Math.max(17, hf * 0.82) && x.t.length >= 20 && x.t.length <= 460);
    c = c.filter(x => !c.some(y => y !== x && y.e.contains(x.e))).sort((a, b) => a.b[1] - b.b[1]);
    if (!c[0]) return;
    out.aoi.subhead = c[0].b; out.info.subhead = { t: c[0].t.slice(0, 320), f: +c[0].f.toFixed(1), words: c[0].t.split(' ').length };
  });

  // ---- hero CTAs --------------------------------------------------------------------------------
  const ctaRe = /get started|try|start|sign ?up|demo|free|book|talk|contact sales|request|join|download|get |launch|create|install|buy|see (it|how)|watch|explore|learn more|shop|continue|subscribe|run /i;
  step('cta', () => {
    const hb = out.aoi.headline, top = hdr ? hdr[3] - 4 : 0;
    const c = btns.filter(x => !x.chip && x.i.box[1] >= top && !inHdr(x.i.box) && !(out.aoi.announce && x.i.box[3] <= out.aoi.announce[3] + 2));
    if (!c.length) return;
    const score = x => { const b = x.i.box; let s = 0; if (ctaRe.test(x.t)) s += 3; if (x.i.filled) s += 2;
      if (hb) { const dy = b[1] - hb[3]; if (dy >= -12 && dy < 460) s += 3 - dy / 150; else if (dy < -12) s -= 3; else s -= 1; if (hov(b, hb) > 0 || Math.abs((b[0] + b[2]) / 2 - (hb[0] + hb[2]) / 2) < vw * 0.25) s += 1; }
      else s += (vh - b[1]) / vh; return s; };
    const main = c.slice().sort((a, b) => score(b) - score(a))[0], mb = main.i.box;
    const grp = c.filter(x => x === main || (Math.abs(x.i.box[1] - mb[1]) <= 18 && Math.min(Math.abs(x.i.box[0] - mb[2]), Math.abs(mb[0] - x.i.box[2])) <= 90) || (Math.abs(x.i.box[0] - mb[0]) <= 16 && Math.min(Math.abs(x.i.box[1] - mb[3]), Math.abs(mb[1] - x.i.box[3])) <= 34));
    const order = grp.slice().sort((a, b) => (a.i.box[1] - b.i.box[1] > 12 ? 1 : (b.i.box[1] - a.i.box[1] > 12 ? -1 : a.i.box[0] - b.i.box[0])));
    const rank = grp.slice().sort((a, b) => (b.i.filled - a.i.filled) || (ctaRe.test(b.t) - ctaRe.test(a.t)) || (order.indexOf(a) - order.indexOf(b)));
    const p = rank[0], q = rank[1];
    out.aoi.cta_primary = p.i.box; out.info.cta_primary = { t: p.t, filled: p.i.filled, bg: p.i.bg, fg: p.i.fg, w: p.i.box[2] - p.i.box[0], h: p.i.box[3] - p.i.box[1], f: +fontOf(p.e).toFixed(1) };
    if (q) { out.aoi.cta_secondary = q.i.box; out.info.cta_secondary = { t: q.t, filled: q.i.filled, outline: q.i.outline, bg: q.i.bg }; }
    out.info.cta_n = grp.length; out.info.cta_order = order.map(x => x.t).join(' | '); out.info.cta_primary_first = order[0] === p;
  });

  // ---- email capture form in the hero -------------------------------------------------------------
  step('form', () => {
    const inp = [...document.querySelectorAll('input[type=email], input[type=text], input:not([type])')].filter(e => vis(e) && !inHdr(B(e)) && (B(e)[2] - B(e)[0]) > 140).sort((a, b) => B(a)[1] - B(b)[1])[0];
    if (!inp) return; const ib = B(inp);
    const near = btns.filter(x => (vov(x.i.box, ib) > 8 && Math.abs(x.i.box[0] - ib[2]) < 280) || (Math.abs(x.i.box[1] - ib[3]) < 44 && hov(x.i.box, ib) > 40));
    out.aoi.form = U([ib, ...near.map(x => x.i.box)]); out.info.form = { placeholder: (inp.getAttribute('placeholder') || '').slice(0, 60), button: near[0] ? near[0].t : null };
  });

  // ---- media inventory, hero visual, trust strip ------------------------------------------------------
  step('media', () => {
    media = [...document.querySelectorAll('img, video, canvas, iframe, svg, lottie-player, dotlottie-player')].filter(vis).map(e => ({ e, b: B(e), tag: e.tagName.toLowerCase() })).filter(x => A(x.b) >= 500);
    media = media.filter(x => !media.some(y => y !== x && y.e.contains(x.e) && y.tag === 'svg'));
    // large elements painted with a CSS background image (not full-page backgrounds)
    document.querySelectorAll('div, section, a, span, figure').forEach(e => {
      if (!quick(e)) return; const r = R(e); if (r.width * r.height < vw * vh * 0.03 || r.width * r.height > vw * vh * 0.75) return;
      const bi = S(e).backgroundImage; if (!bi || !bi.includes('url(') || !cv(e)) return;
      const b = B(e); if (A(b) >= vw * vh * 0.03 && !media.some(m => inside(m.b, b) > 0.8 && A(m.b) > A(b) * 0.5)) media.push({ e, b, tag: 'bgimg' });
    });
  });
  step('visual', () => {
    const hb = out.aoi.headline, hc = hb ? [(hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2] : null, minA = vw * vh * (vw < 600 ? 0.04 : 0.015);
    const big = media.filter(x => A(x.b) >= minA && !inHdr(x.b)).map(x => Object.assign({}, x, { bgLike: A(x.b) > vw * vh * 0.8 || (!!hc && hc[0] > x.b[0] && hc[0] < x.b[2] && hc[1] > x.b[1] && hc[1] < x.b[3]) }));
    out.info.bg_media = big.filter(x => x.bgLike).map(x => x.tag).slice(0, 3).join('+') || null;
    const fg = big.filter(x => !x.bgLike); if (!fg.length) return;
    let vb = U(fg.map(x => x.b)); if (hb && inside(hb, vb) > 0.5) vb = fg.slice().sort((a, b) => A(b.b) - A(a.b))[0].b;
    out.aoi.visual = vb; out.info.visual = { tags: [...new Set(fg.map(x => x.tag))].join('+'), n: fg.length, area: +(A(vb) / (vw * vh) * 100).toFixed(1), side: (vb[0] + vb[2]) / 2 > vw * 0.58 ? 'right' : ((vb[0] + vb[2]) / 2 < vw * 0.42 ? 'left' : 'center'), top: vb[1] };
  });
  step('trust', () => {
    const vb = out.aoi.visual;
    const logos = media.filter(x => (x.tag === 'img' || x.tag === 'svg') && !inHdr(x.b) && (x.b[3] - x.b[1]) >= 12 && (x.b[3] - x.b[1]) <= 90 && (x.b[2] - x.b[0]) >= 28 && (x.b[2] - x.b[0]) <= 300 && !(vb && inside(x.b, vb) > 0.7));
    if (logos.length >= 4) {
      const rows = [];
      for (const l of logos.slice().sort((a, b) => (a.b[1] + a.b[3]) - (b.b[1] + b.b[3]))) { const cy = (l.b[1] + l.b[3]) / 2; const r = rows.find(r => Math.abs(r.cy - cy) <= 22); if (r) { r.items.push(l); r.cy = (r.cy * (r.items.length - 1) + cy) / r.items.length; } else rows.push({ cy, items: [l] }); }
      let good = rows.filter(r => r.items.length >= 4 && (Math.max(...r.items.map(i => i.b[2])) - Math.min(...r.items.map(i => i.b[0]))) >= vw * 0.22);
      if (!good.length && vw < 600) { const g2 = rows.filter(r => r.items.length >= 2); if (g2.length >= 2 && g2.reduce((a, r) => a + r.items.length, 0) >= 4) good = g2; }
      if (good.length) {
        good.sort((a, b) => a.cy - b.cy); const grp = [good[0]]; for (let i = 1; i < good.length; i++) { if (good[i].cy - good[i - 1].cy <= 110) grp.push(good[i]); else break; }
        const items = grp.flatMap(r => r.items); let box = U(items.map(i => i.b));
        const lab = blocks.filter(x => x.t.length >= 8 && x.t.length <= 150 && x.b[3] <= box[1] + 8 && x.b[3] >= box[1] - 90 && /trust|used by|loved|leading|teams|compan|customer|brands|join|power|world|rated|choose|rely|built for|backed|organi[sz]ation|business/i.test(x.t)).sort((a, b) => b.b[3] - a.b[3])[0];
        if (lab) box = U([box, lab.b]);
        out.aoi.trust = box; out.info.trust = { n: items.length, label: lab ? lab.t.slice(0, 140) : null };
      }
    }
    const rt = blocks.filter(x => /\b[45][.,]\d\b/.test(x.t) && /G2|Capterra|star|rating|review|Trustpilot|Gartner/i.test(x.t) && x.t.length <= 120 && !inHdr(x.b)).sort((a, b) => a.t.length - b.t.length)[0];
    if (rt) { out.aoi.rating = rt.b; out.info.rating = rt.t.slice(0, 100); }
  });

  // ---- microcopy under the CTA (not the trust label) -------------------------------------------------
  step('micro', () => {
    const parts = [out.aoi.form, out.aoi.cta_primary, out.aoi.cta_secondary].filter(Boolean); if (!parts.length) return; const cb = U(parts);
    const c = blocks.filter(x => rel(x) && !x.isBtn && x.b[1] >= cb[3] - 2 && x.b[1] <= cb[3] + 58 && hov(x.b, [cb[0] - 80, 0, cb[2] + 80, 0]) > 0 && x.f <= 16.5 && x.t.length >= 6 && x.t.length <= 160
      && !(out.aoi.trust && inside(x.b, out.aoi.trust) > 0.5) && !(out.aoi.rating && inside(x.b, out.aoi.rating) > 0.5) && !(out.aoi.subhead && inside(x.b, out.aoi.subhead) > 0.5));
    if (!c.length) return; const top = Math.min(...c.map(x => x.b[1])); const line = c.filter(x => x.b[1] - top < 28 && !c.some(y => y !== x && y.e.contains(x.e)));
    out.aoi.micro = U(line.map(x => x.b)); out.info.micro = [...new Set(line.sort((a, b) => a.b[0] - b.b[0]).map(x => x.t))].join(' | ').slice(0, 180);
  });

  // ---- logo, nav links, nav CTA ---------------------------------------------------------------------
  step('logo', () => {
    if (!hdr) return;
    const c = [...document.querySelectorAll('a, img, svg')].filter(e => {
      if (!quick(e)) return false; const r = R(e); if (r.top < hdr[1] - 3 || r.bottom > hdr[3] + 3) return false;
      if (r.left > vw * (vw < 600 ? 0.6 : 0.3) || r.width < 20 || r.width > 290 || r.height < 12 || r.height > 92) return false;
      if (e.tagName === 'A') { const cls = (e.getAttribute('class') || '') + ' ' + (e.getAttribute('aria-label') || '') + ' ' + (e.getAttribute('href') || ''); return !!e.querySelector('img, svg') && (/logo|home|brand/i.test(cls) || e.getAttribute('href') === '/' || /^https?:\/\/[^/]+\/?$/.test(e.href || '')); }
      return cv(e);
    });
    const e = c.sort((a, b) => (R(a).left - R(b).left) || (R(b).width * R(b).height - R(a).width * R(a).height))[0];
    if (e) out.aoi.logo = B(e);
  });
  step('nav', () => {
    if (!hdr) return;
    const hb = btns.filter(x => inHdr(x.i.box) && (x.i.filled || x.i.outline));
    const hset = new Set(hb.map(x => x.e));
    let links = [...new Set([...document.querySelectorAll('a, button, [role=button], [role=menuitem], summary, [aria-haspopup]'), ...blocks.filter(x => inHdr(x.b)).map(x => x.e)])]
      .filter(e => vis(e) && inHdr(B(e)) && T(e).length >= 2 && T(e).length <= 30 && !hset.has(e) && ![...hset].some(c => c.contains(e) || e.contains(c)) && !(out.aoi.logo && inside(B(e), out.aoi.logo) > 0.5));
    links = links.filter(e => !links.some(o => o !== e && e.contains(o)));
    const seen = new Set(); links = links.filter(e => { const k = T(e) + '@' + Math.round(R(e).left / 6); if (seen.has(k)) return false; seen.add(k); return true; });
    if (links.length) { out.aoi.nav_links = U(links.map(B)); out.info.nav = { n: links.length, labels: links.sort((a, b) => (B(a)[1] - B(b)[1] > 14 ? 1 : (B(b)[1] - B(a)[1] > 14 ? -1 : B(a)[0] - B(b)[0]))).map(T).join(' · ').slice(0, 240) }; }
    const cs = hb.slice().sort((a, b) => (b.i.filled - a.i.filled) || (b.i.box[0] - a.i.box[0]));
    if (cs[0]) { out.aoi.nav_cta = cs[0].i.box; out.info.nav_cta = { t: cs[0].t, filled: cs[0].i.filled, bg: cs[0].i.bg, all: hb.slice().sort((a, b) => a.i.box[0] - b.i.box[0]).map(x => x.t).join(' · ') }; }
    out.aoi.header = hdr.slice();
  });

  // ---- theme and inventory output -------------------------------------------------------------------
  step('theme', () => {
    const hb = out.aoi.headline; const el = document.elementFromPoint(Math.min(vw - 5, (hb ? hb[0] : vw / 2) + 4), Math.max(2, (hb ? hb[1] : vh * 0.4) - 6)) || document.body;
    const bg = effBg(el); out.info.bg = bg ? '#' + bg.map(x => Math.round(x).toString(16).padStart(2, '0')).join('') : 'image';
    // theme from the headline text colour (light text = dark hero), which is robust to background images
    const tc = rgb(H ? S(firstTextEl(H)).color : S(document.body).color); const tl = tc.length >= 3 ? (0.2126 * tc[0] + 0.7152 * tc[1] + 0.0722 * tc[2]) / 255 : 0;
    out.info.theme = tl > 0.6 ? 'dark' : 'light';
  });
  step('inv', () => {
    out.inv.texts = blocks.slice().sort((a, b) => (a.b[1] - b.b[1]) || (a.b[0] - b.b[0])).slice(0, 170).map(x => ({ b: x.b, t: x.t.slice(0, 150), f: +x.f.toFixed(1), g: x.tag, k: x.isBtn ? 1 : 0 }));
    out.inv.btns = btns.slice().sort((a, b) => (a.i.box[1] - b.i.box[1]) || (a.i.box[0] - b.i.box[0])).slice(0, 50).map(x => ({ b: x.i.box, t: x.t, fl: x.i.filled ? 1 : 0, hd: inHdr(x.i.box) ? 1 : 0, ch: x.chip ? 1 : 0 }));
    out.inv.media = media.filter(x => A(x.b) >= vw * vh * 0.004).sort((a, b) => A(b.b) - A(a.b)).slice(0, 60).map(x => ({ b: x.b, g: x.tag }));
  });
  return JSON.stringify(out);
})()
