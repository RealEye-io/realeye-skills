# HTML report guide

`scripts/build_report.py` turns one JSON file into a single self-contained HTML report (Python 3 standard library; Pillow is optional and only shrinks large screenshots). It draws the layout, dark mode, print styling, inline SVG charts, embedded images, the viewing order, gender and age matrices, and the head-to-head table with a 95% interval. It never invents data: anything absent from the JSON shows as `n/a` or is omitted.

```
python scripts/build_report.py report.json -o report.html
```

Image paths in the JSON are relative to the JSON file.

## What the report contains (generated)

1. **Decision at a glance**: recommendation, KPI tiles, study context including the quality filter
2. **Key findings** tagged `strength`, `risk` or `weak-evidence`
3. **One section per design**, analysed separately:
   - AOI overlay image with numbered viewing-order markers, and the measured heatmap
   - AOI table: viewing ratio (count/N), TTFF, fixation time among fixators, VAI, Reach, Speed, Hold
   - VAI components chart; viewing order by VAI Speed and by TTFF, with a first-fixation timeline
   - **Gender** and **age** matrices (viewing ratio, TTFF, VAI, Reach, Speed, Hold) and a women-vs-men gap table
   - Embedded **dashboard AOI VAI report**: analysed image with AOIs, executive summary, AOI overview, per-window VAI/Reach/Speed/Hold tables and line charts, insights
   - Collapsible table with every AOI report metric
4. **Head-to-head comparison**: viewing order compared, difference table with intervals, grouped charts for every metric
5. **Gender and age insights** across designs
6. **Prioritised actions**, retest plan, evidence and limits, definitions

## Standing rules (see SKILL.md)

- Quality filter Average or better on every result; state N and how many tests were removed.
- The dashboard AOI VAI report cannot be filtered by quality: embed it, but label it unfiltered (`dashboard_vai.note`).
- Gender and age cuts whenever the data allows; mute segments under 30 viewers (the script does this automatically).
- Clean, complete heatmap and AOI images, with no mouse pointer on them.

## How to get the data from the dashboard

The RealEye dashboard keeps its filters in the URL hash, so segments can be loaded by changing it. Load a fresh page between changes (hash-only navigation does not reload the data):

```
https://app.realeye.io/dashboard/item/<ITEM_ID>/aoi#itemId=<ITEM_ID>&genderMale=true&genderFemale=true&genderOther=true&genderNotSpecified=true&ageMin=0&ageMax=99&participantTypeRealEye=true&participantTypeOwn=true&deviceDesktop=true&deviceSmartphone=true&deviceSmartphoneVertical=true&deviceSmartphoneHorizontal=true&deviceTablet=true&setupLocal=true&setupMouse=true&setupOpengaze=true&setupReWebcamV3=true&participantQualityGradeItemMin=3&participantQualityGradeItemMax=6&filterAnswers=%5B%5D&includeAll=0
```

- Quality: `participantQualityGradeItemMin=3` is Average (1 Very low, 2 Low, 3 Average, up to 6 Perfect). Use `Min=3&Max=6`.
- Gender cut: set one of `genderMale`, `genderFemale` to `true` and the others to `false`.
- Age band: `ageMin` and `ageMax`, e.g. 18–24, 25–34, 35–99. Using 18 as the minimum drops viewers with no recorded age.
- The AOI report page (`/aoi`) lists the viewer count (`N tests`) and the metrics per AOI; wait for the loading indicator to finish.
- Heatmap page (`/` without `/aoi`): fit and zoom out until the full image is visible, move the pointer away, then capture. The page's time-range fields also appear in the hash as `itemTimeFrom`/`itemTimeTo` (ms), but the AOI report's own range is fixed per AOI.
- The AOI VAI report is at `/dashboard/study/<STUDY_ID>/item/<ITEM_ID>/aoi-vai-report` and always covers all participants with data.

## JSON schema

