/*
 * Collect RealEye VAI, Reach, Speed and Hold per AOI, audience and time window.
 *
 * Run it in the JavaScript console (or an agent's page-JS tool) of a SIGNED-IN
 * app.realeye.io dashboard tab. It only makes read-only GET requests to the dashboard's own
 * internal endpoints with the user's existing session. Those endpoints are not documented and
 * may change; if a request fails, fall back to the exports or the AOI report UI.
 *
 * Edit CONFIG, paste, run. It returns immediately and fills window.__VAI in the background
 * (about one request per second). Poll window.__done / window.__total, then read the result.
 * Tool output is often truncated at ~1.5k characters, so read window.__VAI in chunks
 * (e.g. one audience per call).
 *
 * Result (ready for report.json "segments"):
 *   window.__VAI[design] = [{label, kind, n, values:[...60 numbers...]}]
 *   values order: for window in [3,5,10] -> for AOI in AOI_ORDER -> [vai, reach, speed, hold]
 */
const CONFIG = {
  items: { A: '<ITEM_ID_A>', B: '<ITEM_ID_B>' },            // dashboard item (stimulus) ids
  aoiOrder: ['Tagline', 'Pack', 'Face', 'Logo', 'Banner'],  // dashboard AOI names (without quotes), in report order
  windowsSeconds: [3, 5, 10],                               // cumulative windows starting at 0.5 s
  minQualityGrade: 3,                                       // 1 Very low, 2 Low, 3 Average ... 6 Perfect. 3 = Average or better
  ages: [[18, 24], [25, 34], [35, 99]],                     // age bands (viewers with no recorded age are excluded)
};

window.__VAI = {}; window.__done = 0; window.__err = [];
const ALL = { m: true, f: true, o: true, n: true }, MEN = { m: true, f: false, o: false, n: false }, WOMEN = { m: false, f: true, o: false, n: false };
const segs = [['All', 'overall', ALL, [0, 99]], ['Men', 'gender', MEN, [0, 99]], ['Women', 'gender', WOMEN, [0, 99]]];
for (const [lo, hi] of CONFIG.ages) { const l = hi >= 99 ? `${lo}+` : `${lo}–${hi}`; segs.push([l, 'age', ALL, [lo, hi]]); }
for (const [lo, hi] of CONFIG.ages) { const l = hi >= 99 ? `${lo}+` : `${lo}–${hi}`; segs.push(['Men ' + l, 'gender_age', MEN, [lo, hi]]); }
for (const [lo, hi] of CONFIG.ages) { const l = hi >= 99 ? `${lo}+` : `${lo}–${hi}`; segs.push(['Women ' + l, 'gender_age', WOMEN, [lo, hi]]); }

const tail = '&participantTypeRealEye=true&participantTypeOwn=true&deviceDesktop=true&deviceSmartphone=true&deviceSmartphoneVertical=true&deviceSmartphoneHorizontal=true&deviceTablet=true&setupLocal=true&setupMouse=true&setupOpengaze=true&setupReWebcamV3=true' +
  `&participantQualityGradeItemMin=${CONFIG.minQualityGrade}&participantQualityGradeItemMax=6&filterAnswers=%5B%5D&includeAll=0`;
const aoiQuery = (a, toMs) => {
  const p = a.itemParts[0]; let q;
  if (a.type === 'rectangle') {
    const t = p.areaPoints.topLeft, b = p.areaPoints.bottomRight;
    q = `&aoi[itemParts][0][areaPoints][topLeft][xPx]=${t.xPx}&aoi[itemParts][0][areaPoints][topLeft][yPx]=${t.yPx}&aoi[itemParts][0][areaPoints][bottomRight][xPx]=${b.xPx}&aoi[itemParts][0][areaPoints][bottomRight][yPx]=${b.yPx}`;
  } else {
    q = '&aoi[itemParts][0][areaPoints][points]=' + JSON.stringify(p.areaPoints.points).replace(/"/g, '%22');
  }
  return q + `&aoi[itemParts][0][type]=${a.type}&aoi[itemParts][0][timeRange][fromMs]=500&aoi[itemParts][0][timeRange][toMs]=${toMs}&itemAoiId=${a.id}`;
};

(async () => {
  const jobs = [];
  for (const [design, id] of Object.entries(CONFIG.items)) {
    const aois = (await (await fetch(`/api/item/${id}/aoi/get/?tryToFix=1`, { credentials: 'include' })).json()).data;
    const byName = Object.fromEntries(aois.map(a => [a.name.replace(/"/g, ''), a]));
    window.__VAI[design] = segs.map(([label, kind]) => ({ label, kind, n: 0, values: new Array(CONFIG.windowsSeconds.length * CONFIG.aoiOrder.length * 4).fill(0) }));
    segs.forEach(([label, kind, g, age], si) => CONFIG.windowsSeconds.forEach((w, wi) => CONFIG.aoiOrder.forEach((nm, ai) => jobs.push({ design, id, si, g, age, w, wi, ai, a: byName[nm] }))));
  }
  window.__total = jobs.length;
  let i = 0;
  const worker = async () => {
    while (i < jobs.length) {
      const j = jobs[i++];
      try {
        const u = `/api/aoi/stats/${j.id}?itemId=${j.id}&genderMale=${j.g.m}&genderFemale=${j.g.f}&genderOther=${j.g.o}&genderNotSpecified=${j.g.n}&ageMin=${j.age[0]}&ageMax=${j.age[1]}` + tail + aoiQuery(j.a, j.w * 1000);
        const r = await (await fetch(u, { credentials: 'include' })).json();
        const m = r.reMetrics, s = window.__VAI[j.design][j.si];
        s.n = r.testsCount;
        const o = j.wi * CONFIG.aoiOrder.length * 4 + j.ai * 4;
        [m.vai, m.reach, m.speed, m.hold].forEach((x, k) => { s.values[o + k] = +x.toFixed(1); });
      } catch (e) { window.__err.push(String(e).slice(0, 80)); }
      window.__done++;
    }
  };
  Promise.all(Array.from({ length: 12 }, worker));
})();
'started';
