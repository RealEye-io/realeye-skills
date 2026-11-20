---
name: neuromarketing-image-report
description: Interpret measured RealEye ET Platform webcam eye tracking for ads, packaging, and other static images, with shot-level guidance for video ads. Build a professional, self-contained HTML report for brand and creative teams using only RealEye VAI and its Reach, Speed and Hold components, by gender, age and time window, with the viewing order, heatmaps and AOI overlay. Diagnose what drew attention and decide between versions using the outcome that fits the campaign goal, not the heatmap. Not for AI attention prediction.
license: MIT
metadata:
  author: RealEye
  version: "1.5.0"
---

# Neuromarketing image report

Use **measured gaze to diagnose the creative**, not to pick the best ad by itself. Attention tells you where people looked, not what they liked, understood, remembered, or will buy. For a creative choice, pair eye tracking with an independent outcome: unaided brand and claim recall for communication, or a product-choice or field test for trial. If no such outcome was measured, give attention findings and a retest plan, not an effectiveness winner.

Read the [RealEye Neuromarketing Report Methodology](<references/RealEye Neuromarketing Report Methodology.md>) before planning or adjudicating a comparison. It contains the survey rubric, video workflow, research notes, and evidence limits.

## 1. Identify the decision

- Capture the exact creative version, target audience, placement (feed, ad break, print or shelf), task (free viewing or directed search), exposure, and the decision the brand team needs to make. Keep tested conditions separate from the intended real-world placement.
- Before testing, specify **one primary outcome**, its scoring and denominator, the smallest worthwhile difference, and any guardrails. Example: *percentage of respondents who can name the toothpaste brand and give its whitening claim without prompting, in the same response record*. Count other outcomes and attention measures as secondary or diagnostic. Do not search many AOIs, windows and audiences and promote whichever result looks best. If no outcome was specified before the data were seen, label the comparison exploratory.
- Define the must-not-miss elements and when they matter. For a toothpaste ad, start with the logo, pack shot, claim or demonstration, face/smile, and CTA or offer. State what the edit must preserve.

## 2. Establish what evidence is available

Read [RealEye data and metric definitions](references/realeye-data.md) before extracting numbers.

| Input | What to deliver |
|---|---|
| Dashboard access (signed in), AOI statistics, AOI VAI report, or exports | VAI, Reach, Speed and Hold per AOI, window and audience. See the [HTML report guide](references/html-report.md) for how to pull them. |
| Survey or choice outcome, with a variant mapping | Assess the planned outcome if the design and data support it. Without gaze, do not infer why viewers responded differently. With gaze, report both measures and their separate denominators. |
| Only a measured heatmap | Qualitative clusters and possible blind spots with the map's window and filters if known. No numbers read from colours. |
| Creative alone, no usable results, or a link that requires unavailable access | No measured findings. Request the AOI statistics or AOI VAI report with the matching creative. Request the survey data if asked to pick a winner. If the creative is available, offer an AOI plan labelled as hypotheses. Do not substitute Attention Predictor. |

