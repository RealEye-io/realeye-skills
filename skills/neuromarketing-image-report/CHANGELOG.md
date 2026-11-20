# Changelog

The version is in `SKILL.md` (`metadata.version`) and is stamped into every report this skill builds.

## 1.16.0
- Sample-size certainty: a result is certain only with at least 100 viewers in every group analysed. The report says so, lists which groups reach 100, marks groups of 30 to 99 with ‡ (indicative) and under 30 with † (anecdotal) everywhere, and the build rejects high confidence on groups under 100.

## 1.15.1
- `scripts/audit_report.py` checks a built report (and its JSON) against the standing rules; the bundled example passes all checks.
- SKILL.md made consistent with the newer rules: current section order, "higher is better", duplicate rule removed.

## 1.15.0
- Designs without AOIs: the skill defines 3 to 8 useful AOIs (`references/aoi-design.md`), checks them with `scripts/check_aois.py` (bounds, size, overlap, preview image), measures them read-only through `customAois` in `dashboard_vai_collect.js`, and marks them as proposed in the report and the blueprint.

## 1.14.0
- The whole designs open the report, each with what it presents and its assumed purpose.
- Higher VAI is stated as better at attracting visual attention (findings, explainer, tooltips, tables).
- Differences between designs are always shown: `{{cmp}}`, `{{diff}}` and `{{gap}}` tokens read the numbers from the data; the build warns about unpaired numbers.
- Hypotheses section: the designer's assumptions tested with verdicts and proven evidence.
- Gender and age insights moved directly after the overall findings.
- "How to improve the study": AOIs, respondents, survey questions, benchmarking, other ideas.
- Every "RealEye" has a tooltip that links to www.RealEye.io; Definitions link to RealEye support pages.
- Floating contents menu with scroll tracking and copy-link buttons; link buttons on headings.
- Mark up tool: highlight text, mark areas, erase; saved in the reader's browser.

## 1.13.0
- Overall findings and conclusions are the first and strongest section. Every finding is its own sub-section with conclusion, why, evidence (numbers checked against the data by the build script, links to tables, charts, heatmaps and the RealEye dashboard), what it means and confidence. Conclusions and actions are sub-sections that link to the findings they follow from. Build fails on wrong numbers, missing why/evidence or broken links.
- Rules for checking conclusions before publishing.
- Study blueprint section: study set-up, downloadable stimuli, exact AOI coordinates in pixels, analysis settings, steps to rerun, `study-blueprint.json` and `report.json` downloads; `aoi_coordinates` table in the data pack.
- Report and skill version stamped in header, footer, meta tag, appendix, data pack and blueprint.

## 1.12.0
- Study facts (created, data collected, RealEye version), participant profile (gender, age, device, data quality), charts next to tables.

## 1.11.0
- Collapsed data pack (markdown with CSV tables) for AI assistants.

## 1.10.0
- Closing AI-agent prompt with the whole report, copy and download buttons.

## 1.9.0
- Tooltip definitions for VAI, Reach, Speed, Hold and AOI.

## 1.8.0
- Tested designs and AOIs in the intro, with dashboard links.

## 1.7.0
- Browser data playbook, viewing order by audience, design thumbnails on hover.

## 1.6.0
- Dashboard-style design, clean image with AOI outlines, AOI cards, dashboard-like heatmaps.

## 1.5.0
- Bundled example and template, dashboard links on tables and heatmaps.

## 1.4.0
- Brand-manager main sections, technical details in an appendix.

## 1.3.0
- VAI-only report, RealEye webcam statement, conclusions first, VAI explainer, viewing order, gender x age x window tables and heatmaps.

## 1.0.0 to 1.2.0
- HTML report with quality filter, gender and age cuts, viewing order, VAI components, embedded AOI VAI report; references for interpretation and data.
