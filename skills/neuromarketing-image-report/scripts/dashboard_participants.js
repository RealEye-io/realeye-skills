/*
 * Collect the participant profile of each design from the RealEye dashboard: how many viewers were collected and analysed,
 * data quality, gender, age, device, and when the data was collected.
 *
 * Run it in the JavaScript console (or an agent's page-JS tool) of a SIGNED-IN app.realeye.io tab. Read-only requests to the
 * dashboard's own internal endpoints with the user's session (undocumented, may change). It returns immediately and fills
 * window.__PARTICIPANTS in the background (about a minute); poll window.__partDone, then read the result in chunks
 * (the tool may truncate long output at about 1.5k characters).
 *
 * Result (matches the report JSON "participants"):
 *   window.__PARTICIPANTS[design] = {collected, analysed, collected_from, collected_to,
 *       quality:{"Very low","Low","Average","Good","Very good","Perfect"}, gender:{Men,Women,Other,"Not specified"},
 *       age:{bands:{...}, with_age, median, mean, min, max}, device:{Desktop,Tablet,Smartphone}, setup:{...}, participant_type:{...}, browser_median:{w,h}}
 *
 * Privacy: participants' display names look like "Name, Male, 39". This script reads only gender and age from them and never
 * outputs or stores the name. Do not report names or author names.
 */
const CONFIG = {
  items: { A: '<ITEM_ID_A>', B: '<ITEM_ID_B>' },
  minQualityGrade: 3,   // analysed = Average (3) or better
};
window.__partDone = false; window.__PARTICIPANTS = {};
(async () => {
  const def = { genderMale: true, genderFemale: true, genderOther: true, genderNotSpecified: true, ageMin: 0, ageMax: 99, participantTypeRealEye: true, participantTypeOwn: true,
    deviceDesktop: true, deviceSmartphone: true, deviceSmartphoneVertical: true, deviceSmartphoneHorizontal: true, deviceTablet: true,
    setupLocal: true, setupMouse: true, setupOpengaze: true, setupReWebcamV3: true, participantQualityGradeItemMin: CONFIG.minQualityGrade, participantQualityGradeItemMax: 6 };
  const aoiQ = a => {
    const p = a.itemParts[0]; let q;
    if (a.type === 'rectangle') { const t = p.areaPoints.topLeft, b = p.areaPoints.bottomRight; q = `&aoi[itemParts][0][areaPoints][topLeft][xPx]=${t.xPx}&aoi[itemParts][0][areaPoints][topLeft][yPx]=${t.yPx}&aoi[itemParts][0][areaPoints][bottomRight][xPx]=${b.xPx}&aoi[itemParts][0][areaPoints][bottomRight][yPx]=${b.yPx}`; }
    else q = '&aoi[itemParts][0][areaPoints][points]=' + JSON.stringify(p.areaPoints.points).replace(/"/g, '%22');
    return q + `&aoi[itemParts][0][type]=${a.type}&aoi[itemParts][0][timeRange][fromMs]=500&aoi[itemParts][0][timeRange][toMs]=10000&itemAoiId=${a.id}`;
  };
  const med = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const iso = t => new Date(t * 1000).toISOString().slice(0, 10);
  for (const [k, id] of Object.entries(CONFIG.items)) {
    const aoi = (await (await fetch(`/api/item/${id}/aoi/get/?tryToFix=1`, { credentials: 'include' })).json()).data[0];
    // number of tests for a filter combination: the AOI statistics endpoint reports testsCount
    const cnt = async over => { const f = { ...def, ...over }; const qs = Object.entries(f).map(([a, b]) => `${a}=${b}`).join('&');
      return (await (await fetch(`/api/aoi/stats/${id}?itemId=${id}&${qs}&filterAnswers=%5B%5D&includeAll=0` + aoiQ(aoi), { credentials: 'include' })).json()).testsCount; };
    const only = (group, keep) => Object.fromEntries(group.map(x => [x, x === keep]));
    const out = { quality: {}, gender: {}, device: {}, setup: {}, participant_type: {} }, tasks = [], add = (f) => tasks.push(f);
    add(async () => out.analysed = await cnt({})); add(async () => out.collected = await cnt({ participantQualityGradeItemMin: 1 }));
    [[1, 'Very low'], [2, 'Low'], [3, 'Average'], [4, 'Good'], [5, 'Very good'], [6, 'Perfect']].forEach(([g, l]) => add(async () => out.quality[l] = await cnt({ participantQualityGradeItemMin: g, participantQualityGradeItemMax: g })));
    [['genderMale', 'Men'], ['genderFemale', 'Women'], ['genderOther', 'Other'], ['genderNotSpecified', 'Not specified']].forEach(([f, l]) => add(async () => out.gender[l] = await cnt(only(['genderMale', 'genderFemale', 'genderOther', 'genderNotSpecified'], f))));
    const devs = ['deviceDesktop', 'deviceSmartphoneVertical', 'deviceSmartphoneHorizontal', 'deviceTablet'], dv = {};
    devs.forEach(d => add(async () => dv[d] = await cnt({ ...only(devs, d), deviceSmartphone: d.includes('Smartphone') })));
    ['setupLocal', 'setupMouse', 'setupOpengaze', 'setupReWebcamV3'].forEach((d, _, arr) => add(async () => out.setup[d] = await cnt(only(arr, d))));
    add(async () => out.participant_type['RealEye panel'] = await cnt({ participantTypeOwn: false })); add(async () => out.participant_type['Own participants'] = await cnt({ participantTypeRealEye: false }));
    await Promise.all(tasks.map(f => f()));
    out.device = { Desktop: dv.deviceDesktop, Tablet: dv.deviceTablet, Smartphone: dv.deviceSmartphoneVertical + dv.deviceSmartphoneHorizontal };
    // gender, age, dates, browser size from the fixation data (name is never read)
    const base = Object.entries({ ...def, participantId: 'all', viewType: 'fixations', heatmapType: 'heatmap', itemTimeFrom: 500, itemTimeTo: 10000 }).map(([a, b]) => `${a}=${b}`).join('&');
    const j = await (await fetch(`/api/item-test/data?itemId=${id}&${base}&filterAnswers=[]&includeAll=0`, { credentials: 'include' })).json();
    const ages = [], ts = [], w = [], h = [];
    for (const p of j) {
      for (const s of (p.participant.displayName || '').split(',').slice(1).map(s => s.trim())) if (/^\d+$/.test(s)) ages.push(+s);
      ts.push(p.participant.createdAtTimestamp); if (p.test) { w.push(p.test.browserWidthPx); h.push(p.test.browserHeightPx); }
    }
    const bands = { 'Under 18': 0, '18–24': 0, '25–34': 0, '35–44': 0, '45–54': 0, '55+': 0 };
    for (const a of ages) bands[a < 18 ? 'Under 18' : a <= 24 ? '18–24' : a <= 34 ? '25–34' : a <= 44 ? '35–44' : a <= 54 ? '45–54' : '55+']++;
    out.age = { bands, with_age: ages.length, median: med(ages), mean: +(ages.reduce((x, y) => x + y, 0) / (ages.length || 1)).toFixed(1), min: Math.min(...ages), max: Math.max(...ages) };
    out.collected_from = iso(Math.min(...ts)); out.collected_to = iso(Math.max(...ts)); out.browser_median = { w: med(w), h: med(h) };
    window.__PARTICIPANTS[k] = out;
  }
  window.__partDone = true;
})();
'started';
