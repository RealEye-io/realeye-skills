# HTML report guide

`scripts/build_report.py` turns one JSON file into a single self-contained HTML report (Python 3.8+ standard library; Pillow is optional and only shrinks large screenshots). It draws the layout (styled after the RealEye dashboard's AOI VAI report), print styling, inline SVG charts, embedded images, the viewing order, the audience tables and the head-to-head comparison. It never invents data and it **renders only VAI and its components (Reach, Speed, Hold)**: raw metrics such as TTFF are deliberately not supported.

```
python scripts/build_report.py report.json -o report.html
```

Image paths in the JSON are relative to the JSON file.

## What the report contains (generated)

Main sections, written for brand managers (plain language, no technical detail):

1. **Header** with one plain line: the test ran on the **RealEye platform with webcam eye tracking**, then the **tested designs and the elements analysed**: each image with its AOIs outlined (switchable), a legend saying what each AOI covers, the viewer count and links to the dashboard heatmap, AOI report and AOI VAI report
2. **Overall findings and conclusions** (first): verdict, KPI tiles, key findings, conclusions, what to do next
3. **What the scores mean (VAI)**: Reach, Speed, Hold in one line each, how to use VAI, component patterns, worked example drawn from the data
4. **Viewing order**: the order by VAI Speed overall (numbered badges on the AOI corners and a ladder of steps with Speed bars for each window), a stability statement, the elements reached by half of the viewers or more per window, and a table for **every audience and window** listing the elements 1st to 5th with differences from the overall order outlined
5. **One section per design**: image with its elements outlined and the dashboard heatmap, scores for 3, 5 and 10 s, Reach · Speed · Hold chart, build-up lines, **gender, age and gender × age tables** (VAI with Reach · Speed · Hold per element and window), **heatmap sheets for every audience and window**
6. **Head-to-head comparison** (2+ designs) and **gender and age insights** (women-vs-men, 18–24 vs 25–34 and gender × age gap tables)
7. **How to test it next** (retest plan)

**Technical appendix** (last, for analysts): about this study (platform, tracking, sample, participant quality filter, windows, audiences, tracker precision), technical notes on VAI, evidence and limits, definitions, sources, and the embedded **dashboard AOI VAI report** (unfiltered) per design.

## Standing rules (see SKILL.md)

Brand-manager main sections, technical detail in the appendix · VAI only · RealEye webcam line · conclusions first, then depth · plain VAI explainer · clear viewing order · quality Average or better (appendix) · every audience × window with heatmaps · dashboard AOI VAI report embedded and labelled unfiltered · clean complete images with no pointer.

## Start from the template and the example

- `assets/template/report.template.json`: the skeleton to fill. Every `<…>` is a placeholder with guidance; the `_help` list at the top repeats the rules. It builds as-is with the example images (the numbers are zeros), so you can check the structure.
- `assets/example/`: a finished two-design report (`report.json`, its images, and the built `example-report.html`). Open the HTML to see the target look. The ids in it are placeholders (`STUDY_ID`, `ITEM_ID_A`), so its links are illustrative.
- Reports must look like the example: same sections in the same order, same plain tone, same tables, charts and heatmap sheets. Do not restyle; the script owns the look.

## Study facts and participants

`study_info` and `participants` (per design id) drive three things: the tiles *Study created*, *Data collected* (the earliest and latest `collected_from` / `collected_to`) and *RealEye version*; the *Who took part* card (charts of gender, age bands plus "No age given", and device, with counts and percentages); and the appendix block *Study and platform* with the data-quality distribution of all collected viewers (Very low and Low are shown as removed) and the set-up details. The same facts go into the data pack (tables `study` and `participants`) and the AI prompt. Collect them with the browser playbook (section 2b) and `scripts/dashboard_participants.js`. Never include participant or author names.

## Tables and charts

Every comparison has a chart and a table. Charts: VAI component bars, build-up lines, head-to-head bars, the viewing-order ladder, audience bar charts with window tabs (gender, age, gender × age), diverging gap charts (women minus men), participant profile bars and the data-quality bars. Tables: scores, audience tables with Reach · Speed · Hold, the viewing-order table per audience, gap tables, participant quality, the AOI VAI report copy. Printing shows all window tabs.

## AI-agent prompt (last section)

The report ends with a prompt the reader can paste into an AI assistant so it ingests the whole report and can answer any follow-up question, run more comparisons and suggest further insights. The script generates it from the JSON: study and method, VAI definitions and reading rules, designs and AOIs (what each covers and where), the full numbers table (VAI/Reach/Speed/Hold per element, design, audience and window), the dashboard AOI VAI report, findings, actions, limits, the dashboard links, answering rules and ideas to explore. The prompt includes the **data pack**, which is also offered on its own in a collapsed block with copy and download buttons: markdown with tidy CSV tables (`study`, `designs`, `elements` with bounding boxes in % of the image, `audiences` with sizes, `vai_by_audience` as the main table with `speed_rank` = viewing-order position, `dashboard_vai_report_unfiltered`, `dashboard_links`). Optional `agent_context` (string) adds the campaign goal, the decision to make or other context. Everything the prompt needs must therefore be in the report JSON.

## Tooltips for metric names

Every use of **VAI, VAI Reach, VAI Speed, VAI Hold, Reach, Speed, Hold and AOI** in the report text (including table headers, legends, tiles and the navigation) gets a dotted underline and a tooltip with a plain-language definition on hover or click. This is automatic. Write the names capitalised exactly like this (lower-case "reach", "hold" or "speed" in ordinary sentences is not treated as a metric). Add your own terms with the top-level `glossary` object, for example `"glossary": {"Banner": "The brand name strip at the bottom of the image."}`; they get tooltips everywhere they appear.

## Design mentions and thumbnails

Every mention of a design shows a thumbnail of it on hover, focus or click (a small popover with the clean image and the design name). The script does this for badges, tags and legends. In the free text of the JSON write designs as `Design A` or the token `{A}`; patterns like `(A)`, `(A and B)`, `in A`, `than B`, `A's`, `A 14.3` and `A: …` are linked automatically. A sentence-initial article "A" is left alone.

## Links to the RealEye dashboard

Set `dashboard.study_id` and every variant's `item_id` and the script links everything to the dashboard: the design headers (heatmap, AOI report, AOI VAI report), the scores table, each audience column header (AOI report with that audience's gender, age and quality filters applied), every heatmap sheet (one link per audience and window to the dashboard heatmap), the viewing order, the comparison, the gender and age section and the appendix copy of the AOI VAI report. Links open the signed-in dashboard in a new tab. The AOI VAI report cannot be filtered, so its link is unfiltered. If ids are missing the report still builds, without links, but a report for a real study should always have them.