Use supplied files first. A `app.realeye.io/dashboard/item/...` URL is a web UI link, not a public API endpoint. Use authorised dashboard access (the user's signed-in browser) for read-only inspection. On a login wall, ask the user to sign in or to supply exports. Do not upload private creatives or participant exports to outside services. Do not ask for passwords or tokens in chat, edit saved AOIs, change participant status, or create share links. Never print participant names or other personal data.

## 3. Design or audit the comparison

1. **Assignment and placement.** For a first-impression A/B test, randomly assign target viewers to **one version each**; seeing A can teach the brand or claim before B. Match context, task, device, and exposure conditions: a real or credible feed, ad break, or shelf with competitors where possible. Use placement-appropriate timing (a few seconds for a brief feed exposure; actual runtime, audio and realistic skip conditions for video). An isolated forced view can overstate real-world attention opportunity.
2. **Study and sample.** Match the exact item/version and record the analysed base per item/window, sample source, tracker, filters and exclusions. Rough planning only: **30-50 usable viewers per version** for descriptive maps; detecting meaningful A/B differences can need **100+ per version**; **30+ per audience** for gender and age cuts. Size the study for the primary outcome, expected variance, smallest worthwhile effect, and losses.
3. **Regions.** Verify saved AOIs on the tested creative, including size and overlap, and name each AOI by what it covers on the image. Prefer regions the tracker can separate: webcam tracking is less precise than a lab tracker. Label AOIs chosen after seeing results exploratory. Do not fabricate measurements.
4. **Windows.** Use the first 3, 5 and 10 seconds (cumulative, starting at 0.5 s to reduce initial centre bias) or the placement-relevant equivalents, and state the actual bounds. For **video**, map AOIs by shot or with validated moving regions if supported. Compare attention by a shared deadline (e.g. the first 3 s) and from the actual brand/pack/claim reveal among people who reached that moment. Inspect time-sliced maps, not a single whole-video heatmap.

## 4. Answer the questions behind the brief

Use [the interpretation guide](references/interpretation.md) to choose which questions matter. Lead with the evidence that could change the decision. Answer them with **VAI and its components only**:

- **Was the key element reached?** Reach: the share of viewers who looked at the AOI. A low Reach is *few viewers looked there in this window*, not *nobody saw it*.
- **Was it noticed soon enough?** Speed: how early in the viewing order. Rank the AOIs by Speed to get the viewing order.
- **Did viewers stay?** Hold: how long attention stays on the AOI relative to the window. Short Hold on a logo can be fine; on a claim that must be read it is not.
- **Did the intended hierarchy work?** Compare the VAI of brand, message, product, action and competing elements according to their roles, then explain each with its Reach, Speed and Hold. VAI is neither a share of the image's attention nor a percentage of viewers, and a higher VAI does not necessarily serve the goal.

For each finding: cite the **observation** (AOI, VAI components, audience, window, N), explain its implication, and separate the **design hypothesis**. A direct-gaze face with higher Hold and a weaker brand banner may justify testing model gaze direction; it does not show the face caused the miss. Heatmaps average people and omit covert attention.

## 5. Score the outcome before choosing

- Immediately after one exposure, ask **"What brand was advertised?"** and **"What was the main message?"** as unaided, open-ended questions. Do not show the creative again or give answer cues before recall. Agree on accepted brand spellings and claim paraphrases before reading variant results. Count joint recall only when the **same respondent** gets both right.
- If appropriate, add purchase intent (a scale) or product preference/choice after recall; optionally ask clarity or liking. Self-reported intent is not trial or sales. For a trial or behavioural goal, use a measured product choice or field outcome rather than inferring it from a survey or gaze.
- Compare the preselected outcome by version, with counts, analysed bases, absolute differences and uncertainty at the participant level when estimable. Respect preset guardrails; do not combine recall and intent after seeing scores. Prefer B for a communication goal if it has credibly better joint recall, even if A has higher VAI. If outcome data are missing, the evidence is too close to call, or the guardrail is unresolved, say so. Do not break a tie with VAI or a heatmap.
- Use discrepancies to plan the edit. High pack Reach but poor brand recall can motivate a clearer or spoken brand cue at the pack reveal; high claim Reach but poor takeout can motivate rewriting the message. High liking and weak brand Reach can flag a branding risk, not demonstrate failed attribution.

## 6. Deliver the report

Write in plain language. **The deliverable is a self-contained, professional HTML report** (one file, images embedded, dark mode, print-to-PDF ready) built with the bundled script `scripts/build_report.py`. Use another format only if the user asks. See [the HTML report guide](references/html-report.md) for the JSON schema, how to pull the data from the RealEye dashboard, and the heatmap sheet generator; see the [worked example](references/worked-example.md) for tone.

### Standing rules for every report

**Write the main report for brand managers.** It exists to help them choose and act, so the main sections are plain, short and free of technical detail. Anything technical goes in a **Technical appendix at the end** (rule 3). In the main sections say "viewers" and "elements" (not AOIs, N, windows, filters or trackers), lead with what to do, and keep a one-line footnote only where a reader could misread a number (e.g. † marks a small audience).

1. **VAI only.** Use only RealEye's VAI and its components Reach, Speed and Hold. Never show raw metrics such as time to first fixation (TTFF), fixation time, fixation ratio, gaze or fixation counts, revisits or K-coefficient: on their own they mislead (a fast TTFF for a handful of viewers looks like speed; a long dwell can mean reading difficulty). The script does not render them.
2. **Say how it was measured, in one plain line near the top:** the test was run on the **RealEye platform with webcam eye tracking** (viewers saw the images on their own devices and their gaze was recorded through their webcams). The details (tracker precision, sample, filters) go in the appendix.
3. **Structure.** Main sections, in this order: *Overall findings and conclusions* (verdict, key findings, conclusions, what to do next) → *What the scores mean (VAI)* (plain definition of Reach, Speed, Hold, how to use it, component patterns, a worked example) → *Viewing order* → one section per design → head-to-head comparison → gender and age insights → how to test it next. Then the **Technical appendix**: about this study (platform, tracking, sample, participant quality filter, windows, audiences, tracker precision), technical notes on VAI (cumulative windows, compare like with like, small groups), evidence and limits, what would change the recommendation, definitions, sources, and the unfiltered dashboard AOI VAI report.
4. **A section that explains VAI,** in plain language, in the main sections: Reach, Speed and Hold in one line each, that VAI is for comparing (not a percentage of viewers), that higher is not always better, that it shows attention not outcome, and the component patterns table.
5. **Clear viewing order.** Show the order of the elements (ranked by VAI Speed) for every design and every window, say whether it is stable across the first 3, 5 and 10 seconds, show numbered markers on the image, and list which elements most viewers reach in each window. It is a relative hierarchy across viewers, never one person's scan path.
6. **Quality filter (technical, appendix).** Analyse only viewers with data quality **Average or better** (`participantQualityGradeItemMin=3&participantQualityGradeItemMax=6` in the dashboard). Apply it to every table, heatmap and audience cut. State the analysed N and how many tests it removed in the appendix. If a source cannot be filtered (the dashboard *AOI VAI report* ignores filters), label it as unfiltered and keep it out of the primary results.
7. **Audiences and windows in full.** For every design give VAI and its components for **all viewers, gender (men, women), age bands (e.g. 18–24, 25–34, 35+) and every gender × age combination, each in the first 3, 5 and 10 seconds**, plus a **heatmap for every audience and window**. Show N per audience, mute audiences under 30 viewers (†), and say plainly when a gap is within noise. Viewers with other or unspecified gender or no recorded age are in the overall results but not in these cuts: say so (appendix).
8. **Embed the dashboard AOI VAI report** per design (analysed image with its AOIs, executive summary, AOI overview, components, per-window tables, insights) in the technical appendix, labelled as unfiltered.
9. **Clean, complete images.** Show the whole creative (tall images have content below the visible viewport), never a mouse pointer on a heatmap or overlay (move the pointer off the image before capturing). Name elements by what they cover (the brand name banner, not the label printed on the pack).
10. **Never state a number you did not read.** Every value comes from RealEye data with its audience and window. Check that VAI equals the mean of its three components before using a row.
11. **Link every table and heatmap to the RealEye dashboard.** Wherever data or a heatmap is shown, give a link to the same view in the RealEye dashboard (heatmap, AOI report, AOI VAI report), with the audience's gender, age and quality filters applied in the link. Always set `dashboard.study_id` and each design's `item_id` in the report JSON; the script then adds the links to the design headers, score tables, audience column headers, every heatmap, the viewing order, the comparison and the appendix.
12. **Make it look like the example.** Every report must look and read like the bundled example (`assets/example/example-report.html`): same section order, same plain-language tone, same tables, charts and heatmap sheets. Start from the template (`assets/template/report.template.json`), fill every placeholder, and do not change the layout or add your own styling; use the script to build it.

### Build the report

1. **Start from the template.** Copy `assets/template/report.template.json` into a new working folder and open `assets/example/example-report.html` (built from `assets/example/report.json`) as the model of how the finished report should look and read. The example is a real two-design report; match its structure, level of detail and tone.
2. Pull VAI, Reach, Speed and Hold for each audience × window (`scripts/dashboard_vai_collect.js`) and the heatmap sheets (`scripts/dashboard_heatmap_sheets.js`), plus the AOI overlay image and the dashboard's own heatmap, following the [guide](references/html-report.md). Name the image files as in the template.
3. Fill the template (every `<…>` placeholder; set `dashboard.study_id` and each `item_id` so the links work).
4. Run `python scripts/build_report.py report.json -o report.html`. The script draws the charts, viewing order, audience tables, comparison and the RealEye links.
5. Open the HTML, check that it renders (no pointer on images, nothing cut off, links open the right dashboard view) and that the numbers match the source, then hand the file to the user. Keep several designs (each analysed separately, then compared) in one report.

Before delivery, reconcile numbers and units with the source, make sure the audience, window and N travel with each number, and remove person-level data, private access links and credentials from the shareable report. Do not publish or send the report without permission.
