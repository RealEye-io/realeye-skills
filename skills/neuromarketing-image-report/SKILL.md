---
name: neuromarketing-image-report
description: Interpret measured RealEye ET Platform eye tracking for ads, packaging, and other static images, with shot-level guidance for video ads. Write a decision brief for brand and creative teams using AOI exports, a measured heatmap or VAI report, and post-view survey or choice data. Diagnose what drew attention and decide between versions using the outcome that fits the campaign goal, not the heatmap. Not for AI attention prediction.
license: MIT
metadata:
  author: RealEye
  version: "1.2.0"
---

# Neuromarketing image report

Use **measured gaze to diagnose the creative**, not to pick the best ad by itself. A fixation tells you where someone looked, not what they liked, understood, remembered, or will buy. For a creative choice, pair eye tracking with an independent outcome: unaided brand and claim recall for communication, or a product-choice or field test for trial. If no such outcome was measured, give attention findings and a retest plan, not an effectiveness winner.

Read the [RealEye Neuromarketing Report Methodology](<references/RealEye Neuromarketing Report Methodology.md>) before planning or adjudicating a comparison. It contains the survey rubric, video workflow, research notes, and evidence limits.

## 1. Identify the decision

- Capture the exact creative version, target audience, placement (feed, ad break, print or shelf), task (free viewing or directed search), exposure, and the decision the brand team needs to make. Keep tested conditions separate from the intended real-world placement.
- Before testing, specify **one primary outcome**, its scoring and denominator, the smallest worthwhile difference, and any guardrails. Example: *percentage of respondents who can name the toothpaste brand and give its whitening claim without prompting, in the same response record*. Count other outcomes and gaze metrics as secondary or diagnostic. Do not search many AOIs, windows, and metrics and promote whichever result looks best. If no outcome was specified before the data were seen, label the comparison exploratory.
- Define the must-not-miss elements and when they matter. For a toothpaste ad, start with the logo, pack shot, claim or demonstration, face/smile, and CTA or offer. State what the edit must preserve.

## 2. Establish what evidence is available

Read [RealEye data and metric definitions](references/realeye-data.md) before extracting numbers.

| Input | What to deliver |
|---|---|
| AOI (Area of Interest) Overall Stats, readable dashboard metrics, or native image AOI VAI Report | Quantitative gaze findings for the people and windows actually documented. Use the matching creative or frames to ground layout recommendations. If absent, do not invent placement or contrast. |
| Survey or choice outcome, with a variant mapping | Assess the planned outcome if the design and data support it. Without gaze, do not infer why viewers responded differently. With gaze, report both measures and their separate denominators. |
| Only a measured heatmap | Qualitative clusters and possible blind spots with the map's window, view type, and filters if known. No percentages, timing, sequence, or count estimates from colors. |
| Creative alone, no usable results, or a link that requires unavailable access | No measured findings. Request the **AOI Overall Stats** CSV or (for images) **AOI VAI Report** PDF with the matching creative. Request the survey data if asked to pick a winner. If the creative is available, offer an AOI plan labeled as hypotheses. Do not substitute Attention Predictor. |

Use supplied files first. A `app.realeye.io/dashboard/item/...` URL is a web UI link, not a public API endpoint. Use authorized dashboard access for one-off inspection, or the documented read-only `api2` exports if already configured. On a login wall, use the export fallback. Do not upload private creatives or participant exports to outside services. Do not ask for passwords or tokens in chat, edit saved AOIs, change participant status, or create share links as part of an analysis.

## 3. Design or audit the comparison

