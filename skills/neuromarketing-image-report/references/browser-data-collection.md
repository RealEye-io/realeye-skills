# Collecting the report data with the browser

The report needs data that only the signed-in RealEye dashboard has. This is the playbook an agent follows with a web browser (the built-in browser pane or Claude in Chrome). Everything is read-only.

## 0. Before you start

- **Sign-in:** the dashboard needs the user's own session. Open `https://app.realeye.io/dashboard/`. If you see a login page, ask the user to sign in in that browser (Google sign-in works) and carry on when they say it is done. Never ask for or type passwords, and never use a token from chat.
- **Never** edit AOIs, change participant status, create share links, download exports, or print participant names (a viewer's display name appears in the fixation data: read only gender and age from it).
- **Tools you need:** navigate, page JavaScript (to read data), screenshot/zoom with *save to disk*, network requests (to find the stimulus image URL), tabs. Use the batch tool to chain steps; one tab per task keeps state clean.
- **What you will collect:** (a) ids, (b) VAI, Reach, Speed and Hold per audience × window, (c) AOI shapes and colours, (d) the clean stimulus image, (e) the main heatmap and the heatmap sheets, (f) the dashboard's AOI VAI report, (g) the study facts and participant profile (section 2b). Then (h) check the render.

## 1. Find the ids

1. Open the link the user gave (`/dashboard/item/<ITEM_ID>/…` or `/dashboard/study/<STUDY_ID>/item/<ITEM_ID>/…`). The item id is the stimulus (one design). The study id appears in the AOI VAI report URL and in the study page `/dashboard/study/<STUDY_ID>/`.
2. Open the AOI report `/dashboard/item/<ITEM_ID>/aoi`. The header shows the stimulus number and file name ("STIMULUS 5 OF 15 · shampoo product.png"), the AOIs and the number of tests. Use the file name for the design name.
3. Repeat for every design you compare. Keep a table: design letter → item id → file name.

## 2. VAI, Reach, Speed, Hold per audience and window (the primary data)

The AOI report loads each AOI's statistics from an internal endpoint that takes the filters and the time range. `scripts/dashboard_vai_collect.js` calls it for every audience × window and fills `window.__VAI`.

1. Open any dashboard page of the study (a fresh tab, same origin as the data).
2. Edit `CONFIG` in the script (item ids, the AOI names exactly as in the dashboard without quotes, windows 3/5/10 s, `minQualityGrade: 3` = Average or better, age bands), run it in the page JavaScript tool. It returns immediately and works in the background (about one request per second; 360 requests take about 6 minutes).
3. Poll `window.__done + '/' + window.__total` and `window.__err.length`; wait for `done == total` with no errors.
4. Read the result in **chunks of about 1.5k characters** (the tool truncates long output): one audience per call, as `label|n|v1,v2,…`. Write the numbers into the report JSON (`segments[].values`, 60 numbers each).
5. **Check every row:** VAI must equal the mean of Reach, Speed and Hold (within 0.2). A mismatch means a transcription error.
6. Check the audience sizes against the dashboard: open the AOI report for one audience (see §9 for the URL) and compare the "N tests" count.

## 2b. Study facts and participant profile

Collect these for the intro tiles, the *Who took part* card and the appendix. Never copy participant names or study author names into the report.

1. **Study created:** open `https://app.realeye.io/dashboard/?status=all&studySearch=<STUDY_ID>` (or search the study id on the studies page and press Enter). The study row shows the creation date under the study name (read the date only, not the author).
2. **Status, type, settings:** open `/dashboard/study/<STUDY_ID>/` and read the page text (page JavaScript `document.querySelector('main').innerText`): study status (Running or Finished), the participant counter ("8711 / 10000"), and the *Study contents* list with each stimulus' display time, finish mode and instruction setting. Click *Study details* for the study type, random order and panelist demographics (what viewers were asked).
3. **RealEye version:** the dashboard sidebar footer shows it ("RealEye v26.11.20.1"; read it with page JavaScript or a zoom on the bottom-left corner). The version at data-collection time is not stored, so report it as the dashboard version at analysis.
4. **Participants:** run `scripts/dashboard_participants.js` (edit `CONFIG`; it fills `window.__PARTICIPANTS`; poll `window.__partDone`). It gives collected and analysed counts, the data-quality distribution, gender, age bands (from the self-reported age; check for implausible values such as age 1), device, tracker set-up, participant type, median browser window, and the first and last collection dates. Dates are as the dashboard stores them; report them as shown.
5. **Study set-up for the blueprint:** from the study page and *Study details*, note for each stimulus the file name, display time, finish mode and instructions, whether the order is random, the participant target and the questions asked, and put them in `blueprint`. This is what someone needs to create the same study again.
6. Put the results in `study_info` and `participants` (see the guide) and add the readable `tracker_text`, `participant_type_text`, `screen_text` and `age_text` lines for the appendix.

## 3. AOI shapes and colours

The report must keep the exact AOI geometry so the study can be recreated. Keep the shapes as numbers, in percent of the image (the report converts them to pixels using the image size, 1024 × 1536 for the example; set `image_px` when it differs). Rectangles come from the dashboard in pixels, polygons as fractions.

Run `scripts/dashboard_aoi_shapes.js` (on the AOI VAI report page to also get the legend colours). Convert the colours to hex. Put each AOI's polygon in `aois[].shape` and its colour in `aois[].color`. Name the AOIs by what they cover on the image (for example "Brand name (banner)", not the label printed on the pack).

## 4. The clean stimulus image

1. Open the AOI report page with the network-requests tool tracking on and look for `project_lg_<ITEM_ID>.jpg` on `d48dl6cezsco5.cloudfront.net` (the page title of that URL shows the pixel size, for example 1024×1536).
2. Open that image URL in a new tab, move the mouse pointer to a far corner (outside the image), and capture the image region at **full resolution** (zoom action, default scale, *save to disk*). Check that no pointer is in the image.
3. Save as `stimulus-<ID>.jpg`.

## 5. Heatmaps

- **Sheets for every audience and window:** open any dashboard page, edit `CONFIG` in `scripts/dashboard_heatmap_sheets.js` (item ids, the stimulus image URLs from §4), run it, wait for `window.__ready`. Then for each design × window: run `window.__show('A', 10)`, move the pointer off the page, and capture the page top-left region that holds the sheet (it fills the viewport width; its height is about half the width) with the zoom action at **default scale** (a low scale gives a low-resolution image). Save as `heat-sheet-<ID>-<3|5|10>.jpg`. Check the sheet shows all 12 audiences, the N in each label, and no pointer.
- **Main heatmap per design:** `window.__showOne('A', 10)`, capture region `[8, 8, 568, 848]` (zoom, default scale). Save as `heatmap-<ID>.jpg`.
- The dashboard's own heatmap page is `/dashboard/item/<ITEM_ID>/` (filters in the URL hash, §9); the scripts draw the same fixation data with a dashboard-like colour scale so all heatmaps match.

## 6. The dashboard AOI VAI report

Open `/dashboard/study/<STUDY_ID>/item/<ITEM_ID>/aoi-vai-report` for each design. It cannot be filtered: it covers all participants with data. Read its tables with page JavaScript (`[...document.querySelectorAll('main table')].map(t => t.innerText…)`): the first table is the VAI summary (VAI, Reach, Speed, Hold, participants), then four tables with the per-window VAI, Reach, Speed and Hold (0.5–3, 0.5–5, 0.5–10 s). Copy them into `dashboard_vai` and note the participant count. The page also holds the executive summary and the actionable insights text.

## 7. Save and convert the images

Screenshots are saved to a file whose path the tool prints. Copy them next to `report.json` with the names the template expects and convert PNG to JPEG (Pillow: `Image.open(p).convert("RGB").save(name, "JPEG", quality=88)`). Use Windows-style paths (`C:/…`) when Python reads them.

## 8. Build and check

Write `report.json`, run `scripts/build_report.py`, then **render the HTML to an image and look at it** (for example `msedge --headless=new --user-data-dir=<temp> --window-size=1200,2600 --screenshot=out.png file:///…/report.html`; shift sections into view with a small injected script if the page is long). Fix anything cut off, overlapping or unreadable, and confirm no mouse pointer is on any image.

## 9. URLs and filters

Filters live in the URL **hash**. Hash-only navigation does not reload the data, so navigate to the dashboard home first, then to the full URL (or open a new tab).

```
https://app.realeye.io/dashboard/item/<ITEM_ID>/aoi#itemId=<ITEM_ID>&genderMale=true&genderFemale=true&genderOther=true&genderNotSpecified=true&ageMin=0&ageMax=99&participantTypeRealEye=true&participantTypeOwn=true&deviceDesktop=true&deviceSmartphone=true&deviceSmartphoneVertical=true&deviceSmartphoneHorizontal=true&deviceTablet=true&setupLocal=true&setupMouse=true&setupOpengaze=true&setupReWebcamV3=true&participantQualityGradeItemMin=3&participantQualityGradeItemMax=6&filterAnswers=%5B%5D&includeAll=0
```

`participantQualityGradeItemMin=3` is Average or better (1 Very low, 2 Low, 3 Average … 6 Perfect). Gender: set one of `genderMale` / `genderFemale` true and the others false. Age: `ageMin` / `ageMax`. The AOI report page ignores a time range in the hash (its window is fixed per AOI); the heatmap page `/dashboard/item/<ITEM_ID>/` takes `itemTimeFrom` / `itemTimeTo` in milliseconds.

## 10. Pitfalls that cost time

- **Page-JS output is blocked** when it contains URLs or query strings ("Cookie/query string data"). Return only numbers and names; avoid returning image `src` values or links.
- **`const` and `let` do not persist** between page-JS calls. Store anything you need on `window` (for example `window.__D`).
- **Output is truncated** at about 1.5k characters: chunk it.
- **Closing tabs** can reset the tab group; create a tab again with the tabs tool and navigate.
- **Resizing the window** often does not change the viewport. Make canvases fit the viewport width (the sheet script does) and capture with the zoom action at default scale for full resolution.
- **A mouse pointer** appears in screenshots at its last position: hover to a far corner before every capture.
- **Tall images** continue below the visible viewport: check the bottom of every image (the brand banner in the example sits at the very bottom).
- **Local files** may not open in the built-in browser pane; use headless Edge or Chrome to render the report instead.