```json
{
  "title": "…", "subtitle": "…", "date": "…", "prepared_for": "optional",
  "study": {"name": "…", "source": "…", "window": "0.5–10 s", "task": "…",
            "quality_filter": "Data quality Average or better (A: 229 of 241 tests …)",
            "independent_groups": false},
  "decision": {"audience": "…", "placement": "…", "primary_outcome": "…",
               "verdict_label": "…", "verdict_text": "…", "summary": "…"},
  "kpis": [{"label": "…", "value": "27%", "note": "62 of 229 viewers"}],
  "headline_findings": [{"tag": "strength|risk|weak-evidence", "title": "…", "text": "…"}],
  "variants": [{
    "id": "A", "name": "…", "description": "…", "n": 229, "excluded": 12,
    "aoi_overlay": {"src": "aoi-A.jpg", "crop": [x0, y0, x1, y1], "caption": "…"},
    "heatmap":     {"src": "heatmap-A.png", "crop": [x0, y0, x1, y1], "caption": "item, view, sample, window"},
    "aois": [{"name": "Tagline", "role": "Claim", "color": "#82c91e", "marker": [23.7, 17.5],
              "count": 204, "n": 229, "ttff": 1.57, "fix_time": 1.76,
              "vai": 62, "reach": 89.1, "speed": 79.0, "hold": 16.5,
              "ttfg": 1.22, "gaze_time": 1.73, "fixations": 1262, "gazes": 19572, "gazes_ratio": 97,
              "avg_fix_dur": 0.28, "ffd": 0.29, "revisits": 1.74, "ttfc": 7.33, "k": 0.54}],
    "segments": {
      "gender": [{"label": "Men", "n": 59, "aois": [ /* same fields as above, same AOI names */ ]},
                 {"label": "Women", "n": 88, "aois": [ … ]}],
      "age":    [{"label": "18–24", "n": 82, "aois": [ … ]}, …]},
    "segment_note": "…",
    "findings": ["…"],
    "dashboard_vai": {
      "scope": "all 240 participants with data, not quality-filtered", "participants": 240,
      "windows": ["0.5–3 s", "0.5–5 s", "0.5–10 s"],
      "summary":   {"Tagline": {"vai": 57.1, "reach": 81.4, "speed": 68.2, "hold": 21.8}, …},
      "by_window": {"vai": {"Tagline": [55.3, 56.4, 59.7], …}, "reach": {…}, "speed": {…}, "hold": {…}},
      "aoi_colors": {"Tagline": "#82c91e", …}, "aoi_image": {"src": "aoi-A.jpg", "crop": […], "caption": "…"},
      "insights": ["…"], "note": "Embedded from the RealEye AOI VAI Report; cannot be filtered by quality."}
  }],
  "segment_findings": ["…"],
  "actions": [{"title": "…", "text": "…", "preserve": "…"}],
  "retest": {"design": "…", "primary_outcome": "…", "guardrail": "…", "diagnostic_gaze_metric": "…"},
  "limits": ["…"], "would_change": ["…"], "sources": ["…"]
}
```

Notes:
- `count` and `n` give the verified count/N; the viewing ratio is computed from them, and they are required for intervals. `ttff` and `fix_time` are seconds among viewers who fixated. `vai`, `reach`, `speed`, `hold` are percentages as RealEye shows them. Omit any field you do not have.
- Use identical AOI names across designs and segments so they line up. Name AOIs by what they cover on the image.
- `crop` is in source-image pixels and removes dashboard chrome from a screenshot. `marker` is the `[x%, y%]` position of the viewing-order number on the AOI image.
- The viewing order is derived from `speed` (and `ttff`); you do not write it.
- Set `independent_groups` to `true` only if different viewers saw each design. Otherwise significant gaps are labelled `indicative` rather than `likely real`.
- Keep the discipline of the brief: windows and denominators with every number, no winner without an outcome, hypotheses labelled as hypotheses, no participant-level data or private links.

## Writing tips

- Lead each finding with the observation (AOI, value, N, window), then the implication, then the design hypothesis.
- Keep `verdict_text` to two or three sentences a brand manager can act on.
- Put the recommendation and its caveat in the same card.