1. **Assignment and placement.** For a first-impression A/B test, randomly assign target viewers to **one version each**; seeing A can teach the brand or claim before B. Match context, task, device, and exposure conditions: a real or credible feed, ad break, or shelf with competitors where possible. Use placement-appropriate timing (e.g., a few seconds for a brief feed exposure; actual runtime, audio and realistic skip conditions for video). An isolated forced view can overstate real-world attention opportunity.
2. **Study and sample.** Match the exact item/version and record the analyzed base per item/window, sample source, tracker, filters and exclusions. Separate missing/unusable gaze from eligible viewers with no fixation. Rough planning only: **30-50 usable viewers per version** for descriptive maps; detecting meaningful A/B differences can need **100+ per version**. Neither guarantees a stable map or adequate power. Size the study for the primary outcome, expected variance, smallest worthwhile effect, and losses.
3. **Regions.** Verify saved AOIs on the tested creative, including size and overlap. Prefer meaningful regions that the tracker can separate: report **pack** attention, not logo attention, if the logo is too small to resolve on the tube. Label AOIs chosen after seeing results exploratory. Propose missing AOIs; do not fabricate measurements.
4. **Windows.** Use a placement-relevant early window and a longer matched window if available. State actual bounds. The image VAI windows are cumulative; RealEye commonly starts at 0.5 s to reduce initial center bias, not eliminate it. For **video**, map AOIs by shot or with validated moving regions if supported. Compare attention by a shared deadline (e.g. the first 3 s) and from the actual brand/pack/claim reveal among people who reached that moment. Inspect time-sliced maps or paths, not a single whole-video heatmap. Report viewing drop-off and timed gaze spread separately; without playback/skip evidence, do not infer retention from lost gaze.

## 4. Answer the questions behind the brief

Use [the interpretation guide](references/interpretation.md) to choose which questions matter. Lead with the evidence that could change the decision.

- **Was the key element noticed?** Start with fixation Ratio, the share of the analyzed item cohort with at least one qualifying fixation. Give `count/N` only when verified. Report a miss as *no recorded fixation in this window*, not *did not see*.
- **Was it noticed soon enough?** Pair early Ratio with mean or median TTFF (time to first fixation) among fixators. A fast TTFF for a small subset does not mean broad or first attention. Claim sequence only with participant-level order or fixation evidence, stating the base for the pattern.
- **Where did looking time go?** Pair fixation time spent and revisits with Ratio. Low Ratio and long time among fixators means longer looking among relatively few people. Compare the brand and claim's share of recorded fixation time against the rest only with a verified same-window total and no double-counted overlap. Long looks or returns may reflect interest, reading difficulty, or noise, not depth or liking.
- **Did the intended hierarchy work?** Compare brand, message, product, action and competing elements according to their roles. Use **Measured VAI** and its Reach / Speed / Hold as a summary when provided, then explain it using the underlying metrics. The composite VAI score is neither a share of the image's attention nor a percentage of viewers. A higher score does not necessarily serve the goal.

For each finding: cite the **observation** (AOI, value, sample, window, source), explain its implication, and separate the **design hypothesis**. For example, a face or smile with high reach and a low-reach pack may justify testing model gaze direction or placing the pack closer to the claim. It does not show the face caused the misses. Heatmaps average people, omit covert attention, and have no required F-shape. Keep fixations, gaze samples, and clicks separate.

## 5. Score the outcome before choosing

- Immediately after one exposure, ask **"What brand was advertised?"** and **"What was the main message?"** as unaided, open-ended questions. Do not show the creative again or give answer cues before recall. Agree on accepted brand spellings and claim paraphrases before reading variant results. Count joint recall only when the **same respondent** gets both right.
- If appropriate, add purchase intent (a scale) or product preference/choice after recall; optionally ask clarity or liking. Self-reported intent is not trial or sales. For a trial or behavioral goal, use a measured product choice or field outcome rather than inferring it from a survey or gaze.
- Compare the preselected outcome by version, with counts, analyzed bases, absolute differences and uncertainty at the participant level when estimable. Respect preset guardrails; do not combine recall and intent after seeing scores. Prefer B for a communication goal if it has credibly better joint recall, even if A received more looks. If outcome data are missing, the evidence is too close to call, or the guardrail is unresolved, say so. Do not break a tie with VAI or a heatmap.
- Use discrepancies to plan the edit. High pack reach but poor brand recall can motivate a clearer or spoken brand cue at the pack reveal; high claim reach but poor takeout can motivate rewriting the message. High liking and weak brand reach can flag a branding risk, not demonstrate failed attribution. Link individual statements about who looked and remembered only when records match.

## 6. Deliver the brief

Write in plain language. **Default deliverable: a self-contained, professional HTML report** (one file, images embedded, dark mode, print-to-PDF ready) built with the bundled script; use another format only if the user asks for it. See [the HTML report guide](references/html-report.md) for the JSON schema and build steps, and the [worked example](references/worked-example.md) for tone.