## Getting the data from the RealEye dashboard

The full step-by-step browser playbook is in [browser-data-collection.md](browser-data-collection.md). The notes below are the reference for the URLs and the data format.

Use the user's signed-in browser (read-only). Never print participant names; never edit AOIs or share anything.

**Filters live in the URL hash.** Load a fresh page between changes (hash-only navigation does not reload the data). Useful keys: `participantQualityGradeItemMin=3&participantQualityGradeItemMax=6` (Average or better; 1 Very low, 2 Low, 3 Average, up to 6 Perfect), `genderMale`, `genderFemale`, `genderOther`, `genderNotSpecified` (true/false), `ageMin`, `ageMax`. The AOI report page is `/dashboard/item/<ITEM_ID>/aoi`, the heatmap page `/dashboard/item/<ITEM_ID>/`, and the AOI VAI report `/dashboard/study/<STUDY_ID>/item/<ITEM_ID>/aoi-vai-report`.

**The AOI VAI report cannot be filtered** by quality, gender or age: it always covers all participants with data. Embed it per design as an unfiltered copy (`dashboard_vai`), and take the primary numbers from the filtered statistics below.

**Filtered VAI per audience and window** (the primary data). The AOI report loads each AOI's statistics from `GET /api/aoi/stats/<ITEM_ID>?<filters>&aoi[itemParts][0]...&aoi[itemParts][0][timeRange][fromMs]=500&aoi[itemParts][0][timeRange][toMs]=<WINDOW_MS>`; the JSON contains `reMetrics: {vai, reach, speed, hold}` and `testsCount` (the viewers analysed). AOI shapes come from `GET /api/item/<ITEM_ID>/aoi/get/`. `scripts/dashboard_vai_collect.js` runs all audience × window combinations from the page (about one request per second) and fills `window.__VAI` in the `segments` format below. Page-JS output is often truncated at about 1.5k characters, so read it in chunks. Before trusting a row, check that VAI equals the mean of Reach, Speed and Hold (within 0.2).

