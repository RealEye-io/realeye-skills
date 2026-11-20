/*
 * Read the AOI shapes (and, on the AOI VAI report page, the legend colours) from the RealEye dashboard.
 *
 * Run it in the JavaScript console (or an agent's page-JS tool) of a SIGNED-IN app.realeye.io tab. Read-only.
 * For the colours, run it on /dashboard/study/<STUDY_ID>/item/<ITEM_ID>/aoi-vai-report; the shapes work on any dashboard page.
 *
 * Result:
 *   window.__SHAPES[design] = ["<AOI name>:x,y x,y x,y ...", ...]   points in % of the image (a rectangle is four points)
 *   window.__LEGEND         = [["<AOI name>", "rgb(r, g, b)"], ...]  the dashboard's AOI colours (VAI report page only)
 * Put each polygon in the report JSON as aois[].shape ([[x, y], ...]) and the colour as aois[].color (hex).
 * Read the result in chunks if the tool truncates long output (about 1.5k characters).
 */
const CONFIG = {
  items: { A: '<ITEM_ID_A>', B: '<ITEM_ID_B>' },
  imageSize: { w: 1024, h: 1536 },   // pixel size of the stimulus (the CDN image tab title shows it, e.g. "(1024×1536)")
};
window.__SHAPES = {};
(async () => {
  for (const [k, id] of Object.entries(CONFIG.items)) {
    const j = await (await fetch(`/api/item/${id}/aoi/get/?tryToFix=1`, { credentials: 'include' })).json();
    window.__SHAPES[k] = j.data.map(a => {
      const p = a.itemParts[0];
      let pts;
      if (a.type === 'rectangle') {           // rectangles come in pixels
        const t = p.areaPoints.topLeft, b = p.areaPoints.bottomRight, W = CONFIG.imageSize.w, H = CONFIG.imageSize.h;
        pts = [[t.xPx / W, t.yPx / H], [b.xPx / W, t.yPx / H], [b.xPx / W, b.yPx / H], [t.xPx / W, b.yPx / H]];
      } else {                                // polygons come as fractions
        pts = p.areaPoints.points.map(q => [q.x, q.y]);
      }
      return a.name.replace(/"/g, '') + ':' + pts.map(q => q.map(v => (v * 100).toFixed(1)).join(',')).join(' ');
    });
  }
  window.__LEGEND = [...document.querySelectorAll('.re2-vai__swatch')].map(s => [(s.parentElement.textContent || '').trim().replace(/"/g, ''), getComputedStyle(s).backgroundColor]);
  window.__shapesReady = true;
})();
'started';
