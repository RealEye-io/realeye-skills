/*
 * Draw heatmaps for every audience and time window as one labelled "sheet" per window.
 *
 * Run it in a SIGNED-IN app.realeye.io dashboard tab (same caveats as dashboard_vai_collect.js).
 * It downloads the filtered fixation data of each item (read-only), builds a 6 x 2 sheet of
 * heatmaps (All, Men, Women, three age bands, then gender x age) on a canvas, and shows one
 * sheet full-screen so it can be captured. Heatmaps are drawn from the same Average-or-better
 * fixation data as the dashboard, from 0.5 s to the end of the window, each scaled to its own
 * maximum, so compare shapes, not intensities.
 *
 * Usage after running:   window.__show('A', 10)   // design key, window in seconds
 * Then move the mouse pointer off the sheet (e.g. to the far bottom-right corner) and capture the
 * region of the sheet at full resolution. Repeat for each design x window (3, 5, 10).
 *
 * Participant names appear in the dashboard data (displayName). This script only reads gender and
 * age from it and never outputs or stores the name.
 */
const CONFIG = {
  items: { A: '<ITEM_ID_A>', B: '<ITEM_ID_B>' },
  imageUrls: {   // the stimulus image the dashboard shows for each item (copy it from the page's network requests)
    A: '<URL_OF_STIMULUS_IMAGE_A>', B: '<URL_OF_STIMULUS_IMAGE_B>' },
  minQualityGrade: 3,
  ages: [[18, 24], [25, 34], [35, 99]],
  cell: { w: 300, h: 450 },           // set h/w to the stimulus aspect ratio
  sigma: 14,                          // blur radius in canvas pixels
};
const base = '&genderMale=true&genderFemale=true&genderOther=true&genderNotSpecified=true&ageMin=0&ageMax=99&participantTypeRealEye=true&participantTypeOwn=true&deviceDesktop=true&deviceSmartphone=true&deviceSmartphoneVertical=true&deviceSmartphoneHorizontal=true&deviceTablet=true&setupLocal=true&setupMouse=true&setupOpengaze=true&setupReWebcamV3=true' +
  `&participantQualityGradeItemMin=${CONFIG.minQualityGrade}&participantQualityGradeItemMax=6&participantId=all&viewType=fixations&heatmapType=heatmap&fineTuneAutoAdjustment=1&itemTimeFrom=500&itemTimeTo=10000&movingMedianRangeMs=200&minFixationDurationMs=80&maxFixationDurationMs=400&gazeVelocityThreshold=30&maxSaccadeDurationMs=150&filterAnswers=[]&includeAll=0&include-fixations-normalized=1`;

window.__D = {}; window.__imgs = {};
const segDefs = [['All', () => true], ['Men', p => p.g === 'Male'], ['Women', p => p.g === 'Female']];
const label = ([lo, hi]) => hi >= 99 ? `${lo}+` : `${lo}–${hi}`;
for (const a of CONFIG.ages) segDefs.push([label(a), p => p.age != null && p.age >= a[0] && p.age <= a[1]]);
for (const a of CONFIG.ages) segDefs.push(['Men ' + label(a), p => p.g === 'Male' && p.age != null && p.age >= a[0] && p.age <= a[1]]);
for (const a of CONFIG.ages) segDefs.push(['Women ' + label(a), p => p.g === 'Female' && p.age != null && p.age >= a[0] && p.age <= a[1]]);
const jet = v => [Math.min(1, Math.max(0, 1.5 - Math.abs(4 * v - 3))) * 255, Math.min(1, Math.max(0, 1.5 - Math.abs(4 * v - 2))) * 255, Math.min(1, Math.max(0, 1.5 - Math.abs(4 * v - 1))) * 255];

window.__sheet = (k, win) => {
  const { w: CW, h: CH } = CONFIG.cell, LB = 28, cols = 6, rows = 2;
  const cv = document.createElement('canvas'); cv.width = cols * CW; cv.height = rows * (CH + LB);
  const c = cv.getContext('2d'); c.fillStyle = '#fff'; c.fillRect(0, 0, cv.width, cv.height);
  segDefs.forEach(([name, f], i) => {
    const x0 = (i % cols) * CW, y0 = Math.floor(i / cols) * (CH + LB), P = window.__D[k].filter(f);
    c.drawImage(window.__imgs[k], x0, y0 + LB, CW, CH);
    const g = new Float32Array(CW * CH), sg = CONFIG.sigma, R = Math.ceil(sg * 3);
    for (const p of P) for (const [x, y, s, d] of p.fx) {
      if (s < 500 || s >= win * 1000) continue;
      const cx = x / 100 * CW, cy = y / 100 * CH;
      for (let yy = Math.max(0, Math.floor(cy - R)); yy < Math.min(CH, cy + R); yy++)
        for (let xx = Math.max(0, Math.floor(cx - R)); xx < Math.min(CW, cx + R); xx++) {
          const dx = xx - cx, dy = yy - cy; g[yy * CW + xx] += d * Math.exp(-(dx * dx + dy * dy) / (2 * sg * sg));
        }
    }
    let mx = 0; for (const v of g) if (v > mx) mx = v;
    const im = c.createImageData(CW, CH);
    for (let q = 0; q < g.length; q++) {
      const v = mx ? g[q] / mx : 0, [r, gg, b] = jet(v);
      im.data[q * 4] = r; im.data[q * 4 + 1] = gg; im.data[q * 4 + 2] = b; im.data[q * 4 + 3] = v < 0.08 ? 0 : Math.min(215, 35 + v * 235);
    }
    const tmp = document.createElement('canvas'); tmp.width = CW; tmp.height = CH; tmp.getContext('2d').putImageData(im, 0, 0);
    c.drawImage(tmp, x0, y0 + LB);
    c.fillStyle = '#fff'; c.fillRect(x0, y0, CW, LB); c.fillStyle = '#222'; c.font = 'bold 15px sans-serif';
    c.fillText(`${name}  ·  N=${P.length}`, x0 + 6, y0 + 19);          // N = viewers in the audience
    c.strokeStyle = '#fff'; c.lineWidth = 2; c.strokeRect(x0, y0, CW, CH + LB);
  });
  return cv;
};
window.__show = (k, win) => {
  let o = document.getElementById('__ov');
  if (!o) { o = document.createElement('div'); o.id = '__ov'; o.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;background:#fff;z-index:999999;overflow:hidden'; document.body.appendChild(o); }
  o.innerHTML = ''; const cv = window.__sheet(k, win); cv.style.cssText = 'display:block;width:1800px;height:' + (cv.height / cv.width * 1800) + 'px'; o.appendChild(cv);
};

(async () => {
  for (const [k, id] of Object.entries(CONFIG.items)) {
    const j = await (await fetch(`/api/item-test/data?itemId=${id}` + base, { credentials: 'include' })).json();
    // displayName looks like "Name, Male, 39" (gender and age may be missing): parse gender and age only.
    window.__D[k] = j.map(p => {
      let g = null, age = null;
      for (const s of (p.participant.displayName || '').split(',').slice(1).map(s => s.trim())) {
        if (/^(Male|Female|Other)$/i.test(s)) g = s; else if (/^\d+$/.test(s)) age = +s;
      }
      return { g, age, fx: (p.fixationsNormalized || []).map(f => [f.point.x, f.point.y, f.startsAtMs, f.durationMs]) };
    });
    await new Promise(res => { const im = new Image(); im.onload = () => { window.__imgs[k] = im; res(); }; im.onerror = res; im.src = CONFIG.imageUrls[k]; });
  }
  window.__ready = true;
})();
'loading';