**Heatmaps per audience and window.** The dashboard draws heatmaps in the browser from `GET /api/item-test/data?...&include-fixations-normalized=1` (normalised fixation points per viewer, with the viewer's gender and age in the display name). `scripts/dashboard_heatmap_sheets.js` loads it with the quality filter and draws one labelled sheet per design × window (12 audiences each). Show a sheet with `window.__show('A', 10)`, move the pointer off the page, then capture the sheet region at full resolution (the zoom action at default scale; low scales give low-resolution images). Also capture the dashboard's own heatmap for all viewers.

**Clean image and AOI shapes.** The clean stimulus is the image the dashboard loads (`.../experiments/experiment_<STUDY_ID>/project_lg_<ITEM_ID>.jpg`, public CDN; open it in a tab, move the pointer off the page and capture the image at full resolution). The AOI shapes come from `GET /api/item/<ITEM_ID>/aoi/get/`: rectangles in pixels, polygons as fractions; divide by the image size (1024 × 1536 in the example) to get percentages. Use the dashboard's AOI colours (shown in its legend).

**Heatmap colours.** `scripts/dashboard_heatmap_sheets.js` uses a dashboard-like colour scale (deep blue to pale yellow to orange to dark red, drawn over the whole image). Capture the main heatmap per design the same way (one large cell) so all heatmaps match.

**Check the render.** Render the HTML to an image (e.g. headless Edge or Chrome with `--screenshot`) and review it before delivery.

**Whole image.** Tall creatives have content below the visible viewport; check the bottom of every capture. Name AOIs by what they cover (a brand banner is not the label printed on the pack).

## JSON schema

```json
{
  "title": "…", "subtitle": "…", "date": "…", "prepared_for": "optional",
  "method": {
    "platform": "RealEye platform",
    "tracking": "Webcam eye tracking: …",
    "banner": "The test was run on the RealEye platform with webcam eye tracking. …",
    "study": "…", "participants": "Design A: 229 viewers (12 of 241 removed for low data quality) …",
    "quality_filter": "Only viewers with data quality Average or better are analysed.",
    "windows": "First 3 s (0.5–3 s), first 5 s, first 10 s, cumulative.",
    "segments": "All viewers; men and women; ages …; gender × age. Audiences under 30 viewers are marked †.",
    "task": "…", "source": "…", "note": "…"},
  "dashboard": {"base": "https://app.realeye.io", "study_id": "<STUDY_ID>", "min_quality": 3},
  "agent_context": "<optional: campaign goal, decision to make, anything the AI assistant should know>",
  "glossary": {"optional term": "optional definition shown as a tooltip"},
  "study_info": {"created": "25 Oct 2023", "status": "Running, 8,711 of 10,000 participants so far", "type": "Images and Videos",
                 "realeye_version": "v26.11.20.1", "version_note": "dashboard version at analysis, 20 Nov 2026",
                 "tracker": "RealEye webcam eye tracking (RealEye webcam tracker v3)", "analysed_on": "20 Nov 2026",
                 "settings": "Both designs: shown for 10 s, finished on keypress, instructions off", "panel": "Own participants, asked for gender and age"},
  "participants": {"A": {"collected": 241, "analysed": 229, "collected_from": "2026-03-24", "collected_to": "2026-11-12",
                         "quality": {"Very low": 3, "Low": 9, "Average": 16, "Good": 50, "Very good": 25, "Perfect": 138},
                         "gender": {"Men": 59, "Women": 88, "Other": 8, "Not specified": 74},
                         "age": {"bands": {"Under 18": 11, "18–24": 82, "25–34": 28, "35–44": 2, "45–54": 3, "55+": 2}, "with_age": 128, "median": 23, "mean": 24.6},
                         "device": {"Desktop": 201, "Tablet": 28},
                         "tracker_text": "…", "participant_type_text": "…", "screen_text": "1512 × 900 px", "age_text": "…"}},
  "participants_note": "optional: note under the participant charts",
  "aoi_order": ["Tagline", "Pack (product)", "Face", "Logo", "Brand name (banner)"],
  "overall": {
    "verdict_label": "…", "verdict_text": "…", "summary": "…",
    "kpis": [{"label": "…", "value": "…", "note": "…"}],
    "findings": [{"tag": "strength|risk|weak-evidence", "title": "…", "text": "…"}],
    "conclusions": ["…"]},
  "variants": [{
    "id": "A", "item_id": "<ITEM_ID_A>", "name": "…", "description": "…",
    "stimulus": {"src": "stimulus-A.jpg"},
    "heatmap":  {"src": "heatmap-A.jpg", "caption": "All viewers, first 10 seconds."},
    "heatmap_sheets": {"3": "heat-sheet-A-3.jpg", "5": "heat-sheet-A-5.jpg", "10": "heat-sheet-A-10.jpg"},
    "heatmap_note": "…",
    "aois": [{"name": "Tagline", "role": "The claim “Wake up the red in your hair.”", "color": "#96d732", "shape": [[3.5, 3.4], [44.0, 3.8], [44.4, 11.6], [35.4, 24.4], [23.5, 31.1], [4.4, 31.2]]}],
    "segments": [
      {"label": "All", "kind": "overall", "n": 229, "values": [ /* 60 numbers */ ]},
      {"label": "Men", "kind": "gender", "n": 59, "values": [ … ]},
      {"label": "18–24", "kind": "age", "n": 82, "values": [ … ]},
      {"label": "Men 18–24", "kind": "gender_age", "n": 24, "values": [ … ]}],
    "findings": ["…"],
    "dashboard_vai": {
      "scope": "all 240 participants with data, not quality-filtered", "participants": 240,
      "windows": ["0.5–3 s", "0.5–5 s", "0.5–10 s"],
      "summary":   {"Tagline": {"vai": 57.1, "reach": 81.4, "speed": 68.2, "hold": 21.8}},
      "by_window": {"vai": {"Tagline": [55.3, 56.4, 59.7]}, "reach": {…}, "speed": {…}, "hold": {…}},
      "aoi_colors": {"Tagline": "#96d732"},
      "insights": ["…"], "note": "…"}
  }],
  "segment_findings": ["…"],
  "actions": [{"title": "…", "text": "…", "preserve": "…"}],
  "retest": {"design": "…", "primary_outcome": "…", "guardrail": "…", "diagnostic_vai_metric": "…"},
  "limits": ["…"], "would_change": ["…"], "sources": ["…"]
}
```

Notes:
- `values` is 60 numbers: for each window (3, 5, 10 s) → for each AOI in `aoi_order` → `[vai, reach, speed, hold]`. `kind` must be one of `overall`, `gender`, `age`, `gender_age`; labels must be `All`, `Men`, `Women`, then the age bands, then `Men <band>` and `Women <band>` (the gap tables look up `Men`, `Women`, `18–24`, `25–34`, `Men 18–24`, `Women 18–24`).
- The viewing order is derived from Speed; the audience, comparison and gap tables are computed. You write only the findings text.
- `stimulus` is the clean analysed image (no outlines, no pointer). Each AOI has a `shape`: its polygon as `[x%, y%]` points of the image (a rectangle is four points), and the dashboard's colour. The script draws the outlines (with a *Show AOIs* switch), puts the numbered viewing-order badges on the AOI corners, and crops the AOI cards from the clean image. AOI names must be identical across designs and in `aoi_order`.
- Audiences under 30 viewers are muted and marked † automatically.
- Keep the discipline of the brief: audience, window and N with every number, no winner without an outcome, hypotheses labelled as hypotheses, no participant-level data or private links.

## Writing tips

- Lead each finding with the observation (AOI, VAI and components, audience, window, N), then the implication, then the design hypothesis.
- Keep `verdict_text` to three sentences a brand manager can act on, and put the recommendation and its caveat in the same card.
- Explain VAI patterns in words: "few viewers reach it, late, and only briefly" rather than a bare number.