### Standing rules for every report

These apply whenever the data allows them; the full how-to is in [the HTML report guide](references/html-report.md).

1. **Quality filter: analyse only participants with data quality Average or better** (RealEye's *Data quality* filter set to Average–Perfect; in the dashboard URL hash `participantQualityGradeItemMin=3&participantQualityGradeItemMax=6`). Apply it to every table, heatmap and segment. State the analysed N and how many tests the filter removed. If a source cannot be filtered (the dashboard *AOI VAI report* ignores filters), label it as unfiltered, never mix it silently into the filtered results.
2. **Gender and age insights whenever possible.** Re-run the AOI report with the Gender filter (men, women) and Age bands (e.g. 18–24, 25–34, 35+) on top of the quality filter. Report viewing ratio, TTFF and VAI with its components per segment, show N for each segment, mute segments under 30 viewers, give a women-vs-men difference with a 95% interval, and say plainly when a gap is within noise. Viewers with other or unspecified gender or no recorded age are not in those cuts: say so. Skip a cut only if the data is not available, and say that.
3. **Viewing order, viewing ratio and VAI in detail.** For every design and AOI show: viewing ratio (fixation ratio with count/N), TTFF, fixation time among fixators, VAI with Reach, Speed and Hold, and the viewing order ranked two ways (VAI Speed and average TTFF) with numbered markers on the AOI image. Viewing order is a relative hierarchy across viewers, never one person's scan path.
4. **Embed everything the AOI VAI report contains**, especially the analysed image with its AOIs drawn on it: AOI overlay, measured heatmap, executive summary, AOI overview, VAI components, the per-window VAI, Reach, Speed and Hold tables (0.5–3, 0.5–5, 0.5–10 s) and the dashboard's insights. Place it per design as a labelled "Dashboard AOI VAI report" block.
5. **Heatmaps and AOI images must be clean and complete.** Show the whole image, not a cropped viewport (zoom the dashboard out until the full creative is visible; check the bottom of tall images). Move the mouse pointer off the image before capturing, so no cursor appears on any heatmap or overlay. Name each AOI by what it actually covers on the image (e.g. the brand name banner, not the label printed on the pack).
6. **Never state a number you did not read.** Every value comes from the RealEye data with its window and N.

### Build the report

1. Capture the evidence next to the JSON: AOI overlay image and measured heatmap per design (crop dashboard chrome with the `crop` option; never invent a visual).
2. Write `report.json` (schema in the guide).
3. Run `python scripts/build_report.py report.json -o report.html`. The script draws the charts, the viewing order, the segment matrices and the head-to-head table (differences with a 95% interval) so you do not compute them by hand.
4. Open the HTML, check that it renders (no pointer on images, nothing cut off) and that the numbers match the source, then hand the file to the user. Keep several designs (each analysed separately, then compared) in one report.

The report must contain:

1. **Decision at a glance:** Creative/version, study context, and recommendation: prefer a version for the stated outcome, keep a feature, revise and retest, or collect more evidence. Lead with the primary outcome and uncertainty when measured. Otherwise say what can and cannot be decided from gaze alone.
2. **Two to four findings:** What worked, what risks the objective, and where evidence is weak. If provided and approved for the report, show the matching stimulus/AOI overlay and measured heatmap with a caption naming the item, view type, sample and window. Do not invent missing visuals.
3. **Prioritized actions:** Identify the first concrete edit (placement, contrast, copy, or shot/audio cue). Specify what to preserve and why. Give the retest's primary outcome and guardrail plus the diagnostic gaze metric and window. Recommend a test, not a causal story the data cannot isolate.
4. **Evidence and limits:** Give outcome counts/rates by version and uncertainty if available, separately from the AOI table (role, window, eligible N, fixation Ratio, TTFF and fixation time spent among fixators; VAI only when useful). Add assignment, scoring, missingness, filters, export sources and geometry or exposure limitations. Label unavailable values; show what evidence could change the decision.

Before delivery, reconcile numbers and units with the source, make sure denominators and windows travel with each comparison, and remove person-level data, private access links, and credentials from the shareable report. Do not publish or send the report without permission.
